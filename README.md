# Analisi locale di documenti finanziari

Prototipo di tesi che legge PDF sintetici, affida attività a due specialisti locali — mercati e fiscalità — e produce un report con dati documentali, fonti e limiti. Le attività indipendenti vengono coordinate da LangGraph. Gli specialisti richiedono l’inferenza al gateway, che controlla l’incarico e costruisce il prompt per Ollama. Anche gli strumenti MCP ottengono le fonti simulate attraverso il gateway, con autorizzazioni temporanee per il compito.

**Le fonti attuali sono simulate.** Il report riproduce fedelmente i dati delle simulazioni e confronta due scenari ipotetici del mutuo. Non fornisce quotazioni reali, consigli finanziari o attestazioni fiscali. Sono supportati i PDF del dataset incluso, non documenti bancari generici.

## Cosa serve

- Python 3.11 o successivo, disponibile su [python.org](https://www.python.org/downloads/).
- [Ollama](https://ollama.com/download) installato e aperto.
- Docker Desktop installato e avviato per la modalità isolata.
- Connessione Internet per installare dipendenze e scaricare i modelli. L'elaborazione della demo avviene localmente.

Aprire i terminali nella cartella principale della repository. Non occorrono chiavi API per usare la demo.

## 1. Installare il progetto

### macOS

```bash
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

### Windows PowerShell

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Non occorre attivare l'ambiente virtuale. Per aggiornare una copia già installata, ripetere solo l'ultimo comando.

## 2. Scaricare i modelli

Con Ollama aperto, eseguire una volta:

```bash
ollama pull llama3.2:3b
ollama pull qwen3:1.7b
```

## 3. Avviare la demo isolata

Installare e aprire Docker Desktop: [macOS](https://docs.docker.com/desktop/setup/install/mac-install/) oppure [Windows](https://docs.docker.com/desktop/setup/install/windows-install/). Lasciare aperto anche Ollama. Tutti i comandi seguenti vanno eseguiti dalla cartella della repository.

La modalità isolata esegue gateway e specialisti nei container. Un piccolo ponte sul computer ritira dal gateway le richieste autorizzate e usa Ollama locale; non apre porte aggiuntive per Ollama. Gli originali sono caricati dal browser e non vengono montati nei container degli specialisti.

**Prima preparazione, macOS:**

```bash
.venv/bin/python scripts/setup_isolation.py
```

**Prima preparazione, Windows PowerShell:**

```powershell
.\.venv\Scripts\python.exe scripts/setup_isolation.py
```

La preparazione genera credenziali locali escluse da Git; se già presenti le mantiene. Non condividerle. Costruire poi le due immagini, su entrambi i sistemi:

```bash
docker build -f deployment/Dockerfile -t tesi-s03-app:local .
docker build -f deployment/Dockerfile.netguard -t tesi-s03-netguard:local .
```

Ripetere la costruzione dopo modifiche al codice; per gli avvii ordinari non serve.

**Avvio dei servizi, macOS e Windows:**

```bash
docker compose -f compose.isolated.yaml up -d --no-build
```

**Avvio del ponte, in un terminale da lasciare aperto:**

macOS:

```bash
.venv/bin/python scripts/run_ollama_bridge.py
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe scripts/run_ollama_bridge.py
```

Se il ponte o Ollama non sono disponibili, le inferenze non vengono completate: non è previsto un percorso alternativo.

Per fermare la demo, premere **Ctrl+C** nel terminale del ponte e poi eseguire:

```bash
docker compose -f compose.isolated.yaml --profile verification down
```

Il comando ferma anche gli eventuali componenti temporanei delle prove. Le verifiche vengono guidate passo per passo e riassunte nel diario.

## 4. Caricare i PDF e leggere il report

1. Aprire [la pagina locale](http://127.0.0.1:8080/).
2. Selezionare fino a quattro PDF dello stesso fascicolo in `dataset/Documents`, per esempio tutti i file `C001_*`.
3. Scegliere gli scenari desiderati e premere **Carica e verifica**.
4. Premere **Esegui scenari selezionati e chiudi sessione**.
5. Leggere il documento con tabelle, fonti e limiti. **Stampa / salva PDF** usa la funzione del browser; **Esporta dati JSON** conserva i dati verificabili. Il salvataggio è una scelta dell’utente.

La pagina mostra la richiesta e gli esiti dei due specialisti; le singole fasi durante l’esecuzione non sono ancora visualizzate in tempo reale. I dati tecnici restano in una sezione espandibile.

Il report distingue valori trasformati, dati mancanti o non specificati e mostra citazioni del testo di origine con un riepilogo di completezza per scenario. La sezione confronti distingue valori coerenti, conflitti e informazioni non confrontabili, mantenendo le provenienze. Il confronto del mutuo mostra rate e interessi teorici a parità di debito e durata: costi esclusi e tassi ipotizzati costanti, anche per il variabile. La rata del documento resta distinta da quella ricalcolata. Il riepilogo fiscale mostra anche interessi × quota come semplice ripartizione ipotetica: vale solo se gli interessi riguardano l’intero mutuo e non sono già ripartiti. Non è un importo detraibile né una detrazione spettante. Un esito completo indica che tutte le attività richieste sono terminate. Un esito parziale conserva le attività riuscite e spiega quelle bloccate, fallite o non verificate. Un risultato senza provenienza obbligatoria è indicato come non verificato ed escluso dai calcoli. La sessione viene chiusa automaticamente al termine; per ripetere l'analisi caricare nuovamente i PDF.

Per provare un caso incompleto usare `C006_*`: manca il capitale del mutuo, quindi l'attività mercati viene bloccata e quella fiscale può proseguire. Conto e busta paga sono riconosciuti, ma non aggiungono ancora dati ai due scenari.

Prima delle chiamate, il gateway applica anche un filtro locale per identificativi, entità e valori sensibili conosciuti della sessione. Il filtro può commettere errori e affianca le viste ridotte e i destinatari autorizzati; non garantisce anonimato assoluto.

Il report esportato contiene importi esatti. La demo non conserva uno storico dei profili e non salva automaticamente i report sul server. Il prototipo non ha ancora tutti i controlli di sicurezza previsti dalla tesi: usare il dataset sintetico e mantenere i servizi accessibili solo localmente.

## Documentazione del progetto

- [Diario di progetto](DIARIO_PROGETTO.md): sintesi delle modifiche e delle verifiche.
- [Attività da completare](DA_IMPLEMENTARE.md): lavori residui, priorità e criteri di completamento.
