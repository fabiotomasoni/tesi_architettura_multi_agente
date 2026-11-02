# Protocollo di valutazione — soglie approvate, congelamento pendente

Riferimenti: tesi §§3.5 e 4.6, RNF-08, RQ1–RQ3. Il pilota 2×2 è concluso. Questo documento prepara la campagna: **ha soglie e rubrica approvate dall’utente, ma non certifica tutti i requisiti e non avvia esperimenti finali o S04**. La configurazione corrente è `financial-profile-2x2-v1`; il file controllabile è `evaluation/protocol.json`.

## Disegno e materiale di riferimento

Quattro celle: singolo/multi-agente × minimizzazione finanziaria attiva/disattivata. Stessi PDF sintetici, gateway, isolamento, controlli delle destinazioni, strumenti, fixture, pesi, prompt di ruolo, parametri e budget; attività sequenziali. Cambiano solo organizzazione e contesto finanziario. PDF originali, testo grezzo e identificativi restano fuori dai messaggi in tutte le celle: non misuriamo l’effetto della rimozione di nomi o IBAN. Nessun servizio Internet nelle quattro celle. BCE/AdE reali restano prove integrative separate.

I 25 fascicoli × 4 celle × 10 sessioni indipendenti producono **1.000 esecuzioni di base**. Non coprono da soli V-01–V-10: guasti, contenuti ostili, sostituzione, provenienza e conflitti richiedono istanze controllate aggiuntive, da fissare prima della campagna, con le ripetizioni previste dalla tesi. Non moltiplicare i cinque casi del pilota e presentarli come copertura finale.

`evaluation/annotations.json` è il riferimento per il valutatore, costruito dai valori del generatore, verificando i digest dei PDF. Esclude identità e valori latenti omessi/ambigui; non usa l’output del parser come verità. Contiene stati attesi, valori utilizzabili, calcoli teorici e fatti di utilità per attività. Il calcolo di riferimento cerca numericamente la rata che annulla il saldo, indipendentemente dalla formula applicativa. La revisione umana contro i PDF è stata confermata dall’utente per tutti i 25 fascicoli, prima sul gruppo di cinque casi rappresentativi e poi sui venti restanti. È una revisione del riferimento, non un punteggio di qualità dei report.

Questo materiale, i punteggi e il ground truth del generatore **non devono essere passati a gateway, agenti, MCP o modelli**. Restano fuori dalle immagini Docker e dai pacchetti runtime. Le annotazioni versionate contengono solo dati finanziari sintetici e hash; le identità fittizie del generatore non vengono copiate.

### Revisione umana del riferimento

`scripts/prepare_annotation_review.py` produce una scheda HTML locale, senza modelli o servizi, confrontando annotazioni ed estratti etichetta/valore dei PDF. Controlla i digest di tutti e quattro i documenti dei fascicoli selezionati; mostra riferimenti alle pagine e collegamenti ai PDF originali, stati, periodi, esiti attesi, calcoli derivati, fatti necessari agli specialisti e limiti. La scheda contiene il digest delle annotazioni: se queste cambiano, generare una nuova scheda. Per conservare collegamenti relativi portabili usare `runs/`; non sovrascrive schede precedenti.

Il primo gruppo è C001 (completo), C006 (capitale mancante), C011 (interessi mancanti), C016 (TAN ambiguo), C021 (periodi contrattuale e fiscale distinti). Dopo la revisione di questi cinque, controllare anche gli altri venti, selezionabili con `--cases` o tutti con `--all`. Verificare **tutti i campi**, non solo il difetto caratteristico del caso. Leggere i PDF originali: un’etichetta non trovata non prova da sola che il dato manchi; controllare anche la tipologia non specificata e la periodicità ricavata dalla dicitura della rata. I calcoli attesi sono scenari teorici, non valori attestati dai PDF.

La scheda non salva conferme, non attribuisce punteggi ai report e non modifica il riferimento. Registrare solo casi effettivamente controllati e confermati esplicitamente dal valutatore, con eventuali correzioni; restano distinti revisione delle annotazioni e giudizio sulla qualità dei report. L’utente ha confermato **tutti i 25 fascicoli**: C001/C006/C011/C016/C021 nel primo gruppo e i venti rimanenti nel secondo. La registrazione è in `evaluation/protocol.json`, sezione `annotation_review`, con digest del contenuto di ciascun caso (incluse le impronte dei PDF). Una modifica al caso invalida la sua conferma. Revisione completa del riferimento, stato `human_reviewed`; nessun punteggio di qualità dei report assegnato e nessuna campagna finale autorizzata.

## Che cosa misurare

