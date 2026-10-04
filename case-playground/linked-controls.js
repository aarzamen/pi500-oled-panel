import { normalize } from './geometry.js';

export const GLOBAL_GROUPS = Object.freeze({
  wall:Object.freeze(['wall','face','coverWall','bezelWidth','screenBezel']),
  rounding:Object.freeze(['corner','edge','coverEdge','bezelRadius','screenRadius','buttonRadius','rearOpeningRadius'])
});
export const GLOBAL_RANGES = Object.freeze({
  wall:Object.freeze({min:.75,max:1.5}),
  rounding:Object.freeze({min:.5,max:1.5})
});
const LIMITS={wall:[1,5],face:[.8,4],coverWall:[1,5],bezelWidth:[1,8],screenBezel:[0,4],corner:[0,12],edge:[0,2],coverEdge:[0,2.5],bezelRadius:[0,15],screenRadius:[0,5],buttonRadius:[0,3],rearOpeningRadius:[0,6]};
const close=(a,b)=>Math.abs(a-b)<1e-8;
const neat=n=>Math.round(n*1e6)/1e6;
function inside(x,y,w,h,r,margin) {
  w-=margin;h-=margin;r=Math.max(0,r-margin);
  return Math.abs(x)<=w+1e-8 && Math.abs(y)<=h+1e-8 && Math.hypot(Math.max(0,Math.abs(x)-(w-r)),Math.max(0,Math.abs(y)-(h-r)))<=r+1e-8;
}
function corners(x,y,w,h){return [-1,1].flatMap(dx=>[-1,1].map(dy=>[x+dx*w/2,y+dy*h/2]));}

/**
 * Link structural wall dimensions or roundness using an immutable preset baseline.
 * factor is a ratio (1 means 100%). Does not mutate either argument.
 *
 * Result: {state, adjustments, changedKeys}. adjustments lists every dependent
 * clamp/enlargement with {key,from,to,reason}; ordinary linked changes are in
 * changedKeys. Shell dimensions only grow to preserve clearance. Returning to
 * 100% restores the linked values; restoring the whole preset restores its size.
 * Mechanical fits, post/hole sizes, positions, spring webs and clip thickness
 * stay independent. No global value implies identical thickness/radius everywhere.
 */
