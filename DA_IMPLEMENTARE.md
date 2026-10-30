# Attività da completare

Lista dei lavori residui ricavata dai capitoli 3–4 della tesi e confrontata con il codice. Non è un elenco di funzionalità già realizzate. Il diario conserva decisioni e risultati; questo file conserva soltanto ciò che resta da fare.

## Regola di aggiornamento

Ogni attività ha un ID stabile. Quando codice e prove previste sono completati, registrare nel diario ID, decisioni ed evidenze, quindi rimuovere qui il compito. Se completato solo in parte, restringere la descrizione al residuo e mantenere l'ID. Non eliminare un requisito perché esiste una dimostrazione nominale. Scelte che cambiano perimetro, catalogo o protocollo sperimentale vanno concordate prima di implementarle.

P03 completato nel perimetro ipotetico concordato (Step 27); P04 completato nel perimetro ipotetico concordato (Step 29); P05 completato per i contratti e le fixture attuali (Step 32); S01 completato per il catalogo locale attuale con controlli A2A, inferenza, strumenti e fonti MCP (Step 39); prossimo lavoro S02. Nessuna fonte remota reale abilitata, isolamento e autenticazione completa restano S03. P01 completato nel perimetro del template sintetico (Step 23); P02 completato per il catalogo attuale e le fixture (Step 25). Le osservazioni del percorso reale oggi riguardano grandezze diverse: nuovi adattatori per fonti sovrapposte richiederanno ulteriori verifiche. L'ordine seguente è una proposta operativa; i riferimenti RF/RNF/V indicano invece i requisiti della tesi.

## Priorità 1 — Provenienza e correttezza dell'analisi


## Priorità 2 — Confine dei dati e controlli di sicurezza

Da completare prima di consentire fonti o inferenza esterne reali.

- [ ] **S02 — Rilevazione locale di dati vietati** (RF-03, RQ2, V-02). Integrare regole, riconoscimento locale di entità e confronto con valori sensibili noti della sessione, comprese rappresentazioni normalizzate di importi/date. Misurare divulgazioni residue e richieste legittime bloccate; nessuna promessa di anonimato assoluto.
- [ ] **S03 — Isolamento e identità dei chiamanti** (RNF-03, sezione 4.5). Container non privilegiati, senza originali/socket runtime, rete e DNS limitati. Solo proxy con uscita e credenziali remote. Autenticare i chiamanti oltre alla verifica delle Card. Completato con tentativi diretti di connessione falliti anche da tool malevolo, non solo con configurazione nominale.
- [ ] **S04 — Contenuti ostili e metadati** (V-05/V-10). Ampliare fixture malevole su Card, descrizioni tool, risultati MCP e artefatti. Verificare che contenuti non attendibili non cambino piano, permessi o destinatari. I test che rifiutano variazioni delle fixture esatte non coprono l'intero modello di minaccia.

## Priorità 3 — Robustezza, contratti e osservabilità

- [ ] **R01 — Ciclo di vita completo** (RNF-02, sezione 4.4, V-02). Coprire annullamento nella pipeline multi-agente reale, consegna del report fallita, temporanei e arresto/recupero del processo. Gestire sessioni abbandonate prima dell'avvio del workflow, oggi sotto TTL pigro. Provare anche assenza di stato nei servizi remoti dopo annullamento; non dedurla dalla sola pulizia gateway. Nessuna garanzia di azzeramento fisico RAM/swap.
- [ ] **R02 — Budget, timeout e guasti ulteriori** (RNF-04/RNF-06, V-04). Portare valori hardcoded in configurazione fidata; fissarli prima della campagna. Fixture per timeout durante Ollama, fonte fiscale lenta, risposte malformate e risultato fiscale errato; verificare esito parziale, mancati retry non autorizzati e pulizia.
- [ ] **R03 — Traccia completa e correlata** (RF-05/RF-10, RNF-06). ID opachi lungo A2A/MCP; nome tool, categorie parametri ed esiti; tempi di estrazione, pianificazione, policy, invio/diniego, controllo, report e pulizia anche sui guasti. Separare richieste applicative da messaggi protocollo e non sommare tempi annidati. Nessun corpo sensibile nei log o negli errori.
- [ ] **R04 — Sostituzione e configurazione** (RNF-05, V-06). Sostituire agente e tool equivalenti cambiando configurazione autorizzata senza modificare il trattamento locale dei PDF. Configurare provider/modello mantenendo invariato il confine dei dati; verificare contratti e Card attesi.
- [ ] **R05 — Copertura dell'ingresso** (RF-01/RF-02, V-03). Aggiungere fixture reali di PDF solo immagini, cifrati/protetti e corrotti; controllare esclusione e prosecuzione con altri file sufficienti. Concordare ampliamento ad altri layout PDF nativi: il parser resta specifico del template e non può essere descritto come generale. OCR escluso dal perimetro della prima versione.
- [ ] **R06 — Affidabilità del report** (RF-08/RNF-07). Dopo P02–P04 riportare ipotesi, inferenze/calcoli e conflitti oltre alle evidenze. Verificare errore di verifica di fonte con conservazione delle altre attività utilizzabili: oggi un errore inatteso di composizione può interrompere tutto il report, pur pulendo la sessione.