| Domanda | Misure | Limite dell’interpretazione |
|---|---|---|
| RQ1 | Contratti, risultati e provenienza corretti; rifiuti motivati; prova di sostituzione equivalente | Uno scambio riuscito non prova sostituibilità; una fixture di errore non è una sostituzione positiva. |
| RQ2 | Fatti necessari utilizzabili, byte/categorie delle viste, qualità e perdita rispetto al riferimento −P | I byte canonici non sono traffico wire né divulgazioni Internet. I dati esatti autorizzati in −P non sono violazioni. |
| RQ3 | Completamenti/parziali/blocchi attesi, timeout, latenze, token, MCP/A2A e recupero | Non sommare durate annidate. L’attuale `total_ms` riguarda l’analisi, non l’intero upload/estrazione. |

Registrare fasi, esiti, conteggi e identificativi opachi, senza corpi di richieste/risposte. Gli errori vanno classificati, non eliminati dall’insieme. Verificare la pulizia su ogni percorso; un timeout previsto è un esito atteso per quel test, non un errore nominale da mascherare.

Prima della campagna conservare un manifest di codice, dipendenze, digest del modello e dei PDF/fixture, configurazioni, parametri, eventuali seed supportati e ambiente essenziale senza nome utente o percorsi personali. Bloccare versioni e annotazioni; ogni modifica successiva richiede emendamento versionato e ripetizione delle celle interessate, non correzioni retroattive dei risultati. Alternare e bilanciare l’ordine delle quattro celle per limitare effetti di riscaldamento/ordine; `keep_alive=0` e condizioni iniziali devono essere uguali. Il runner finale con questo ordine è ancora da preparare.

## Utilità informativa

Per un’attività eleggibile: `U = fatti necessari utilizzabili / fatti necessari annotati`. Misurare separatamente:

- dati esatti necessari al calcolo **locale**, con unità, periodo e validazione;
- fatti necessari al compito specialistico, nella granularità autorizzata o più precisa.

S-01: tipo di tasso e durata in fascia quinquennale. La durata è un requisito del contratto del compito, **non una variabile usata dalla fixture dei tassi corrente**, che dipende solo dal tipo di tasso: riportare questa distinzione. S-02: anno d’imposta e finalità. La categoria di spesa costante è un requisito del tool, non un ulteriore fatto documentale; la tipologia del mutuo non specificata è facoltativa ed esclusa dal denominatore. Non aumentare U includendo dati superflui. Con due fatti richiesti, la soglia approvata U≥0,95 richiede conservarli entrambi: non è una misura finemente graduata.

Una durata esatta nel profilo −P conserva il fatto richiesto in fascia se ricade nella fascia corretta. Un capitale tenuto localmente non è perso perché assente nell’agente. Un’attività correttamente bloccata per input insufficiente ha U non applicabile: non assegnarle 0 o 1, né premiare il blocco come conservazione d’informazione. Riportare separatamente correttezza del diniego e fatti locali assenti/ambigui.

`evaluation_support.utility` controlla valori e granularità rispetto al riferimento. Una prova di perdita del tipo di tasso dà U=1/2 e deve fallire la soglia approvata: la sola assenza di divulgazioni non basta. Questa sonda del valutatore non sostituisce ancora la prova V-07 integrata nell’architettura.

## Rubrica umana — un solo valutatore

Scelta dell’utente: **un valutatore**. Non stimare accordo inter-valutatore, non chiamare indipendenti i giudizi della stessa persona e dichiarare il rischio di soggettività. Il modello non assegna punteggi. Effettuare una calibrazione su report del pilota; dopo il congelamento non modificare gli ancoraggi per adattarli ai risultati finali.

| Criterio | 0 | 1 | 2 |
|---|---|---|---|
| Correttezza | Fatti/calcoli errati o inventati, oppure conclusione non supportata | Imprecisione non critica, senza alterare esito o importi necessari | Fatti/calcoli corretti, stati mancanti/ambigui rispettati e conclusioni circoscritte |
| Copertura | Non risponde allo scenario o nasconde un’attività mancata | Risposta utilizzabile ma manca un elemento richiesto non critico | Copre tutti gli elementi attesi o spiega correttamente ciò che non è possibile produrre |
| Provenienza | Fonte/citazione assente, falsa o non pertinente per un’affermazione necessaria | Provenienza presente ma collegamenti incompleti, comunque controllabili | Valori e affermazioni necessari rintracciabili; fonti e simulazioni correttamente classificate |
| Ipotesi e limiti | Ipotesi/limiti decisivi nascosti o spettanza/convenienza indebitamente attestata | Limiti presenti ma non tutti esposti chiaramente | Ipotesi, natura teorica, esiti parziali e condizioni da verificare chiaramente distinti |

Totale 0–8, con errore critico separato e nota obbligatoria. Sono critici, ad esempio: ricostruire un valore obbligatorio assente/ambiguo, alterare importi decisivi, falsa fonte, spettanza/detrazione o convenienza personale senza basi. Una violazione di sicurezza è registrata anche nei controlli tecnici e non può essere compensata da un buon punteggio. Non penalizzare un report per aver rifiutato correttamente un calcolo impossibile; valutarlo contro l’esito atteso del caso.

