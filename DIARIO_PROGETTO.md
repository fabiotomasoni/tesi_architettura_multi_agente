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

## Step 14 — Agente fiscale e coordinamento dei due specialisti

### Decisioni e implementazione

Autorizzato il secondo specialista e il coordinamento delle attività richieste. Policy portata a 0.2.0 per mantenere ristrutturazione come renovation; nessuna modifica ai PDF o ai risultati pregressi. Il tipo mutuo generico other non è stato modificato in questo step.

Aggiunti TaxView/TaxTask/TaxEvidence/TaxResult: solo anno, categoria e finalità nella vista, correlazione/scadenza/versione nell'incarico, fonte simulata e limiti nel risultato. Agente fiscale custom ADK esposto A2A sulla porta 8002, tool MCP lookup_tax e Ollama qwen3:1.7b. Fixture simulated-tax-v1 con riferimento DEMO-TAX-001: contenuto inventato, nessuna legge, aliquota o spettanza reale. Thinking disabilitato, contesto 4096, massimo 200 token generati e keep_alive=0. Sintesi non verificata, separata dall'evidenza.

Client fiscale verifica Card, correlazione e corrispondenza di anno/finalità. Cleanup ADK/A2A analogo al servizio mercati. Nuovo endpoint /analysis: solo scenari selezionati, subgrafi LangGraph asincroni concorrenti con TaskGroup, aggregazione completed/partial/blocked/failed e finalizzazione unica gateway in finally. I subgrafi non possiedono la sessione e non dichiarano una propria cancellazione. Nessun checkpointer o traccia LangSmith esportata. Il risultato è aggregazione strutturata, non report o consiglio finanziario.

UI aggiornata al coordinatore; API S-01 precedente conservata. Aggiunto scripts/run_multi_pilot.py per selezione scenari, casi sufficienti/incompleti e pulizia automatica. Il runner storico ora registra la versione policy effettiva dell'upload. Le versioni 0.1.0 delle evidenze storiche non vengono riscritte.

### Verifiche eseguite

69 test automatici superati, 49 warning di libreria; pip check senza incompatibilità. Nuovi casi: due scenari completi; solo mercati; solo fiscale; C006 capitale mancante, C011 interessi mancanti, C016 tasso ambiguo con esito partial e chiamata del solo specialista ammesso; indisponibilità di un ramo con conservazione dell'altro; rifiuto importi esatti nel contratto fiscale; finalità renovation conservata dal PDF; risposta fiscale A2A con store svuotati. Test di concorrenza con barriera: entrambi i rami entrano prima di procedere, poi timeout fiscale con mercato conservato e cleanup unico. Il test A2A usa lavorazione sostituita, non Ollama reale.

L'avvio dei servizi sulle porte 8001/8002 per la nuova prova reale è stato impedito dall'ambiente (operation not permitted). Nessuna nuova esecuzione reale con due modelli è dichiarata superata. Procedura nel README: pilota con 15 record attesi, sei completed e nove partial; prove di selezione e guasto fiscale da eseguire dall'autore.

### Limiti e lavoro successivo

I modelli locali possono essere accodati da Ollama secondo memoria e configurazione: parallelismo dei rami non garantisce inferenza GPU simultanea o vantaggio prestazionale. Fonte fiscale solo inventata: non valuta correttezza normativa. Moduli fiscali riprendono la struttura del primo specialista; estrazione di helper condivisi possibile dopo verifica del pilota. Mancano ancora report, calcoli locali, proxy/isolamento, prove fiscali avversarie/timeout dedicate, controllo conflitti e valutazione 2×2. Il nuovo runner raccoglie risultati funzionali ma non ancora tutti i metadati necessari alla riproducibilità della campagna finale.

## Step 15 — Pilota reale dei due specialisti

Esaminati gli ultimi 15 record di runs/multi_pilot.jsonl, policy 0.2.0. Tutti passed=true, automatic_session_closed=true e cleanup_verified=true.

| Caso | Ripetizioni | Mercati S-01 | Fiscale S-02 | Esito aggregato |
|---|---:|---|---|---|
| C001 | 3 | completed | completed | completed |
| C024 | 3 | completed | completed | completed |
| C006 | 3 | blocked/input_not_ready | completed | partial |
| C011 | 3 | completed | blocked/input_not_ready | partial |
| C016 | 3 | blocked/input_not_ready | completed | partial |

Ogni attività completata riporta una richiesta A2A e una chiamata Ollama. Nei rami bloccati questi conteggi sono assenti, non valori zero misurati; i test automatici verificano separatamente il mancato invio della delega. Nessuna attività completata presenta error_code. Confermati sei esiti completi, nove parziali e pulizia automatica gateway per tutte le esecuzioni.

Risultato acquisito: due specialisti locali reali completano le attività sufficienti e l'aggregazione conserva il risultato utilizzabile quando l'altro scenario è insufficiente. I record non dimostrano inferenza simultanea GPU, correttezza normativa delle fonti simulate o eliminazione di ogni rischio di privacy. Il runner resta funzionale e non registra tutti i metadati della campagna finale.

Prossime prove suggerite: richiesta di ciascun solo scenario e guasto di un agente con l'altro disponibile. Sono controlli distinti dal blocco per dati insufficienti e, per il nuovo coordinatore, non ancora eseguiti dall'autore in questa raccolta. Nessuna modifica al codice richiesta dagli esiti nominali verificati.

## Step 16 — Selezione, guasto parziale e primo report locale RF-08

### Evidenze verificate

Letto runs/only_markets.jsonl: C001, soltanto S-01, completed, passed=true, chiusura automatica e pulizia verificate. Letto runs/multi_tax_off.jsonl: C001 con due scenari, mercati completed e fiscale failed/delegation_failed, totale partial, chiusura e pulizia vere. passed=false è atteso nel confronto nominale del runner. runs/only_tax.jsonl non presente: prova reale di sola selezione fiscale non dichiarata eseguita; selezione coperta dal test automatico.

### Implementazione

Aggiunto gateway/report.py, composizione deterministica locale su profilo ed esiti già verificati. Sezioni distinte: fatti documentali per scenario richiesto con unità/periodo/provenienza/stato, fonti simulate con schema/provenienza controllati ma non verificate nel mondo reale, sintesi non verificate con modello, esiti tecnici e limiti. Mancanti/ambigui non sono stimati; i fallimenti non generano fonti né sintesi presentate come valide. Nessuna ulteriore inferenza e nessun calcolo finanziario o fiscale.

Composizione dopo aggregazione e prima della finalizzazione; cleanup in finally anche se la composizione fallisce. Misurato report_ms. Lo snapshot locale del profilo resta nella richiesta solo fino al ritorno della risposta; nessun database o file report automatico. Il client riceve il report e può esportarlo esplicitamente come JSON; la copia contiene valori esatti e non è una traccia tecnica. Nuovo caricamento pulisce il report precedente dalla pagina.

La pagina mostra sezioni separate tramite textContent, senza interpretare sintesi come HTML. Lo script multi pilota registra presenza e tempo del report, senza salvarne contenuto, profilo o sintesi nei log sperimentali.

### Verifiche eseguite

73 test automatici superati, 49 warning noti di libreria. Quattro nuovi casi: separazione fatti/fonti/sintesi, campo obbligatorio mancante senza fonte inventata, report prodotto via API con successiva sessione assente, cleanup anche se il generatore del report solleva errore. Restano superati i casi multi-agente parziali e di selezione. Test con servizi sostituiti: nessuna nuova esecuzione reale del report con entrambi i modelli ancora dichiarata; verifica visiva browser da eseguire dall'autore.

### Prove manuali proposte

Riavviare gateway, mantenere Ollama e i due agenti attivi. C001: report completo dei due esiti tecnici; verificare i cinque gruppi e nessuna conclusione personalizzata. C006: report partial, capitale missing, nessuna fonte mercati, fonte fiscale presente. Agente fiscale spento con C001: report partial, fonte mercati conservata, motivo delegation_failed fiscale. Ripristinare il fiscale. Provare esportazione esplicita JSON e nuovo caricamento, senza pubblicare dati documentali non necessari. Facoltativo: run_multi_pilot.py con nuovo file output per report_present/report_ms.

### Limiti

RF-08 parzialmente realizzato: manca ancora la valutazione dei valori documentali rispetto al contesto e il report personalizzato. RF-07 sui conflitti non è dimostrato dalla semplice separazione delle fonti. Fonte simulata non è normativa o quotazione reale. Mancano riferimenti puntuali al testo, proxy/isolamento e valutazione qualità/utilità. I report possono includere dati sensibili locali: non copiarli nelle tracce tecniche e non conservarli implicitamente lato server.

## Step 17 — Fedeltà fiscale e verifica del contenuto delle fixture

### Problema osservato e perimetro confermato

Esaminati i due report esportati dall'autore: nel completo le sezioni sono correttamente distinte; nel parziale capitale missing, S-01 bloccato e fonte fiscale conservata. La sintesi fiscale libera del parziale contiene però l'affermazione non supportata “Non è attualmente soggetta a tasse”. Non è un difetto meramente stilistico: trasforma assenza di attestazione in conclusione fiscale. La precedente etichetta unverified non impediva l'esposizione al lettore. L'autore conferma di mantenere fonti simulate e consolidare prima la fedeltà.

### Correzione e garanzie circoscritte

Aggiunto catalogo fidato gateway/tax_evidence.py: contenuto esatto della fixture, contesto atteso dal profilo/incarico e digest canonico SHA-256. Verifica dopo MCP, client A2A gateway e composizione report: un ID corretto non basta se condizioni, riferimento, anno o finalità sono difformi. Nessuna nuova fonte normativa o chiamata Internet.

