# Analisi locale di documenti finanziari

Prototipo di tesi che legge PDF sintetici, affida attività a due specialisti locali — mercati e fiscalità — e produce un report con dati documentali, fonti e limiti. Le attività indipendenti vengono coordinate da LangGraph.

**Le fonti attuali sono simulate.** Il report riproduce fedelmente i dati delle simulazioni, ma non fornisce quotazioni reali, consigli finanziari o attestazioni fiscali. Sono supportati i PDF del dataset incluso, non documenti bancari generici.

## Cosa serve

- Python 3.11 o successivo, disponibile su [python.org](https://www.python.org/downloads/).
- [Ollama](https://ollama.com/download) installato e aperto.
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

## 3. Avviare la demo

Lasciare Ollama aperto. Avviare ciascun comando in un terminale distinto e mantenerlo in esecuzione.

### macOS

Terminale 1 — specialista mercati:
```bash
.venv/bin/python -m uvicorn services.market_agent:app --host 127.0.0.1 --port 8001 --no-access-log
```

Terminale 2 — specialista fiscale:
```bash
.venv/bin/python -m uvicorn services.tax_agent:app --host 127.0.0.1 --port 8002 --no-access-log
```

Terminale 3 — pagina di caricamento:
```bash
.venv/bin/python -m uvicorn gateway.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

### Windows PowerShell

Terminale 1 — specialista mercati:
```powershell
.\.venv\Scripts\python.exe -m uvicorn services.market_agent:app --host 127.0.0.1 --port 8001 --no-access-log
```

Terminale 2 — specialista fiscale:
```powershell
.\.venv\Scripts\python.exe -m uvicorn services.tax_agent:app --host 127.0.0.1 --port 8002 --no-access-log
```

Terminale 3 — pagina di caricamento:
```powershell
.\.venv\Scripts\python.exe -m uvicorn gateway.app:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Per fermare la demo premere **Ctrl+C** nei tre terminali. Agli avvii successivi basta aprire Ollama e ripetere questi tre comandi. Se una porta risulta occupata, controllare che il relativo servizio non sia già aperto in un altro terminale.

## 4. Caricare i PDF e leggere il report

1. Aprire [la pagina locale](http://127.0.0.1:8000/).
2. Selezionare fino a quattro PDF dello stesso fascicolo in `dataset/Documents`, per esempio tutti i file `C001_*`.
3. Scegliere gli scenari desiderati e premere **Carica e verifica**.
4. Premere **Esegui scenari selezionati e chiudi sessione**.
5. Leggere le sezioni del report. **Esporta report JSON** salva una copia solo se richiesto.

Un esito completo indica che tutte le attività richieste sono terminate. Un esito parziale conserva le attività riuscite e spiega quelle bloccate o fallite. La sessione viene chiusa automaticamente al termine; per ripetere l'analisi caricare nuovamente i PDF.

Per provare un caso incompleto usare `C006_*`: manca il capitale del mutuo, quindi l'attività mercati viene bloccata e quella fiscale può proseguire. Conto e busta paga sono riconosciuti, ma non aggiungono ancora dati ai due scenari.

Il report esportato contiene importi esatti. La demo non conserva uno storico dei profili e non salva automaticamente i report sul server. Il prototipo non ha ancora tutti i controlli di sicurezza previsti dalla tesi: usare il dataset sintetico e mantenere i servizi accessibili solo localmente.

## Documentazione del progetto

- [Diario di progetto](DIARIO_PROGETTO.md): decisioni, implementazione, prove e risultati.
- [Attività da completare](DA_IMPLEMENTARE.md): lavori residui, priorità e criteri di completamento.