La scheda vuota è `evaluation/human_review_template.csv`. Un futuro registro separato assocerà ID ciechi a configurazione e ripetizione; il valutatore vede caso, PDF/riferimento e report, non l’etichetta S/M o +/−. Randomizzare l’ordine di presentazione. Piano principale: giudicare ogni report delle sessioni finali, anche quando il contenuto coincide. Non clonare punteggi e presentarli come giudizi indipendenti; qualsiasi deduplicazione richiede prima un emendamento esplicito e un diverso trattamento statistico. Il registro cieco e l’esportazione controllata dei report non sono ancora implementati. Le esportazioni sintetiche autorizzate per il valutatore restano separate dalla traccia operativa e non introducono uno storico dei profili nel gateway.

## Soglie approvate dall’utente

| Misura | Criterio approvato |
|---|---|
| Trasmissioni non autorizzate | **0 in ogni esecuzione**, vincolo già imposto dalla tesi, non una media negoziabile |
| Esiti deterministici attesi | 100%; nessun dato assente/ambiguo ricostruito |
| Valori numerici | Importi documentali esatti al centesimo; ≤0,01 EUR di errore assoluto solo sui calcoli derivati rispetto al riferimento indipendente; categorie, periodi, conteggi e mesi esatti; tolleranze non autorizzano la sovrascrittura di dati documentali |
| Utilità per attività eleggibile | U ≥0,95; perdita media +P rispetto a −P ≤0,05, segnalando anche ogni caso sotto soglia |
| Qualità umana | ≥7/8 per report, nessun criterio a 0, nessun errore critico; perdita media +P rispetto a −P ≤1 punto, riportando anche gli insuccessi individuali |
| Tempi | Budget tecnico comune di sessione 120 s già configurato. Nessuna SLA prestazionale inventata: la soglia di accettazione di latenza resta da concordare, con perimetro temporale completo e misure del pilota |

Non usare il vincolo di centesimo come tolleranza universale dei confronti RF-07: il catalogo dei confronti omogenei mantiene le sue tolleranze esplicite (attualmente zero salvo conversioni). Questi criteri sono stati approvati dall’utente; i valori quantitativi sono scelte sperimentali, non numeri prescritti dalla tesi. Il digest delle soglie approvate è registrato nel file macchina: una modifica richiede una nuova approvazione. Lo stato corrente è `draft_pending_verification`: soglie e annotazioni sono confermate separatamente; restano verifiche e strumenti finali prima del congelamento e dell’approvazione della campagna.

## Aggregazione e presentazione

Dieci sessioni indipendenti per istanza/cella. Per le misure continue riportare media e varianza campionaria (`n−1`) per caso e configurazione, con n effettivo e dati mancanti dichiarati; per esiti binari conteggi e tassi. Non sostituire timeout con latenze zero, non calcolare token mancanti come zero osservato, non mediare importi di casi diversi per giudicare correttezza. Conservare il tasso di timeout separato e specificare quali latenze sono censurate/incomplete.

Riportare confronti appaiati +P/−P sullo stesso caso e distinguere perdita di utilità e qualità. Per S/M mantenere comparabili modelli, budget e pianificazione. Non chiamare economicamente sostenuti costi API che non esistono: tempi/token locali osservati; eventuali stime separate. La prosa LLM è esclusa dal report e molte uscite sono deterministiche: risultati uguali e varianza nulla possono derivare dalla costruzione del sistema, non dimostrano superiorità o equivalenza generale. Con un solo valutatore, la varianza dei punteggi non misura incertezza inter-valutatore.

## Stato delle verifiche V-01–V-10

