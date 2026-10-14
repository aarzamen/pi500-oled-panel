import nativeParameters from '../mechanical/cad-rebuild/source/parameters.json' with { type: 'json' };

const clone = value => JSON.parse(JSON.stringify(value));
function freezeTree(value) {
  if (value && typeof value === 'object') {
    Object.values(value).forEach(freezeTree);
    Object.freeze(value);
  }
  return value;
}

/** The complete, unchanged published native generator inputs, in millimeters. */
export const DEFAULTS = freezeTree(clone(nativeParameters));

const field = (key, label, min, max, step, group, help) => ({ key, label, min, max, step, group, help });
export const PARAMETER_META = freezeTree([
  field('case_width', 'Case width', 40, 90, 0.1, 'Basic', 'Outer width. The board and compressed latch arms must both fit inside it.'),
  field('case_height', 'Case height', 28, 70, 0.1, 'Basic', 'Outer height. Changing it also changes the matched stand.'),
  field('wall', 'Wall thickness', 0.8, 4, 0.1, 'Basic', 'Thicker walls reduce the PCB cavity and latch insertion clearance.'),
  field('corner_radius', 'Corner rounding', 0.5, 15, 0.1, 'Basic', 'Outer radius. The native inner cavity keeps at least a 0.5 mm radius.'),
  field('stand_tilt_degrees', 'Stand rearward lean', 0, 30, 1, 'Basic', 'Degrees. The native cradle supports plans from 0° to 30°; stability still needs a print.'),
  field('stand_clearance', 'Stand clearance per side', 0.1, 1, 0.05, 'Basic', 'Added on each side of the calculated body depth. Regenerate the stand with the case.'),
  field('pcb_keepout_width', 'PCB envelope width', 20, 75, 0.01, 'Board', '44.53 mm is the seller envelope, not a measured physical outline. Button X uses a separate 44 mm reference.'),
  field('pcb_keepout_height', 'PCB envelope height', 15, 55, 0.01, 'Board', '27.66 mm is the seller envelope; the approximate community model is 27 mm tall.'),
  field('pcb_thickness', 'PCB thickness', 0.6, 4, 0.05, 'Board', '1.6 mm is a community-model estimate. Confirm the physical board before changing its supports.'),
  field('measured_switch_top_height', 'Released button peak above PCB', 0.8, 5, 0.05, 'Board', 'Original module measured 2.65 mm. A new slider value is a planning override until measured.'),
  field('measured_switch_fixed_height', 'Fixed housing above PCB', 0.4, 4, 0.05, 'Board', 'Original module measured 1.8 mm. Keep this separate from the moving actuator peak.'),
  field('header_rear_projection', 'Bare pin rear projection', 1, 12, 0.1, 'Board', 'Estimated distance behind the PCB. The calculated closed depth clears bare pins, not attached DuPont plugs.'),
  field('mount_hole_pitch_x', 'Mount pitch across', 12, 70, 0.1, 'Mounts', 'Original board approximately 40 mm; precision was limited by a low caliper battery.'),
  field('mount_hole_pitch_y', 'Mount pitch vertically', 10, 55, 0.1, 'Mounts', 'Original board approximately 24 mm. Confirm centers on the actual board.'),
  field('mount_hole_y_offset', 'Mount vertical offset', -10, 10, 0.1, 'Mounts', 'Moves both rows together. Check the pilots stay within the PCB envelope.'),
  field('post_diameter', 'Post outside diameter', 2.4, 8, 0.1, 'Mounts', 'Must leave printed material around the blind screw pilot.'),
  field('post_base_diameter', 'Post base diameter', 3, 10, 0.1, 'Mounts', 'Raised support base. Check it against nearby display and key openings.'),
  field('pilot_diameter', 'Screw pilot diameter', 0.8, 3.5, 0.05, 'Mounts', 'A modeled blind hole, not a guaranteed screw thread size. Try a short screw in the printed material.'),
  field('post_height', 'Exposed post height', 1, 6, 0.05, 'Mounts', 'Native source recalculates the raised base from the complete button stack; changing this alone cannot move the PCB.'),
  field('pilot_depth', 'Blind pilot depth', 0.5, 5, 0.1, 'Mounts', 'Must stay above the front face. Check screw bottoming and board clamping physically.'),
  field('face', 'Front face thickness', 0.8, 3, 0.1, 'Detail', 'Part of the released cap stack that sets the PCB front position.'),
  field('cover_face', 'Rear face thickness', 0.8, 3, 0.1, 'Detail', 'Adds to total closed depth after pin projection and rear clearance.'),
  field('cover_seam_z', 'Cover seam depth', 5, 15, 0.1, 'Detail', 'Must remain behind the PCB and leave room for the locating lip.'),
  field('cap_side_clearance', 'Key clearance per side', 0.1, 1.5, 0.05, 'Detail', 'Widens each aperture. Too much removes the retaining overlap or material between keys.'),
  field('cap_release_gap', 'Released cap gap', 0.1, 1.2, 0.05, 'Detail', 'Clearance between the front face and retaining flange; included in the complete stack.'),
  field('cap_flange_depth', 'Retaining flange thickness', 0.2, 1.2, 0.05, 'Detail', 'Included in PCB depth. Regenerate and check every cap when it changes.'),
  field('cap_travel_check', 'Inward key travel check', 0.1, 0.8, 0.05, 'Detail', 'Geometric travel allowance; actual actuation force and return still need a physical test.'),
  field('knockout_width', 'Rear panel width', 15, 35, 0.1, 'Detail', 'Must clear the estimated eight-position connector envelope, 8 × 2.54 = 20.32 mm.'),
  field('knockout_height', 'Rear panel height', 3, 10, 0.1, 'Detail', 'The reference straight connector envelope is 4.2 mm tall. Confirm all eight actual housings.'),
  field('knockout_membrane', 'Intact panel skin', 0.2, 0.8, 0.05, 'Detail', 'Outer skin after the inside score. Open the required panel with the cover detached.'),
  field('layer_height', 'Depth rounding layer', 0.1, 0.32, 0.01, 'Detail', 'Calculated closed depth rounds upward to a whole layer. Slice for your own printer.'),
]);

