import modeling from '@jscad/modeling';

const { roundedRectangle, rectangle, cuboid, cylinder, polygon } = modeling.primitives;
const { extrudeLinear, extrudeFromSlices, slice } = modeling.extrusions;
const { union, subtract } = modeling.booleans;
const { translate, rotateX } = modeling.transforms;
const { geom2, geom3 } = modeling.geometries;
const { measureBoundingBox } = modeling.measurements;
const SEGMENTS = 24, EPS = .02;

export const DEFAULTS = Object.freeze({
  width:51.1,height:33.16,depth:8,wall:2,face:1.5,corner:3,edge:.5,
  screenStyle:'plain',screenChamfer:1.5,screenW:24.6,screenH:15,screenX:-4.85,screenY:.75,screenRadius:.6,screenBezel:1,screenRaise:.6,
  buttonStyle:'flexure',buttonProtrusion:1.2,buttonW:7.5,buttonH:4.5,buttonPitch:5.95,buttonX:13.75,buttonY:8.7,buttonGap:.4,buttonRadius:.5,
  bezelOn:true,bezelWidth:2.45,bezelHeight:3.3,bezelRadius:4,
  coverDepth:8,coverWall:2,coverEdge:.8,fit:.25,lip:1.8,closure:'snap',tabWidth:7,tabThickness:1,hook:.45,
  pcbPostDiameter:4,pcbHoleDiameter:2,rearOpeningWidth:24,rearOpeningHeight:7,rearOpeningX:0,rearOpeningY:10.5,rearOpeningRadius:.6,vents:false,pcbMounts:true
});
export const PRESETS = [
  {name:'Original footprint',description:'Measured XY footprint; deeper shell to clear a provisional 1.6 mm PCB and locating lip.',values:{...DEFAULTS}},
  {name:'Rounded',description:'Softer outer corners, raised screen rim, deeper snap cover.',values:{...DEFAULTS,corner:4,edge:.8,bezelRadius:5,coverEdge:1.1,coverDepth:9,screenRaise:.9}},
  {name:'Slim slip fit',description:'Shallow removable rear cap with a locating lip; no latch retention.',values:{...DEFAULTS,closure:'friction',depth:8,face:1.3,coverDepth:5.5,coverWall:1.6,coverEdge:.6,bezelHeight:2.2,fit:.15}},
  {name:'Screw cover',description:'Separate matching ears for M2 through screws and pilot holes.',values:{...DEFAULTS,closure:'screw',coverDepth:8,bezelOn:false}},
  {name:'ZIP face style',description:'Beveled screen and separate button strip adapted from the ZIP shapes to the existing PCB layout.',values:{...DEFAULTS,screenStyle:'beveled',screenW:25.16,screenH:14.2,screenRadius:1,screenX:-4.05,screenY:.11,screenRaise:0,buttonStyle:'strip',buttonW:5.2,buttonH:3.2,buttonRadius:1.1,buttonGap:.3,buttonPitch:5.95}}
];
const LIMITS = {
  width:[30,100],height:[22,80],depth:[3,20],wall:[1,5],face:[.8,4],corner:[0,12],edge:[0,2],
  screenChamfer:[.1,3],screenW:[8,60],screenH:[6,40],screenX:[-35,35],screenY:[-25,25],screenRadius:[0,5],screenBezel:[0,4],screenRaise:[0,3],
  buttonProtrusion:[.2,4],buttonW:[3,15],buttonH:[2,10],buttonPitch:[3,15],buttonX:[-40,40],buttonY:[-30,30],buttonGap:[.2,1.2],buttonRadius:[0,3],
  bezelWidth:[1,8],bezelHeight:[.8,10],bezelRadius:[0,15],coverDepth:[3,30],coverWall:[1,5],coverEdge:[0,2.5],fit:[.05,.8],lip:[.6,5],tabWidth:[3,14],tabThickness:[.6,2.5],hook:[.15,1.2],pcbPostDiameter:[3,8],pcbHoleDiameter:[.8,4],rearOpeningWidth:[5,70],rearOpeningHeight:[3,35],rearOpeningX:[-40,40],rearOpeningY:[-30,30],rearOpeningRadius:[0,6]
};
export function normalize(input={}) {
  const s={...DEFAULTS};
  if (!input || typeof input!=='object') return s;
  for(const [key,[min,max]] of Object.entries(LIMITS)) {
    const n=Number(input[key]); if(input[key]!==null && input[key]!=='' && Number.isFinite(n))s[key]=Math.max(min,Math.min(max,n));
  }
  for(const key of ['bezelOn','vents','pcbMounts']) if(typeof input[key]==='boolean')s[key]=input[key];
  if(['snap','friction','screw'].includes(input.closure))s.closure=input.closure;
  if(['plain','beveled'].includes(input.screenStyle))s.screenStyle=input.screenStyle;
  if(['flexure','strip'].includes(input.buttonStyle))s.buttonStyle=input.buttonStyle;
  return s;
}
function rr(w,h,r) {
  if (w<=0 || h<=0)throw new Error('A wall leaves no interior space. Reduce its thickness.');
  return r<=.0001?rectangle({size:[w,h]}):roundedRectangle({size:[w,h],roundRadius:Math.min(r,w/2-.001,h/2-.001),segments:SEGMENTS});
}
function prism(w,h,r,z0,z1,x=0,y=0) {return translate([x,y,z0],extrudeLinear({height:z1-z0},rr(w,h,r)));}
function box(w,h,z0,z1,x=0,y=0) {return translate([x,y,(z0+z1)/2],cuboid({size:[w,h,z1-z0]}));}
// geom2 has XY only; lift slice edges explicitly for a rounded profile loft.
function easedBody(w,h,r,z0,z1,edge,atTop=false) {
  if(edge<.001)return prism(w,h,r,z0,z1);
  const sections=[0,.134,.5,1].map(t=>({z:z0+edge*t,inset:edge*(1-Math.sqrt(1-(1-t)**2))}));
  sections.push({z:z1,inset:0});
  if(atTop) { for(const p of sections)p.z=z0+z1-p.z;sections.reverse(); }
  return extrudeFromSlices({numberOfSlices:sections.length,repair:false,callback:(_,i)=>{
    const p=sections[i], sides=geom2.toSides(rr(w-2*p.inset,h-2*p.inset,Math.max(.025,r-p.inset)));
    return slice.create(sides.map(e=>e.map(v=>[v[0],v[1],p.z])));
  }},slice.fromSides(geom2.toSides(rr(w,h,Math.max(r,.025)))));
}
function bevelPassage(w,h,r,amount,z,x=0,y=0) {
  return translate([x,y,0],extrudeFromSlices({numberOfSlices:2,repair:false,callback:(_,i)=>{
    const extra=i===0?amount:0;
    return slice.create(geom2.toSides(rr(w+2*extra,h+2*extra,r+extra)).map(e=>e.map(v=>[v[0],v[1],z+i*amount])));
  }},slice.fromSides(geom2.toSides(rr(w,h,r)))));
}
function nearRectangle(x,y,cx,cy,w,h) {return Math.hypot(Math.max(Math.abs(x-cx)-w/2,0),Math.max(Math.abs(y-cy)-h/2,0));}
function inside(x,y,halfW,halfH,r,margin=0) {
  const ax=Math.abs(x),ay=Math.abs(y),ww=halfW-margin,hh=halfH-margin,rrr=Math.max(0,r-margin);
  return ax<=ww && ay<=hh && Math.hypot(Math.max(0,ax-(ww-rrr)),Math.max(0,ay-(hh-rrr)))<=rrr+1e-6;
}
function ventRows(s) {
  const width=Math.min(20,s.width-2*s.wall-8);
  return [-6,-3,0,3,6].filter(y=>Math.abs(s.rearOpeningX)>=(s.rearOpeningWidth+width)/2+1 || Math.abs(s.rearOpeningY-y)>=(s.rearOpeningHeight+1.2)/2+1);
}
function validate(s) {
  const fail=(condition,message)=>{if(condition)throw new Error(message);};
  fail(s.corner>=Math.min(s.width,s.height)/2-1,'Reduce the body corner radius or enlarge the body.');
  fail(s.edge>=s.face-.25 || s.edge>=s.wall-.25,'Edge easing needs at least 0.25 mm of face and wall behind it. Reduce edge easing.');
  fail(s.coverEdge>=s.coverWall-.25 || s.coverEdge>=s.coverDepth-.5,'Reduce cover edge easing or increase the cover wall.');
  fail(s.depth<=s.face+1,'Increase body depth above face thickness plus 1 mm.');
  fail(s.lip>=s.depth-s.face-.5,'Registration lip reaches the front face. Reduce lip engagement or increase body depth.');
  fail(s.coverDepth<=s.coverWall+1,'Increase cover depth or reduce its wall thickness.');
  fail(s.screenRadius>=Math.min(s.screenW,s.screenH)/2,'Reduce screen corner radius below half its smaller dimension.');
  fail(s.buttonRadius>=Math.min(s.buttonW,s.buttonH)/2,'Reduce button corner radius below half the button height/width.');
  if(s.screenStyle==='beveled') {
    fail(s.screenRadius<.05,'Beveled screens need a nonzero corner radius. Increase screen corner radius to at least 0.05 mm.');
    fail(s.screenChamfer>s.face+s.screenRaise+1e-6,'Screen bevel is deeper than the face. Reduce bevel width or increase face thickness.');
    fail(s.screenRaise>0 && s.screenBezel<s.screenChamfer+.35,'A raised beveled rim needs rim width at least bevel + 0.35 mm. Increase rim width or set screen raise to zero.');
  }
  if(s.buttonStyle==='flexure')fail(s.buttonPitch<s.buttonH+2*s.buttonGap+.45,'Button slots overlap or leave a weak web. Increase button pitch or reduce button height/gap.');
  else {
    fail(s.buttonRadius<.05,'Separate button openings need a nonzero corner radius. Increase button radius.');
    fail(s.buttonPitch<s.buttonH+2.5,'Button retaining flanges overlap. Increase button pitch or reduce button height.');
    fail(Math.min(s.buttonW,s.buttonH)-2*s.buttonGap<.8,'Button clearance leaves stems thinner than 0.8 mm. Reduce clearance or enlarge the buttons.');
  }
  const screenExtra=Math.max(s.screenRaise>0?s.screenBezel:0,s.screenStyle==='beveled'?s.screenChamfer:0);
  const rectangles=[[s.screenX,s.screenY,s.screenW+2*screenExtra,s.screenH+2*screenExtra,'Screen']];
  const buttonExtra=s.buttonStyle==='strip'?1.2:2*s.buttonGap;
  for(let i=0;i<4;i++)rectangles.push([s.buttonX,s.buttonY-i*s.buttonPitch,s.buttonW+buttonExtra,s.buttonH+buttonExtra,'Button']);
  const flangeRectangles=s.buttonStyle==='strip'?Array.from({length:4},(_,i)=>[s.buttonX,s.buttonY-i*s.buttonPitch,s.buttonW+2.2,s.buttonH+2.2]):[];
  for(const [x,y,w,h] of flangeRectangles)for(const dx of [-w/2,w/2])for(const dy of [-h/2,h/2])fail(!inside(x+dx,y+dy,s.width/2-s.wall,s.height/2-s.wall,Math.max(0,s.corner-s.wall),.2),'Button retaining flanges meet a body wall. Move/reduce the buttons or enlarge the body.');
  for(const [x,y,w,h,label] of rectangles) {
    for(const dx of [-w/2,w/2])for(const dy of [-h/2,h/2])fail(!inside(x+dx,y+dy,s.width/2,s.height/2,s.corner,s.wall+.3),`${label} is too close to a wall. Enlarge the body or move/reduce that feature.`);
  }
  const [sx,sy,sw,sh]=rectangles[0];
  for(const [x,y,w,h] of rectangles.slice(1))fail(Math.abs(x-sx)<(w+sw)/2+.45 && Math.abs(y-sy)<(h+sh)/2+.45,'Screen rim overlaps a button flexure. Move them apart or reduce the rim.');
  if(s.pcbMounts) {
    fail(s.pcbPostDiameter-s.pcbHoleDiameter<1.6-1e-6,'PCB screw holes leave less than 0.8 mm of post wall. Increase post diameter or reduce hole diameter.');
    fail(s.depth+1e-6<s.face+4.6+s.lip+.1,'The provisional PCB stack intersects the registration lip. Set body depth to at least face + 4.6 mm + lip + 0.1 mm, reduce lip engagement, or disable PCB mounts.');
    for(const x of [-22.5,22.5])for(const y of [-14,14])fail(!inside(x,y,s.width/2-s.wall,s.height/2-s.wall,Math.max(0,s.corner-s.wall),.1),'The provisional 45 × 28 mm PCB intersects the body walls. Enlarge the body or reduce wall thickness.');
    for(const x of [-20,20])for(const y of [-11.5,11.5]) {
      fail(!inside(x,y,s.width/2-s.wall,s.height/2-s.wall,Math.max(0,s.corner-s.wall),s.pcbPostDiameter/2+.1),'Measured PCB bosses do not fit this body. Enlarge it or disable PCB mounts.');
      fail(nearRectangle(x,y,s.screenX,s.screenY,s.screenW,s.screenH)<s.pcbPostDiameter/2+.05,'Screen opening intersects a measured PCB boss. Move/reduce screen or disable mounts.');
      for(const [bx,by,bw,bh] of (s.buttonStyle==='strip'?flangeRectangles:rectangles.slice(1)))fail(nearRectangle(x,y,bx,by,bw,bh)<s.pcbPostDiameter/2+.05,'Button slots or retaining flanges intersect a PCB post. Move/reduce buttons, reduce post diameter, or disable mounts.');
    }
  }
  fail(s.rearOpeningRadius>=Math.min(s.rearOpeningWidth,s.rearOpeningHeight)/2,'Reduce rear opening corner radius below half its smaller dimension.');
  for(const dx of [-s.rearOpeningWidth/2,s.rearOpeningWidth/2])for(const dy of [-s.rearOpeningHeight/2,s.rearOpeningHeight/2]) {
    const x=s.rearOpeningX+dx,y=s.rearOpeningY+dy;
    fail(!inside(x,y,s.width/2,s.height/2,s.corner,s.coverWall+.35),'Rear opening removes the cover perimeter. Move or reduce the opening, enlarge the body, or reduce cover wall thickness.');
    fail(!inside(x,y,s.width/2-s.wall,s.height/2-s.wall,Math.max(0,s.corner-s.wall),.15),'The straight rear connector path meets the front shell wall. Move or reduce the rear opening, or enlarge the body.');
  }
  if(s.vents)fail(ventRows(s).length===0,'The rear opening leaves no separate vent rows with a 1 mm web. Reduce or move the opening, or disable vents.');
  fail(s.bezelOn && s.bezelWidth<s.fit+.7,'Sleeve wall is too thin for this fit clearance. Increase bezel width.');
  fail(s.bezelOn && s.bezelRadius>s.corner+s.bezelWidth-.35,'Sleeve corner radius removes its inner corner wall. Reduce bezel corner radius or increase bezel width.');
  if(s.closure==='snap') {
    fail(s.wall<1.25,'Snap relief channels require body walls of at least 1.25 mm. Increase wall thickness.');
    fail(s.pcbMounts && s.width/2-s.wall-s.fit-s.tabThickness+.45<22.7,'Snap arms encroach on the approximate 45 mm PCB width. Enlarge the body or reduce snap thickness.');
    fail(s.depth<s.face+2.7,'Snap catches need body depth of at least face + 2.7 mm.');
    fail(s.hook>s.wall-.85,'Snap hook exceeds the body catch depth. Reduce the hook or increase wall thickness.');
    fail(s.tabWidth>s.height-2*s.wall-2*s.corner-2,'Snap arms are too wide for the side wall. Reduce tab width.');
    const armOuter=s.width/2-s.wall-s.fit+.45, armCenter=armOuter-s.tabThickness/2;
    for(const sign of [-1,1]) {
      fail(Math.abs(s.rearOpeningX-sign*armCenter)<(s.rearOpeningWidth+s.tabThickness)/2+.8 && Math.abs(s.rearOpeningY)<(s.rearOpeningHeight+s.tabWidth)/2+.8,'Rear opening weakens a snap-arm anchor. Move or reduce the opening, or choose another closure.');
      if(s.pcbMounts)for(const y of [-11.5,11.5])fail(nearRectangle(sign*20,y,sign*armCenter,0,s.tabThickness,s.tabWidth)<s.pcbPostDiameter/2+.15,'Snap arms intersect the PCB posts. Reduce post diameter or tab width, or enlarge the case.');
    }
  }
}