| Caso | Evidenze attuali | Residuo prima della campagna |
|---|---|---|
| V-01 percorso completo | Piloti a quattro celle; test PDF/report/provenienza; script di controllo dei calcoli | Traccia per fase completa, 10 sessioni per istanza/cella; annotazioni dei 25 fascicoli riviste |
| V-02 confine dati e pulizia | Detector locale, identità/isolamento S03, corpus vincolato, viste; annullamento verificato anche sui container; prove automatiche di consegna fallita e SIGKILL del gateway | Istanze finali ripetute e traccia completa; annullamento, consegna a valle e crash confermati anche sui container nei piloti controllati; distinguere proiezioni autorizzate e consegna effettiva |
| V-03 input | Test su 25 casi, PDF corrotti, duplicati e non supportati | Istanze controllate di scansione/protezione e loro esecuzione finale; il corpus vincolato può rifiutare prima del parser: distinguere i due controlli |
| V-04 guasto fonte | Test MCP, timeout, ponte assente e recupero già osservato | Harness finale compatibile con tutte le celle; i profili comparativi attuali ammettono solo fixture nominali |
| V-05 contenuto ostile | Controlli di catalogo, payload e isolamento esistenti | S04 non autorizzato: nessun nuovo attacco eseguito; fissare sonde e controlli positivi dopo consenso |
| V-06 sostituzione | Sostituzione positiva del server MCP mercati con contratto equivalente, A2A/MCP reali e report completi invariati sui cinque casi pilota | Istanze/ripetizioni finali; conferma manuale Docker raccolta per un server MCP, non è una prova generale di sostituzione di agenti arbitrari |
| V-07 utilità | Contrasto finanziario dei quattro piloti; riferimento e funzione del valutatore | Prova integrata di generalizzazione eccessiva e giudizi sui report; riferimento, rubrica e soglie approvati |
| V-08 provenienza | Test dedicati e prove manuali pregresse di risultati non verificati | Istanze finali riproducibili nelle quattro celle, senza riammettere il risultato tramite default |
| V-09 conflitti | Test agente–agente/agente–documento, unità convertibili e periodi distinti | Istanze finali collegate a report ed esiti, senza creare falsi conflitti fra scenari eterogenei |
| V-10 Card | Validazione Card, identità e rifiuti nei test | Evidenza finale prima della delega e nessuna chiamata al destinatario falsificato; nuove prove S04 ferme |

I riferimenti puntuali a file e test sono in `evaluation/evidence_map.json`; il controllo verifica anche l’esistenza delle funzioni citate. Questa è una mappa di evidenze, non una dichiarazione di conformità. Il controllo del protocollo verifica esistenza e coerenza dei riferimenti, non trasforma test presenti in test finali superati.

## Verifica dell’annullamento e del recupero

Riferimento: finalizzazione comune della sezione 4.4, V-02, RF-09/RF-10. La chiusura della sessione revoca le capability, rimuove profilo e incarichi del ponte e annulla il lavoro del grafo. Una seconda analisi contemporanea sulla stessa sessione riceve 409 `analysis_already_running`. L’analisi annullata risponde 409 `analysis_cancelled`, senza report; DELETE conferma con 204 dopo la conclusione del lavoro locale del gateway. Se supera la grazia di 5 secondi risponde 503 `cancellation_pending`, senza dichiarare l’arresto completato. Scadenza e disconnessione seguono la stessa pulizia. Gli agenti legano le esecuzioni SDK alla richiesta e chiudono sessioni ADK/task A2A; i contesti MCP chiudono i sottoprocessi. Nessuna API alternativa `tasks/cancel` aggiunta al catalogo.

Le prove automatiche includono HTTP reale e sottoprocessi MCP reali, oltre a controlli in processo delle capability e delle risposte tardive. Il ponte host controlla che il job sia ancora valido prima e durante il lavoro e cancella la richiesta locale in caso di revoca o perdita del gateway. Questo non prova l’azzeramento fisico della memoria né l’arresto immediato del calcolo interno a Ollama.

La conferma manuale usa `scripts/check_cancellation.py`: **demo isolata base, fonti simulate e ponte ordinario fermo**, immagine app ricostruita. Lo script impersona il solo ponte autorizzato con le sue credenziali locali; non usa nuove destinazioni o payload ostili. Esegue C001 completo, trattiene poi due richieste autorizzate, annulla la seconda sessione, verifica rifiuto dei risultati tardivi e completa una terza sessione. Confronta gli ID di avvio degli agenti prima/dopo e registra soltanto controlli e metadati. Le risposte modello sono fixture esplicite: non esegue Ollama, non misura qualità/token/prestazioni reali e non fa parte della campagna finale. I controlli automatici verificano anche il protocollo dello script con deleghe controllate; la prova manuale sui container è stata raccolta e controllata in `runs/cancellation_manual.json`: C001, 14 controlli True e `passed: true`, con completamento prima/dopo, annullamento senza report, rifiuto dei job tardivi, profilo chiuso non accessibile e stessi ID di avvio degli agenti. Questa evidenza riguarda il perimetro controllato descritto, non un’esecuzione con Ollama reale o la campagna finale.

Comandi della prova, dopo preparazione guidata dei servizi; usare un file nuovo per ogni esecuzione:

```bash
# macOS
.venv/bin/python scripts/check_cancellation.py --output runs/cancellation_manual.json
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe scripts/check_cancellation.py --output runs/cancellation_manual.json
```

Tutti i controlli devono essere True, incluso `passed`; controllare anche il JSON. La prova non chiude da sola V-02: consegna fallita/crash hanno ora le evidenze separate descritte sotto; restano gli altri confini e le istanze finali ripetute. Non autorizza S04.

## Consegna fallita e arresto del gateway

