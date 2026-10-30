# Diario di progetto

Il diario registra decisioni, implementazione, problemi e verifiche del prototipo. Gli step sono numerati senza date. Le prove automatiche sono distinte dalle esecuzioni reali dell'autore; funzionalità previste e proprietà non verificate non sono presentate come risultati acquisiti.

## Step 01 — Gateway locale e contratti JSON

### Obiettivo e decisioni

Realizzare il primo componente dei capitoli 3–4 della tesi, temporaneamente senza PDF. Scelti Python, FastAPI e Pydantic; nomi del codice in inglese, documentazione e messaggi in italiano. Installazione documentata per macOS e Windows PowerShell, usando direttamente il Python virtuale per evitare problemi di attivazione.

Sessioni in memoria, UUID opachi, un solo worker e nessun database dei profili. Ogni fatto comprende valore, unità, periodo, provenienza e stato. Schemi chiusi rifiutano campi sconosciuti; gli errori di schema non riflettono il corpo della richiesta. Nell'ingresso JSON lo stato validated è dichiarato dal chiamante, non verificato contro un documento.

Policy 0.1.0 con viste per attività/destinatario. Le viste non includono importi esatti. Durate generalizzate in fasce di cinque anni, limite inferiore escluso e superiore incluso. Dati insufficienti bloccano lo scenario interessato. Chiusura con DELETE, svuotamento all'arresto ordinato e TTL di 30 minuti applicato in modo pigro al successivo accesso/creazione.

### Test e risultati

**11 test automatici superati**: viste S-01/S-02, campi mancanti o ambigui, unità e periodi, valori negativi/frazionari, destinatari errati, scenari non richiesti, assenza di identificativi riflessi negli errori, cancellazione e scadenza. Risultato: il gateway applica i controlli previsti dal contratto JSON.

### Problemi risolti

Creato ambiente virtuale isolato per installare le dipendenze. L'esportazione delle dipendenze con pip freeze incontrava la repository senza commit: requirements-lock.txt è stato generato dai metadati installati, escludendo progetto e strumenti di installazione. Conservato l'avviso TestClient/httpx per migrazione futura, senza nasconderlo.

## Step 02 — Ingresso PDF e interfaccia locale

### Implementazione

Aggiunti caricamento multiplo dal browser e parser pypdf per i prospetti sintetici del dataset. Il parser legge esclusivamente i PDF caricati, senza consultare ground_truth o generatore. Estrae numeri italiani in Decimal, mantiene documento/pagina e non ricostruisce dati mancanti. Usa transitoriamente l'IBAN fittizio per verificare l'appartenenza allo stesso fascicolo, senza inserirlo nel profilo restituito.

Riconosciuti mutuo, certificazione interessi, conto e paga. Solo i primi due alimentano gli scenari attuali. La certificazione annuale mantiene il proprio anno d'imposta: un mutuo 2025 e interessi 2024 non sono automaticamente discordanti. Tipologia non esplicitata e ristrutturazione restano attualmente mappate a other, con perdita di specificità dichiarata.

Limiti: quattro file per caricamento, 5 MiB per file, 20 pagine per documento. File cifrati, senza testo, corrotti, duplicati o di fascicoli diversi sono rifiutati. Un rifiuto interrompe l'intero caricamento; recupero dei file validi ancora da sviluppare.

### Test e risultati

**37 test automatici superati**, inclusi i precedenti 11 e l'elaborazione dei 25 fascicoli sintetici, 100 PDF. Verificati scenari completi, capitale/interessi mancanti, tasso ambiguo, periodi diversi, assenza dell'anagrafica nei risultati, duplicati, documenti misti, input non PDF e disponibilità della pagina HTML.

L'autore ha inoltre provato il caricamento dal browser di C025 e C024: profilo e viste prodotti, fasce di durata coerenti, importi esatti esclusi dalle viste. Si tratta di prove sul template sintetico, non su documenti bancari generici.

## Step 03 — Ordine della repository e documentazione

