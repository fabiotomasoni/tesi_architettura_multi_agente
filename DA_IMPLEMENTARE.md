# Quattro passi per chiudere il prototipo

La tesi, soprattutto capitoli 3–4, resta il riferimento. Questo piano operativo concordato riunisce il residuo senza cancellare requisiti o aggiungere infrastrutture. I capitoli 5–6 saranno scritti dall’autore sulle evidenze e non sono compiti di sviluppo.

**Già disponibile:** gateway per PDF nativi del dataset, provenienza documentale, viste minimizzate, LangGraph, servizi ADK/A2A, MCP, Ollama, isolamento Docker e collegamenti controllati a BCE e alle istruzioni AdE 730/2025–2026. Esistono upload, report JSON e documento leggibile/stampabile. I piloti di annullamento, consegna fallita, crash, sostituzione MCP e tracciamento sono confermati nel perimetro descritto nel diario; non sostituiscono la valutazione finale.

**Punto da correggere:** oggi gli LLM descrivono le fonti, ma la loro prosa è esclusa dal report; analisi e sintesi utilizzate sono applicative. La base tecnica è avanzata, mentre il contributo utile dei modelli resta da realizzare e valutare. I quattro passi seguenti sono ancora aperti.

## 1. Dare agli LLM un compito utile e circoscritto

Riferimenti: S-01/S-02, RF-04–RF-08, sezioni 4.2–4.3.

- Partire dall’agente mercati: usare la vista autorizzata e la fonte già verificata per spiegare pertinenza, limiti e informazioni mancanti rispetto all’attività richiesta. La statistica BCE aggregata non diventa un TAN contrattuale o un’offerta personale.
- Estendere poi il fiscale: individuare condizioni pertinenti e informazioni mancanti nei passaggi annuali AdE autorizzati, senza dichiarare spettanza o calcolare detrazioni.
- Definire risposte strutturate con riferimenti alle evidenze ricevute. I dettagli dei contratti vanno concordati prima dell’implementazione. Nessun nuovo provider, modello o terzo LLM orchestratore necessario.
- Mantenere applicativi estrazione, autorizzazioni, minimizzazione, calcoli e controlli numerici. Il modello non decide i propri permessi. Nelle prove simulate deve riconoscere il carattere simulato delle fonti.

**Chiusura:** il modello produce un contributo identificabile e utile all’analisi, distinto dai risultati già ottenuti con regole. Verificare anche l’assenza di risposta o una risposta irrilevante: il sistema deve segnalarla, senza inventare un’analisi completata. Non richiedere differenze artificiali tra singolo agente e multi-agente.

## 2. Integrare i risultati nel report e completarne le verifiche

Riferimenti: RF-07–RF-10, RNF-02–RNF-06, V-01–V-10, sezioni 4.4–4.5.

- Integrare separatamente fatti documentali, fonti, calcoli locali e analisi generata. Controllare schema, riferimenti, numeri, omissioni e affermazioni non supportate. Una citazione valida non prova da sola la correttezza dell’intera spiegazione: la prosa non verificata resta dichiarata tale.
- Completare V-09 tramite gli agenti reali, come concordato: entrambi consultano via MCP il riferimento BCE comune. Fonte e contratto nominale sono già definiti; mancano integrazione e fixture controfattuali esplicite. Questo controllo di interoperabilità non sostituisce il lavoro utile del passo 1.
- Riutilizzare REGISTRO_PROVE.md ed evaluation/test_registry.json per materializzare le sole istanze mancanti e adattare i driver alle quattro configurazioni. Distinguere timeout della fonte da timeout del modello, e conflitto verificato da risultato infedele alla fonte.
- Dopo le modifiche agli agenti aggiornare la versione del runtime sperimentale e ripetere il pilota a quattro celle. Nessun vecchio successo prova automaticamente il nuovo comportamento.

**Chiusura:** ogni famiglia V-01–V-10 ha procedura ed evidenza riproducibile; guasti, conflitti e fonti mancanti producono limiti o esiti parziali corretti. **S04, incluse le nuove prove ostili e sulle Agent Card, resta in attesa dell’ok esplicito dell’utente.**

## 3. Rifinire la demo e il documento per l’utente

Riferimenti: RF-01/RF-02/RF-08/RF-09, RNF-07, sezione 4.2.

- Completare la pagina esistente: caricamento, avvio, avanzamento reale delle attività, esiti degli agenti e salvataggio del documento. Non simulare percentuali o fasi.
- Evidenziare errori, conflitti e dati obbligatori mancanti con testo, simbolo e rosso; distinguere i limiti non bloccanti. Periodi diversi tra domini differenti non sono automaticamente conflitti.
- Costruire il documento sullo stesso JSON verificato, conservando citazioni, ipotesi e limiti. Nessuna conclusione definitiva di convenienza o spettanza senza evidenze sufficienti.
- Dichiarare il perimetro del parser: template sintetici nativi, niente OCR; conto e busta paga oggi non alimentano S-01/S-02. Non presentare un’analisi completa di reddito e liquidità.

**Chiusura:** un utente comprende anche un risultato parziale; documento e JSON sono coerenti. Esportazione esplicita, nessuno storico dei profili; un guasto di presentazione conserva il risultato strutturato.

## 4. Completare la valutazione riproducibile

Riferimenti: RNF-08, RQ1–RQ3, sezioni 3.5/4.6.

- Conservare il confronto singolo/multi × minimizzazione attiva/disattivata, con dati, pesi, impostazioni, fonti fissate e budget comparabili. Senza minimizzazione si condivide il profilo finanziario strutturato concordato, mai PDF, testo grezzo o identificativi; nessun servizio reale è raggiungibile in queste condizioni.
- Preparare manifest di ambiente/modelli, runner finale e registro cieco per l’unico valutatore concordato. Le 25 annotazioni sono confermate dall’autore; soglie e rubrica sono approvate. Il protocollo completo resta da congelare e la campagna finale non è ancora autorizzata.
- Eseguire le dieci ripetizioni indipendenti per caso/configurazione previste, dopo il congelamento. Misurare qualità e utilità del contributo LLM, privacy, robustezza, tempi, token e costi; distinguere dati osservati, stime e consumi non disponibili. Riportare media, varianza campionaria e conteggi/tassi, senza assumere superiorità del multi-agente.
- Tenere separate demo Internet e confronto su fonti locali/simulate fissate. Verificare setup macOS/Windows; Windows non è ancora verificato direttamente.

**Chiusura:** demo riproducibile e risultati collegati alle tre RQ, con limiti dichiarati. I piloti delle quattro celle già eseguiti (cinque casi, una ripetizione per cella) non sono la campagna finale.

## Metodo e prossimo intervento

**Partire dal passo 1, agente mercati:** concordare il contratto minimo di analisi contestuale, poi implementare e verificare il percorso completo prima di replicarlo sul fiscale. Riutilizzare vista minimizzata, connettore BCE e gateway esistenti; nessuna nuova fonte o ipotesi economica implicita. Un confronto finanziario alternativo reale richiederebbe un riferimento compatibile e costi documentati: non ricavarlo dalla statistica BCE.

Aggiornare questo file rimuovendo il residuo soltanto dopo verifica. Dettare i comandi in chat uno alla volta, indicando terminale, servizi e risultato atteso; controllare anche i file prodotti prima di registrare un successo nel diario. Mantenere il diario breve, numerato e senza date. Non avviare la campagna finale o S04 con un semplice aggiornamento documentale. Database dei profili, OCR, agenti remoti e ulteriori infrastrutture restano fuori dal perimetro implicito.
