# Protocollo di valutazione — soglie approvate, congelamento pendente

Riferimenti: tesi §§3.5 e 4.6, RNF-08, RQ1–RQ3. Il pilota tecnico corrente 2×2 è confermato dai file del blocco 2; la campagna finale resta distinta. Questo documento prepara la campagna: **ha soglie e rubrica approvate dall’utente, ma non certifica tutti i requisiti e non avvia esperimenti finali; S04 è autorizzato solo nel perimetro locale concordato**. La configurazione corrente nel codice è `financial-profile-2x2-v6` (pilota tecnico confermato, campagna finale non autorizzata); il file controllabile è `evaluation/protocol.json`.

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
| Tempi | Budget tecnico comune di sessione 120 s già configurato. Nessuna SLA prestazionale approvata: latenza descrittiva, perimetro temporale completo, medie/varianze e conteggi dei timeout |

Non usare il vincolo di centesimo come tolleranza universale dei confronti RF-07: il catalogo dei confronti omogenei mantiene le sue tolleranze esplicite (attualmente zero salvo conversioni). Questi criteri sono stati approvati dall’utente; i valori quantitativi sono scelte sperimentali, non numeri prescritti dalla tesi. Il digest delle soglie approvate è registrato nel file macchina: una modifica richiede una nuova approvazione. Lo stato corrente è `draft_pending_verification`: soglie e annotazioni sono confermate separatamente; restano verifiche e strumenti finali prima del congelamento e dell’approvazione della campagna.

## Aggregazione e presentazione

Dieci sessioni indipendenti per istanza/cella. Per le misure continue riportare media e varianza campionaria (`n−1`) per caso e configurazione, con n effettivo e dati mancanti dichiarati; per esiti binari conteggi e tassi. Non sostituire timeout con latenze zero, non calcolare token mancanti come zero osservato, non mediare importi di casi diversi per giudicare correttezza. Conservare il tasso di timeout separato e specificare quali latenze sono censurate/incomplete.

Riportare confronti appaiati +P/−P sullo stesso caso e distinguere perdita di utilità e qualità. Per S/M mantenere comparabili modelli, budget e pianificazione. Non chiamare economicamente sostenuti costi API che non esistono: tempi/token locali osservati; eventuali stime separate. Le selezioni LLM sono separate dai calcoli deterministici; un eventuale commento ammesso dai filtri resta non verificato semanticamente: risultati uguali e varianza nulla possono derivare dalla costruzione del sistema, non dimostrano superiorità o equivalenza generale. Con un solo valutatore, la varianza dei punteggi non misura incertezza inter-valutatore.

## Registro operativo V-01–V-10

Il [REGISTRO_PROVE.md](REGISTRO_PROVE.md) definisce la copertura riutilizzabile dei 25 fascicoli e dieci cicli aggiuntivi con 29 varianti controllate. Il file macchina è `evaluation/test_registry.json`; `scripts/check_test_registry.py` controlla coerenza con tesi, annotazioni, quattro celle e autorizzazioni. L’audit del protocollo include anche questi controlli. Definizione preparata, fixture/driver finali ancora da completare; nessuna esecuzione o approvazione della campagna implicita.

I cicli contengono più sessioni e controlli di recupero: i loro totali fisici e i report da giudicare restano da calcolare prima del congelamento. Riutilizzare un run di base per più assert non lo trasforma in ripetizioni indipendenti. Un test di comparatore o detector rimane evidenza di componente, finché manca il percorso integrato richiesto dal registro.

**Scelta V-09 confermata dall’autore:** estendere entrambi gli agenti con un compito comune di verifica di un riferimento numerico pubblico autorizzato, consultato via MCP e restituito con fonte/unità/periodo/prodotto. Valori del fascicolo locali; fixture dichiaratamente simulate nei test. È una modifica ancora da implementare, non coperta dal solo comparatore attuale. Verificare le ricevute prima del confronto: un numero non fedele alla fonte va rifiutato; un conflitto verificato richiede osservazioni controfattuali entrambe ammesse dal catalogo di test. Nessuna statistica aggregata viene trasformata in TAN personale. Fissata la fonte comune sulla serie BCE già prevista, con tasso AAR/NDER aggregato mensile e tipi esistenti; adattatore verificato nel catalogo confronti 0.2.0. Il collegamento a entrambi gli agenti resta da implementare; il replay del CSV istituzionale congelato non attesta un nuovo recupero. Predisporre separatamente ricevute controfattuali dichiarate, versionare il protocollo runtime e ripetere il pilota a quattro celle prima di congelare: le misure precedenti rimangono della versione `financial-profile-2x2-v1`.

