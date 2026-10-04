import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {zipSync,strToU8} from 'fflate';
import {applyGlobal, GLOBAL_GROUPS, GLOBAL_RANGES} from './linked-controls.js';
const $=id=>document.getElementById(id);
const {defaults:DEFAULTS,presets:PRESETS}=JSON.parse($('case-config').textContent);
const reference=JSON.parse($('source-data').textContent);
const zipReference=JSON.parse($('zip-source-data').textContent);
const screenStyleNames={plain:'Current window',beveled:'ZIP beveled window'};
const buttonStyleNames={flexure:'Current flexing tabs',strip:'ZIP rounded button strip'};
const closureNames={snap:'Snap-fit',friction:'Slip-fit',screw:'Screw-fastened'};
let state={...DEFAULTS}, source='design', requestedRev=0,lastBuiltRev=-1,inFlight=false,timer,valid=false,firstBuild=true;
let lastParts={},lastWarnings=[],lastBuildMs=0,bodyColor='#b6c7d0';
let lastGoodState=null,lastGoodPreset='Original footprint',linkedRollback=null;
let dimensionFeedback=null,lastEditedFields=[];
const pendingExports=new Map();let exportId=0;
const STORAGE_KEY='oled-case-workshop-v2';
let level='easy', startingPreset='Original footprint', baseline={...DEFAULTS};
const levels={easy:0,intermediate:1,expert:2};
const easyKeys=new Set(['closure','screenStyle','buttonStyle','bezelOn']);
const expertKeys=new Set(['screenX','screenY','buttonX','buttonY','buttonPitch','buttonGap','pcbMounts','fit','lip','tabWidth','tabThickness','hook','rearOpeningX','rearOpeningY']);
const levelDescriptions={easy:'Two linked sliders and a few style choices. Open Intermediate for individual part sizes.',intermediate:'Size each part, adjust mounting screws, and inspect the back opening. Expert adds offsets and fit details.',expert:'All dimensions, offsets, clearances and catch geometry. Small changes can affect the fit.'};
function selectBaseline(name){const preset=PRESETS.find(p=>p.name===name)||PRESETS[0];startingPreset=preset.name;baseline={...DEFAULTS,...preset.values};}
try{const stored=localStorage.getItem('oled-case-workshop-level');if(Object.hasOwn(levels,stored))level=stored}catch{}
function readSettings(data){
 if(![1,2].includes(data?.schema)||!data.parameters||typeof data.parameters!=='object'||Array.isArray(data.parameters))throw Error('Choose an OLED Case Workshop settings file.');
 const parameters={...DEFAULTS};
 for(const [key,value] of Object.entries(data.parameters)){
  if(data.schema===1&&['cableWidth','cableHeight'].includes(key))continue;
  if(!Object.hasOwn(DEFAULTS,key))throw Error('Unrecognized setting: '+key);
  if(typeof DEFAULTS[key]!==typeof value||(typeof value==='number'&&!Number.isFinite(value)))throw Error('Invalid value for '+key);
  parameters[key]=value;
 }
 return parameters;
}
try{const saved=JSON.parse(localStorage.getItem(STORAGE_KEY)||localStorage.getItem('oled-case-workshop-v1'));if(saved){state=readSettings(saved);selectBaseline(saved.startingPreset);}}catch{}
const groups=[
 ['Body',true,[['width','Body width',46,90,.1],['height','Body height',30,65,.01],['depth','Shell depth',4,20,.1],['wall','Wall thickness',1.2,4,.1],['face','Front thickness',1,3.5,.1],['corner','Body corner radius',.5,10,.1],['edge','Body edge rounding',0,1.5,.05]]],
 ['PCB mounting screws',true,[['pcbMounts','PCB mounting posts','bool'],['pcbPostDiameter','Standoff outside diameter',3,8,.1],['pcbHoleDiameter','Screw-hole diameter',.8,4,.05]]],
 ['Window & button style',true,[['screenStyle','Screen opening style','screenStyle'],['buttonStyle','Button style','buttonStyle'],['screenChamfer','Window bevel depth',.2,2,.1],['buttonProtrusion','Button protrusion',.3,2,.1]]],
 ['Screen & buttons',false,[['screenW','Screen opening width',18,34,.01],['screenH','Screen opening height',10,23,.1],['screenX','Screen horizontal offset',-12,4,.01],['screenY','Screen vertical offset',-6,7,.01],['screenRadius','Window corner radius',0,3,.1],['buttonW','Button / opening width',5,10,.1],['buttonH','Button / opening height',2.5,5.5,.1],['buttonPitch','Button spacing',4.5,7,.05],['buttonX','Button column offset',10,23,.1],['buttonY','Top button offset',5,15,.1],['buttonGap','Button clearance gap',.25,1,.05],['buttonRadius','Button corner rounding',0,2,.05]]],
 ['Bezels',false,[['bezelOn','Separate outer bezel','bool'],['bezelWidth','Outer bezel width',1,5,.1],['bezelHeight','Front rim height',.8,6,.1],['bezelRadius','Outer corner radius',1,12,.1],['screenBezel','Screen bezel width',0,2,.1],['screenRaise','Screen bezel height',0,2,.1]]],
 ['Back cover & fit',true,[['closure','Closing mechanism','closure'],['coverDepth','Extra rear depth',4,22,.1],['coverWall','Cover wall / plate',1.2,3.5,.1],['coverEdge','Cover edge rounding',0,1.5,.05],['fit','Clearance per side',.1,.6,.05],['lip','Engagement depth',1,3,.1],['vents','Back ventilation slots','bool']]],
 ['Rear connector opening',true,[['rearOpeningWidth','Opening width',10,40,.1],['rearOpeningHeight','Opening height',3,14,.1],['rearOpeningX','Horizontal offset',-15,15,.1],['rearOpeningY','Vertical offset',-12,12,.1],['rearOpeningRadius','Opening corner radius',0,3,.1]]],
 ['Snap catches',false,[['tabWidth','Catch width',4,10,.1],['tabThickness','Flex arm thickness',.6,1.5,.05],['hook','Hook engagement',.2,.8,.05]]]
];
const labels={};
for(const [title,open,controls] of groups){
 const section=document.createElement('details');section.open=open;section.dataset.group=title;
 if(title==='Snap catches')section.id='snap-controls';
 const summary=document.createElement('summary');summary.textContent=title;section.append(summary);
 for(const [key,label,min,max,step] of controls){
  labels[key]=label;const wrap=document.createElement('div');wrap.className='control';wrap.id='control-'+key;wrap.dataset.key=key;wrap.dataset.level=easyKeys.has(key)?'0':expertKeys.has(key)?'2':'1';
  if(min==='bool'){
   const l=document.createElement('label');l.className='check';l.htmlFor=key;l.append(document.createTextNode(label));
   const input=document.createElement('input');input.type='checkbox';input.id=key;input.checked=!!state[key];input.onchange=()=>change(key,input.checked);l.append(input);wrap.append(l);
  }else if(['closure','screenStyle','buttonStyle'].includes(min)){
   const l=document.createElement('label');l.className='label';l.htmlFor=key;l.textContent=label;const select=document.createElement('select');select.id=key;select.className='select';
   Object.entries(min==='closure'?closureNames:min==='screenStyle'?screenStyleNames:buttonStyleNames).forEach(([value,text])=>{const o=document.createElement('option');o.value=value;o.textContent=text;select.append(o)});select.value=state[key];select.onchange=()=>{if(key==='buttonStyle'){$('show-buttons').checked=select.value==='strip';Object.assign(state,select.value==='strip'?{buttonW:5.2,buttonH:3.2,buttonRadius:1.1,buttonGap:.3,buttonPitch:5.95}:{buttonW:DEFAULTS.buttonW,buttonH:DEFAULTS.buttonH,buttonRadius:DEFAULTS.buttonRadius,buttonGap:DEFAULTS.buttonGap,buttonPitch:DEFAULTS.buttonPitch})}if(key==='screenStyle'){const v=select.value==='beveled'?PRESETS.find(p=>p.name==='ZIP face style').values:DEFAULTS;for(const k of ['screenW','screenH','screenRadius','screenX','screenY','screenRaise','screenChamfer'])state[k]=v[k];state.screenChamfer=Math.min(state.screenChamfer,state.face)}if(['screenStyle','buttonStyle'].includes(key)){state[key]=select.value;reconcileFaceStyles();}change(key,select.value)};wrap.append(l,select);
  }else{
   const head=document.createElement('div');head.className='control-head';const l=document.createElement('label');l.htmlFor=key;l.textContent=label;const value=document.createElement('span');value.className='value';
   const number=document.createElement('input');number.id=key;number.type='number';number.min=min;number.max=max;number.step=step;number.value=state[key];number.setAttribute('aria-label',label+' in millimeters');
   const unit=document.createElement('span');unit.textContent='mm';value.append(number,unit);head.append(l,value,makeReset(key));
   const range=document.createElement('input');range.type='range';range.min=min;range.max=max;range.step=step;range.value=state[key];range.id=key+'-range';range.setAttribute('aria-label',label);
   range.oninput=()=>{number.value=range.value;change(key,Number(range.value))};
   number.oninput=()=>{const n=Number(number.value);if(number.value===''||!Number.isFinite(n))return;range.value=n;change(key,n)};
   number.onchange=()=>{const n=Number(number.value);if(number.value===''||!Number.isFinite(n)){number.value=state[key];return}range.value=n;change(key,n)};
   number.onblur=()=>{number.value=state[key]};
   wrap.append(head,range);
  }if(typeof min==='string')wrap.append(makeReset(key));const badge=document.createElement('span');badge.className='dimension-badge';badge.hidden=true;wrap.append(badge);section.append(wrap);
 }
 if(title==='Window & button style'){
  const p=document.createElement('p');p.className='help';p.textContent='The ZIP style adds a sloped screen opening and a separate four-key strip. Selecting a button style loads its starting dimensions. ZIP face style applies both source-inspired shapes with spacing adapted to this PCB.';section.append(p);
 }
 if(title==='PCB mounting screws'){
  const p=document.createElement('p');p.className='help';p.textContent='Outside diameter makes each post thicker. Screw-hole diameter is the printed pilot bore, not the screw thread designation. Posts remain 3 mm tall; hole spacing stays fixed. Changes apply to all four PCB mounts.';
  const b=document.createElement('button');b.textContent='Inspect mounting posts';b.id='inspect-mounts';b.onclick=()=>inspectPart('front');section.append(p,b);
 }
 if(title==='Rear connector opening'){
  const p=document.createElement('p');p.className='help';p.textContent='Straight DuPont connectors leave perpendicular to the PCB, through the backplate. Position this gap over the complete pin row. Offsets use front-view axes; positive vertical is upward. PCB + pins is an approximate fixed-position guide.';
  const b=document.createElement('button');b.textContent='Inspect rear opening';b.id='inspect-rear';b.onclick=()=>inspectPart('back');section.append(p,b);
 }
 if(title==='Screen & buttons'){const p=document.createElement('p');p.className='help';p.textContent='Offsets are from the shell center. Positive vertical values move upward. PCB hole spacing stays fixed when the shell grows.';section.append(p)}
 if(title==='Back cover & fit'){const p=document.createElement('p');p.className='help';p.textContent='The lip and catches are generated together with their mating shell. Start with a small fit test before a full print.';section.append(p)}
 if(title==='Snap catches'){const p=document.createElement('p');p.className='help';p.textContent='Flexible side arms latch into body catches. Remove the outer sleeve to reach them. Material and layer direction determine how well they flex.';section.append(p)}
 $('controls').append(section);
}
function reconcileFaceStyles(){
 const extra=Math.max(state.screenRaise>0?state.screenBezel:0,state.screenStyle==='beveled'?state.screenChamfer:0);
 const buttonExtra=state.buttonStyle==='strip'?1.2:2*state.buttonGap;
 const rightLimit=state.buttonX-(state.buttonW+buttonExtra)/2-(state.screenW+2*extra)/2-.5;
 if(state.screenX>rightLimit){state.screenX=Math.round(rightLimit*100)/100;toast('Screen shifted left to clear the selected buttons.')}
}
const resetKeys={screenStyle:['screenStyle','screenW','screenH','screenRadius','screenX','screenY','screenRaise','screenChamfer'],buttonStyle:['buttonStyle','buttonW','buttonH','buttonRadius','buttonGap','buttonPitch','buttonProtrusion']};
function makeReset(key){
 const b=document.createElement('button');b.type='button';b.className='reset-value';b.textContent='↺';b.dataset.reset=key;b.setAttribute('aria-label','Reset '+(labels[key]||key));
 b.onclick=()=>{for(const k of resetKeys[key]||[key])state[k]=baseline[k];if(key==='buttonStyle')$('show-buttons').checked=state.buttonStyle==='strip';change(key,state[key]);toast((labels[key]||key)+' restored')};return b;
}
function applyLinked(kind,factor){
 const previous=lastGoodState?{...lastGoodState}:{...state};
 try{const result=applyGlobal(baseline,state,kind,factor);state=result.state;change('wall',state.wall);lastEditedFields=['global-'+kind];const notes=result.adjustments.map(a=>`${labels[a.key]||a.key}: ${a.to.toFixed(2)} mm`);const message=notes.length?'Adjusted for clearance: '+notes.join('; ')+'.':'';$('linked-adjustments').textContent=message;$('linked-adjustments').hidden=!notes.length;setDimensionFeedback(result.adjustments.map(a=>a.key),message,'adjusted');linkedRollback={revision:requestedRev,state:previous,preset:lastGoodState?lastGoodPreset:startingPreset}}catch(error){syncControls();setDimensionFeedback(['global-'+kind],error.message,'review');$('linked-adjustments').textContent=error.message;$('linked-adjustments').hidden=false;toast(error.message)}
}
function createLinkedControl(kind,title){
 const row=document.createElement('div');row.className='control linked-control';row.id='control-global-'+kind;row.dataset.key='global-'+kind;row.dataset.level='0';labels['global-'+kind]=title;
 row.innerHTML=`<div class="control-head"><label for="global-${kind}">${title}</label><span class="value"><output id="global-${kind}-value">100%</output></span><button class="reset-value" id="reset-global-${kind}" aria-label="Reset ${title}">↺</button></div><input id="global-${kind}" aria-label="${title}" type="range" min="${GLOBAL_RANGES[kind].min*100}" max="${GLOBAL_RANGES[kind].max*100}" step="5" value="100"><p class="help" id="global-${kind}-summary"></p>`;
 row.querySelector('input').oninput=e=>{applyLinked(kind,Number(e.target.value)/100)};
 row.querySelector('button').onclick=()=>{applyLinked(kind,1)};
 const badge=document.createElement('span');badge.className='dimension-badge';badge.hidden=true;row.append(badge);
 $('linked-controls').append(row);
}
createLinkedControl('wall','Wall thickness scale');createLinkedControl('rounding','Edge rounding scale');
function clearDimensionFeedback(){
 dimensionFeedback=null;$('dimension-feedback').hidden=true;$('dimension-links').replaceChildren();
 document.querySelectorAll('.control[data-key]').forEach(row=>{
  row.classList.remove('dimension-conflict','dimension-adjusted','dimension-review');row.querySelector('.dimension-badge').hidden=true;
  row.querySelectorAll('input,select').forEach(input=>{input.removeAttribute('aria-invalid');input.removeAttribute('aria-describedby')});
 });
 document.querySelectorAll('#controls details').forEach(section=>{section.classList.remove('has-dimension-conflict','has-dimension-adjusted','has-dimension-review');section.querySelector('summary').removeAttribute('title')});
}
function setDimensionFeedback(fields,message,kind='conflict'){
 clearDimensionFeedback();const keys=[...new Set(fields||[])].filter(key=>$('control-'+key));if(!keys.length)return;
 dimensionFeedback={keys,message,kind};const panel=$('dimension-feedback');panel.hidden=false;panel.dataset.kind=kind;
 $('dimension-feedback-title').textContent=kind==='adjusted'?'Adjusted for clearance':kind==='review'?'Review recent adjustment':'Check highlighted dimensions';
 $('dimension-feedback-message').textContent=message;
 for(const key of keys){
  const row=$('control-'+key);row.classList.add('dimension-'+kind);const badge=row.querySelector('.dimension-badge');badge.hidden=false;badge.textContent=kind==='adjusted'?'Adjusted automatically':kind==='review'?'Review this change':'Check fit';
  row.querySelectorAll('input,select').forEach(input=>{input.setAttribute('aria-describedby','dimension-feedback-message');if(kind==='conflict')input.setAttribute('aria-invalid','true')});
  const section=row.closest('details');if(section){section.classList.add('has-dimension-'+kind);section.querySelector('summary').title='Contains highlighted dimensions';if(!row.hidden&&!section.hidden)section.open=true}
  const button=document.createElement('button');button.type='button';button.textContent=labels[key];button.dataset.dimensionTarget=key;button.setAttribute('aria-label','Show '+labels[key]);button.onclick=()=>revealDimensions([key]);$('dimension-links').append(button);
 }
}
function revealDimensions(keys){
 const rows=keys.map(key=>$('control-'+key)).filter(Boolean);if(!rows.length)return;
 const required=Math.max(levels[level],...rows.map(row=>Number(row.dataset.level)));level=Object.keys(levels).find(name=>levels[name]===required);updateLevel();
 try{localStorage.setItem('oled-case-workshop-level',level)}catch{}
 for(const row of rows){const section=row.closest('details');if(section)section.open=true}
 rows[0].scrollIntoView({block:'center',behavior:'instant'});const input=rows[0].querySelector('input:not(:disabled),select:not(:disabled)');input?.focus({preventScroll:true});
}
$('show-related-dimensions').onclick=()=>{if(dimensionFeedback)revealDimensions(dimensionFeedback.keys)};
function updateLevel(){
 document.querySelectorAll('[data-level-button]').forEach(b=>{const active=b.dataset.levelButton===level;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active))});
 $('level-description').textContent=levelDescriptions[level];
 document.querySelectorAll('#controls details').forEach(section=>{
  const controls=[...section.querySelectorAll('.control')];for(const row of controls)row.hidden=Number(row.dataset.level)>levels[level];
  section.hidden=controls.every(row=>row.hidden)||(section.id==='snap-controls'&&state.closure!=='snap');
  if(level==='easy'&&!section.hidden)section.open=true;
  for(const help of section.querySelectorAll('.help'))help.hidden=level==='easy';
 });
 $('expert-views').hidden=level!=='expert';
 $('baseline-name').textContent=startingPreset;
 document.querySelectorAll('[data-preset]').forEach(b=>{const active=PRESETS[Number(b.dataset.preset)].name===startingPreset;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active))});
}
document.querySelectorAll('[data-level-button]').forEach(b=>b.onclick=()=>{level=b.dataset.levelButton;updateLevel();try{localStorage.setItem('oled-case-workshop-level',level)}catch{}});
function syncControls(){
 for(const key of Object.keys(DEFAULTS)){const el=$(key);if(!el)continue;if(el.type==='checkbox')el.checked=!!state[key];else if(!(el.type==='number'&&document.activeElement===el))el.value=state[key];const r=$(key+'-range');if(r)r.value=state[key]}
 for(const [key,enabled] of [['screenChamfer',state.screenStyle==='beveled'],['buttonProtrusion',state.buttonStyle==='strip']]){if($(key))$(key).disabled=!enabled;if($(key+'-range'))$(key+'-range').disabled=!enabled}
 for(const b of document.querySelectorAll('[data-reset]')){const key=b.dataset.reset;b.disabled=(resetKeys[key]||[key]).every(k=>state[k]===baseline[k]);b.title=`Restore ${labels[key]} to ${baseline[key]}${typeof baseline[key]==='number'?' mm':''} (${startingPreset})`;}
 for(const kind of ['wall','rounding']){
  const keys=GLOBAL_GROUPS[kind],anchor=kind==='wall'?'wall':'corner';const ratio=baseline[anchor]?state[anchor]/baseline[anchor]:1;
  const uniform=keys.every(k=>Math.abs(state[k]-(k==='bezelWidth'?state.fit+(baseline.bezelWidth-baseline.fit)*ratio:baseline[k]*ratio))<.011);
  $('global-'+kind).title=uniform?'Linked values match this scale.':'Some part values are custom or limited for clearance. Moving this slider relinks the group.';$('global-'+kind).value=100*ratio;$('global-'+kind+'-value').textContent=Math.round(100*ratio)+'%';
  $('global-'+kind+'-summary').textContent=kind==='wall'?`Shell ${state.wall.toFixed(2)} · face ${state.face.toFixed(2)} · cover ${state.coverWall.toFixed(2)} mm`:`Body ${state.corner.toFixed(2)} · bezel ${state.bezelRadius.toFixed(2)} · window ${state.screenRadius.toFixed(2)} mm`;
  $('reset-global-'+kind).disabled=keys.every(k=>Math.abs(state[k]-baseline[k])<.00001);
 }
 $('closure-label').textContent=closureNames[state.closure]||state.closure;
 $('clearance-label').textContent=`${Number(state.fit).toFixed(2)} mm clearance per side`;
 updateLevel();
}
function change(key,value){linkedRollback=null;state[key]=value;source='design';document.querySelectorAll('[data-source]').forEach(b=>b.classList.toggle('active',b.dataset.source===source));syncControls();scheduleBuild([key]);updatePrompt()}
PRESETS.forEach((preset,i)=>{const b=document.createElement('button');b.textContent=preset.name;b.title=preset.description;b.dataset.preset=String(i);b.onclick=()=>{selectBaseline(preset.name);state={...baseline};$('linked-adjustments').hidden=true;for(const part of ['front','bezel','back','buttons'])$('show-'+part).checked=true;source='design';syncControls();scheduleBuild();updatePrompt();toast(preset.name)};$('presets').append(b)});
$('reset').onclick=()=>{state={...baseline};$('linked-adjustments').hidden=true;for(const part of ['front','bezel','back','buttons'])$('show-'+part).checked=true;source='design';syncControls();scheduleBuild();updatePrompt();toast(startingPreset+' restored')};
function setStatus(message,type=''){ $('status').className='status '+type;$('status-text').textContent=message;}
function setExportEnabled(value){valid=value;value=value&&source==='design';['export-front','export-back','download-set'].forEach(id=>$(id).disabled=!value);$('export-bezel').disabled=!value||!state.bezelOn;$('export-buttons').disabled=!value||state.buttonStyle!=='strip'}
function scheduleBuild(editedFields=[]){lastEditedFields=editedFields;clearDimensionFeedback();$('linked-adjustments').hidden=true;requestedRev++;setExportEnabled(false);setStatus('Updating solids…','busy');clearTimeout(timer);timer=setTimeout(kickBuild,110)}
const workerURL=URL.createObjectURL(new Blob([$('geometry-worker').textContent],{type:'application/javascript'}));
const worker=new Worker(workerURL);URL.revokeObjectURL(workerURL);
function kickBuild(){if(inFlight)return;inFlight=true;worker.postMessage({type:'build',state,revision:requestedRev})}
worker.onmessage=({data})=>{
 if(data.type==='built'){
  inFlight=false;if(data.revision!==requestedRev){kickBuild();return}
  lastBuiltRev=data.revision;state=data.state;lastGoodState={...state};lastGoodPreset=startingPreset;linkedRollback=null;lastParts=data.parts;lastWarnings=data.warnings||[];lastBuildMs=data.ms;
  syncControls();showModel();setExportEnabled(true);setStatus(`Updated · ${Object.values(lastParts).reduce((n,p)=>n+p.positions.length/9,0).toLocaleString()} triangles · ${Math.round(data.ms)} ms`);
  $('warnings').textContent=lastWarnings.join(' ');updatePrompt();
  try{localStorage.setItem(STORAGE_KEY,JSON.stringify(settings()))}catch{}
  if(firstBuild){fitView();firstBuild=false}
 }else if(data.type==='error'){
  if(data.request){const p=pendingExports.get(data.request);if(p){p.reject(Error(data.message));pendingExports.delete(data.request)}return}
  inFlight=false;if(data.revision!==requestedRev){kickBuild();return}
  if(linkedRollback?.revision===data.revision){const previous=linkedRollback.state;selectBaseline(linkedRollback.preset);linkedRollback=null;state=previous;syncControls();scheduleBuild();updatePrompt();$('linked-adjustments').textContent='That combination could not be built safely. Your previous design was restored. Try a nearby scale or adjust individual parts in Intermediate.';$('linked-adjustments').hidden=false;toast('Previous design restored; try a different scale.');return}
  setExportEnabled(false);setStatus(data.message,'error');setDimensionFeedback(data.fields?.length?data.fields:lastEditedFields,data.message,data.fields?.length?'conflict':'review');$('warnings').textContent='Showing the last valid shape. Correct the settings above to export.';
 }else if(data.type==='exported'){
  const p=pendingExports.get(data.request);if(p){p.resolve(data.parts);pendingExports.delete(data.request)}
 }
};
worker.onerror=e=>{inFlight=false;setExportEnabled(false);setStatus('The model could not be built: '+e.message,'error')};

