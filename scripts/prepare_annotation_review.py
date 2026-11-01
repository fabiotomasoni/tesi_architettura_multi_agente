"""Schede locali per rivedere il riferimento contro i PDF; nessun giudizio assegnato."""
import argparse
import hashlib
from html import escape
import json
import os
from pathlib import Path
from urllib.parse import quote

from pypdf import PdfReader
if __package__:
    from .prepare_evaluation_annotations import FIXTURE_RATES
else:
    from prepare_evaluation_annotations import FIXTURE_RATES

ROOT = Path(__file__).resolve().parents[1]
FIRST_CASES = ['C001', 'C006', 'C011', 'C016', 'C021']
FIELDS = {
    'mortgage_type': ('Tipologia del mutuo', None),
    'rate_type': ('Tipo di tasso', 'Tipo tasso'),
    'remaining_principal': ('Capitale residuo', 'Capitale residuo'),
    'remaining_months': ('Durata residua', 'Durata residua'),
    'annual_rate': ('TAN', 'Tasso annuo nominale'),
    'payment_amount': ('Rata documentata', 'Rata mensile'),
    'payment_frequency': ('Periodicità', 'Rata mensile'),
    'tax_year': ('Anno d’imposta', 'Anno imposta'),
    'purpose': ('Finalità fiscale', 'Finalita'),
    'annual_interest': ('Interessi annui', 'Interessi annui documentati'),
    'ownership_share': ('Quota d’intestazione', 'Quota intestazione'),
}
STATES = {'validated': 'Presente', 'missing': 'Mancante', 'ambiguous': 'Ambiguo',
          'not_specified': 'Non specificato'}
VALUES = {'fixed': 'fisso', 'variable': 'variabile', 'mixed': 'misto',
          'monthly': 'mensile', 'primary_home_purchase': 'acquisto abitazione principale',
          'primary_home_construction': 'costruzione abitazione principale',
          'renovation': 'ristrutturazione', 'other': 'altra finalità'}
UNITS = {'EUR': 'EUR', 'month': 'mesi', 'percent_per_year': '% annuo',
         'category': 'categoria', 'year': 'anno', 'fraction': 'frazione (1 = 100%)'}
LIMITS = {
    'documents_synthetic': 'Documenti sintetici, non documenti finanziari reali.',
    'fixtures_simulated': 'Fonti sperimentali simulate, non tassi o norme reali aggiornati.',
    'no_recommendation': 'Nessuna raccomandazione o convenienza personale attestata.',
    'no_tax_entitlement': 'Nessuna spettanza fiscale o detrazione calcolata.',
    'hypothetical_allocation_only': 'Interessi × quota è solo un’ipotesi: importo dell’intero mutuo, non già ripartito.',
    'variable_or_mixed_frozen_rate_not_forecast': 'Tasso variabile/misto mantenuto costante: scenario, non previsione.',
}


def text(value):
    return escape(str(value), quote=True)


def cell(value):
    return '<td>' + text(value) + '</td>'


def table(headers, rows):
    return ('<div class="table"><table><thead><tr>' + ''.join('<th scope="col">' + text(h) + '</th>' for h in headers)
            + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(cell(v) for v in row) + '</tr>' for row in rows)
            + '</tbody></table></div>')


def source_fragments(pages, key):
    """Solo etichetta/valore: niente testo integrale o identità nell’HTML."""
    label = FIELDS[key][1]
    if label is None:
        return 'Nessuna classificazione esplicita annotata: controllare l’intero PDF; non dedurla dalla finalità.'
    hits = []
    for number, content in enumerate(pages, 1):
        lines = [line.strip() for line in content.splitlines()]
        for index, line in enumerate(lines):
            if line == label:
                raw = lines[index + 1] if index + 1 < len(lines) else '[valore non trovato]'
                hits.append(f'Pagina {number}: {label} → {raw}')
    if not hits:
        return f'Etichetta «{label}» non trovata nelle {len(pages)} pagine. Controllare nel PDF che il dato non compaia altrove.'
    result = ' | '.join(hits)
    if key == 'payment_frequency':
        result += ' — periodicità ricavata dalla dicitura «Rata mensile».'
    return result


def display_value(fact):
    value = fact['value']
    if value is None:
        return 'Nessun valore utilizzabile'
    return f'{VALUES.get(value, value)} [{value}]' if value in VALUES else str(value)


def pdf_link(path, output):
    # Spostando l'intera repository, la scheda in runs mantiene i collegamenti.
    return quote(Path(os.path.relpath(path, output.parent)).as_posix(), safe='/')