Report portato a 0.2.0. Sintesi fiscale deterministica estrattiva: ciascuna condizione copiata senza parafrasi, riferimento source_ref alla posizione, contesto e digest. Nessuna deduzione di diritto, esenzione o aliquota. Campo real_world_verified=false mantenuto. Il digest è identificazione contenuto, non firma o prova di autenticità normativa.

Prosa libera del modello fiscale esclusa dal report e sostituita nel riepilogo tecnico /analysis con un messaggio di esclusione. Il modello continua a essere invocato per continuità della pipeline; model_evaluation conserva hash e modello, senza testo o giudizio semantico automatico. La sintesi mercati rimane esplicitamente non verificata: la garanzia estrattiva riguarda solo la parte fiscale. Nessun aggiornamento retroattivo dei report precedenti.

### Verifiche

82 test superati prima del mascheramento aggiuntivo del riepilogo tecnico; suite completa rieseguita dopo la modifica. Nove nuovi casi: rifiuto anno, finalità, riferimento, ID, conclusione aggiunta o istruzione ostile nella fixture; corrispondenza esatta delle frasi con le condizioni e riferimenti; regressione sulla frase fiscale errata, assente dal report; riverifica del contenuto al report senza fidarsi dell'esito dell'agente. I test non dimostrano fedeltà semantica universale di un LLM: eliminano la parafrasi libera dal contenuto fiscale presentato.

### Prossima prova manuale

Riavviare fiscale e gateway, ripetere C001/C006 ed esportare nuovi report 0.2.0. Verificare faithful_summaries con riferimenti, unverified_summaries privo di S-02, model_evaluation senza prosa, fonte ancora simulata. Questa nuova esecuzione reale non è ancora dichiarata svolta dall'autore. Prima di fonti reali occorrono verifica istituzionale, validità temporale e ambito, oltre al proxy/isolamento della tesi. Il sistema non promette fedeltà al diritto reale usando fixture inventate.

## Step 18 — Verifica reale dei report fiscali fedeli alla fixture

Esaminati i due nuovi report esportati dall'autore, entrambi report_version 0.2.0. Il primo è completed con entrambi gli scenari; il secondo è partial, S-01 blocked/input_not_ready e S-02 completed.

Ricalcolata per ciascuno la sintesi attesa con il catalogo fiscale fidato: corrispondenza esatta con faithful_summaries, condizioni e riferimenti di origine corretti e digest della fonte coincidente. Contesti mantenuti: anno 2025 con primary_home_purchase nel completo e renovation nel parziale. real_world_verified=false in entrambi.

Nessuna prosa fiscale in unverified_summaries: nel completo resta soltanto S-01; nel parziale la lista è vuota. model_evaluation indica free_text_included=false e conserva solo modello, motivo e hash dell'output fiscale. La precedente conclusione fiscale non supportata non è riproposta dal report.

Conclusione: confermata sulle due esportazioni la fedeltà estrattiva alla fixture autorizzata e l'esclusione della parafrasi libera fiscale. Non è una verifica della normativa reale né della fedeltà universale del modello. Nessuna modifica al codice richiesta dai risultati; nessun file esportato copiato nella repository o nelle tracce sperimentali.

## Step 19 — Fedeltà delle sintesi mercati

### Implementazione

Autorizzata l'estensione dei controlli ai mercati. Aggiunto gateway/market_evidence.py come catalogo fidato simulated-rates-v1: tasso 3.20/3.60/3.40 per fisso/variabile/misto, data 2025-12-31 e unità annuale. Controlli dopo MCP, nel client A2A gateway e al report, confrontando il contenuto atteso per la vista richiesta. Il digest identifica il contenuto autorizzato, non è una firma né verifica del mercato reale.

Report portato a 0.3.0; policy invariata a 0.2.0 perché nessuna nuova trasformazione dei dati personali. Sintesi mercati deterministica con tasso/data e riferimenti ai campi della fonte, contesto minimizzato e limiti. Nessun confronto di convenienza. Prosa libera dei modelli esclusa da entrambe le sezioni del report e dal riepilogo tecnico /analysis; hash e motivo rimangono in model_evaluation. Sintesi mercati e fiscale confluiscono in faithful_summaries; unverified_summaries è vuoto nei percorsi attuali. I modelli continuano a essere invocati; l'endpoint storico /markets resta tecnico e non protetto da questa composizione del report.

### Verifiche eseguite

90 test automatici superati, 49 warning noti. Otto nuovi casi: tasso, data, unità, ID o flag simulato alterati, campo di istruzione aggiunto, tasso incoerente col tipo richiesto e raccomandazione libera del modello non promossa nel report. Aggiornato il precedente test report che si aspettava la sintesi mercati non verificata: ora richiede estrazione fedele e prosa esclusa. Restano superati test fiscali, subgrafi, casi parziali e finalizzazione.

### Prova reale da raccogliere

Riavviare agenti e gateway; C001 e C024 devono esportare report 0.3.0 con entrambe le sintesi estrattive e tassi simulati rispettivamente 3.20 e 3.60. C006 deve restare partial con sola sintesi fiscale. Nessuna nuova prova browser/Ollama reale dichiarata in questo step. Conservare i report precedenti come evidenze storiche senza riscriverli.

### Limiti

Fedeltà verificata rispetto a fixture autorizzate, non verità del dato nel mondo reale. Un modello che risponde liberamente non viene dichiarato semanticamente affidabile: il testo mostrato è costruito dal codice. Restano da valutare utilità effettiva degli agenti/modelli, fonti istituzionali reali, confronto economico, conflitti, proxy e isolamento. Non si può usare questa scelta per sostenere qualità intrinseca delle sintesi LLM.

## Step 20 — Verifica reale dei report 0.3.0

Esaminati tre report esportati dall'autore, senza copiarli nella repository. Tutti report_version 0.3.0, unverified_summaries vuoto e prosa dei modelli esclusa secondo model_evaluation.

| Esportazione | Stato | Mercati | Fiscale |
|---|---|---|---|
| Report 5 | completed | completed, fixture 3.20% | completed |
| Report 6 | partial | blocked, nessuna fonte/sintesi mercati | completed |
| Report 7 | completed | completed, fixture 3.60% | completed |

Per ciascuna sintesi presente ricalcolato il risultato atteso dal catalogo fidato con il contesto dichiarato: corrispondenza esatta e digest fonte coincidente. Tutte le fonti mantengono real_world_verified=false. Nessun valore simulato presentato come quotazione o normativa reale. Nessuna correzione richiesta dagli esiti.

La verifica conferma estrazione fedele alle fixture sui casi esportati, non affidabilità semantica della prosa esclusa o validità reale delle fonti. Il controllo dei dati documentali contro ogni PDF e la campagna 2×2 restano distinti da questa verifica delle sintesi.

## Step 21 — Documentazione d'uso e lavori residui

README riscritto come guida unica: scopo e limiti della demo, prerequisiti, installazione macOS/Windows, due modelli, avvio dei tre servizi, caricamento e lettura/esportazione del report. Eliminati ripetizioni, istruzioni di vecchie versioni e dettagli sperimentali non necessari all'utente. Nessun percorso personale inserito. Il diario resta storico tecnico, non scaletta da trascrivere integralmente nel capitolo 5.

Creato DA_IMPLEMENTARE.md dal confronto dei requisiti e criteri di verifica della tesi con codice, test e risultati acquisiti. Ogni compito ha ID, riferimento e condizione di completamento; restano solo lavori residui. Una volta verificato uno step si registra qui l'evidenza e si rimuove il compito dalla lista, oppure si restringe al residuo. Non dichiarati interamente soddisfatti requisiti coperti solo in parte.

Priorità proposta: provenienza documentale puntuale e distinzione estratto/derivato/non specificato, poi controlli di conflitto e analisi locale; proxy e isolamento obbligatori prima di fonti remote. Evidenziato il tema sperimentale ancora aperto: i modelli generano prosa esclusa, mentre report e scelta tool sono deterministici; non attribuire loro benefici di qualità non misurati. Fonti reali trattate come estensione separata dalla campagna 2×2 locale della tesi. Nessuna modifica al codice applicativo o ai risultati dei test in questo step.

## Step 22 — Provenienza documentale puntuale e completezza del report

### Decisione confermata

L'autore conferma tipologia mutuo non specificata con limite esplicito, senza bloccare la ricerca simulata. Policy 0.3.0: mortgage_type è contesto facoltativo, distinto dai dati necessari al calcolo S-01. Se assente non viene creato un fatto fittizio other: la vista usa not_specified e il report dichiara l'assenza. Nessuna modifica retroattiva ai PDF o ai piloti precedenti; contratti aggiornati per i servizi, che vanno riavviati.

### Implementazione

Ogni fatto estratto conserva citazione esatta, posizione start/end nel testo della pagina (intervallo semiaperto), etichetta, pagina, ID opaco, SHA-256 del PDF e del testo pagina, metodo/versione pypdf. Origine extracted/transformed/derived distinta dall'input JSON dichiarato. Annotata la trasformazione: numeri italiani, mesi, categorie, percentuale/quota; frequenza mensile derivata dall'etichetta Rata mensile e non inventata. La provenienza del periodo è separata: situazione mutuo oppure anno d'imposta. Testo completo e originali non vengono aggiunti ai messaggi A2A/MCP; le citazioni finanziarie restano nel profilo/report locali.