const viewport=$('viewport');
const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,preserveDrawingBuffer:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor(0x000000,0);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.25;viewport.prepend(renderer.domElement);
const scene=new THREE.Scene();const camera=new THREE.PerspectiveCamera(36,1,.1,3000);camera.up.set(0,1,0);camera.position.set(75,63,115);
const orbit=new OrbitControls(camera,renderer.domElement);orbit.enableDamping=true;orbit.dampingFactor=.1;orbit.minDistance=25;orbit.maxDistance=650;
scene.add(new THREE.HemisphereLight(0xe3f0ff,0x44515b,2.4));
function lamp(color,power,pos){const l=new THREE.DirectionalLight(color,power);l.position.set(...pos);scene.add(l)}lamp(0xfff3df,3,[30,70,100]);lamp(0xb9deff,2,[-75,-20,40]);lamp(0xffffff,2,[30,-50,-80]);
const models=new THREE.Group();scene.add(models);const guide=new THREE.Group();scene.add(guide);
const grid=new THREE.GridHelper(230,46,0x526273,0x374552);grid.rotation.x=Math.PI/2;grid.position.z=-55;grid.material.transparent=true;grid.material.opacity=.45;scene.add(grid);
const meshMap={};
function decoded(text){const raw=atob(text),bytes=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)bytes[i]=raw.charCodeAt(i);return new Float32Array(bytes.buffer)}
const zipParts=Object.fromEntries(Object.entries(zipReference).map(([name,p])=>[name,{positions:decoded(p.data)}]));
for(const [value,part] of Object.entries(zipReference)){const option=document.createElement('option');option.value=value;option.textContent=part.label;$('zip-part').append(option)}
$('zip-part').onchange=()=>{showModel();fitView()};
const refParts=Object.fromEntries(Object.entries(reference).map(([name,p])=>[name,{positions:decoded(p.data)}]));
function makeGeometry(input,kind){
 const print=$('layout-mode').value==='print';const src=input;const out=new Float32Array(src.length);
 let low=Infinity,high=-Infinity;for(let i=2;i<src.length;i+=3){low=Math.min(low,src[i]);high=Math.max(high,src[i])}
 for(let i=0;i<src.length;i+=9){
  for(let j=0;j<3;j++){
   const k=i+j*3,d=i+((!print&&j>0)?3-j:j)*3;
   out[d]=src[k];out[d+1]=print&&kind!=='front'?-src[k+1]:src[k+1];
   out[d+2]=print?(kind==='front'?src[k+2]-low:high-src[k+2]):-src[k+2];
  }
 }
 const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.BufferAttribute(out,3));geometry.computeVertexNormals();geometry.computeBoundingBox();return geometry;
}
function dimensions(part){if(!part?.bounds)return '—';return part.bounds[0].map((n,i)=>(part.bounds[1][i]-n).toFixed(1)).join(' × ')+' mm'}
function disposeGroup(group){for(const child of [...group.children]){child.geometry?.dispose();child.material?.map?.dispose();child.material?.dispose();group.remove(child)}}
function showModel(){
 disposeGroup(models);disposeGroup(guide);for(const key of Object.keys(meshMap))delete meshMap[key];
 const zipKey=$('zip-part').value;
 const active=source==='zip'?{front:zipParts[zipKey]}:source==='reference'?refParts:lastParts;
 $('zip-reference-controls').hidden=source!=='zip';$('export-reason').hidden=source==='design';
 $('export-reason').textContent='Reference view: switch to Editable design to export your generated case.';
 for(const [name,part] of Object.entries(active)){
  const material=new THREE.MeshStandardMaterial({color:name==='front'?bodyColor:name==='bezel'?'#86bfce':name==='buttons'?'#d9ba72':'#c5ac8c',metalness:.12,roughness:.46,wireframe:$('wireframe').checked,side:THREE.DoubleSide});
  const mesh=new THREE.Mesh(makeGeometry(part.positions,name),material);mesh.name=name;models.add(mesh);meshMap[name]=mesh;
 }
 const displayState=source!=='design'?DEFAULTS:state;
 if(source!=='zip'&&$('show-board').checked&&$('layout-mode').value!=='print'){
  const pcb=new THREE.Mesh(new THREE.BoxGeometry(45,28,1.6),new THREE.MeshStandardMaterial({color:0x267d76,transparent:true,opacity:.45,depthWrite:false}));pcb.position.set(0,0,-(displayState.face+3+.8));guide.add(pcb);
  // Illustrative eight-way straight 2.54 mm row, independent of aperture settings.
  for(let i=0;i<8;i++){
   const x=(i-3.5)*2.54,z=displayState.face+4.6;
   const housing=new THREE.Mesh(new THREE.BoxGeometry(2.4,2.54,12),new THREE.MeshStandardMaterial({color:0x343940,roughness:.7}));housing.position.set(x,10.5,-(z+6));guide.add(housing);
   const wire=new THREE.Mesh(new THREE.CylinderGeometry(.35,.35,5,8),new THREE.MeshStandardMaterial({color:[0x303943,0xbf453b,0xdaa94c,0x4e9770,0x647bab,0xdfb665,0xaaaeb2,0x303943][i]}));wire.rotation.x=Math.PI/2;wire.position.set(x,10.5,-(z+14.5));guide.add(wire);
  }
  const cv=document.createElement('canvas');cv.width=512;cv.height=312;const c=cv.getContext('2d');c.fillStyle='#09131b';c.fillRect(0,0,512,312);c.fillStyle='#efe75d';c.font='bold 44px monospace';c.fillText('OLED',26,59);c.fillRect(22,80,468,3);c.fillStyle='#49c6e9';c.font='33px monospace';c.fillText('Case preview',24,137);c.fillText('128 x 64',24,187);c.font='24px monospace';c.fillText('Hardware guide only',24,254);
  const tex=new THREE.CanvasTexture(cv);tex.colorSpace=THREE.SRGBColorSpace;
  const panel=new THREE.Mesh(new THREE.PlaneGeometry(displayState.screenW-.3,displayState.screenH-.3),new THREE.MeshBasicMaterial({map:tex,side:THREE.DoubleSide}));panel.position.set(displayState.screenX,displayState.screenY,-1.8);guide.add(panel);
 }
 $('front-dimension-label').textContent=source==='zip'?'Reference part':'Front shell';
 $('front-size').textContent=source==='zip'?zipReference[zipKey].dimensions.map(n=>n.toFixed(1)).join(' × ')+' mm':source==='reference'?reference.front.dimensions.map(n=>n.toFixed(1)).join(' × ')+' mm':dimensions(lastParts.front);
 $('back-size').textContent=source!=='design'?'Not in this reference':dimensions(lastParts.back);
 $('view-title').textContent=source==='zip'?zipReference[zipKey].label:source==='reference'?'Original reference mesh':closureNames[state.closure]+' enclosure';
 $('view-subtitle').textContent=source==='zip'?'Exact ZIP mesh • Individual part, not an assembly':source==='reference'?'Fixed reference • Front shell and outer bezel':'Parametric reconstruction • Millimeters';
 document.querySelectorAll('[data-source]').forEach(b=>b.classList.toggle('active',b.dataset.source===source));
 applyLayout();setExportEnabled(valid);
}
function inspectPart(part){
 source='design';$('layout-mode').value='assembled';
 for(const name of ['front','bezel','back','buttons'])$('show-'+name).checked=name===part;
 $('show-board').checked=false;showModel();cameraView('back');
}
function applyLayout(){
 const mode=$('layout-mode').value,spread=Number($('explode').value),w=source==='reference'?56:state.width+2*state.bezelWidth;
 for(const [name,mesh] of Object.entries(meshMap)){
  mesh.visible=source==='zip'||$('show-'+name).checked;mesh.position.set(0,0,0);
  if(mode==='exploded')mesh.position.z=name==='bezel'?spread:name==='back'?-spread:name==='buttons'?spread*.5:0;
  if(mode==='print'){mesh.position.x=name==='front'?-w-8:name==='back'?w+8:0;if(name==='buttons'){mesh.position.x=w+8;mesh.position.y=-state.height-10}}
 }
 grid.position.z=mode==='print'?-.3:-(state.depth+state.coverDepth+spread+12);
 $('explode').disabled=mode!=='exploded';$('explode-value').textContent=spread+' mm';
}
function fitView(){
 const box=new THREE.Box3();let any=false;for(const mesh of models.children)if(mesh.visible){box.expandByObject(mesh);any=true}if(!any)return;
 const size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3());const dir=camera.position.clone().sub(orbit.target).normalize();
 const vertical=Math.max(size.y,size.z*.65),horizontal=size.x/camera.aspect;
 const distance=Math.max(horizontal,vertical)*.64/Math.tan(THREE.MathUtils.degToRad(camera.fov/2))+size.z*.55+20;
 orbit.target.copy(center);camera.position.copy(center).addScaledVector(dir,Math.max(distance,65));camera.near=.1;camera.far=2000;camera.updateProjectionMatrix();orbit.update();
}
function cameraView(mode){const center=orbit.target.clone();const length=camera.position.distanceTo(center);const dir=mode==='front'?new THREE.Vector3(0,0,1):mode==='back'?new THREE.Vector3(0,0,-1):new THREE.Vector3(.58,.46,1).normalize();camera.position.copy(center).addScaledVector(dir,length);camera.up.set(0,1,0);orbit.update();fitView()}
new ResizeObserver(()=>{const w=viewport.clientWidth,h=viewport.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix()}).observe(viewport);
function animate(){requestAnimationFrame(animate);orbit.update();grid.visible=camera.position.z>=orbit.target.z;renderer.render(scene,camera)}animate();
document.querySelectorAll('[data-source]').forEach(b=>b.onclick=()=>{source=b.dataset.source;showModel();fitView()});
document.querySelectorAll('[data-camera]').forEach(b=>b.onclick=()=>cameraView(b.dataset.camera));$('fit-view').onclick=fitView;
$('layout-mode').onchange=()=>{showModel();fitView()};$('explode').oninput=()=>{applyLayout()};$('reset-separation').onclick=()=>{$('explode').value=17;applyLayout()};
['show-front','show-bezel','show-back','show-buttons','show-board','wireframe'].forEach(id=>$(id).onchange=showModel);
document.querySelectorAll('[data-color]').forEach(b=>b.onclick=()=>{bodyColor=b.dataset.color;document.querySelectorAll('[data-color]').forEach(x=>x.classList.toggle('active',x===b));showModel()});