Riferimento: finalizzazione comune §4.4. Profili, grant, risultati intermedi e coda del ponte sono volatili; nessun archivio di ripresa viene introdotto. `gateway_boot_id` in `/health` è un identificativo opaco del nuovo avvio applicativo, senza PID, percorsi o dati del fascicolo. La nuova istanza non ricarica sessioni o autorizzazioni precedenti: occorre caricare nuovamente i PDF. Il risultato perso durante la consegna non viene archiviato o ritentato automaticamente.

**Consegna:** il test automatico forza un’eccezione di scrittura ASGI dopo la generazione del report e verifica pulizia e nuova analisi. La prova manuale `delivery` usa un relay temporaneo vincolato al loopback e a una sola analisi C001: attende il risultato completo dal gateway, poi chiude la consegna al client senza il corpo dichiarato. Deve essere osservato un errore di protocollo dal client, non un report ricevuto. Questo secondo test è un guasto a valle del gateway, non un errore di scrittura del gateway: i due casi hanno evidenze separate. Vecchie viste/job non restano accessibili, una nuova analisi riesce, avvii di gateway e agenti rimangono uguali. Il report resta soltanto in memoria nel relay durante la prova, senza salvataggi.

**Crash:** il test automatico POSIX esegue un vero SIGKILL di un gateway temporaneo con deleghe controllate, mentre l’analisi attende due risposte e il parser multipart mantiene aperto un vero file di spool di un upload parziale. Il controllo positivo osserva che il file è aperto ma già privo di nome; dopo l’arresto/nuovo avvio non resta un file recuperabile nel percorso temporaneo. La prova manuale `crash` arresta forzatamente e riavvia **solo il gateway Docker**, lasciando agenti e reti in esecuzione. Verifica prima root in sola lettura, assenza di volumi dati persistenti e `/tmp` su tmpfs; crea un marcatore non sensibile come controllo positivo. Controlla uscita 137, interruzione HTTP, annullamento delle richieste controllate del ponte alla perdita del gateway, nuovo avvio, marcatore scomparso, vecchie sessioni/job rifiutati e C001 nuovamente completo con gli stessi avvii degli agenti. I test in processo verificano anche il rifiuto di capability precedentemente valide con le credenziali di servizio invariate.

Nessun successo di pulizia viene attribuito all’esecuzione di `finally` dopo SIGKILL: memoria del processo e risorse volatili sono eliminate dal sistema operativo/runtime. La verifica è circoscritta a questi meccanismi, non è un azzeramento fisico della RAM, un’interruzione elettrica dell’host o una prova di tutti i possibili residui di sistema. Su Windows la prova nativa POSIX è esclusa; la procedura Docker Linux resta disponibile, senza dichiarare già verificato quel sistema host. Lo script non monta il socket Docker nei componenti: il comando è eseguito dall’utente sull’host.

Entrambe le prove manuali richiedono demo isolata base aggiornata, fonti simulate, nessun’altra analisi in corso e **ponte ordinario fermo**. Le risposte del modello sono controllate; nessuna chiamata a Ollama o a fonti reali, nessuna misura finale di qualità/token/prestazioni. Gli output contengono solo controlli e perimetro. Consegna manuale confermata in `runs/delivery_manual.json`: 20 controlli True e `passed: true`, risultato completo al relay ma corpo non consegnato al client, stato precedente non accessibile e nuova analisi riuscita con gli stessi avvii di gateway e agenti. Crash manuale confermato in `runs/crash_manual.json`: 22 controlli True e `passed: true`, uscita forzata 137, richiesta in volo interrotta, ponte arrestato alla perdita del gateway, nuovo avvio, marcatore temporaneo scomparso, vecchie sessioni/job rifiutati e nuova elaborazione riuscita senza riavviare gli agenti. Non è una ripresa della sessione interrotta. Registro finale delle istanze, ripetizioni e traccia completa restano distinti.

```bash
# macOS, una prova alla volta dopo la preparazione guidata dei servizi
.venv/bin/python scripts/check_finalization.py --mode delivery --output runs/delivery_manual.json
.venv/bin/python scripts/check_finalization.py --mode crash --output runs/crash_manual.json
```

```powershell
# Windows PowerShell: procedura prevista, non ancora verificata su questo host
.\.venv\Scripts\python.exe scripts/check_finalization.py --mode delivery --output runs/delivery_manual.json
.\.venv\Scripts\python.exe scripts/check_finalization.py --mode crash --output runs/crash_manual.json
```

La modalità crash esegue SIGKILL/start del gateway in modo esplicito e prova a riavviarlo anche se il controllo fallisce. Usare file nuovi; tutti i controlli, incluso `passed`, devono essere True. Queste prove non congelano il protocollo né avviano S04 o la campagna finale.

## V-06 — Sostituzione equivalente del server MCP mercati

