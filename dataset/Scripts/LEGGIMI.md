# Generatore dataset tesi

25 fascicoli indipendenti, 4 documenti ciascuno: esattamente 100 PDF nativi italiani. Cinque gruppi bilanciati di casi: completi, capitale mancante, interessi mancanti, tasso ambiguo, periodi differenti. Tutte le identità sono fittizie; CF e IBAN sono deliberatamente non operativi e non costituiscono un benchmark completo di validazione formale delle PII.

## Avvio
Apri il terminale nella cartella Scripts, quindi:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Inserisci la chiave in `.env` dopo OPENAI_API_KEY=, poi:

```sh
python genera_dataset.py
```

Prima prova facoltativa senza API: `python genera_dataset.py --offline` (scrive Preview_offline, non Documents). `--cases 1` prova un fascicolo; rilancia senza opzioni per completare tutti i 25 riutilizzando le descrizioni API già salvate.

## Costi e ripresa
Il limite è 8,50 USD, lasciando margine sui 9 USD disponibili. Non si cerca di spendere tutto il credito: 25 chiamate brevi dovrebbero costare molto meno. Tariffe di riferimento gpt-4.1-mini: 0,40 USD/milione input e 1,60 USD/milione output, verificate il 29 ottobre 2026 nella documentazione ufficiale: https://developers.openai.com/api/docs/models/gpt-4.1-mini . Ricontrollarle prima di esecuzioni future. Il modello può essere soggetto a dismissione: in caso di indisponibilità il programma si ferma senza sostituzioni automatiche.

Ogni chiamata prenota preventivamente un costo prudenziale; anche errori e timeout conservano la prenotazione. Nessun retry automatico. Le risposte valide vengono salvate, le esecuzioni successive le riusano. Non eliminare state/budget.json per aggirare il tetto. Il limite riguarda questo generatore e questo listino, non altri usi della chiave o il saldo totale dell'account. Il contatore non è una fattura: usage e modello effettivo sono conservati per riconciliazione. La chiave non viene stampata né salvata nei risultati.

## Metodo e limiti
Numeri monetari in centesimi, saldo e netto riconciliati; rata calcolata su ammortamento mensile con tasso corrente. Per mutui variabili è una fotografia, non una previsione. Fiscalità e contributi sono simulati e non riproducono una normativa vigente. L'API genera solo descrizioni amministrative, senza numeri o identità, e non riceve documenti reali o la tesi.

`state/ground_truth.json` contiene valori, varianti, esiti attesi, viste consentite e hash dei PDF. È materiale per il valutatore: NON fornirlo all'architettura come input. I valori latenti omessi o ambigui nei documenti non sono evidenze utilizzabili. Le annotazioni sono per fascicolo: la provenienza puntuale pagina/span va verificata nel parser del prototipo. La busta paga e l'estratto conto sono contesto, non sostituiscono i campi obbligatori S-01/S-02.

Questi PDF coprono gli ingressi e la minimizzazione; non dimostrano interoperabilità, robustezza di rete o conformità del sistema. V-04, V-05, V-06, V-08, V-10 e la discordanza agente-documento V-09 richiedono fixture separate di servizi e risultati. Scansioni, cifratura e corruzione non sono incluse nei 100 PDF nativi. Non presentare i 25 fascicoli come le dieci ripetizioni per configurazione previste dalla tesi: quelle sono esecuzioni del prototipo sugli stessi ingressi.

Il file .env è escluso dal versionamento con .gitignore. Se fosse già tracciato in precedenza, .gitignore non lo rimuove dalla cronologia.