function updatePrompt(){
 const base=`Create a printable enclosure for the HW-937AB OLED module, based on the supplied screeen1.stl front shell and outer bezel, with a matching ${closureNames[state.closure].toLowerCase()} back cover.`;
 const diffs=Object.keys(DEFAULTS).filter(k=>k!=='closure'&&state[k]!==DEFAULTS[k]);
 const changes=diffs.map(k=>typeof state[k]==='boolean'?`${state[k]?'enable':'disable'} ${labels[k]?.toLowerCase()||k}`:typeof state[k]==='string'?`use ${(k==='screenStyle'?screenStyleNames:buttonStyleNames)[state[k]]||state[k]}`:`set ${(labels[k]||k).toLowerCase()} to ${Number(state[k]).toFixed(2).replace(/\.?0+$/,'')} mm`);
 $('prompt').textContent=base+(changes.length?' Compared with the original-footprint preset, '+changes.join('; ')+'.':' Keep the original-footprint starting dimensions.')+' Route the straight DuPont connector row through the rear plate, with continuous top walls. Preserve the chosen four-button style and screen opening, provide separate front, cover, and optional key-strip STL files, and check PCB, connector and catch clearance with a test print.';
}
function toast(text){$('toast').textContent=text;$('toast').classList.add('show');setTimeout(()=>$('toast').classList.remove('show'),2400)}
function saveBlob(blob,name){const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000)}
function settings(){return {schema:2,source:'screeen1.stl',units:'mm',parameters:state,startingPreset}}
$('save-settings').onclick=()=>saveBlob(new Blob([JSON.stringify(settings(),null,2)],{type:'application/json'}),'oled-case-settings.json');
$('load-settings').onclick=()=>$('settings-file').click();
$('settings-file').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;const data=JSON.parse(await file.text());state=readSettings(data);selectBaseline(data.startingPreset);source='design';syncControls();scheduleBuild();updatePrompt();toast(data.schema===1?'Older settings loaded; rear connector opening uses the new defaults.':'Settings loaded')}catch(error){toast(error.message)}e.target.value=''};
$('copy-prompt').onclick=async()=>{try{await navigator.clipboard.writeText($('prompt').textContent)}catch{const area=document.createElement('textarea');area.value=$('prompt').textContent;document.body.append(area);area.select();document.execCommand('copy');area.remove()}const b=$('copy-prompt');b.textContent='Copied!';setTimeout(()=>b.textContent='Copy brief',1800)};
function requestExport(parts){if(!valid||source!=='design')return Promise.reject(Error('Fix the design before exporting.'));return new Promise((resolve,reject)=>{const request=++exportId;pendingExports.set(request,{resolve,reject});worker.postMessage({type:'export',request,parts,revision:lastBuiltRev})})}
for(const part of ['front','bezel','back','buttons'])$('export-'+part).onclick=async()=>{try{const closure=state.closure;const result=await requestExport([part]);if(!result[part])throw Error('This part is disabled.');saveBlob(new Blob([result[part]],{type:'model/stl'}),`oled-${part}-${closure}.stl`);toast(`${part==='back'?'Back cover':part==='front'?'Front shell':part==='buttons'?'Button strip':'Outer bezel'} STL download requested`)}catch(e){toast(e.message)}};
$('download-set').onclick=async()=>{try{const snapshot={closure:state.closure,settings:JSON.stringify(settings(),null,2),brief:$('prompt').textContent,warnings:[...lastWarnings]};const exported=await requestExport(['front','bezel','back','buttons']);const files={};for(const [name,bytes] of Object.entries(exported))files[`oled-${name}-${snapshot.closure}.stl`]=bytes;files['settings.json']=strToU8(snapshot.settings);files['design-brief.txt']=strToU8(snapshot.brief);files['PRINT-NOTES.txt']=strToU8('OLED Case Workshop\nUnits: millimeters.\nThese are newly generated parametric parts based on screeen1.stl. The rear cover is a new design.\nImport each STL as a separate object. Check print orientation, supports, material flexibility and fitting before printing.\nPCB and connector clearances are approximate, not physically verified. Print a small fit prototype first.\nSnap arms latch into matching body catches; remove the outer sleeve to access them.\nScrew closure requires fasteners selected after measuring the assembled stack.\nThe backplate opening is for straight DuPont connectors perpendicular to the PCB. Its size and offset must match the actual connector row.\nWhen included, the separate button strip fits behind the matching apertures. Check switch travel and retaining-flange clearance.\nPCB screw-hole diameter is the printed pilot bore, not a nominal screw thread size.\nClearance is per side.\n\n'+snapshot.warnings.join('\n'));saveBlob(new Blob([zipSync(files,{level:6})],{type:'application/zip'}),`oled-case-${snapshot.closure}-print-set.zip`);toast('Print set download requested')}catch(e){toast(e.message)}};
$('about').onclick=()=>$('notes').hidden=false;$('close-notes').onclick=()=>$('notes').hidden=true;$('notes').onclick=e=>{if(e.target===$('notes'))$('notes').hidden=true};document.addEventListener('keydown',e=>{if(e.key==='Escape')$('notes').hidden=true});
window.caseWorkshop={getState:()=>({...state}),getStatus:()=>({valid,requestedRev,lastBuiltRev,inFlight,warnings:lastWarnings,ms:lastBuildMs}),setState:patch=>{state={...state,...patch};syncControls();scheduleBuild();updatePrompt()},exportParts:requestExport,getParts:()=>Object.fromEntries(Object.entries(lastParts).map(([k,v])=>[k,{bounds:v.bounds,volume:v.volume,triangles:v.positions.length/9}]))};
syncControls();updatePrompt();scheduleBuild();
function registerCaseTools(){
 const context=document.modelContext;if(!context?.registerTool)return;
 const lifecycle=new AbortController();window.addEventListener('pagehide',()=>lifecycle.abort(),{once:true});
 const enums={closure:Object.keys(closureNames),screenStyle:Object.keys(screenStyleNames),buttonStyle:Object.keys(buttonStyleNames)};
 const properties=Object.fromEntries(Object.entries(DEFAULTS).map(([key,value])=>[key,{type:typeof value,...(enums[key]?{enum:enums[key]}:{}),description:labels[key]||key}]));
 const result=()=>({parameters:{...state},startingPreset,controlLevel:level,valid,parts:window.caseWorkshop.getParts(),warnings:[...lastWarnings],units:'mm'});
 function settle(revision){return new Promise((resolve,reject)=>{
  const finish=(error)=>{clearTimeout(timeout);worker.removeEventListener('message',receive);error?reject(error):resolve()};
  const receive=({data})=>{if(data.revision!==revision)return;if(data.type==='error')finish(Error(data.message));else if(data.type==='built')finish(requestedRev===revision?null:Error('The design changed during this update. Read the current design before trying again.'))};
  const timeout=setTimeout(()=>finish(Error('The design update timed out.')),20000);worker.addEventListener('message',receive);
 })}
 let configuring=false;
 const definitions=[{
  name:'get_case_design',title:'Read case design',description:'Read the current OLED case parameters, model validity, printable part dimensions and fit notes. Does not change the design.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true,untrustedContentHint:false},
  execute(input={}){if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).length)throw Error('This tool takes no parameters.');return result()}
 },{
  name:'configure_case_design',title:'Configure case design',description:'Apply an OLED case preset and/or dimensional settings to the visible editor. Returns after the new model is built. Does not print, download files, or publish anything. Invalid geometry restores the previous design.',
  inputSchema:{type:'object',properties:{preset:{type:'string',enum:PRESETS.map(p=>p.name)},parameters:{type:'object',properties,additionalProperties:false}},additionalProperties:false},annotations:{readOnlyHint:false,untrustedContentHint:false},
  async execute(input){
   if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).some(k=>!['preset','parameters'].includes(k)))throw Error('Provide a preset and/or case parameters.');
   if(configuring||inFlight||requestedRev!==lastBuiltRev||!valid)throw Error('Wait for a valid design to finish building first.');
   const preset=input.preset===undefined?null:PRESETS.find(p=>p.name===input.preset);if(input.preset!==undefined&&!preset)throw Error('Unknown preset.');
   if(input.parameters!==undefined&&(!input.parameters||typeof input.parameters!=='object'||Array.isArray(input.parameters)))throw Error('Parameters must be an object.');
   for(const [key,values] of Object.entries(enums))if(input.parameters?.[key]!==undefined&&!values.includes(input.parameters[key]))throw Error('Invalid choice for '+key);
   const candidate=readSettings({schema:2,parameters:{...(preset?{...DEFAULTS,...preset.values}:state),...(input.parameters||{})}});
   const previous={...state},previousPreset=startingPreset;if(preset)selectBaseline(preset.name);configuring=true;state=candidate;source='design';if(state.buttonStyle==='strip')$('show-buttons').checked=true;syncControls();scheduleBuild();updatePrompt();const revision=requestedRev;
   try{await settle(revision);return result()}catch(error){if(requestedRev===revision){state=previous;selectBaseline(previousPreset);syncControls();scheduleBuild();updatePrompt();await settle(requestedRev)}throw error}finally{configuring=false}
  }
 }];
 for(const definition of definitions){try{Promise.resolve(context.registerTool(definition,{signal:lifecycle.signal})).catch(()=>{})}catch{}}
}
registerCaseTools();
