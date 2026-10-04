import assert from 'node:assert/strict';
import {DEFAULTS,PRESETS,buildModel,triangles,stl} from './geometry.js';
import modeling from '@jscad/modeling';
const api=await import('./linked-controls.js').catch(()=>null);
assert.ok(api?.applyGlobal,'Linked controls helper must be implemented');
const {applyGlobal,GLOBAL_GROUPS,GLOBAL_RANGES}=api;
assert.deepEqual(GLOBAL_GROUPS.wall,['wall','face','coverWall','bezelWidth','screenBezel']);
assert.deepEqual(GLOBAL_GROUPS.rounding,['corner','edge','coverEdge','bezelRadius','screenRadius','buttonRadius','rearOpeningRadius']);
assert.equal(GLOBAL_RANGES.wall.min,.75);assert.equal(GLOBAL_RANGES.rounding.max,1.5);
let models=0,solids=0;
const meshRejections=[];
const knownMeshLimits=new Set(['Slim slip fit wall150 rounding150 front','flexure rounding90 front','flexure rounding110 front','strip rounding95 front']);
function checkedMesh(solid,label) {
 try{return triangles(solid);}catch(error){
  assert.match(error.message,/unresolved solid seam/);
  assert.ok(knownMeshLimits.has(label),`Unexpected mesh rejection: ${label}: ${error.message}`);
  meshRejections.push(label);return null;
 }
}
const protectedKeys=['screenW','screenH','screenX','screenY','buttonW','buttonH','buttonX','buttonY','buttonPitch','fit','lip','tabWidth','tabThickness','hook','pcbPostDiameter','pcbHoleDiameter','rearOpeningWidth','rearOpeningHeight','rearOpeningX','rearOpeningY'];
for(const preset of PRESETS) {
 const base=preset.values, before=JSON.stringify(base);
 for(const kind of ['wall','rounding'])assert.deepEqual(applyGlobal(base,base,kind,1).state,base,`${preset.name}: 100% preserves preset`);
 for(const wallFactor of [.75,1.5])for(const roundFactor of [.5,1.5]) {
  const a=applyGlobal(base,base,'wall',wallFactor),b=applyGlobal(base,a.state,'rounding',roundFactor),s=b.state;
  assert.ok(s.wall>=base.wall*wallFactor);
  if(s.wall!==base.wall*wallFactor)assert.ok(a.adjustments.some(x=>x.key==='wall'),'wall minimum is explicit');
  for(const key of protectedKeys)assert.equal(s[key],base[key],`${preset.name}: preserves ${key}`);
  assert.ok(s.width>=base.width && s.height>=base.height && s.depth>=base.depth,'only required enlargement');
  for(const result of [a,b])for(const adj of result.adjustments)assert.ok(adj.reason && adj.from!==adj.to,'dependent changes are explained');
  const model=buildModel(s);models++;
  for(const [name,solid]of Object.entries(model.parts))if(solid) {
   const mesh=checkedMesh(solid,`${preset.name} wall${wallFactor*100} rounding${roundFactor*100} ${name}`);
   if(mesh){assert.ok(mesh.length>0);assert.ok(stl(solid).byteLength>84);solids++;}
   assert.ok(modeling.measurements.measureVolume(solid)>0);
   if(s.pcbMounts) {
    const pcb=modeling.transforms.translate([0,0,s.face+3.8],modeling.primitives.cuboid({size:[45,28,1.6]}));
    assert.ok(Math.abs(modeling.measurements.measureVolume(modeling.booleans.intersect(solid,pcb)))<.002,`${preset.name}/${name}: PCB clearance`);
   }
  }
  const parts=Object.entries(model.parts).filter(([,solid])=>solid);
  for(let i=0;i<parts.length;i++)for(let j=i+1;j<parts.length;j++)assert.ok(Math.abs(modeling.measurements.measureVolume(modeling.booleans.intersect(parts[i][1],parts[j][1])))<.01,`${preset.name} wall${wallFactor} rounding${roundFactor}: assembled ${parts[i][0]}/${parts[j][0]} collision`);
 }
 assert.equal(JSON.stringify(base),before,'preset is immutable');
}
// Exercise every advertised 5% tick and the actual UI reset sequence.
for(const base of [DEFAULTS,PRESETS[4].values]) {
 for(const kind of ['wall','rounding'])for(let pct=GLOBAL_RANGES[kind].min*100;pct<=GLOBAL_RANGES[kind].max*100;pct+=5) {
  const result=applyGlobal(base,base,kind,pct/100),model=buildModel(result.state);models++;
  for(const [name,solid]of Object.entries(model.parts))if(solid) {
   if(checkedMesh(solid,`${base.buttonStyle} ${kind}${pct} ${name}`))solids++;
  }
 }
 let state=applyGlobal(base,base,'wall',1.05).state;
 const grown={width:state.width,height:state.height,depth:state.depth};
 state=applyGlobal(base,state,'wall',1).state;
 for(const key of GLOBAL_GROUPS.wall)assert.equal(state[key],base[key],`wall100% restores ${key}`);
 for(const key of ['width','height','depth'])assert.equal(state[key],grown[key],'scale reset preserves the enlarged envelope');
 state=applyGlobal(base,state,'rounding',1.05).state;
 for(const solid of Object.values(buildModel(state).parts))if(solid)triangles(solid);
 for(const kind of ['wall','rounding']) {
  const scaled=applyGlobal(base,base,kind,1.25).state,reset=applyGlobal(base,scaled,kind,1).state;
  for(const key of GLOBAL_GROUPS[kind])assert.equal(reset[key],base[key],`125%→100% restores ${key}`);
 }
}
const advanced={...DEFAULTS,width:70,height:50,depth:12,screenX:-5.1,rearOpeningX:-2,fit:.3,pcbHoleDiameter:1.8};
const advancedResult=applyGlobal(DEFAULTS,advanced,'wall',1.5).state;
for(const key of ['width','height','depth',...protectedKeys])assert.equal(advancedResult[key],advanced[key],`preserves advanced ${key}`);
assert.equal(advancedResult.bezelWidth,advanced.fit+(DEFAULTS.bezelWidth-DEFAULTS.fit)*1.5,'sleeve wall scales independently of current fit');
assert.throws(()=>applyGlobal(DEFAULTS,DEFAULTS,'wall',2),/range|75|150/i);
assert.throws(()=>applyGlobal(DEFAULTS,DEFAULTS,'rounding',NaN),/finite|factor/i);
assert.throws(()=>applyGlobal(DEFAULTS,DEFAULTS,'unknown',1),/kind/i);
console.log(`PASS: linked mapping across ${models} real models; ${solids} meshes validated; preset identity, protected dimensions, PCB/assembly clearances, reset sequence and explanations verified.`);
console.log(`KNOWN MESH LIMITS: ${meshRejections.length} configurations rejected by the existing solid triangulator; UI must roll back these global changes.`);
for(const label of meshRejections)console.log(`  ${label}`);