Report 0.4.0: include campi obbligatori e facoltativi di ciascuno scenario richiesto, stati missing/not_specified/ambiguous, problemi di validazione e stato della provenienza. completeness elenca inventario, obbligatori mancanti, ambigui/non validati, senza span e contesto opzionale assente. Il report non chiama completa l'intera conoscenza finanziaria dell'utente: la copertura riguarda lo schema dei due scenari. I valori JSON senza span restano caller_declared_not_document_verified, non diventano verificati per il solo fatto di avere documento/pagina.

Aggiunto scripts/check_report_provenance.py, eseguito senza modelli: identifica i PDF per hash, verifica testo/citazione/intervalli/etichette, ricalcola trasformazioni e periodo, controlla inventario dei campi e sezioni documentali rispetto agli scenari. Non stampa valori finanziari. Il controllo confronta un'esportazione con i PDF disponibili: non certifica autenticità, esattezza di informazioni estranee allo schema o generalizzazione ad altri layout. Nessun digest è una firma di un'autorità esterna.

### Verifiche eseguite

124 test superati, 49 warning noti. Aggiunti controlli di provenienza/trasformazione su tutti i 25 fascicoli, citazioni ambigue mantenute senza interpretazione arbitraria, campi mancanti espliciti, impossibilità di far passare valori/citazioni/intervalli/periodi alterati e campi o sezioni omessi e un campo presente falsamente dichiarato mancante. Verificata la vista S-01 con not_specified e soli tre campi consentiti. Nessuna garanzia di provenienza puntuale attribuita ai vecchi report, che non contenevano questi metadati.

### Procedura manuale da completare

1. Riavviare gateway e due agenti con i comandi del README; Ollama aperto.
2. Caricare C001, eseguire entrambi gli scenari ed esportare report 0.4.0. Attesi completed, policy 0.3.0, tipologia not_specified, citazioni nei fatti e nelle origini dei periodi, nessun obbligatorio mancante/ambiguo/senza span.
3. Confrontare un importo, il tipo tasso, la quota e la periodicità con i PDF: leggere anche la regola di trasformazione, non solo la coincidenza del numero. Controllare che i periodi si riferiscano al prospetto corretto.
4. Eseguire check_report_provenance.py passando il percorso del report esportato, usando il Python virtuale. Atteso Problemi: 0. Per C001 con due scenari sono presenti dieci fatti obbligatori verificabili; il tipo mutuo opzionale assente non viene contato come fatto inventato.
5. Ripetere C006: partial, capitale missing, conteggio/limite esplicito e fonte mercati assente. Attesi nove fatti verificabili e zero problemi con il verificatore.
6. Ripetere C016: partial, tasso ambiguous con citazione che conserva le alternative, senza scegliere un valore; la verifica della provenienza non trasforma l'ambiguità in validità. Attesi dieci fatti con riferimenti verificabili, uno ambiguo, zero problemi di corrispondenza.
7. Conservare separatamente eventuali report con importi esatti; non inserirli nelle tracce tecniche. Windows: usare il percorso Python già documentato. Comunicare gli output prima di dichiarare la prova manuale completata.

### Lista residui e limiti

P01 ridotto nel file DA_IMPLEMENTARE alla sola raccolta manuale finale; P02 resta prossimo incremento. Rimangono limiti del parser specifico, assenza di coordinate grafiche, gestione di conflitti tra documenti e catalogo delle tolleranze. I riferimenti sono nel testo estratto, non coordinate sul PDF. Le copie esplicitamente esportate dall'utente sopravvivono alla cancellazione della sessione per scelta dell'utente; il server non aggiunge uno storico dei profili.

## Step 23 — Verifica manuale finale della provenienza e chiusura P01

L'autore ha eseguito il verificatore sui tre nuovi report; ripetuto il controllo direttamente sui file e confrontati esiti e completezza. Tutti report 0.4.0, policy 0.3.0.

| Esportazione | Stato | Fatti con riferimenti verificati | Problemi | Limite documentale |
|---|---|---:|---:|---|
| Report 8, caso completo | completed | 10 | 0 | Nessun obbligatorio mancante/ambiguo |
| Report 9, capitale assente | partial | 9 | 0 | remaining_principal missing, S-01 blocked |
| Report 10, tasso ambiguo | partial | 10 | 0 | annual_rate ambiguous, S-01 blocked |

S-02 completed in tutti i casi; mortgage_type opzionale non specificato, senza categoria inventata. Nessun fatto presente privo di span. Nel terzo caso la verifica conferma il riferimento al testo ambiguo, non la validità di un tasso: l'attività resta correttamente bloccata.

La precedente esecuzione con 11 problemi riguardava il vecchio report 0.1.0, privo di metadati puntuali; il nuovo report 8 passa. Non attribuito al nuovo parser un difetto dovuto al file precedente e nessuna modifica retroattiva all'esportazione storica.

P01 rimosso dalla lista dei lavori residui dopo completamento di codice, 124 test automatici e verifica manuale dei tre casi. Chiusura circoscritta al template sintetico: generalizzazione del parser, conflitti tra fonti e autenticità documentale restano fuori da questa evidenza. Prossimo lavoro proposto P02, catalogo dei confronti e gestione delle discordanti senza sovrascritture arbitrarie.

## Step 24 — Catalogo dei confronti e discordanza P02

### Implementazione

Aggiunto gateway/comparisons.py: osservazioni con ID, grandezza, prodotto, periodo, valore/unità, tipo e riferimento di fonte e stato verificato. Prima dei numeri si controllano validazione, significato, prodotto e periodo. Catalogo 0.1.0: tasso contrattuale distinto dal benchmark, capitale residuo, rata, interessi annuali e durata. Conversioni esplicite tra percentuale/frazione/punti base annuali, euro/centesimi e anni/mesi. Nessuna conversione automatica fra tassi mensili e annuali, valute o periodi diversi.

Tolleranza iniziale zero dopo conversione, dichiarata nel catalogo e nei risultati; l'API interna consente tolleranze esplicite per quantità, mai decise dal modello o dedotte dal pilota. Questi valori non sono soglie sperimentali di qualità già approvate: vanno congelati nel protocollo prima della campagna finale. Usata aritmetica Decimal.

Esiti consistent/conflict/not_comparable con motivo, valori normalizzati, differenza e tolleranza. Entrambe le osservazioni e provenienze originali sono conservate; nessun vincitore, media o sovrascrittura. Osservazioni non verificate, quantità non configurate, unità incompatibili e numeri non finiti non producono un falso conflitto.

Report 0.5.0 con consistency, numero di coppie confrontabili e conflitti irrisolti. In presenza di conflitto analysis_status=unresolved_conflict e limite esplicito; status resta esito tecnico delle attività, non approvazione dell'analisi. Nessuna conclusione personalizzata viene autorizzata. Nel percorso attuale il tasso contrattuale documentale e il tasso simulato del mercato hanno significato diverso: il confronto restituisce not_comparable/quantity_mismatch. Per S-02 non si inventano osservazioni numeriche da condizioni fiscali testuali.

Il parametro interno di osservazioni aggiuntive serve alle fixture di report e non è un ingresso HTTP per dati arbitrari. Il percorso normale non ha ancora osservazioni agentiche sovrapposte dello stesso contratto: le prove di conflitto sono sintetiche e dichiarate tali. Completare nuovi adattatori solo quando una fonte effettivamente restituisca la stessa grandezza con contesto verificabile.

### Verifiche eseguite

137 test superati, 49 warning noti. Aggiunti casi agente–documento, agente–agente e documento–documento discordanti, conservazione delle provenienze e immutabilità del profilo, periodi/prodotti/grandezze diversi, dati non verificati, unità non supportate, NaN, conversione punti base/frazione, euro/centesimi e durata, tolleranza esplicita e conflitto nel report senza scelta arbitraria. Corretto un test che usava evidenza con default impliciti: osservazioni report normalizzate tramite il contratto RateEvidence prima di leggerne data e unità.

Eseguito scripts/check_comparisons.py: sei fixture tutte passed=true. File runs/comparisons.json con osservazioni interamente sintetiche, escluso da Git. Il test agente–documento non deriva dall'alterazione di un PDF dell'autore né da un servizio reale. Non equivale alla campagna V-09 completa per quattro configurazioni.

### Procedura manuale

1. Dalla radice eseguire `.venv/bin/python scripts/check_comparisons.py`; Windows usare `.\.venv\Scripts\python.exe`. Nessun servizio richiesto. Attesi conflict per agent_document_conflict, consistent per equivalent_basis_points, not_comparable per gli altri quattro casi; tutti passed=True.
2. Riavviare gateway, mantenere agenti e Ollama attivi. Caricare C001 e produrre un report 0.5.0. In consistency attesi zero conflitti, zero coppie confrontabili e una coppia not_comparable/quantity_mismatch tra tasso contrattuale e benchmark. Le provenienze e i valori originali restano visibili.
3. Controllare che non sia riportata una contraddizione o convenienza solo perché i due tassi sono numericamente diversi. Le sintesi delle fixture restano fedeli; report 0.4.0 e precedenti rimangono evidenze storiche.
4. Comunicare output e report per chiudere la verifica manuale residua P02. Il file di attività mantiene espliciti limiti e residui, senza dichiarare conflitti reali non osservati.

### Limiti

Il periodo attuale è una chiave esplicita, non un riconoscimento libero di intervalli nel linguaggio naturale. Il flag verified riguarda l'ammissione dell'osservazione da parte dei controlli applicativi, non autenticità del documento o validità del mercato reale. Nessun confronto esaustivo delle molteplici grandezze nei PDF implicito in zero conflitti. Catalogo confronti distinto dalla policy di minimizzazione: policy resta 0.3.0.

