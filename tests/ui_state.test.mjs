// Verifiche del solo stato UI; nessuna inferenza, rete o dipendenza da installare.
import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import {test} from 'node:test';
const path=new URL('../gateway/static/ui_state.js',import.meta.url);
const {stageState,progressFor,severity,uploadMessage,finalMessage}=await import('data:text/javascript;base64,'+readFileSync(path).toString('base64'));
test('Nessuna fase inventata con metadati assenti o malformati',()=>{
 assert.equal(stageState([],['model_proxy']),'waiting');
 assert.equal(stageState([{phase:'model_proxy',outcome:'completed'}],['model_proxy']),'waiting');
 assert.equal(stageState([{phase:'model_proxy',duration_ms:1,outcome:'completed'}],['model_proxy']),'observed');
 assert.equal(stageState([{phase:'model_proxy',duration_ms:null,outcome:'running'}],['model_proxy']),'running');
 assert.equal(stageState([{phase:'model_proxy',duration_ms:1,outcome:'failed'}],['model_proxy']),'problem');
});
test('Una nuova consultazione aperta prevale sulla precedente conclusa',()=>{
 assert.equal(stageState([{phase:'source_proxy',duration_ms:1,outcome:'completed'},{phase:'source_proxy',duration_ms:null}],['source_proxy']),'running');
});
test('Generalista condiviso: nessuna inferenza fiscale attribuita ai mercati',()=>{
 const spans=[{scenario:'BATCH',phase:'a2a_message',duration_ms:1,outcome:'completed'},{scenario:'BATCH',phase:'model_proxy',duration_ms:null},{scenario:'S-02',phase:'model_proxy',duration_ms:null}];
 assert.equal(progressFor({spans},'S-01')[1].state,'observed');
 assert.equal(progressFor({spans},'S-01')[3].state,'waiting');
 assert.equal(progressFor({spans},'S-02')[3].state,'running');
});
test('Parziali, blocchi e non verificati hanno messaggi distinti',()=>{
 assert.equal(severity('partial'),'warning');assert.equal(severity('blocked'),'error');assert.equal(severity('unverified'),'error');
 assert.match(uploadMessage({scenarios:{a:{ready:true},b:{ready:false}}}),/parziale/);
 assert.match(finalMessage({status:'partial',session_closed:true}),/parziale.*Sessione sul gateway chiusa/);
 assert.match(finalMessage({status:'unverified'}),/non verificati/);
});