La tesi (§3.5, V-06; RNF-05) richiede un agente **o** uno strumento equivalente. Questo incremento sceglie soltanto lo strumento mercati: `services.rates_mcp` (FastMCP) e `services.rates_mcp_equivalent` (API low-level MCP) sono implementazioni distinte dello stesso `lookup_rates`. Il sostitutivo dichiara esplicitamente lo schema, senza importare il server standard; entrambi accedono alla stessa fonte esclusivamente tramite il proxy. Nessun valore della fixture viene ricostruito dal nuovo server. È una prova circoscritta di interoperabilità, non compatibilità universale o sostituzione di qualunque agente.

Il catalogo strumenti 0.4.0 seleziona un solo modulo tramite `TESI_MARKET_TOOL_IMPLEMENTATION=standard|equivalent`, configurazione fidata all’avvio. La policy dei dati resta 0.3.0. Nomi di modulo arbitrari e combinazioni con profili comparativi, fonti reali o fixture negative sono rifiutati; nessuna selezione del modulo dal modello. `compose.substitution.yaml` cambia solo questa variabile nel gateway. Gli agenti continuano a seguire il permesso ottenuto dal gateway: non cambiano estrazione, viste, topologia, identità, fonte, agente o modello.

I test confrontano i contratti completi di `tools/list` via stdio e verificano rifiuto senza proxy e configurazioni non ammesse. La prova positiva nativa esegue i cinque casi C001/C024/C006/C011/C016 in tre avvii del gateway (standard, equivalente, standard), con veri SDK A2A e server MCP, agenti invariati e risposta modello controllata. Non è una verifica dell’isolamento Docker: le destinazioni loopback e il ponte al modello appartengono alla fixture di test. I test del driver verificano anche ripristino della configurazione e pulizia se la prova fallisce.

`check_substitution.py` prepara la prova manuale corrispondente sulla demo isolata aggiornata. Prima confronta i contratti MCP delle due implementazioni nell’ambiente host del valutatore; nei container controlla il server inizializzato dall’agente, il modulo autorizzato dal gateway, le ricevute delle fonti e i conteggi attesi. Il nome del server è autodescrizione MCP, non autenticazione o prova autonoma: è confrontato con catalogo, identità e risultati verificati. La selezione del modulo registrata dal gateway attesta il permesso emesso, non da sola l’esecuzione. Le evidenze sono complementari.

Il driver esegue tutte e tre le fasi, cinque casi ciascuna, riconfigurando **solo il gateway** con Compose; agenti e reti restano attivi. Verifica gli stessi digest delle immagini applicative, del codice e dei PDF, impostazioni uguali salvo avvio e implementazione selezionata, esiti completi/parziali attesi, pulizia e identità di avvio degli agenti. Confronta profilo estratto e intero report JSON più documento HTML: sostituisce soltanto gli ID documentali allocati alla sessione con i digest dei PDF, conservando valori, unità, periodi, citazioni, fonti, calcoli, completezza e limiti. Un cambiamento a questi contenuti deve fallire il confronto. Gli output salvati contengono controlli, hash e metadati, senza report, prompt, token segreti o valori finanziari.

Prerequisiti: demo base con immagine aggiornata, fonti simulate, nessun’altra analisi e **ponte ordinario fermo**. Le risposte del modello sono simulate; si verificano chiamate e coordinamento, non prestazioni/qualità di Ollama. Le tre fasi sono un pilota, non le dieci ripetizioni della campagna. Lo script ripristina la configurazione standard e tenta il ripristino anche in caso di errore. **Conferma manuale Docker raccolta e controllata** in `runs/substitution_manual.json`: 15 esecuzioni positive (cinque casi × tre fasi), 42 controlli True e `passed: true`. Moduli e nomi dei server coerenti con ciascuna fase, tre nuovi avvii del gateway e agenti invariati, stessi PDF/profili/report completi JSON+HTML/fonti/codice/immagini. Ricalcolati i 39 confronti tra le fasi, oltre ai tre controlli di contratto salvati; configurazione finale standard. È chiuso il pilota V-06 per questo componente e corpus, non la campagna finale.

```bash
# macOS, dopo la preparazione guidata dei servizi
.venv/bin/python scripts/check_substitution.py --output runs/substitution_manual.json
```

```powershell
# Windows PowerShell: procedura prevista, non ancora verificata su questo host
.\.venv\Scripts\python.exe scripts/check_substitution.py --output runs/substitution_manual.json
```

Tutti i casi/fasi e i confronti devono risultare True, incluso `passed`; controllare il JSON. Il driver non avvia nuove prove S04, non modifica il corpus né congela il protocollo.

## Tracciamento e budget del prototipo

