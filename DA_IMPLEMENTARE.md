# Quattro passi per chiudere il prototipo

La tesi, soprattutto capitoli 3–4, resta il riferimento. Questo piano operativo concordato riunisce il residuo senza cancellare requisiti o aggiungere infrastrutture. I capitoli 5–6 saranno scritti dall’autore sulle evidenze e non sono compiti di sviluppo.

**Già disponibile:** gateway per PDF nativi del dataset, provenienza documentale, viste minimizzate, LangGraph, servizi ADK/A2A, MCP, Ollama, isolamento Docker e collegamenti controllati a BCE e alle istruzioni AdE 730/2025–2026. Esistono upload, report JSON e documento leggibile/stampabile. I piloti di annullamento, consegna fallita, crash, sostituzione MCP e tracciamento sono confermati nel perimetro descritto nel diario; non sostituiscono la valutazione finale.

**Stato del contributo LLM:** entrambi gli specialisti selezionano enunciati associati alla fonte e alla vista autorizzata. Il gateway ricostruisce testi e riferimenti; l’eventuale commento resta separato e non verificato semanticamente. Le domande fiscali riportano gli estratti delle due edizioni AdE e sono tutte candidate **da verificare**, senza spettanza accertata. I calcoli e i dati documentali restano indipendenti dal modello.

## 1. Contributo utile e circoscritto degli LLM — implementazione completata

Riferimenti: S-01/S-02, RF-04–RF-08, sezioni 4.2–4.3.

- Implementati `market-selection-1` e `tax-selection-1`: uno/due enunciati sulla fonte, uno sul contesto e commento opzionale. Identificativi fuori catalogo o risposta assente non producono sostituti inventati.
- Testi e citazioni ricostruiti dal gateway dopo la scelta. Per il fiscale: domande e informazioni da raccogliere dal catalogo già esistente, con estratti/pagine dell’edizione corrispondente. Non sono requisiti personali soddisfatti né checklist normativa esaustiva. La checklist locale completa resta disponibile anche quando il modello ne evidenzia un sottoinsieme.
- Commento escluso conservando la selezione valida (`selection_only`); nessuna certificazione semantica o di pertinenza. Estrazione, autorizzazioni, minimizzazione e calcoli restano applicativi; il modello non sceglie permessi o destinazioni.
- Modelli, budget e scadenze invariati: S-01 768 token/S-02 200, pesi comuni nel confronto, runtime `financial-profile-2x2-v5`, inferenza 0.5.0 e report 0.15.0. Nessun modello/provider/infrastruttura aggiunto.

**Verifica tecnica automatica completata.** Il pilota manuale mercati precedente è confermato su C001/C024. **Resta la conferma della demo aggiornata per entrambi gli agenti** con `scripts/check_block1.py` (cinque fascicoli, fonti reali): procedura nel protocollo. Non confondere una selezione valida con un commento corretto o una valutazione umana positiva. La nuova esecuzione a quattro celle appartiene al passo 2; i vecchi piloti non verificano v5.

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

Completare la verifica manuale del blocco 1 con i comandi forniti insieme: aggiornamento immagine, Compose con BCE/AdE, riavvio di un solo ponte e controllo dei cinque fascicoli. Lo script può esportare esplicitamente i report sul client; non crea uno storico nel gateway. Controllare il file di esito prima di registrare il successo. Quindi proseguire dal passo 2, senza nuove infrastrutture o fonti.

Su richiesta dell’autore ogni blocco viene svolto in un unico lavoro, con implementazione, documenti e verifiche automatiche; alla fine fornire tutti i comandi manuali con terminale, servizi, esiti attesi e titolo del commit. Non interrompere ogni comando per conferma. Diario breve, numerato e senza date; aggiornare i residui solo dopo verifica. S04 e campagna finale richiedono ancora autorizzazione distinta. Database dei profili, OCR, agenti remoti e ulteriori infrastrutture restano fuori dal perimetro implicito.