Rinominata con autorizzazione la cartella del dataset in dataset. Controllate radice e sottocartelle gateway/static, tests, examples, dataset/Documents, dataset/Scripts, ambienti annidati e stato del generatore.

.gitignore esclude ambienti, cache, prodotti Python, temporanei, file di sistema/editor, segreti, stato API, budget, annotazioni del valutatore e anteprime. Codice, test, PDF sintetici, esempi, requisiti e .env.example restano versionabili. Nessun materiale dell'autore eliminato. Esclusioni verificate con git check-ignore.

README ripulito da percorsi personali e informazioni del computer. Il diario usa soltanto numeri degli step. L'ambiente del generatore precedentemente spostato può richiedere ricreazione: gli ambienti virtuali non sono generalmente relocabili.

## Step 04 — Agente mercati ADK con A2A, MCP e Ollama

### Scelte e implementazione

Realizzato un solo specialista, lasciando LangGraph e agente fiscale agli incrementi successivi. Contratti MarketTask/MarketView/MarketResult con correlazione, scenario, scopo, scadenza con fuso orario, versione policy, esito e provenienza obbligatoria per completamento.

Il gateway verifica nome, endpoint, versione, skill e streaming della Card locale prima della delega; valida il risultato e la correlazione. Il client non segue redirect né proxy d'ambiente. È un controllo di configurazione, non autenticazione crittografica.

Agente custom ADK BaseAgent esposto tramite to_a2a. Pipeline programmata: MCP stdio reale, quindi sintesi tramite Ollama locale llama3.2:3b. A2A SDK 0.3.x è coerente con la specifica richiamata nella tesi. ADK 1.39.1 segnala sperimentale il proprio adattatore A2A; non occorrono chiavi cloud.

Fixture simulated-rates-v1: 3.20% fisso, 3.60% variabile, 3.40% misto; riferimento sintetico 2025-12-31. Il valore dipende solo dal tipo di tasso. Fascia e tipologia non lo modificano. Non sono quotazioni reali o offerte confrontabili con il contratto.

Ollama riceve soltanto l'evidenza simulata, con contesto 4096, massimo 200 token generati, temperatura zero e keep_alive=0. La sintesi è distinta dalla fonte e dichiarata non verificata. Nessun confronto economico personalizzato.

Richieste serializzate; sessioni ADK e task A2A cancellati dopo la risposta. Il gateway mantiene la propria sessione fino a DELETE/TTL. Nessuna cronologia o continuazione multi-turno.

### Test e risultati

**42 test automatici superati**: contratti contro campi extra, provenienza obbligatoria, fixture, incarico scaduto e risposta A2A con cancellazione dello stato. pip check senza incompatibilità.

Prova reale integrata con C025: PDF → gateway → A2A → ADK → MCP → Ollama, esito completed. L'autore ha verificato C024: vista variabile, fascia oltre 20 fino a 25 anni, risultato sintetico 3.60%, provenienza esplicita e sintesi in italiano.

## Step 05 — Misure, controlli negativi e pilota nominale

### Strumentazione

Misurati preparazione vista, verifica Card, round trip A2A, MCP e Ollama, caricamento modello, richieste applicative e token. MCP include avvio processo, inizializzazione e chiusura. I tempi sono annidati: non vanno sommati. I conteggi non rappresentano tutti i messaggi di basso livello.

scripts/run_pilot.py apre sessioni indipendenti e verifica DELETE seguito da 404. Esporta in append JSONL in runs/, escluso da Git, senza profili, prompt o sintesi. Registra ambiente, stato Git, esiti e misure. Le sottofasi non completate non ricevono valori inventati.

### Test automatici

**48 test superati**. Aggiunti controlli: C006/C016 non invocano la delega; Card alterata rifiutata prima dell'invio; fonte assente e correlazione errata rifiutate; MCP reale con Ollama sostituito per verificare che il payload contenga soltanto l'evidenza simulata. Questi test controllati non dimostrano isolamento o assenza di ogni possibile divulgazione.

### Pilota eseguito dall'autore

Esaminati i 12 record forniti: tre ripetizioni per caso, tutte con passed=true e cleanup_verified=true.

