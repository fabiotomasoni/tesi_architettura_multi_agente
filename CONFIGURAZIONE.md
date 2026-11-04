# Configurazione

Questa guida avvia la demo isolata con Docker Desktop e Ollama sul computer. Tutti i comandi partono dalla cartella principale della repository, quella che contiene `pyproject.toml`. La demo non richiede chiavi API.

## Prerequisiti

- Python 3.11 o successivo; i container usano Python 3.12.
- Docker Desktop con Docker Compose e container Linux.
- Ollama avviato sul computer.
- Connessione Internet per installare dipendenze, costruire le immagini e scaricare i modelli. Le consultazioni pubbliche BCE e Agenzia delle Entrate sono facoltative.

Su Windows, apri **PowerShell** e usa Docker Desktop con il motore per container Linux (WSL 2). Su macOS, apri **Terminale**. I comandi Windows sono predisposti per PowerShell; la campagna della tesi è stata eseguita su macOS.

## 1. Ambiente Python e identità locali

**macOS**

```bash
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python scripts/setup_isolation.py
```

**Windows PowerShell**

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe scripts/setup_isolation.py
```

Non occorre attivare l’ambiente virtuale. L’ultimo comando crea le identità in `.local/` oppure mantiene quelle già presenti. Se la configurazione è incompleta, lo script lo segnala senza sovrascrivere le credenziali.

## 2. Modelli e immagini

**macOS e Windows**, con Docker Desktop e Ollama aperti:

```bash
docker compose version
ollama pull llama3.2:3b
ollama pull qwen3:1.7b
docker build -f deployment/Dockerfile -t tesi-s03-app:local .
docker build -f deployment/Dockerfile.netguard -t tesi-s03-netguard:local .
```

Per gli avvii successivi non serve riscaricare i modelli o ricostruire le immagini. Ricostruisci l’immagine dell’applicazione quando cambiano codice o dipendenze; ricostruisci quella di isolamento se cambia la sua configurazione di build.

## 3. Avviare la demo con fonti simulate

Nel primo terminale, **macOS e Windows**:

```bash
docker compose -f compose.isolated.yaml up -d --no-build
docker compose -f compose.isolated.yaml ps
```

Nel secondo terminale, dalla stessa cartella, avvia il ponte e lascialo aperto.

**macOS**

```bash
.venv/bin/python scripts/run_ollama_bridge.py
```

**Windows PowerShell**

```powershell
.\.venv\Scripts\python.exe scripts/run_ollama_bridge.py
```

Apri [la demo locale](http://127.0.0.1:8080/). Se non risponde, controlla Docker e lo stato dei container. Se la pagina si apre ma le inferenze falliscono, controlla che Ollama e il ponte siano attivi e che entrambi i modelli siano presenti in `ollama list`.

## 4. Usare la demo

1. Carica fino a quattro PDF di uno stesso fascicolo in `dataset/Documents`, per esempio tutti i `C001_*`.
2. Seleziona gli scenari e scegli **Carica e verifica**, poi **Avvia analisi**.
3. Leggi il risultato. Puoi scegliere **Scarica documento HTML**, **Esporta dati JSON** o **Stampa / salva PDF**.
4. Se vuoi provare un esito parziale, usa `C006_*`: la mancanza del capitale residuo blocca S-01 e consente S-02.

Per controllare il JSON di C001 con i quattro PDF e i due scenari, salva il file come `report.json` nella cartella di lavoro oppure sostituisci il percorso nei comandi.

**macOS**

```bash
.venv/bin/python scripts/check_report_provenance.py report.json
.venv/bin/python scripts/check_financial_context.py report.json
```

**Windows PowerShell**

```powershell
.\.venv\Scripts\python.exe scripts/check_report_provenance.py report.json
.\.venv\Scripts\python.exe scripts/check_financial_context.py report.json
```

Atteso: 13 fatti verificati, zero problemi e `passed: True` per il contesto finanziario. Questi controlli non assegnano voti alla qualità del report.

## 5. Abilitare le fonti pubbliche

Ferma il ponte precedente con **Ctrl+C**. Nel primo terminale, **macOS e Windows**:

```bash
docker compose -f compose.isolated.yaml -f compose.ecb.yaml -f compose.ade.yaml --profile verification up -d --no-build
```

Nel secondo terminale avvia **un solo ponte**.

**macOS**

```bash
.venv/bin/python scripts/run_ollama_bridge.py --enable-ecb --enable-ade
```

**Windows PowerShell**

```powershell
.\.venv\Scripts\python.exe scripts/run_ollama_bridge.py --enable-ecb --enable-ade
```

Per attivare una sola fonte, usa solo il relativo file Compose e il relativo flag del ponte. La fonte BCE è una statistica mensile aggregata; le edizioni fiscali configurate sono le istruzioni 730/2025 e 730/2026, per gli anni d’imposta 2024 e 2025. Se una fonte abilitata non è utilizzabile, la demo lo segnala senza sostituirla con una fonte simulata.

## 6. Arrestare o cambiare modalità

Ferma prima il ponte con **Ctrl+C**. Usa gli stessi file Compose dell’avvio, sostituendo `up -d --no-build` con `down`.

**Demo simulata, macOS e Windows**

```bash
docker compose -f compose.isolated.yaml down
```

**Demo BCE e Agenzia delle Entrate, macOS e Windows**

```bash
docker compose -f compose.isolated.yaml -f compose.ecb.yaml -f compose.ade.yaml --profile verification down
```

Per tornare alle fonti simulate, ripeti il punto 3 con il file Compose base e il ponte senza flag.

## 7. Test ed esperimenti

Per eseguire i test, dalla cartella della repository:

```bash
# macOS
.venv/bin/python -m pytest -q
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe -m pytest -q
```

Alcune prove di integrazione avviano processi e servizi temporanei in locale; la suite completa richiede più tempo delle prove mirate. Per le quattro configurazioni, la preparazione dei manifest e la raccolta delle evidenze segui il [protocollo di valutazione](PROTOCOLLO_VALUTAZIONE.md#verifica-del-quarto-blocco--valutazione-riproducibile). La demo con fonti pubbliche e la campagna sperimentale sono procedure separate.
