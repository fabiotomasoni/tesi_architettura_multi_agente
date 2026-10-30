"""Verifica locale report/PDF senza modelli e senza stampare valori finanziari."""
import argparse,hashlib,json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from pypdf import PdfReader


def number(raw):return Decimal(raw.removesuffix(' EUR').removesuffix('%').strip().replace('.','').replace(',','.'))


def verify(report, directory):
    documents={hashlib.sha256(p.read_bytes()).hexdigest():p for p in directory.glob('*.pdf')}
    checked=0
    problems=[]
    required={'S-01':{'rate_type','remaining_principal','remaining_months','annual_rate','payment_amount','payment_frequency'},'S-02':{'tax_year','purpose','annual_interest','ownership_share'}}
    expected_scenarios=set(report['requested_scenarios'])
    actual=[s['scenario'] for s in report['document_data']]
    if set(actual)!=expected_scenarios or len(actual)!=len(expected_scenarios):
        problems.append('Sezioni documentali mancanti, duplicate o non richieste')
    labels={'rate_type':'Tipo tasso','remaining_principal':'Capitale residuo','remaining_months':'Durata residua','annual_rate':'Tasso annuo nominale','payment_amount':'Rata mensile','payment_frequency':'Rata mensile','tax_year':'Anno imposta','purpose':'Finalita','annual_interest':'Interessi annui documentati','ownership_share':'Quota intestazione'}
    for section in report['document_data']:
        expected_fields=required[section['scenario']] | ({'mortgage_type'} if section['scenario']=='S-01' else set())
        if set(section['facts'])!=expected_fields:
            problems.append(section['scenario']+': inventario campi incompleto o inatteso')
        for name,fact in section['facts'].items():
            if fact['status'] in {'missing','not_specified'}:
                hashes={f.get('source',{}).get('document_sha256') for f in section['facts'].values()}
                if name in labels:
                    for digest in hashes:
                        if digest in documents:
                            text='\n'.join(p.extract_text() or '' for p in PdfReader(documents[digest]).pages)
                            if labels[name] in text.splitlines():
                                problems.append(f"{section['scenario']}/{name}: campo dichiarato assente ma etichetta presente")
                continue
            source=fact.get('source',{})
            path=documents.get(source.get('document_sha256'))
            if path is None:
                problems.append(f"{section['scenario']}/{name}: PDF di origine non identificato");continue
            try:
                text=PdfReader(path).pages[source['page']-1].extract_text() or ''
                if hashlib.sha256(text.encode()).hexdigest()!=source['page_text_sha256']:raise ValueError('testo pagina diverso')
                if not 0<=source['start']<source['end']<=len(text):raise ValueError('intervallo non valido')
                raw=text[source['start']:source['end']]
                if raw!=source['quote']:raise ValueError('citazione non corrispondente')
                if name in labels and source['label']!=labels[name]:raise ValueError('etichetta diversa dal campo atteso')
                before=text[:source['start']].rstrip()
                if not before.endswith(source['label']):raise ValueError('etichetta non corrispondente')
                if fact['status']=='validated':
                    rule=fact['transformation']
                    if rule=='italian_number':expected=number(raw)
                    elif rule=='months_from_label':expected=number(raw.removesuffix(' mesi'))
                    elif rule=='percentage_to_fraction':expected=number(raw)/100
                    elif rule=='monthly_from_label':
                        if source['label']!='Rata mensile':raise ValueError('derivazione non supportata')
                        expected='monthly'
                    elif rule=='category_mapping':expected={'fisso':'fixed','variabile':'variable','misto':'mixed','acquisto abitazione principale':'primary_home_purchase','ristrutturazione':'renovation'}[raw]
                    elif rule=='identity':expected=raw
                    else:raise ValueError('trasformazione non riconosciuta')
                    if isinstance(expected,Decimal):
                        if expected!=Decimal(str(fact['value'])):raise ValueError('valore trasformato diverso')
                    elif expected!=fact['value']:raise ValueError('valore diverso')
                period=fact.get('period_source')
                if not period:raise ValueError('origine periodo assente')
                period_path=documents[period['document_sha256']]
                page=PdfReader(period_path).pages[period['page']-1].extract_text() or ''
                if hashlib.sha256(page.encode()).hexdigest()!=period['page_text_sha256']:raise ValueError('testo periodo diverso')
                quote=page[period['start']:period['end']]
                if quote!=period['quote'] or not page[:period['start']].rstrip().endswith(period['label']):raise ValueError('riferimento periodo non coerente')
                expected_period=datetime.strptime(quote,'Situazione al %d/%m/%Y').date().isoformat() if period['label']=='Riferimento' else f'{int(quote):04}-12-31'
                if expected_period!=fact['period']:raise ValueError('periodo non coerente')
                checked+=1
            except (ValueError,KeyError,TypeError,IndexError,ArithmeticError):
                problems.append(f"{section['scenario']}/{name}: riferimento o trasformazione non verificabile")
    return checked,problems


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--pdf-dir',type=Path,default=Path(__file__).resolve().parents[1]/'dataset'/'Documents')
    args=parser.parse_args()
    checked,problems=verify(json.loads(args.report.read_text()),args.pdf_dir)
    print('Fatti verificati:',checked)
    print('Problemi:',len(problems))
    for problem in problems:print(problem)
    raise SystemExit(1 if problems else 0)


if __name__=='__main__':main()
