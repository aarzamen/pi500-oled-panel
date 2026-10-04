import assert from 'node:assert/strict';
import modeling from '@jscad/modeling';
import { buildModel, triangles, DEFAULTS } from './geometry.js';

// These cases exercise the production validation path. Removing its field
// metadata, including unrelated controls, or dropping worker forwarding fails.
const cases = [
  [{pcbPostDiameter:3,pcbHoleDiameter:2},
    'PCB screw holes leave less than 0.8 mm of post wall. Increase post diameter or reduce hole diameter.',
    ['pcbPostDiameter','pcbHoleDiameter']],
  [{edge:1.3},
    'Edge easing needs at least 0.25 mm of face and wall behind it. Reduce edge easing.',
    ['edge','face','wall']],
  [{coverEdge:1.8},
    'Reduce cover edge easing or increase the cover wall.',
    ['coverEdge','coverWall','coverDepth']],
  [{lip:5},
    'The provisional PCB stack intersects the registration lip. Set body depth to at least face + 4.6 mm + lip + 0.1 mm, reduce lip engagement, or disable PCB mounts.',
    ['depth','face','lip','pcbMounts']],
  [{rearOpeningY:15},
    'Rear opening removes the cover perimeter. Move or reduce the opening, enlarge the body, or reduce cover wall thickness.',
    ['rearOpeningX','rearOpeningY','rearOpeningWidth','rearOpeningHeight','width','height','corner','coverWall']],
  [{bezelWidth:1,fit:.6},
    'Sleeve wall is too thin for this fit clearance. Increase bezel width.',
    ['bezelWidth','fit']],
  [{screenStyle:'beveled',screenRaise:0,screenChamfer:2},
    'Screen bevel is deeper than the face. Reduce bevel width or increase face thickness.',
    ['screenChamfer','face','screenRaise']],
  [{buttonPitch:3},
    'Button slots overlap or leave a weak web. Increase button pitch or reduce button height/gap.',
    ['buttonPitch','buttonH','buttonGap']],
  [{screenW:46,screenStyle:'plain',screenRaise:0},
    'Screen is too close to a wall. Enlarge the body or move/reduce that feature.',
    ['screenW','screenH','screenX','screenY','width','height','wall','corner']],
  [{screenW:46,screenStyle:'beveled',screenRaise:0},
    'Screen is too close to a wall. Enlarge the body or move/reduce that feature.',
    ['screenW','screenH','screenX','screenY','screenChamfer','width','height','wall','corner']],
  [{screenW:46,screenStyle:'plain',screenRaise:.6},
    'Screen is too close to a wall. Enlarge the body or move/reduce that feature.',
    ['screenW','screenH','screenX','screenY','screenBezel','screenRaise','width','height','wall','corner']],
];

for (const [input,message,fields] of cases) {
  assert.throws(()=>buildModel(input), error=>{
    assert.equal(error.message,message);
    assert.deepEqual(error.fields,fields);
    assert.equal(new Set(error.fields).size,error.fields.length);
    assert.ok(error.fields.every(key=>Object.hasOwn(DEFAULTS,key)));
    return true;
  });
}

// Unknown triangulation causes must not invent a dimension diagnosis.
assert.throws(()=>triangles(modeling.geometries.geom3.create([])), error=>{
  assert.match(error.message,/triangulation failed/);
  assert.ok(!error.fields || error.fields.length===0);
  return true;
});

// Supply only the worker transport boundary; all model/error code stays real.
const previousSelf=globalThis.self, messages=[];
try {
  globalThis.self={postMessage:message=>messages.push(message)};
  await import('./worker.js');
  self.onmessage({data:{type:'build',state:cases[0][0],revision:17}});
  assert.deepEqual(messages.pop(),{
    type:'error',revision:17,request:undefined,message:cases[0][1],fields:cases[0][2]
  });
  self.onmessage({data:{type:'export',revision:18,request:9,parts:['front']}});
  assert.deepEqual(messages.pop(),{
    type:'error',revision:18,request:9,
    message:'Wait for the current design to finish building before exporting.',fields:[]
  });
} finally {
  if(previousSelf===undefined)delete globalThis.self;else globalThis.self=previousSelf;
}

console.log(`Dimension feedback: ${cases.length} exact validation mappings, unknown-cause fallback, and worker forwarding passed.`);
