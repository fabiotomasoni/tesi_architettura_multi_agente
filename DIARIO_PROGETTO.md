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

## Metodo da mantenere

Concordare i cambiamenti di perimetro e scrivere nella repository. Dettare i comandi in chat uno alla volta, con terminale, servizi e risultato atteso; l’utente esegue e l’assistente controlla anche i file prodotti. Registrare solo modifica, evidenza verificata e limite. Non trasformare prove previste in risultati, nascondere warning o sommare tempi annidati.

Avvio nel README; verifiche con pytest, piloti e script di controllo. I comandi precisi, anche Windows, vengono dettati in chat senza duplicarli nel diario. Il ponte usa un terminale separato.

**Ricerca ancora aperta:** baseline e quattro configurazioni, soglie/rubriche fissate prima dei test, dieci ripetizioni, giudizio umano e analisi privacy/utilità/costi. Nessun servizio reale nelle condizioni senza minimizzazione. Niente database dei profili, OCR, agenti remoti o benchmark integrali impliciti. S04 fermo fino all’ok dell’utente; nessun commit eseguito.
