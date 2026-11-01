# Quattro passi verso la consegna

La tesi, soprattutto capitoli 3–4, resta il riferimento. I precedenti P/S/R/E/T/X sono riuniti qui: meno passaggi operativi, senza cancellare requisiti o aggiungere nuovi progetti.

**Oggi:** gateway PDF, viste minimizzate, LangGraph, due agenti ADK/A2A, MCP, Ollama, controlli di provenienza, calcoli locali e isolamento verificati nel catalogo attuale. Esistono upload, report JSON e una prima presentazione leggibile/stampabile. **Sono disponibili fonti reali BCE e pubblicazioni annuali AdE, oltre alle fixture degli esperimenti**, il parser riconosce il template sintetico e il testo LLM non verificato è escluso dal documento.

## 1. Fonti reali e lavoro utile degli agenti

Riferimenti: S-01/S-02, RF-04–RF-07, sezioni 4.2–4.3. **È parte della consegna, non un’estensione facoltativa.**

Il primo collegamento mercati alla serie mensile BCE è implementato, con citazione e controllo della risposta; confermato anche nelle prove manuali C001/C006. Il suo indicatore aggregato non è utilizzabile come TAN. Implementato anche il collegamento fiscale alle istruzioni 730/2025 e 730/2026, attraverso il proxy del gateway e HTTPS; verifica manuale completata con C001, C021 e C011 (due annualità, due finalità, esito parziale). Il catalogo accetta solo le edizioni controllate: una modifica richiede revisione esplicita. Agenti e MCP non ottengono accesso diretto a Internet. Contratti e report separano ora pubblicazioni annuali reali e fixture; mantenere soltanto le destinazioni necessarie al proxy.

Ogni informazione deve avere fonte/URL, estratto citato, unità, definizione, periodo e momento del recupero. «Aggiornato» significa ultima pubblicazione disponibile: un indicatore statistico non è un’offerta personale; la norma va riferita all’anno d’imposta corretto. Un hash non certifica autorevolezza o verità. Fonte assente o dubbia: limite esplicito, senza sostituzioni inventate.

Concordare il ruolo dei modelli nella ricerca e nella produzione di informazioni citate: oggi la loro prosa non contribuisce al report. Calcoli e autorizzazioni restano applicativi; non è obbligatorio un terzo LLM.

**Verifica finale:** entrambi gli scenari consultano davvero fonti ammesse, con provenienza controllabile, nessun dato vietato trasmesso e risultato parziale corretto se una fonte manca.

L’analisi locale del contratto è ora indipendente dal confronto esterno: rata e totali teorici documentali restano disponibili senza tasso alternativo. Verifica manuale completata su C001, C024 e C006, incluso ponte spento e successivo riavvio manuale. Per un confronto alternativo reale resta da definire un riferimento compatibile con ipotesi e costi documentati. Nessuna sostituzione automatica del TAN con la statistica BCE.

S-02: riepilogo locale strutturato implementato con dati documentali, condizioni selettive da verificare, informazioni necessarie e citazioni annuali. Nessuna spettanza o codice assegnato. Test automatici e prove manuali completati con C001/C021/C011: acquisto/ristrutturazione, due annualità e input incompleto. Fonti simulate o mancanti non producono una checklist normativa reale.

## 2. Demo e documento per l’utente

Riferimenti: RF-01/RF-02/RF-08/RF-09, RNF-07, sezione 4.2.

Completare una pagina semplice: caricare, avviare, vedere avanzamento reale ed esiti degli agenti, leggere e salvare il documento. La prima presentazione e stampa/PDF tramite browser sono già presenti; gli stati durante la richiesta sono generali, non una traccia live delle fasi. Non simulare percentuali o attività.

Indicazione dell’utente per la rifinitura finale: evidenziare problemi con colore, testo e simbolo, senza affidarsi al solo colore. Rosso per errori, conflitti effettivi o dati obbligatori mancanti/ambigui che impediscono l’attività; avviso distinto per limiti non bloccanti. Periodi differenti di grandezze o domini diversi (come contratto e anno fiscale in C021) non sono automaticamente un conflitto. La grafica deve riflettere gli stati verificati nel JSON, senza inventare problemi.

Rifinire il report sullo stesso JSON: fatti e citazioni, fonti, confronto orientativo del mutuo, riferimenti fiscali, ipotesi e limiti. Nessuna detrazione o convenienza definitiva senza evidenze sufficienti. Consolidare i PDF nativi supportati e la gestione dei file esclusi; dichiarare la copertura del parser. Conto e busta paga oggi non alimentano S-01/S-02: non presentare un’analisi completa di liquidità e reddito, né aggiungere OCR implicitamente.

**Verifica finale:** un utente comprende anche un esito parziale e riceve un documento fedele al JSON. Esportazione esplicita, nessuno storico; un guasto di impaginazione conserva il risultato strutturato.

## 3. Verifiche essenziali dell’architettura

Riferimenti: RF-09/RF-10, RNF-02–RNF-06, V-01–V-10, sezioni 4.4–4.5.

