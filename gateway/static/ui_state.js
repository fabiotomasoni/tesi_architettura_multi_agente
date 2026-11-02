// Solo metadati osservati: nessuna percentuale o conclusione finanziaria calcolata.
export const labels = Object.freeze({ready:'Dati pronti',blocked:'Non eseguibile',requested:'In attesa',running:'In corso',completed:'Completata',partial:'Parziale',failed:'Non completata',unverified:'Non verificata',cancelled:'Annullata'});
export const reasons = Object.freeze({input_not_ready:'Dati obbligatori mancanti o non validati.',invalid_view:'La vista disponibile non contiene i dati necessari.',timeout:'Tempo massimo superato.',missing_provenance:'Provenienza obbligatoria assente: risultato escluso.',not_authorized:'Richiesta rifiutata dal gateway.',delegation_failed:'Comunicazione con lo specialista non completata.',execution_failed:'Attività non completata: controllare i servizi locali.'});
export const stageDefinitions = Object.freeze([
  {label:'Preparazione',phases:['prepare_task']},
  {label:'Specialista',phases:['delegate','a2a_card','a2a_message']},
  {label:'Strumenti e fonti',phases:['tool_authorization','source_proxy']},
  {label:'Modello',phases:['model_proxy']},
  {label:'Verifica risultato',phases:['verify_result']}
]);
export function stageState(spans,phases) {
  const rows=spans.filter(s=>phases.includes(s.phase));
  if(!rows.length)return 'waiting';
  // Due consultazioni possono avvenire in successione: un nuovo span aperto
  // prevale su uno precedente terminato, senza anticipare le fasi successive.
  if(rows.some(s=>s.duration_ms===null))return 'running';
  if(rows.some(s=>['failed','blocked','unverified','cancelled'].includes(s.outcome)))return 'problem';
  return rows.some(s=>typeof s.duration_ms==='number'&&s.duration_ms>=0&&s.outcome==='completed')?'observed':'waiting';
}
export function progressFor(trace,scenario) {
  const spans=(trace.spans||[]).filter(s=>s.scenario===scenario || s.scenario==='BATCH'&&['a2a_card','a2a_message'].includes(s.phase));
  return stageDefinitions.map(stage=>({...stage,state:stageState(spans,stage.phases)}));
}
export function severity(status){return ['failed','blocked','unverified'].includes(status)?'error':status==='partial'?'warning':status==='completed'?'success':'info';}
export function uploadMessage(data) {
  const sections=Object.values(data.scenarios||{}),ready=sections.filter(s=>s.ready).length;
  return ready===sections.length?'Controlli automatici completati. Puoi avviare l’analisi.':ready?'Alcuni approfondimenti non sono eseguibili. Puoi ottenere un report parziale.':'Nessun approfondimento richiesto dispone di tutti i dati necessari. Il report spiegherà i limiti.';
}
export function finalMessage(data) {
  const status=data.report?.status||data.status;
  const summary=status==='completed'?'Attività concluse. Leggi risultati, ipotesi e limiti nel documento.':status==='partial'?'Report parziale disponibile: conserva i risultati utilizzabili e indica le attività non completate.':status==='unverified'?'Risultati esterni non verificati. Il documento distingue i dati locali dai contenuti esclusi.':'Analisi non completata per tutti gli approfondimenti. Il documento riporta dati disponibili e motivi.';
  return summary+(data.session_closed?' Sessione sul gateway chiusa.':'');
}
