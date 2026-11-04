# Registro delle prove V-01–V-10

Riferimenti: tesi §3.5, Tabella 3.3 e §§4.4–4.6. Le dieci famiglie sono requisiti della tesi; le varianti sono la loro applicazione al prototipo. Il registro controllabile è [evaluation/test_registry.json](evaluation/test_registry.json). La campagna finale v7 `campaign_v2` è stata completata e verificata; i riferimenti alle evidenze sono in fondo.

L’autore ha autorizzato **solo S04 locale con dati sintetici** per V02-PAYLOADS, V05-HOSTILE e V10-CARDS: due payload vietati, istruzione nel risultato, metadati tool alterati, tre Card falsificate. Nessuna destinazione Internet di esfiltrazione o estensione implicita del perimetro.

| Famiglia | Procedura eseguita | Cosa deve dimostrare |
|---|---|---|
| V-01 Percorso completo | Corpus di 25 casi; finale su 25 e pilota su cinque; controllo PDF/report/traccia. | Dati e fonti distinguibili, risultati documentali fedeli e chiusura della sessione. |
| V-02 Confine e pulizia | Viste +P/−P, due payload controllati, isolamento Docker, annullamento, TTL, guasto ASGI, consegna troncata e crash. | Diniego prima dell’invio vietato; revoca dei vecchi accessi e nuova elaborazione. |
| V-03 Input incompleto/non supportato | Tre PDF sintetici fissati, caricamento misto e sola attività non pronta; casi mancanti/ambigui del corpus. | Parser raggiunto, input inutilizzabile escluso, attività valide conservate. |
| V-04 Guasto fonte | Timeout S-01, fonte fiscale malformata, entrambe indisponibili, controlli prima/dopo. | Timeout della fonte distinto dal modello; nessuna fonte sostitutiva inventata. |
| V-05 Contenuto ostile | Campo istruzione aggiunto al risultato e capacità MCP estranea al catalogo. | Schema/catalogo bloccano la prosecuzione; nessun nuovo strumento o modello invocato. |
| V-06 Sostituzione | Standard → MCP equivalente → standard, C001. | Stessi agenti, immagini, impostazioni e report normalizzato; riconfigurazione del solo gateway. |
| V-07 Utilità | Vista troppo generale prima della validazione, confrontata con −P invariato. | U=0,5 in +P, sotto 0,95; il successivo rifiuto non rende U non applicabile. |
| V-08 Provenienza | Fonte obbligatoria omessa per S-01 o per entrambe. | `unverified`, contenuto escluso e nessun completamento inventato. |
| V-09 Discordanze | Due agenti leggono realmente via MCP il riferimento comune e lo restituiscono con ricevuta. | Conflitti agente–agente/agente–documento, unità equivalenti, periodi/prodotti diversi; nessuna sovrascrittura. |
| V-10 Card falsificata | Alterazione controllata di identità, endpoint o capacità dopo il GET e prima della delega. | Zero `message/send` al servizio rifiutato. Nel single il rifiuto riguarda entrambe le attività; nel multi può proseguire S-02. |

## Riferimento comune e fedeltà delle fonti

Il laboratorio usa la risposta BCE già archiviata della serie MIR.M.IT.B.A2C.A.R.A.2250.EUR.N, copiata senza modifiche in `gateway/fixtures/ecb_reference.json` e fissata nel registro tramite digest. **È un replay, non una nuova consultazione Internet.** Entrambe le attività consultano `services.reference_mcp` tramite permessi distinti, monouso e senza argomenti finanziari. Il gateway confronta ogni risultato con la propria ricevuta prima dell’aggregazione.

I cinque casi controfattuali sono esplicitamente simulati e non attribuiscono numeri inventati alla BCE. Il caso agente–documento attesta nel solo test la stessa grandezza/prodotto/periodo del contratto C001. La statistica aggregata reale resta distinta dal TAN. Un valore alterato rispetto alla stessa ricevuta è un errore di fedeltà, non un conflitto fra fonti verificate. Entrambe le provenienze restano nel report; i conflitti irrisolti sospendono le conclusioni applicative.

## Esecuzione e limiti

