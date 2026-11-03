"""Presentazione locale del JSON verificabile: nessuna inferenza o nuovo calcolo."""
from html import escape

LABELS = {
    'mortgage_type': 'Tipologia del mutuo', 'rate_type': 'Tipo di tasso',
    'remaining_principal': 'Capitale residuo', 'remaining_months': 'Durata residua',
    'annual_rate': 'Tasso annuo contrattuale', 'payment_amount': 'Rata documentata',
    'payment_frequency': 'Periodicità della rata', 'tax_year': 'Anno d’imposta',
    'purpose': 'Finalità dichiarata', 'annual_interest': 'Interessi annui documentati',
    'ownership_share': 'Quota di intestazione',
    'payslip_net': 'Netto della busta paga', 'account_opening_balance': 'Saldo iniziale del conto',
    'account_closing_balance': 'Saldo finale del conto',
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
REASONS = {'invalid_view':'La vista prodotta dalla policy non contiene i dati richiesti: attività bloccata.','incompatible_market_measure': 'Il riferimento BCE AAR/NDER è aggregato, non un TAN o un’offerta: non viene usato per calcolare una rata alternativa.','input_not_ready': 'Dati obbligatori mancanti, ambigui o non validati.',
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


def report_alerts(report):
    """Indicazioni di lettura derivate dal JSON, senza nuovi calcoli finanziari."""
    alerts=[]
    if (report.get('consistency') or {}).get('unresolved_conflicts',0):
        alerts.append(('error','Conflitto da risolvere',['Valori discordanti conservati con entrambe le provenienze. Nessun valore documentale è stato sostituito. Le conclusioni applicative sono sospese.']))
    for section in report.get('completeness',[]):
        domain='Mutuo' if section.get('scenario')=='S-01' else 'Interessi e fiscalità'
        required=list(dict.fromkeys(section.get('missing_required',[])+section.get('ambiguous_or_unvalidated',[])))
        details=[]
        if required:details.append('Dati obbligatori mancanti o non validati: '+', '.join(LABELS.get(n,n) for n in required)+'.')
        details.extend(dict.fromkeys(item['reason'] for item in section.get('validation_issues',[])))
        if details:alerts.append(('error',domain+' — dati non utilizzabili',details))
        optional=section.get('optional_not_specified',[])
        if optional:alerts.append(('warning',domain+' — limite di contesto',['Non specificato: '+', '.join(LABELS.get(n,n) for n in optional)+'. Nessuna categoria è stata inventata.']))
        missing_span=section.get('without_document_span',[])
        if missing_span:alerts.append(('warning',domain+' — provenienza documentale incompleta',['Campi senza citazione del PDF: '+', '.join(LABELS.get(n,n) for n in missing_span)+'.']))
    for item in report.get('outcomes',[]):
        if item.get('status')!='completed':
            domain='Mutuo' if item.get('scenario')=='S-01' else 'Interessi e fiscalità'
            alerts.append(('error',domain+' — '+STATUSES.get(item.get('status'),'Non completato'),[REASONS.get(item.get('error_code'),item.get('interpretation') or 'Nessuna conclusione verificata da questa attività.')]))
    if report.get('simulated_sources'):alerts.append(('warning','Fonti simulate',['I riferimenti di test non sono quotazioni o norme reali. Le eventuali fonti istituzionali sono indicate separatamente.']))
    excluded=[a for a in report.get('model_analyses',[]) if a.get('status')!='available']
    if excluded:alerts.append(('warning','Contributi dei modelli con limiti',['Commenti assenti o esclusi restano distinti dalle eventuali selezioni valide. Non viene generata una spiegazione sostitutiva.']))
    return alerts


def render_report_document(report):
    parts = ['<article class="report-document">', '<h2>' + text(report.get('title', 'Report locale')) + '</h2>']
    def paragraph(content,tone=None):
        parts.append('<p'+(' class="report-alert tone-'+tone+'"' if tone else '')+'>' + text(content) + '</p>')
    def heading(content):
        parts.append('<h3>' + text(content) + '</h3>')
    def listing(items):
        if items:
            parts.append('<ul>' + ''.join('<li>' + text(item) + '</li>' for item in items) + '</ul>')
    def table(headers, rows, tones=None):
        parts.append('<div class="table-wrap"><table><thead><tr>' + ''.join('<th scope="col">' + text(h) + '</th>' for h in headers) + '</tr></thead><tbody>')
        for index,row in enumerate(rows):
            tone=tones[index] if tones else None
            parts.append('<tr'+(' class="tone-'+tone+'"' if tone else '')+'>' + ''.join('<td>' + text(cell) + '</td>' for cell in row) + '</tr>')
        parts.append('</tbody></table></div>')
    paragraph('Esito dell’analisi: ' + STATUSES.get(report.get('status'), str(report.get('status', 'Non disponibile'))))
    if report.get('external_sources'):
        paragraph('Documenti del dataset sintetico. Le fonti istituzionali recuperate e le eventuali fonti simulate sono distinte nelle citazioni. Nessuna offerta personale o spettanza fiscale attestata.')
    else:
        paragraph('Dati del dataset sintetico. Le fonti di questa versione sono simulate o non disponibili: questo documento non verifica offerte di mercato o normative reali.')
    paragraph('Perimetro: PDF nativi dei template sintetici; nessun OCR. Conto e busta paga forniscono un contesto mensile facoltativo, senza accertare reddito stabile, sostenibilità o diritti fiscali. La validazione non certifica l’autenticità dei documenti.')
    parts.append('<ul class="report-legend"><li>Dati documentali con provenienza</li><li>Fonti istituzionali o simulate</li><li>Calcoli locali con ipotesi</li><li>Selezioni e commenti LLM separati</li></ul>')
    for tone,title,details in report_alerts(report):
        parts.append('<div class="report-alert tone-'+tone+'" role="note"><p><strong>'+('! ' if tone=='error' else 'Nota — ')+text(title)+'</strong></p>')
        listing(details)
        parts.append('</div>')
    if report.get('status')=='completed':
        paragraph('Completamento tecnico delle attività, non garanzia di convenienza, spettanza fiscale o correttezza semantica dei commenti del modello.','info')
    elif report.get('status')=='partial':
        paragraph('Il risultato è parziale: i dati e gli approfondimenti utilizzabili sono conservati, con le attività non completate indicate sotto.','warning')
    heading('1. Attività e risultati disponibili')
    table(['Attività', 'Esito', 'Indicazione'], [
        ['Mutuo' if item.get('scenario') == 'S-01' else 'Interessi e fiscalità',
         STATUSES.get(item.get('status'), item.get('status', 'Non disponibile')),
         REASONS.get(item.get('error_code'), item.get('interpretation', ''))]
        for item in report.get('outcomes', [])],tones=['error' if item.get('status')!='completed' else None for item in report.get('outcomes',[])])
    heading('2. Dati documentali e provenienza')
    sections = list(report.get('document_data', []))
    context = report.get('financial_context')
    if context:
        sections.append({'scenario': 'CONTEXT', 'facts': context['facts']})
    for section in sections:
        optional_context = section.get('scenario') == 'CONTEXT'
        paragraph('Conto e busta paga — contesto facoltativo' if optional_context else 'Mutuo' if section.get('scenario') == 'S-01' else 'Interessi e fiscalità')
        rows = [];row_tones=[]
        for name, fact in section.get('facts', {}).items():
            source = fact.get('source') or {}
            reference = (str(source.get('document_id', '')) + ', pagina ' + str(source.get('page', ''))
                         if source else 'Nessuna citazione disponibile')
            if fact.get('provenance_status') != 'text_span_available' and source:
                reference += ' — collegamento al PDF non verificato'
            quote = source.get('quote')
            if quote is not None:
                reference += ' — «' + str(quote) + '»'
            problematic=(fact.get('status') in {'missing','ambiguous','unvalidated'} or bool(fact.get('validation_issues'))) and not optional_context
            optional=fact.get('status')=='not_specified' or (optional_context and (fact.get('status') in {'missing','ambiguous','unvalidated'} or bool(fact.get('validation_issues'))))
            row_tones.append('error' if problematic else 'warning' if optional else None)
            rows.append([('! ' if problematic else '')+LABELS.get(name, name), value(fact), str(fact.get('period', '—'))[:7] if fact.get('period_granularity')=='month' else fact.get('period', '—'), reference])
        table(['Informazione', 'Valore', 'Periodo', 'Documento e citazione'], rows, tones=row_tones)
    if context:
        listing(context['limits'])
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
    review=report.get('tax_review')
    if review:
        heading('Approfondimenti fiscali e condizioni non accertate')
        if review.get('status')=='conditions_identified':
            paragraph(review.get('candidate_scope',''))
            for condition in review.get('conditions',[]):
                heading(condition['title'])
                paragraph('Da verificare; applicabilità al caso non accertata. '+condition['question'])
                listing(condition.get('needed_information',[]))
                source=condition['source']
                paragraph('Istruzioni 730/'+str(source['publication_year'])+', anno d’imposta '+str(source['tax_year'])+', pagina '+str(source['page'])+': «'+source['quote']+'»')
                from .tax_publications import PUBLICATIONS
                allowed={p['source_url'] for p in PUBLICATIONS.values()}
                page=source.get('page')
                url=source.get('source_url')
                if url in allowed and type(page) is int and 1<=page<=175 and source.get('source_ref')==url+'#page='+str(page):
                    parts.append('<p><a href="'+text(source['source_ref'])+'" target="_blank" rel="noopener noreferrer">Consulta la pagina della pubblicazione</a></p>')
        else:
            paragraph('Condizioni non valutate. '+REASONS.get(review.get('reason'),'Fonte istituzionale utilizzabile non disponibile per questo riepilogo.'))
        paragraph(review['conclusion'])
        listing(review.get('limits',[]))
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
    for generated in report.get('model_analyses', []):
        heading('Condizioni fiscali messe in evidenza dall’agente' if generated.get('scenario')=='S-02' else 'Enunciati messi in evidenza dall’agente mercati')
        paragraph(generated.get('warning', 'Pertinenza della selezione e commento non verificati semanticamente.'))
        if generated.get('status') not in {'available', 'selection_only'}:
            paragraph('Selezione non disponibile o esclusa; nessuna spiegazione sostitutiva generata.')
            continue
        paragraph('I testi sono ricostruiti dal catalogo e dalla vista autorizzata dopo la scelta del modello; non sono citazioni letterali della pubblicazione.')
        for kind, label in [('source', 'Sulla fonte'), ('context', 'Sul contesto ricevuto')]:
            paragraph(label)
            listing(item['text'] + ' [Riferimenti: ' + ', '.join(item['references']) + ']'
                    for item in generated.get('selected_statements', []) if item['kind'] == kind)
        if generated.get('scenario')=='S-02':
            paragraph('Tutte le condizioni restano da verificare. La scelta del modello non prova requisiti soddisfatti o diritto a una detrazione.')
            for item in generated.get('selected_statements',[]):
                source=item.get('source') or {}
                if source.get('simulated') is False:
                    paragraph('Estratto della pubblicazione: «'+str(source.get('quote',''))+'» — pagina '+str(source.get('page',''))+', anno d’imposta '+str(source.get('tax_year','')))
                    paragraph('Fonte: '+str(source.get('source_ref','')))
                listing(item.get('needed_information',[]))
        paragraph('Breve spiegazione del modello — non verificata semanticamente','warning')
        explanation = (generated.get('content') or {}).get('explanation')
        if generated.get('status') == 'available' and explanation:
            paragraph(explanation)
        else:
            paragraph('Commento escluso dai controlli; selezione valida conservata, senza un commento sostitutivo.')
        table(['Riferimento', 'Valore nella fonte o nella vista autorizzata'],
              [[ref, raw if raw is not None else 'Non specificato nella vista autorizzata']
               for ref, raw in generated.get('references', {}).items()])
        paragraph('La selezione e il commento non alimentano i calcoli e non determinano conclusioni finanziarie verificate.')
    for reference in report.get('comparison_references',[]):
        paragraph('Riferimento comune letto tramite MCP — '+reference['scenario'])
        evidence=reference['evidence']
        paragraph('Replay di una risposta istituzionale archiviata; nessun nuovo recupero Internet.' if evidence['origin']=='recorded_official_response_replay' else 'Ricevuta controfattuale interamente simulata; valore non attribuito alla BCE.')
        paragraph('Fonte: '+evidence['source_id']+'; periodo: '+evidence['period']+'; valore: '+evidence['value']+' '+evidence['unit'])
        paragraph(reference['usage_limit'])
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
            paragraph('! Conflitto segnalato: nessun valore è stato sostituito automaticamente.','error')
            for side in ('left', 'right'):
                item = pair.get(side) or {}
                paragraph('Grandezza: '+str(item.get('quantity',''))+'; prodotto: '+str(item.get('product',''))+'; valore originale: '+str(item.get('value', '')) + ' ' + str(item.get('unit', '')) + ' — periodo: ' + str(item.get('period', 'Non disponibile')) + ' — fonte: ' + str(item.get('source_ref', 'Non disponibile')))
    paragraph(consistency.get('scope', 'Copertura limitata ai dati previsti dagli scenari richiesti.'))
    heading('7. Limiti e conclusioni')
    listing(report.get('limits', []))
    paragraph('I risultati sostengono soltanto gli approfondimenti descritti, nelle ipotesi dichiarate. L’eventuale interpretazione LLM è separata e non verificata semanticamente; le altre sintesi libere sono escluse.')
    parts.append('</article>')
    return ''.join(parts)