## Step 25 — Verifica finale P02

L'autore ha eseguito check_comparisons.py: sei casi tutti passed=True. Verificato direttamente runs/comparisons.json: conflitto agente–documento, equivalenza dopo conversione punti base e non confrontabilità per periodo, prodotto, benchmark e grandezza diversi confermati.

Esaminato report esportato 11, versione 0.5.0, policy 0.3.0, stato completed. La coppia registrata conserva tasso contrattuale 3.1 e benchmark sintetico 3.20, entrambe le provenienze, periodo e unità. Esito not_comparable/quantity_mismatch; unresolved_conflicts=0, comparable_pairs=0, nessuna scelta o sovrascrittura. analysis_status circoscritto a no_conflict_in_registered_observations. Il report non presenta la differenza come contraddizione o convenienza. Ricalcolata provenienza documentale: dieci fatti verificati, zero problemi.

P02 rimosso dalla lista residui nel perimetro del catalogo e delle fixture implementate, dopo test automatici e prova manuale. Restano espliciti: conflitti sintetici non sono conflitti osservati da fonti reali; le attuali osservazioni agentiche non duplicano la misura contrattuale. Nuove fonti sovrapposte richiederanno adattatori e verifiche dedicate. Il requisito generale RF-07 non è dichiarato verificato per qualsiasi documento o fonte futura. Nessuna modifica al codice richiesta dai risultati. Prossimo incremento proposto P03, confronto locale orientativo S-01 con ipotesi e calcoli verificabili.

## Step 26 — Confronto locale orientativo del mutuo P03

### Perimetro concordato

Dopo spiegazione in linguaggio semplice l'autore approva rate mensili posticipate costanti, capitale e durata residui documentali, tasso contrattuale e tasso della fixture. Costi non documentati esclusi, non assunti realmente nulli. Variabile/misto trattati soltanto come scenari a tasso congelato, non previsioni. Periodicità diverse segnalate non supportate. Nessuna raccomandazione di rinegoziazione.

### Implementazione

Aggiunto gateway/mortgage.py. Formula rata A=P*i/[1-(1+i)^(-n)], con i=tasso annuo nominale percentuale/1200; per tasso zero A=P/n. Decimal con precisione locale 50; importi esposti a centesimi ROUND_HALF_UP. Totali teorici calcolati dalla rata non arrotondata; non sono un piano bancario con rate/ultima rata arrotondate e spese. Limite del modello 1–1200 mesi, tassi 0–100%, capitale positivo/finito.

Report 0.6.0 con mortgage_comparison: input e riferimenti ai fatti, fonte alternativa e digest, rata documentale, rata teorica ai due tassi, totale rate/interessi teorici e differenze contratto meno simulato. Positivo indica scenario simulato più basso; negativo più alto. Nessuna etichetta di risparmio garantito. Eventuale differenza rata documentale–modello segnalata, senza correzione automatica del documento e senza dichiarare errore contrattuale.

Calcolo solo locale dopo verifica della fixture, senza modificare viste A2A/MCP o prompt. Non eseguito su dati mancanti/ambigui, attività mercati fallita, evidenza assente, periodicità non mensile o conflitti irrisolti. Lo stato tecnico completed non equivale ad approvazione della convenienza. Confronto ipotetico tra scenari distinto dal confronto RF-07 fra due affermazioni sulla stessa grandezza: tasso contrattuale e benchmark restano non confrontabili come verità del medesimo fatto.

### Test e risultati

149 test superati, 49 warning noti. Nuovi casi tasso zero, singola rata, saldo residuo tramite ricorrenza mensile indipendente dalla formula, coerenza con rate del dataset fisso/variabile, segno delle differenze, mancanti/ambigui/conflitti, fonte assente, periodicità non supportata, rata documentale diversa preservata e input matematici invalidi.

Aggiunto scripts/check_mortgage.py: ricostruisce la rata con ricerca numerica sul saldo mensile invece della formula chiusa; confronta rate/totali/interessi, tassi con fonti, differenze e rata documentale preservata. Test verifica anche rifiuto di un importo teorico alterato. Per not_calculated segnala soltanto che il report dichiara l'assenza del calcolo: non è verifica automatica della causa del blocco, che resta coperta dai test applicativi e dalla lettura del report.

Verifica locale diretta senza modelli: C001 rata teorica contrattuale 1604.32, simulata 1608.35, differenza -4.03 EUR/mese; C024 867.11 e 809.91, differenza 57.20 EUR/mese sotto ipotesi di tassi costanti. Questi numeri sono scenari sintetici, non offerte o conclusioni economiche reali. Non ancora raccolta nuova esportazione browser dell'autore.

### Procedura manuale

1. Riavviare gateway; agenti e Ollama attivi. Caricare C001, eseguire scenari ed esportare nuovo report 0.6.0.
2. Controllare mortgage_comparison: status calculated, rate teoriche 1604.32/1608.35, differenza -4.03, rata documentale preservata, ipotesi/costi esclusi e personalized_recommendation=false.
3. Eseguire scripts/check_mortgage.py passando il percorso esatto del nuovo report con Python virtuale: attesi tutti True. Il verificatore usa un metodo numerico indipendente, ma le stesse ipotesi matematiche; non prova validità di un'offerta reale.
4. Ripetere C024: 867.11/809.91, differenza 57.20; leggere il limite esplicito sul variabile, non interpretare il risultato come previsione.
5. Ripetere C006 o C016: not_calculated/input_not_ready, nessun numero inventato. Fonte fiscale e report parziale restano disponibili.
6. Verificare anche provenienza con check_report_provenance.py sui nuovi file. Per Windows usare il Python virtuale documentato nel README. Condividere report e output per chiudere P03.

Lista residui aggiornata: P03 limitato alla verifica manuale finale. README rimane orientato all'uso, con breve spiegazione delle ipotesi; dettagli matematici e test restano nel diario. Policy invariata a 0.3.0 perché nessuna trasformazione dei dati condivisi è cambiata.

## Step 27 — Verifica reale P03 e chiusura del compito

Esaminati i tre report esportati 12/13/14, tutti versione 0.6.0; ripetuti controllo numerico indipendente e verifica di provenienza. Nessun file con importi copiato nella repository.

| Report | Esito | Rata modello contrattuale | Rata scenario simulato | Differenza mensile | Provenienza |
|---|---|---:|---:|---:|---|
| 12, fisso | completed/calculated | 1604.32 EUR | 1608.35 EUR | -4.03 EUR | 10 fatti, zero problemi |
| 13, variabile | completed/calculated | 867.11 EUR | 809.91 EUR | 57.20 EUR | 10 fatti, zero problemi |
| 14, capitale mancante | partial/not_calculated, input_not_ready | Non calcolata | Non calcolata | Non calcolata | 9 fatti, zero problemi |

Nei primi due report tutti i sei controlli numerici sono veri: scenario contrattuale, scenario simulato, tassi corrispondenti alle fonti, differenze, rata documentale preservata e nessuna raccomandazione. Nel terzo il verificatore conferma solo la dichiarazione not_calculated; letto separatamente il motivo input_not_ready e verificata l'assenza del capitale tramite provenienza/inventario del report.

Ipotesi esplicite in tutti: stesso capitale/durata, tasso nominale diviso 12, rate mensili posticipate costanti, tassi congelati, costi/imposte/assicurazioni non documentati esclusi, arrotondamento dei soli importi esposti. Nel variabile presente il limite non previsivo. Nessuna offerta reale, risparmio garantito o conclusione definitiva di convenienza.

P03 rimosso dai residui dopo implementazione, 149 test automatici e prova manuale nel perimetro concordato. Nessuna correzione richiesta dagli esiti. Prossimo lavoro P04: occorre concordare un'applicazione fiscale locale coerente con le sole fixture simulate, senza introdurre aliquote o diritti non verificati.

## Step 28 — Riepilogo fiscale e ripartizione ipotetica P04

### Perimetro concordato

L'autore sceglie riepilogo e scenario ipotetico. I PDF non chiariscono se gli interessi siano già ripartiti: il prodotto interessi × quota viene presentato soltanto sotto l'ipotesi esplicita che l'importo riguardi l'intero mutuo e non sia già attribuito alla persona. Nessuna aliquota, soglia, base detraibile o diritto fiscale inventato. Quota di intestazione non interpretata come prova di spettanza.

### Implementazione

Aggiunto gateway/tax_application.py con calcolo deterministico locale, Decimal e arrotondamento HALF_UP ai centesimi dopo il prodotto. Report 0.7.0: documentary_context con anno/finalità/interessi/quota, input_refs ai fatti, hypothetical_allocation con formula/origine/arrotondamento, fonte simulata con digest e condizioni da verificare con riferimenti. Flag deduction_calculated=false, tax_entitlement=not_assessed e personalized_recommendation=false. Risultato derivato non presentato come importo personale documentato.

Non calcolato se dati minimi mancanti/ambigui o non coerenti, fonte fiscale indisponibile o conflitti irrisolti. Fonte verificata nuovamente rispetto al catalogo. Solo S-02 richiesto produce questa sezione; nessun importo aggiunto alle viste degli agenti o ai prompt. Con S-01 ancora disponibile il report può restare parziale. Nessun aggiornamento retroattivo ai report precedenti; policy resta 0.3.0.

### Verifiche eseguite

156 test superati, 49 warning noti. Nuovi casi quote 100/50 percento e contesti diversi, controllo indipendente tramite aritmetica intera, mezzo centesimo HALF_UP, interessi zero, mancanti/ambigui/periodi errati/quote fuori intervallo, conflitti, fonte assente/alterata, ipotesi e limiti espliciti, profilo immutato. Verificata anche integrazione report con solo S-02 e assenza del confronto mutuo non richiesto.