| Caso | Condizione | Esecuzioni | Risultato osservato |
|---|---|---:|---|
| C001 | Completo, fisso | 3 | HTTP 200, completed |
| C024 | Completo, variabile | 3 | HTTP 200, completed |
| C006 | Capitale mancante | 3 | HTTP 409, blocked |
| C016 | Tasso ambiguo | 3 | HTTP 409, blocked |

| Caso | Media gateway_total_ms | Varianza campionaria ms² |
|---|---:|---:|
| C001 | 1676.375 | 2.738 |
| C024 | 1687.004 | 28.460 |

Nei sei successi: MCP circa 211–233 ms, Ollama 1430–1448 ms, caricamento modello 555–560 ms, 119 token input e 46 output per esecuzione. keep_alive=0 comporta caricamenti ripetuti: non sono prove separate a caldo. Le 12 verifiche di cancellazione riguardano il gateway.

L'autore ha ripetuto la suite: 48 passed, 12 warning. Gli avvisi ADK sperimentale e TestClient/httpx non sono errori di test; restano da monitorare.

## Step 06 — Guasti e timeout durante MCP

### Guasti eseguiti dall'autore

| Condizione | Esito osservato | Pulizia gateway |
|---|---|---|
| Agente spento | HTTP 502, error | Verificata |
| Ollama spento | HTTP 200, failed | Verificata |

Gli esiti sono quelli attesi. HTTP 200 con failed significa consegna di un risultato di attività fallita, non successo dell'analisi. Per questa raccolta i guasti sono documentati dall'output comunicato dall'autore.

Il runner è stato esteso con --expect agent-off, ollama-off e timeout: passed confronta con il guasto atteso. I vecchi passed=false delle prove negative effettuate in modalità nominale non invalidano il comportamento osservato.

### Fixture timeout

Aggiunti error_code timeout/execution_failed. slow_rates_mcp attende 10 s; timeout_agent usa un budget di 2 s. Fixture separata dal servizio nominale e non selezionabile attraverso il payload utente. Ollama non viene raggiunto quando il timeout interrompe MCP.

**49 test automatici superati**: il nuovo test effettua MCP stdio reale, ottiene timeout senza evidenza e controlla store ADK/A2A vuoti. Finestra tecnica del test: 1.8–8 s, non SLA. Registrati 19 warning di libreria.

### Prova reale eseguita dall'autore

Esaminato runs/timeout.jsonl: tre richieste C001, tutte HTTP 200, failed, error_code=timeout, passed=true e cleanup_verified=true. gateway_total_ms: 2085.821, 2083.888, 2075.767. Il servizio risponde in circa 2.08 s anziché attendere i 10 s della fixture.

Risultato: il timeout durante MCP è gestito e restituito in modo strutturato. I file non contengono una verifica indipendente della terminazione del processo MCP; la pulizia degli store ADK/A2A è coperta dal test automatico.

## Step 07 — Ripristino dopo sostituzione dell'agente

Fermata la fixture timeout e avviato l'agente nominale. Esaminato runs/recovery.jsonl: C001 HTTP 200 completed, error_code=null, passed=true, cleanup_verified=true; gateway_total_ms 1691.280, una chiamata MCP, una Ollama, 119 token input e 46 output.

Risultato positivo: il percorso nominale funziona dopo il ripristino della configurazione. Questa prova richiede un riavvio e non dimostra da sola disponibilità nello stesso processo dopo timeout. Da questa distinzione deriva lo step successivo.

## Step 08 — Recupero nello stesso processo senza riavvio

### Fixture e controllo automatico

services.recovery_agent rende lenta solo la prima richiesta; le successive seguono la pipeline nominale. Il contatore è locale alla fixture. Ogni risposta include agent_boot_id opaco, costante per l'avvio del modulo agente. scripts/check_recovery.py confronta gli ultimi record dedicati.

**50 test automatici superati**. Il nuovo test usa lavorazione controllata: timeout, seconda richiesta completata, stesso identificativo d'avvio e store ADK/A2A vuoti dopo entrambe. Il timeout MCP reale è verificato separatamente nello step 06. Registrati 26 warning, senza fallimenti.

