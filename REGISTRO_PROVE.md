# Registro delle prove V-01–V-10

Riferimenti: tesi §3.5, Tabella 3.3 e §§4.4–4.6. Le dieci famiglie sono requisiti della tesi; le varianti sono la loro applicazione al prototipo. Il registro controllabile è [evaluation/test_registry.json](evaluation/test_registry.json). Nessuna campagna finale è stata avviata.

L’autore ha autorizzato **solo S04 locale con dati sintetici** per V02-PAYLOADS, V05-HOSTILE e V10-CARDS: due payload vietati, istruzione nel risultato, metadati tool alterati, tre Card falsificate. Nessuna destinazione Internet di esfiltrazione o estensione implicita del perimetro.

| Famiglia | Procedura predisposta | Cosa deve dimostrare |
|---|---|---|
| V-01 Percorso completo | Corpus di 25 casi; pilota corrente su cinque; controllo PDF/report/traccia. | Dati e fonti distinguibili, risultati documentali fedeli e chiusura della sessione. |
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

Il runtime è `financial-profile-2x2-v6`: due consultazioni MCP e una inferenza per attività completata, uguali fra celle; strumenti 0.5.0 e report 0.16.0. I vecchi piloti non verificano questa versione. Il contatore MCP comprende anche il riferimento comune; le metriche del contenuto finanziario restano misure della vista canonica, non catture dei byte trasmessi.

## Stato della campagna

Restano previste 25 × 4 × 10 = 1.000 esecuzioni di base e dieci ripetizioni di ogni variante aggiuntiva per cella. I dieci cicli e le 29 varianti restano quelli concordati. I controlli prima/dopo non diventano ripetizioni indipendenti né vengono deduplicati arbitrariamente. Totali fisici, manifest e registro cieco saranno fissati prima del congelamento; qualità e utilità della selezione richiedono l’unico valutatore concordato.

La verifica statica `scripts/check_test_registry.py` controlla definizioni, file/digest e collegamenti. Non esegue procedure e non autorizza una campagna. **Pilota tecnico Docker corrente confermato dai file `runs/block2_manual*`: quattro celle positive, venti esecuzioni Ollama e 259 controlli di confronto senza problemi. Congelamento e campagna finale restano pendenti.** Comandi completi nel [protocollo](PROTOCOLLO_VALUTAZIONE.md#verifica-del-secondo-blocco).