Aggiunto scripts/check_tax_application.py: ricalcola il prodotto con Fraction e arrotondamento intero, confronta contesto e valori documentali e controlla i flag di mancata attestazione fiscale. Il test rileva un importo derivato alterato. Il controllo not_calculated conferma la dichiarazione, non verifica da solo la causa; le cause sono coperte dai test applicativi e dalla lettura del report.

Prove locali dirette senza Ollama: C001 prodotto ipotetico 4852.52 EUR; C024 2413.79 EUR (4827.57 × 0.5); C011 not_calculated/input_not_ready. Nessun nuovo report browser ancora raccolto per questo step.

### Procedura manuale

1. Riavviare gateway, lasciare agenti e Ollama attivi. C001 con entrambi gli scenari: esportare report 0.7.0. tax_application calculated, contesto documentale mantenuto, prodotto ipotetico 4852.52, nessuna detrazione.
2. C024: quota 0.5, interessi 4827.57, prodotto ipotetico 2413.79. Verificare che il valore sia distinto dal dato documentale e dichiarato non già attribuibile alla persona senza l'ipotesi.
3. C011: report partial, S-02 bloccato, tax_application not_calculated/input_not_ready; S-01 può continuare. Nessuna quota o interesse ricostruiti.
4. Eseguire check_tax_application.py con il percorso esatto dei nuovi report e Python virtuale; attesi tutti True. Per C011 attesi flag di mancata detrazione/spettanza/raccomandazione e not_calculated_as_declared=True.
5. Controllare anche provenienza e ipotesi nel testo; condividere report e output prima di chiudere P04. Windows: percorso Python come nel README.

### Limiti e residui

P04 ristretto alla verifica manuale finale. Il risultato non risponde alla normativa reale: la fixture è inventata. La correttezza aritmetica non dimostra spettanza né validità dell'ipotesi di ripartizione. Prima di un'applicazione fiscale reale servono semantica documentale, fonti istituzionali temporalmente pertinenti, requisiti verificati e controlli delle uscite. Le copie dei report con dati esatti restano consegne esplicite, non tracce sperimentali.

## Step 29 — Verifica reale P04 e chiusura del compito

Esaminati direttamente i report esportati 15/16/17, tutti report_version 0.7.0. Ripetuti controllo aritmetico indipendente e verifica della provenienza documentale.

| Report | Stato | Contesto fiscale | Ripartizione ipotetica | Provenienza |
|---|---|---|---|---|
| 15 | completed/calculated | 2025, acquisto abitazione principale, quota 1 | 4852.52 × 1 = 4852.52 EUR | 10 fatti, zero problemi |
| 16 | completed/calculated | 2024, ristrutturazione, quota 0.5 | 4827.57 × 0.5 = 2413.79 EUR dopo arrotondamento | 10 fatti, zero problemi |
| 17 | partial/not_calculated | S-02 blocked/input_not_ready, S-01 completed | Nessun importo ricostruito | 9 fatti, zero problemi |

Nei primi due report tutti i nove controlli del verificatore sono veri. Nel terzo sono veri i tre flag di mancata detrazione/spettanza/raccomandazione e not_calculated_as_declared. La verifica di provenienza e il motivo applicativo sono stati letti separatamente: il solo flag not_calculated non dimostra la correttezza del blocco.

Controllati ipotesi e limiti: interessi assunti riferiti all'intero mutuo e non già ripartiti, quota usata solo come fattore aritmetico, rischio di doppia ripartizione esplicito, nessuna fonte normativa reale o attestazione fiscale. L'importo derivato è distinto da importo personale documentato. Nel report 16 il periodo 2024 è conservato, senza riallinearlo arbitrariamente alla situazione mutuo 2025.

P04 rimosso dalle attività residue dopo implementazione, 156 test automatici e verifica manuale nel perimetro concordato. Nessuna correzione richiesta dai risultati. Non dimostrata spettanza o correttezza normativa reale. Prossimo lavoro P05: distinguere provenienza mancante da errore generico e gestire risultati non verificati senza perdere le altre attività utilizzabili.

## Step 30 — Risultati senza provenienza e stato non verificato P05

### Implementazione

Stato unverified ed error_code missing_provenance nei contratti. Un risultato privo di evidenza non può più presentarsi come completed. Nel gateway gateway/result_validation.py distingue envelope non valido/correlazione errata da evidenza assente o metadati obbligatori omessi. Verifica la presenza esplicita nel payload ricevuto prima dei default Pydantic: i default della fixture non ricostruiscono una fonte non trasmessa. I campi non di provenienza restano sottoposti allo schema, quindi un valore malformato non diventa automaticamente unverified.

I risultati non verificati conservano solo correlazione/modello e motivo del diniego, con evidenza rimossa e sintesi sostituita da testo locale esplicito. Nessuna ricostruzione della fonte o conclusione ricevuta esposta al lettore. Conteggio provenance_verified=0 distinto da result_validated, che riguarda il contratto sanitizzato. La verifica Card rimane separata.

I subgrafi propagano unverified; aggregazione partial se esiste un altro ramo completed, altrimenti unverified se almeno un ramo ha provenienza mancante. Report 0.8.0: esito esplicito, nessuna fonte/sintesi fedele o calcolo da quel ramo, limite dichiarato e altre attività preservate. La sessione viene comunque chiusa. Calcoli P03/P04 richiedono completed, quindi non usano dati non verificati.

Fixture services/unverified_market_agent: dichiara intenzionalmente completed senza evidence tramite bypass dello schema esclusivamente per la prova negativa di protocollo. Non chiama modelli o MCP e non sostituisce il servizio nominale. Il gateway deve riclassificarla, non fidarsi dell'etichetta completed. Nessuna modifica ai report storici; policy resta 0.3.0.

### Verifiche

165 test superati, 56 warning noti. Nove nuovi casi: fonte/evidenza assente in mercati e fiscale, mancata promozione dei default, contenuto malformato distinto, esclusione da report/calcoli, altro ramo conservato, API con solo risultato unverified e cleanup, fixture A2A realmente serializzata con risultato incompleto e store svuotato. Aggiornato test storico che si aspettava errore generico per fonte assente: ora richiede unverified/missing_provenance; Card o correlazione errate restano errori.

Prove automatiche in processo/controllate, non nuova prova manuale dell'autore. README aggiornato brevemente; P05 ristretto al residuo manuale nel file lavori.

### Verifica manuale passo per passo

1. Riavviare gateway per caricare il codice. Lasciare fiscale e Ollama attivi.
2. Fermare solo agente mercati sulla porta 8001. Avviare al suo posto `.venv/bin/python -m uvicorn services.unverified_market_agent:app --host 127.0.0.1 --port 8001 --no-access-log`. Windows: Python virtuale come nel README.
3. Aprire pagina locale, caricare C001 e richiedere entrambi gli scenari. Attesi partial; attività S-01 unverified/missing_provenance, fiscale completed; report 0.8.0 con sole fonte/sintesi fiscale. mortgage_comparison not_calculated/market_evidence_unavailable. Nessuna frase della fixture senza fonte presente come conclusione; messaggio esplicito di mancata provenienza.
4. Esportare il report. Verificare il percorso reale anche con `.venv/bin/python scripts/run_multi_pilot.py --cases C001 --output runs/multi_missing_provenance.jsonl`: atteso partial e pulizia True; passed False rispetto al nominale è atteso. Leggere nei record missing_provenance, non delegation_failed.
5. Con solo S-01 selezionato in una nuova sessione: atteso unverified, nessuna fonte/sintesi/calcolo, report e pulizia comunque disponibili. Il blocco non deve inventare risultato personalizzato.
6. Fermare fixture, riavviare services.market_agent:app sulla stessa porta. Riprovare C001 con entrambi: completed e fonti/sintesi corrette; condividere report e record prima di chiudere P05.

### Limiti

Non è verifica della normativa o affidabilità semantica del modello. La fonte alterata con contenuto invalido resta distinta da fonte semplicemente mancante; può ancora produrre errore di delega generico. Il rifiuto della fonte obbligatoria impedisce l'attività personalizzata interessata, non necessariamente le altre. Restano catalogo/proxy, isolamento e completamento delle prove avversarie oltre alle fixture note.

## Step 31 — Prova reale di provenienza mancante con altro ramo disponibile

Esaminato report 18 versione 0.8.0 e ultimo record di runs/multi_missing_provenance.jsonl. Esito partial; S-01 unverified/missing_provenance, S-02 completed. Fonti e sintesi fedeli presenti soltanto per S-02. mortgage_comparison not_calculated/market_evidence_unavailable; applicazione fiscale ipotetica ancora calculated. Dieci fatti documentali con riferimenti verificati, zero problemi: la mancanza di provenienza riguarda il risultato agente, non i PDF.

Pilota: passed=false rispetto al nominale previsto completed, come atteso per la prova negativa; automatic_session_closed=true e cleanup_verified=true. Entrambi i rami attraversano request_view, delegate_a2a, verify_result; lo scambio A2A è completato, ma il risultato mercati è riclassificato non verificato e non usato. Nessuna correzione necessaria.

Verificata la distinzione fra risultato non verificato e guasto generico nel percorso reale. P05 ristretto a due residui manuali: solo S-01 non verificato e ripristino nominale dopo rimozione della fixture. Non dichiarate eseguite queste prove finché non raccolte le evidenze. Fonte non verificata non diventa valida per effetto di provenienza documentale corretta degli input.

