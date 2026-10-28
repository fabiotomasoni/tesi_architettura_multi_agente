# Diario di progetto

Questo file viene aggiornato a ogni step di sviluppo con decisioni, motivazioni, modifiche, verifiche, problemi e soluzioni. Le funzionalità previste rimangono distinte da quelle implementate e verificate. Nuove scelte dubbie vengono sottoposte all'autore prima di procedere.

## Step 01 — Gateway con ingresso JSON

### Perimetro confermato

L'autore ha autorizzato Python, FastAPI e Pydantic; sessioni temporanee in memoria, validazione S-01/S-02, viste minimizzate e cancellazione. PDF, Ollama, LangGraph, ADK, A2A e MCP sono rinviati. Documentazione e messaggi applicativi in italiano; nomi del codice in inglese. Installazione documentata per macOS e Windows PowerShell.

### Decisioni e realizzazione

- API locale con un solo worker e sessioni identificate da UUID. Nessun database e nessuna scrittura dei profili su disco.
- Contratti Pydantic chiusi: campi sconosciuti rifiutati, senza riportare il corpo sensibile negli errori di schema.
- Un fatto contiene valore, unità, data, codice opaco del documento, pagina e stato. In questo incremento lo stato validated è dichiarato dal chiamante: non è una verifica documentale.
- Controlli semantici su categorie, unità, numeri, intervalli e date; dati insufficienti bloccano solo lo scenario interessato.
- Policy 0.1.0: viste costruite da campi ammessi; durata in fasce di cinque anni, limite inferiore escluso e superiore incluso. Gli importi esatti non entrano nelle viste.
- DELETE elimina la sessione; arresto ordinato svuota lo store. Scadenza di 30 minuti con rimozione pigra al prossimo accesso/creazione, non cancellazione temporizzata. Nessuna garanzia di azzeramento fisico della memoria.
- Esempi JSON sintetici per percorso completo e campo mancante; documentazione interattiva FastAPI per provare le richieste.

### Verifiche eseguite

Ambiente virtuale creato nella repository; dipendenze installate. Python 3.14, FastAPI 0.162.0 e Pydantic 2.14.1. Eseguito `python -m pytest -q`: **11 test superati**. Coperti viste dei due specialisti, campi mancanti/ambigui, unità, date, numeri negativi/frazionari, destinatario errato, attività non richiesta, mancata riflessione di un identificativo nell'errore, cancellazione e scadenza. Test API in processo; avvio di rete e Windows non verificati in questa sessione. Comandi Windows documentati con percorso diretto del Python virtuale per evitare problemi di attivazione PowerShell.

### Problemi e trattamento

- Python disponibile inizialmente privo di FastAPI: creato un ambiente isolato e installate le dipendenze, senza modificare l'ambiente globale.
- `pip freeze` ha tentato di risolvere la repository senza commit iniziale: generato requirements-lock.txt dai metadati delle distribuzioni installate, escludendo progetto e strumenti di installazione.
- Il TestClient della versione installata segnala la futura dismissione dell'integrazione httpx. I test passano; migrazione del client di test da valutare in uno step successivo, senza sopprimere l'avviso.

### Limiti e prossimo step

Nessuna estrazione o validazione contro PDF, nessuna scansione PII generale, proxy, isolamento, autenticazione, tracciamento sperimentale, inferenza o report. Il server è destinato soltanto a prove locali con dati sintetici. Il limite temporale delle sessioni e la chiusura esplicita non sostituiscono la finalizzazione completa del workflow prevista in tesi. I successivi collegamenti ai componenti agentici richiedono uno step concordato.


## Step 02 — Caricamento PDF e riordino

### Richiesta e decisioni confermate

L'autore richiede caricamento PDF semplice, integrazione del dataset e aggiornamento dei due documenti. Confermata la rinomina di `Dataset ` in `dataset` e l'esclusione da Git di ambienti, cache, segreti e stato operativo; nessun materiale preesistente eliminato.