export function buildModel(input={}) {
  const s=normalize(input); validate(s);
  const iw=s.width-2*s.wall, ih=s.height-2*s.wall, ir=Math.max(0,s.corner-s.wall), rear=s.depth+s.coverDepth;
  const shell=easedBody(s.width,s.height,s.corner,0,s.depth,s.edge);
  let front=subtract(shell,prism(iw,ih,ir,s.face,s.depth+1));
  if(s.screenRaise>0 && s.screenBezel>0)front=union(front,prism(s.screenW+2*s.screenBezel,s.screenH+2*s.screenBezel,s.screenRadius+s.screenBezel,-s.screenRaise,EPS,s.screenX,s.screenY));
  const faceCuts=[prism(s.screenW,s.screenH,s.screenRadius,-s.screenRaise-1,s.face+1,s.screenX,s.screenY)];
  if(s.screenStyle==='beveled')faceCuts.push(bevelPassage(s.screenW,s.screenH,s.screenRadius,s.screenChamfer,-s.screenRaise,s.screenX,s.screenY));
  const keySolids=[];let buttons=null;
  for(let i=0;i<4;i++) {
    const x=s.buttonX,y=s.buttonY-i*s.buttonPitch;
    if(s.buttonStyle==='strip') {
      faceCuts.push(prism(s.buttonW,s.buttonH,s.buttonRadius,-.1,s.face+.1,x,y));
      faceCuts.push(bevelPassage(s.buttonW,s.buttonH,s.buttonRadius,.6,0,x,y));
      keySolids.push(prism(s.buttonW-2*s.buttonGap,s.buttonH-2*s.buttonGap,Math.max(0,s.buttonRadius-s.buttonGap),-s.buttonProtrusion,s.face+.3+EPS,x,y));
      keySolids.push(prism(s.buttonW+2.2,s.buttonH+2.2,s.buttonRadius+1.1,s.face+.3,s.face+.7,x,y));
      if(i<3)keySolids.push(box(1,s.buttonPitch,s.face+.3,s.face+.55,x,y-s.buttonPitch/2));
      continue;
    }
    const ring=subtract(rr(s.buttonW+2*s.buttonGap,s.buttonH+2*s.buttonGap,s.buttonRadius+s.buttonGap),rr(s.buttonW,s.buttonH,s.buttonRadius));
    // Remove the left side of the slot: the full button height remains an integral hinge.
    const uSlot=subtract(ring,translate([-s.buttonW/2-s.buttonGap,0],rectangle({size:[s.buttonGap*2+.8,s.buttonH+4*s.buttonGap]})));
    faceCuts.push(translate([x,y,-1],extrudeLinear({height:s.face+2},uSlot)));
  }
  front=subtract(front,...faceCuts);
  if(keySolids.length)buttons=union(...keySolids);
  if(s.pcbMounts) {
    const bosses=[],holes=[];
    for(const x of [-20,20])for(const y of [-11.5,11.5]) {
      bosses.push(translate([x,y,s.face+1.5-EPS/2],cylinder({radius:s.pcbPostDiameter/2,height:3+EPS,segments:SEGMENTS})));
      holes.push(translate([x,y,s.face+1.8+.05],cylinder({radius:s.pcbHoleDiameter/2,height:2.5,segments:SEGMENTS})));
    }
    front=subtract(union(front,...bosses),...holes);
  }
  let back=subtract(easedBody(s.width,s.height,s.corner,s.depth,rear,s.coverEdge,true),prism(s.width-2*s.coverWall,s.height-2*s.coverWall,Math.max(0,s.corner-s.coverWall),s.depth-1,rear-s.coverWall));
  const lipWall=.9, lipW=iw-2*s.fit, lipH=ih-2*s.fit, lipR=Math.max(0,ir-s.fit);
  let lip=subtract(prism(lipW,lipH,lipR,s.depth-s.lip,s.depth+s.coverWall+.1),prism(lipW-2*lipWall,lipH-2*lipWall,Math.max(0,lipR-lipWall),s.depth-s.lip-1,s.depth+s.coverWall+.2));
  // A radial flange at the mating edge joins the inner lip to the cap wall.
  const flange=subtract(prism(s.width-2*s.coverWall+EPS,s.height-2*s.coverWall+EPS,Math.max(0,s.corner-s.coverWall),s.depth,s.depth+.7),prism(lipW-2*lipWall,lipH-2*lipWall,Math.max(0,lipR-lipWall),s.depth-.1,s.depth+.8));
  lip=union(lip,flange);
  if(s.pcbMounts) {
    const reliefs=[];
    for(const x of [-20,20])for(const y of [-11.5,11.5])reliefs.push(translate([x,y,s.face+1.6],cylinder({radius:s.pcbPostDiameter/2+.2,height:3.4,segments:SEGMENTS})));
    lip=subtract(lip,...reliefs);
  }
  if(s.closure==='snap') {
    const slotWidth=s.tabWidth+2*Math.max(.5,s.fit), outer=iw/2-s.fit+.45, inner=outer-s.tabThickness;
    // Slots free both arm edges all the way to the back plate. The lip is interrupted locally.
    const separations=[-1,1].map(sign=>box(s.wall+s.coverWall+4,slotWidth,s.depth-s.lip-1,rear-s.coverWall,sign*(s.width/2-s.wall),0));
    lip=subtract(lip,...separations);
    // Arms lie inside the cap; side-wall clearance is retained instead of cutting the outer cap wall.
    const tip=s.face+.7, shoulder=tip+1.2, hookOuter=outer+s.fit+s.hook;
    const arms=[];
    for(const sign of [-1,1]) {
      const channel=box(s.tabThickness+2*s.fit,slotWidth,tip-.2,rear-s.coverWall,sign*(outer-s.tabThickness/2),0);
      front=subtract(front,channel);
      back=subtract(back,channel);
      arms.push(box(s.tabThickness,s.tabWidth,tip,rear-s.coverWall+.12,sign*(inner+s.tabThickness/2),0));
      const points=[[outer-.08,tip],[hookOuter,shoulder],[outer-.08,shoulder]];
      const ramp=translate([0,s.tabWidth/2,0],rotateX(Math.PI/2,extrudeLinear({height:s.tabWidth},polygon({points:sign>0?points:points.map(p=>[-p[0],p[1]]).reverse()}))));
      arms.push(ramp);
      front=subtract(front,box(s.wall+.8,s.tabWidth+2*s.fit,tip-.15,shoulder+s.fit,sign*(s.width/2-s.wall/2),0));
    }
    back=union(back,lip,...arms);
  } else back=union(back,lip);
  // A straight connector path runs perpendicular to the PCB and through the rear
  // plate. Cutting the entire column also clears any overlapping lip or flange.
  back=subtract(back,prism(s.rearOpeningWidth,s.rearOpeningHeight,s.rearOpeningRadius,s.depth-s.lip-.2,rear+.2,s.rearOpeningX,s.rearOpeningY));
  if(s.vents) {
    const ventCuts=ventRows(s).map(y=>prism(Math.min(20,iw-8),1.2,.5,rear-s.coverWall-.1,rear+.1,0,y));
    back=subtract(back,...ventCuts);
  }
  let bezel=null;
  if(s.bezelOn) {
    bezel=subtract(prism(s.width+2*s.bezelWidth,s.height+2*s.bezelWidth,s.bezelRadius,-s.bezelHeight,s.depth),prism(s.width+2*s.fit,s.height+2*s.fit,s.corner+s.fit,-.02,s.depth+.1),prism(s.width-1.2,s.height-1.2,Math.max(0,s.corner-.6),-s.bezelHeight-.1,.01));

  }
  if(s.closure==='screw') {
    const earX=s.width/2+3, earY=-s.height/2+7, earThickness=Math.min(2.5,s.depth-s.face-.2);
    for(const sign of [-1,1]) {
      const x=sign*earX;
      const ear=prism(9,7,3,s.depth-earThickness,s.depth,x-sign*.3,earY);
      const pilot=translate([x,earY,s.depth-earThickness/2+.3],cylinder({radius:.8,height:earThickness,segments:SEGMENTS}));
      front=union(front,subtract(ear,pilot));
      const backEar=prism(9,7,3,s.depth,s.depth+2.5,x-sign*.3,earY);
      const hole=translate([x,earY,s.depth+1.25],cylinder({radius:1.15,height:3,segments:SEGMENTS}));
      back=union(back,subtract(backEar,hole));
      if(bezel)bezel=subtract(bezel,prism(9+2*s.fit,7+2*s.fit,3+s.fit,s.depth-earThickness-s.fit,s.depth+.1,x-sign*.3,earY));
    }
  }
  const warnings=['Parametric reconstruction from measured reference proportions; PCB, connector and button travel need a test print.',s.pcbMounts?`PCB posts are ${s.pcbPostDiameter.toFixed(2)} mm outside diameter with ${s.pcbHoleDiameter.toFixed(2)} mm blind screw holes and 3 mm height, at fixed centers ±20 × ±11.5 mm. Verify fastener and board stack before assembly.`:'PCB mounting bosses are disabled.'];
  warnings.push('Rear opening assumes straight connectors perpendicular to an eight-pin row. Its position and connector housing dimensions are unmeasured; adjust the opening to the actual board.');
  if(s.vents)warnings.push(`${ventRows(s).length} separate vent rows remain; rows near the connector opening are omitted to preserve a 1 mm web.`);
  if(s.closure==='snap')warnings.push(`Snap hooks retain ${s.hook.toFixed(2)} mm inside matching side windows. Material, print orientation, fatigue and insertion force are unverified.${s.bezelOn?' Slide the sleeve off to access both release windows.':''}`);
  if(s.closure==='friction')warnings.push('The slip-fit registration lip locates the removable cap but provides no latch retention. Tape or adhesive may be needed for secure retention; verify clearance with a small test piece.');
  if(s.closure==='screw')warnings.push('External ears use 2.3 mm cover holes and blind 1.6 mm body pilots for nominal M2 screws. Confirm screw length and printed pilot fit.');
  warnings.push('Inspect support needs and button hinge layer direction in the slicer. PCB stack height and registration-lip clearance require direct measurement.');
  if(s.face>1.8)warnings.push('A thick front face makes the integral button hinges stiff; verify safe switch travel.');
  if(s.buttonStyle==='strip')warnings.push('The separate button strip uses 0.3 mm flange clearance above the face and 0.4 mm retaining flanges joined by thin webs. Switch travel, spring action and retention are unverified.');
  if(s.screenStyle==='beveled' || s.buttonStyle==='strip')warnings.push('ZIP face shapes are approximated and adapted to this PCB layout; this is not a direct reuse of the source mesh.');
  const parts={front,bezel,back,buttons},bounds=Object.values(parts).filter(Boolean).map(solid=>measureBoundingBox(solid));
  const min=[0,1,2].map(a=>Math.min(...bounds.map(b=>b[0][a]))),max=[0,1,2].map(a=>Math.max(...bounds.map(b=>b[1][a])));
  return {state:s,parts,warnings,dimensions:{width:max[0]-min[0],height:max[1]-min[1],depth:max[2]-min[2]}};
}