Le sonde nuove per payload vietati, contenuti ostili e Card falsificate restano subordinate al consenso S04. I riferimenti a file/test già presenti sono in `evaluation/evidence_map.json`; la loro esistenza non attesta che tutte le istanze finali siano state eseguite o superate.

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

Il catalogo strumenti 0.5.0 seleziona un solo modulo tramite `TESI_MARKET_TOOL_IMPLEMENTATION=standard|equivalent`, configurazione fidata all’avvio. La policy dei dati resta 0.3.0. Nomi di modulo arbitrari e combinazioni con profili comparativi, fonti reali o fixture negative sono rifiutati; nessuna selezione del modulo dal modello. `compose.substitution.yaml` cambia solo questa variabile nel gateway. Gli agenti continuano a seguire il permesso ottenuto dal gateway: non cambiano estrazione, viste, topologia, identità, fonte, agente o modello.

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

1. Annotazioni dei 25 fascicoli, rubrica, soglie e latenza descrittiva sono approvate. Nessun voto umano sui report è implicito.
2. Il pilota tecnico del blocco 2 è confermato; il blocco 4 aggiunge la raccolta tracciabile e richiede il proprio pilota strumentato.
3. Preparare e controllare il manifest concreto, il piano fisico delle esecuzioni e l’esportazione cieca, con la procedura sotto.
4. Approvare esplicitamente l’impronta del manifest. Solo dopo avviare la campagna finale e compilare i giudizi umani. I capitoli 5–6 restano lavoro dell’autore.

## Selezione degli specialisti e commento opzionale

Perimetro ristretto confermato dall’autore dopo l’esito negativo di report-locale-36 e la diagnosi dei modelli. Il runtime corrente è `financial-profile-2x2-v6`, contratto `market-selection-1`, generazione `market-selection-generation-1`, catalogo `market-statements-1`. Il mercati sceglie uno/due enunciati sulla fonte e uno sul contesto fra quelli ricevuti; può aggiungere una breve spiegazione collegata alla selezione. Il gateway costruisce il catalogo da fonte validata e vista già autorizzata, conserva il profilo finanziario completo nel laboratorio senza minimizzazione e ricontrolla la risposta. Nessuna selezione viene inventata se il modello manca o propone identificativi non ammessi.

Il report ricostruisce i testi dal catalogo dopo la scelta, non dal testo fornito dal modello. Sono definizioni/trasformazioni controllate con riferimenti ai campi della fonte/vista; non citazioni letterali delle pubblicazioni. Verifica di identificativi/testi/riferimenti distinta dalla pertinenza della scelta: `selection_relevance_verified` e `semantic_verified` restano falsi. Una selezione valida sopravvive al commento escluso (`selection_only`), senza spiegazione sostitutiva. I fatti documentali, le fonti e i calcoli locali restano indipendenti dalla selezione. Una prova controllata dimostra che scelte diverse del modello cambiano il focus del report a parità di risultati finanziari, senza attribuire questo effetto a una scelta autonoma degli strumenti o delle destinazioni.

Numeri/date confrontati con i soli riferimenti degli enunciati scelti; non basta che un numero sia altrove nell’input. Controlli lessicali su alcune raccomandazioni, confusioni di fonte, proprietà non selezionate e frasi apparentemente incomplete: possibili falsi positivi e copertura incompleta, nessuna certificazione semantica generale. Il valutatore giudica pertinenza, completezza, fedeltà e utilità; commento assente/escluso resta un limite da valutare, anche se il pilota tecnico accetta una selezione valida. Le soglie e la rubrica approvate non cambiano. Nei JSONL del pilota si registrano stato, conteggi e disponibilità del commento, senza testi o identificativi degli enunciati scelti.

