"""Presentazione locale del JSON verificabile: nessuna inferenza o nuovo calcolo."""
from html import escape

LABELS = {
    'mortgage_type': 'Tipologia del mutuo', 'rate_type': 'Tipo di tasso',
    'remaining_principal': 'Capitale residuo', 'remaining_months': 'Durata residua',
    'annual_rate': 'Tasso annuo contrattuale', 'payment_amount': 'Rata documentata',
    'payment_frequency': 'Periodicità della rata', 'tax_year': 'Anno d’imposta',
    'purpose': 'Finalità dichiarata', 'annual_interest': 'Interessi annui documentati',
    'ownership_share': 'Quota di intestazione',
}
CATEGORIES = {
    'fixed': 'Fisso', 'variable': 'Variabile', 'mixed': 'Misto', 'monthly': 'Mensile',
    'quarterly': 'Trimestrale', 'semiannual': 'Semestrale', 'annual': 'Annuale',
    'primary_home_purchase': 'Acquisto abitazione principale',
    'primary_home_construction': 'Costruzione abitazione principale',
    'renovation': 'Ristrutturazione', 'other': 'Altro, come dichiarato',
    'residential': 'Residenziale',
}
COMPARISON_REASONS = {'incompatible_market_measure': 'Il riferimento BCE AAR/NDER è aggregato, non un TAN o un’offerta: non viene usato per calcolare una rata alternativa.','quantity_mismatch': 'grandezze differenti', 'product_mismatch': 'prodotti differenti',
    'period_mismatch': 'periodi differenti', 'unverified_observation': 'provenienza non verificata',
    'unknown_quantity': 'grandezza non supportata', 'unsupported_unit': 'unità non convertibile',
    'invalid_numeric_value': 'valore numerico non utilizzabile'}
STATUSES = {'completed': 'Completato', 'partial': 'Parziale', 'blocked': 'Non eseguito',
            'failed': 'Non completato', 'unverified': 'Non verificato'}
REASONS = {'incompatible_market_measure': 'Il riferimento BCE AAR/NDER è aggregato, non un TAN o un’offerta: non viene usato per calcolare una rata alternativa.','input_not_ready': 'Dati obbligatori mancanti, ambigui o non validati.',
           'timeout': 'Tempo massimo superato.', 'missing_provenance': 'Provenienza obbligatoria assente.',
           'not_authorized': 'Richiesta non autorizzata dal gateway.',
           'market_evidence_unavailable': 'Fonte mercati non disponibile o non utilizzabile.',
           'tax_evidence_unavailable': 'Fonte fiscale non disponibile o non utilizzabile.',
           'unsupported_payment_frequency': 'Periodicità non supportata dal modello di calcolo.',
           'unresolved_conflict': 'Conflitto tra valori ancora da risolvere.'}


def text(value):
    return escape(str(value), quote=True)


def number(value):
    """Separatore italiano, senza convertire in float o alterare i decimali."""
    raw = str(value)
    import re
    if not re.fullmatch(r'-?\d+(?:\.\d+)?', raw):
        return raw
    sign = '-' if raw.startswith('-') else ''
    integer, separator, fraction = raw.lstrip('-').partition('.')
    # Raggruppamento da destra mantenendo l’ordine delle cifre.
    chunks = []
    while integer:
        chunks.insert(0, integer[-3:])
        integer = integer[:-3]
    return sign + '.'.join(chunks) + (',' + fraction if separator else '')


def value(fact):
    status = fact.get('status')
    if status in {'missing', 'not_specified'}:
        return 'Non documentato' if status == 'missing' else 'Non specificato'
    raw = fact.get('value')
    if raw is None:
        return 'Non disponibile'
    unit = fact.get('unit')
    result = CATEGORIES.get(str(raw), str(raw)) if unit == 'category' else str(raw) if unit == 'year' else number(raw)
    suffix = {'EUR': ' €', 'month': ' mesi', 'percent_per_year': ' % annuo',
              'fraction': ' (quota frazionaria)'}.get(unit, '')
    if status in {'ambiguous', 'unvalidated'}:
        result += ' — ambiguo o non validato; non utilizzabile nei calcoli'
    return result + suffix


