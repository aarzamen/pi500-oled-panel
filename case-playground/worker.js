import { DEFAULTS, normalize, buildModel, triangles, stl } from './geometry.js';
import modeling from '@jscad/modeling';
let current=null, revision=-1;
self.onmessage=({data})=>{
 try{
  if(data.type==='build'){
   const start=performance.now(); const model=buildModel(data.state); current=model;revision=data.revision;
   const parts={}, transfers=[];
   for(const [name,solid] of Object.entries(model.parts)){
    if(!solid)continue;
    const positions=new Float32Array(triangles(solid));
    const bounds=modeling.measurements.measureBoundingBox(solid);
    parts[name]={positions,bounds,volume:modeling.measurements.measureVolume(solid)};transfers.push(positions.buffer);
   }
   self.postMessage({type:'built',revision,state:model.state,warnings:model.warnings,dimensions:model.dimensions,parts,ms:performance.now()-start},transfers);
  }else if(data.type==='export'){
   if(!current||data.revision!==revision)throw new Error('Wait for the current design to finish building before exporting.');
   const result={},transfers=[];
   for(const name of data.parts){if(current.parts[name]){const solid = name === 'front' ? current.parts[name] : modeling.transforms.rotateX(Math.PI, current.parts[name]);const bytes=stl(solid);result[name]=bytes;transfers.push(bytes.buffer);}}
   self.postMessage({type:'exported',request:data.request,parts:result},transfers);
  }
 }catch(error){self.postMessage({type:'error',revision:data.revision,request:data.request,message:error.message||String(error)});}
};
