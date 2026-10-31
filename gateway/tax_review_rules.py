"""Estratti delle edizioni AdE fissate: non checklist esaustiva o consulenza.
Spazi normalizzati dal testo pypdf; pagine PDF della pubblicazione.
"""
RULES = {
    "2024": {
        "paid_year": {
            "page": 58,
            "quote": "In questi righi vanno indicati gli importi degli interessi passivi, degli oneri accessori e delle quote di rivalutazione pagati nel 2024 per i mutui, a prescindere dalla scadenza della rata.",
            "title": "Pagamento e periodo d’imposta",
            "question": "Verificare i pagamenti effettivi e la loro riferibilità all’anno documentato.",
            "needed_information": [
                "Quietanze e pagamenti effettivi nell’anno d’imposta"
            ]
        },
        "own_share": {
            "page": 59,
            "quote": "Se il mutuo è intestato a più persone, ogni cointestatario può fruire della detrazione unicamente per la propria quota di interessi.",
            "title": "Quota degli interessi",
            "question": "Verificare a chi sono attribuiti gli interessi e se l’importo è già ripartito; la quota documentale non certifica la quota fiscalmente utilizzabile.",
            "needed_information": [
                "Intestatari del mutuo",
                "Attribuzione degli interessi e ripartizione già effettuata"
            ]
        },
        "purchase_purpose": {
            "page": 59,
            "quote": "Rigo E7 - Interessi per mutui ipotecari per l’acquisto dell’abitazione principale: indicare gli interessi passivi, gli oneri accessori e le quote di rivalutazione dipendenti da clausole di indicizzazione per mutui ipotecari contratti per l’acquisto di immobili adibiti ad abitazione principale.",
            "title": "Finalità e garanzia del mutuo",
            "question": "Verificare nel contratto la finalità di acquisto e la natura ipotecaria. La finalità dichiarata nel riepilogo non verifica tutti i requisiti.",
            "needed_information": [
                "Contratto e garanzia ipotecaria",
                "Finalità contrattuale"
            ]
        },
        "purchase_borrower": {
            "page": 59,
            "quote": "Per abitazione principale si intende quella nella quale il contribuente o i suoi familiari dimorano abitualmente. Pertanto, la detrazione spetta al contribuente acquirente e intestatario del contratto di mutuo, anche se l’immobile è adibito ad abitazione principale di un suo fa- miliare (coniuge, parenti entro il terzo grado e affini entro il secondo grado).",
            "title": "Acquirente, intestatario e abitazione principale",
            "question": "Verificare la posizione di acquirente e intestatario e l’uso dell’immobile come abitazione principale.",
            "needed_information": [
                "Titolo di acquisto e intestazione del mutuo",
                "Dimora abituale del contribuente o dei familiari"
            ]
        },
        "purchase_dates": {
            "page": 59,
            "quote": "La detrazione spetta a condizione che l’immobile sia adibito ad abitazione principale entro un anno dall’acquisto, e che l’acquisto sia avvenuto nell’anno antecedente o successivo al mutuo.",
            "title": "Date di acquisto, stipula e destinazione",
            "question": "Verificare le date e il regime applicabile al contratto, comprese le disposizioni per contratti meno recenti ed eventuali eccezioni: non si applica automaticamente il termine generale.",
            "needed_information": [
                "Date di acquisto e stipula",
                "Destinazione ad abitazione principale",
                "Eventuali condizioni particolari previste dalle istruzioni"
            ]
        },
        "loan_changes": {
            "page": 59,
            "quote": "In questi casi per data di stipula del mutu o è da in- tendersi la data di stipula del contratto di accollo/subentro/rinegoziazione/ del mutuo.",
            "title": "Data rilevante e modifiche del contratto",
            "question": "Verificare stipula ed eventuali accolli, subentri o rinegoziazioni prima di individuare il riferimento dichiarativo.",
            "needed_information": [
                "Data di stipula",
                "Eventuali accolli, subentri e rinegoziazioni"
            ]
        },
        "renovation_1997": {
            "page": 60,
            "quote": "La detrazione riguarda gli interessi passivi, gli oneri e le quote di rivalutazione dipendenti da clausole di indicizzazione pe r mutui (anche non ipotecari) contratti nel 1997 per effettuare interventi di manutenzione, restauro e ristrutturazione degli edifici.",
            "title": "Distinzione del caso storico del 1997",
            "question": "Verificare se si tratta del caso specifico dei mutui contratti nel 1997; non attribuire questo regime alla finalità generica ristrutturazione.",
            "needed_information": [
                "Anno e finalità del contratto",
                "Tipologia degli interventi"
            ]
        },
        "renovation_qualification": {
            "page": 131,
            "quote": "Per costruzione di unità immobiliare si intendono tutti gli interventi realizzati in conformità al provvedimento di abilitazione comunale che autorizzi una nuova costruzione, compresi gli interventi di ristrutturazione edilizia di cui all’art. 31, comma 1, lett. d), della L. 5 agosto 1978, n. 457.",
            "title": "Qualificazione edilizia dell’intervento",
            "question": "Per il possibile percorso costruzione/ristrutturazione dell’abitazione principale, verificare la qualificazione edilizia e i titoli abilitativi. Non ogni lavoro indicato come ristrutturazione rientra in questo percorso.",
            "needed_information": [
                "Provvedimento abilitativo",
                "Qualificazione edilizia degli interventi"
            ]
        },
        "renovation_dates": {
            "page": 131,
            "quote": "il mutuo deve essere stipulato non oltre sei mesi antecedenti, ovvero nei diciotto mesi successivi alla data di inizio dei lavori di costruzione; se invece si tratta di mutui stipulati in data antecedente al 1° dicembre 2007, i termini sono di sei mesi, antecedenti o successivi, alla data di inizio dei lavori di costruzione.",
            "title": "Rapporto temporale tra mutuo e lavori",
            "question": "Verificare date di stipula e inizio lavori e la disciplina temporale applicabile.",
            "needed_information": [
                "Data di stipula",
                "Data di inizio lavori",
                "Eventuali condizioni particolari o proroghe da approfondire"
            ]
        },
        "renovation_use": {
            "page": 131,
            "quote": "l’immobile deve essere adibito ad abitazione principale entro sei mesi dal termine dei lavori di costruzione;  il contratto di mutuo deve essere stipulato dal soggetto che avrà il pos - sesso dell’unità immobiliare a titolo di proprietà o di altro diritto reale;",
            "title": "Abitazione principale e titolarità",
            "question": "Nel possibile percorso costruzione/ristrutturazione dell’abitazione principale, verificare uso, termine dei lavori e titolarità; restano da esaminare le eccezioni della fonte.",
            "needed_information": [
                "Data di fine lavori e destinazione ad abitazione principale",
                "Proprietà o altro diritto reale del soggetto che stipula il mutuo"
            ]
        },
        "renovation_documents": {
            "page": 131,
            "quote": "Per fruire della detrazione occorre conservare, esibire o trasmettere, a ri - chiesta degli uffici finanziari, le quietanze di pagamento degli interessi passivi relativi al mutuo, la copia del contratto di mutuo ipotecario (dal quale risulti che lo stesso è assistito da ipoteca e che è stato stipulato per la costruzione dell’immobile da destinare ad abitazione principale), le abilitazioni ammini- strative richieste dalla vigente legislazione edilizia e le copie delle fatture o ricevute fiscali comprovanti le spese di costruzione dell’immobile stesso.",
            "title": "Documentazione di mutuo e lavori",
            "question": "Verificare contratto ipotecario, quietanze, autorizzazioni e spese effettive dei lavori; non sostituirli con il solo importo annuo del riepilogo.",
            "needed_information": [
                "Contratto ipotecario e quietanze",
                "Titoli abilitativi",
                "Fatture o ricevute dei lavori"
            ]
        },
        "renovation_loan_changes": {
            "page": 61,
            "quote": "In questi casi per data di stipula del mutuo è da intendersi la data di stipula del contrat to di accollo/subentro/rinegoziazione/ del mutuo.",
            "title": "Data rilevante e modifiche del contratto",
            "question": "Verificare stipula ed eventuali accolli, subentri o rinegoziazioni prima di individuare il riferimento dichiarativo.",
            "needed_information": [
                "Data di stipula",
                "Eventuali accolli, subentri e rinegoziazioni"
            ]
        }
    },
    "2025": {
        "paid_year": {
            "page": 61,
            "quote": "In questi righi vanno indicati gli importi degli interessi passivi, degli oneri accessori e delle quote di rivalutazione pagati nel 2025 per i mu- tui, a prescindere dalla scadenza della rata.",
            "title": "Pagamento e periodo d’imposta",
            "question": "Verificare i pagamenti effettivi e la loro riferibilità all’anno documentato.",
            "needed_information": [
                "Quietanze e pagamenti effettivi nell’anno d’imposta"
            ]
        },
        "own_share": {
            "page": 61,
            "quote": "Se il mutuo è intestato a più persone, ogni cointestatario può fruire della detrazione unicamente per la propria quota di interessi.",
            "title": "Quota degli interessi",
            "question": "Verificare a chi sono attribuiti gli interessi e se l’importo è già ripartito; la quota documentale non certifica la quota fiscalmente utilizzabile.",
            "needed_information": [
                "Intestatari del mutuo",
                "Attribuzione degli interessi e ripartizione già effettuata"
            ]
        },
        "purchase_purpose": {
            "page": 62,
            "quote": "Rigo E7 - Interessi per mutui ipotecari per l’acquisto dell’abitazione principale: indicare gli interessi passivi, gli oneri accessori e le quote di rivalutazione dipendenti da clausole di indicizzazione per mutui ipotecari contratti per l’acquisto di immobili adibiti ad abitazione principale.",
            "title": "Finalità e garanzia del mutuo",
            "question": "Verificare nel contratto la finalità di acquisto e la natura ipotecaria. La finalità dichiarata nel riepilogo non verifica tutti i requisiti.",
            "needed_information": [
                "Contratto e garanzia ipotecaria",
                "Finalità contrattuale"
            ]
        },
        "purchase_borrower": {
            "page": 62,
            "quote": "Per abitazione principale si intende quella nella quale il contribuente o i suoi familiari dimorano abitualmente. Pertanto, la detrazione spetta al contribuente acquirente e intestatario del contratto di mutuo, anche se l’immobile è adibito ad abitazione principale di un suo fa- miliare (coniuge, parenti entro il terzo grado e affini entro il secondo grado).",
            "title": "Acquirente, intestatario e abitazione principale",
            "question": "Verificare la posizione di acquirente e intestatario e l’uso dell’immobile come abitazione principale.",
            "needed_information": [
                "Titolo di acquisto e intestazione del mutuo",
                "Dimora abituale del contribuente o dei familiari"
            ]
        },
        "purchase_dates": {
            "page": 62,
            "quote": "La detrazione spetta a condizione che l’immobile sia adibito ad abitazione principale entro un anno dall’acquisto, e che l’acquisto sia avvenuto nell’anno antecedente o successivo al mutuo.",
            "title": "Date di acquisto, stipula e destinazione",
            "question": "Verificare le date e il regime applicabile al contratto, comprese le disposizioni per contratti meno recenti ed eventuali eccezioni: non si applica automaticamente il termine generale.",
            "needed_information": [
                "Date di acquisto e stipula",
                "Destinazione ad abitazione principale",
                "Eventuali condizioni particolari previste dalle istruzioni"
            ]
        },
        "loan_changes": {
            "page": 62,
            "quote": "In questi casi per data di stipula del mutuo è da intendersi la data di stipula del contratto di accollo/subentro/rinego ziazione/ del mutuo.",
            "title": "Data rilevante e modifiche del contratto",
            "question": "Verificare stipula ed eventuali accolli, subentri o rinegoziazioni prima di individuare il riferimento dichiarativo.",
            "needed_information": [
                "Data di stipula",
                "Eventuali accolli, subentri e rinegoziazioni"
            ]
        },
        "renovation_1997": {
            "page": 64,
            "quote": "La detrazione riguarda gli interessi passivi, gli oneri e le quote di rivalutazione dipendenti da clausole di indicizzazione per mutui (an- che non ipotecari) contratti nel 1997 per effettuare interventi di manutenzione, restauro e ristrutturazione degli edifici.",
            "title": "Distinzione del caso storico del 1997",
            "question": "Verificare se si tratta del caso specifico dei mutui contratti nel 1997; non attribuire questo regime alla finalità generica ristrutturazione.",
            "needed_information": [
                "Anno e finalità del contratto",
                "Tipologia degli interventi"
            ]
        },
        "renovation_qualification": {
            "page": 138,
            "quote": "Per costruzione di unità immobiliare si intendono tutti gli interventi realizzati in conformità al provvedimento di abilitazione comunale che autorizzi una nuova costruzione, compresi gli interventi di ristrutturazione edilizia di cui all’art. 31, comma 1, lett. d), della L. 5 agosto 1978, n. 457.",
            "title": "Qualificazione edilizia dell’intervento",
            "question": "Per il possibile percorso costruzione/ristrutturazione dell’abitazione principale, verificare la qualificazione edilizia e i titoli abilitativi. Non ogni lavoro indicato come ristrutturazione rientra in questo percorso.",
            "needed_information": [
                "Provvedimento abilitativo",
                "Qualificazione edilizia degli interventi"
            ]
        },
        "renovation_dates": {
            "page": 138,
            "quote": "il mutuo deve essere stipulato non oltre sei mesi antecedenti, ovvero nei diciotto mesi successivi alla data di inizio dei lavori di costruzione; se invece si tratta di mutui stipulati in data antecedente al 1° dicembre 2007, i termini sono di sei mesi, antecedenti o successivi, alla data di inizio dei lavori di costruzione.",
            "title": "Rapporto temporale tra mutuo e lavori",
            "question": "Verificare date di stipula e inizio lavori e la disciplina temporale applicabile.",
            "needed_information": [
                "Data di stipula",
                "Data di inizio lavori",
                "Eventuali condizioni particolari o proroghe da approfondire"
            ]
        },
        "renovation_use": {
            "page": 138,
            "quote": "l’immobile deve essere adibito ad abitazione principale entro sei mesi dal termine dei lavori di costruzione;  il contratto di mutuo deve essere stipulato dal soggetto che avrà il pos - sesso dell’unità immobiliare a titolo di proprietà o di altro diritto reale;",
            "title": "Abitazione principale e titolarità",
            "question": "Nel possibile percorso costruzione/ristrutturazione dell’abitazione principale, verificare uso, termine dei lavori e titolarità; restano da esaminare le eccezioni della fonte.",
            "needed_information": [
                "Data di fine lavori e destinazione ad abitazione principale",
                "Proprietà o altro diritto reale del soggetto che stipula il mutuo"
            ]
        },
        "renovation_documents": {
            "page": 138,
            "quote": "Per fruire della detrazione occorre conservare, esibire o trasmettere, a ri - chiesta degli uffici finanziari, le quietanze di pagamento degli interessi passivi relativi al mutuo, la copia del contratto di mutuo ipotecario (dal quale risulti che lo stesso è assistito da ipoteca e che è stato stipulato per la costruzione dell’immobile da destinare ad abitazione principale), le abilitazioni ammini- strative richieste dalla vigente legislazione edilizia e le copie delle fatture o ricevute fiscali comprovanti le spese di costruzione dell’immobile stesso.",
            "title": "Documentazione di mutuo e lavori",
            "question": "Verificare contratto ipotecario, quietanze, autorizzazioni e spese effettive dei lavori; non sostituirli con il solo importo annuo del riepilogo.",
            "needed_information": [
                "Contratto ipotecario e quietanze",
                "Titoli abilitativi",
                "Fatture o ricevute dei lavori"
            ]
        },
        "renovation_loan_changes": {
            "page": 64,
            "quote": "In questi casi per data di stipula del mutuo è da intendersi la data di stipula del contratto di accollo/subentro/rinegoziazione/ del mutuo.",
            "title": "Data rilevante e modifiche del contratto",
            "question": "Verificare stipula ed eventuali accolli, subentri o rinegoziazioni prima di individuare il riferimento dichiarativo.",
            "needed_information": [
                "Data di stipula",
                "Eventuali accolli, subentri e rinegoziazioni"
            ]
        }
    }
}

# Revisione congiunta obbligatoria di estratti e digest delle edizioni.
EDITION_DIGESTS = {'2024': 'ef1ec4ea4fb6de29a6b3709abbb41d85451ddd4f0a542e6d38063d22ab1e5d5e', '2025': '7a7a86c4a4eddfa2878a5e0aaa9f54a1c47aacdf1faff613db6443d555ec5a5d'}