### Prova reale eseguita dall'autore e file verificati

Avviata una sola istanza recovery_agent, senza riavvii tra le due richieste. Esaminati direttamente runs/same_process_timeout.jsonl e runs/same_process_recovery.jsonl.

| Richiesta | HTTP | Stato | error_code | gateway_total_ms | passed | Pulizia gateway |
|---|---:|---|---|---:|---|---|
| Prima, MCP lento | 200 | failed | timeout | 2089.572 | true | Verificata |
| Seconda, nominale | 200 | completed | null | 1666.243 | true | Verificata |

Lo stesso agent_boot_id è presente in entrambi i record. Nel recupero: MCP 207.769 ms, Ollama 1450.864 ms, caricamento modello 558.595 ms, 119 token input e 46 output.

L'autore ha eseguito check_recovery.py ottenendo tutti i controlli positivi:

- timeout_atteso: True;
- recupero_completato: True;
- stesso_avvio_agente: True;
- sessioni_gateway_cancellate: True.

**Conclusione verificata:** dopo il timeout di un'attività, lo stesso processo agente rimane disponibile e completa una nuova richiesta indipendente senza riavvio. Non è una ripresa dello stesso task e non implica retry automatici.

### Comandi per ripetere la sequenza

Dalla radice della repository, avviare Ollama e gateway; fermare qualsiasi agente già sulla porta 8001. In un terminale dedicato:

```bash
.venv/bin/python -m uvicorn services.recovery_agent:app --host 127.0.0.1 --port 8001 --no-access-log
```

In un altro terminale, senza richieste dal browser e senza riavvii fra i comandi:

```bash
.venv/bin/python scripts/run_pilot.py --cases C001 --expect timeout --output runs/same_process_timeout.jsonl
.venv/bin/python scripts/run_pilot.py --cases C001 --output runs/same_process_recovery.jsonl
.venv/bin/python scripts/check_recovery.py
```

Per Windows PowerShell sostituire `.venv/bin/python` con `.\.venv\Scripts\python.exe`. Per ripetere la sequenza completa riavviare la fixture prima della prima richiesta. I file sono in append; il controllo usa gli ultimi record. Al termine fermare la fixture e tornare a services.market_agent:app.

## Step 09 — Consolidamento delle evidenze

Diario riscritto per raccogliere risultati acquisiti, motivazioni e limiti, aggiornando lo stato delle prove ora completate. Nessuna modifica al codice applicativo in questo step. Nessun commit creato automaticamente.

### Risultati acquisiti e collegamento alla tesi

- Ingresso, estrazione controllata e blocco di dati insufficienti: parti di RF-01/RF-02 e V-01/V-03.
- Viste minimizzate e controllo dei payload nel percorso implementato: parti di RF-03 e V-02, senza dimostrare l'intero confine di sicurezza.
- Delega A2A, strumento MCP e provenienza: parti di RF-04–RF-06, RQ1 e V-08/V-10.
- Guasti, timeout e nuova richiesta dopo timeout: parti di RF-09, RNF-04 e V-04.
- Tempi, token e conteggi: prima strumentazione di RF-10/RNF-06 e RQ3.

### Limiti ancora aperti

Parser limitato al template sintetico; niente OCR, coordinate/span o autenticità documentale. Generalizzazione della categoria other da migliorare. Nessun recupero parziale dei PDF validi in un caricamento rifiutato. Upload multipart può usare temporanei; limiti applicativi non proteggono da soli da body grandi. TTL pigro e DELETE non garantiscono azzeramento fisico di RAM/swap.

Non ancora verificati timeout durante Ollama, annullamento, isolamento di rete, autenticazione e sicurezza contro contenuti ostili. Mancano proxy completo, LangGraph, agente fiscale, fonti reali, calcoli personalizzati, report finale e finalizzazione globale. Le misure sono locali e annidate; quelle prodotte dal servizio non sono una certificazione indipendente.

