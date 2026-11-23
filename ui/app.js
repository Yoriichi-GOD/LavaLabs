/* LavaLabs integration. SI-assisted code; scientific sources retain their identities. */
(() => {
 'use strict';
 const $=id=>document.getElementById(id);
 const node=(tag,text,cls)=>{const element=document.createElement(tag);if(text!==undefined)element.textContent=text;if(cls)element.className=cls;return element;};
 const number=(value,digits=2)=>typeof value==='number'&&Number.isFinite(value)?value.toLocaleString('en-GB',{minimumFractionDigits:digits,maximumFractionDigits:digits}):'Unavailable';
 let selectedCase='nepal',caseData=null,field='elevation',mapMode=false,selection=0,library,drawVersion=0,plotQueue=Promise.resolve();
 async function get(url){const response=await fetch(url,{cache:'no-store'});let data;try{data=await response.json();}catch{throw Error('The local service returned an unreadable result.');}if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'The evidence could not be loaded.');return data;}
 const measure=()=>{document.documentElement.style.setProperty('--sq-header-h',document.querySelector('body>header').getBoundingClientRect().height+'px');document.documentElement.style.setProperty('--sq-scroll-footer-h',document.querySelector('body>footer').getBoundingClientRect().height+'px');};
 new ResizeObserver(measure).observe(document.querySelector('body>header'));new ResizeObserver(measure).observe(document.querySelector('body>footer'));measure();
 document.fonts.ready.then(measure);

 function show(name){
  $('lab').hidden=name!=='cases';$('evaluation').hidden=name!=='evidence';
  const earth=$('earth');if(earth&&name!=='terrain')earth.hidden=true;
  document.querySelector('main>.intro').hidden=false;
  $('lab-tab').classList.toggle('active',name==='cases');$('eval-tab').classList.toggle('active',name==='evidence');
  $('earth-tab')?.classList.toggle('active',name==='terrain');
  $('page-title').textContent=name==='terrain'?'Terrain & flood':name==='evidence'?'Research evidence':'Case studies';
  $('page-description').textContent=name==='terrain'?'Inspect terrain, analyze a flood area, and review response priorities.':name==='evidence'?'Atmospheric prediction, NDVI, terrain and drainage—with their measured controls and limits.':'Four measured windows. Source observations, terrain and uncertainty together.';
  if(name==='cases'){if(!caseData)loadCase(selectedCase);else requestAnimationFrame(drawCase);}
  if(name==='evidence')loadResearch();
  document.dispatchEvent(new CustomEvent('lavalabs:workspace',{detail:name}));
 }
 window.Lava={show};
 // Keep the inherited optical-context extension's small public contract while
 // the previous application's model workspace remains outside this product.
 window.SQNoir={last:null,context(run,scene,view){this.last=[run,scene,view];if(run)$('footer-context').textContent=`${run.name||'Nepal'} · Retained SAR / optical · ${scene?'Historical DSM':'Terrain not selected'}`;},execution(){}};
 $('lab-tab').addEventListener('click',()=>{show('cases');queueMicrotask(()=>history.replaceState(null,'','#cases'));});
 $('eval-tab').addEventListener('click',()=>{show('evidence');queueMicrotask(()=>history.replaceState(null,'','#evidence'));});
 if(!['#cases','#evidence','#terrain','#flood','#investigate'].includes(location.hash))history.replaceState(null,'','#terrain');
 if(location.hash==='#cases')show('cases');else if(location.hash==='#evidence')show('evidence');
 document.addEventListener('DOMContentLoaded',()=>{
  const tab=$('earth-tab');if(tab){document.querySelector('header nav').prepend(tab);tab.addEventListener('click',()=>show('terrain'));}
  // A link from a source view can reopen the complete Nepal workspace without a reload.
  document.querySelectorAll('a[href="/LavaLabs/#terrain"]').forEach(link=>link.addEventListener('click',event=>{event.preventDefault();$('earth-tab')?.click();}));
  measure();
 });

 async function plotly(){
  if(window.Plotly)return;
  if(!library)library=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='/LavaLabs/jai/assets/vendor/plotly-4.1.1.min.js';script.onload=resolve;script.onerror=()=>{library=null;reject(Error('3D could not load. The measured map remains available.'));};document.head.append(script);});
  await library;
 }
 function keyValue(label,value){const row=node('div');row.append(node('dt',label),node('dd',value));return row;}
 function renderDetails(){
  const data=caseData,layer=data.fields[field],statistics=layer.native_stats||layer.display_grid_stats;
  $('case-title').textContent=data.name;$('case-unit').textContent=layer.unit;
  $('case-meta').textContent=`${data.event?'Event context '+data.event:'Land-cover context '+data.study_period.filter(Boolean).join('–')} · ${data.terrain_product_label} · ${data.crs}`;
  $('case-display-note').textContent=`${layer.display_mapping}. DSM grid ${data.grid.shape[1]} × ${data.grid.shape[0]}; ${data.display_step===1?'the full frozen grid is shown':`every ${data.display_step}th grid sample is shown`}. Unknown cells remain blank.`;
  $('case-interpretation').textContent=field.startsWith('ndvi')?'Vegetation-index observations can flag areas for review. The optical layer is mapped onto historical terrain for inspection; this does not establish vegetation damage, hydraulic change or physical co-registration.':field==='hand'?'Height above the modeled drainage network gives topographic context. It is not observed water depth or a flood simulation.':'This is a measured surface-model derivative. Buildings and vegetation may affect the DSM; surveyed bare-earth DTM and physical flow remain separate evidence requirements.';
  const stats=$('case-statistics');stats.replaceChildren(keyValue('Selected layer',layer.label),keyValue('Median on supported cells',number(statistics.median)+' '+layer.unit),keyValue('10th–90th percentile',number(statistics.p10)+' to '+number(statistics.p90)),keyValue('Supported cells',number(statistics.n,0)),keyValue('Statistics population',layer.native_stats?'native source grid':'common mapped grid'),keyValue('Source sampling',number(layer.native_resolution_m,0)+' m'));
  const observations=$('case-observations');observations.replaceChildren();
  for(const observation of data.observations){const row=node('div',undefined,'observation-row');row.append(node('strong',observation.date),node('span',`${number(observation.clear_fraction*100,1)}% clear on this observation's declared grid · ${number(Math.abs(observation.native_grid.cell_size_m[0]),0)} m source sampling`));observations.append(row);}
  const limits=$('case-limits');limits.replaceChildren(...data.limitations.map(text=>node('li',text)));
  if(data.case_id==='kedarnath')limits.prepend(node('li','Only a small common clear subset is observable. Blank areas do not mean no change.'));
  const sources=$('case-sources');sources.replaceChildren();
  for(const source of data.sources){const row=node('div',undefined,'source-item');row.append(node('span',source.file||source.filename||source.role||'Retained source'));if(source.sha256)row.append(node('code',source.sha256));sources.append(row);}
  $('case-download').href=`/LavaLabs/api/lava/cases/${selectedCase}/view`;$('case-download').download=`lavalabs-${selectedCase}-${field}.json`;
  $('case-panels').href=`/LavaLabs/api/research/cases/${selectedCase}/panels.png`;$('case-summary').href=`/LavaLabs/api/research/cases/${selectedCase}`;$('case-summary').download=`lavalabs-${selectedCase}-summary.json`;
  document.querySelectorAll('[data-case]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.case===selectedCase)));
  $('footer-context').textContent=`${data.name} · ${layer.label} · Source-linked retained inputs`;
 }
 function canvasMap(){
  const layer=caseData.fields[field],values=layer.values,canvas=$('case-map'),rows=values.length,columns=values[0].length;
  canvas.width=columns;canvas.height=rows;const context=canvas.getContext('2d'),image=context.createImageData(columns,rows);
  const finite=values.flat().filter(Number.isFinite),low=field.startsWith('ndvi')?-1:Math.min(...finite),high=field.startsWith('ndvi')?1:Math.max(...finite);
  for(let row=0;row<rows;row++)for(let column=0;column<columns;column++){
   const value=values[row][column],index=(row*columns+column)*4;
   if(value==null){image.data.set([35,38,41,255],index);continue;}
   const amount=Math.max(0,Math.min(1,(value-low)/(high-low||1)));
   const color=field.startsWith('ndvi')?[Math.round(184-137*amount),Math.round(125+66*amount),Math.round(92+42*amount)]:[Math.round(55+177*amount),Math.round(65+160*amount),Math.round(74+133*amount)];
   image.data.set([...color,255],index);
  }
  context.putImageData(image,0,0);
 }
 async function drawCase(){
  if(!caseData)return;const token=selection,renderVersion=++drawVersion;renderDetails();
  $('case-plot').hidden=mapMode;$('case-map').hidden=!mapMode;$('case-mode').textContent=mapMode?'View in 3D':'View as map';$('case-mode').setAttribute('aria-pressed',String(mapMode));$('case-reset').disabled=mapMode;
  if(mapMode){canvasMap();return;}
  try{
   await plotly();if(token!==selection||renderVersion!==drawVersion||$('lab').hidden)return;
   const data=caseData,layer=data.fields[field],isIndex=field.startsWith('ndvi');
   const z=data.elevation.map((row,r)=>row.map((value,c)=>layer.values[r][c]==null?null:value));
   const colors=isIndex?[[0,'#a96f56'],[.5,'#d4d6cd'],[1,'#53897a']]:[[0,'#293640'],[.45,'#879594'],[1,'#d7cbb4']];
   const trace={type:'surface',x:data.x,y:data.y,z,surfacecolor:layer.values,colorscale:colors,colorbar:{title:{text:layer.unit,font:{size:11}},thickness:9,len:.72,tickfont:{size:11}},hovertemplate:'Easting %{x:.0f} m<br>Northing %{y:.0f} m<br>Elevation %{z:.1f} m<br>Layer %{surfacecolor:.3f}<extra></extra>',connectgaps:false};
   if(isIndex){trace.cmin=-1;trace.cmax=1;}
   plotQueue=plotQueue.catch(()=>{}).then(()=>{if(token!==selection||renderVersion!==drawVersion)return;return Plotly.react($('case-plot'),[trace],{autosize:true,paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',margin:{l:5,r:42,t:10,b:10},font:{family:'Geist',color:'#bac0c4',size:11},scene:{bgcolor:'rgba(0,0,0,0)',xaxis:{title:{text:'Easting m'},gridcolor:'#292e32',showspikes:false},yaxis:{title:{text:'Northing m'},gridcolor:'#292e32',showspikes:false},zaxis:{title:{text:'DSM m'},gridcolor:'#292e32',showspikes:false},aspectmode:'data',camera:{eye:{x:1.35,y:1.35,z:1.05}}},uirevision:selectedCase},{displayModeBar:false,responsive:true,scrollZoom:true});});await plotQueue;
   $('case-message').textContent='';
  }catch(error){if(token!==selection)return;mapMode=true;$('case-message').textContent=error.message;drawCase();}
 }
 async function loadCase(id){
  const token=++selection;selectedCase=id;$('case-select').value=id;$('case-message').textContent='Reading retained terrain and optical evidence…';$('case-field').disabled=true;$('case-mode').disabled=true;
  try{
   const data=await get(`/LavaLabs/api/lava/cases/${id}/view`);if(token!==selection)return;caseData=data;
   $('case-field').replaceChildren(...Object.entries(data.fields).map(([key,value])=>{const option=node('option',value.label);option.value=key;return option;}));
   if(!data.fields[field])field='elevation';$('case-field').value=field;await drawCase();
  }catch(error){if(token===selection)$('case-message').textContent=error.message;}
  finally{if(token===selection){$('case-field').disabled=false;$('case-mode').disabled=false;}}
 }
 $('case-select').onchange=event=>loadCase(event.target.value);$('case-field').onchange=event=>{field=event.target.value;drawCase();};
 $('case-mode').onclick=()=>{mapMode=!mapMode;drawCase();};$('case-reset').onclick=()=>{if(window.Plotly)Plotly.relayout($('case-plot'),{'scene.camera':{eye:{x:1.35,y:1.35,z:1.05}}});};
 document.querySelectorAll('[data-case]').forEach(button=>button.onclick=()=>loadCase(button.dataset.case));
 new ResizeObserver(()=>{if(window.Plotly&&caseData&&!$('lab').hidden&&!mapMode)Plotly.Plots.resize($('case-plot'));}).observe($('case-plot'));
 let researchLoaded=false;
 async function loadResearch(){
  if(researchLoaded)return;
  try{const data=await get('/LavaLabs/api/lava/research'),list=$('research-list');list.replaceChildren();for(const item of data.studies){const row=node('article',undefined,'research-row');row.setAttribute('role','listitem');const heading=node('div');heading.append(node('h2',item.title),node('p',item.scope,'scope'));const finding=node('div');finding.append(node('p',item.finding),node('p',item.limit,'result-limit'));const link=node('a','Original report ↗');link.href=item.report+(document.documentElement.hasAttribute('data-hosted')?'.md':'');link.setAttribute('download','');row.append(heading,finding,link);list.append(row);}researchLoaded=true;}catch(error){$('research-list').replaceChildren(node('p',error.message));}
 }
 get('/LavaLabs/api/lava/status').then(data=>{$('lava-status').textContent=document.documentElement.hasAttribute('data-hosted')?'Public demo · Saved observations':data.flood.available?'Local evidence ready':'Saved evidence · flood service unavailable';}).catch(()=>{$('lava-status').textContent='Evidence unavailable';});
})();