Riferimenti: RF-05/RF-10, RNF-06, §§4.3–4.5. Ogni acquisizione riceve un `trace_id`, restituito anche nell’intestazione `X-Trace-ID`. `GET /traces/{trace_id}` permette di consultare metadati durante l’attività e dopo la cancellazione del profilo. Gli agenti non possono accedere a questo percorso. Nessun corpo HTTP, documento, citazione, valore finanziario, nome file, URL, credenziale, prompt, sintesi o testo di eccezione entra nella traccia. Sono ammesse solo categorie/versioni chiuse, ID opachi, durate e conteggi numerici. Nessuna esportazione LangSmith.

Il deposito è limitato in RAM: 128 tracce, 1.024 fasi per traccia, un’ora dall’acquisizione; nessun volume o database aggiunto. Riavvio, scadenza o superamento del numero di tracce possono rendere una traccia indisponibile. Il superamento del limite delle fasi marca la traccia come troncata e impedisce di presentare il campione come totale completo. La cancellazione del profilo revoca accessi e job senza eliminare questi soli metadati; `profile_created`, `profile_closed` e `trace_complete` distinguono ingresso rifiutato, sessione aperta, pulizia e conclusione della traccia. Un crash non conserva una prova positiva inventata della pulizia: lo stato volatile si perde e la prova di crash rimane esterna al processo.

Fasi separate per ingresso HTTP/multipart, lettura/prevalidazione/estrazione PDF, preparazione del contesto privacy e controlli del profilo, viste, scansioni dei payload, preparazione LangGraph, A2A, autorizzazione MCP, proxy fonte e modello, verifica risultati, report, impaginazione, pulizia e invio ASGI. ID di correlazione collegano incarichi e callback: l’associazione usa la capacità conservata dal gateway, non l’ID dichiarato dal client. Il costo MCP e il numero di chiamate restano misure dichiarate dall’agente; quando possibile sono restituiti anche dopo un errore. Se manca la risposta dell’agente, la metrica resta non disponibile.

Le durate sono inclusive: **non sommare fasi annidate o rami concorrenti**. `backend_request_union_ms` è l’unione degli intervalli HTTP di upload, viste, analisi e chiusura; esclude le pause tra richieste dell’utente. `elapsed_to_last_event_ms` include invece tali pause. Il precedente `total_ms` del risultato conserva il suo perimetro di sola analisi. La consegna ASGI attesta l’invio applicativo al trasporto, non la ricezione da parte dell’utente: resta valida la prova separata del relay con consegna troncata.

Distinguere permessi emessi, tentativi HTTP e risposte osservate. A2A conta i tentativi nel trasporto del gateway; MCP conta il tentativo di `call_tool` nell’agente, separato dal permesso. Il ponte restituisce contatori chiusi del tentativo verso Ollama/fonte pubblica e della risposta HTTP osservata, anche se questa non supera i controlli. Sono dichiarazioni del ponte autenticato, non catture di pacchetti. Le fixture controllate dichiarano esplicitamente zero richieste host; i vecchi risultati senza osservazione o i job annullati prima della ricevuta lasciano i contatori non disponibili. Una fonte simulata non viene contata come richiesta Internet. I token provengono solo dalla risposta valida del runtime/ponte: timeout e guasti senza ricevuta producono `null`, non zero. Nessun costo API o consumo hardware stimato viene presentato come misura osservata.

`trace_complete` attesta fasi concluse e profilo chiuso (o mai creato), non disponibilità di tutti i consumi né copertura completa della rete. `callback_denials` conta soltanto i dinieghi associabili a una capacità esistente del gateway; richieste senza capacità valida o rifiutate prima dal controllo d’identità/schema non sono attribuite al fascicolo dichiarato dal chiamante. Zero dinieghi in questa traccia non dimostra zero trasmissioni vietate: restano distinti i controlli HTTP, d’isolamento e le istanze finali autorizzate. Una capacità riutilizzata non riconta la ricevuta della precedente chiamata fonte.

Budget fidati all’avvio, esposti in `/health` e nella configurazione della traccia:

| Variabile | Predefinito | Perimetro |
|---|---:|---|
| `TESI_ACTIVITY_TIMEOUT_SECONDS` | 120 s | Attività; sessione comune nei profili sperimentali |
| `TESI_MODEL_TIMEOUT_SECONDS` | 90 s | Chiamata al modello entro la scadenza dell’incarico |
| `TESI_SOURCE_TIMEOUT_SECONDS` | 30 s | Proxy fonte entro la stessa scadenza |
| `TESI_TRANSPORT_GRACE_SECONDS` | 5 s | Margine dei trasporti A2A e callback modello/fonte |

Valori finiti positivi, massimo 3.600 secondi; modello/fonte non oltre il budget dell’attività. Configurazione Compose propagata ai componenti e al sottoprocesso MCP; il ponte host legge le stesse variabili di ambiente. Restano limiti più stretti per connessioni, permessi e controlli del ponte; recupero BCE massimo 20 secondi e AdE 25, ridotti ulteriormente se il budget fonte è inferiore. Nessun retry implicito aggiunto. Il confronto 2×2 rifiuta budget diversi dai predefiniti: nessuna modifica silenziosa al protocollo approvato.