Le evidenze raccolte sono prove pilota. Non dimostrano vantaggi del multi-agente né il confronto fattoriale 2×2. I record indicano working_tree_dirty=true: il commit registrato non basta a ricostruire lo stato eseguito; conservare una revisione stabile prima della campagna finale e identificare il modello anche tramite digest. Windows è documentato ma non verificato con esecuzione reale in questa raccolta.

## Step 10 — Revisione della tesi e allineamento del prototipo

### Riferimento e metodo

Riletto il testo completo dei capitoli 1–4, dei capitoli 5–6 ancora non sviluppati e dei riferimenti della tesi; confrontati requisiti con parser, policy, API, contratti, adattatore A2A, servizi, script e test. La revisione riguarda contenuto e codice; non verifica la fedeltà grafica dei diagrammi incorporati. Nessuna modifica al documento di tesi o ai risultati storici del pilota.

### Correzioni applicate

- RF-01 e scenario alternativo della sezione 3.2: un PDF rifiutato non annulla più i documenti validi sufficienti. Prevalidazione per file, esclusione degli input rifiutati, elenco rejected_documents con posizione nell'upload e motivo senza nome del file. Se tutti sono rifiutati: HTTP 400. Documenti validi di fascicoli diversi e duplicati continuano a bloccare l'aggregazione; limiti di dimensione restano bloccanti.
- Il parser viene eseguito una volta per prevalidare e nuovamente per aggregare i validi: costo aggiuntivo esplicito da considerare nei successivi esperimenti, non ottimizzazione prestazionale.
- Robustezza RF-02: un anno d'imposta testuale NaN viene segnalato come non valido senza provocare un errore nella verifica del periodo. Non viene usato nei calcoli.
- README aggiornato con il nuovo comportamento e mantenuti i limiti non risolti.

### Verifiche

52 test superati, 26 warning di libreria. Due nuovi casi: PDF non valido insieme a mutuo valido, con S-01 utilizzabile e S-02 insufficiente; anno non finito rifiutato senza errore applicativo. Restano superati tutti i test precedenti, compresi i 25 fascicoli e il timeout MCP. Le precedenti misure di latenza non vengono ricalcolate o attribuite a questa revisione.

### Stato dei requisiti dopo la revisione

| Requisito | Stato effettivo | Lavoro residuo |
|---|---|---|
| RF-01 | Ingresso PDF del template e recupero dei validi | Altri layout nativi e fixture scansione/cifratura/corruzione |
| RF-02 | Estrazione locale, unità e periodi, documento/pagina | Porzione di testo, distinzione estratto/derivato/non specificato |
| RF-03, RNF-01 | Viste chiuse e minimizzazione nel percorso locale | Proxy, controllo dei payload esterni, PII e quasi-identificatori |
| RF-04 | Delega A2A al solo specialista mercati | Pianificazione LangGraph, fiscale e parallelismo |
| RF-05 | MCP reale con una fixture locale | Catalogo configurabile e traccia strumento/categorie/esito/correlazione |
| RF-06 | Risultato strutturato e rifiuto se fonte obbligatoria assente | Stato esplicito non verificato e propagazione dei limiti al report |
| RF-07 | Coerenza di unità e periodi del profilo | Catalogo confronti/tolleranze e discordanza agente–documento |
| RF-08, RNF-07 | Sintesi del solo dato simulato, dichiarata non verificata | Report locale completo con dati, fonti, inferenze e limiti |
| RF-09, RNF-04 | Guasto, timeout MCP e disponibilità dopo timeout verificati | Report parziale, annullamento e timeout Ollama |
| RF-10, RNF-06 | Tempi e conteggi nel pilota | Tracce correlate complete, budget configurabili e costi di policy |
| RNF-02, sezione 4.4 | Chiusura manuale/TTL gateway; cleanup ADK/A2A | Finalizzazione comune automatica su tutti i percorsi e recupero dopo crash |
| RNF-03, sezione 4.5 | Schemi e Card controllati | Autenticazione e isolamento host/container; blocco uscite dirette |
| RNF-05, V-06 | Contratti presenti | Prova di sostituzione agente/tool tramite configurazione |
| RNF-08, sezione 4.6 | Dataset sintetico e pilota | Fatti annotati, rubriche, quattro condizioni comparabili, dieci ripetizioni |

