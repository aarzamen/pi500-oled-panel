import assert from 'node:assert/strict';
import { performance } from 'node:perf_hooks';
import modeling from '@jscad/modeling';

// Deliberately fails before geometry implementation is present.
const api = await import('./geometry.js').catch(() => null);
assert.ok(api?.buildModel, 'The parametric solid generator must be implemented');
const { DEFAULTS, PRESETS, normalize, buildModel, triangles, stl } = api;
const { measureBoundingBox, measureVolume } = modeling.measurements;
const { intersect } = modeling.booleans;
let assertions = 0;
function check(value, message) { assert.ok(value, message); assertions++; }
function meshCheck(solid, label) {
  const mesh = triangles(solid);
  check(mesh.length > 36 && mesh.length % 9 === 0, `${label}: triangle count`);
  check(mesh.every(Number.isFinite), `${label}: finite vertices`);
  const edges = new Map(), adjacency = new Map();
  let signedVolume = 0;
  const key = (v) => v.map(n => Math.round(n * 1e5)).join(',');
  for (let i=0; i<mesh.length; i+=9) {
    const p=[mesh.slice(i,i+3),mesh.slice(i+3,i+6),mesh.slice(i+6,i+9)];
    const ids=p.map(key);
    check(new Set(ids).size === 3, `${label}: nondegenerate triangle ${i/9}`);
    const [a,b,c]=p;
    signedVolume += (a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6;
    for (let j=0;j<3;j++) {
      const x=ids[j],y=ids[(j+1)%3], tag=[x,y].sort().join('|');
      const item=edges.get(tag)||{count:0,balance:0}; item.count++; item.balance+=x<y?1:-1; edges.set(tag,item);
      if(!adjacency.has(x)) adjacency.set(x,new Set()); adjacency.get(x).add(y);
      if(!adjacency.has(y)) adjacency.set(y,new Set()); adjacency.get(y).add(x);
    }
  }
  const bad=[...edges.values()].filter(e=>e.count!==2||e.balance!==0);
  check(bad.length===0, `${label}: ${bad.length} edges fail watertight/oriented check`);
  const pending=[adjacency.keys().next().value], visited=new Set();
  while(pending.length) {const v=pending.pop();if(visited.has(v))continue;visited.add(v);for(const n of adjacency.get(v))if(!visited.has(n))pending.push(n);}
  check(visited.size===adjacency.size, `${label}: one connected solid`);
  check(signedVolume>0,`${label}: positive winding volume`);
  check(Math.abs(signedVolume-measureVolume(solid))<.5,`${label}: triangle/solid volume agreement`);
  const bytes=stl(solid); check(bytes instanceof Uint8Array,`${label}: binary bytes`);
  const dv=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength), n=dv.getUint32(80,true);
  check(bytes.length===84+n*50,`${label}: STL length`);
  check(n===mesh.length/9,`${label}: STL triangle count agrees`);
  const bounds=measureBoundingBox(solid), exported=[[Infinity,Infinity,Infinity],[-Infinity,-Infinity,-Infinity]];
  for(let t=0;t<n;t++)for(let j=0;j<3;j++)for(let axis=0;axis<3;axis++) {
    const v=dv.getFloat32(84+t*50+12+j*12+axis*4,true);
    exported[0][axis]=Math.min(exported[0][axis],v);exported[1][axis]=Math.max(exported[1][axis],v);
  }
  check(Math.abs(exported[0][2])<1e-5,`${label}: print-bed Z is zero`);
  for(let axis=0;axis<3;axis++)check(Math.abs((bounds[1][axis]-bounds[0][axis])-(exported[1][axis]-exported[0][axis]))<.002,`${label}: export preserves dimensions axis ${axis}`);
}
check(Object.keys(normalize()).length===Object.keys(DEFAULTS).length,'normalize exact documented keys');
check(normalize({width:NaN}).width===DEFAULTS.width,'nonfinite defaults');
check(normalize({width:1}).width>1,'unsafe scalar values clamped');
check(normalize({closure:'unknown'}).closure==='snap','closure sanitized');
check(PRESETS.length===5,'five presets including ZIP face style');
check(DEFAULTS.screenStyle==='plain' && DEFAULTS.buttonStyle==='flexure','style defaults preserve the original face');
check(DEFAULTS.screenChamfer===1.5 && DEFAULTS.buttonProtrusion===1.2,'style dimensional defaults');
check(DEFAULTS.pcbPostDiameter===4 && DEFAULTS.pcbHoleDiameter===2,'independent PCB post and screw-hole diameter defaults');
check(DEFAULTS.rearOpeningWidth===24 && DEFAULTS.rearOpeningHeight===7 && DEFAULTS.rearOpeningY===10.5,'rear eight-pin-row opening defaults');
check(!('cableWidth' in DEFAULTS) && !('cableHeight' in normalize({cableHeight:9})),'retired top-edge cable keys are ignored');
function featureCheck(model,name) {
  const s=model.state, {parts}=model, rear=s.depth+s.coverDepth;
  const rounded=modeling.primitives.roundedRectangle({size:[s.rearOpeningWidth,s.rearOpeningHeight],roundRadius:s.rearOpeningRadius,segments:24});
  const passage=modeling.transforms.translate([s.rearOpeningX,s.rearOpeningY,s.face+4.6],modeling.extrusions.extrudeLinear({height:rear-s.face-4.6+.2},rounded));
  for(const [part,solid] of Object.entries(parts))if(solid)check(Math.abs(measureVolume(intersect(solid,passage)))<.001,`${name}/${part}: uninterrupted perpendicular connector path`);
  const sample=modeling.transforms.translate([s.rearOpeningX,s.rearOpeningY,rear-s.coverWall/2],modeling.primitives.cuboid({size:[s.rearOpeningWidth+.4,s.rearOpeningHeight+.4,.1]}));
  const expected=((s.rearOpeningWidth+.4)*(s.rearOpeningHeight+.4)-modeling.measurements.measureArea(rounded))*.1;
  check(Math.abs(measureVolume(intersect(parts.back,sample))-expected)<.002,`${name}: rear plate cross-section matches opening dimensions/radius`);
  const probes=[['front',s.height/2-s.wall/2,s.depth-.4],['back',s.height/2-s.coverWall/2,s.depth+.8]];
  if(parts.bezel)probes.push(['bezel',s.height/2+(s.fit+s.bezelWidth)/2,s.depth-.4]);
  for(const [part,y,z] of probes) {
    const wallProbe=modeling.transforms.translate([0,y,z],modeling.primitives.cuboid({size:[s.width-2*s.corner-2,.25,.2]}));
    check(Math.abs(measureVolume(intersect(parts[part],wallProbe))-measureVolume(wallProbe))<.001,`${name}/${part}: entire straight top wall is continuous`);
  }
  const probe=(x,y,z)=>modeling.transforms.translate([x,y,z],modeling.primitives.cuboid({size:[.015,.1,.015]}));
  if(s.screenStyle==='beveled') {
    const x=s.screenX+s.screenW/2+s.screenChamfer/2;
    check(Math.abs(measureVolume(intersect(parts.front,probe(x,s.screenY,-s.screenRaise+s.screenChamfer*.1))))<1e-6,`${name}: screen mouth flares outward`);
    const throat=probe(x,s.screenY,s.face-.05);
    check(Math.abs(measureVolume(intersect(parts.front,throat))-measureVolume(throat))<1e-6,`${name}: screen throat stays smaller than mouth`);
  }
  if(s.buttonStyle==='strip') {
    check(Boolean(parts.buttons),`${name}: separate button strip exists`);
    const bounds=measureBoundingBox(parts.buttons);
    check(Math.abs(bounds[0][2]+s.buttonProtrusion)<1e-6,`${name}: requested button protrusion`);
    check(Math.abs(bounds[1][2]-(s.face+.7))<1e-6,`${name}: 0.4 mm flange above 0.3 mm clearance`);
    const capSlice=modeling.transforms.translate([s.buttonX,s.buttonY,-.1],modeling.primitives.cuboid({size:[s.buttonW+.2,s.buttonH+.2,.05]}));
    const capBounds=measureBoundingBox(intersect(parts.buttons,capSlice));
    check(Math.abs(capBounds[1][0]-capBounds[0][0]-(s.buttonW-2*s.buttonGap))<1e-6,`${name}: stem X clearance`);
    check(Math.abs(capBounds[1][1]-capBounds[0][1]-(s.buttonH-2*s.buttonGap))<1e-6,`${name}: stem Y clearance`);
    const web=modeling.transforms.translate([s.buttonX,s.buttonY-s.buttonPitch/2,s.face+.425],modeling.primitives.cuboid({size:[.9,.1,.2]}));
    check(Math.abs(measureVolume(intersect(parts.buttons,web))-measureVolume(web))<1e-6,`${name}: connecting web spans adjacent buttons`);
    const mouth=probe(s.buttonX+s.buttonW/2+.2,s.buttonY,.05),throat=probe(s.buttonX+s.buttonW/2+.2,s.buttonY,s.face-.05);
    check(Math.abs(measureVolume(intersect(parts.front,mouth)))<1e-6,`${name}: button entry bevel flares outward`);
    check(Math.abs(measureVolume(intersect(parts.front,throat))-measureVolume(throat))<1e-6,`${name}: button opening retains its throat`);
  } else check(parts.buttons===null,`${name}: flexures remain integral`);
  if(s.pcbMounts) {
    const section=modeling.transforms.translate([-20,11.5,s.face+1.5],modeling.primitives.cuboid({size:[s.pcbPostDiameter+.1,s.pcbPostDiameter+.1,.1]}));
    const actual=intersect(parts.front,section), bounds=measureBoundingBox(actual);
    for(const axis of [0,1])check(Math.abs(bounds[1][axis]-bounds[0][axis]-s.pcbPostDiameter)<1e-5,`${name}: actual post outside diameter axis ${axis}`);
    const fac=12*Math.sin(Math.PI/12);
    check(Math.abs(measureVolume(actual)-fac*((s.pcbPostDiameter/2)**2-(s.pcbHoleDiameter/2)**2)*.1)<.001,`${name}: actual screw-hole diameter by annular cross-section`);
    const floor=modeling.transforms.translate([-20,11.5,s.face+.3],modeling.primitives.cylinder({radius:s.pcbHoleDiameter/2-.1,height:.1,segments:24}));
    check(Math.abs(measureVolume(intersect(parts.front,floor))-measureVolume(floor))<.001,`${name}: screw pilot remains blind`);
  }
}
const scenarios=[...PRESETS.map(p=>[p.name,p.values]),['large rounded', {width:58,height:39,corner:5,edge:.9,fit:.35}],['vents, no mounts or sleeve',{vents:true,pcbMounts:false,bezelOn:false}],['square edges',{corner:0,edge:0,screenRadius:0,buttonRadius:0,coverEdge:0,bezelRadius:0}],['screw with sleeve',{closure:'screw',bezelOn:true}],['thin shell',{wall:1.5,coverWall:1.5,fit:.35}],['large shell and clips',{width:58,height:39,wall:2.5,coverWall:2.4,depth:9,lip:2.5,tabWidth:9,tabThickness:1.4,hook:.65}],['larger posts with screw cover',{closure:'screw',width:58,height:40,pcbPostDiameter:6,pcbHoleDiameter:3,buttonW:6,buttonX:12.5,rearOpeningWidth:26,rearOpeningHeight:6,rearOpeningX:2,rearOpeningY:11}],['small posts square port',{pcbPostDiameter:3.4,pcbHoleDiameter:1.6,rearOpeningWidth:22,rearOpeningHeight:5,rearOpeningRadius:0}],['offset slip-fit port with vents',{closure:'friction',vents:true,rearOpeningX:-3,rearOpeningY:9.5,rearOpeningWidth:21,rearOpeningHeight:6,rearOpeningRadius:1.2}],['beveled screen only',{screenStyle:'beveled',screenRaise:0}],['button strip only',{buttonStyle:'strip',buttonW:5.2,buttonH:3.2,buttonRadius:1.1,buttonGap:.3}],['raised beveled rim and long buttons',{screenStyle:'beveled',screenChamfer:1.4,screenRaise:.4,screenBezel:2.1,buttonStyle:'strip',buttonW:5.2,buttonH:3.2,buttonRadius:1.1,buttonGap:.3,buttonProtrusion:2.2}]];
let worst=0;
for(const [name,input] of scenarios) {
  const start=performance.now(), model=buildModel(input); worst=Math.max(worst,performance.now()-start);
  for(const [part,solid] of Object.entries(model.parts))if(solid)meshCheck(solid,`${name}/${part}`);
  featureCheck(model,name);
  check(model.dimensions.width>=model.state.width,'dimensions include body');
  if(model.state.pcbMounts) {
    const pcb=modeling.transforms.translate([0,0,model.state.face+3+.8],modeling.primitives.cuboid({size:[45,28,1.6]}));
    for(const [part,solid] of Object.entries(model.parts))if(solid)check(Math.abs(measureVolume(intersect(pcb,solid)))<.002,`${name}/${part}: provisional board stack clears solids`);
  }
  check(model.warnings.some(w=>/fit|print/i.test(w)),'physical-fit warning');
  for(const [a,b] of [['front','back'],['front','bezel'],['back','bezel'],['front','buttons'],['back','buttons'],['bezel','buttons']])if(model.parts[a]&&model.parts[b])check(Math.abs(measureVolume(intersect(model.parts[a],model.parts[b])))<.01,`${name}: ${a}/${b} no assembled collision`);
}
for(const [input,word] of [[{screenW:46},/screen/i],[{buttonPitch:3},/button/i],[{depth:3},/depth|mount/i],[{lip:5},/lip/i],[{rearOpeningWidth:49},/rear|opening|connector/i],[{rearOpeningY:15},/rear|opening/i],[{rearOpeningRadius:4},/radius/i],[{pcbPostDiameter:3,pcbHoleDiameter:2},/post|hole/i],[{pcbPostDiameter:6},/boss|post|button/i],[{vents:true,rearOpeningY:0,rearOpeningHeight:17},/vent/i],[{rearOpeningWidth:44,rearOpeningY:0},/anchor/i],[{screenStyle:'beveled'},/rim/i],[{screenStyle:'beveled',screenRaise:0,screenChamfer:2},/bevel/i],[{buttonStyle:'strip'},/button|flange/i],[{buttonStyle:'strip',buttonW:5.2,buttonH:3.2,buttonRadius:1.1,buttonGap:.3,buttonX:14.424},/post/i],[{wall:1,coverWall:1},/snap|wall/i],[{wall:4,closure:'friction'},/PCB|walls/i]]) {
  assert.throws(()=>buildModel(input),word);assertions++;
}
// A pulling cap must hit the catch shoulder; an ornamental clip would fail this.
const snap=buildModel();
// Clip arms must clear a provisional 45 mm PCB width in their central span.
const clipBoard=modeling.transforms.translate([0,0,3.9],modeling.primitives.cuboid({size:[45,7,1.6]}));
check(Math.abs(measureVolume(intersect(snap.parts.back,clipBoard)))<.001,'snap arms clear provisional 45 mm PCB at z3.1–4.7');
check(measureVolume(intersect(snap.parts.front,modeling.transforms.translate([0,0,.6],snap.parts.back)))>.3,'snap hooks positively retain against body catches');
const signature=(model)=>JSON.stringify(Object.values(model.parts).filter(Boolean).map(s=>modeling.geometries.geom3.toPolygons(s).map(p=>p.vertices)));
const stripFields={buttonStyle:'strip',buttonW:5.2,buttonH:3.2,buttonRadius:1.1,buttonGap:.3};
for(const [key,value] of Object.entries(DEFAULTS)) {
  let base={}, altered;
  if(key==='screenStyle') {base={screenRaise:0};altered='beveled';}
  else if(key==='screenChamfer') {base={screenStyle:'beveled',screenRaise:0};altered=value-.03;}
  else if(key==='buttonStyle') {base={...stripFields,buttonStyle:'flexure'};altered='strip';}
  else if(key==='buttonProtrusion') {base=stripFields;altered=value+.03;}
  else altered=typeof value==='number'?value+(['face','lip'].includes(key)?-.03:.03):typeof value==='boolean'?!value:'friction';
  check(signature(buildModel({...base,[key]:altered}))!==signature(buildModel(base)),`${key} changes real geometry when its feature is enabled`);
}
console.log(`PASS: ${scenarios.length} complete model scenarios; ${assertions} geometry/export assertions; worst build ${Math.round(worst)}ms.`);