Restano gli stessi modelli (llama3.2:3b mercati e pesi comuni nel laboratorio; qwen3:1.7b fiscale della demo), contesto 4096, temperatura zero, limiti 768 token S-01/200 S-02, una inferenza per attività e le deadline concordate. Non si adottano qwen3:4b, retry o nuovi provider. Il fiscale usa tax-selection-1, generazione tax-selection-generation-1 e catalogo tax-statements-1, con lo stesso compito circoscritto. I risultati delle versioni precedenti e le prove iterative di sviluppo non costituiscono la valutazione del runtime v6: ripetere il pilota a quattro celle dopo gli incrementi sugli agenti, prima del congelamento.

Quattro riproduzioni con il modello locale attuale tramite broker su viste sintetiche fisse/variabili e ricevuta BCE archiviata/fixture hanno prodotto selezioni valide. Il testo dei commenti ha evidenziato anche incompletezza e proprietà non selezionate, coperte da nuove regressioni; non viene dichiarata verificata l’intera prosa. Nessun PDF, ground truth o dato originale al modello, nessun nuovo recupero BCE e nessuna prova dell’isolamento Docker in queste riproduzioni. Le verifiche automatiche con modello controllato coprono anche MCP, ciclo di vita, guardie e report. **Pilota manuale della selezione mercati confermato sulla demo aggiornata:** report-locale (3).json/C001 fisso e report-locale (4).json/C024 variabile. Testi e riferimenti selezionati ricostruibili dal catalogo, digest fonte coerente, ricevuta modello presente; in entrambi selection_only, con prosa esclusa rispettivamente per proprietà non selezionata e possibile frase incompleta. Conferma del percorso e delle guardie, non della correttezza dei commenti o di qualità umana già misurata. Restano la conferma fiscale della demo aggiornata, i nuovi piloti a quattro celle e la valutazione finale. S04 locale circoscritto autorizzato dall’autore; campagna finale non autorizzata.

Il fiscale ricava le condizioni dal catalogo già citato `tax_review_rules`, solo dopo controllo dell’edizione e della ricevuta della fonte. Ogni scelta conserva domanda, informazioni da raccogliere, estratto letterale, pagina, anno d’imposta, edizione e digest del documento. La domanda del catalogo non viene presentata come citazione letterale: l’estratto è separato. Il modello non decide applicabilità, soddisfazione dei requisiti o spettanza. La checklist locale completa non viene ridotta dalla selezione. Con le fixture tutte le indicazioni restano esplicitamente simulate.

Le ricevute del gateway legano anche la risposta fiscale all’inferenza effettiva: l’agente non può cambiarla o ometterla. Nel prompt minimizzato non compaiono interessi, quota, importi del mutuo, PDF o identificativi; nel solo laboratorio senza minimizzazione si conserva il profilo finanziario strutturato concordato. Gli estratti pubblici sono esentati dal controllo di sottostringhe sensibili solo dopo ricostruzione esatta dal catalogo verificato. Filtri conservativi possono escludere anche frasi lecite; non certificano tutte le parafrasi. I commenti fiscali senza chiusura di frase sono esclusi, senza completamenti inventati.

## Verifica del primo blocco

Pilota tecnico della demo aggiornata con fonti reali, distinto dal confronto 2×2 e dalla campagna finale. Fermare il ponte precedente con Ctrl+C; lasciare Docker Desktop e Ollama aperti. Dalla radice della repository:

```bash
.venv/bin/python -m pytest -q
docker build -f deployment/Dockerfile -t tesi-s03-app:local .
docker compose -f compose.isolated.yaml -f compose.ecb.yaml -f compose.ade.yaml --profile verification up -d --no-build
```

In un secondo terminale, sempre nella repository, avviare un solo ponte e lasciarlo aperto:

```bash
.venv/bin/python scripts/run_ollama_bridge.py --enable-ecb --enable-ade
```

Nel primo terminale:

```bash
.venv/bin/python scripts/check_block1.py --output runs/block1_manual.json --reports-dir runs/block1_reports
```

Windows PowerShell: stessi comandi Docker; sostituire `.venv/bin/python` con `.\.venv\Scripts\python.exe` nei tre comandi Python. Per ripetere il pilota scegliere nomi nuovi per output e cartella: non sovrascrive prove esistenti.