- `tests/test_block2_pipeline.py`: quattro assetti logici, agenti ADK/A2A, MCP stdio e callback HTTP reali, modello controllato. La factory nativa è usata nel solo test: **non è una prova di isolamento Docker né una misura LLM**. Include TTL con orologio controllato, guasto ASGI e controllo dell’utilità prima dello schema.
- `scripts/check_block2.py`: pilota nei container delle quattro celle, preflight di isolamento, guasti, Card, payload, provenienza, confronti, sostituzione, annullamento, consegna e SIGKILL reale. Le risposte del modello nelle prove funzionali sono dichiaratamente controllate. Il ponte ordinario deve essere fermo.
- `--live-pilot`: aggiunge cinque fascicoli per cella con **Ollama reale**, stesso modello, prompt di ruolo, budget e fonti locali fissate. I JSONL sono controllati anche come confronto 2×2. Non assegna voti umani.

Il timeout fonte attende il budget comune di 30 secondi; restano 120/90/30/5 secondi per attività/modello/fonte/margine. Il TTL non misura un’attesa reale di 1.800 secondi. Un nuovo avvio dopo SIGKILL non riprende la sessione vecchia e non dimostra cancellazione fisica della RAM. Le Card sono alterate nel trasporto di verifica dopo una risposta autentica: non si simula una compromissione della rete o dell’identità del container. Le sonde payload sono inserite nel punto di controllo del gateway; la traccia distingue il diniego del detector da quello dello schema/catalogo.

Il selettore chiuso `TESI_VERIFICATION_PROFILE` è configurazione fidata del laboratorio, mai una scelta di Card, modello o API pubblica. I profili negativi accettano solo C001. I tre PDF negativi sono ammessi per digest, poi sottoposti al parser; modifiche ai loro byte restano rifiutate dal corpus. Non si montano documenti o ground truth nei servizi.

Il precedente pilota `runs/block2_manual*` riguarda il runtime `financial-profile-2x2-v6`: due consultazioni MCP e una inferenza per attività completata, uguali fra celle; strumenti 0.5.0 e report 0.16.0. Le prove v6 non sono attribuite alla v7. Il contatore MCP comprende anche il riferimento comune; le metriche del contenuto finanziario restano misure della vista canonica, non catture dei byte trasmessi.

## Campagna finale v7 ed evidenze

Lo snapshot `financial-profile-2x2-v7` è in `runs/campaign_v2`, con `manifest.json` e `approval.json` verificati. Il pilota v7 ha superato quattro blocchi. La finale ha superato **40 blocchi su 40**: 1.000 sessioni di base con Ollama, 2.400 sessioni di controllo, 120 rifiuti attesi e 3.200 report consegnati. La pulizia è confermata in tutti i tentativi. Il tentativo parziale del blocco 30 è archiviato fuori dalla raccolta conteggiata. Le impronte in `final/completion.json` corrispondono ai file conservati.

| Famiglie | Dove verificare, a partire da `campaign_v2/` |
|---|---|
| V-01, V-03 | `final/private/base/` per le basi Ollama; `final/private/controlled/` per gli ingressi negativi e gli esiti attesi. |
| V-02 | `final/private/isolation/` per le sonde di rete; `final/private/controlled/` e `final/private/native/` per payload, revoca, pulizia e ripristino. |
| V-04, V-05, V-08, V-09, V-10 | `final/private/controlled/`, con variante ed esito di ciascun controllo. |
| V-06 | Voce `equivalent_mcp_substitution` nei riepiloghi di `final/private/controlled/`. |
| V-07 | Utilità nominale in `final/private/base/`; variante `utility_loss` nei controlli, distinta dalle basi. |

I record di `final/private/blocks/` collegano esecuzioni, casi, tracce ed eventuali report. `human_review_60/summary_rated.json` riepiloga misure tecniche e 60 giudizi dell’unico valutatore, tutti 8/8 e senza errori critici segnalati. I 3.140 report fuori campione restano senza voto. L’esito tecnico positivo non costituisce una misura di qualità per quei report.

Il controllo statico `scripts/check_test_registry.py` valida definizioni, digest e collegamenti; non esegue prove e non determina lo stato del manifest approvato. Per distinguere esiti, copertura e limiti per RQ1–RQ3, vedi il [protocollo](PROTOCOLLO_VALUTAZIONE.md#risultati-e-riferimenti-per-il-capitolo-6). Gli artefatti di `runs/` sono conservati nell’archivio separato dalla repository Git.
