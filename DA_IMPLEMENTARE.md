# Quattro passi per chiudere il prototipo

La tesi, soprattutto capitoli 3–4, resta il riferimento. Questo piano operativo concordato riunisce il residuo senza cancellare requisiti o aggiungere infrastrutture. I capitoli 5–6 saranno scritti dall’autore sulle evidenze e non sono compiti di sviluppo.

**Già disponibile:** gateway per PDF nativi del dataset, provenienza documentale, viste minimizzate, LangGraph, servizi ADK/A2A, MCP, Ollama, isolamento Docker e collegamenti controllati a BCE e alle istruzioni AdE 730/2025–2026. Esistono upload, report JSON e documento leggibile/stampabile. I piloti di annullamento, consegna fallita, crash, sostituzione MCP e tracciamento sono confermati nel perimetro descritto nel diario; non sostituiscono la valutazione finale.

**Stato del contributo LLM:** entrambi gli specialisti selezionano enunciati associati alla fonte e alla vista autorizzata. Il gateway ricostruisce testi e riferimenti; l’eventuale commento resta separato e non verificato semanticamente. Le domande fiscali riportano gli estratti delle due edizioni AdE e sono tutte candidate **da verificare**, senza spettanza accertata. I calcoli e i dati documentali restano indipendenti dal modello.

## 1. Contributo utile e circoscritto degli LLM — implementazione completata

Riferimenti: S-01/S-02, RF-04–RF-08, sezioni 4.2–4.3.

- Implementati `market-selection-1` e `tax-selection-1`: uno/due enunciati sulla fonte, uno sul contesto e commento opzionale. Identificativi fuori catalogo o risposta assente non producono sostituti inventati.
- Testi e citazioni ricostruiti dal gateway dopo la scelta. Per il fiscale: domande e informazioni da raccogliere dal catalogo già esistente, con estratti/pagine dell’edizione corrispondente. Non sono requisiti personali soddisfatti né checklist normativa esaustiva. La checklist locale completa resta disponibile anche quando il modello ne evidenzia un sottoinsieme.
- Commento escluso conservando la selezione valida (`selection_only`); nessuna certificazione semantica o di pertinenza. Estrazione, autorizzazioni, minimizzazione e calcoli restano applicativi; il modello non sceglie permessi o destinazioni.
- Modelli, budget e scadenze invariati: S-01 768 token/S-02 200, pesi comuni nel confronto, runtime corrente `financial-profile-2x2-v6`, inferenza 0.5.0 e report 0.16.0. Nessun modello/provider/infrastruttura aggiunto.

**Verifica tecnica automatica completata.** Il pilota manuale mercati precedente è confermato su C001/C024. **Resta la conferma della demo aggiornata per entrambi gli agenti** con `scripts/check_block1.py` (cinque fascicoli, fonti reali): procedura nel protocollo. Non confondere una selezione valida con un commento corretto o una valutazione umana positiva. La nuova esecuzione a quattro celle è predisposta nel passo 2; i vecchi piloti non verificano v6.

## 2. Risultati e verifiche — implementazione predisposta, pilota finale del blocco da confermare

Riferimenti: RF-07–RF-10, RNF-02–RNF-06, V-01–V-10, §§4.4–4.5.

- Collegati gli agenti reali al riferimento comune tramite MCP e capability distinte. Ricevute controllate dal gateway; replay pubblico distinto da controfattuali simulati. Confronti e provenienze nel report, senza sovrascrivere i documenti.
- Predisposte le varianti del registro: input negativi fissati per digest, guasti fonte, provenienza, conflitti, sostituzione, utilità prima della validazione e controlli del ciclo di vita. Le prove applicative controllate e quelle Docker hanno perimetri espliciti.
- **S04 autorizzato dall’autore soltanto per i tre cicli locali concordati**, senza destinazioni Internet di esfiltrazione. Card alterate nel trasporto di verifica; payload nel punto di controllo; nessuna pretesa di copertura universale degli attacchi.
- Aggiornati contatori e driver: runtime `financial-profile-2x2-v6`, strumenti 0.5.0, report 0.16.0. Ogni attività completata consulta due strumenti MCP e un modello; condizioni uguali fra le quattro celle. Corretto il long poll HTTP disconnesso del ponte, che poteva sottrarre un job alla richiesta successiva.

**Residuo per chiudere il blocco:** eseguire e controllare `scripts/check_block2.py --live-pilot` sull’immagine aggiornata. Il comando percorre le quattro celle e ripete il pilota reale a cinque fascicoli per cella. Non certifica qualità semantica o finale, non avvia le dieci ripetizioni e non sostituisce il manifest congelato. Registro e procedure nel [REGISTRO_PROVE.md](REGISTRO_PROVE.md).

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

Confermare il pilota corrente del blocco 2 con i comandi completi nel protocollo; conservare anche gli esiti negativi senza sovrascriverli. Poi restano la rifinitura della demo/documento (blocco 3) e la valutazione riproducibile con manifest, registro cieco e congelamento (blocco 4). La verifica reale BCE/AdE del blocco 1 rimane distinta dal confronto sulle fixture.

Ogni blocco viene svolto in un unico lavoro, con codice, documenti e verifiche automatiche; alla fine fornire tutti i comandi manuali con terminale, servizi, esiti attesi e titolo del commit. Diario breve, numerato e senza date. Scalare il residuo soltanto dopo verifica. La campagna finale richiede autorizzazione distinta; S04 ha soltanto l’autorizzazione locale circoscritta registrata. Database dei profili, OCR, agenti remoti e nuove infrastrutture restano fuori dal perimetro implicito.