### Scelte da concordare e prossimo incremento proposto

Non alterate automaticamente le categorie other: il parser assegna una categoria generica al tipo mutuo non esplicitato e generalizza ristrutturazione. Prima della ricerca fiscale occorre distinguere informazioni non specificate da finalità documentate, concordando catalogo e versione della policy, senza inventare campi o modificare il dataset retroattivamente.

Prossimo incremento proposto: orchestratore LangGraph per il solo S-01, con validazione, richiesta vista al gateway, delega A2A, verifica risultato e uscita strutturata. Mantenere policy nel gateway e non nei nodi del grafo; definire finalizzazione automatica della sessione per successo, dati insufficienti ed errore. Misurare estrazione/pianificazione/delega/controllo/pulizia senza sommare tempi annidati. Report personalizzato, secondo specialista e uscite reali restano incrementi successivi. Prima di fonti o inferenza remote rendere operativo il proxy e verificare l'isolamento. Nessuna di queste estensioni è dichiarata implementata in questo step.

## Step 11 — Orchestrazione LangGraph S-01

### Implementazione

Autorizzata l'introduzione di LangGraph. Aggiunto gateway/workflow.py con StateGraph asincrono, transizioni condizionali, richiesta vista al gateway, delega A2A e verifica di schema/correlazione/esito. Il grafo coordina il flusso, non usa un ulteriore LLM. Policy, controllo Card e adattatore A2A restano nel gateway. S-02 e report personalizzato rimangono fuori da questo incremento.

Stato in memoria con solo incarico minimizzato e risultato, senza checkpointer o persistenza. Tracciamento LangSmith esplicitamente disabilitato nel contesto dell'invocazione. Finalizzazione in finally con rimozione sessione gateway anche in caso di errore o cancellazione del task; durata cleanup misurata. La chiusura precede il ritorno della risposta e non dipende dal browser. Non equivale a recupero dopo crash dell'host né alla cancellazione certa di una richiesta A2A già in elaborazione.

Nuovo endpoint /sessions/{id}/workflow e pulsante dedicato; percorso diretto /markets preservato. Il workflow restituisce HTTP 200 con status completed/blocked/failed; payload inesistenti o richieste invalide restano errori HTTP. Sessione consumata a fine workflow. Script pilota esteso con --workflow, fasi, versione LangGraph e verifica di cancellazione automatica (DELETE deve dare 404, senza essere la causa della cancellazione).

### Verifiche e problemi risolti

58 test automatici superati, 38 avvisi di libreria; pip check senza dipendenze incompatibili. Sei nuovi casi: successo, attività fallita, eccezione della delega, risultato con correlazione errata, dati insufficienti senza invio A2A, cancellazione del task esterno. Tutti verificano finalizzazione. L'iniziale test che sollevava CancelledError direttamente dal nodo era trasformato da LangGraph in NodeCancelledError: sostituito con cancellazione effettiva del task chiamante, per controllare il percorso corretto.

Prova gateway in processo con servizio A2A non disponibile: failed e sessione assente dopo il workflow. Nessuna esportazione di profili o prompt introdotta. La verifica automatica usa delega controllata; non va confusa con una campagna finale con modelli reali.

### Prova da eseguire dall'autore

Aggiornare dipendenze, riavviare gateway e agente, mantenere Ollama aperto. Eseguire run_pilot.py --workflow --repetitions 3 --output runs/langgraph_pilot.jsonl con Python dell'ambiente virtuale. Attesi 12 esiti, sei completed e sei blocked, sessione chiusa automaticamente in tutti. Registrare i file prima di dichiarare eseguito il pilota LangGraph dell'autore. Ripetere poi guasti e timeout con --workflow; il risultato è ora strutturato HTTP 200 anche quando l'attività fallisce. Non modificati retroattivamente i risultati dei piloti precedenti.