const PURPOSES = freezeTree({
  'pi-status': { label: 'Pi status panel', direction: 'Use the measured four-button OLED as a local Pi status and navigation panel. Start with the documented standalone runtime and verify wiring on the selected host.' },
  'bench-controls': { label: 'Bench controls', direction: 'Plan a compact four-button bench interface for a separate controller or workload. Define each button action and the display content before adding host-specific software.' },
  'sensor-station': { label: 'Sensor station', direction: 'Plan a small sensor readout with four local navigation buttons. Specify sensors, units, update cadence and failure display as a separate software task.' },
  'custom-board': { label: 'Custom board plan', direction: 'Create a separate measured profile for a new board. Recheck the PCB, display, keys and connector geometry rather than scaling this enclosure as a whole.' },
});
const BACKS = new Set(['back-dual-knockouts', 'back-lower-open', 'back-upper-open']);
const NUMERIC_KEYS = Object.keys(DEFAULTS).filter(key => typeof DEFAULTS[key] === 'number' && !key.startsWith('source_'));
const ARRAY_KEYS = ['button_centers_y'];
const own = (value, key) => Object.hasOwn(value, key);
const record = value => value !== null && typeof value === 'object' && !Array.isArray(value)
  && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null);
const finite = value => typeof value === 'number' && Number.isFinite(value);
const round = value => Number.isFinite(value) ? Number(value.toFixed(6)) : null;
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const changedKeys = parameters => [...NUMERIC_KEYS, ...ARRAY_KEYS].filter(key => !same(parameters[key], DEFAULTS[key]));
const ORIGINAL_MODULE = 'Original purchased ACEIRMC SSD1315 / HW-937AB module; these are reference measurements, not measurements of this draft or another board.';

export function getDefaultState() {
  return { useCase: 'pi-status', back: 'back-dual-knockouts', exploded: false, showStand: true, parameters: clone(DEFAULTS) };
}

export function getPreset(id) {
  return normalizeState({ useCase: typeof id === 'string' && own(PURPOSES, id) ? id : 'pi-status' });
}

