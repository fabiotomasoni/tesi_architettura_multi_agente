# Diario di progetto

Riferimento: requisiti e architettura dei capitoli 3–4 della tesi. Questo diario conserva solo modifiche rilevanti, verifiche e limiti. La numerazione richiama i passaggi già svolti; le ripetizioni dei comandi e gli output completi sono stati rimossi. I requisiti della tesi non vanno cambiati per adattarli al prototipo. Il lavoro residuo è riunito nei quattro punti di [DA_IMPLEMENTARE.md](DA_IMPLEMENTARE.md).

## Modifiche 1–22 — Gateway, dataset e prima architettura

Creato il gateway Python/FastAPI/Pydantic, inizialmente con ingresso JSON e poi con upload dei PDF del dataset sintetico. Gli scenari sono S-01, confronto orientativo del mutuo, e S-02, riferimenti relativi agli interessi da approfondire. Il gateway estrae e valida i valori, conserva localmente quelli esatti e prepara viste distinte per mercati e fiscalità. Campi mancanti o ambigui bloccano soltanto le attività che li richiedono; non sono ricostruiti dal modello.

Parser pypdf limitato al template sintetico, fino a quattro PDF entro 5 MiB e 20 pagine ciascuno. Leggibilità e sufficienza dei dati sono separate; file non supportati, duplicati o di fascicoli diversi sono rifiutati. Conto e busta paga sono riconosciuti, senza alimentare S-01/S-02. Nessun OCR o scenario aggiuntivo.

Due servizi ADK/A2A 0.3 usano MCP stdio reale e modelli locali llama3.2:3b e qwen3:1.7b (contesto 4096, massimo 200 token, temperatura zero, keep_alive=0; thinking fiscale disabilitato). LangGraph coordina i soli scenari richiesti con finalizzazione comune. Nessun terzo LLM per pianificare.

Dataset sintetico in `dataset`; ground truth separata dall’ingresso. Ambienti, cache, segreti, stato e raccolte locali esclusi da Git. Nessun database dei profili, nessun invio degli originali a provider e nessun salvataggio automatico del report.

**Verifiche:** C001/C024 completati, C006/C016 bloccati nello scenario insufficiente; gestiti agente spento, Ollama indisponibile e timeout con pulizia gateway. Una fixture e agent_boot_id hanno distinto recupero nello stesso processo da ripristino dopo riavvio. Tre ripetizioni costituiscono un pilota, non la campagna finale.

## Modifiche 23–26 — Provenienza e confronto dei valori (P01–P02)

Fatti collegati a documento/pagina, citazione e intervallo nel testo, digest, unità, periodo e trasformazione. Il periodo ha una provenienza distinta. Il verificatore rilegge i PDF e controlla anche la copertura; un ingresso JSON dichiarato non diventa automaticamente verificato sul documento.

La tipologia del mutuo non è esplicita nel dataset: con approvazione dell’utente resta facoltativa e «non specificata», accompagnata da un limite. Non viene trasformata arbitrariamente nella categoria «altro». I campi necessari al calcolo restano obbligatori e separati da quelli di contesto.

Il confronto RF-07 verifica grandezza, prodotto, unità e periodo prima del valore. Conversioni esplicite e Decimal; nessuna equivalenza implicita tra tassi di periodicità diversa. Un tasso contrattuale e un benchmark di mercato non rappresentano il medesimo fatto. I conflitti conservano entrambe le provenienze; non si sovrascrive il documento e non si sceglie automaticamente una fonte. Zero conflitti tra le osservazioni registrate non significa verifica esaustiva dei PDF.

**Verifiche:** citazioni C001/C006/C016 senza problemi; fixture per conflitti agente–documento/agente–agente/documento–documento e per conversioni, periodi, prodotti e grandezze non confrontabili. Questi conflitti sono introdotti nei test, non osservati nelle fonti nominali.

## Modifiche 27–29 — Calcoli locali orientativi (P03–P04)

Concordato un confronto del mutuo a rate mensili costanti, stesso capitale/durata, tasso annuo nominale diviso 12 e calcoli Decimal. Rata documentale distinta dalla teorica, totali da rata non arrotondata e importi esposti ai centesimi. Costi non documentati esclusi; variabile/misto a tasso congelato, senza previsione o risparmio garantito. Lo scostamento non corregge il documento né riproduce necessariamente il piano bancario.

Per gli interessi è stato concordato un riepilogo e il prodotto ipotetico interessi × quota. Si esplicita l’ipotesi, non verificata, che l’importo riguardi l’intero mutuo e non sia già ripartito: non è un importo personale attestato né una detrazione spettante. Nessuna aliquota o soglia normativa inventata. Ingressi insufficienti, fonti inutilizzabili, conflitti e periodicità non supportate impediscono i calcoli pertinenti.

**Verifiche:** report nominali C001 e C024 controllati con verificatori indipendenti; tutti i sei controlli mutuo e i nove fiscali veri. Su casi privi dei dati richiesti, verificata l’assenza dichiarata del calcolo. Provenienza, ipotesi, differenze e conservazione della rata documentale restano verificabili nel JSON.

## Modifiche 30–32 — Fedeltà delle sintesi e provenienza obbligatoria (P05)

Un’uscita fiscale del modello conteneva una conclusione non sostenuta dalla fixture. Le sintesi pubblicate di entrambi gli specialisti sono quindi estrattive e deterministiche, verificate contro il catalogo delle fonti simulate. Le affermazioni riportano riferimenti ai campi della fonte e digest. La prosa LLM non verificata è esclusa dal report; per la sperimentazione restano modello, hash e motivo dell’esclusione. Questa scelta tutela la fedeltà ma limita il contributo effettivo dei modelli: non si attribuisce loro la correttezza della sintesi applicativa.

Provenienza assente: `unverified/missing_provenance`, senza evidenza utilizzabile nei calcoli. I campi devono essere realmente ricevuti, non inventati dai default Pydantic. Errori di schema/contenuto restano distinti; il ramo valido è conservato e l’assenza di risultati utilizzabili non produce un falso completamento.

**Verifiche:** fixture MCP e agente senza provenienza, singolo ramo non verificato e ripristino nominale: partial/unverified attesi, esclusione dai calcoli, pulizia e successivo completed. Un hash non dimostra autorevolezza o verità.

## Modifiche 33–39 — Controlli centralizzati nel gateway (S01)

Centralizzati incarichi A2A, richieste di inferenza, autorizzazione degli strumenti e accesso alle fonti. Cataloghi chiusi, diniego predefinito, ricostruzione da template e nessun inoltro di URL o intestazioni arbitrarie. Le Card sono confrontate con identità, endpoint e capacità attesi prima della delega. Redirect e destinazioni alternative sono rifiutati.

Capability monouso legate a correlazione, scenario e scadenza, revocate alla finalizzazione. Nessun retry implicito dopo timeout o uso di risposte tardive. Inferenza e fonti MCP attraversano il gateway.

