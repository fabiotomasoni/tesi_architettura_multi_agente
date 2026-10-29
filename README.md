# Gateway locale per l’architettura multi-agente

Terzo incremento del prototipo di tesi: caricamento PDF da una pagina locale, estrazione deterministica, sessioni in memoria, controlli e viste minimizzate per S-01 (mutuo) e S-02 (interessi del mutuo). Include un agente mercati locale ADK/A2A, uno strumento MCP simulato e una sintesi Ollama. Non effettua ancora analisi finanziarie personalizzate o chiamate a fonti Internet.

## Prerequisiti

Python 3.11 o successivo, con pip e venv. Scaricare Python da https://www.python.org/downloads/ se necessario. Su Windows installare anche il launcher `py`. Aprire un terminale nella cartella della repository. Per il solo caricamento PDF non occorre Ollama; per la demo agentica serve Ollama in esecuzione con `llama3.2:3b`.

## Installazione e avvio su macOS

```bash
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m uvicorn gateway.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

## Installazione e avvio su Windows PowerShell

Eseguire i comandi dalla cartella principale della repository.

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn gateway.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Si usa direttamente Python dell'ambiente virtuale: non occorre attivarlo e non occorre modificare la policy di esecuzione PowerShell. Su entrambi i sistemi fermare il server con Ctrl+C. Negli avvii successivi basta ripetere il comando uvicorn dalla repository. Non usare più worker: le sessioni sono locali al processo. Non esporre il server in rete.

## Prima prova dal browser

Aprire **http://127.0.0.1:8000/**. Non occorre copiare JSON o identificativi.

1. Selezionare i quattro PDF `C001_*` in `dataset/Documents` con il selettore multiplo.
2. Lasciare selezionati entrambi gli scenari e premere **Carica e verifica**.
3. Leggere esito, campi estratti con documento/pagina e viste minimizzate. Il profilo completo è mostrato solo nella pagina locale; non è la vista destinata agli agenti.
4. Premere **Chiudi e cancella sessione**. Un nuovo caricamento chiude prima la sessione precedente.

Prove consigliate: C006 (capitale mancante), C011 (interessi mancanti), C016 (tasso ambiguo), C021 (periodi diversi ma entrambi gli scenari utilizzabili). Caricare un solo fascicolo per volta; è possibile usare soltanto il PDF mutuo o interessi per lo scenario corrispondente. Conto e busta paga sono riconosciuti come contesto, ma non sostituiscono campi obbligatori.

Il parser supporta **solo il template sintetico attuale**, non PDF bancari generici. Legge i PDF caricati, senza accedere a generatore, annotazioni o ground truth. PDF corrotti, cifrati, senza testo, duplicati o appartenenti a fascicoli diversi sono rifiutati. In questo incremento un documento rifiutato interrompe l'intero caricamento: i file validi non vengono recuperati separatamente. Limiti applicativi: quattro file, 5 MiB per file e 20 pagine per documento. Il limite in byte è verificato dopo la ricezione multipart, non è una protezione completa da richieste sovradimensionate.

L'API JSON e http://127.0.0.1:8000/docs restano disponibili per sviluppo. La nuova API è `POST /sessions/pdf`, con campi multipart `files` e `scenarios` (S-01/S-02).

## Struttura della repository

- `gateway/`: API, contratti, policy, parser PDF e pagina locale.
- `tests/`: verifiche del gateway e dei 25 fascicoli.
- `examples/`: ingressi JSON sintetici, conservati per test e sviluppo.
- `dataset/Documents/`: 100 PDF sintetici versionabili.
- `dataset/Scripts/`: generatore, dipendenze e istruzioni originali.
- `dataset/Scripts/state*/`: stato locale e annotazioni del valutatore, esclusi da Git.

Il gateway usa l’ambiente `.venv` nella radice della repository. Ambienti virtuali, cache, segreti e stato operativo del generatore sono esclusi dal versionamento tramite `.gitignore`.

Il file `.gitignore` si trova nella radice. I file il cui nome inizia con un punto possono essere nascosti: per visualizzarli usare `ls -la` su macOS oppure `Get-ChildItem -Force` in PowerShell.

## Contratti e regole attuali

Ogni fatto ha valore, unità, data di riferimento, provenienza (codice opaco del documento e pagina) e stato. Sono ammessi solo i campi dello schema. Gli errori 422 non ripetono il corpo ricevuto. Le categorie ammesse sono definite in `gateway/policy.py` e visibili negli esempi; unità e intervalli sono verificati dal codice. Le date S-01 devono coincidere; gli interessi S-02 devono riferirsi all'anno d'imposta indicato. La durata è generalizzata in fasce di cinque anni: (0,5], (5,10], ecc. La versione della policy accompagna ogni vista.

**Limite dell'ingresso JSON (conservato per sviluppo):** `validated` è una dichiarazione del chiamante. I controlli attuali verificano formato e coerenza, non la corrispondenza con un PDF. Non vengono inventati valori mancanti. Non inviare identificativi diretti: non fanno parte del contratto. Il parser PDF estrae soltanto etichette autorizzate e non inserisce anagrafica nel profilo. Non sono ancora presenti rilevazione PII generale o scansione di payload arbitrari. La provenienza conserva documento e pagina, ma non ancora coordinate/span. Il tipo di mutuo non esplicitato nel template è classificato genericamente come `other`; la ristrutturazione è mappata nella categoria fiscale generale `other`.

Le sessioni vengono eliminate con DELETE o all'arresto ordinato; la scadenza di 30 minuti è applicata in modo pigro alla successiva creazione/accesso. Non è un timer di cancellazione immediata. L'eliminazione rimuove i riferimenti applicativi, senza garanzie di azzeramento fisico della RAM o dello swap. Nessun profilo viene scritto dall'applicazione su disco. Il gestore multipart può usare file temporanei locali, chiusi al termine del caricamento. Il testo originale non viene conservato nella sessione. La chiusura della scheda invia una richiesta di cancellazione best effort, senza garanzia in caso di crash o rete interrotta; usare il pulsante esplicito.

## Test

Da un secondo terminale nella repository:

macOS:
```bash
.venv/bin/python -m pytest -q
```

Windows PowerShell:
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Stato e passi successivi

Realizzati: ingresso PDF del dataset, pagina di caricamento, contratti JSON, sessioni, controlli per scenario, viste, dinieghi e chiusura esplicita. Da implementare: parser per formati generici, verifica completa della provenienza, proxy esterno, isolamento, LangGraph, secondo specialista, report, tracce sperimentali e finalizzazione automatica del workflow. Questo incremento non dimostra ancora le proprietà di sicurezza dell'architettura completa.

Le decisioni e le verifiche di ogni step sono registrate in `DIARIO_PROGETTO.md`. Le dipendenze in `pyproject.toml` hanno intervalli compatibili; `requirements-lock.txt` registra le versioni dell'ambiente verificato. Per riprodurlo, dopo la creazione dell'ambiente eseguire `python -m pip install -r requirements-lock.txt` usando il percorso di Python dell'ambiente indicato sopra, quindi `python -m pip install --no-deps -e .`.

Riferimenti di installazione: https://fastapi.tiangolo.com/virtual-environments/ e https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/.


## Demo agente mercati — A2A, ADK, MCP e Ollama

Eseguire dalla radice della repository. Aggiornare prima le dipendenze con `.venv/bin/python -m pip install -e '.[dev]'` su macOS oppure `.\.venv\Scripts\python.exe -m pip install -e ".[dev]"` su Windows PowerShell. L'installazione ADK include molte dipendenze Google, ma questa demo non richiede chiavi Google e non usa inferenza cloud.

1. Avviare l'app Ollama e scaricare il modello: `ollama pull llama3.2:3b`.
2. In un terminale avviare il servizio mercati.

macOS:
```bash
.venv/bin/python -m uvicorn services.market_agent:app --host 127.0.0.1 --port 8001 --no-access-log
```

Windows PowerShell:
```powershell
.\.venv\Scripts\python.exe -m uvicorn services.market_agent:app --host 127.0.0.1 --port 8001 --no-access-log
```

3. In un secondo terminale avviare il gateway con il comando già indicato (porta 8000).
4. Aprire http://127.0.0.1:8000/, caricare un fascicolo completo (ad esempio C025) e premere **Esegui agente mercati (A2A → MCP → Ollama)**.
5. Il risultato deve avere `status: completed`, `simulated: true`, `source_id: simulated-rates-v1`, tasso sintetico e sintesi esplicitamente non verificata. Chiudere la sessione con il pulsante. Fermare entrambi i servizi con Ctrl+C.

Il server MCP stdio viene avviato e chiuso dall'agente, senza un terzo terminale. Il modello è fissato a llama3.2:3b; contesto 4096 e massimo 200 token generati. Le richieste hanno una scadenza di 120 secondi. Nessun download automatico o sostituzione di modello. Ollama riceve soltanto l'evidenza simulata; non riceve PDF o importi esatti.

### Percorso e limiti verificabili

`POST /sessions/{id}/markets` richiede la vista al gateway, valida il contratto e controlla nome, endpoint, versione e skill della Agent Card locale prima della delega A2A. Si usa A2A SDK 0.3.x, coerente con la versione citata nella tesi. Il servizio deriva da ADK BaseAgent: il flusso è programmato, non pianificato liberamente dal modello. MCP recupera una fixture fissa; Ollama ne sintetizza il contenuto. La sintesi non costituisce evidenza e non può modificare i campi della fonte strutturata.

L'agente serializza le richieste e cancella sessioni ADK e task A2A al termine della risposta, anche in caso di errore. Non supporta cronologia, continuazioni o recupero dei task dopo la richiesta. Il gateway mantiene la propria sessione fino alla chiusura/TTL. Non è ancora implementata la finalizzazione globale di un workflow LangGraph.

`failed` segnala il fallimento dell'attività; HTTP 502 indica delega, Card o risposta non valida; HTTP 409 indica dati documentali insufficienti. Il supporto ADK ad A2A emette avvisi sperimentali: le versioni testate sono registrate in requirements-lock.txt. Mancano autenticazione, isolamento di rete e proxy: gli endpoint locali e i contratti chiusi non dimostrano da soli la sicurezza completa prevista dalla tesi.

Riferimento ADK: https://google.github.io/adk-docs/a2a/quickstart-exposing/.

## Pilota e test del primo specialista

La procedura completa è nello **Step 05 di DIARIO_PROGETTO.md**. Nuove misure nella risposta: creazione vista, controllo Card, round trip A2A, MCP (avvio/inizializzazione/chiusura inclusi), Ollama, caricamento modello e token. I tempi sono annidati: non sommarli. I conteggi indicano richieste applicative, non tutti i messaggi di protocollo.

Con i tre servizi avviati, da un terzo terminale:

macOS:
```bash
.venv/bin/python scripts/run_pilot.py --repetitions 3
```

Windows PowerShell:
```powershell
.\.venv\Scripts\python.exe scripts/run_pilot.py --repetitions 3
```

Il comando usa C001, C024, C006 e C016, con sessioni indipendenti e verifica della cancellazione gateway. Scrive in append `runs/pilot.jsonl`, escluso da Git: solo metadati, esiti e misure, senza profili, prompt o sintesi. Conservare separatamente l'ID/digest del modello mostrato da `ollama list` e la versione `ollama --version`. Il tag del modello da solo non è un identificativo immutabile. Le misure dettagliate attuali sono disponibili per attività completate; un guasto conserva l'esito e il tempo osservato dal pilota, senza attribuire arbitrariamente il guasto a una sottofase. La pulizia ADK/A2A è verificata dai test automatici, non dal controllo gateway del pilota.

## Timeout controllato

Lo Step 06 del diario documenta risultati del primo pilota e prova dedicata. Fermare l'agente normale e avviare **al suo posto** `services.timeout_agent:app`, con lo stesso comando uvicorn e porta 8001. La fixture MCP attende 10 s, mentre l'attività ha budget 2 s. Poi eseguire:

```bash
.venv/bin/python scripts/run_pilot.py --cases C001 --expect timeout --repetitions 3 --output runs/timeout.jsonl
```

Su Windows PowerShell usare `.\.venv\Scripts\python.exe` al posto di `.venv/bin/python`. Attesi HTTP 200, failed, error_code timeout, passed=true e cancellazione gateway verificata. Tornare poi a services.market_agent:app ed eseguire un caso nominale per controllare il ripristino. Questa fixture verifica timeout durante MCP, non durante Ollama. Non usare il servizio lento per la demo normale.

Il runner supporta anche `--expect agent-off` (502 atteso) e `--expect ollama-off` (200 failed atteso): nei test negativi passed confronta così con l'esito negativo previsto.

Per verificare disponibilità dopo timeout **senza riavvio**, usare invece `services.recovery_agent:app`: prima richiesta lenta, successive normali. Procedura nello Step 08 del diario. I risultati riportano `measurements.agent_boot_id`; deve coincidere nelle due richieste. Non premere il pulsante agente nel browser durante la sequenza, perché consumerebbe la prima richiesta della fixture.
