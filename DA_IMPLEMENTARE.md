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

**Verifica tecnica automatica completata.** Il pilota manuale mercati precedente è confermato su C001/C024. **Resta la conferma della demo aggiornata per entrambi gli agenti** con `scripts/check_block1.py` (cinque fascicoli, fonti reali): procedura nel protocollo. Non confondere una selezione valida con un commento corretto o una valutazione umana positiva. Il pilota corrente a quattro celle è confermato nel passo 2; i vecchi piloti non verificano v6.

## 2. Risultati e verifiche — pilota tecnico confermato

Riferimenti: RF-07–RF-10, RNF-02–RNF-06, V-01–V-10, §§4.4–4.5.

- Collegati gli agenti reali al riferimento comune tramite MCP e capability distinte. Ricevute controllate dal gateway; replay pubblico distinto da controfattuali simulati. Confronti e provenienze nel report, senza sovrascrivere i documenti.
- Predisposte le varianti del registro: input negativi fissati per digest, guasti fonte, provenienza, conflitti, sostituzione, utilità prima della validazione e controlli del ciclo di vita. Le prove applicative controllate e quelle Docker hanno perimetri espliciti.
- **S04 autorizzato dall’autore soltanto per i tre cicli locali concordati**, senza destinazioni Internet di esfiltrazione. Card alterate nel trasporto di verifica; payload nel punto di controllo; nessuna pretesa di copertura universale degli attacchi.
- Aggiornati contatori e driver: runtime `financial-profile-2x2-v6`, strumenti 0.5.0, report 0.16.0. Ogni attività completata consulta due strumenti MCP e un modello; condizioni uguali fra le quattro celle. Corretto il long poll HTTP disconnesso del ponte, che poteva sottrarre un job alla richiesta successiva.

**Pilota confermato dai file `runs/block2_manual*`:** quattro celle, 54 prove controllate e isolamento positivo per cella, venti esecuzioni Ollama complessive con pulizia confermata; confronto fra celle: 259 controlli, zero problemi. Non certifica qualità semantica o finale, non avvia le dieci ripetizioni e non sostituisce il manifest congelato. Registro e procedure nel [REGISTRO_PROVE.md](REGISTRO_PROVE.md).

## 3. Rifinire la demo e il documento per l’utente — implementato, verifica manuale della demo aggiornata pendente

Riferimenti: RF-01/RF-02/RF-08/RF-09, RNF-07, sezione 4.2.

- Completata la pagina: caricamento, avvio, avanzamento dai metadati esistenti, esiti degli agenti e download HTML/JSON. Stampa tramite il browser, senza percentuali o fasi simulate.
- Errori, conflitti e dati obbligatori inutilizzabili evidenziati con testo, simbolo e rosso; limiti non bloccanti in ambra. Periodi diversi tra domini differenti non sono automaticamente conflitti.
- Documento derivato dallo stesso JSON verificato, con citazioni, ipotesi e limiti; nessuna nuova inferenza o calcolo di presentazione. Conservati i riferimenti comuni anche quando si richiede solo S-02.
- Perimetro del parser esplicito nella pagina e nel documento: template sintetici nativi, niente OCR; conto e busta paga non alimentano S-01/S-02. Non viene presentata un’analisi completa di reddito e liquidità.

**Da confermare dall’autore:** demo Docker/Ollama aggiornata e anteprima/salvataggio PDF nel proprio browser, con i casi e i comandi nel protocollo. Le prove UI con modello controllato non attestano qualità LLM o una nuova acquisizione Internet. Esportazione esplicita, nessuno storico dei profili; un guasto di presentazione conserva il risultato strutturato.

## 4. Valutazione riproducibile — pilota confermato, approvazione finale pendente

Riferimenti: RNF-08, RQ1–RQ3, sezioni 3.5/4.6.

- Conservare il confronto singolo/multi × minimizzazione attiva/disattivata, con dati, pesi, impostazioni, fonti fissate e budget comparabili. Senza minimizzazione si condivide il profilo finanziario strutturato concordato, mai PDF, testo grezzo o identificativi; nessun servizio reale è raggiungibile in queste condizioni.
- Implementati manifest di sorgenti, PDF/fixture, dipendenze, immagini e pesi Ollama; piano bilanciato a blocchi, runner e registro cieco per l’unico valutatore. Le 25 annotazioni, soglie e rubrica restano quelle approvate. I dati del valutatore sono separati dal runtime. Nessuna approvazione finale registrata automaticamente.
- Predisposte le dieci ripetizioni per caso/configurazione e tutte le varianti già registrate, con controlli adiacenti, conteggio degli ingressi e dei report consegnati. Riprese solo su blocchi mai avviati: nessun retry/overwrite implicito. Riepiloghi di tempi, token, byte/categorie e utilità; media/varianza campionaria, contrasti organizzazione/policy e interazione descrittiva. Voti importati dal solo valutatore; costi non misurati e osservazioni assenti rimangono null, senza successi o tariffe inventati.
- Tenere separate demo Internet e confronto su fonti locali/simulate fissate. Verificare setup macOS/Windows; Windows non è ancora verificato direttamente.

**Pilota confermato:** `runs/campaign_v1`, quattro celle positive, 260 sessioni create, 12 upload rifiutati e 240 report consegnati; venti sessioni Ollama reali, schede ancora senza voti. Manifest, evidenze e pubblicazione verificati. **Residuo:** approvare esplicitamente quel manifest, prima delle esecuzioni finali e dei voti umani. Piano atteso: 1.000 basi Ollama + 2.400 sessioni dei cicli controllati già concordati, 120 upload rifiutati e 3.200 report consegnabili da valutare, se tutti i percorsi hanno gli esiti previsti. I numeri osservati e le assenze vengono registrati: non sono risultati già ottenuti. Nessuna deduplicazione arbitraria dei controlli. I vecchi piloti non sostituiscono questa raccolta.

## Metodo e prossimo intervento

I piloti dei blocchi 2 e 4 sono confermati. Resta distinta la conferma manuale della demo/PDF (blocco 3). Il manifest concreto `runs/campaign_v1` è verificato e attende l’approvazione esplicita dell’autore per la campagna finale, senza ulteriori funzionalità da aggiungere al prototipo. Conservare anche gli esiti negativi senza sovrascriverli. La verifica reale BCE/AdE del blocco 1 rimane distinta dal confronto sulle fixture.

Ogni blocco viene svolto in un unico lavoro, con codice, documenti e verifiche automatiche; alla fine fornire tutti i comandi manuali con terminale, servizi, esiti attesi e titolo del commit. Diario breve, numerato e senza date. Scalare il residuo soltanto dopo verifica. La campagna finale richiede autorizzazione distinta; S04 ha soltanto l’autorizzazione locale circoscritta registrata. Database dei profili, OCR, agenti remoti e nuove infrastrutture restano fuori dal perimetro implicito.
