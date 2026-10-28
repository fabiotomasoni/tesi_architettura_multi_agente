#!/usr/bin/env python3
"""100 PDF sintetici: 25 casi x 4 documenti. Nessun documento reale inviato alle API."""
import argparse, hashlib, json, os, random, sys
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = Path(__file__).resolve().parent
VERSION = '1.0'

def save(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)

def euro(cents):
    return f'{cents / 100:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.') + ' EUR'

def generate_case(i):
    r = random.Random(42600 + i)
    variant = ['completo', 'capitale_mancante', 'interessi_mancanti', 'tasso_ambiguo', 'periodi_diversi'][((i-1)//5)]
    capital = r.randrange(4500000, 33000000)
    months = r.choice([59,60,61,119,120,121,179,180,181,239,240,241,300])
    rate = r.choice([225,310,375,425,510])
    monthly = Decimal(rate) / Decimal(120000)
    installment = int((Decimal(capital)*monthly/(1-(1+monthly)**(-months))).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    gross = r.randrange(230000,650000)
    tax = gross * 23 // 100
    pension = gross * 919 // 10000
    net = gross-tax-pension
    opening = r.randrange(100000,1800000)
    movements = [dict(date='2025-12-02',description='Accredito retribuzione novembre',cents=net),dict(date='2025-12-05',description='Rata mutuo',cents=-installment)]
    for day in range(6,29):
        movements.append(dict(date=f'2025-12-{day:02}',description=r.choice(['Alimentari','Trasporto','Utenze','Farmacia','Assicurazione','Ristorante','Bonifico familiare']),cents=-r.randrange(1200,28000)))
    interest = r.randrange(120000,880000)
    return dict(id=f'C{i:03}',variant=variant,person=f'{["Elena","Marco","Sara","Davide","Giulia"][i%5]} { ["Riva","Fontana","Greco","Moretti","Villa"][i//5%5]}',
        cf=f'TSTFNT85A01F205{i%10}',iban=f'IT00X0000000000{i:012}',address=f'Via Esempio Sintetico {i}, 24100 Bergamo',email=f'persona{i}@example.invalid',
        employer=f'Impresa Dimostrativa {i} S.r.l.',capital_cents=capital,months=months,rate_bp=rate,installment_cents=installment,
        rate_type='fisso' if i%2 else 'variabile',purpose='acquisto abitazione principale' if i%3 else 'ristrutturazione',share_percent=50 if i%4==0 else 100,
        annual_interest_cents=interest,gross_cents=gross,tax_cents=tax,pension_cents=pension,net_cents=net,
        opening_cents=opening,closing_cents=opening+sum(x['cents'] for x in movements),movements=movements)

SCHEMA={'type':'object','properties':{k:{'type':'string'} for k in ['conto','paga','mutuo','interessi']},'required':['conto','paga','mutuo','interessi'],'additionalProperties':False}

def prose(case, state_dir, offline):
    cache = state_dir / (case['id']+'.json')
    if cache.exists():
        data=json.loads(cache.read_text()); assert data['version']==VERSION
        return data['prose']
    if offline:
        return {k:'Comunicazione dimostrativa relativa alle condizioni e alle operazioni del periodo. I valori di riferimento sono riportati nei prospetti seguenti.' for k in SCHEMA['required']}
    from openai import OpenAI
    ledger_path=state_dir/'budget.json'
    ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {'reserved_usd':0,'calls':[]}
    model=os.getenv('OPENAI_MODEL','gpt-4.1-mini')
    if model != 'gpt-4.1-mini': raise RuntimeError('Modello non previsto dal listino: aggiornare esplicitamente codice e tariffe prima di cambiarlo.')
    prompt=('Scrivi quattro testi amministrativi italiani sintetici, uno per estratto conto, busta paga, situazione mutuo e certificazione interessi. '
        'Ogni testo deve avere 100-180 parole, variare lo stile e descrivere la lettura del prospetto. Non introdurre cifre, nomi, date, diritti fiscali, fatti personali o condizioni economiche; non inventare dati mancanti. '
        'Non dare consigli. Sono documenti fittizi di ricerca. Variante: '+case['variant']+'; indice stilistico: '+case['id'])
    # UTF-8 bytes bound input tokens conservatively; allow schema and message framing overhead.
    input_bound=len(prompt.encode())+len(json.dumps(SCHEMA).encode())+4096
    reserve=input_bound*0.40/1e6+2200*1.60/1e6
    budget=float(os.getenv('BUDGET_USD','8.50'))
    if not 0 < budget <= 9: raise RuntimeError('BUDGET_USD deve essere maggiore di zero e non superiore a 9.')
    if ledger['reserved_usd']+reserve>budget: raise RuntimeError('Budget prudenziale raggiunto. Ripresa consentita solo entro il tetto residuo.')
    entry={'case':case['id'],'reserved_usd':reserve,'status':'pending'}
    ledger['reserved_usd']+=reserve; ledger['calls'].append(entry); save(ledger_path,ledger)
    # No automatic retries: uncertain calls retain their full reservation on disk.
    client=OpenAI(max_retries=0, timeout=90)
    try:
        response=client.chat.completions.create(model=model,messages=[{'role':'user','content':prompt}],max_completion_tokens=2200,
            response_format={'type':'json_schema','json_schema':{'name':'descrizioni','strict':True,'schema':SCHEMA}})
        entry.update(status='received',response_id=response.id,model=response.model,usage=response.usage.model_dump() if response.usage else None)
        save(ledger_path,ledger)
        if response.choices[0].finish_reason!='stop': raise RuntimeError('Risposta incompleta; rilanciare per un nuovo tentativo contabilizzato.')
        data=json.loads(response.choices[0].message.content)
        if set(data)!=set(SCHEMA['required']) or any(not isinstance(v,str) or len(v)>4500 or any(c.isdigit() for c in v) for v in data.values()):
            raise RuntimeError('Descrizioni non valide; prenotazione della chiamata conservata.')
        save(cache,{'version':VERSION,'prose':data}); return data
    except Exception:
        entry['status']='failed_or_uncertain';save(ledger_path,ledger);raise

def render(path, title, sections, note, style_index):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    styles=getSampleStyleSheet();styles['Normal'].fontSize=10;styles['Normal'].leading=14
    story=[Paragraph(escape(title),styles['Title']),Paragraph('FACSIMILE SINTETICO - NON VALIDO PER USI AMMINISTRATIVI',styles['Normal']),Spacer(1,16)]
    for heading, rows in sections:
        story.extend([Paragraph(escape(heading),styles['Heading2'])])
        table=Table([[Paragraph(escape(str(k)),styles['Normal']),Paragraph(escape(str(v)),styles['Normal'])] for k,v in rows],colWidths=[170,325],hAlign='LEFT')
        table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),0.3,colors.lightgrey),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#eef2f5')),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7)]))
        story.extend([table,Spacer(1,14)])
    story.append(Paragraph(escape(note),styles['Normal']))
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.drawString(45,25,'Dati fittizi per sperimentazione | pagina '+str(doc.page))
    SimpleDocTemplate(str(path),pagesize=(595.28,841.89),leftMargin=45,rightMargin=45,topMargin=40,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)

def documents(c,p,out):
    ident=[('Intestatario',c['person']),('Codice fiscale di test (non validato)',c['cf']),('IBAN di test (non operativo)',c['iban']),('Residenza',c['address']),('Contatto',c['email'])]
    common=[('Anagrafica',ident)]
    mortgage=[('Riferimento','Situazione al 31/12/2025'),('Contratto',f'MUT-SYN-{c["id"]}'),('Finalita',c['purpose']),('Tipo tasso',c['rate_type']),('Durata residua',str(c['months'])+' mesi'),('Rata mensile',euro(c['installment_cents'])),('Quota intestazione',str(c['share_percent'])+'%')]
    if c['variant']!='capitale_mancante':mortgage.append(('Capitale residuo',euro(c['capital_cents'])))
    mortgage.append(('Tasso annuo nominale', 'Dato da verificare: 3,10% oppure 4,25%, stesso periodo' if c['variant']=='tasso_ambiguo' else str(c['rate_bp']/100).replace('.',',')+'%'))
    if c['rate_type']=='variabile': mortgage.append(('Avvertenza','La rata e una fotografia del periodo; il tasso futuro non e noto.'))
    ints=[('Anno imposta','2024' if c['variant']=='periodi_diversi' else '2025'),('Finalita',c['purpose']),('Quota intestazione',str(c['share_percent'])+'%'),('Spese accessorie',euro(18000)),('Condizioni fiscali','Requisiti di accesso non certificati da questo prospetto')]
    if c['variant']!='interessi_mancanti':ints.append(('Interessi annui documentati',euro(c['annual_interest_cents'])))
    specs=[('conto','Estratto conto dicembre 2025',common+[('Riepilogo',[('IBAN',c['iban']),('Saldo iniziale',euro(c['opening_cents'])),('Saldo finale',euro(c['closing_cents']))]),('Movimenti',[(x['date']+' '+x['description'],euro(x['cents'])) for x in c['movements']])]),
    ('paga','Prospetto retribuzione novembre 2025',common+[('Datore e competenze',[('Datore',c['employer']),('Contratto lavoro','Tempo indeterminato - impiegato'),('Lordo',euro(c['gross_cents'])),('Ritenute fiscali simulate',euro(c['tax_cents'])),('Contributi simulati',euro(c['pension_cents'])),('Netto',euro(c['net_cents'])),('Accredito','02/12/2025')])]),
    ('mutuo','Situazione del mutuo',common+[('Condizioni documentate',mortgage)]),('interessi','Certificazione interessi mutuo',common+[('Riepilogo annuale',ints)])]
    files=[]
    for kind,title,sections in specs:
        file=out/(c['id']+'_'+kind+'.pdf');render(file,title,sections,p[kind],int(c['id'][1:]));files.append(file.name)
    return files

def main():
    envfile=SCRIPT/'.env'
    if envfile.exists():
        for line in envfile.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key,value=line.split('=',1)
                os.environ.setdefault(key.strip(),value.strip().strip(chr(34)).strip(chr(39)))
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--offline',action='store_true',help='Verifica locale senza API, in cartella separata');ap.add_argument('--cases',type=int,default=25);args=ap.parse_args()
    if not 1<=args.cases<=25:ap.error('--cases deve essere tra 1 e 25')
    if not args.offline and not os.getenv('OPENAI_API_KEY'):sys.exit('Inserisci OPENAI_API_KEY in Scripts/.env prima di avviare.')
    base=ROOT/('Preview_offline' if args.offline else 'Documents');base.mkdir(exist_ok=True)
    state=SCRIPT/('state_offline' if args.offline else 'state');state.mkdir(exist_ok=True)
    # Prevent concurrent runs from bypassing the shared budget ledger.
    lock=SCRIPT/'.generation.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:sys.exit('Generazione gia attiva. Dopo un arresto anomalo, rimuovi .generation.lock solo se nessun processo e attivo.')
    os.close(fd)
    try:
        manifest=[]
        for i in range(1,args.cases+1):
            c=generate_case(i);p=prose(c,state,args.offline);files=documents(c,p,base)
            expected={'S-01':'non_personalizzabile' if c['variant'] in ['capitale_mancante','tasso_ambiguo'] else 'confronto_orientativo_locale', 'S-02':'non_personalizzabile' if c['variant']=='interessi_mancanti' else 'ricerca_con_requisiti_da_verificare'}
            manifest.append({'case':c,'files':files,'sha256':{f:hashlib.sha256((base/f).read_bytes()).hexdigest() for f in files},'expected':expected,
                'external_allowed':{'mercati':{'tipo':c['rate_type'],'durata_fascia_mesi':[60*((c['months']-1)//60)+1,60*((c['months']-1)//60+1)]},'fiscale':{'anno':2024 if c['variant']=='periodi_diversi' else 2025,'categoria':'interessi mutuo','finalita':c['purpose']}},
                'warnings':['I campi omessi nel PDF non sono utilizzabili anche se presenti nel generatore.','Periodi diversi non implicano discordanza.','Dati fiscali simulati, nessuna attestazione di spettanza.']})
            save(state/'ground_truth.json',manifest)
            print(f'{i}/{args.cases} fascicoli pronti ({4*i} PDF)',flush=True)
        print('Completato. Annotazioni riservate al valutatore: '+str(state/'ground_truth.json'))
    finally:lock.unlink(missing_ok=True)

if __name__=='__main__':main()