/** Reject malformed values without coercion; preserve finite invalid geometry for diagnostics. */
export function normalizeState(input) {
  let source = record(input) ? input : {};
  if (own(source, 'state') && record(source.state)) source = source.state;
  const state = getDefaultState();
  if (own(source, 'useCase') && typeof source.useCase === 'string' && own(PURPOSES, source.useCase)) state.useCase = source.useCase;
  if (own(source, 'back') && typeof source.back === 'string' && BACKS.has(source.back)) state.back = source.back;
  if (own(source, 'exploded') && typeof source.exploded === 'boolean') state.exploded = source.exploded;
  if (own(source, 'showStand') && typeof source.showStand === 'boolean') state.showStand = source.showStand;
  if (own(source, 'parameters') && record(source.parameters)) {
    for (const key of NUMERIC_KEYS) {
      if (own(source.parameters, key) && finite(source.parameters[key])) state.parameters[key] = source.parameters[key];
    }
    for (const key of ARRAY_KEYS) {
      const value = source.parameters[key];
      if (own(source.parameters, key) && Array.isArray(value) && value.length === DEFAULTS[key].length && value.every(finite)) state.parameters[key] = [...value];
    }
  }
  const changed = changedKeys(state.parameters);
  if (changed.length || state.useCase === 'custom-board') {
    state.parameters.calibration_complete = false;
    state.parameters.physical_calibration.applies_to = ORIGINAL_MODULE;
    state.parameters.planning_overrides = {
      verified: false,
      use_case: state.useCase,
      changed_parameters: Object.fromEntries(changed.map(key => [key, { original: clone(DEFAULTS[key]), value: clone(state.parameters[key]) }])),
    };
  }
  return state;
}

const rect = (x, y, width, height) => ({ left: x - width / 2, right: x + width / 2, bottom: y - height / 2, top: y + height / 2 });
const overlap = (a, b) => a.left < b.right && a.right > b.left && a.bottom < b.top && a.top > b.bottom;
const circleOverlaps = (x, y, radius, rectangle) => {
  const nearestX = Math.max(rectangle.left, Math.min(x, rectangle.right));
  const nearestY = Math.max(rectangle.bottom, Math.min(y, rectangle.top));
  return (x - nearestX) ** 2 + (y - nearestY) ** 2 < radius ** 2;
};
function insideRounded(rectangle, width, height, radius) {
  const halfWidth = width / 2, halfHeight = height / 2;
  if (width <= 0 || height <= 0 || radius < 0 || radius >= Math.min(width, height) / 2) return false;
  return [rectangle.left, rectangle.right].every(x => [rectangle.bottom, rectangle.top].every(y => {
    if (Math.abs(x) > halfWidth || Math.abs(y) > halfHeight) return false;
    const dx = Math.max(0, Math.abs(x) - (halfWidth - radius));
    const dy = Math.max(0, Math.abs(y) - (halfHeight - radius));
    return dx * dx + dy * dy <= radius * radius + 1e-9;
  }));
}