const triangleCache=new WeakMap();
export function triangles(solid) {
  if(!solid || !geom3.isA(solid))throw new Error('Select a generated solid before exporting.');
  if(triangleCache.has(solid))return triangleCache.get(solid);
  // Boolean polygons can contain T-junctions. Split every boundary at the same
  // welded vertices before fanning convex faces, so STL edges match exactly.
  const grid=1e4, vertices=new Map();
  const weld=(p)=>{const key=p.map(n=>Math.round(n*grid)).join(',');if(!vertices.has(key))vertices.set(key,p.map(n=>Math.round(n*grid)/grid));return vertices.get(key);};
  const polygons=geom3.toPolygons(solid).map(p=>p.vertices.map(weld));
  const points=[...vertices.values()], result=[];
  for(const source of polygons) {
    const boundary=[];
    for(let j=0;j<source.length;j++) {
      const a=source[j],b=source[(j+1)%source.length],u=b.map((n,k)=>n-a[k]),len2=u.reduce((sum,n)=>sum+n*n,0);
      if(len2<1e-12)continue;
      const splits=[{t:0,p:a}];
      for(const p of points) {
        const d=p.map((n,k)=>n-a[k]), t=d.reduce((sum,n,k)=>sum+n*u[k],0)/len2;
        if(t<=1e-7 || t>=1-1e-7)continue;
        const dist2=d.reduce((sum,n,k)=>sum+(n-t*u[k])**2,0);
        if(dist2<2.5e-8)splits.push({t,p});
      }
      splits.sort((a,b)=>a.t-b.t);
      for(const entry of splits)if(!boundary.length || Math.hypot(...entry.p.map((n,k)=>n-boundary[boundary.length-1][k]))>1e-6)boundary.push(entry.p);
    }
    if(boundary.length<3)continue;
    const center=boundary.reduce((sum,p)=>sum.map((n,k)=>n+p[k]/boundary.length),[0,0,0]);
    for(let j=0;j<boundary.length;j++) {
      const a=boundary[j],b=boundary[(j+1)%boundary.length],u=a.map((n,k)=>n-center[k]),v=b.map((n,k)=>n-center[k]);
      if(Math.hypot(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])<1e-14)continue;
      result.push(...center,...a,...b);
    }
  }
  if(result.length===0 || result.length%9!==0 || result.some(v=>!Number.isFinite(v)))throw new Error('Solid triangulation failed. Adjust the geometry before exporting.');
  const edges=new Map(), neighbors=new Map();
  const vertexKey=(p)=>p.map(n=>Math.round(n*1e5)).join(',');
  for(let i=0;i<result.length;i+=9) {
    const ids=[vertexKey(result.slice(i,i+3)),vertexKey(result.slice(i+3,i+6)),vertexKey(result.slice(i+6,i+9))];
    if(new Set(ids).size!==3)throw new Error('This combination creates a microscopic mesh edge. Change a radius or clearance slightly before exporting.');
    for(let j=0;j<3;j++) {
      const a=ids[j],b=ids[(j+1)%3],key=[a,b].sort().join('|'),edge=edges.get(key)||{count:0,balance:0};
      edge.count++;edge.balance+=a<b?1:-1;edges.set(key,edge);
      if(!neighbors.has(a))neighbors.set(a,new Set());neighbors.get(a).add(b);
      if(!neighbors.has(b))neighbors.set(b,new Set());neighbors.get(b).add(a);
    }
  }
  if([...edges.values()].some(e=>e.count!==2 || e.balance!==0))throw new Error('This combination leaves an unresolved solid seam. Adjust a radius or clearance slightly; export has been stopped.');
  const pending=[neighbors.keys().next().value],seen=new Set();
  while(pending.length) {const v=pending.pop();if(seen.has(v))continue;seen.add(v);for(const n of neighbors.get(v))if(!seen.has(n))pending.push(n);}
  if(seen.size!==neighbors.size)throw new Error('This combination disconnects a feature. Increase the adjoining wall or reduce the opening before exporting.');
  triangleCache.set(solid,result);return result;
}
export function stl(solid) {
  const mesh=triangles(solid),count=mesh.length/9,bytes=new Uint8Array(84+count*50),dv=new DataView(bytes.buffer);
  bytes.set(new TextEncoder().encode('OLED case playground | millimeters | parametric reconstruction'));
  dv.setUint32(80,count,true);
  let minZ=Infinity;for(let i=2;i<mesh.length;i+=3)minZ=Math.min(minZ,mesh[i]);
  for(let t=0;t<count;t++) {
    const offset=84+50*t,i=9*t,a=mesh.slice(i,i+3),b=mesh.slice(i+3,i+6),c=mesh.slice(i+6,i+9);
    const u=b.map((v,j)=>v-a[j]),v=c.map((n,j)=>n-a[j]),n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],length=Math.hypot(...n)||1;
    for(let k=0;k<3;k++)dv.setFloat32(offset+4*k,n[k]/length,true);
    for(let j=0;j<9;j++)dv.setFloat32(offset+12+4*j,mesh[i+j]-(j%3===2?minZ:0),true);
  }
  return bytes;
}