**Stato delle fonti:** `simulated-rates-v1` e `simulated-tax-v1`, con riferimenti e condizioni di test. Nessuna consultazione Internet, normativa reale o offerta corrente. MCP è realmente utilizzato come protocollo, ma il protocollo non implica che le informazioni provengano da Internet. Fonte, contenuto e contatori sono verificati separatamente dall’esistenza del collegamento MCP.

**Verifiche:** controlli su payload/destinatari non ammessi e capability errate, scadute o consumate. Stack locale completo A2A/ADK/MCP con Ollama reale su C001/C006 e con connettore avversario: percorso nominale completato, diniego prima di fonte/inferenza, ramo indipendente conservato, pulizia gateway e store agenti controllati separatamente nei test. Prima di S03, questi controlli applicativi non impedivano da soli connessioni dirette del processo.

## Modifica 40 — Filtro locale dei dati vietati (S02)

Aggiunto un contesto volatile per sessione con entità, importi e date conosciuti. Il filtro combina regole per email, IBAN, codice fiscale e telefono, riconoscimento locale euristico di persone/indirizzi/organizzazioni e confronto dei valori normalizzati. Non è un modello NER generale né una garanzia di anonimato. Alias, nomi sconosciuti senza contesto e codifiche non supportate possono sfuggire; parole comuni possono causare falsi positivi.

Corretti falsi positivi da collisioni importo/anno/fascia e da nomi estesi sulle righe successive. Eccezioni solo nei campi autorizzati e, per dati pubblici coincidenti, dopo verifica esatta del catalogo; mai nel testo libero o nei metadati arbitrari. Errori di costruzione del contesto non pubblicano sessioni parziali.

**Verifiche automatiche e manuali:** 26 sonde vietate rilevate, nove legittime accettate e 35 viste utilizzabili del dataset non bloccate, con zero errori nel corpus annotato di regressione. Non è una stima su testi generici. Suite allora 290 test; pilota manuale C001 completed e C006 partial, filtro 0.2.0 effettivamente presente nei rami eseguiti. Report C001 esportato: dieci fatti verificati, zero problemi, sei controlli mutuo e nove fiscali veri.

## Modifiche 41–42 — Isolamento locale e identità (S03)

Scelti con l’utente Docker Desktop e Compose. La tesi prevede container e restrizioni di rete nelle sezioni 4.1 e 4.5; non prescrive il prodotto Docker. Docker concretizza quel requisito. I configuratori di rete fidati applicano default DROP IPv4/IPv6 prima dell’avvio delle applicazioni. Gateway/orchestratore e due specialisti operano in workload distinti, senza privilegi applicativi, originali o socket del runtime; gli MCP stdio condividono il workload del proprio agente. Non si dichiara isolamento reciproco tra agente e proprio tool.

Ollama resta nativo per usare l’accelerazione locale. Il ponte host è un’aggiunta tecnica necessaria a questa scelta: ritira soltanto richieste autorizzate dal gateway, verifica il template e contatta Ollama su loopback senza aprire una porta aggiuntiva. Il gateway della demo è pubblicato su 127.0.0.1:8080. Coda volatile limitata, nessun backend alternativo o retry implicito dell’inferenza. Le durate del modello e del giro del ponte sono distinte e annidate.

Identità locali separate per ruolo/direzione, oltre alle capability degli incarichi; credenziali escluse da Git/immagini. Identità assenti o scambiate rifiutate. Non è mTLS o attestazione di processo: host, gateway e configurazione sono fidati. Per le fonti reali va abilitata soltanto l’uscita del proxy, non Internet diretto alle applicazioni.

**Verifiche:** 322 test, 68/68 controlli Docker ripetuti dall’utente, bersagli di controllo disponibili e uscite vietate fallite anche da due MCP avversari. Verificati privilegi, mount, porte e identità; normalizzati NET_ADMIN/CAP_NET_ADMIN nel verificatore senza ampliare permessi. Pilota manuale C001 completed/C006 partial, report e pulizia gateway confermati. S03 chiuso nel perimetro locale, senza dedurre azzeramento RAM o copertura Windows/fonti remote.

## Modifica 43 — Riallineamento alla tesi e prima presentazione del documento

Riletta la tesi e riscritto il piano in quattro risultati: fonti reali/agenti, demo/documento, verifiche essenziali, valutazione/consegna. Le fonti reali non sono più opzionali per la consegna richiesta dall’utente. «Aggiornato» significa ultima pubblicazione disponibile, con periodo e provenienza; non un’offerta personale in tempo reale garantita. La dimostrazione con Internet va distinta dalla campagna 2×2 locale/simulata prescritta dalla sezione 4.6.

Corretta l’interfaccia che negava l’esistenza di un report. Il documento HTML deriva dal JSON e mostra fatti/citazioni, confronti, fonti, ipotesi e limiti senza nuovi calcoli o prosa LLM. JSON esportabile e stampa/PDF tramite browser. Un guasto di presentazione conserva i dati. Mostrati richiesta ed esito degli agenti; le fasi live restano da completare senza simulare attività.

Escluse anche le note libere degli agenti dai limiti del report: potevano reintrodurre affermazioni non sostenute dalla fonte. Restano i limiti applicativi e dei calcoli; regressioni fiscali/mercati aggiornate.

Corretta anche la scadenza soltanto pigra delle sessioni: un controllo periodico elimina quelle scadute anche senza nuove richieste; shutdown in finally. Restano da verificare annullamento completo e recupero dopo crash. L’estrattore resta specifico del dataset e non analizza complessivamente liquidità e reddito; i modelli non hanno ancora un ruolo sostanziale nel testo finale. Questi limiti rimangono nel piano, senza reintrodurre testo non verificato per nasconderli.

**Verifiche:** suite completa 331 passed, 106 warning. Otto nuovi test verificano fedeltà del documento su cinque casi, precisione, trattamento sicuro del testo e conservazione del JSON se la presentazione fallisce; una nuova prova conferma la scadenza senza richieste successive. Controllata la sintassi dello script della pagina. La prova browser della presentazione usa deleghe simulate su un server locale temporaneo: non sostituisce le verifiche reali di A2A/MCP/Ollama. Nessuna fonte Internet attivata e nessun nuovo attacco S04 avviato.

## Modifica 44 — Prima fonte mercati istituzionale

Aggiunta modalità BCE esplicita, mantenendo le fixture come configurazione predefinita per gli esperimenti. Il tool MCP passa dal gateway; il ponte locale esegue una sola richiesta HTTPS predefinita alla serie MIR italiana sui nuovi mutui abitativi. Nessun documento o dato personale nella richiesta. Container e regole di isolamento invariati.

Il gateway conserva e controlla risposta CSV, serie, unità, periodo, momento del recupero e impronta; confronta il risultato dell’agente con la risposta effettivamente recuperata. Il report separa fonte reale e fiscale simulata. L’AAR/NDER aggregato non è un TAN né un’offerta: il confronto della rata alternativa resta non calcolato, senza fallback inventati. La prosa del modello resta non verificata ed esclusa dalle conclusioni.