/** Dimensional preflight only. Native CAD collision checks and physical fit remain separate. */
export function evaluatePlan(input) {
  const state = normalizeState(input), p = state.parameters;
  const changed = changedKeys(p), warnings = [];
  const add = (severity, fields, message) => warnings.push({ severity, fields: [...new Set(fields)], message });
  const pcbFront = p.face + p.measured_switch_top_height + p.cap_flange_depth + p.cap_release_gap;
  const pcbBack = pcbFront + p.pcb_thickness;
  const pinRear = pcbBack + p.header_rear_projection;
  const minimumDepth = pinRear + p.rear_clearance + p.cover_face;
  const caseDepth = p.layer_height > 0 ? Math.ceil((minimumDepth - 1e-9) / p.layer_height) * p.layer_height : NaN;
  const buttonRest = p.face + p.cap_release_gap + p.cap_flange_depth;
  const dimensions = {
    caseWidth: round(p.case_width), caseHeight: round(p.case_height), caseDepth: round(caseDepth),
    pcbFront: round(pcbFront), pcbBack: round(pcbBack), pinRear: round(pinRear), buttonRest: round(buttonRest),
  };

  for (const meta of PARAMETER_META) {
    if (p[meta.key] < meta.min || p[meta.key] > meta.max) add('error', [meta.key], `${meta.label} is outside this workbench's ${meta.min}–${meta.max} planning range${meta.key === 'stand_tilt_degrees' ? ' in degrees' : ' in mm'}. Keep the entered value visible and revise it before regeneration.`);
  }
  const allowZero = new Set(['mount_hole_y_offset', 'button_x', 'glass_center_x', 'glass_center_y', 'header_x', 'header_y', 'stand_tilt_degrees', 'window_overlap_x', 'window_overlap_y', 'rear_clearance']);
  for (const key of NUMERIC_KEYS) {
    if (!allowZero.has(key) && p[key] <= 0 && !warnings.some(warning => warning.severity === 'error' && warning.fields.includes(key))) add('error', [key], `${key.replaceAll('_', ' ')} must be positive for the native generator.`);
  }
  for (const key of ['window_overlap_x', 'window_overlap_y', 'rear_clearance']) {
    if (p[key] < 0) add('error', [key], `${key.replaceAll('_', ' ')} cannot be negative.`);
  }
  if (Object.values(dimensions).some(value => value === null)) add('error', ['layer_height', 'measured_switch_top_height', 'pcb_thickness'], 'The stack calculation exceeds a finite planning dimension. Reduce the inputs before continuing.');

  const innerWidth = p.case_width - 2 * p.wall, innerHeight = p.case_height - 2 * p.wall;
  const innerRadius = Math.max(0.5, p.corner_radius - p.wall);
  if (p.corner_radius >= Math.min(p.case_width, p.case_height) / 2 || innerRadius >= Math.min(innerWidth, innerHeight) / 2) add('error', ['corner_radius', 'wall', 'case_width', 'case_height'], 'The corner radius leaves no valid rounded native cavity. Reduce rounding or increase the case dimensions.');
  else if (p.corner_radius < p.wall + 0.5) add('warning', ['corner_radius', 'wall'], `The native cavity keeps a minimum 0.5 mm inner radius. Use at least ${round(p.wall + 0.5)} mm outer rounding for a consistent rounded wall; verify this corner in regenerated CAD.`);
  if (innerWidth <= p.pcb_keepout_width || innerHeight <= p.pcb_keepout_height
      || !insideRounded(rect(0, 0, p.pcb_keepout_width, p.pcb_keepout_height), innerWidth, innerHeight, innerRadius)) add('error', ['case_width', 'case_height', 'wall', 'corner_radius', 'pcb_keepout_width', 'pcb_keepout_height'], 'The conservative PCB envelope reaches the cavity wall or rounded corners. Increase the case or reduce wall thickness after checking the real board.');
  const compressedClearance = innerWidth / 2 - p.fit - p.snap_thickness - (p.fit + p.snap_engagement) - p.pcb_keepout_width / 2;
  if (compressedClearance < 0.25 - 1e-9) add('error', ['case_width', 'wall', 'pcb_keepout_width', 'fit', 'snap_thickness', 'snap_engagement'], `Compressed latch-arm clearance is ${round(compressedClearance)} mm per side. The native generator requires at least 0.25 mm; board width and latch deflection must be solved together.`);

  const pilotRadius = p.pilot_diameter / 2;
  if (p.mount_hole_pitch_x / 2 + pilotRadius >= p.pcb_keepout_width / 2
      || p.mount_hole_pitch_y / 2 + Math.abs(p.mount_hole_y_offset) + pilotRadius >= p.pcb_keepout_height / 2) add('error', ['mount_hole_pitch_x', 'mount_hole_pitch_y', 'mount_hole_y_offset', 'pilot_diameter', 'pcb_keepout_width', 'pcb_keepout_height'], 'A mount pilot reaches or lies outside the PCB envelope. Measure its actual hole center and edge clearance before moving the posts.');
  if (p.pilot_diameter >= p.post_diameter || p.pilot_diameter >= p.post_base_diameter) add('error', ['pilot_diameter', 'post_diameter', 'post_base_diameter'], 'The pilot is as wide as a supporting post or base, leaving no surrounding material. Reduce the pilot or enlarge the support.');
  else if ((p.post_diameter - p.pilot_diameter) / 2 < 0.6) add('warning', ['pilot_diameter', 'post_diameter'], 'Less than 0.6 mm of nominal post material surrounds the pilot. Check screw fit and print strength with the actual material.');
  if (p.post_diameter > p.post_base_diameter) add('warning', ['post_diameter', 'post_base_diameter'], 'The exposed post is wider than its base. Inspect the regenerated support and avoid assuming its printed strength.');
  if (pcbFront - p.face - p.post_height < -1e-9) add('error', ['post_height', 'measured_switch_top_height', 'cap_flange_depth', 'cap_release_gap'], 'The exposed post is taller than the complete button stack permits; its raised base would be negative. Recalculate the cap stack and both post sections together.');
  if (p.pilot_depth >= pcbFront - p.face) add('error', ['pilot_depth', 'face', 'measured_switch_top_height', 'cap_flange_depth', 'cap_release_gap'], 'The blind pilot would reach the front face. Shorten the pilot and verify screw bottoming against the entire PCB support stack.');
  if (p.cover_seam_z <= pcbBack + 0.35) add('error', ['cover_seam_z', 'pcb_thickness', 'measured_switch_top_height', 'face', 'cap_flange_depth', 'cap_release_gap'], 'The cover seam is too close to the PCB back for the native locating lip. Increase the seam depth or revisit the complete board stack.');
  if (Number.isFinite(caseDepth) && p.cover_seam_z + 0.3 >= caseDepth - p.cover_face) add('error', ['cover_seam_z', 'cover_face', 'header_rear_projection'], 'The cover seam leaves no rear cavity above the locating ledge. Revise seam and rear depth together.');
  if (p.measured_switch_top_height <= p.measured_switch_fixed_height) add('error', ['measured_switch_top_height', 'measured_switch_fixed_height'], 'The released moving peak must project above the fixed switch housing. These two heights describe different parts of the original button.');
  else if (p.cap_travel_check >= p.measured_switch_top_height - p.measured_switch_fixed_height) add('error', ['cap_travel_check', 'measured_switch_top_height', 'measured_switch_fixed_height'], 'The planned inward travel reaches the estimated fixed housing height. Recheck cap and housing collision in native CAD and on the assembled board.');

  const apertureWidth = p.cap_width + 2 * p.cap_side_clearance;
  const apertureHeight = p.cap_height + 2 * p.cap_side_clearance;
  if (apertureWidth >= p.cap_flange_width || apertureHeight >= p.cap_flange_height) add('error', ['cap_side_clearance', 'cap_width', 'cap_height', 'cap_flange_width', 'cap_flange_height'], 'A key aperture is as large as its retaining flange. Restore flange overlap so the cap cannot pass through the face.');
  if (p.cap_total_depth <= p.cap_flange_depth || p.cap_total_depth <= buttonRest) add('error', ['cap_total_depth', 'cap_flange_depth', 'face', 'cap_release_gap'], 'The cap must include a shaft beyond its flange and project through the exterior face. Recheck the complete cap dimensions.');
  if (Math.min(p.cap_width, p.cap_height) <= 1.1 || Math.min(p.cap_flange_width, p.cap_flange_height) <= 2.4) add('error', ['cap_width', 'cap_height', 'cap_flange_width', 'cap_flange_height'], 'The native key shaft uses 0.55 mm rounding and the flange uses 1.2 mm rounding. Their widths and heights must exceed twice those radii.');
  const screenWidth = p.glass_width - 2 * p.window_overlap_x, screenHeight = p.glass_height - 2 * p.window_overlap_y;
  const screen = rect(p.glass_center_x, p.glass_center_y, screenWidth, screenHeight);
  if (screenWidth <= 1.3 || screenHeight <= 1.3 || !insideRounded(screen, innerWidth, innerHeight, innerRadius)) add('error', ['glass_width', 'glass_height', 'glass_center_x', 'glass_center_y', 'window_overlap_x', 'window_overlap_y', 'case_width', 'case_height', 'wall'], 'The display aperture no longer fits the front cavity or its native 0.65 mm corner rounding. Confirm glass and active image dimensions before regenerating.');
  const keyRects = p.button_centers_y.map(y => rect(p.button_x, y, apertureWidth, apertureHeight));
  if (keyRects.some(key => !insideRounded(key, innerWidth, innerHeight, innerRadius))) add('error', ['button_x', 'button_centers_y', 'cap_side_clearance', 'case_width', 'case_height', 'wall'], 'A key aperture reaches the front cavity boundary. Confirm the button column and pitch against the real board.');
  if (keyRects.some(key => overlap(key, screen))) add('error', ['button_x', 'button_centers_y', 'glass_width', 'glass_center_x', 'cap_side_clearance'], 'A key aperture overlaps the display opening. Keep the glass and button position evidence separate and remeasure their spacing.');
  const mountCenters = [-1, 1].flatMap(sx => [-1, 1].map(sy => [sx * p.mount_hole_pitch_x / 2, sy * p.mount_hole_pitch_y / 2 + p.mount_hole_y_offset]));
  if (mountCenters.some(([x, y]) => [screen, ...keyRects].some(aperture => circleOverlaps(x, y, p.post_base_diameter / 2, aperture)))) add('error', ['post_base_diameter', 'mount_hole_pitch_x', 'mount_hole_pitch_y', 'mount_hole_y_offset', 'glass_width', 'button_x'], 'A raised post base overlaps a display or key aperture. Reposition or resize the measured supports while keeping the complete PCB and cap stack.');
  const sortedY = [...p.button_centers_y].sort((a, b) => a - b);
  if (sortedY.some((y, index) => index && y - sortedY[index - 1] <= Math.max(apertureHeight, p.cap_flange_height))) add('error', ['button_centers_y', 'cap_height', 'cap_flange_height', 'cap_side_clearance'], 'Neighboring key openings or retaining flanges overlap. Confirm each key has independent clearance and return.');

  const connectorWidth = 8 * p.header_pitch, connectorHeight = 4.2;
  if (p.knockout_width <= connectorWidth || p.knockout_height <= connectorHeight) add('error', ['knockout_width', 'knockout_height', 'header_pitch'], `The rear opening cannot clear the estimated ${round(connectorWidth)} × 4.2 mm straight eight-position DuPont envelope with clearance. Measure actual plugs before choosing the opening.`);
  else if (!insideRounded(rect(0, 0, connectorWidth, connectorHeight), p.knockout_width, p.knockout_height, p.knockout_radius)) add('error', ['knockout_width', 'knockout_height', 'knockout_radius', 'header_pitch'], 'Rounded port corners intrude into the estimated connector envelope. Increase the opening or reduce its radius after measuring the actual plugs.');
  if (p.knockout_radius >= Math.min(p.knockout_width, p.knockout_height) / 2) add('error', ['knockout_radius', 'knockout_width', 'knockout_height'], 'The panel corner radius is too large for its width or height.');
  if (p.knockout_membrane <= 0 || p.knockout_membrane >= p.cover_face || p.knockout_membrane >= p.cover_face - 0.05) add('error', ['knockout_membrane', 'cover_face'], 'The knockout needs a positive outer skin and space for its inside score below the rear face.');
  const headerRects = [rect(p.header_x, p.header_y, p.knockout_width + 2 * p.knockout_score_width, p.knockout_height + 2 * p.knockout_score_width), rect(-p.header_x, -p.header_y, p.knockout_width + 2 * p.knockout_score_width, p.knockout_height + 2 * p.knockout_score_width)];
  if (headerRects.some(panel => !insideRounded(panel, p.case_width, p.case_height, p.corner_radius))) add('error', ['knockout_width', 'knockout_height', 'knockout_score_width', 'header_x', 'header_y', 'case_width', 'case_height', 'corner_radius'], 'A scored rear panel crosses the case perimeter. Keep the surrounding wall continuous and revise the panel or header position.');
  if (state.back === 'back-dual-knockouts') add('warning', ['knockout_width', 'knockout_height'], 'Both rear panels are intact. The closed depth clears estimated bare pins only; straight DuPont plugs need the matching panel opened with the cover detached.');
  else add('info', ['knockout_width', 'knockout_height'], `${state.back === 'back-lower-open' ? 'Lower' : 'Upper'} open refers to assembly Y. The original reference header maps to lower / negative Y; verify the actual cable side.`);

  if (changed.length) add('warning', changed, 'These values are planning overrides. Published STEP/STL downloads and the original model view remain the unchanged CAD v3 base; regenerate native geometry and checks for this plan.');
  if (state.useCase === 'custom-board') add('warning', ['pcb_keepout_width', 'pcb_keepout_height', 'mount_hole_pitch_x', 'mount_hole_pitch_y', 'measured_switch_top_height'], 'This is a new-board planning purpose. Original measurements apply to the purchased module only; verify a new mechanical and electrical profile before use.');
  add('warning', ['pcb_keepout_width', 'pcb_keepout_height', 'mount_hole_pitch_x', 'mount_hole_pitch_y', 'button_x'], 'Baseline evidence differs: seller envelope 44.53 × 27.66 mm; approximate community PCB 44 × 27 mm; original hole pitch about 40 × 24 mm. Button X=14.25 still uses 22 − 4.75 − 3 on the reference outline. Keep those assumptions separate.');
  add('info', [], 'Assembled physical CAD v3 fit is unverified. Dimensional checks do not establish key feel, screw fit, latch retention, knockout removal, connector fit or stand stability.');
  return { parameters: clone(p), dimensions, warnings, changed, valid: !warnings.some(warning => warning.severity === 'error'), hasChanges: changed.length > 0 };
}