Verificata anche una richiesta reale con PDF C001, servizio ADK/A2A avviato, MCP stdio e Ollama: completed, error_code assente, session_closed=true e successivo DELETE 404. Il servizio avviato per la verifica è stato fermato al termine.

## Step 12 — Pilota LangGraph eseguito dall'autore

Verificati direttamente i 12 record della raccolta runs/langgraph_pilot.jsonl: LangGraph 1.2.18, workflow S-01-langgraph-v1. Tutti riportano passed=true, automatic_session_closed=true e cleanup_verified=true.

| Caso | Ripetizioni | Esito | Fasi osservate |
|---|---:|---|---|
| C001 | 3 | HTTP 200 completed | request_view, delegate_a2a, verify_result, cleanup |
| C024 | 3 | HTTP 200 completed | request_view, delegate_a2a, verify_result, cleanup |
| C006 | 3 | HTTP 200 blocked | request_view, cleanup |
| C016 | 3 | HTTP 200 blocked | request_view, cleanup |

Il grafo completa i casi sufficienti e interrompe quelli con capitale mancante o tasso ambiguo prima del nodo di delega. La sessione gateway risulta già assente prima che il runner provi a cancellarla: verificata finalizzazione automatica, non soltanto cancellazione manuale a fine test. La pulizia interna ADK/A2A rimane coperta dai test automatici separati.

HTTP 200 blocked è l'esito strutturato previsto dal workflow; il percorso diretto storico resta diverso (HTTP 409). Nessuna correzione richiesta dai risultati. Non si attribuisce a LangGraph un overhead confrontando direttamente questi tempi con il pilota precedente: caricamento modello e condizioni non sono controllati in modo sufficiente. Persistono le limitazioni di campione pilota e working_tree_dirty=true.

Prossima verifica proposta: ripetere indisponibilità agente, Ollama e timeout tramite --workflow per controllare finalizzazione del grafo nelle prove reali negative. Non ancora dichiarate eseguite dall'autore per questo nuovo percorso.

## Step 13 — Guasti reali e timeout nel workflow LangGraph

Controllati direttamente i file langgraph_agent_off.jsonl, langgraph_ollama_off.jsonl, langgraph_timeout.jsonl e langgraph_recovery.jsonl in runs/. Tutti i sette record presenti hanno passed=true, automatic_session_closed=true e cleanup_verified=true. Il file Ollama spento contiene due esecuzioni in append, entrambe valide; non sono state eliminate o confuse con un'unica prova.

| Condizione | Record presenti | Stato | Codice | Percorso |
|---|---:|---|---|---|
| Agente spento | 1 | failed | delegation_failed | request_view → delegate_a2a fallita → cleanup |
| Ollama spento | 2 | failed | execution_failed | request_view → delegate_a2a → verify_result → cleanup |
| MCP lento | 3 | failed | timeout | request_view → delegate_a2a → verify_result → cleanup |
| Ripristino nominale | 1 | completed | null | request_view → delegate_a2a → verify_result → cleanup |

Tutte le risposte HTTP sono 200, coerentemente con il contratto di esito strutturato del workflow. Su errore Ollama e timeout MCP la delega è completed perché il servizio A2A ha restituito correttamente un risultato di attività fallita; verify_result completed significa che tale risultato ha superato i controlli, non che l'analisi sia riuscita. Agente spento impedisce invece lo scambio e salta la verifica del risultato.

Timeout osservati nella fase delega: 2083.905, 2082.324 e 2081.726 ms, coerenti con la fixture a budget 2 s. Ripristino nominale: una chiamata MCP, una Ollama, 119 token input e 46 output. Identificativi d'avvio diversi tra fixture e ripristino: questa raccolta verifica recupero dopo cambio di servizio; la verifica senza riavvio resta quella acquisita nello Step 08.

Conclusione: il workflow gestisce le condizioni negative provate e finalizza automaticamente la sessione gateway. Nessuna correzione al codice richiesta da questi esiti. Non sono dimostrati timeout durante Ollama o finalizzazione dopo crash dell'host. Nessun commit creato automaticamente.