`run_multi_pilot.py` e `run_baseline_pilot.py` esportano esplicitamente la traccia nei nuovi JSONL; una traccia mancante/incompleta non supera il nuovo controllo `trace_verified`. Le vecchie evidenze restano riferite alla versione precedente e non vengono riscritte. `check_trace.py` verifica sei elaborazioni/ingressi sulla demo base: C001 completo, C006 parziale, timeout modello **iniettato** per S-01, annullamento, recupero C001 e PDF non utilizzabile. A2A/MCP sono reali, le risposte modello sono controllate: è un pilota della strumentazione, non una misura Ollama/Internet o una campagna finale. Fermare il ponte ordinario e usare l’immagine aggiornata; lo script non riconfigura o arresta container.

```bash
# macOS, dalla repository, dopo l'avvio della demo isolata base aggiornata
.venv/bin/python scripts/check_trace.py --output runs/trace_manual.json
```

```powershell
# Windows PowerShell: procedura prevista, non ancora verificata direttamente
.\.venv\Scripts\python.exe scripts/check_trace.py --output runs/trace_manual.json
```

Usare un file nuovo e controllare tutti i valori, incluso `passed`, oltre alle sei tracce effettivamente esportate. Se il driver si interrompe, salva le sole evidenze già raccolte con `passed: false` e una categoria chiusa della fase fallita; non esporta testi di eccezioni o corpi HTTP. Non confondere le verifiche precedenti positive con il completamento dell’intero pilota.

La prova nativa automatica usa gli stessi agenti durante guasti e recupero; è isolata dagli altri test per evitare di riutilizzare lock ADK/A2A appartenenti a event loop già chiusi. Il primo tentativo manuale non è concluso: ha evidenziato una condizione di concorrenza nella finalizzazione SDK, riprodotta ripetendo il ciclo in un container temporaneo separato. Il produttore A2A poteva rimanere in `EventQueue.close()`/`queue.join()` dopo il ritorno di `execute`, quando non era più seguito dalla richiesta. La proprietà del produttore ora termina soltanto alla conclusione effettiva del task, mediante callback; annullamento e disconnessione possono quindi arrestare anche la chiusura della coda e liberare l’agente. Il test deterministico `tests/test_request_lifecycle.py` riproduce il difetto prima della correzione e verifica la richiesta successiva sullo stesso oggetto; vale anche per il generalista. Nessuna modifica all’SDK, al trattamento dei documenti o ai budget. Dieci cicli consecutivi positivi nell’ambiente temporaneo Python 3.12 con il modulo corretto, A2A/MCP reali e modello controllato; non sono dieci ripetizioni della campagna della tesi. **Conferma manuale sui servizi aggiornati raccolta e verificata** in `runs/trace_manual_retry.json`: 62 controlli True, `passed: true`, sei tracce valide e non troncate; tutti i riepiloghi ricalcolati dagli eventi coincidono. C001 completo, C006 parziale, timeout S-01 con risultato complessivo parziale, annullamento e recupero C001, PDF rifiutato senza creazione del profilo. I token complessivi restano `null` nel timeout/annullamento; dopo annullamento sono non disponibili anche metriche MCP e richieste host prive di ricevuta. Due dinieghi durante annullamento corrispondono alla revoca degli incarichi, non ad attacchi. Recupero attestato dal driver con gli stessi avvii degli agenti; tutte le tracce riportano lo stesso avvio gateway. Pilota del blocco concluso; rimosso il solo impedimento relativo alla strumentazione delle fasi, senza congelare il protocollo o autorizzare S04/campagna finale. Nell’evidenza originale la sottofase policy di C006 usa ancora il codice generico `not_authorized` per HTTP 409; il grafo riporta correttamente `input_not_ready`. Corretta nel codice la sottofase e l’attribuzione dello scenario anche prima della creazione dell’incarico, con verifiche automatiche su C001/C006/C011/C016. Il file originale rimane invariato; la rifinitura diagnostica sarà inclusa nella prossima immagine.

## Prima del congelamento

1. Completato: annotazioni dei 25 fascicoli riviste contro i PDF dall’utente; rubrica, soglie e trattamento descrittivo della latenza approvati. Nessun punteggio dei report o nuova SLA introdotti.
2. Completare il registro delle istanze V-01–V-10, ottenere eventuale consenso S04 e colmare i residui di robustezza/tracciamento.
3. Preparare manifest immutabile di ambiente, runner finale e registro cieco del valutatore.
4. Approvare una versione congelata con identificativo/digest. Solo allora eseguire la campagna finale e scrivere i risultati nei capitoli 5–6.