**Verifiche:** 373 test superati, 106 warning. Prova reale Docker → A2A → MCP → gateway/ponte → BCE e Ollama: C001 completed, C006 partial con mercati bloccati; sessioni cancellate. Artefatti locali in runs/ecb_validation.jsonl e runs/ecb_report_validation.json. Controllo BCE: 13 verifiche positive; provenienza: 10 fatti, zero problemi; controlli fiscali positivi. Queste sono prove pilota, non la campagna finale. Restano fonte fiscale reale, verifica manuale della demo e ruolo sostanziale del modello. S04 non avviato.

## Modifica 45 — Fedeltà degli esiti senza calcolo e chiusura mercati BCE

La verifica manuale dei report C001 e C006 conferma rispettivamente esito completo e parziale, citazione BCE separata dalla fiscalità simulata e provenienza documentale senza problemi (10 e 9 fatti). C006 ha evidenziato note su un tasso simulato mai utilizzato: la causa era l’inserimento anticipato di ipotesi e limiti nei blocchi comuni. Corretti tutti i percorsi senza calcolo, anche fiscali: niente ipotesi applicate o note sulle fixture; restano motivo, limiti pertinenti e contesto verificato. Nessun cambiamento alle formule dei calcoli eseguiti.

Aggiunte dieci regressioni su input mancanti, conflitti, periodicità non supportata, errori, evidenze assenti e parametri non supportati; esteso il controllo BCE. Suite completa: 383 passed, 106 warning; quattro test inizialmente impediti dal blocco delle connessioni locali sono passati dopo l’abilitazione. Il primo collegamento mercati reale è chiuso nel suo perimetro: statistica aggregata, non ricerca di offerte personali. Fiscalità reale e ruolo sostanziale dei modelli restano da completare; S04 fermo.

## Modifica 46 — Verifica preliminare delle pubblicazioni fiscali