Esiti attesi: C001/C024/C021 `completed`, C006/C011 `partial`; per tutti `passed: True`, `pulizia: True`, infine `passed: True`. Il controllo include PDF/citazioni/periodi, fonti/digest/ricevute, checklist completa e assenza di spettanza, calcoli locali, inventario dei risultati, ricostruzione delle selezioni, tracce e cancellazione della sessione e delle viste. Le fonti reali devono rispondere: nessun successo viene attribuito a un errore di fonte o del modello. I JSON e HTML esportati sono copie client del report sintetico richieste esplicitamente, separate dai metadati di verifica; nessun nuovo archivio del gateway.

`selection_only` è ammesso: conferma la selezione controllata e l’esclusione del commento, non la qualità della prosa. Aprire i cinque HTML e controllare leggibilità, utilità delle condizioni evidenziate e limiti; citazioni corrette non garantiscono da sole pertinenza o completezza dell’interpretazione. Questo giudizio non riceve automaticamente un voto positivo dal pilota.

## Verifica del secondo blocco

Riferimenti e limiti nel [registro](REGISTRO_PROVE.md). È un pilota del runtime v6, non il congelamento o la campagna finale. S04 è stato autorizzato dall’autore soltanto per payload sintetici, risultato/metadati ostili e Card locali. Conservare i precedenti risultati: non diventano evidenze della nuova immagine.

Fermare **tutti i ponti ordinari** con Ctrl+C, compreso quello sperimentale. Lasciare Docker Desktop e Ollama aperti. Dalla repository, macOS:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/check_evaluation_protocol.py
.venv/bin/python scripts/check_test_registry.py
docker build -f deployment/Dockerfile -t tesi-s03-app:local .
.venv/bin/python scripts/setup_isolation.py
.venv/bin/python scripts/setup_baseline.py
.venv/bin/python scripts/check_block2.py --live-pilot --output runs/block2_manual.json
```

Windows PowerShell, stessi controlli:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/check_evaluation_protocol.py
.\.venv\Scripts\python.exe scripts/check_test_registry.py
docker build -f deployment/Dockerfile -t tesi-s03-app:local .
.\.venv\Scripts\python.exe scripts/setup_isolation.py
.\.venv\Scripts\python.exe scripts/setup_baseline.py
.\.venv\Scripts\python.exe scripts/check_block2.py --live-pilot --output runs/block2_manual.json
```

Le identità esistenti vengono mantenute. Lo script configura e verifica le celle S+P, S−P, M+P, M−P, usa un ponte controllato per le prove funzionali e gestisce autonomamente il ponte Ollama per il pilota reale. **Non avviare un ponte a mano durante la procedura.** Le fonti restano locali/simulate; nessun recupero BCE/AdE avviene nel confronto. Il timeout fonte attende davvero 30 secondi in ogni cella: la procedura richiede diversi minuti.

Atteso: audit senza problemi, `S04 autorizzato: True` nel perimetro concordato e campagna finale ancora non autorizzata. I casi nominali completi mostrano `completed`; gli input insufficienti `partial`/`blocked`; i guasti e la provenienza mancante gli esiti previsti, senza trasformarli in successi analitici. Ogni verifica riuscita stampa `passed: True pulizia: True`; il riepilogo finale deve essere `passed: True`. Nel pilota Ollama C001/C024 completano e C006/C011/C016 sono parziali, tutti con controlli e pulizia positivi. Se una verifica fallisce il comando termina con esito non positivo e conserva la fase e le evidenze disponibili.

Il JSON principale rinvia ai quattro esiti di cella, alle tracce e ai quattro JSONL reali. I report finanziari non vengono archiviati automaticamente dal gateway. I consumi delle fixture controllate non sono misure Ollama. Le scelte LLM e gli eventuali commenti restano da valutare umanamente, anche quando il pilota tecnico passa. Per ripetere scegliere un nome di output nuovo; non sovrascrivere prove precedenti.

Alla fine viene ripristinata **la demo base con fonti simulate**, senza lasciare ponti in background. Per tornare alla demo BCE/AdE seguire il README. I soli esiti verificati vanno aggiunti al diario: questa procedura non autorizza la campagna finale.


## Verifica del terzo blocco — interfaccia e documento