## Step 32 — Revisione RF-06/RNF-07/V-08 e chiusura P05

### Evidenze reali finali

Esaminato runs/only_unverified.jsonl: soltanto S-01, stato unverified/missing_provenance, provenance_verified=0, report presente, chiusura automatica e pulizia vere. passed=false è corretto nel confronto con il nominale. Nessuna attività fiscale avviata.

Esaminato runs/p05_recovery.jsonl: entrambi gli scenari completed, fonte e contenuto fixture verificati per entrambi, provenance_verified=1, report presente, passed=true e pulizia automatica verificata. Ripristino dopo rimozione della fixture confermato.

### Rilettura della tesi e lacuna trovata

Riletti RF-06, RF-08/RF-09, RNF-07, V-08 e sezioni 4.3/4.5. La gestione deve riguardare anche una fonte omessa prima del confine A2A. La revisione ha individuato che la validazione della risposta MCP poteva applicare default di provenienza e trasformare l'omissione in metadati apparentemente presenti. La verifica A2A da sola non era sufficiente: P05 non è stato chiuso prima della correzione.

### Correzioni e nuove regressioni

Aggiunto controllo di presenza esplicita dei metadati di provenienza nella risposta MCP prima dei default, condiviso dai cataloghi mercati e fiscale. Il contenuto non di provenienza resta sottoposto allo schema; una struttura malformata non viene promossa a evidenza valida. MissingProvenanceError è convertito dagli agenti in unverified/missing_provenance, evidence nulla e testo locale di esclusione, prima dell'inferenza.

Nuova fixture services/missing_source_mcp con due strumenti reali stdio che restituiscono dati strutturati senza source_id. Test per mercati e fiscale verificano che l'omissione interrompa la pipeline prima di Ollama. Un primo test ha rilevato che l'eccezione dentro il contesto async MCP veniva avvolta in ExceptionGroup: spostata la validazione del contenuto dopo la chiusura dei contesti MCP, mantenendo errore specifico e pulizia. Aggiornato un precedente test con evidenza abbreviata per usare tutti i metadati espliciti.

Suite finale: **171 test superati, 70 warning di libreria**. I nuovi test coprono controllo catalogo, conversione dell'errore nell'agente tramite A2A e passaggio MCP reale senza invocazione del modello. Gli avvisi aumentano con i percorsi ADK esercitati, non sono fallimenti.

### Valutazione di soddisfacimento

P05 soddisfatto nel perimetro dei contratti, strumenti e scenari attuali:

- fonte obbligatoria assente distinta da schema/correlazione errati e guasto di esecuzione;
- stato unverified esplicito attraverso agente, gateway, grafo e report;
- evidenza/sintesi/calcoli del ramo non verificato esclusi, senza fonti ricostruite dai default;
- attività indipendente valida preservata con risultato partial;
- se manca l'unica attività indispensabile, nessuna risposta personalizzata, ma esito unverified e limiti;
- sessioni chiuse e ritorno al nominale verificato.

Non equivale a pieno soddisfacimento della tesi: V-08 va ancora inserito nella campagna finale dieci ripetizioni per ciascuna delle quattro configurazioni; fonti reali, proxy e isolamento restano da implementare. Nuovi strumenti e contratti richiederanno corrispondenti campi di provenienza obbligatori. Nessuna norma reale, autenticità documentale o affidabilità universale del modello dedotta da queste prove.

P05 rimosso dai residui; P01–P05 chiusi nei rispettivi perimetri esplicitati. README conservato essenziale, codice di questa revisione da caricare riavviando gateway e agenti prima delle successive prove. Nessun commit creato automaticamente.


## Step 33 — Primo confine applicativo delle deleghe A2A S01

### Perimetro e implementazione

Avviato S01 dopo la ripresa del lavoro. Nuovo gateway/a2a_egress.py: catalogo locale immutabile versione 0.1.0 con endpoint, tipo di incarico, identità e skill dei due specialisti. La policy delle viste resta 0.3.0. Gli adattatori mercati e fiscale usano il catalogo anche per i controlli Card e un trasporto HTTP vincolato al singolo incarico.

Prima del trasporto vengono rivalidati incarico, versione corrente della policy e scadenza. Sono ammessi soltanto GET della Card configurata e POST message/send all’endpoint esatto dello scenario. Query, metodi o destinazioni differenti, corpi opachi, metadati aggiuntivi, intestazioni fuori catalogo e contenuti diversi dall’incarico autorizzato sono rifiutati. Il corpo viene ricostruito da template e contratto; intestazioni in uscita ricostruite da HTTPX, nessuna estensione arbitraria inoltrata. Timeout locali del trasporto fissati esplicitamente; nessun retry di connessione. Qualsiasi risposta 3xx è rifiutata, senza seguire Location: in questo catalogo nessun redirect è autorizzato.

I dinieghi sono EgressDenied senza payload nell’errore. Il workflow li distingue dai guasti con blocked/not_authorized e conserva la finalizzazione comune. L’endpoint storico /markets restituisce 403 per questo diniego; mantiene il proprio ciclo di sessione esplicito preesistente.

### Prove eseguite

Suite completa: **184 passed, 72 warning**, 6.12 secondi. Tredici nuovi test, senza servizi esterni: SDK A2A reale sopra trasporto HTTP simulato per entrambi gli scenari; destinazione differente, query, metodo, intestazione aggiuntiva, metadati, vista alterata rispetto all’incarico, corpo opaco, redirect, incarico scaduto e policy storica; diniego nel workflow con pulizia. Nei dinieghi preventivi il ricevitore simulato registra zero richieste. Nel redirect ne registra una sola, quella alla destinazione ammessa, senza invio alla Location. La compatibilità SDK è verificata sul payload realmente serializzato: il suo ID JSON-RPC viene rigenerato come UUID con trattini; ammessi UUID canonici con o senza trattini.

Suite precedente inclusa, nessun avviso soppresso. git diff --check superato. Nessuna nuova prova manuale con Ollama né nuovo report esportato acquisiti in questo incremento.

### Procedura manuale da acquisire

Lasciare aperti Ollama e i due specialisti nominali. Fermare soltanto il gateway con Ctrl+C nel suo terminale e riavviarlo dalla radice della repository con `.venv/bin/python -m uvicorn gateway.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log`. Caricare C001, selezionare entrambi gli scenari ed eseguire. Attesi report 0.8.0, completed per entrambi, fonti simulate e calcoli precedenti preservati. Esportare il nuovo report e verificarlo con i tre verificatori esistenti, usando il nome effettivo. Acquisire poi C006: S-01 blocked/input_not_ready, S-02 completed, esito partial. Non confondere tale blocco di ingresso con un diniego del trasporto. Le prove negative di trasporto sopra descritte sono automatiche, non prove manuali di isolamento.

### Limiti e seguito

S01 resta aperto. Questo è un trasporto applicativo delle deleghe A2A locali, non il proxy completo delle uscite della tesi. Le chiamate MCP stdio e le richieste Ollama degli specialisti restano nel percorso precedente. Il catalogo vincola gli schemi esistenti; non implementa ancora riconoscimento PII/valori sensibili di sessione, autenticazione dei chiamanti o isolamento host/container. I componenti non sono ancora impediti a livello rete dal creare connessioni alternative. Nessuna prova di non aggirabilità, nessuna fonte reale autorizzata, nessuna nuova garanzia di anonimato. Restano da centralizzare inferenza e connettori, ampliare catalogo/controlli e acquisire la prova manuale nominale. Nessun commit creato.


## Step 34 — Verifica del report nominale dopo il primo incremento S01

Esaminato direttamente report-locale-20.json esportato dall’utente: versione 0.8.0, policy 0.3.0, dati corrispondenti a C001, entrambi gli scenari completed senza error_code. Eseguiti i tre verificatori del progetto sul file effettivo: provenienza di dieci fatti verificata con zero problemi; tutti i sei controlli mutuo e i nove controlli fiscali veri.

Lette anche fonti, sintesi, completezza e limiti: entrambe le fonti dichiarate simulate e non verificate nel mondo reale; sintesi deterministiche riferite ai campi delle fixture; prosa dei modelli esclusa. Tipologia mutuo non specificata mantenuta tale. Tasso contrattuale e benchmark distinti per grandezza, senza falso conflitto; nessuna spettanza fiscale, detrazione o raccomandazione dichiarata. Ipotesi di ripartizione e limiti economici conservati.

La prova conferma il risultato nominale esportato dopo l’incremento. Il report non contiene identificativo della versione del trasporto, traccia di ogni richiesta o prova della pulizia: da questo file, da solo, non si dimostrano l’effettivo attraversamento del nuovo trasporto, i dinieghi o l’isolamento. Le verifiche automatiche dello Step 33 rimangono evidenze distinte. Nessuna correzione richiesta dal report. Non copiati nel diario importi o citazioni documentali.

Resta da acquisire C006 con entrambi gli scenari: partial, S-01 blocked/input_not_ready, S-02 completed, senza capitale ricostruito e senza calcolo mutuo. S01 resta aperto per i residui dello Step 33.


## Step 35 — Verifica del report C006 dopo il primo incremento S01

Esaminato direttamente report-locale-21.json, versione 0.8.0 e policy 0.3.0. Dati corrispondenti a C006. Esito partial: S-01 blocked/input_not_ready per remaining_principal mancante; S-02 completed senza errore. Il capitale resta missing, il confronto mutuo not_calculated/input_not_ready. Nessuna fonte, sintesi o valutazione del modello mercati riportata; il ramo fiscale valido è preservato.