Riunire le prove esistenti e completare i casi della tesi: input non utilizzabili, fonte lenta/malformata, provenienza mancante, conflitti, annullamento, consegna fallita e pulizia/recupero. La scadenza delle sessioni abbandonate è periodica. Implementato annullamento di grafo/deleghe, accessi temporanei e incarichi del ponte; prove automatiche su DELETE, disconnessione HTTP reale, TTL, rifiuto tardivo, sottoprocessi MCP reali, pulizia ADK e ripartenza degli specialisti/generalista. Conferma manuale sui container completata con check_cancellation.py: runs/cancellation_manual.json contiene 14 controlli positivi, annullamento senza report, risposte tardive rifiutate e recupero con gli stessi avvii degli agenti. Risposte del modello controllate e dichiarate, nessuna inferenza Ollama reale. Verificati automaticamente errore di invio ASGI, consegna interrotta al client e SIGKILL di un gateway temporaneo con upload parziale, perdita dello stato volatile e nuova analisi; gli agenti di questa prova nativa di crash sono fixture. Consegna fallita confermata manualmente sulla demo Docker: runs/delivery_manual.json, 20 controlli positivi, corpo non ricevuto dal client, stato rimosso e nuova analisi con gli stessi avvii. Crash confermato manualmente in runs/crash_manual.json: 22 controlli positivi, SIGKILL/uscita 137, nuovo avvio del gateway, marcatore tmpfs scomparso, stato precedente rifiutato e nuova analisi completa con gli stessi agenti. I piloti di annullamento, consegna fallita e crash sono conclusi nel perimetro dichiarato; restano istanze e ripetizioni finali. Nessuna promessa di azzeramento fisico della RAM, arresto interno immediato di Ollama o prova di interruzione elettrica dell’intero sistema.

Completare la traccia essenziale con fasi, tempi/token, conteggi A2A/MCP/fonti, dinieghi e pulizia senza contenuti sensibili. Separare tempi annidati, rendere configurabili budget/timeout e provare una sostituzione equivalente di agente/tool senza modificare l’estrazione.

Per V-05/V-10 bastano attacchi rappresentativi e controlli positivi, non interi benchmark accademici. **Il precedente S04 resta in attesa dell’ok esplicito dell’utente:** questa riscrittura non lo avvia.

**Verifica finale:** ogni V-01–V-10 ha procedura ed evidenza riproducibile; nessuna conclusione inventata dopo guasti o attacchi. Comandi dettati passo per passo e file effettivi controllati prima di registrare il successo.

## 4. Valutazione e consegna della tesi

Riferimenti: RNF-08, RQ1–RQ3, sezioni 3.5/4.6, capitoli 5–6.

Implementati i primi profili pilota S+P/M+P: un servizio ADK generalista con un incarico A2A contro due specialisti, stesso modello llama3.2:3b, fixture, policy attiva, budget di sessione 120 secondi e attività sequenziali in entrambi. Identità e configurazione demo separate; risultati per scenario e report invariati. Verifica manuale dei due profili completata sui cinque casi pilota (una ripetizione ciascuno), con esiti e risultati strutturati coincidenti. Implementati anche S−P/M−P nel perimetro concordato del profilo finanziario completo, esclusi originali/testo/identificativi. Corpus sintetico vincolato da manifest, fonti locali e controlli invariati. Il protocollo fonte+contesto è stato verificato manualmente su tutte le quattro celle: cinque casi, una ripetizione per cella, 20 esecuzioni con esiti attesi, confronto e pulizia positivi. È un pilota, non la campagna finale. Restano la copertura finale dei casi e le condizioni complete di confronto. Preparata bozza PROTOCOLLO_VALUTAZIONE.md con annotazioni preliminari dei 25 fascicoli, rubrica a un valutatore (scelta dell’utente), tolleranze/soglie proposte e mappa delle evidenze V-01–V-10. Controllo automatico disponibile; non approva né congela la campagna. Soglie, rubrica e trattamento descrittivo dei tempi approvati dall’utente; il protocollo resta non congelato. Revisione umana delle 25 annotazioni completata e confermata dall’utente; restano verifiche mancanti, manifest di ambiente, registro cieco e runner finale. Il vecchio endpoint del solo agente mercati non è la baseline.

Eseguire le **dieci sessioni indipendenti per caso e configurazione** previste dalla tesi. Nel confronto principale tutte le configurazioni usano gli stessi dati sintetici, modelli locali e risposte locali/simulate fissate. Le prove Internet della demo restano separate; senza minimizzazione nessun servizio reale è raggiungibile. Misurare privacy/utilità, qualità, tempi/token/costi, media e varianza campionaria, conteggi/tassi e zero divulgazioni vietate come vincolo assoluto. Distinguere stime e spese osservate.

Scrivere i capitoli 5–6 sulle evidenze effettive, motivare Docker e ponte locale, verificare setup macOS/Windows e conservare soltanto dati sperimentali ammessi. Windows non è ancora verificato direttamente.

**Verifica finale:** demo riproducibile, risultati collegati alle tre RQ e limiti dichiarati, senza presentare piloti o funzionalità previste come valutazione conclusa.

## Regola di lavoro

Prossimo residuo: prova positiva di sostituzione equivalente di un componente (V-06), poi completamento del tracciamento e delle istanze della campagna finale. Annullamento, consegna fallita a valle e nuova elaborazione dopo arresto forzato del gateway sono confermati anche sui container, nel perimetro dei piloti controllati. Revisione umana delle annotazioni completata: 25/25 fascicoli confermati esplicitamente dall’utente; conferme legate ai digest dei casi. Soglie e rubrica sono già approvate, il protocollo completo resta da congelare. Nuove fonti e ipotesi economiche richiedono un perimetro concordato. Ridurre il residuo al superamento delle verifiche; nel diario lasciare modifica, evidenza e limite. Database dei profili, agenti remoti, OCR, operazioni bancarie, infrastrutture ulteriori e un’interfaccia per amministrare Docker non sono requisiti impliciti della consegna.
