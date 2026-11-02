# Analisi locale di documenti finanziari

Prototipo di tesi che legge PDF sintetici, affida attività a due specialisti locali — mercati e fiscalità — e produce un report con dati documentali, fonti e limiti. Le attività indipendenti vengono coordinate da LangGraph. Gli specialisti richiedono l’inferenza al gateway, che controlla l’incarico e costruisce il prompt per Ollama. Anche gli strumenti MCP ottengono le fonti attraverso il gateway, con autorizzazioni temporanee per il compito.

**La modalità predefinita usa fonti simulate; è disponibile anche una fonte BCE reale per i mercati.** Il report riproduce fedelmente i dati delle simulazioni e confronta due scenari ipotetici del mutuo. Non fornisce quotazioni reali, consigli finanziari o attestazioni fiscali. Sono supportati i PDF del dataset incluso, non documenti bancari generici.

## Cosa serve

- Python 3.11 o successivo, disponibile su [python.org](https://www.python.org/downloads/).
- [Ollama](https://ollama.com/download) installato e aperto.
- Docker Desktop installato e avviato per la modalità isolata.
- Connessione Internet per installare dipendenze e scaricare i modelli. L’elaborazione avviene localmente; la modalità BCE consulta una fonte pubblica via Internet.

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

Durante l’elaborazione puoi premere **Annulla analisi e cancella sessione**. Il gateway interrompe l’analisi, revoca gli accessi temporanei e rifiuta risultati tardivi; puoi poi caricare un nuovo fascicolo. Anche la chiusura della connessione interrompe la richiesta. Il ponte aggiornato chiude la richiesta locale a Ollama quando l’incarico viene revocato: questo non certifica l’arresto immediato del calcolo interno al modello. Dopo questo aggiornamento ricostruire l’immagine dell’applicazione e riavviare il ponte.

Se la consegna del report fallisce, il gateway non lo conserva per un successivo recupero. Dopo un arresto del gateway, caricare nuovamente i PDF per una nuova analisi: la sessione interrotta non riprende automaticamente. Le prove guidate di questi percorsi sono descritte nel [protocollo di valutazione](PROTOCOLLO_VALUTAZIONE.md).

È disponibile anche una prova guidata di sostituzione dello strumento mercati: confronta lo stesso report prima, durante e dopo il cambio del server MCP, mantenendo gli agenti. Usa fonti e risposte del modello simulate; istruzioni e limiti sono nel protocollo, senza cambiare l’avvio ordinario della demo.

## Documentazione del progetto

I nuovi piloti salvano anche una traccia di soli tempi, conteggi ed esiti, senza documenti o prompt. La procedura guidata per verificarla è nel [protocollo di valutazione](PROTOCOLLO_VALUTAZIONE.md#tracciamento-e-budget-del-prototipo); il report per l’utente conserva gli stessi dati e contenuti.

Se il controllo delle tracce si interrompe, il file indica `passed: false` e la fase interessata, conservando le sole evidenze raccolte. Per riprovare usare un nome di output nuovo: le prove precedenti non vengono sovrascritte.

- [Diario di progetto](DIARIO_PROGETTO.md): sintesi delle modifiche e delle verifiche.
- [Attività da completare](DA_IMPLEMENTARE.md): lavori residui, priorità e criteri di completamento.

## Fonte BCE reale per l’agente mercati

Fermare il ponte precedente con Ctrl+C. Dopo una modifica al codice, ricostruire l’immagine e avviare questa configurazione (macOS e Windows):

```bash
docker build -f deployment/Dockerfile -t tesi-s03-app:local .
docker compose -f compose.isolated.yaml -f compose.ecb.yaml --profile verification up -d --no-build
```

Avviare poi un solo ponte, in un terminale separato:

```bash
# macOS
.venv/bin/python scripts/run_ollama_bridge.py --enable-ecb
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe scripts/run_ollama_bridge.py --enable-ecb
```

Aprire http://127.0.0.1:8080 e caricare i PDF come prima. Il report distingue la statistica BCE dai riferimenti fiscali, ancora simulati. Mostra valore, mese di osservazione, momento del recupero e collegamento istituzionale. Si consulta l’ultima pubblicazione mensile disponibile: non sono offerte in tempo reale. L’indicatore aggregato AAR/NDER non viene sostituito al TAN nel calcolo della rata. Se la fonte non risponde, il report dichiara il limite senza usare una simulazione di riserva.

Agenti e strumenti restano isolati: il ponte esegue soltanto la richiesta pubblica fissata dal gateway, senza documenti o dati personali. Per tornare alle fixture, fermare il ponte, eseguire l’avvio Compose senza `-f compose.ecb.yaml` e riavviare il ponte senza `--enable-ecb`.

Per controllare il JSON esportato nella modalità BCE:

```bash
# macOS; sostituire report.json con il file esportato
.venv/bin/python scripts/check_ecb_report.py report.json
```

```powershell
.\.venv\Scripts\python.exe scripts/check_ecb_report.py report.json
```

Il controllo verifica la coerenza con la risposta pubblica salvata nel report; non effettua una nuova consultazione Internet.

## Pubblicazioni fiscali ufficiali

È disponibile la consultazione delle istruzioni 730/2025 per l’anno d’imposta 2024 e 730/2026 per il 2025. Il gateway seleziona l’edizione annuale e controlla il PDF recuperato. Il report cita estratti e pagine, senza attribuire automaticamente un codice fiscale o una detrazione. La dicitura generica «ristrutturazione» non basta a stabilire i requisiti. Gli estratti non sono una checklist esaustiva; le condizioni personali restano da verificare.

Fermare il ponte precedente con Ctrl+C, ricostruire l’immagine e avviare entrambe le fonti reali:

```bash
docker build -f deployment/Dockerfile -t tesi-s03-app:local .
docker compose -f compose.isolated.yaml -f compose.ecb.yaml -f compose.ade.yaml --profile verification up -d --no-build
```

Nel terminale separato, avviare un solo ponte:

```bash
# macOS
.venv/bin/python scripts/run_ollama_bridge.py --enable-ecb --enable-ade
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe scripts/run_ollama_bridge.py --enable-ecb --enable-ade
```

Usare la stessa pagina locale. Se il documento ufficiale cambia, non è disponibile o l’anno non è supportato, l’attività fiscale fallisce esplicitamente senza sostituzioni simulate. Una nuova edizione richiede revisione del catalogo: «fonte ufficiale» non significa applicabilità personale verificata. La ripartizione interessi × quota resta un’ipotesi aritmetica. Per tornare alle fixture usare soltanto il file Compose base e il ponte senza flag.

Controllo del JSON esportato (su Windows usare `.\.venv\Scripts\python.exe`):

```bash
.venv/bin/python scripts/check_ade_report.py report.json
.venv/bin/python scripts/check_tax_application.py report.json
```

I controlli rigiocano la verifica locale del catalogo e dei dati: non sono una nuova consultazione Internet o una verifica della spettanza.

## Analisi locale del contratto

Il report distingue il modello teorico del contratto dal confronto con un tasso alternativo. Se i dati sono sufficienti, mostra rata mensile teorica, interessi residui teorici e scostamento dalla rata documentata anche quando la fonte mercati non è disponibile o il dato BCE non è un TAN. Per un tasso variabile o misto si tratta soltanto di uno scenario con tasso mantenuto costante. La rata del documento non viene corretta e il risultato non dimostra convenienza o errori contrattuali.

Per verificare il JSON esportato:

```bash
# macOS
.venv/bin/python scripts/check_mortgage.py report.json
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe scripts/check_mortgage.py report.json
```

Il controllo ricalcola il modello con un metodo numerico indipendente e verifica gli scostamenti. La BCE resta contesto statistico; nessuna rata alternativa viene inventata.

## Approfondimenti fiscali nel report

Con una fonte AdE verificata, il report presenta i dati documentali e una selezione di condizioni da approfondire, ciascuna con anno, pagina ed estratto ufficiale. Acquisto, costruzione e finalità generica «ristrutturazione» restano distinti: nessun regime o codice è assegnato automaticamente. Le condizioni sono da verificare; le informazioni necessarie potrebbero essere nei PDF senza essere estratte dai campi supportati. Il riepilogo non è una checklist esaustiva e non determina la spettanza. La ripartizione interessi × quota resta separata e ipotetica. Senza fonte ufficiale utilizzabile, il report non inventa condizioni normative.

Verifica del JSON esportato:

```bash
# macOS
.venv/bin/python scripts/check_tax_review.py report.json
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe scripts/check_tax_review.py report.json
```

Il controllo verifica coerenza con i dati documentali, selezione delle condizioni, citazioni del catalogo e assenza di spettanza attribuita. Non effettua una nuova consultazione Internet né certifica il diritto fiscale.

## Pilota a singolo agente e multi-agente

La baseline usa un agente generalista per S-01 e S-02. Il confronto preliminare usa gli stessi PDF, gateway, controlli, calcoli e report; fonti simulate fissate e `llama3.2:3b` per tutte le attività. Entrambe le organizzazioni eseguono le attività in sequenza, con budget totale di sessione di 120 secondi. Non è la campagna finale e non include la modalità senza minimizzazione.

Prima di cambiare configurazione, attendere la fine delle analisi, fermare il ponte con Ctrl+C e arrestare i container della demo:

```bash
docker compose -f compose.isolated.yaml --profile verification down
```

Preparare una volta le identità della baseline (le identità della demo restano separate):

```bash
# macOS
.venv/bin/python scripts/setup_baseline.py
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe scripts/setup_baseline.py
```

Dopo aver costruito l’immagine come per la demo, avviare **una sola configurazione**:

```bash
# Singolo agente
docker compose -f compose.isolated.yaml -f compose.experiment-single.yaml up -d --no-build
```

Nel terminale separato, mantenendo Ollama aperto:

```bash
.venv/bin/python scripts/run_experiment_bridge.py --organization single
```

Nel terminale dei test:

```bash
.venv/bin/python scripts/run_baseline_pilot.py --organization single --output runs/baseline_single_manual.jsonl
```

Per passare al multi-agente, fermare il ponte, arrestare prima la configurazione singola e poi avviare quella multi:

```bash
docker compose -f compose.isolated.yaml -f compose.experiment-single.yaml down
docker compose -f compose.isolated.yaml -f compose.experiment-multi.yaml up -d --no-build
```

Avviare il ponte con `--organization multi`, quindi eseguire il pilota con `--organization multi --output runs/baseline_multi_manual.jsonl`. Su Windows sostituire `.venv/bin/python` con `.\.venv\Scripts\python.exe` in tutti i comandi Python. Usare nomi nuovi per nuove prove: lo script aggiunge righe ai file esistenti.

Confrontare infine:

```bash
.venv/bin/python scripts/check_baseline_pilot.py runs/baseline_single_manual.jsonl runs/baseline_multi_manual.jsonl
```

I cinque casi previsti sono C001/C024 completi e C006/C011/C016 parziali. Il controllo verifica esiti, pulizia, pesi del modello, impostazioni, risultati strutturati e conteggi delle chiamate. La prosa LLM resta esclusa dal report: questo pilota confronta funzionamento e coordinamento, non dimostra un vantaggio qualitativo dei modelli. I tempi delle fasi possono essere annidati e non vanno sommati indiscriminatamente.

Per tornare alla demo, fermare il ponte sperimentale, eseguire `down` con il file sperimentale usato, poi ripetere l’avvio BCE/AdE e del relativo ponte descritto sopra. Le fonti reali sono rifiutate dai profili sperimentali.

## Piloti senza minimizzazione finanziaria (S−P/M−P)

Nel laboratorio è possibile condividere con ciascun agente e con i suoi MCP/modello l’intero profilo finanziario estratto: valori esatti, unità, periodi e stati di validazione, senza selezione per dominio o durata in fasce. I valori assenti restano assenti e quelli ambigui mantengono il loro stato. PDF, testo grezzo, citazioni documentali e identificativi diretti restano esclusi dai messaggi in tutte le configurazioni: questo confronto riguarda la minimizzazione dei **campi finanziari**, non la rimozione di nomi o IBAN.

Tutti i profili sperimentali ora accettano soltanto i PDF del corpus sintetico fissato, verificati tramite digest; l’ingresso JSON diretto è disabilitato. Il gateway non monta il dataset. File rigenerati richiedono una revisione esplicita del manifest. Autenticazione, schemi, destinazioni, isolamento e budget restano attivi. Nessuna fonte o inferenza remota è disponibile.

Il protocollo aggiornato usa per tutti i profili lo stesso prompt strutturato «fonte + contesto», con contesto minimizzato o completo. **Rieseguire anche S+P/M+P** per il confronto a quattro celle: i precedenti piloti non sono mescolabili con questo protocollo. Rimangono validi come prove del precedente incremento.

Dopo aver fermato il ponte e arrestato la configurazione precedente, per S−P:

```bash
docker compose -f compose.isolated.yaml -f compose.experiment-single.yaml -f compose.experiment-unminimized.yaml up -d --no-build
```

Ponte in un terminale separato:

```bash
.venv/bin/python scripts/run_experiment_bridge.py --organization single --minimization disabled
```

Pilota:

```bash
.venv/bin/python scripts/run_baseline_pilot.py --organization single --minimization disabled --output runs/single_disabled_manual.jsonl
```

Per M−P usare il file `compose.experiment-multi.yaml` al posto di quello single e `--organization multi` nei comandi Python. Prima di ogni cambio fermare il ponte ed eseguire `down` con i file della configurazione corrente. Per S+P/M+P omettere il file unminimized e usare `--minimization active` in ponte e pilota. Usare quattro file JSONL nuovi. Su Windows sostituire `.venv/bin/python` con `.\.venv\Scripts\python.exe`.

Confronto finale dei quattro piloti:

```bash
.venv/bin/python scripts/check_factorial_pilot.py --single-active runs/single_active_manual.jsonl --multi-active runs/multi_active_manual.jsonl --single-disabled runs/single_disabled_manual.jsonl --multi-disabled runs/multi_disabled_manual.jsonl
```

Le nuove metriche riportano byte canonici e categorie delle viste autorizzate, senza valori. Non sono conteggi completi dei pacchetti di rete o prova di consegna di una chiamata fallita. Nei casi completati misurano il contesto autorizzato ai confini A2A, MCP e modello. Non si misura divulgazione reale a Internet: i quattro profili restano locali. Il report deterministico può rimanere uguale pur condividendo più dati; ciò non dimostra un miglioramento di utilità o qualità. Rubriche, soglie e campagna finale restano da completare.

## Preparazione della valutazione finale

Il pilota non sostituisce la valutazione della tesi. La bozza è in [PROTOCOLLO_VALUTAZIONE.md](PROTOCOLLO_VALUTAZIONE.md): criteri e soglie approvati, rubrica con un valutatore e verifiche ancora necessarie. Le annotazioni e la scheda vuota sono in `evaluation/`; sono materiale del valutatore, escluso dal runtime e dalle immagini Docker, non input per gli agenti. Nessun giudizio umano è già compilato.

Controllare la coerenza della bozza:

```bash
# macOS
.venv/bin/python scripts/check_evaluation_protocol.py
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe scripts/check_evaluation_protocol.py
```

Un esito senza problemi verifica la preparazione dei file, **non approva soglie o campagna finale**. Soglie, rubrica e trattamento dei tempi sono stati approvati dall’utente. Le annotazioni dei 25 fascicoli sono state confermate dall’utente; non sono punteggi di qualità dei report. Mancano ancora prove e strumenti finali, quindi il protocollo non è congelato. Non è necessario riavviare Docker per questo incremento.

La revisione del riferimento è completata per tutti i 25 fascicoli. Per consultare nuovamente il confronto con i PDF, è possibile generare una scheda; l’esempio seleziona i primi cinque casi rappresentativi:

```bash
# macOS
.venv/bin/python scripts/prepare_annotation_review.py
open runs/annotation_review_first5.html
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe scripts/prepare_annotation_review.py
Start-Process .\runs\annotation_review_first5.html
```

La scheda affianca valori attesi ed estratti, con collegamenti ai PDF da leggere. Controllare tutti i campi e segnalare le discordanze: nessuna conferma viene salvata automaticamente. Docker e Ollama non servono per questa revisione. Per gli altri casi usare `--cases C002 C003` oppure `--all`, con `--output runs/annotation_review_all.html`. Se il file esiste già, aprirlo oppure scegliere un nuovo nome; la generazione non sovrascrive le schede.