export function applyGlobal(base,input,kind,factor) {
  if(!Object.hasOwn(GLOBAL_GROUPS,kind))throw new Error('Unknown linked control kind; use wall or rounding.');
  if(typeof factor!=='number' || !Number.isFinite(factor))throw new Error('The linked control factor must be finite.');
  const range=GLOBAL_RANGES[kind];
  if(factor<range.min || factor>range.max)throw new Error(`${kind==='wall'?'Wall':'Rounding'} scale must stay in the ${range.min*100}–${range.max*100}% range.`);
  const b=normalize(base),original=normalize(input),s={...original},adjustments=[];
  const note=(key,value,reason)=>{
    value=neat(value);if(close(value,s[key]))return;
    adjustments.push({key,from:s[key],to:value,reason});s[key]=value;
  };
  for(const key of GLOBAL_GROUPS[kind]) {
    // The outer sleeve's actual radial wall is its width minus fit clearance.
    const target=key==='bezelWidth'?s.fit+(b.bezelWidth-b.fit)*factor:b[key]*factor;
    const [lo,hi]=LIMITS[key];s[key]=neat(target);
    if(target<lo || target>hi)note(key,Math.max(lo,Math.min(hi,target)),'Limited to the supported dimension range.');
  }
  if(s.closure==='screw')note('wall',Math.max(s.wall,1.85-s.fit),'Screw-ear clearance sets a minimum body wall thickness.');
  // Easing cannot consume a complete face/wall. The small safety reserve also
  // avoids equality at the solid generator's strict minimum-thickness checks.
  note('edge',Math.floor((Math.min(s.edge,s.face-.3,s.wall-.3)+1e-9)*20)/20,'Front edge easing uses 0.05 mm steps and leaves material behind it.');
  note('coverEdge',Math.floor((Math.min(s.coverEdge,s.coverWall-.3,s.coverDepth-.55)+1e-9)*20)/20,'Rear edge easing uses 0.05 mm steps and leaves material behind it.');
  note('bezelRadius',Math.min(s.bezelRadius,s.corner+s.bezelWidth-.4),'Sleeve corner radius limited to preserve its wall.');
  note('screenRadius',Math.max(s.screenStyle==='beveled'?.05:0,Math.min(s.screenRadius,Math.min(s.screenW,s.screenH)/2-.1)),'Screen radius limited to fit the opening.');
  note('buttonRadius',Math.max(s.buttonStyle==='strip'?.05:0,Math.min(s.buttonRadius,Math.min(s.buttonW,s.buttonH)/2-.1)),'Button radius limited to fit the opening.');
  note('rearOpeningRadius',Math.min(s.rearOpeningRadius,Math.min(s.rearOpeningWidth,s.rearOpeningHeight)/2-.1),'Rear opening radius limited to fit the opening.');
  if(s.screenStyle==='beveled') {
    note('screenChamfer',Math.min(s.screenChamfer,s.face+s.screenRaise),'Screen bevel reduced to fit the front thickness.');
    if(s.screenRaise>0 && s.screenBezel<s.screenChamfer+.35)throw new Error('The linked wall scale leaves too little raised screen rim. Reduce screen raise or bevel width in Advanced.');
  }
  if(s.bezelOn && s.bezelWidth<s.fit+.7)throw new Error('The linked wall scale leaves too little sleeve material. Increase wall scale or sleeve width.');
  if(s.closure==='snap' && (s.wall<1.25 || s.hook>s.wall-.85))throw new Error('The linked wall scale is too thin for the selected snap hook. Increase wall scale or reduce hook projection in Advanced.');
  if(s.coverDepth<=s.coverWall+1)note('coverDepth',s.coverWall+1.05,'Rear depth increased to keep the cover hollow.');

  const extra=Math.max(s.screenRaise>0?s.screenBezel:0,s.screenStyle==='beveled'?s.screenChamfer:0);
  const faceRects=[[s.screenX,s.screenY,s.screenW+2*extra,s.screenH+2*extra]];
  const buttonExtra=s.buttonStyle==='strip'?1.2:2*s.buttonGap;
  for(let i=0;i<4;i++)faceRects.push([s.buttonX,s.buttonY-i*s.buttonPitch,s.buttonW+buttonExtra,s.buttonH+buttonExtra]);
  const [sx,sy,sw,sh]=faceRects[0];
  for(const [x,y,w,h]of faceRects.slice(1))if(Math.abs(x-sx)<(w+sw)/2+.45 && Math.abs(y-sy)<(h+sh)/2+.45)throw new Error('The linked wall scale crowds the screen rim and buttons. Reduce wall scale or move those features in Advanced.');

  const checks=[];
  for(const rect of faceRects)for(const [x,y]of corners(...rect))checks.push({x,y,inset:0,margin:s.wall+.3});
  if(s.buttonStyle==='strip')for(let i=0;i<4;i++)for(const [x,y]of corners(s.buttonX,s.buttonY-i*s.buttonPitch,s.buttonW+2.2,s.buttonH+2.2))checks.push({x,y,inset:s.wall,margin:.2});
  if(s.pcbMounts) {
    for(const x of [-22.5,22.5])for(const y of [-14,14])checks.push({x,y,inset:s.wall,margin:.1});
    for(const x of [-20,20])for(const y of [-11.5,11.5])checks.push({x,y,inset:s.wall,margin:s.pcbPostDiameter/2+.1});
  }
  for(const [x,y]of corners(s.rearOpeningX,s.rearOpeningY,s.rearOpeningWidth,s.rearOpeningHeight)) {
    checks.push({x,y,inset:0,margin:s.coverWall+.35});checks.push({x,y,inset:s.wall,margin:.15});
  }
  let width=s.width,height=s.height;
  if(s.closure==='snap') {
    if(s.pcbMounts)width=Math.max(width,2*(22.7+s.wall+s.fit+s.tabThickness-.45)+.02);
    height=Math.max(height,s.tabWidth+2*s.wall+2*s.corner+2.02);
  }
  width=Math.max(width,2*s.corner+2.02);height=Math.max(height,2*s.corner+2.02);
  // Grow only when the existing advanced envelope cannot contain the fixed
  // features. Uniform 0.05 mm steps keep corner growth symmetric and reproducible.
  for(let i=0;checks.some(c=>!inside(c.x,c.y,width/2-c.inset,height/2-c.inset,Math.max(0,s.corner-c.inset),c.margin));i++) {
    if(i>2000 || width>=100 || height>=80)throw new Error('These linked settings need a body beyond the supported size. Reduce the scale or revise the feature layout.');
    const needWidth=checks.some(c=>Math.abs(c.x)>width/2-c.inset-c.margin+1e-8);
    const needHeight=checks.some(c=>Math.abs(c.y)>height/2-c.inset-c.margin+1e-8);
    if(needWidth || !needHeight)width+=.05;
    if(needHeight || !needWidth)height+=.05;
  }
  note('width',width,'Body width increased to preserve PCB, connector and feature clearance.');
  note('height',height,'Body height increased to preserve PCB, connector and feature clearance.');
  let depth=Math.max(s.depth,s.face+1.01,s.face+s.lip+.51);
  if(s.pcbMounts)depth=Math.max(depth,s.face+4.6+s.lip+.1);
  if(s.closure==='snap')depth=Math.max(depth,s.face+2.7);
  if(depth>20 || width>100 || height>80)throw new Error('These linked settings exceed the supported body dimensions. Reduce the scale.');
  note('depth',depth,'Body depth increased to preserve the PCB stack and locating-lip clearance.');
  return {state:s,adjustments,changedKeys:Object.keys(s).filter(key=>!close(s[key],original[key]) && s[key]!==original[key])};
}