Stesso gateway, agenti, fonti, modelli e budget: questo incremento presenta gli esiti, senza aggiungere calcoli o criteri finanziari. Le fasi vengono lette dalla traccia locale già esistente, senza percentuali simulate. Il verde indica completamento tecnico, non correttezza semantica del modello. I dati obbligatori inutilizzabili e i conflitti sono rossi con testo/simbolo; contesto non specificato, fonti simulate e commenti esclusi sono note ambra. Periodi differenti fra mutuo e anno fiscale non sono automaticamente conflitti.

Dalla repository, macOS, fermare il ponte precedente con Ctrl+C; lasciare Docker Desktop e Ollama aperti:

```bash
.venv/bin/python -m pytest -q --ignore=tests/test_block2_pipeline.py
docker build -f deployment/Dockerfile -t tesi-s03-app:local .
docker compose -f compose.isolated.yaml -f compose.ecb.yaml -f compose.ade.yaml --profile verification up -d --no-build
```

In un secondo terminale, avviare un solo ponte e lasciarlo aperto:

```bash
.venv/bin/python scripts/run_ollama_bridge.py --enable-ecb --enable-ade
```

Windows PowerShell: stessi comandi Docker; comandi Python corrispondenti:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests/test_block2_pipeline.py
.\.venv\Scripts\python.exe scripts/run_ollama_bridge.py --enable-ecb --enable-ade
```

Il ponte va nel secondo terminale anche su Windows. Le 76 integrazioni lunghe del blocco 2 restano separate: questa verifica esegue le regressioni, senza ripetere la campagna Docker. Verifica di sviluppo corrente: 826 test passati, 127 warning delle dipendenze. Atteso sulla propria installazione: test passati; i warning delle dipendenze non vanno nascosti. Nessun nuovo programma o pacchetto grafico da installare per la demo.

Aprire http://127.0.0.1:8080/ e ricaricare completamente la pagina (Cmd+Shift+R su macOS, Ctrl+F5 su Windows). Scegliere entrambi gli approfondimenti. Per ogni caso selezionare almeno mutuo e interessi dello stesso fascicolo, poi **Carica e verifica → Avvia analisi**. Conto e paga facoltativi non alimentano i due scenari. Non modificare manualmente i dati estratti.

| Caso | Esito atteso con fonti/modelli disponibili | Controllo visivo |
|---|---|---|
| C001 | completo | Entrambi gli esiti disponibili; tipologia non specificata come limite, non errore obbligatorio. |
| C006 | parziale | Capitale mancante e attività mercati non eseguibile in rosso; risultato fiscale conservato. |
| C016 | parziale | TAN ambiguo in rosso, nessuna scelta arbitraria del tasso; risultato fiscale conservato. |
| C021 | completo | Periodi distinti nei documenti, senza conflitto inventato tra domini. |

Usare **Nuova analisi** fra i casi. Una fase registrata non dimostra da sola correttezza del risultato; se la traccia non è disponibile, la pagina lo dichiara senza inventare avanzamento. Verificare le fonti effettivamente recuperate nel report: una fonte configurata non è necessariamente disponibile. Il tasso mensile aggregato BCE non è un’offerta né il TAN da usare come tasso alternativo personale. Le condizioni AdE restano da verificare. Commento escluso e selezione valida sono distinti.

Su C001 scaricare **documento HTML** e **dati JSON**. Aprire l’HTML: deve contenere gli stessi importi, periodi, fonti, citazioni, selezioni, ipotesi e limiti, senza dipendenze grafiche da Internet. Con **Stampa / salva PDF**, oppure stampando l’HTML scaricato nel browser, controllare l’anteprima A4: tutte le sezioni, righe e citazioni devono essere leggibili, senza tagli laterali; nessun modulo di upload o dettaglio tecnico nella stampa. Il salvataggio PDF nel browser dell’autore è una conferma manuale distinta dai test automatici. Se il browser integrato non apre la stampa, aprire la demo o l’HTML in un browser ordinario.

Verificare il JSON esportato (adattare il solo nome se il browser aggiunge un suffisso):

```bash
# macOS
.venv/bin/python scripts/check_report_provenance.py "$HOME/Downloads/report-locale.json"
```

```powershell
# Windows PowerShell
.\.venv\Scripts\python.exe scripts/check_report_provenance.py "$HOME\Downloads\report-locale.json"
```

Atteso C001: **Fatti verificati: 10; Problemi: 0**. Per C006: 9, zero problemi; C016: 10, zero problemi (anche l’ambiguità documentata mantiene provenienza); C021: 10, zero problemi. Questo controllo non attribuisce un voto alla prosa del modello e non confronta l’impaginazione del PDF.

Infine ricaricare C001, avviare e premere **Annulla analisi e cancella sessione** mentre è in corso. Atteso: annullamento/chiusura dichiarati, nessun report tardivo mostrato, nuovo caricamento consentito. Ripetere C001 e verificare il recupero. Se il completamento precede il clic, la pagina dichiara la sessione già chiusa: non registrarlo come annullamento durante l’esecuzione.

Il test di presentazione indisponibile resta automatico: mantiene report JSON e pulizia, disabilitando HTML/stampa senza documento inventato. I conflitti di valori hanno entrambe le provenienze e conclusioni sospese; il controllo UI di questa rappresentazione usa un conflitto sintetico esplicitamente dichiarato, distinto dalla prova agente–agente del blocco 2. Nessun nuovo endpoint di collaudo è incluso nella distribuzione.


## Verifica del quarto blocco — valutazione riproducibile

Questo blocco aggiunge strumenti del valutatore, non modifica agenti, policy, fonti o budget. La preparazione non congela né avvia la campagna. `evaluation/protocol.json` resta il documento di preparazione con soglie già approvate; l’eventuale `approval.json` congela separatamente l’intero snapshot identificato dal digest del manifest, incluso il protocollo copiato. Nessuna autorizzazione finale viene dedotta dall’ok ai blocchi di sviluppo.

### Piano e conteggi

Il runner usa 40 blocchi (10 ripetizioni × 4 celle), con ordine Williams delle celle e ordine dei 25 casi fissato per ripetizione e identico fra celle. Con dieci ripetizioni, non multiple di quattro, le posizioni differiscono al massimo di una presenza. Il seed del piano è registrato; non viene aggiunto un seed al modello che il payload attuale non imposta. Non si promette determinismo dell’inferenza.

| Raccolta prevista | Campagna finale | Pilota strumentato |
|---|---:|---:|
| Sessioni di base con Ollama reale | 1.000 | 20 |
| Sessioni create dai cicli controllati | 2.400 | 240 |
| Totale sessioni create | 3.400 | 260 |
| Upload negativi rifiutati prima della sessione | 120 | 12 |
| Tentativi di upload complessivi | 3.520 | 272 |
| Report effettivamente consegnabili attesi | 3.200 | 240 |

Sono conseguenze dei cicli/controlli già registrati, non nuovi casi della tesi. Ogni blocco riusa la suite Docker del blocco 2 senza il vecchio pilota a cinque casi: 45 analisi più i tre driver fisici (annullamento, relay e crash), tre upload negativi. Sono 54 sessioni create e 51 report consegnabili. TTL con orologio controllato e guasto diretto ASGI usano il percorso nativo ADK/A2A/MCP: prima, guasto, recupero per variante, sei sessioni e quattro report consegnabili. Non sono prove di isolamento Docker o attese reali di 1.800 secondi. Il controllo standard immediatamente precedente alla sostituzione è riusato esplicitamente nella sequenza standard/equivalente/ripristino.

I conteggi attesi non sostituiscono quelli osservati: un errore resta nel registro. Un report generato a monte ma perso nel relay non viene trattato come consegnato al valutatore. Input rifiutati, annullamento, TTL, guasto ASGI e crash non ricevono un voto zero inventato. Nessuna deduplicazione dei report o copia di voti. Le basi con Ollama sono separate dalle risposte controllate, anche nei riepiloghi di token e qualità.

### Preparazione e pilota, macOS

Fermare con Ctrl+C tutti i ponti già aperti, ordinari o sperimentali. Lasciare Docker Desktop e Ollama attivi. Controllare `ollama ps`: non devono esserci modelli caricati o altre inferenze in corso; se necessario `ollama stop NOME_MODELLO` scarica dalla memoria il solo modello indicato, senza eliminarlo. Il runner richiede questa condizione all’inizio di ogni blocco e mantiene `keep_alive=0`. Il runner gestisce i propri ponti: **non avviarne uno a mano durante il pilota**. Dalla repository:

```bash
.venv/bin/python -m pytest -q --ignore=tests/test_block2_pipeline.py
.venv/bin/python -m pytest -q tests/test_block2_pipeline.py -k nominal
docker build -f deployment/Dockerfile -t tesi-s03-app:local .
.venv/bin/python scripts/setup_isolation.py
.venv/bin/python scripts/setup_baseline.py
.venv/bin/python scripts/prepare_campaign.py prepare --directory runs/campaign_v1
.venv/bin/python scripts/prepare_campaign.py check --directory runs/campaign_v1
.venv/bin/python scripts/run_campaign.py --directory runs/campaign_v1 --pilot
```

La seconda immagine netguard è quella già usata nei blocchi precedenti; per una prima installazione seguire il README. Il preparatore controlla che i file runtime nell’immagine coincidano con i sorgenti. Registra immagini, versioni host/container, pesi del modello comune, configurazione, PDF/fixture, annotazioni e rubriche, senza nomi utente, percorsi personali, credenziali o prompt delle sessioni. Usa i parametri esistenti (4096 token di contesto, temperatura zero, 768/200 token di risposta, `keep_alive=0`, budget 120/90/30/5). L’ambiente viene controllato prima e dopo ogni blocco. L’analisi non riceve mai annotazioni o voti.

Atteso: test passati; quattro prove nominali della pipeline passate; manifest preparato, `Campagna avviata: False`, poi `Problemi: 0`. Il pilota attraversa quattro celle, con cinque casi Ollama per cella e i cicli controllati, e richiede diversi minuti. Le righe nominali dopo ogni guasto sono i controlli di recupero previsti. Per blocco: `created: 65`, `rejected: 3`, `delivered: 60`, conteggi coerenti; alla fine **`Pilota completo: True`**. Il runner restituisce la demo base simulata e chiude i propri ponti.

La cartella deve essere nuova. Manifest o file cambiati bloccano l’esecuzione; dopo una modifica al codice preparare un nuovo snapshot. Un blocco iniziato non viene ripetuto automaticamente. Per proseguire usare `--block ID` soltanto su blocchi mai avviati, mantenendo piano e ripetizione originali; non spostare o cancellare un fallimento per farlo sparire. Un upload senza risposta resta di esito ignoto e non viene presentato come sessione sicuramente assente/pulita. Se manca la conferma della pulizia, il runner si ferma.

### Registro cieco e riepilogo del pilota

Dopo il completamento:

```bash
.venv/bin/python scripts/review_campaign.py export --directory runs/campaign_v1 --pilot
.venv/bin/python scripts/review_campaign.py summary --directory runs/campaign_v1 --pilot --output runs/campaign_v1/pilot/summary.json
open runs/campaign_v1/pilot/public/index.html
```

Atteso: 240 report nel registro se tutti i percorsi hanno gli esiti previsti; **punteggi assegnati automaticamente: 0**. I campi di `public/ratings.csv` devono essere vuoti. Il riepilogo senza `--ratings` ha qualità non disponibile, nessuna media/voto simulato. Non serve assegnare 240 voti al pilota per provare il funzionamento del registro: controllare qualche documento, riferimenti e campi della scheda. I voti della campagna finale restano distinti.

`private/` contiene i collegamenti alle configurazioni e gli originali, `public/` soltanto gli identificativi casuali e il materiale da valutare. Il valutatore deve lavorare sul pubblico senza consultare la mappa privata; il contenuto può comunque suggerire la condizione. Un solo valutatore non consente di stimare accordo indipendente. Le trasformazioni per nascondere le etichette non cambiano importi, citazioni, selezioni o calcoli. I report identici restano schede distinte. JSON e HTML sono legati alle impronte; casi, ID duplicati/sconosciuti, voti mancanti/fuori scala e documenti alterati vengono rifiutati.

### Windows PowerShell

Stessi comandi Docker. Procedura prevista, non ancora verificata direttamente:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --ignore=tests/test_block2_pipeline.py
.\.venv\Scripts\python.exe -m pytest -q tests/test_block2_pipeline.py -k nominal
docker build -f deployment/Dockerfile -t tesi-s03-app:local .
.\.venv\Scripts\python.exe scripts/setup_isolation.py
.\.venv\Scripts\python.exe scripts/setup_baseline.py
.\.venv\Scripts\python.exe scripts/prepare_campaign.py prepare --directory runs/campaign_v1
.\.venv\Scripts\python.exe scripts/prepare_campaign.py check --directory runs/campaign_v1
.\.venv\Scripts\python.exe scripts/run_campaign.py --directory runs/campaign_v1 --pilot
.\.venv\Scripts\python.exe scripts/review_campaign.py export --directory runs/campaign_v1 --pilot
.\.venv\Scripts\python.exe scripts/review_campaign.py summary --directory runs/campaign_v1 --pilot --output runs/campaign_v1/pilot/summary.json
Start-Process "runs\campaign_v1\pilot\public\index.html"
```