def review_case(case, directory, output):
    cid = case['case_id']
    pages = {}
    links = []
    for scenario, kind in [('S-01', 'mutuo'), ('S-02', 'interessi')]:
        path = directory / f'{cid}_{kind}.pdf'
        pages[scenario] = [p.extract_text() or '' for p in PdfReader(path).pages]
        links.append(f'<a href="{text(pdf_link(path, output))}" target="_blank" rel="noopener">Apri {text(path.name)}</a>')
    body = f'<section id="{text(cid)}"><h2>{text(cid)} · {text(case["variant"].replace("_", " "))}</h2><p>' + ' · '.join(links) + '</p>'
    for scenario, title in [('S-01', 'Mutuo'), ('S-02', 'Fiscalità')]:
        rows = []
        for key, fact in case['facts'].items():
            if fact['scenario'] == scenario:
                rows.append((FIELDS[key][0], STATES[fact['status']], display_value(fact),
                             UNITS[fact['unit']], fact['period'], source_fragments(pages[scenario], key)))
        outcome = case['expected_activities'][scenario]
        reason = 'attività completabile con fonte simulata'
        if outcome == 'blocked':
            reason = 'attività bloccata: ' + ', '.join(FIELDS[k][0] + ' ' + STATES[f['status']].lower()
                for k, f in case['facts'].items() if f['scenario'] == scenario and f['status'] in {'missing', 'ambiguous'})
        body += '<h3>' + text(scenario + ' · ' + title) + '</h3><p><strong>Esito atteso:</strong> ' + text(reason) + '</p>'
        body += table(['Campo', 'Stato annotato', 'Valore nel riferimento', 'Unità', 'Periodo', 'Riscontro testuale da controllare nel PDF'], rows)
    if case['facts']['annual_rate']['status'] == 'ambiguous':
        body += '<p class="notice">I due tassi nel PDF non autorizzano a sceglierne uno: il TAN utilizzabile resta assente.</p>'
    contract_period = case['facts']['annual_rate']['period']
    tax_period = case['facts']['tax_year']['period']
    body += '<p>Periodo del contratto: ' + text(contract_period) + '; periodo fiscale: ' + text(tax_period) + '. '
    body += 'Date diverse riguardano due domini distinti: non costituiscono da sole un conflitto.</p>'
    body += '<h3>Calcoli attesi · derivati, non letti nei PDF</h3><p>Modello a rate mensili costanti, capitale e durata documentali. Totali da rata non arrotondata; arrotondamento finale al centesimo. Costi esclusi. La rata documentata resta distinta dal modello.</p>'
    calculations = case['expected_calculations']
    rows = []
    for key, label in [('contract', 'Scenario con TAN documentale'), ('alternative_fixture', 'Scenario con tasso della fixture simulata')]:
        if key in calculations:
            v = calculations[key]
            rate = case['facts']['annual_rate']['value'] if key == 'contract' else FIXTURE_RATES[case['facts']['rate_type']['value']]
            label += ' (' + rate + '% annuo)'
            rows.append((label, v['monthly_payment'], v['total_payments'], v['remaining_interest']))
    body += table(['Scenario teorico', 'Rata EUR', 'Totale rate EUR', 'Interessi residui EUR'], rows) if rows else '<p>Nessun calcolo del mutuo: input obbligatorio mancante o ambiguo.</p>'
    if 'hypothetical_interest_share' in calculations:
        facts = case['facts']
        body += '<p>Ripartizione ipotetica: ' + text(facts['annual_interest']['value'] + ' EUR × ' + facts['ownership_share']['value'] + ' = ' + calculations['hypothetical_interest_share'] + ' EUR') + '. Non è una detrazione o un importo personale documentato.</p>'
    else:
        body += '<p>Nessuna ripartizione fiscale calcolabile: interessi annui mancanti.</p>'
    body += '<h3>Fatti necessari allo specialista</h3><ul>'
    for scenario, facts in case['agent_utility_facts'].items():
        if facts is None:
            description = 'utilità non applicabile: attività bloccata correttamente.'
        else:
            parts = []
            for fact in facts:
                value = fact['value']
                if fact['field'] == 'remaining_years_band':
                    parts.append(f'Durata: oltre {value["lower_exclusive"]} e fino a {value["upper_inclusive"]} anni inclusi (o durata esatta equivalente). Richiesta dal contratto del compito; non usata dalla fixture.')
                else:
                    parts.append(FIELDS[fact['field']][0] + ': ' + str(VALUES.get(value, value)))
            description = '; '.join(parts)
        body += '<li>' + text(scenario + ': ' + description) + '</li>'
    body += '</ul><p>Importi esatti necessari ai calcoli restano locali: la loro assenza dalle viste degli agenti non è perdita di utilità. Tipologia non specificata esclusa dal denominatore.</p>'
    body += '<h3>Limiti attesi da controllare</h3><ul>' + ''.join('<li>' + text(LIMITS[x]) + '</li>' for x in case['required_report_limits']) + '</ul>'
    body += '<p class="notice"><strong>Controllo umano del riferimento.</strong> Verificare valori, unità, periodi e stati sui PDF aperti, poi esiti attesi, ipotesi e fatti necessari al compito. Segnalare ogni discordanza; l’assenza di un’etichetta da sola non prova l’assenza dell’informazione. Lo stato delle conferme è nel protocollo, non viene assegnato dalla scheda.</p></section>'
    return body