export function makeSettings(input) {
  return JSON.stringify({ schemaVersion: 1, sourceSha256: DEFAULTS.source_sha256, state: normalizeState(input) }, null, 2) + '\n';
}

const prettyValue = value => Array.isArray(value) ? `[${value.map(prettyValue).join(', ')}]` : String(round(value));
const REPO = 'https://github.com/aarzamen/pi500-oled-panel';
const KIT = `${REPO}/tree/main/mechanical/cad-rebuild`;
const FENCE = String.fromCharCode(96).repeat(3);

/** A self-contained brief that distinguishes original measurements from this draft. */
export function makeHandoff(input) {
  const state = normalizeState(input), plan = evaluatePlan(state), p = plan.parameters, d = plan.dimensions;
  const purpose = PURPOSES[state.useCase];
  const changes = plan.changed.length
    ? plan.changed.map(key => `- ${key}: ${prettyValue(DEFAULTS[key])} → ${prettyValue(p[key])}${key === 'stand_tilt_degrees' ? ' degrees' : ' mm'}. Planning override; verify the input before treating it as a measurement.`).join('\n')
    : '- No dimensional overrides. The complete native JSON below preserves the published base dimensions.';
  const checks = plan.warnings.map(warning => `- ${warning.severity.toUpperCase()}: ${warning.message}${warning.fields.length ? ` Related parameters: ${warning.fields.join(', ')}.` : ''}`).join('\n');
  return `# Maker workbench handoff: ${purpose.label}

Please develop this selected plan from the public native CAD v3 source. ${purpose.direction}

Selected back: ${state.back}. Show matched stand: ${state.showStand ? 'yes' : 'no'}. The exploded-view selection (${state.exploded ? 'on' : 'off'}) is only a viewing preference.
This is a dimensional plan. ${plan.valid ? 'It passes the workbench dimensional preflight.' : 'It has dimensional conflicts; resolve the errors below before generating a print candidate.'} Native CAD kernel checks, slicing, and an assembled physical print remain separate work. Published base downloads and the original mesh view do not regenerate when the plan changes.

## Current planning values

${changes}

Calculated case: ${d.caseWidth} × ${d.caseHeight} × ${d.caseDepth} mm. Assembly Z=0 is the exterior front face; positive Z goes into the case.
The complete released stack is front face ${p.face} + released actuator peak ${p.measured_switch_top_height} + retaining flange ${p.cap_flange_depth} + release gap ${p.cap_release_gap} = PCB front Z ${d.pcbFront} mm. PCB thickness ${p.pcb_thickness} gives PCB back Z ${d.pcbBack}; estimated bare pins end at Z ${d.pinRear}. Cap contact rests at Z ${d.buttonRest}. The closed depth rounds upward to ${p.layer_height} mm layers after pin projection, rear clearance and rear face. The native generator recalculates the raised post base; changing only exposed post height must not preload or separate the keys.

## Original module measurements and uncertain references

The purchased source is ACEIRMC SSD1315 yellow/blue, Amazon ASIN [B0GWQPY2C7](https://www.amazon.com/dp/B0GWQPY2C7), five-pack with four buttons and eight header pins. The tested board is HW-937AB. Original measured released peak / fixed housing heights are 2.65 / 1.8 mm above the front PCB surface. Original mounting pitch is approximately 40 × 24 mm; low caliper battery limited precision. These original observations are reference data, not confirmation of the current slider choices or a new board.

The original 4.75 mm datum is PCB right edge to the nearest fixed switch housing EDGE. It is not the moving actuator center. Button X=22 − 4.75 − 3 = 14.25 mm uses the approximate community PCB width of 44 mm and estimated housing width of 6 mm. The seller envelope is 44.53 × 27.66 mm and supplies the conservative PCB keepout. Do not silently substitute that width into the switch-center derivation or scale the whole enclosure. Physical outline, PCB thickness, glass/active area and height, button Y centers, header geometry and all eight plug housings need measurement.

Hellfire's “OLED | 0.96 | 4 button,” dated April 8, 2025, is an approximate community model from GrabCAD, not a factory drawing. Redistribution permission for the separately supplied PCB STEP and derived hardware assembly is unknown; they are not in the public kit. Obtain a lawfully held original for the optional hash-checked hardware validator. Preserve source attribution and the expected original hash in parameters.json.

Use proper rigid 180° rotation about X for the reference module, glass, keys and cover print poses. The back print pose is (x,y,z) → (x,−y,case_depth−z), determinant +1; assembly lower/upper Y reverses in print orientation. Do not replace this rotation with a reflection. The lower-open back matches the estimated original header side, at negative assembly Y.

Straight rear DuPont housings require the matching rear panel open. Closed depth covers estimated bare pins only. Keep the top wall continuous, verify the ${p.knockout_width} × ${p.knockout_height} mm port against all eight actual plugs, and detach the cover before opening a scored membrane. The latch cavity, conservative board envelope and inward latch deflection are coupled; the native generator checks at least 0.25 mm compressed-arm radial clearance. Regenerate the matching stand together with any case-depth change.

The current board uses four wires for the I2C display plus four independent K1–K4 conductors for working buttons. The Dorhea SSD1306 ASIN [B0GWTWPMNT](https://www.amazon.com/dp/B0GWTWPMNT) is an unpurchased candidate that also lists independent buttons. Four-wire operation of the complete panel is unverified. A shared-bus button expander and driver need separate electrical and runtime tests.

The rich companion JSON data feed and loopback companion app are a future plan, not an installed service. Treat sensor or bench software as a separate implementation task. The optional PanelBridge rollout remains parked; do not infer another board's wiring or host controls from the tested Pi runtime.

## Preflight findings

${checks}

## Complete native generator JSON

Save the following JSON as maker-parameters.json in the extracted kit root. Any changed/custom-board profile sets calibration_complete=false; physical_calibration applies only to the original module, and planning_overrides records unverified choices. The generator's calibration flag never proves assembled fit.

${FENCE}json
${JSON.stringify(p, null, 2)}
${FENCE}

## Public source, files and regeneration

- [Project README](${REPO}/blob/main/README.md)
- [Native kit README](${REPO}/blob/main/mechanical/cad-rebuild/README.md)
- [Portable CAD source](${KIT}/source)
- [Native STEP parts and enclosure-only assembly](${KIT}/STEP)
- [Complete public base ZIP](https://raw.githubusercontent.com/aarzamen/pi500-oled-panel/main/mechanical/cad-rebuild/OLED-case-CAD-v3-public.zip)
- [Fitment notes](${REPO}/blob/main/docs/fitment.md)
- [Sourcing and variants](${REPO}/blob/main/docs/hardware-sourcing.md)
- [Future companion plan](${REPO}/blob/main/docs/companion-app-plan.md)

From the extracted public kit directory, create a Python 3.12 environment with uv and generate a new output. Resolve the preflight errors first. No separate community STEP is required for authored enclosure geometry.

${FENCE}bash
uv venv --python 3.12 source/.venv
uv pip install --python source/.venv/bin/python -r source/requirements.txt
source/.venv/bin/python source/export_design.py --parameters ./maker-parameters.json --output ./maker-plan-output
source/.venv/bin/python -m unittest discover -s source -p 'test_*.py'
${FENCE}

Run the generator's native-solid and collision checks for this parameter file and inspect regenerated STEP/STL/stand. Slice for the intended printer and material; the supplied public Bambu profile uses normal cooldown and unload. Print and assemble a fit prototype with PCB, four caps, screws and straight connectors. Check each cap moves and returns without preload; both latches close and release with board installed; screws clamp without bottoming or breaking posts; ports clear all eight housings; the glass is not loaded; and the stand holds the deeper body with a stable cable path. Earlier empty-case success does not prove assembled v3 fit. Record the actual board measurements and print result before describing a variant as validated.
`;
}