Eseguire la build Docker prima di `prepare`, come su macOS. Usare sempre un nome nuovo per ripetere una prova; non sovrascrivere snapshot o giudizi.

**Pilota manuale confermato:** log e file di `runs/campaign_v1` verificati. Quattro celle positive, 272 tentativi di upload, 260 sessioni create, 240 report pubblicati e nessuna pulizia non confermata. Venti sessioni con Ollama reale (28 inferenze), distinte dalle prove controllate. Manifest e impronte delle evidenze integri; 240 associazioni ID/caso/hash e HTML coerenti, schede senza punteggi, riepilogo ricalcolato identico. Provenienza documentale ricontrollata sui 244 JSON originali: 2.388 fatti e zero problemi. I quattro report generati a monte del relay guasto non entrano nelle schede. Nessun voto umano o approvazione finale attribuiti. Non occorre ripetere il pilota se sorgenti, ingressi e ambiente restano conformi al manifest.

### Campagna finale — solo dopo revisione e autorizzazione esplicite

I comandi seguenti sono la procedura futura, **non istruzioni per avviare subito la campagna**. Dopo pilota positivo e conferma dell’autore del manifest concreto:

```bash
.venv/bin/python scripts/prepare_campaign.py approve --directory runs/campaign_v1 --approve-final-campaign
.venv/bin/python scripts/run_campaign.py --directory runs/campaign_v1
.venv/bin/python scripts/review_campaign.py export --directory runs/campaign_v1
```