## Priorità 4 — Valutazione e riproducibilità

- [ ] **E01 — Ruolo effettivo dei modelli e baseline** (RQ1/RQ3, sezione 4.6). Concordare un compito utile e valutabile per gli agenti: oggi i tool sono scelti dal codice e la prosa LLM è esclusa dal report. Non attribuire ai modelli la qualità della sintesi deterministica. Definire singolo agente equivalente prima di misurare vantaggi della specializzazione.
- [ ] **E02 — Quattro configurazioni confrontabili** (sezione 4.6). Realizzare S+P, M+P, S−P e M−P; mantenere gateway, instradamento, isolamento, schemi e timeout. Senza minimizzazione solo documenti sintetici, inferenza locale e connettori locali/simulati; stesse condizioni anche nei corrispondenti casi con policy. Non sostituire la baseline con l'endpoint diretto del solo agente mercati.
- [ ] **E03 — Annotazioni e rubriche** (RNF-08, V-07). Annotare fatti necessari per attività e granularità, risultati attesi, qualità del report e limiti. Completare provenienza pagina/porzione senza usare ground truth come ingresso. Aggiungere generalizzazione eccessiva che faccia fallire l'utilità pur senza divulgare dati.
- [ ] **E04 — Congelare il protocollo dopo il pilota** (sezione 3.5). Fissare soglie/tolleranze, budget, versioni, digest modelli e PDF, prompt, strumenti e risposte delle fonti; registrare seed se disponibili. Identificare stato effettivo del codice, non solo commit con working tree dirty. Completarne registrazione nei runner.
- [ ] **E05 — Campagna V-01–V-10** (sezioni 3.5/4.6). Dieci sessioni indipendenti per caso e configurazione; media e varianza campionaria per misure quantitative, conteggi/tassi per esiti binari. Zero violazioni come requisito assoluto. I piloti a tre ripetizioni già raccolti non sostituiscono questa campagna.
- [ ] **E06 — Analisi dei risultati** (RQ1–RQ3). Utilità residua, qualità umana del report, dati trasmessi e rimasti locali, latenza/token/costi per fase, completamento e robustezza. Distinguere tariffe stimate da spese osservate; prove locali non hanno costi API sostenuti. Non dedurre accelerazione dal solo parallelismo dei rami.
- [ ] **E07 — Consegna riproducibile**. Verificare setup su Windows, pacchetto/dipendenze su ambiente pulito e procedure del README. Conservare evidenze revisionate senza dati sensibili; mantenere avvisi di libreria monitorati e valutare migrazione TestClient/httpx.

## Scrittura della tesi

- [ ] **T01 — Capitolo 5**. Descrivere implementazione effettiva, contratti, ciclo di vita, versioni, parser, dati e scelte deterministiche/agentiche. Riassumere il diario per decisioni rilevanti, senza trascrivere ogni comando o step. Esplicitare le riduzioni del perimetro rispetto al progetto.
- [ ] **T02 — Capitolo 6**. Presentare risultati della campagna, risposta alle tre RQ, compromessi, limiti e sviluppi futuri. Usare i piloti come verifiche preliminari, non come confronto completo.

## Estensioni da concordare, separate dal confronto principale

- [ ] **X01 — Fonti reali istituzionali e di mercato**. Dopo S01–S03, scegliere fonti e verificare autorevolezza, data/versione, ambito e collegamento tra affermazione e passo citato. Un digest non dimostra la verità o validità normativa. Prove remote separate dal 2×2, con policy attiva e soli dati sintetici.

OCR, agenti su host remoti, database dei profili e operazioni bancarie non sono attività obbligatorie della prima versione. Non aggiungerle alla lista come requisiti impliciti.
