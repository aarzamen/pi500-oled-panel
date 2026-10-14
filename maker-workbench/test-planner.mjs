import test from 'node:test';
import assert from 'node:assert/strict';
import nativeParameters from '../mechanical/cad-rebuild/source/parameters.json' with { type: 'json' };
import {
  DEFAULTS, PARAMETER_META, getDefaultState, getPreset, normalizeState,
  evaluatePlan, makeHandoff, makeSettings,
} from './planner.js';

function withParameters(overrides) {
  const state = getDefaultState();
  Object.assign(state.parameters, overrides);
  return state;
}

function hasError(plan, field) {
  return plan.warnings.some(warning => warning.severity === 'error' && warning.fields.includes(field));
}

test('base plan preserves native generator inputs and the complete released stack', () => {
  const state = getDefaultState();
  const plan = evaluatePlan(state);
  assert.deepEqual(DEFAULTS, nativeParameters);
  assert.deepEqual(plan.parameters, nativeParameters);
  assert.equal(state.back, 'back-dual-knockouts');
  assert.equal(state.showStand, true);
  assert.equal(state.exploded, false);
  assert.deepEqual(plan.dimensions, {
    caseWidth: 51.3, caseHeight: 33.4, caseDepth: 12.2,
    pcbFront: 4.55, pcbBack: 6.15, pinRear: 10.55, buttonRest: 1.9,
  });
  assert.equal(plan.valid, true);
  assert.equal(plan.hasChanges, false);
  assert.deepEqual(plan.changed, []);
  assert.ok(plan.warnings.some(warning => /physical.*unverified|unverified.*physical/i.test(warning.message)));
});

test('changing any part of the cap stack moves the board and rounds depth to a full layer', () => {
  const plan = evaluatePlan(withParameters({
    face: 1.4, measured_switch_top_height: 3.2, cap_flange_depth: 0.6, cap_release_gap: 0.5,
  }));
  assert.equal(plan.dimensions.pcbFront, 5.7);
  assert.equal(plan.dimensions.pcbBack, 7.3);
  assert.equal(plan.dimensions.buttonRest, 2.5);
  assert.equal(plan.dimensions.pinRear, 11.7);
  assert.equal(plan.dimensions.caseDepth, 13.4);
  assert.equal(plan.hasChanges, true);
  assert.ok(plan.changed.includes('cap_flange_depth'));
});

test('all purpose presets reuse base geometry and return independent state', () => {
  for (const id of ['pi-status', 'bench-controls', 'sensor-station', 'custom-board']) {
    const state = getPreset(id);
    const plan = evaluatePlan(state);
    assert.equal(state.useCase, id);
    assert.equal(plan.dimensions.caseWidth, 51.3);
    assert.equal(plan.dimensions.caseDepth, 12.2);
    assert.equal(plan.hasChanges, false);
    state.parameters.button_centers_y[0] = 999;
    assert.equal(getPreset(id).parameters.button_centers_y[0], -8.7);
  }
  assert.equal(getPreset('unknown').useCase, 'pi-status');
});

test('normalization rejects malformed primitives, inherited keys and injected provenance', () => {
  const bad = JSON.parse('{"useCase":"<script>","back":"../private","exploded":"true","showStand":0,"parameters":{"wall":{"valueOf":"2"},"pcb_thickness":null,"post_diameter":"4","corner_radius":"NaN","__proto__":{"polluted":true},"physical_calibration":{"switch_top_height":99},"calibration_complete":true,"unexpected":3}}');
  const state = normalizeState(bad);
  assert.deepEqual(state, getDefaultState());
  assert.equal({}.polluted, undefined);
  assert.equal(normalizeState(null).useCase, 'pi-status');
  assert.equal(normalizeState([]).useCase, 'pi-status');
  assert.equal(normalizeState('invalid JSON').useCase, 'pi-status');
  const inherited = { parameters: Object.create({ wall: 9 }) };
  assert.equal(normalizeState(inherited).parameters.wall, 1.6);
  assert.equal(normalizeState({ parameters: { wall: Infinity, pcb_thickness: NaN } }).parameters.wall, 1.6);
});

test('finite physically impossible choices stay visible and invalidate the plan', () => {
  const state = normalizeState(withParameters({ wall: 4, mount_hole_pitch_x: 50, pilot_diameter: 4 }));
  assert.equal(state.parameters.wall, 4);
  assert.equal(state.parameters.mount_hole_pitch_x, 50);
  const plan = evaluatePlan(state);
  assert.equal(plan.valid, false);
  assert.ok(hasError(plan, 'wall'));
  assert.ok(hasError(plan, 'mount_hole_pitch_x'));
  assert.ok(hasError(plan, 'pilot_diameter'));
});

test('compressed latches reject a cavity that fits the board but loses insertion clearance', () => {
  const plan = evaluatePlan(withParameters({ case_width: 50.5 }));
  assert.equal(plan.valid, false);
  assert.ok(plan.warnings.some(warning => warning.severity === 'error' && /compressed.*latch|compressed.*snap/i.test(warning.message)));
});

test('board envelope, key retention and connector apertures expose their coupled fields', () => {
  const fixtures = [
    [{ case_height: 30 }, 'case_height'],
    [{ cap_side_clearance: 1.5 }, 'cap_side_clearance'],
    [{ knockout_width: 19 }, 'knockout_width'],
    [{ knockout_height: 3 }, 'knockout_height'],
    [{ glass_width: 50 }, 'glass_width'],
    [{ button_x: 30 }, 'button_x'],
    [{ pcb_thickness: 4 }, 'pcb_thickness'],
    [{ measured_switch_top_height: 1.6 }, 'measured_switch_top_height'],
    [{ pilot_depth: 5 }, 'pilot_depth'],
    [{ corner_radius: 20 }, 'corner_radius'],
    [{ stand_tilt_degrees: 45 }, 'stand_tilt_degrees'],
    [{ post_base_diameter: 10 }, 'post_base_diameter'],
    [{ cap_width: 1 }, 'cap_width'],
  ];
  for (const [parameters, field] of fixtures) {
    const plan = evaluatePlan(withParameters(parameters));
    assert.equal(plan.valid, false, field);
    assert.ok(hasError(plan, field), field);
  }
});