Controllati i 25 PDF interessi: anni d’imposta 2024 (5) e 2025 (20); acquisto abitazione principale (17) e ristrutturazione (8). Recuperate direttamente via HTTPS due pubblicazioni ufficiali, entrambe HTTP 200 application/pdf: [730/2025](https://infoprecompilata.agenziaentrate.gov.it/portale/documents/10180/208302/730_2025_istruzioni.pdf), 168 pagine, per il 2024; [730/2026](https://infoprecompilata.agenziaentrate.gov.it/portale/documents/d/guest/730_istruzioni_2026.pdf), 175 pagine, per il 2025. Il secondo URL è collegato dalla pagina ufficiale del Quadro E. Verificati sezioni interessi, rigo E7, costruzione/ristrutturazione e appendici: pagine PDF 58–61 e 130–131 nel primo; 61–64 e 137–138 nel secondo (sezioni da acquisire integralmente).

L’anno della dichiarazione non coincide con quello d’imposta; anche la data di stipula e gli eventuali subentri/rinegoziazioni incidono sui riferimenti. «Ristrutturazione» generica non prova i requisiti del mutuo per ristrutturazione edilizia dell’abitazione principale. Il prossimo incremento recupererà la pubblicazione annuale ammessa e citerà condizioni pertinenti senza attribuire automaticamente codici, detrazioni o spettanza. Anni non catalogati e fonte indisponibile dovranno produrre un limite esplicito, senza fallback simulato. Questa verifica non ha ancora collegato l’agente fiscale a Internet: configurazione e codice applicativo invariati.

## Modifica 47 — Collegamento fiscale alle due pubblicazioni annuali

Aggiunta modalità AdE esplicita: MCP richiede la fonte al gateway e il ponte recupera via HTTPS soltanto il PDF annuale autorizzato, senza dati del fascicolo. Anni 2024/2025 associati alle istruzioni 730/2025 e 730/2026; controllati formato, dimensione, URL senza redirect e digest delle edizioni già esaminate. Un PDF aggiornato richiede revisione del catalogo, non viene interpretato automaticamente. Estratti selezionati per contesto con pagine, anno e recupero; non sono una checklist esaustiva. Report 0.10.0 distingue fonti reali/simulate e mantiene la ripartizione ipotetica senza detrazione, codice assegnato o spettanza personale. Fonte assente, anno non supportato o ponte non abilitato: nessun fallback simulato.

Il primo pilota ha evidenziato falsi blocchi privacy: numeri di pagina coincidenti con dati documentali e sottostringhe di nomi sintetici nel testo pubblico (Riva/rivalutazione). Corretto il trattamento delle citazioni immutabili, già confrontate esattamente con catalogo e ricevuta; invariato il rilevatore per i campi variabili. Regressioni includono collisioni e tentativi di alterare evidenza/ricevuta.

**Verifiche:** 410 passed, 106 warning; 27 nuovi test fiscali, sintassi pagina controllata. Ripetizione reale Docker/A2A/MCP/gateway/ponte/AdE/Ollama: C001, C021 e C022 completed; C006 e C011 partial per input mancanti. Tutti i controlli fonte, aritmetica e cancellazione positivi; entrambe le annualità e finalità coperte. Evidenze locali in runs/ade_recovery_validation.jsonl e runs/ade_report_C*.json; il primo pilota fallito resta distinto in runs/ade_validation.jsonl. Da completare la prova manuale dell’utente. README e residui aggiornati; nessuna campagna finale o S04 avviata.

## Modifica 48 — Verifica manuale C001 con entrambe le fonti reali

Controllato report-locale-26.json esportato dall’utente: entrambi gli scenari completed, nessuna fixture, BCE coerente e AdE 730/2026 per anno d’imposta 2025 con citazioni alle pagine 61–62. Tutti i 9 controlli AdE e 13 BCE positivi; 10 fatti documentali verificati, zero problemi. Ripartizione soltanto ipotetica, nessuna detrazione/spettanza o convenienza attestata. Il JSON non dimostra da solo isolamento e pulizia, coperti dai test dedicati.

La verifica ha scoperto un difetto nell’avvio diretto di check_tax_application.py: import del supporto valido come modulo ma non come script. Corretto per entrambe le modalità e aggiunta regressione in sottoprocesso con report reale di test. Controllo sul file utente ora interamente positivo; 39 test pertinenti superati, 13 warning. Nessuna modifica al report o ricostruzione dei container necessaria. Restano le prove manuali dell’altra annualità/finalità e degli esiti parziali.

## Modifica 49 — Chiusura delle prove manuali del collegamento fiscale

Controllati report-locale-27.json (C021) e report-locale-28.json (C011). C021 completed: anno d’imposta 2024, istruzioni 730/2025, citazioni per ristrutturazione con applicabilità non accertata; tutti i controlli AdE, BCE e aritmetici positivi, 10 fatti documentali verificati e zero problemi. C011 partial: mercati completati con BCE, fiscalità bloccata per annual_interest mancante; nessuna fonte/sintesi fiscale, ripartizione o ipotesi applicata inventata. Controlli BCE e fiscali positivi, 9 fatti verificati e zero problemi.

Con C001 già verificato, le prove manuali coprono entrambe le annualità, acquisto/ristrutturazione ed esito parziale. Chiuso il collegamento alle due edizioni AdE nel perimetro concordato. Non è una verifica fiscale personale o una copertura esaustiva della normativa; indisponibilità/alterazione/anno fuori catalogo restano coperti dai test automatici. Nessuna nuova conclusione su isolamento o cancellazione ricavata dai soli JSON esportati. Restano ruolo sostanziale dei modelli, demo e valutazione della tesi; S04 fermo.

## Modifica 50 — S-01: modello documentale indipendente dalla fonte

Report 0.11.0: aggiunta mortgage_contract_analysis, separata dal confronto alternativo. Con dati validati, periodi allineati e rate mensili, calcola rata e totali residui teorici al TAN documentale, conserva la rata del PDF e mostra lo scostamento senza correggerla o diagnosticare errori contrattuali. Variabile/misto: solo scenario a tasso congelato. Nessuna nuova offerta o ipotesi di tasso alternativo. BCE resta contesto; fonte mancante/non verificata non elimina il modello locale. Input insufficienti, unità/periodi errati, conflitti o periodicità non supportata impediscono il modello. Esito tecnico dell’agente invariato.

Documento leggibile e check_mortgage.py aggiornati; controllo numerico indipendente anche per il nuovo blocco e comando diretto verificato. Test coprono fonte reale congelata, fixture, guasto/diniego/provenienza mancante, fisso/variabile, dati invalidi e manomissione dei risultati. Prova locale su C001/C024: modello calcolato, alternativa BCE non calcolata; C006: entrambi non calcolati. Suite completa: 434 passed, 106 warning. Si tratta di prove offline, non di nuovi recuperi Internet. Da completare la verifica manuale dopo ricostruzione dell’immagine. Il confronto con un’offerta reale compatibile resta aperto; S04 fermo.

## Modifica 51 — Verifica manuale del modello locale S-01

Controllati report-locale-29/30/31/32.json. Il primo C001 è failed con due timeout: l’utente ha confermato il ponte spento; il modello locale rimane corretto. Dopo riavvio del ponte C001 completed, con fonti BCE/AdE e rata teorica 1.604,32 EUR. C024 completed: rata teorica 867,11 EUR e limite esplicito di tasso congelato, senza previsione. Entrambi: 10 fatti documentali verificati, zero problemi; controlli modello, fonti e ripartizione positivi. Non sono disponibili tempi per fase nei JSON esportati e il riavvio manuale non dimostra recupero automatico nello stesso processo.

C006 partial: capitale residuo mancante, agente mercati bloccato, modello contrattuale e confronto non calcolati senza stime; fiscalità completata con fonte AdE. Controlli pertinenti tutti positivi, 9 fatti verificati e zero problemi. Nessuna fonte mercati aggiunta. Chiuso l’incremento del modello locale indipendente, non l’intero confronto economico S-01: resta necessario un riferimento alternativo compatibile e documentato prima di un confronto reale. Nessuna nuova evidenza su isolamento o pulizia ricavata dai soli report. S04 fermo.

## Modifica 52 — S-02: riepilogo fiscale e condizioni citate

Report 0.12.0: aggiunto tax_review, separato dalla ripartizione ipotetica. Riporta dati e provenienza documentali, contesto candidato, condizioni da verificare e informazioni necessarie, con estratti e pagine delle edizioni AdE autorizzate. Acquisto, costruzione e ristrutturazione restano distinti; per quest’ultima sono separati caso storico 1997 e possibile percorso edilizio dell’abitazione principale. Nessun regime/codice, aliquota o spettanza attribuiti. Tutte le condizioni personali restano non valutate dai campi supportati: non si afferma che informazioni non estratte siano assenti dai PDF. Catalogo selettivo, non esaustivo, vincolato ai digest delle edizioni verificate.

Fonte mancante/simulata, input invalido o conflitto: nessuna checklist normativa ufficiale inventata. La ricevuta del gateway resta obbligatoria. Nessuna modifica alle uscite, ai prompt o ai calcoli esistenti. Aggiornati documento leggibile, README e residui; nuovo check_tax_review.py per dati, citazioni, annualità, pertinenza e assenza di spettanza.

**Verifiche:** 460 passed, 106 warning; 26 nuove regressioni per due annualità, finalità, errori, input incompleti, alterazioni, edizione cambiata, link non autorizzati e comando diretto. Riesaminate le pagine dei PDF ufficiali già fissati, con digest corrispondente; nessuna nuova edizione assunta. Prove offline su C001/C022: 6 condizioni; C006/C021: 8; C011: nessuna, input incompleto. Controlli tutti positivi. Da completare prova manuale della demo dopo ricostruzione immagine; nessun nuovo esperimento comparativo o S04 avviato.

## Modifica 53 — Verifica manuale del riepilogo fiscale

Controllati report-locale-33/34/35.json (versione 0.12.0). C001 completed: 6 condizioni candidate per acquisto, anno 2025 e istruzioni 730/2026; C021 completed: 8 condizioni candidate per ristrutturazione, anno 2024 e istruzioni 730/2025, con caso storico 1997 distinto e nessun regime assegnato. Tutti i controlli riepilogo, AdE, BCE, modello mutuo e ripartizione positivi; 10 fatti documentali verificati e zero problemi per ciascuno.

C011 partial: mercati completati, fiscalità bloccata per annual_interest mancante. Profilo disponibile conservato senza inventare il dato assente, condizioni vuote, nessuna fonte fiscale o ripartizione. Controlli pertinenti positivi, 9 fatti verificati e zero problemi. Chiuso l’incremento selettivo S-02 nel perimetro concordato; non è una verifica esaustiva della normativa o della spettanza. Nessuna nuova evidenza di isolamento/pulizia dedotta dai soli report. S04 fermo.

## Modifica 54 — Baseline S+P e profilo comparabile M+P

Seguendo 3.5/4.6, aggiunto un solo agente ADK generalista per S-01/S-02: un incarico A2A aggregato con capability separate per attività, accesso diretto agli stessi MCP e risultati distinti. Riutilizzati gateway, estrazione, policy, validatori, calcoli e report. Identità generalista/gateway/ponte separate da quelle della demo; container non privilegiato nello slot di rete già previsto, specialista fiscale non avviato nella configurazione singola. Nessuna nuova uscita di rete.

Profili sperimentali espliciti single/multi: fixture nominali fissate, llama3.2:3b per entrambe le attività, parametri invariati e keep_alive=0. Attività sequenziali e scadenza comune di sessione a 120 secondi in entrambi; il profilo demo conserva modelli e concorrenza. Fonti Internet e avvio del gateway sperimentale senza isolamento rifiutati. La prosa LLM resta esclusa: il pilota misura soprattutto coordinamento/costi/robustezza, senza presumere un vantaggio qualitativo.

**Verifiche:** 473 passed, 106 warning; 13 nuove regressioni su profili, contratti, identità, ponte, esiti parziali e comparatore. Prove reali Docker/A2A/MCP/Ollama, una ripetizione per configurazione: C001/C024 completed; C006/C011/C016 partial, controlli e pulizia positivi. Pesi con digest uguale e risultati strutturati coincidenti sui cinque casi. Nei casi completi: singolo = una delega e stesso boot ID; multi = due deleghe e due boot ID; entrambi due MCP/due inferenze. La delega comune è contata dal coordinatore, non duplicata per risultato. Artefatti locali runs/baseline_single_validation.jsonl e runs/baseline_multi_validation.jsonl, check_baseline_pilot positivo. Ripristinata demo BCE/AdE su 8080 e fermati solo i ponti di verifica temporanei.

README e residui aggiornati; script pilota conserva soltanto metadati, digest e controlli, senza prosa o dati documentali. Da completare prova manuale guidata. Non sono implementati S−P/M−P, campagna finale, rubriche/soglie o dieci ripetizioni; i tempi pilota non dimostrano superiorità. S04 fermo.

## Modifica 55 — Confronto manuale dei piloti S+P/M+P

Verificati runs/baseline_single_manual.jsonl e runs/baseline_multi_manual.jsonl: cinque righe ciascuno, senza duplicati; stessi casi, pesi del modello, impostazioni e risultati strutturati. C001/C024 completed, C006/C011/C016 partial in entrambi; controlli, finalizzazione e cancellazione positivi. check_baseline_pilot.py: passed True. Nei casi completi una delega A2A e un’identità di agente nel singolo, due deleghe e identità distinte nel multi; due chiamate MCP e due inferenze in entrambi. Nei parziali una sola attività eseguibile: una delega, un MCP e un’inferenza.

Chiusa la verifica manuale dei primi profili S+P/M+P. Una ripetizione per caso e configurazione è un pilota, non la campagna della tesi; i tempi osservati non dimostrano superiorità. Prosa LLM esclusa dal report e nessuna valutazione umana della qualità ancora eseguita. Restano S−P/M−P, copertura delle verifiche, annotazioni/rubriche/soglie e dieci ripetizioni finali. S04 fermo.

## Modifica 56 — S−P/M−P nel laboratorio finanziario sintetico

Perimetro confermato dall’utente: profilo finanziario completo con valori esatti, unità, periodi e stati, senza selezione per specialista né durata in fasce. Originali, testo grezzo, citazioni dei PDF e identificativi restano esclusi in tutte le celle: questa è l’operazionalizzazione della minimizzazione finanziaria, non un confronto sulla rimozione di nomi/IBAN. Nuovo profilo di avvio esplicito; non selezionabile nei messaggi. Conservati instradamento, autenticazione, schemi, destinazioni, budget e validazione dei dati locali. Il profilo completo deve coincidere con quello autorizzato per la sessione e viene revocato con essa.

Tutte le celle sperimentali ammettono solo PDF del corpus sintetico fissato per digest, senza montare il dataset; ingresso JSON diretto e fascicoli mescolati rifiutati. Nessuna fonte reale. Stessi MCP e formato del prompt fonte+contesto in tutte le celle; il contesto è minimizzato o completo. Protocollo financial-profile-2x2-v1: occorrono nuovi S+P/M+P, senza mescolare i piloti precedenti. Metriche di byte canonici/categorie delle viste autorizzate ai confini A2A/MCP/modello, senza valori nei log; non sono pacchetti wire né prova di consegna dopo guasti o divulgazioni Internet.

**Verifiche:** 493 passed, 106 warning; contratti chiusi, vincoli del corpus, rifiuto delle fonti reali, forma delle viste, conservazione delle ambiguità, revoca e comparatore. Pilota reale Docker/A2A/MCP/Ollama sui cinque casi, una ripetizione per ciascuna delle quattro celle: esiti attesi e pulizia positivi; check_factorial_pilot passed True. Artefatti runs/four_{single,multi}_{active,disabled}_validation.jsonl. Risultati strutturati uguali e pesi/budget confrontabili. C001: viste attive 119 byte mercati e 90 fiscalità contro 996 byte ciascuna senza minimizzazione; importi esatti da zero a tre campi. È un’osservazione pilota sul contenuto finanziario autorizzato, non una misura generale di privacy/utilità o un vantaggio qualitativo dimostrato. Ripristinata la precedente configurazione multi/active su 8080; il ponte dell’utente va riavviato con il codice aggiornato.

README e residui aggiornati, nuovo check_factorial_pilot.py. Da completare prova manuale delle quattro celle. Restano rubriche, soglie, annotazioni, copertura V-01–V-10 e campagna finale con dieci ripetizioni; S04 non avviato.

## Modifica 57 — Verifica manuale delle quattro celle pilota

Controllati runs/{single,multi}_{active,disabled}_manual.jsonl: cinque righe senza duplicati per cella, stesso protocollo financial-profile-2x2-v1, ingressi per caso, pesi, impostazioni e budget confrontabili. Tutte le 20 esecuzioni con esiti attesi, controlli e pulizia positivi: C001/C024 completed, C006/C011/C016 partial. check_factorial_pilot.py: passed True. Risultati strutturati coincidenti nelle quattro celle.

La riduzione del contesto finanziario è confermata nei controlli A2A/MCP/modello: per C001, viste canoniche di 119 byte mercati e 90 fiscalità con minimizzazione contro 996 byte ciascuna senza; da zero a tre campi di importi esatti, in entrambe le organizzazioni. Sono metriche del contenuto finanziario autorizzato nel laboratorio, non traffico wire complessivo o divulgazioni reali verso Internet.

Chiuso il pilota manuale 2x2 nel perimetro concordato, con una ripetizione per caso/cella. Non è la campagna finale: nessuna conclusione statistica su prestazioni o superiorità, nessuna verifica umana della qualità ancora eseguita. Il report deterministico resta invariato; non si assume un vantaggio d’utilità dai dati aggiuntivi. Restano rubriche, soglie, annotazioni, verifiche mancanti e dieci ripetizioni finali; S04 fermo.

## Modifica 58 — Bozza del protocollo di valutazione finale

Preparati PROTOCOLLO_VALUTAZIONE.md e file evaluation/: disegno 2x2, annotazioni preliminari per 25 fascicoli, rubrica 0–8, scheda umana vuota, soglie proposte e mappa puntuale V-01–V-10. Scelta dell’utente: un solo valutatore, senza accordo inter-valutatore stimato. Le 1.000 esecuzioni di base non coprono automaticamente le istanze aggiuntive di guasto/sicurezza. Campagna finale e S04 non avviati.

Riferimento costruito dal ground truth del generatore controllando i PDF per digest, valori, unità e periodi, senza usare l’output applicativo come verità. Esclusi identità e valori latenti omessi/ambigui. Calcoli attesi con riferimento numerico indipendente; materiale riservato al valutatore, fuori da runtime/immagini. Necessaria revisione umana delle annotazioni. Distinte utilità locale e dell’agente; attività non eleggibili N/A, durata più precisa ammessa, nessun premio per campi superflui. La fixture mercati usa soltanto il tipo di tasso: la durata è necessaria al contratto del compito ma non causalmente alla fixture; limite esplicito.

Proposte, non approvate: calcoli derivati entro 0,01 EUR (importi documentali esatti), U≥0,95, qualità≥7/8 senza criteri a zero o errori critici, perdita media di U≤0,05 e qualità≤1 punto. Zero trasmissioni non autorizzate è già vincolo della tesi. Nessuna SLA di latenza inventata; restano manifest, registro cieco, runner finale e residui V-01–V-10. Nessun punteggio umano compilato dal sistema.

**Verifiche:** suite completa 508 passed, 106 warning; 15 test del valutatore, ripetuti dopo completamento della mappa. check_evaluation_protocol: 951 controlli, zero problemi, stato draft_pending_user_approval e campagna non autorizzata. Le verifiche della bozza non provano conformità finale o approvazione. README e residui aggiornati; nessuna modifica a servizi, modelli o container.

## Modifica 59 — Approvazione dei criteri, non della campagna

L’utente ha approvato rubrica e soglie presentate: zero trasmissioni non autorizzate, dati documentali esatti, calcoli derivati entro 0,01 EUR, utilità almeno 0,95, qualità almeno 7/8 senza criteri a zero o errori critici, perdita media massima 0,05 di utilità e 1 punto di qualità; tempi descrittivi con budget tecnico 120 secondi, nessuna SLA aggiuntiva. Registrata approvazione separata con digest delle soglie nel protocollo v2. Nessun giudizio umano assegnato.

Stato draft_pending_annotation_review_and_verification: annotazioni ancora da rivedere, requisiti mancanti da verificare e protocollo non congelato. Campagna finale e S04 restano non avviati. Audit: 952 controlli, zero problemi; 16 test pertinenti superati, 13 warning. Regressione verifica che modificare le soglie invalida l’approvazione registrata e non abilita la campagna. Documentazione e residui allineati.

## Modifica 60 — Schede per la revisione delle annotazioni

Preparato uno strumento locale per confrontare il riferimento con i PDF: valori, unità, periodi, estratti con pagina, assenze/ambiguità, esiti, calcoli teorici, utilità e limiti. Primo gruppo C001/C006/C011/C016/C021; disponibili selezione degli altri casi e corpus intero. Digest controllati prima della generazione, nessuna chiamata a modelli o servizi, nessuna identità copiata negli estratti selezionati. Le schede sono in runs, fuori da Git; annotazioni e punteggi non vengono modificati o approvati automaticamente.

Verifiche: 25 test pertinenti superati, 13 warning di dipendenza; incluse regressioni su PDF modificato, TAN ambiguo, dati mancanti, periodi distinti, selezioni errate, escape HTML e mancata sovrascrittura. Revisione umana ancora da effettuare per tutti i 25 casi; campagna finale e S04 non avviati. Nessuna modifica al runtime o ricostruzione Docker necessaria.

## Modifica 61 — Conferma dei primi cinque riferimenti

Registrata la conferma esplicita dell’utente per C001/C006/C011/C016/C021: 5/25 annotazioni riviste contro i PDF. Ogni conferma è legata al digest del caso; modificare dati, stati, calcoli o impronte dei documenti la invalida. Nessun punteggio umano dei report assegnato. Preparata la scheda dei venti casi restanti; protocollo non congelato, campagna finale e S04 fermi.

Audit: 960 controlli, zero problemi; 27 test pertinenti superati, 13 warning di dipendenza. Annotata per l’interfaccia finale l’evidenziazione dei problemi con colore e testo: rosso per impedimenti e conflitti effettivi, avviso distinto per limiti non bloccanti; periodi contrattuali e fiscali diversi non sono da soli una discordanza.

## Modifica 62 — Revisione del riferimento completata

L’utente ha confermato i venti fascicoli restanti: revisione delle annotazioni completa, 25/25, con digest per ciascun caso. Stato del riferimento human_reviewed; protocollo v3 draft_pending_verification. Rimosso soltanto il residuo della revisione umana delle annotazioni: nessun punteggio dei report assegnato, nessun congelamento o avvio della campagna finale; S04 fermo. Schede e documentazione distinguono ora generazione del confronto e conferme già registrate.

Audit: 982 controlli, zero problemi; 29 test pertinenti superati, 13 warning di dipendenza. Verificati copertura completa, invalidazione dopo modifica del riferimento e mantenimento degli altri vincoli della campagna. Prossimo lavoro: annullamento completo e pulizia degli incarichi, poi verifiche residue e tracciamento.

## Modifica 63 — Annullamento, revoca e recupero

Rif. tesi §4.4, finalizzazione comune e V-02. Colmata la lacuna fra cancellare il profilo e fermare il lavoro: un’operazione attiva per sessione, annullamento del grafo su DELETE/disconnessione/TTL, revoca delle capability e rimozione degli incarichi del ponte, risultati tardivi esclusi. Il ponte verifica la validità del job e chiude la richiesta locale revocata. Gli agenti legano le esecuzioni SDK alla richiesta e puliscono ADK/A2A/MCP; lo stesso responsabile della sessione gestisce la finalizzazione. Interfaccia: annullamento disponibile durante l’analisi, nessuna visualizzazione della risposta tardiva.

Verifiche: suite completa 534 passed, 120 warning delle dipendenze; test con HTTP reale, veri sottoprocessi MCP terminati, accessi precedenti rifiutati e nuova sessione riuscita; generalista interrompe la sequenza e riparte nello stesso processo. Controllato anche il caso di risposta tardiva nella pagina. Audit del protocollo: 988 controlli, zero problemi, annotazioni confermate 25/25.

Preparato check_cancellation.py per la prova manuale della demo isolata: C001 prima, annullamento con due job trattenuti, rifiuto tardivo e C001 dopo, stessi avvii degli agenti. Risposte modello controllate e dichiarate, nessuna inferenza Ollama reale o misura finale; nessun payload finanziario nei risultati della prova. **Prova manuale sui container ancora da eseguire.** Nessuna promessa di arresto immediato del calcolo interno a Ollama o azzeramento fisico della RAM. Restano consegna fallita/crash, sostituzione e tracciamento; campagna finale e S04 fermi.

## Modifica 64 — Prova manuale di annullamento confermata

Controllato runs/cancellation_manual.json dopo la ricostruzione dell’immagine e l’avvio della demo isolata base: C001, 14 controlli True e passed True. Analisi iniziale completa e ripulita; seconda analisi annullata con entrambi i job trattenuti, duplicato rifiutato, nessun report consegnato, job e risultati tardivi rifiutati, profilo chiuso non accessibile. Nuova analisi completa e ripulita con gli stessi ID di avvio dei due agenti, senza riavviarli. Risposte del modello simulate e dichiarate: prova del coordinamento e del recupero, non di qualità o prestazioni Ollama. Annullamento confermato nel perimetro del pilota; restano consegna fallita/crash, sostituzione e tracciamento. Campagna finale e S04 fermi.

## Modifica 65 — Consegna fallita e recupero dopo arresto

Rif. tesi §4.4 e V-02. Verificati errore di invio ASGI e consegna interrotta a valle dopo report completo: sessione/accessi rimossi e nuova analisi riuscita. Prova automatica con vero SIGKILL di un gateway temporaneo, deleghe controllate e upload parziale con spool aperto ma già senza nome; al nuovo avvio stato precedente rifiutato, risorse temporanee non recuperabili dal percorso e analisi nuovamente riuscita. Aggiunto solo un identificativo opaco di avvio a health, senza archivio o ripresa automatica dei profili.

Suite completa: 542 passed, 120 warning; audit 994 controlli, zero problemi. Preparato check_finalization.py per due prove manuali: consegna troncata via relay loopback; SIGKILL/start del solo gateway Docker con controllo positivo di tmpfs. Risposte modello simulate e dichiarate; nessuna prova di blackout dell’host o azzeramento fisico della RAM. **Prove manuali Docker ancora da eseguire.** I container dell’utente non sono stati interrotti durante lo sviluppo. Restano conferme manuali, sostituzione equivalente, tracciamento e campagna finale; S04 fermo.

## Modifica 66 — Consegna fallita confermata sui container

Controllato runs/delivery_manual.json: C001, 20 controlli True e passed True. Report completo al relay, nessun byte del corpo applicativo consegnato al client e guasto di protocollo effettivamente osservato. Sessione/viste/job precedenti assenti, risultati tardivi rifiutati e nuova analisi completa con gli stessi avvii di gateway e agenti. È una consegna fallita a valle del gateway; l’errore di scrittura diretta ASGI ha evidenza automatica separata. Risposte modello simulate, nessuna misura Ollama reale. Resta la prova manuale di crash; campagna finale e S04 fermi.

## Modifica 67 — Crash del gateway confermato sui container

Controllato runs/crash_manual.json: C001, 22 controlli True e passed True. Verificati storage volatile e marcatore tmpfs, due job attivi prima del SIGKILL, uscita 137 e interruzione HTTP; il ponte annulla le richieste alla perdita del gateway. Al nuovo avvio il marcatore è assente e vecchie sessioni/viste/job e risposte tardive sono rifiutati. Nuova analisi completa e ripulita con gli stessi avvii degli agenti: è una nuova elaborazione dopo ricaricamento, non ripresa della sessione interrotta. Piloti di annullamento, consegna fallita e crash conclusi nel perimetro controllato, con risposte modello simulate; nessuna prova di blackout o cancellazione fisica della memoria. Residui aggiornati: sostituzione equivalente, tracciamento e istanze/ripetizioni finali. Campagna finale e S04 fermi.

## Modifica 68 — Sostituzione equivalente MCP (V-06)

Scelto uno strumento, come ammesso da V-06/RNF-05: server mercati FastMCP sostituibile con implementazione low-level MCP distinta e stesso contratto lookup_rates, sempre tramite proxy. Selezione chiusa all’avvio del solo gateway, catalogo strumenti 0.4.0; policy dati 0.3.0 invariata. Nessuna modifica al trattamento locale dei documenti o all’agente. Prova positiva nativa su cinque casi e tre fasi standard/equivalente/standard (15 esecuzioni), A2A/MCP reali e risposta modello controllata: profilo, intero report JSON/HTML, fonti e avvii degli agenti invariati. Nei confronti si normalizzano soltanto gli ID allocati ai documenti, preservando i contenuti e le provenienze.

Suite completa 556 passed, 127 warning; audit 1.000 controlli, zero problemi. Verificati contratti stdio, rifiuto di moduli non selezionati/configurazioni non ammesse e ripristino/pulizia dopo errore. Preparati compose.substitution.yaml e check_substitution.py: confronto e ripristino automatico sulla demo isolata, senza riavviare gli agenti. **Prova manuale Docker ancora da eseguire.** Nessuna pretesa di sostituzione universale o misura di prestazioni/qualità Ollama. Residui aggiornati; campagna finale e S04 fermi.

## Modifica 69 — V-06 confermato sui container

Controllato runs/substitution_manual.json: 15 esecuzioni positive (C001/C024/C006/C011/C016 nelle tre fasi standard/equivalente/standard), 42 controlli True e passed True; ricalcolati i 39 confronti tra le fasi. Contratto MCP identico, implementazioni/server distinti e modulo autorizzato coerente con ogni fase. Invariati PDF, profilo, intero report JSON/HTML, fonti, codice, immagini e avvii degli agenti; riconfigurato solo il gateway e ripristinato lo standard. Pilota V-06 concluso per un server MCP equivalente, come ammesso dalla tesi; risposte modello simulate, nessuna prova universale o misura di qualità/prestazioni Ollama. Rimosso il residuo della conferma manuale: restano traccia completa, istanze/ripetizioni e strumenti della campagna finale. S04 fermo.

## Modifica 70 — Traccia dell’elaborazione e budget configurabili

Rif. RF-05/RF-10, RNF-06 e §§4.3–4.5: collegati upload/estrazione, contesto privacy, viste/scansioni, grafo, A2A, permessi MCP, fonte/modello, verifiche, report, presentazione, invio ASGI e pulizia. Soli metadati ammessi in RAM limitata, consultabili dopo la cancellazione del profilo ed esportati esplicitamente nei nuovi piloti. Durate annidate non additive, pausa dell’utente separata dal tempo delle richieste; metriche dell’agente e ricevute del ponte dichiarate come tali. Distinti permessi, tentativi e risposte; guasti senza ricevuta lasciano consumi non disponibili, senza inventare zero token. Un replay della capacità fonte non riconta ricevute precedenti. Budget configurabili all’avvio della demo, invariati e obbligatori nel confronto 2×2; report documentale invariato.

Suite completa: **579 passed, 127 warning**; audit **1.004 controlli, zero problemi**, campagna non autorizzata. Verifica nativa con A2A/MCP reali: completo, parziale, ingresso rifiutato, timeout modello iniettato, annullamento e recupero con gli stessi agenti; modelli controllati, nessuna misura Ollama/Internet. Risolto l’isolamento della fixture di test per evitare lock ADK/A2A riutilizzati tra event loop chiusi. Tracce troncate/perse non diventano totali completi; invio ASGI non prova ricezione dal client e zero dinieghi associati non prova assenza di esfiltrazione. Preparato check_trace.py: **conferma manuale Docker ancora da raccogliere**; container dell’utente non modificati. Aggiornati README, residui e protocollo; priorità al prototipo funzionante, capitoli 5–6 a cura dell’autore sulle evidenze. S04 e campagna finale fermi.

## Modifica 71 — Recupero dopo annullamento e diagnosi del pilota

Il primo check_trace manuale si è interrotto, senza produrre un successo. Riprodotto il blocco con cicli ripetuti in un container temporaneo Python 3.12: un producer SDK poteva rimanere nella chiusura della coda dopo la fine di execute, fuori dall’insieme dei task ancora posseduti dalla richiesta; il lock dell’agente restava occupato. Corretto RequestExecutor: il producer viene rimosso solo quando il task è effettivamente concluso, tramite callback. Test deterministico negativo prima della correzione e positivo dopo; nuova richiesta accettata senza ricreare l’agente. Dieci cicli consecutivi positivi della fixture nativa A2A/MCP nell’ambiente temporaneo, risposte modello controllate e nessuna rete esterna: prova del ciclo di vita, non campagna finale o conferma della demo distribuita.

Il driver salva ora verifiche/tracce già raccolte anche se si interrompe, con passed false e fase/categoria chiuse, senza testo di eccezioni o corpi HTTP. Suite completa **584 passed, 127 warning**; audit **1.005 controlli, zero problemi**. Nessun allungamento dei timeout, modifica all’SDK o riavvio dei servizi dell’utente. **Occorre ricostruire l’immagine, aggiornare i servizi e ripetere la conferma manuale**. Residui/protocollo aggiornati; S04 e campagna finale fermi.

## Modifica 72 — Pilota del tracciamento confermato

Controllato runs/trace_manual_retry.json: **62 controlli True, passed true e sei tracce valide, complete e non troncate**; ricalcolati dai singoli eventi tutti i riepiloghi, con corrispondenza. Confermati C001 completo, C006 parziale, timeout S-01 con esito parziale, annullamento senza report, recupero C001 e PDF rifiutato senza profilo. Un solo avvio gateway; il driver attesta stessi avvii degli agenti prima/dopo i guasti. Profili creati chiusi; token non disponibili in timeout/annullamento, metriche MCP e richieste host non disponibili se manca la ricevuta. I due dinieghi nell’annullamento derivano dalla revoca. Risposte modello controllate, nessuna misura reale Ollama/Internet o campagna finale.

Rifinita una sola diagnostica emersa dal file: HTTP 409 per dati insufficienti nella sottofase policy diventa input_not_ready, coerente col grafo, e indica lo scenario anche prima di creare il task. Verifica mirata su C001/C006/C011/C016: **4 passed, 13 warning**; evidenza manuale originale invariata, rifinitura inclusa alla prossima costruzione dell’immagine. Chiuso il pilota del blocco 1 e rimosso il relativo impedimento dal protocollo; restano registro delle istanze, manifest/runner/registro cieco e prove finali. S04 e campagna finale non autorizzati.

## Modifica 73 — Registro operativo V-01–V-10

Rilette Tabella 3.3 e §§4.4–4.6 della tesi. Creati REGISTRO_PROVE.md ed evaluation/test_registry.json: dieci famiglie, riuso dei 25 fascicoli e dieci cicli aggiuntivi con 29 varianti, ciascuna da ripetere dieci volte per cella. Distinti requisiti della tesi, proposte operative, piloti disponibili e preparazioni ancora mancanti. I cicli non equivalgono a singole sessioni; totali fisici e report da valutare restano da calcolare prima del congelamento. Esplicitati i limiti del corpus vincolato, dei timeout modello/fonte e dei driver demo rispetto alle quattro celle.

L’autore ha confermato per V-09 l’estensione reale degli agenti: entrambi consultano via MCP un riferimento numerico pubblico comune e restituiscono fonte/unità/periodo/prodotto; fixture dichiarate nei test e dati del fascicolo locali. Da fissare grandezza/ricevute e implementare il contratto; verificare la fedeltà prima di confrontare, senza promuovere valori alterati a conflitti verificati. Serviranno nuova versione runtime e nuovo pilota a quattro celle. Audit offline del registro **180 controlli, zero problemi**; audit complessivo **1.185 controlli, zero problemi**; verifiche dedicate **31 passed, 13 warning**. Nessun servizio avviato, nessuna prova operativa eseguita o risultato finale attribuito. Aggiornati protocollo, README e residui. S04 e campagna finale fermi; prossimo lavoro: contratto e implementazione dell’osservazione pubblica comune.

## Modifica 74 — Fonte e contratto pubblico comune fissati

Scelta la serie BCE MIR.M.IT.B.A2C.A.R.A.2250.EUR.N già prevista dal connettore, verificandone la definizione sul portale ufficiale: AAR/NDER aggregato dei nuovi mutui abitativi in Italia, percentuale annua e periodo mensile. Riusati EcbRateEvidence/Observation; adattatore con verifica del CSV e catalogo confronti 0.2.0. Valore e periodo provengono dalla fonte, non dal modello; il dato rimane distinto dal TAN del documento e dai riferimenti fiscali AdE già selezionati. Nessun nuovo provider o modello introdotto.

Verifiche mirate su fonte, contratto, confronti e registro: **93 passed, 13 warning**; audit registro **182 controlli, zero problemi**, protocollo **1.187 controlli, zero problemi**. Test offline sullo snapshot pubblico già acquisito: nessun nuovo recupero reale attestato. Fonte e contratto nominale definiti; **integrazione nei risultati di entrambi gli agenti ancora da realizzare**. Le future perturbazioni sono fixture esplicite, non dati attribuiti alla BCE. Aggiornati registro, protocollo e residui; campagna finale e S04 fermi.

## Modifica 75 — Piano di chiusura in quattro passi

Riorganizzato DA_IMPLEMENTARE.md: contributo utile degli LLM; integrazione e verifiche; demo/documento; valutazione riproducibile. Esplicitato il limite attuale: i modelli generano descrizioni delle fonti, ma la loro prosa non alimenta il report. Priorità proposta all’analisi contestuale dell’agente mercati, poi al fiscale, mantenendo calcoli e sicurezza applicativi e senza nuove infrastrutture. Conservati i residui V-01–V-10, il riferimento comune V-09, i piloti già confermati e le condizioni del confronto. Solo documentazione: nessuna funzionalità o prova aggiunta; dettagli del contratto LLM da concordare, S04 e campagna finale non autorizzati.

## Metodo da mantenere

Concordare i cambiamenti di perimetro e scrivere nella repository. Dettare i comandi in chat uno alla volta, con terminale, servizi e risultato atteso; l’utente esegue e l’assistente controlla anche i file prodotti. Registrare solo modifica, evidenza verificata e limite. Non trasformare prove previste in risultati, nascondere warning o sommare tempi annidati.

Avvio nel README; verifiche con pytest, piloti e script di controllo. I comandi precisi, anche Windows, vengono dettati in chat senza duplicarli nel diario. Il ponte usa un terminale separato.

**Ricerca ancora aperta:** baseline e quattro configurazioni, soglie/rubriche fissate prima dei test, dieci ripetizioni, giudizio umano e analisi privacy/utilità/costi. Nessun servizio reale nelle condizioni senza minimizzazione. Niente database dei profili, OCR, agenti remoti o benchmark integrali impliciti. S04 fermo fino all’ok dell’utente; nessun commit eseguito.
