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