test('rounded connector corners reject a port whose rectangular envelope alone would fit', () => {
  const plan = evaluatePlan(withParameters({ knockout_width: 21, knockout_height: 4.4, knockout_radius: 1.2 }));
  assert.equal(plan.valid, false);
  assert.ok(hasError(plan, 'knockout_radius'));
});

test('extreme finite inputs cannot expose infinite calculated dimensions', () => {
  const plan = evaluatePlan(withParameters({ case_width: 1e308, pcb_thickness: 1e308, measured_switch_top_height: 1e308 }));
  assert.equal(plan.valid, false);
  assert.ok(Object.values(plan.dimensions).every(value => value === null || Number.isFinite(value)));
});

test('a small outer rounding flags the native minimum inner radius without claiming print failure', () => {
  const plan = evaluatePlan(withParameters({ corner_radius: 1.2 }));
  assert.ok(plan.warnings.some(warning => warning.fields.includes('corner_radius') && /radius|rounding/i.test(warning.message)));
});

test('drafts preserve original measurements as reference and remove calibrated claims', () => {
  const state = withParameters({ measured_switch_top_height: 3.1, mount_hole_pitch_x: 39 });
  const plan = evaluatePlan(state);
  assert.equal(plan.parameters.calibration_complete, false);
  assert.equal(plan.parameters.physical_calibration.switch_top_height, 2.65);
  assert.equal(plan.parameters.physical_calibration.mount_hole_pitch_x, 40);
  assert.match(plan.parameters.physical_calibration.applies_to, /original.*module/i);
  assert.equal(plan.parameters.planning_overrides.verified, false);
  assert.deepEqual(plan.parameters.planning_overrides.changed_parameters.measured_switch_top_height, { original: 2.65, value: 3.1 });
  assert.equal(evaluatePlan(getPreset('custom-board')).parameters.calibration_complete, false);
});

test('settings roundtrip preserves purpose, view, planning values and validated provenance', () => {
  const state = withParameters({ wall: 1.7, cap_release_gap: 0.35 });
  state.useCase = 'bench-controls';
  state.back = 'back-lower-open';
  state.exploded = true;
  state.showStand = false;
  const settings = JSON.parse(makeSettings(state));
  assert.equal(settings.schemaVersion, 1);
  assert.deepEqual(normalizeState(settings), normalizeState(state));
  assert.equal(settings.state.parameters.calibration_complete, false);
  assert.equal(settings.sourceSha256, nativeParameters.source_sha256);
});

test('metadata exposes the requested controls with real native defaults and readable groups', () => {
  const keys = new Set(PARAMETER_META.map(field => field.key));
  for (const key of [
    'wall', 'corner_radius', 'pcb_keepout_width', 'pcb_keepout_height', 'pcb_thickness',
    'measured_switch_top_height', 'mount_hole_pitch_x', 'mount_hole_pitch_y',
    'post_diameter', 'pilot_diameter', 'cap_side_clearance', 'cap_release_gap',
    'knockout_width', 'knockout_height', 'stand_tilt_degrees', 'stand_clearance',
  ]) assert.ok(keys.has(key), key);
  for (const field of PARAMETER_META) {
    assert.ok(['Basic', 'Board', 'Mounts', 'Detail'].includes(field.group));
    assert.ok(Number.isFinite(DEFAULTS[field.key]));
    assert.ok(field.min <= DEFAULTS[field.key] && DEFAULTS[field.key] <= field.max, field.key);
    assert.ok(field.step > 0);
  }
});

test('handoff carries selected purpose, actual changes, full generator JSON and exact measurement datum', () => {
  const state = getPreset('sensor-station');
  state.parameters.wall = 1.8;
  const handoff = makeHandoff(state);
  assert.match(handoff, /sensor station/i);
  assert.match(handoff, /wall.*1\.6.*1\.8/);
  assert.match(handoff, /4\.75 mm.*nearest fixed.*edge/i);
  assert.match(handoff, /2\.65.*1\.8/);
  assert.match(handoff, /40.*24.*approximate|approximately.*40.*24/i);
  assert.match(handoff, /180.*X|X.*180/);
  assert.match(handoff, /reflection/i);
  assert.match(handoff, /DuPont/);
  assert.match(handoff, /B0GWQPY2C7/);
  assert.match(handoff, /B0GWTWPMNT/);
  assert.match(handoff, /four.wire.*unverified|four.wire.*not.*verified/i);
  assert.match(handoff, /Hellfire/);
  assert.match(handoff, /redistribut/i);
  assert.match(handoff, /companion.*future|future.*companion/i);
  assert.match(handoff, /uv venv --python 3\.12/);
  assert.match(handoff, /source\/export_design\.py/);
  assert.match(handoff, /https:\/\/github\.com\/aarzamen\/pi500-oled-panel/);
  assert.doesNotMatch(handoff, /\/Users\/ama|192\.168\.|password|credential/i);
  const json = handoff.match(/```json\n([\s\S]*?)\n```/);
  assert.ok(json);
  const parameters = JSON.parse(json[1]);
  assert.equal(parameters.wall, 1.8);
  assert.equal(parameters.calibration_complete, false);
  assert.equal(parameters.physical_calibration.switch_top_height, 2.65);
});