### Modifiche realizzate

- Pagina locale alla radice: selezione multipla, scenari, invio, esiti, profilo con provenienza e viste automatiche; cancellazione con pulsante. API JSON conservata per compatibilità.
- Parser pypdf locale basato sulle etichette del template sintetico. Nessun accesso a ground_truth, generatore o risposte API. Anagrafica esclusa dal profilo; IBAN fittizio usato transitoriamente solo per impedire il mescolamento dei fascicoli.
- Numeri italiani convertiti in Decimal, tassi ambigui esclusi, campi mancanti non ricostruiti. Provenienza documento/pagina; coordinate/span rinviati. Il template non specifica una tipologia residenziale esplicita: si usa other senza inventarla. Ristrutturazione mappata a other.
- Certificazione annuale riferita al suo anno d'imposta, distinta dalla data della situazione mutuo: il gruppo periodi_diversi non viene erroneamente bloccato.
- Da uno a quattro PDF per caricamento, massimo 5 MiB e 20 pagine ciascuno. File non validi o duplicati bloccano il caricamento completo; recupero parziale dei PDF validi ancora da implementare.
- Ispezionati radice, gateway/static, tests, examples, dataset/Documents, dataset/Scripts e sottocartelle state, state_offline e .venv. .gitignore ricorsivo per prodotti Python, ambienti, cache, file editor/sistema e segreti; esclusioni specifiche per stato API, budget, ground truth, lock di generazione e anteprime. PDF, script, requisiti e .env.example conservati come sorgenti versionabili.

### Verifiche e problemi

37 test superati, inclusi tutti i 25 fascicoli reali del dataset caricato (100 PDF), mantenendo gli 11 test precedenti. Verificati assenza dell'anagrafica nei risultati, scenari incompleti/ambigui, periodi diversi, documenti misti, duplicati, file non PDF e disponibilità HTML. Nessun risultato finanziario o protocollo agentico misurato. Test eseguiti su macOS con TestClient; interazione visiva nel browser e Windows non ancora verificati.

Risolto il nome della cartella con spazio finale tramite rinomina autorizzata. Ambiente del generatore conservato ma potenzialmente non relocabile: da ricreare se necessario. Rimane l'avviso di deprecazione httpx del TestClient.

### Limiti

Supporto limitato al template, nessun OCR e nessun riconoscimento generale PII. Upload multipart può utilizzare temporanei locali, chiusi sempre nel finally; i limiti applicativi non impediscono da soli la ricezione di body molto grandi. Il browser mostra il profilo completo localmente e soltanto le viste ridotte sono destinate ai futuri agenti. Cancellazione alla chiusura scheda best effort; restano chiusura esplicita e TTL pigro. Proxy, isolamento e workflow agentico rimangono previsti. Per esperimenti futuri il parser specifico del template va dichiarato, senza presentare questi risultati come generalizzabili a PDF finanziari arbitrari.


## Step 03 — Igiene del versionamento e documentazione

- Ricontrollate tutte le sottocartelle del progetto e le categorie di file locali presenti. Confermato `.gitignore` nella radice, estese le regole per cache degli strumenti Python, ambienti, coverage, file temporanei e credenziali.
- Mantenuti versionabili codice, test, PDF sintetici, esempi, requisiti e `.env.example`. Esclusi ambienti annidati, cache, `.DS_Store`, `.env`, stato API, budget e annotazioni del valutatore. Nessun file dell'autore eliminato.
- README reso indipendente dal computer dell'autore: rimossi percorsi personali e cronologia delle cartelle locali; istruzioni da eseguire dalla radice della repository. Aggiunte indicazioni per visualizzare `.gitignore`, nascosto da alcuni file manager.
- Rimosse le date dalle intestazioni del diario; mantenuti numerazione e contenuto tecnico degli step.
- Verificate le esclusioni con `git check-ignore` e l'assenza di percorsi personali nel README. Nessun cambiamento al codice applicativo.
