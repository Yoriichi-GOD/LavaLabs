/* SI-assisted LavaLabs aggregate evidence. No competition rows or images. */
(() => {
 'use strict';
 const section=document.getElementById('atmospheric-evidence');
 if(!section)return;
 const $=id=>document.getElementById(id);
 const script=document.currentScript;
 const source=new URL('results.json',script.src).href;
 const labels={table:'Table control',official:'Official image summaries',no_fallback:'No fallback + quality',spatial:'Spatial + quality'};
 const targets=['t_ch4','t_no2','t_co','t_aai','t_firms'];
 const fmt=value=>Number(value).toFixed(5);
 const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 let state='idle',receipt;
 function validate(value){
  if(!value||value.schema!==2||!labels[value.retained_variant])throw Error('The atmospheric receipt has an unsupported version.');
  if(Object.values(value.selection.development_comparison.scores).some(score=>!Number.isFinite(score.mcrmse)))throw Error('The development comparison contains incomplete metrics.');
  for(const score of Object.values(value.confirmation)){
   if(!Number.isFinite(score.mcrmse)||targets.some(t=>!Number.isFinite(score.rmse[t])||!Number.isInteger(score.observed[t])||score.observed[t]<1))throw Error('The atmospheric receipt contains incomplete metrics.');
  }
  if(!value.confirmation[value.retained_variant]||!value.confirmation.table)throw Error('The retained method is missing its confirmation control.');
  return value;
 }
 function target(){
  const t=$('atmo-target').value,selected=receipt.confirmation[receipt.retained_variant],base=receipt.confirmation.table;
  const values=$('atmo-target-values');values.replaceChildren();
  for(const [label,value] of [['Table control RMSE',fmt(base.rmse[t])],['Retained method RMSE',fmt(selected.rmse[t])],['Observed confirmation labels',selected.observed[t].toLocaleString('en-GB')]]){
   const group=node('div');group.append(node('dt',label),node('dd',value));values.append(group);
  }
  $('atmo-target-note').textContent=selected.rmse[t]<base.rmse[t]?'The retained method has lower error for this target on these confirmation sites. This is a diagnostic result, not a calibrated probability.':'The retained method does not improve this target on these confirmation sites. Retention is based on the five-target metric; this weakness remains visible.';
 }
 function render(){
  const chosen=receipt.retained_variant,comparison=receipt.selection.development_comparison.scores;
  $('atmo-verdict').textContent=chosen==='official'?'Retain the satellite and table blend.':chosen==='table'?'Retain the simpler table control.':'Retain the custom variant that passed both controls.';
  const confirm=receipt.confirmation[chosen],base=receipt.confirmation.table;
  $('atmo-conclusion').textContent=`${labels[chosen]}: ${fmt(confirm.mcrmse)} MCRMSE versus ${fmt(base.mcrmse)} for the table control on ${receipt.selection.confirmation_sites} held-out training sites. The confirmation partition is an acceptance gate, so this is not an untouched final-test estimate.`;
  $('atmo-public-score').textContent=Number.isFinite(receipt.image_public_mcrmse)?`Accepted public test score: ${fmt(receipt.image_public_mcrmse)}, compared with ${fmt(receipt.raw_baseline.public_mcrmse)} for the first raw baseline. Private-test performance remains unknown.`:'Public scoring has not been observed for this candidate.';
  const plot=$('atmo-comparison');plot.replaceChildren();
  const max=Math.max(1.05,...Object.values(comparison).map(s=>s.mcrmse))*1.05;
  for(const name of ['table','official','no_fallback','spatial']){
   const row=node('div',undefined,'atmo-row');if(name===chosen)row.classList.add('retained');
   const heading=node('div',undefined,'atmo-row-heading');heading.append(node('span',labels[name]),node('strong',fmt(comparison[name].mcrmse)));
   const track=node('div',undefined,'atmo-track'),bar=node('div',undefined,'atmo-bar');bar.style.width=`${100*comparison[name].mcrmse/max}%`;track.append(bar);track.setAttribute('aria-hidden','true');
   row.append(heading,track);plot.append(row);
  }
  $('atmo-validation-note').textContent=`${receipt.counts.train.toLocaleString('en-GB')} training observations · ${receipt.counts.sites} sites · ${receipt.feature_extraction.chip_count.toLocaleString('en-GB')} supplied chips. Development family selection has selection optimism.`;
  $('atmo-method-copy').textContent=`Fixed regularized HistGradientBoosting; three outer development site folds, three inner site folds for convex mixture selection, and a separate ${receipt.selection.confirmation_sites}-site acceptance partition. Final refit uses five grouped folds for weights. ${receipt.limitations.join(' ')}`;
  if(receipt.sparse_followup){
   const s=receipt.sparse_followup;
   if([s.development_control,s.development_candidate,s.brightness_control,s.shuffled_control,s.stress_control,s.stress_candidate].some(v=>!Number.isFinite(v)))throw Error('The spectral follow-up receipt contains incomplete metrics.');
   const card=node('section',undefined,'atmo-conclusion');card.id='atmo-spectral-followup';
   card.append(node('h3','Sparse spectral features pass the controlled comparison.'));
   card.append(node('p',`FIRMS-only follow-up: ${fmt(s.development_candidate)} MCRMSE versus ${fmt(s.development_control)} for the frozen control on ${s.development_sites} development sites. Wins ${s.fold_wins}/${s.folds} folds; the other four targets are unchanged.`));
   card.append(node('p',`Environmental holdouts: ${fmt(s.stress_candidate)} versus ${fmt(s.stress_control)}. Brightness-only control: ${fmt(s.brightness_control)}; shuffled descriptors: ${fmt(s.shuffled_control)}.`, 'atmo-caption'));
   card.append(node('p',Number.isFinite(s.public_mcrmse)?`Accepted public score: ${fmt(s.public_mcrmse)}. Private-test accuracy is unknown.`:'Public scoring is pending; these are development results.', 'atmo-caption'));
   card.append(node('p',s.limitation,'atmo-caption'));
   $('atmo-content').prepend(card);$('atmo-verdict').textContent='Earlier control and acceptance check';
  }
  target();$('atmo-content').hidden=false;$('atmo-status').textContent='Measured experiment · Aggregate evidence only';
 }
 async function load(){
  if(state!=='idle')return;state='loading';
  try{const response=await fetch(source,{cache:'no-store'});if(!response.ok)throw Error('The atmospheric evidence could not be loaded.');receipt=validate(await response.json());render();state='ready';}
  catch(error){state='error';$('atmo-status').textContent=`${error.message} Reload the page to retry; the other research evidence remains available.`;}
 }
 $('atmo-target').addEventListener('change',()=>{if(state==='ready')target();});
 document.addEventListener('lavalabs:workspace',event=>{if(event.detail==='evidence')load();});
 if(!document.getElementById('evaluation').hidden)load();
})();