Senza approvazione del manifest il secondo comando si rifiuta prima di modificare i servizi. L’approvazione richiede anche l’integrità delle evidenze del pilota corrente; non viene scritta dal pilota stesso. Nella campagna ogni sessione parte da zero; i controlli di recupero richiamano intenzionalmente gli identificativi vecchi per verificarne il diniego.

L’unico valutatore compila `final/public/ratings.csv` secondo la rubrica approvata: correttezza, copertura, provenienza e limiti, ciascuno 0–2; `critical_error` yes/no, note obbligatorie per errore critico. Poi:

```bash
.venv/bin/python scripts/review_campaign.py summary --directory runs/campaign_v1 --ratings runs/campaign_v1/final/public/ratings.csv --output runs/campaign_v1/final/summary_rated.json
```

Windows: sostituire solo l’eseguibile Python come sopra. I riepiloghi mantengono medie e varianze campionarie per caso/cella/replica e controlli distinti, conteggi di stato, disponibilità dei campioni e differenze appaiate +P/−P, singolo/multi e interazione descrittiva. Non sono test di significatività o prova di superiorità. Le fasi annidate sono inclusive: non vengono sommate per fabbricare un totale. Le due letture diagnostiche delle viste per misurare utilità sono uguali in tutte le celle e distinte dal tempo della sola analisi; l’unione dei tempi backend comprende queste richieste. Byte e categorie sono misure del JSON canonico, non catture del traffico.

Consumi sconosciuti rimangono null; i costi di energia/hardware non misurati e tariffe API non sostenute non vengono inventati. I dinieghi non sono divulgazioni. Il riepilogo non converte l’assenza di osservazioni in zero violazioni e non dichiara automaticamente soddisfatta la privacy: per il vincolo assoluto occorre leggere le prove di isolamento e le sonde autorizzate, senza compensare un’eventuale violazione con le medie. Il contenuto del modello resta soggetto a valutazione umana anche quando schema e riferimenti passano.