def render_report_document(report):
    parts = ['<article class="report-document">', '<h2>' + text(report.get('title', 'Report locale')) + '</h2>']
    def paragraph(content):
        parts.append('<p>' + text(content) + '</p>')
    def heading(content):
        parts.append('<h3>' + text(content) + '</h3>')
    def listing(items):
        if items:
            parts.append('<ul>' + ''.join('<li>' + text(item) + '</li>' for item in items) + '</ul>')
    def table(headers, rows):
        parts.append('<table><thead><tr>' + ''.join('<th scope="col">' + text(h) + '</th>' for h in headers) + '</tr></thead><tbody>')
        for row in rows:
            parts.append('<tr>' + ''.join('<td>' + text(cell) + '</td>' for cell in row) + '</tr>')
        parts.append('</tbody></table>')
    paragraph('Esito dell’analisi: ' + STATUSES.get(report.get('status'), str(report.get('status', 'Non disponibile'))))
    if report.get('external_sources'):
        paragraph('Documenti del dataset sintetico. Le fonti istituzionali recuperate e le eventuali fonti simulate sono distinte nelle citazioni. Nessuna offerta personale o spettanza fiscale attestata.')
    else:
        paragraph('Dati del dataset sintetico. Le fonti di questa versione sono simulate o non disponibili: questo documento non verifica offerte di mercato o normative reali.')
    heading('1. Attività e risultati disponibili')
    table(['Attività', 'Esito', 'Indicazione'], [
        ['Mutuo' if item.get('scenario') == 'S-01' else 'Interessi e fiscalità',
         STATUSES.get(item.get('status'), item.get('status', 'Non disponibile')),
         REASONS.get(item.get('error_code'), item.get('interpretation', ''))]
        for item in report.get('outcomes', [])])
    heading('2. Dati documentali e provenienza')
    for section in report.get('document_data', []):
        paragraph('Mutuo' if section.get('scenario') == 'S-01' else 'Interessi e fiscalità')
        rows = []
        for name, fact in section.get('facts', {}).items():
            source = fact.get('source') or {}
            reference = (str(source.get('document_id', '')) + ', pagina ' + str(source.get('page', ''))
                         if source else 'Nessuna citazione disponibile')
            if fact.get('provenance_status') != 'text_span_available' and source:
                reference += ' — collegamento al PDF non verificato'
            quote = source.get('quote')
            if quote is not None:
                reference += ' — «' + str(quote) + '»'
            rows.append([LABELS.get(name, name), value(fact), fact.get('period', '—'), reference])
        table(['Informazione', 'Valore', 'Periodo', 'Documento e citazione'], rows)
    contract = report.get('mortgage_contract_analysis')
    if contract:
        heading('3. Analisi locale del contratto e confronto orientativo')
        if contract.get('status') == 'calculated':
            paragraph('Modello teorico sui dati del contratto. Questo calcolo non utilizza il tasso BCE o un’offerta alternativa.')
            current=contract.get('contract_rate_scenario', {})
            table(['Indicatore', 'Modello al TAN documentale'], [
                [label,number(current[key])+unit] for key,label,unit in (
                    ('annual_rate_percent','TAN documentale',' %'),
                    ('theoretical_monthly_payment','Rata mensile teorica',' €'),
                    ('theoretical_total_interest','Interessi residui teorici',' €'),
                    ('theoretical_total_payments','Totale pagamenti teorico',' €')) if key in current])
            paragraph('Rata mensile documentata: '+number(contract['documented_monthly_payment'])+' €.')
            gap=contract['documented_vs_model']
            paragraph('Scostamento rata documentata − rata teorica: '+number(gap['difference_documented_minus_model'])+' €. '+gap['interpretation'])
        else:
            paragraph('Analisi locale non calcolata. '+REASONS.get(contract.get('reason'),'Dati o condizioni non sufficienti.'))
        listing(contract.get('assumptions',[]))
        listing(contract.get('limits',[]))
    mortgage = report.get('mortgage_comparison')
    if mortgage:
        heading('Confronto con un tasso alternativo' if contract else '3. Confronto orientativo del mutuo')
        if mortgage.get('status') == 'calculated':
            paragraph('Scenari matematici a parità di capitale e durata residui. Il tasso alternativo è simulato; la differenza non è un risparmio garantito.')
            current = mortgage.get('contract_rate_scenario', {})
            alternative = mortgage.get('simulated_rate_scenario', {})
            rows = []
            for key, label, unit in [('annual_rate_percent', 'Tasso annuo', ' %'),
                                     ('theoretical_monthly_payment', 'Rata mensile teorica', ' €'),
                                     ('theoretical_total_interest', 'Interessi residui teorici', ' €'),
                                     ('theoretical_total_payments', 'Totale pagamenti teorico', ' €')]:
                rows.append([label, number(current[key]) + unit if key in current else 'Non disponibile',
                             number(alternative[key]) + unit if key in alternative else 'Non disponibile'])
            table(['Indicatore', 'Scenario al tasso contrattuale', 'Scenario al tasso simulato'], rows)
            if 'documented_monthly_payment' in mortgage:
                paragraph('Rata mensile del documento, mantenuta distinta dal modello: ' + number(mortgage['documented_monthly_payment']) + ' €.')
            differences = mortgage.get('difference_contract_minus_simulated', {})
            if 'monthly_payment' in differences:
                paragraph('Differenza rata contrattuale teorica − rata simulata: ' + number(differences['monthly_payment']) + ' € al mese.')
                paragraph(differences.get('sign_convention', ''))
        else:
            paragraph('Confronto non calcolato. ' + REASONS.get(mortgage.get('reason'), 'Dati o condizioni non sufficienti; consultare gli esiti.'))
            if not contract and 'documented_monthly_payment' in mortgage:
                paragraph('Rata documentata, mantenuta distinta dal riferimento BCE: '+number(mortgage['documented_monthly_payment'])+' €.')
        listing(mortgage.get('assumptions', []))
        listing(mortgage.get('limits', []))
        if mortgage.get('status')!='calculated':
            paragraph('Per approfondire una rinegoziazione occorrono un’offerta riferita al caso, con TAN, durata e costi documentati e confrontabili. Il dato statistico non li sostituisce.')
    tax = report.get('tax_application')
    if tax:
        heading('4. Interessi e aspetti fiscali da approfondire')
        paragraph('Nessuna detrazione o spettanza fiscale è stata determinata.')
        if tax.get('status') == 'calculated':
            context = tax.get('documentary_context', {})
            table(['Dato documentale', 'Valore'], [[label, (str(context[key]) if key=='tax_year' else number(context[key])) + suffix] for key, label, suffix in (
                ('tax_year', 'Anno d’imposta', ''), ('annual_interest_EUR', 'Interessi annui', ' €'),
                ('ownership_share', 'Quota frazionaria', '')) if key in context])
            allocation = tax.get('hypothetical_allocation', {})
            if 'amount_EUR' in allocation:
                paragraph('Ripartizione esclusivamente ipotetica (interessi × quota): ' + number(allocation['amount_EUR']) + ' €. Non è un importo personale attestato dal documento né un importo detraibile.')
        else:
            paragraph('Ripartizione non calcolata. ' + REASONS.get(tax.get('reason'), 'Dati o condizioni non sufficienti; consultare gli esiti.'))
        listing(tax.get('assumptions', []))
        listing(item.get('text', '') for item in tax.get('conditions_to_verify', []))
        listing(tax.get('limits', []))
    heading('5. Fonti consultate e contenuti verificati')
    sources = report.get('simulated_sources', []) + report.get('external_sources', [])
    if not sources:
        paragraph('Nessuna fonte utilizzabile disponibile per gli scenari richiesti.')
    for source in sources:
        evidence = source.get('evidence') or {}
        if evidence.get('source_id')=='ade-annual-mortgage-v1':
            paragraph('Agenzia delle Entrate — istruzioni 730/'+str(evidence.get('publication_year'))+' per anno d’imposta '+str(evidence.get('tax_year'))+'. Edizione verificata, non valutazione della spettanza personale.')
            paragraph('Recuperato: '+str(evidence.get('retrieved_at','')))
            from .tax_publications import PUBLICATIONS
            url=evidence.get('source_url','')
            if url in {p['source_url'] for p in PUBLICATIONS.values()}:
                parts.append('<p>Pubblicazione: <a href="'+text(url)+'" target="_blank" rel="noopener noreferrer">'+text(url)+'</a></p>')
        elif evidence.get('simulated') is False:
            paragraph('BCE / Eurosistema — statistica istituzionale recuperata via HTTPS e controllata dal gateway. Non è un’offerta personalizzata.')
            paragraph('Serie: '+str(evidence.get('series_key','')))
            paragraph('Valore: '+number(evidence.get('annual_rate_percent',''))+' % annuo AAR/NDER; mese osservato: '+str(evidence.get('observation_period','')))
            paragraph('Recuperato: '+str(evidence.get('retrieved_at',''))+'; ultimo dato restituito dalla fonte, non aggiornamento continuo.')
            from .ecb_source import SOURCE_URL, PORTAL_URL
            for label,key in (('Scheda della serie','portal_url'),('Dati consultati','source_url')):
                url=evidence.get(key,'')
                if url in {SOURCE_URL,PORTAL_URL}:
                    parts.append('<p>'+text(label)+': <a href="'+text(url)+'" target="_blank" rel="noopener noreferrer">'+text(url)+'</a></p>')
                else:
                    paragraph(label+': '+str(url))
        else:
            paragraph(str(evidence.get('source_id', 'Fonte senza identificativo')) + ' — fonte simulata; fedeltà al catalogo di test, non verifica del mondo reale.')
        if 'reference_date' in evidence:
            paragraph('Periodo di riferimento della fonte: ' + str(evidence['reference_date']))
        if 'reference' in evidence:
            paragraph('Riferimento di test: ' + str(evidence['reference']))
    for summary in report.get('faithful_summaries', []):
        listing(str(item.get('text', '')) + ' [Fonte: ' + str(item.get('source_ref', 'Non disponibile')) + ']'
                for item in summary.get('statements', []))
    if not report.get('faithful_summaries'):
        paragraph('Nessuna sintesi con provenienza verificata disponibile.')
    heading('6. Completezza e confronti')
    for section in report.get('completeness', []):
        for key, description in [('missing_required', 'Campi obbligatori mancanti'),
                                 ('ambiguous_or_unvalidated', 'Campi ambigui o non validati'),
                                 ('optional_not_specified', 'Informazioni facoltative non specificate'),
                                 ('without_document_span', 'Campi senza citazione documentale')]:
            fields = section.get(key, [])
            if fields:
                paragraph(str(section.get('scenario', '')) + ' — ' + description + ': ' + ', '.join(LABELS.get(name, name) for name in fields))
        listing(LABELS.get(item.get('field'), 'Periodo' if item.get('field')=='period' else str(item.get('field', ''))) + ': ' + str(item.get('reason', '')) for item in section.get('validation_issues', []))
    consistency = report.get('consistency') or {}
    for pair in consistency.get('comparisons', []):
        if pair.get('status') == 'not_comparable':
            paragraph('Valori non confrontabili come fatto identico: ' + COMPARISON_REASONS.get(pair.get('reason'), 'grandezza, prodotto o periodo diverso') + '. Questo non costituisce di per sé un conflitto.')
        elif pair.get('status') == 'consistent':
            paragraph('Valori coerenti nelle osservazioni confrontabili, entro la tolleranza dichiarata nel JSON.')
        elif pair.get('status') == 'conflict':
            paragraph('Conflitto segnalato: nessun valore è stato sostituito automaticamente.')
            for side in ('left', 'right'):
                item = pair.get(side) or {}
                paragraph(str(item.get('value', '')) + ' ' + str(item.get('unit', '')) + ' — periodo: ' + str(item.get('period', 'Non disponibile')) + ' — fonte: ' + str(item.get('source_ref', 'Non disponibile')))
    paragraph(consistency.get('scope', 'Copertura limitata ai dati previsti dagli scenari richiesti.'))
    heading('7. Limiti e conclusioni')
    listing(report.get('limits', []))
    paragraph('I risultati sostengono soltanto gli approfondimenti descritti, nelle ipotesi dichiarate. Le sintesi libere dei modelli non verificate sono escluse dal documento.')
    parts.append('</article>')
    return ''.join(parts)