Eseguiti i tre verificatori sul file effettivo: nove fatti documentali verificati, zero problemi; not_calculated_as_declared vero per il mutuo; tutti i nove controlli fiscali veri. Letti separatamente motivo del blocco, completezza, contesto fiscale, fonte simulata, sintesi deterministica e ipotesi. Nessun capitale ricostruito, nessuna detrazione o spettanza attestata. Nessun importo o citazione documentale copiato nel diario.

Acquisite le due verifiche manuali dei risultati previste nello Step 33: C001 nominale (Step 34) e C006 parziale. Nessuna correzione richiesta da questa prova. Il blocco osservato è di sufficienza dell’ingresso, non un diniego del trasporto. Il report non prova da solo assenza di chiamate di rete, pulizia o caricamento della nuova versione del trasporto; tali proprietà restano distinte dalle evidenze dei test automatici. S01 rimane aperto per centralizzazione di inferenza e connettori e ulteriori controlli; nessuna prova di isolamento o uscita reale aggiunta.


## Step 36 — Inferenza locale controllata dal gateway S01

### Scelta e percorso

Incremento autorizzato dall’utente dopo la proposta di spostare le chiamate Ollama nel gateway, coerentemente con il controllo dei payload di inferenza previsto nei capitoli 3–4. Il percorso applicativo è specialista → POST /internal/inference del gateway → Ollama locale → gateway → specialista. Nessun nuovo provider, fonte reale o ruolo dei modelli introdotto. Il report rimane 0.8.0 e la policy delle viste 0.3.0.

Nuovo gateway/inference.py con catalogo inferenza 0.1.0, modelli e prompt precedenti, parametri invariati: contesto 4096, massimo 200 token, temperatura zero, keep_alive=0; thinking disabilitato per il fiscale. Il gateway costruisce integralmente il payload usando evidenza verificata contro il catalogo delle fixture. Lo specialista non sceglie URL, modello, prompt o opzioni. Credenziale, correlazione, profilo e documenti non entrano nel prompt Ollama.

### Autorizzazione e ciclo di vita

Ogni delega dei tre endpoint gateway (markets, workflow, analysis) registra un incarico con credenziale casuale di 256 bit, trasmessa nel contratto A2A come inference_token e nell’intestazione Authorization verso il gateway. Campo opzionale solo per compatibilità di lettura dei contratti: una richiesta di inferenza senza autorizzazione è rifiutata. Il token non è una PII e non entra nei risultati, report o misure. Il broker è in memoria e per istanza applicativa; continua il requisito di un solo worker.

Il controllo associa credenziale, correlazione, scenario, incarico attivo, policy corrente e scadenza. Rivalida esplicitamente la provenienza MCP e il contenuto della fixture prima di chiamare Ollama. L’autorizzazione è consumata prima dell’invio: una chiamata, anche fallita o in timeout, non abilita retry. È rimossa nel finally della delega anche per eccezione o annullamento, alla chiusura della sessione, alla pulizia pigra delle sessioni scadute e allo shutdown ordinario. Una revoca durante la chiamata impedisce la consegna tardiva del risultato.

Richieste non autorizzate: HTTP 403; schema con campi arbitrari: 422 senza riflettere il corpo; timeout: 504; guasti dell’inferenza: 502 con messaggio locale privo del contenuto originale. Redirect Ollama rifiutati, nessun endpoint alternativo. Gli specialisti convertono il diniego in blocked/not_authorized senza evidenza; timeout in failed/timeout. Il ramo indipendente rimane utilizzabile.

Nuovo services/inference_client.py, utilizzato da entrambe le pipeline dopo MCP e verifica fonte. Nessuna chiamata diretta a /api/chat rimane nei moduli services. I moduli fidati del gateway non costituiscono tuttavia un confine di sicurezza di processo per il solo fatto di risiedere in una directory diversa.

### Misure

ollama_ms misura nel gateway il tempo della richiesta locale a Ollama; inference_gateway_roundtrip_ms misura nello specialista il giro completo attraverso il gateway. Sono tempi annidati e non vanno sommati. Nei risultati restituiti al gateway, gateway_inference_authorized e gateway_inference_completed vengono impostati dal broker usando il proprio stato, non accettati dall’agente; inference_catalog_version identifica il catalogo. I contatori mancanti di Ollama non sono sostituiti con zeri inventati: risposta senza prompt_eval_count, eval_count o load_duration è errore. Gli zeri nelle fixture di test sono valori espliciti della simulazione. Restano da completare le misure sui guasti in R03.

### Verifiche eseguite

Suite completa: **208 passed, 86 warning**, 6.65 secondi. Ventiquattro nuovi test rispetto allo Step 33; aggiornati due test precedenti per controllare il nuovo confine invece della chiamata diretta rimossa. Nessun avviso soppresso; nuovi avvisi ADK dai percorsi A2A aggiuntivi.

Coperti: entrambi i payload Ollama e i parametri, credenziale/correlazione assenti nel payload al modello, consumo monouso; credenziale assente o errata, correlazione/scenario diversi, incarico scaduto o revocato, fonte mancante, contenuto alterato o aggiuntivo, scelta arbitraria di modello/prompt/URL/opzioni; nessuna chiamata Ollama nei dinieghi preventivi. Redirect con singola richiesta; revoca per eccezione/annullamento; risultato tardivo dopo revoca scartato. Due prove A2A reali in processo verificano conversione del diniego in blocked e pulizia degli store ADK/A2A.

Prove integrate attraverso API gateway e nuovo client inferenza, con MCP stdio reale e Ollama simulato: entrambi i rami completati; timeout Ollama mercati con fiscale completato, esito partial e sessione chiusa. Le deleghe A2A in queste due prove sono sostituite dai callback delle pipeline; il trasporto A2A SDK è coperto separatamente dai test esistenti. Nessuna nuova inferenza Ollama reale eseguita o prestazione misurata con questi test. git diff --check superato.

### Prove manuali ancora da acquisire

Tenere Ollama aperto. Fermare e riavviare tutti e tre i servizi nominali con i comandi del README; i vecchi specialisti contatterebbero ancora direttamente Ollama. Nel browser caricare C001 con entrambi gli scenari, eseguire ed esportare il nuovo report. Attesi completed, versione report 0.8.0, stessi dati, fonti simulate e calcoli; verificare il file effettivo con i tre verificatori. Poi C006, attesi partial, mercati blocked/input_not_ready e fiscale completed. I report non contengono le misure del broker: raccogliere anche una ripetizione con `scripts/run_multi_pilot.py --cases C001 C006 --repetitions 1 --output runs/s01_inference_gateway.jsonl` tramite Python virtuale. Nel C001 attesi gateway_inference_authorized=1 e gateway_inference_completed=1 per entrambi i rami; nel C006 solo per il fiscale. Leggere direttamente JSONL, stati, fasi e pulizia prima di acquisire la verifica. Non dedurre la pulizia degli agenti dal solo flag gateway.

### Limiti e residui

S01 rimane aperto; MCP stdio è ancora eseguito dagli specialisti, non mediato dal nuovo broker. Nessun rilevatore generale di PII o valori di sessione e nessuna fonte reale introdotti. La credenziale temporanea limita operazione e vita dell’incarico, ma chi la possiede può presentare quella richiesta: non autentica il processo specialistico né sostituisce S03. Finché manca isolamento di rete, un processo può tentare connessioni dirette fuori da questo percorso. La revoca non garantisce l’arresto immediato di un’inferenza già in corso nel processo Ollama, né una cancellazione fisica della memoria. Gli arresti e l’annullamento end-to-end restano R01. La prosa LLM resta esclusa dal report; la sua qualità non è dimostrata da questi test. Nessun commit creato.


## Step 37 — Verifica del report C001 dopo il broker inferenza

Letto direttamente report-locale-22.json: versione 0.8.0, policy 0.3.0, dati C001, entrambi gli scenari completed senza errore. Eseguiti i tre verificatori sul file effettivo: dieci fatti verificati e zero problemi di provenienza, sei controlli mutuo e nove fiscali tutti veri. Fonti esplicitamente simulate, sintesi deterministiche, prosa LLM esclusa, ipotesi e limiti mantenuti; nessuna tipologia mutuo inventata né detrazione o convenienza attestata. Nessuna correzione richiesta dal report. Non copiati importi o citazioni nel diario.

Acquisito il risultato nominale della prova manuale richiesta dopo lo Step 36. Il report non espone le misure del broker: da questo solo file non si dimostra l’attraversamento del nuovo percorso. runs/s01_inference_gateway.jsonl non presente al momento del controllo. Restano report C006 e pilota C001/C006 con controllo diretto di gateway_inference_authorized, gateway_inference_completed, esiti, fasi e pulizia. S01 rimane aperto.


## Step 38 — Verifica reale del percorso inferenza e residuo S01

Letto report-locale-23.json: C006, versione 0.8.0, partial; S-01 blocked/input_not_ready per capitale mancante, confronto mutuo not_calculated, S-02 completed con sola fonte fiscale simulata. Tre verificatori eseguiti: nove fatti verificati, zero problemi; not_calculated_as_declared vero; nove controlli fiscali veri. Nessun dato mancante ricostruito o conclusione di spettanza. Nessun importo o citazione copiato nel diario.