def render(annotation_path, case_ids, directory, output):
    raw = annotation_path.read_bytes()
    annotation = json.loads(raw)
    indexed = {case['case_id']: case for case in annotation['cases']}
    if not case_ids or len(set(case_ids)) != len(case_ids) or any(cid not in indexed for cid in case_ids):
        raise ValueError('Selezionare fascicoli esistenti e senza duplicati')
    # Controlla tutti i PDF del fascicolo, anche quelli non usati da S-01/S-02.
    for cid in case_ids:
        for name, digest in indexed[cid]['pdf_sha256'].items():
            if Path(name).name != name or not name.startswith(cid + '_'):
                raise ValueError('Nome PDF fuori catalogo')
            if hashlib.sha256((directory / name).read_bytes()).hexdigest() != digest:
                raise ValueError('PDF cambiato rispetto al riferimento: ' + name)
    digest = hashlib.sha256(raw).hexdigest()
    body = '<h1>Revisione delle annotazioni</h1><p class="notice">Materiale del valutatore. Nessun modello o servizio viene chiamato. La scheda non è un report utente o un giudizio di qualità e non sostituisce la revisione umana.</p><p>Aprire i due PDF di ogni fascicolo e confrontarli con questa scheda. Gli estratti sono selezionati automaticamente; per assenze, ambiguità e contesto leggere anche il documento completo. Conto e busta paga non alimentano questi scenari.</p>'
    body += '<p>Versione: ' + text(annotation['annotation_version']) + ' · Stato: ' + text(annotation['status']) + '</p><p class="digest">SHA-256 delle annotazioni: ' + digest + '</p>'
    body += '<nav>' + ' · '.join(f'<a href="#{text(cid)}">{text(cid)}</a>' for cid in case_ids) + '</nav>'
    body += ''.join(review_case(indexed[cid], directory, output) for cid in case_ids)
    body += '<footer>La scheda non salva conferme. Comunicare i casi controllati e le eventuali correzioni: solo dopo una conferma esplicita verrà registrata la revisione del riferimento. Campagna finale e S04 non avviati.</footer>'
    return '<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'"><title>Revisione annotazioni</title><style>body{font:16px/1.5 system-ui,sans-serif;max-width:1200px;margin:32px auto;padding:0 20px;color:#162636;background:#f7f9fb}h1,h2,h3{line-height:1.2}h2{color:#123e65}section{background:white;border:1px solid #c8d5df;padding:24px;margin:24px 0;border-radius:10px}a{color:#12538a}nav{padding:12px;background:#e8f0f6}.notice{background:#fff4d6;padding:14px;border-left:4px solid #aa7710}.table{overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;vertical-align:top;border:1px solid #cad6df;padding:9px;min-width:90px}th{background:#edf3f8}td:last-child{min-width:210px}.digest{font:12px monospace;overflow-wrap:anywhere}footer{padding:20px 0}@media print{body{background:white;margin:0;padding:0;font-size:11px}section{border:0;padding:0;break-before:page}nav{display:none}th,td{min-width:0;padding:5px;font-size:10px}td:last-child{min-width:0}.table{overflow:visible}tr{break-inside:avoid}}</style></head><body>' + body + '</body></html>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--cases', nargs='+')
    selection.add_argument('--all', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'runs/annotation_review_first5.html')
    args = parser.parse_args()
    ids = [f'C{i:03}' for i in range(1, 26)] if args.all else args.cases or FIRST_CASES
    output = args.output.resolve()
    if output.suffix.lower() != '.html':
        parser.error('Usare un file di uscita .html')
    try:
        if output.exists():
            raise ValueError('File già presente: scegliere un nuovo nome per conservare la scheda precedente')
        result = render(ROOT / 'evaluation/annotations.json', ids, ROOT / 'dataset/Documents', output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('x', encoding='utf-8') as stream:
            stream.write(result)
    except (ValueError, OSError, KeyError) as error:
        parser.error(str(error))
    print('Fascicoli:', ' '.join(ids))
    print('Scheda creata:', output.name)
    print('Consultare il protocollo per le conferme umane. Nessuna annotazione approvata automaticamente.')


if __name__ == '__main__':
    main()