Letti direttamente entrambi i record di runs/s01_inference_gateway.jsonl, una ripetizione ciascuno. C001 completed, passed=true: entrambi i rami con gateway_inference_authorized=1 e gateway_inference_completed=1, inference_catalog_version=0.1.0, una chiamata MCP e una Ollama per ramo, fonte verificata e assenza di errori. C006 partial, passed=true: S-01 fermo alla sola fase request_view, input_not_ready e misure vuote; S-02 completed con gli stessi indicatori del broker a 1. automatic_session_closed e cleanup_verified veri in entrambi. Le misure attestano l’utilizzo del broker nel percorso osservato; cleanup_verified riguarda il gateway, non dimostra da solo la pulizia degli store degli agenti. I tempi della richiesta Ollama sono inferiori ai corrispondenti roundtrip gateway; nessuna somma di tempi annidati né deduzione di accelerazione. Nessuna credenziale o corpo documentale nei record letti.

Completata la verifica manuale del secondo incremento S01 (inferenza), insieme allo Step 37. S01 complessivo ancora aperto: manca completare catalogo fidato degli strumenti e autorizzazione delle richieste/uscite dei connettori MCP. L’architettura della tesi mantiene il client MCP nello specialista e il server MCP come adattatore della fonte: non occorre spostare l’intera comunicazione MCP nell’orchestratore o eliminare questo confine. Va invece estesa l’autorità del gateway sulle operazioni ammesse e sulle eventuali richieste esterne del connettore. Le fixture correnti non hanno uscite reali: non costituiscono una prova di controllo di tali uscite. Rilevazione PII/valori vietati resta S02; non aggirabilità di rete e autenticazione completa restano S03. Non dichiarato completato S01, nessun commit creato.


## Step 39 — Completamento del catalogo MCP e chiusura S01

### Incremento conclusivo

L’utente ha chiesto di completare S01 dopo la verifica degli incrementi A2A e inferenza. Aggiunti gateway/tool_egress.py, services/tool_client.py e services/source_client.py. L’architettura conserva gli specialisti come client MCP e i server MCP come adattatori delle fonti. Prima di avviare il server, lo specialista richiede al gateway l’autorizzazione dello strumento e degli argomenti. Il server MCP richiede poi la fonte tramite il proxy del gateway. In produzione il catalogo 0.1.0 contiene soltanto lookup_rates/services.rates_mcp e lookup_tax/services.tax_mcp con le rispettive fixture locali: nessun endpoint Internet reale configurato.

Il gateway lega autorizzazioni a incarico, scenario, correlazione, scadenza e credenziale temporanea. Confronta gli argomenti con la vista autorizzata in forma canonica, compresi tipi e campi; sceglie server, tool e destinazione dal catalogo fidato. Una credenziale distinta e monouso per la fonte è iniettata nel sottoprocesso MCP tramite ambiente e inviata al gateway nell’intestazione Authorization. Non è un argomento dello strumento né un campo di evidenza o report. Autorizzazione strumento e richiesta fonte sono consumate una sola volta; non sono previsti retry o fallback. La revoca comune della delega/sessione elimina anche la possibilità di usare la credenziale fonte.

POST /internal/tools/authorize e POST /internal/sources sono i nuovi endpoint applicativi. Fonte, metodo, intestazioni e corpo devono rispettare il template. Percorsi o query aggiunti, campi arbitrari, credenziali sbagliate, scenari o correlazioni differenti sono negati prima del trasporto; corpi opachi o metodi fuori schema sono rifiutati. Il proxy HTTP, disponibile per futuri adattatori fidati ma senza fonti reali attive, ricostruisce il corpo dai soli campi autorizzati; non inoltra credenziali interne o intestazioni applicative del chiamante. Configurazioni HTTP con credenziali in URL, query o frammenti sono rifiutate. Qualunque redirect è negato senza seguire Location. Dinieghi e timeout delle fonti sono convertiti dai connettori in esiti strutturati e dagli agenti in blocked/not_authorized o failed/timeout. La verifica dell’evidenza avviene dopo la chiusura dei contesti MCP, conservando la distinzione della provenienza mancante.

Misure locali aggiunte dal broker: gateway_tool_authorized, gateway_source_authorized, gateway_source_completed, gateway_source_ms e tool_catalog_version. I tempi delle fonti sono compresi nel giro MCP e non vanno sommati ai tempi che li includono. Nessun contenuto documentale o credenziale aggiunto alle misure.

### Fixture negative e configurazione fidata

Aggiunta services/forbidden_source_mcp, esclusivamente fixture avversaria: tenta di inserire un campo aggiuntivo nella richiesta fonte. Non è selezionata nel catalogo nominale. Le fixture precedenti restano separate dalla demo. Per autorizzare la fixture lenta nelle prove timeout/recupero, avviare il gateway con TESI_MCP_PROFILE=market_timeout: abilita la scelta esplicita di services.slow_rates_mcp e mantiene il nominale per le richieste successive, senza cambiare il processo agente. TESI_MCP_PROFILE=missing_source seleziona invece services.missing_source_mcp per entrambi gli scenari. Il profilo si sceglie nell’ambiente fidato del gateway prima dell’avvio, non attraverso richieste o output remoti. Profilo ignoto: avvio rifiutato. Alla fine delle prove ripristinare nominal e riavviare gateway. Verificate separatamente le selezioni dei due profili mediante import in processi nuovi; non dichiarata una nuova prova reale completa del recupero dopo timeout.

### Suite automatica

Suite completa finale: **237 passed, 106 warning**, 8.95 secondi. Ventinove test aggiunti al conteggio precedente di 208; aggiornate le verifiche dei connettori e delle fixture in seguito al nuovo controllo. Gli avvisi aggiuntivi derivano dai nuovi percorsi SDK/ADK e dai server locali di prova; nessuna soppressione. git diff --check superato.

Nuove prove: catalogo di entrambi gli strumenti, argomenti e server non autorizzati, consumo monouso, sorgenti/percorsi/query/intestazioni/corpi vietati, credenziali non pertinenti o revocate, richieste non registrate, ingresso opaco/metodo errato, template HTTP e mancato inoltro del redirect. Il trasporto HTTP delle fonti è simulato; non è una prova contro una fonte Internet reale.

Due prove complete su porte loopback temporanee, senza sostituire i servizi della demo già avviati: API gateway, SDK A2A, agenti ADK, MCP stdio, callback HTTP del connettore al gateway e inferenza. La suite ordinaria simula solo Ollama; i risultati sono controllati per C001/C006 sia con catalogo nominale sia con connettore avversario selezionato nella sola configurazione di test. Verificati risultato parziale, diniego prima della fonte/inferenza, chiusura gateway e store A2A degli agenti vuoti.

### Verifica integrata con Ollama reale

Eseguita autonomamente anche la variante esplicita con Ollama reale, dati sintetici e gli stessi servizi temporanei locali. Non è una prova manuale eseguita da Fabio. Comando riproducibile: TESI_S01_REAL_OLLAMA=1 TESI_S01_EVIDENCE=runs/s01_complete_final.jsonl .venv/bin/python -m pytest -q tests/test_tool_egress.py -k whole_stack. Esito: **2 passed, 27 deselected, 38 warning**, 9.47 secondi. La durata del test non costituisce una misura sperimentale comparativa.

Letti direttamente i quattro record di runs/s01_complete_final.jsonl:

- C001 nominale: completed, entrambi i rami con contatori strumento/fonte autorizzata/fonte completata/inferenza completata uguali a 1.
- C006 nominale: partial; mercati bloccato in request_view con input_not_ready, nessuna misura di delega; fiscale completato con i quattro contatori a 1.
- C001 con connettore avversario: partial; mercati blocked/not_authorized, strumento autorizzato ma fonte autorizzata/completata e inferenza completata a 0. Fiscale completato con il percorso intero.
- C006 con connettore avversario: partial; il ramo mercati è fermato prima della delega per ingresso insufficiente; fiscale completato.

Tutti i record hanno real_ollama=true, passed=true e cleanup_verified=true. Il controllo di pulizia registrato riguarda il gateway; la prova controlla separatamente gli store A2A vuoti. Nessun source_token, inference_token, importo documentale o citazione nei record. Una precedente raccolta reale, prima dell’ultima rifinitura della scelta del modulo, resta in runs/s01_complete_validation.jsonl; la raccolta finale indicata sopra è quella riferita al codice conclusivo. Nessuna statistica di campagna ricavata da queste esecuzioni.

### Stato conclusivo e perimetro

S01 completato e rimosso dai residui per i due scenari e il catalogo locale attuale: autorità applicativa centralizzata per A2A, inferenza, strumenti e richieste fonti; template chiusi, diniego predefinito, credenziali temporanee per incarico, nessun inoltro di payload opachi, redirect o alternative non autorizzate. Il proxy HTTP è verificato su trasporto controllato, non su una fonte remota reale. Una nuova integrazione richiederà la propria voce di catalogo e prove equivalenti: nessuna fonte può essere attivata liberamente tramite URL fornita da agente o modello.

Restano S02 (rilevazione generale di PII/valori vietati, normalizzazione e misure privacy/utilità), S03 (identità dei processi e isolamento di rete/host), S04 (ulteriori attacchi), R01/R03 e campagna sperimentale. I processi non sono ancora impediti a livello host dal tentare connessioni dirette: S01 non dimostra non aggirabilità, anonimato o soddisfacimento completo dei requisiti di sicurezza della tesi. Le fonti reali X01 restano disabilitate fino ai controlli previsti. Nessun commit creato.

I servizi della demo dell’utente, rimasti aperti durante queste prove su porte diverse, devono essere riavviati per caricare il codice aggiornato. Non è necessario ripetere adesso le stesse prove per chiudere S01: la verifica integrata reale conclusiva è già acquisita e letta. Una conferma visiva nella demo resta possibile, distinta dalle evidenze sopra. Prossimo lavoro S02.
