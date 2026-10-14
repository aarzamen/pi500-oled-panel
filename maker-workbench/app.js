import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { DEFAULTS, PARAMETER_META, getDefaultState, getPreset, normalizeState, evaluatePlan, makeHandoff, makeSettings } from './planner.js';
import { MODELS, BASE_PARAMETERS } from './model-data.js';

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const STORAGE = 'oled-case-workbench:cad-v3:';
const BACK_LABELS = {
  'back-dual-knockouts': 'Back · panels intact',
  'back-lower-open': 'Back · lower open',
  'back-upper-open': 'Back · upper open',
};
const META_BY_KEY = new Map(PARAMETER_META.map((item) => [item.key, item]));
const fields = new Map();
const interfaceGroup = (meta) => meta.group === 'Basic' && !['wall', 'corner_radius'].includes(meta.key)
  ? (meta.key.startsWith('stand_') ? 'Detail' : 'Board') : meta.group;
let state = getDefaultState();
let plan = evaluatePlan(state);
let modelView;
let feedbackTimer;
let saveTimer;
let restored = false;

function format(value, precision = 3) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  return Number(value.toFixed(precision)).toString();
}

function unitFor(key) {
  return key === 'stand_tilt_degrees' ? '°' : 'mm';
}

function feedback(message, error = false) {
  const target = $('#feedback');
  target.textContent = message;
  target.classList.toggle('error', error);
  target.hidden = false;
  clearTimeout(feedbackTimer);
  feedbackTimer = setTimeout(() => { target.hidden = true; }, error ? 7000 : 4200);
}

function readStored(key) {
  try {
    const raw = localStorage.getItem(STORAGE + key);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!isSettingsObject(parsed)) return null;
    return normalizeState(parsed);
  } catch {
    return null;
  }
}

function isSettingsObject(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  if ('schemaVersion' in value && value.schemaVersion !== 1) return false;
  const candidate = value.state || value;
  return !!candidate && typeof candidate === 'object' && !Array.isArray(candidate)
    && !!candidate.parameters && typeof candidate.parameters === 'object'
    && !Array.isArray(candidate.parameters);
}

function storeDraft() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    try {
      localStorage.setItem(STORAGE + 'draft', makeSettings(state));
    } catch {
      $('#storage-status').textContent = 'Browser storage is unavailable. Save a settings JSON to keep this plan.';
    }
  }, 200);
}

function buildParameterControls() {
  for (const meta of PARAMETER_META) {
    const container = $('#parameters-' + interfaceGroup(meta).toLowerCase());
    if (!container) continue;
    const unit = unitFor(meta.key);
    const field = document.createElement('div');
    field.className = 'field';
    field.dataset.field = meta.key;
    const labelRow = document.createElement('div');
    labelRow.className = 'field-label-row';
    const label = document.createElement('label');
    label.htmlFor = 'value-' + meta.key;
    label.textContent = meta.label;
    const reset = document.createElement('button');
    reset.type = 'button';
    reset.className = 'reset-field';
    reset.textContent = 'Reset';
    reset.dataset.reset = meta.key;
    reset.setAttribute('aria-label', `Reset ${meta.label.toLowerCase()} to ${format(DEFAULTS[meta.key])} ${unit}`);
    labelRow.append(label, reset);
    const controls = document.createElement('div');
    controls.className = 'field-controls';
    const range = document.createElement('input');
    range.type = 'range';
    range.id = 'range-' + meta.key;
    range.min = meta.min;
    range.max = meta.max;
    range.step = meta.step;
    range.setAttribute('aria-label', meta.label + ' slider');
    range.setAttribute('aria-describedby', 'help-' + meta.key);
    const numberWrap = document.createElement('div');
    numberWrap.className = 'number-wrap';
    const input = document.createElement('input');
    input.type = 'number';
    input.id = 'value-' + meta.key;
    input.min = meta.min;
    input.max = meta.max;
    input.step = meta.step;
    input.inputMode = 'decimal';
    input.setAttribute('aria-describedby', 'help-' + meta.key + ' error-' + meta.key);
    const unitLabel = document.createElement('span');
    unitLabel.className = 'unit';
    unitLabel.textContent = unit;
    numberWrap.append(input, unitLabel);
    controls.append(range, numberWrap);
    const help = document.createElement('p');
    help.className = 'field-help';
    help.id = 'help-' + meta.key;
    help.textContent = meta.help;
    const error = document.createElement('p');
    error.className = 'field-error';
    error.id = 'error-' + meta.key;
    error.hidden = true;
    field.append(labelRow, controls, help, error);
    container.append(field);
    fields.set(meta.key, { field, range, input, error, meta });
    range.addEventListener('input', () => setParameter(meta.key, Number(range.value), range));
    input.addEventListener('input', () => {
      if (input.value.trim() === '' || !Number.isFinite(input.valueAsNumber)) {
        input.setAttribute('aria-invalid', 'true');
        field.classList.add('error');
        error.hidden = false;
        error.textContent = 'Enter a number. The draft keeps the last complete value.';
        return;
      }
      setParameter(meta.key, input.valueAsNumber, input);
    });
    input.addEventListener('blur', () => {
      input.value = format(state.parameters[meta.key], 6);
      renderControls();
    });
  }
}

function setParameter(key, value, activeInput) {
  state.parameters[key] = value;
  update(activeInput);
}

function renderControls(activeInput) {
  for (const [key, entry] of fields) {
    const value = state.parameters[key];
    if (entry.input !== activeInput) entry.input.value = format(value, 6);
    if (entry.range !== activeInput) entry.range.value = value;
    entry.field.classList.toggle('modified', plan.changed.includes(key));
    entry.field.classList.remove('warning', 'error', 'info');
    entry.input.removeAttribute('aria-invalid');
    entry.error.hidden = true;
    entry.error.textContent = '';
  }
  const severityRank = { info: 1, warning: 2, error: 3 };
  const fieldMessages = new Map();
  for (const warning of plan.warnings) {
    for (const key of warning.fields) {
      const entry = fields.get(key);
      if (!entry) continue;
      const existing = fieldMessages.get(key);
      if (!existing || severityRank[warning.severity] > severityRank[existing.severity]) {
        fieldMessages.set(key, warning);
      }
    }
  }
  for (const [key, warning] of fieldMessages) {
    const entry = fields.get(key);
    entry.field.classList.add(warning.severity);
    entry.error.textContent = warning.message;
    entry.error.hidden = false;
    if (warning.severity === 'error') entry.input.setAttribute('aria-invalid', 'true');
  }
  $$('[name="use-case"]').forEach((input) => { input.checked = input.value === state.useCase; });
  $('#back-choice').value = state.back;
  $('#exploded-view').checked = state.exploded;
  $('#show-stand').checked = state.showStand;
  $('.stand-legend').hidden = !state.showStand;
  $$('[data-count]').forEach((element) => {
    const count = PARAMETER_META.filter((meta) => interfaceGroup(meta) === element.dataset.count && plan.changed.includes(meta.key)).length;
    element.textContent = count ? `${count} changed` : '';
  });
}

function focusField(key) {
  if (key === 'back') {
    $('#back-choice').scrollIntoView({ block: 'center', behavior: 'smooth' });
    $('#back-choice').focus({ preventScroll: true });
    return;
  }
  const entry = fields.get(key);
  if (!entry) return;
  const detail = entry.field.closest('details');
  if (detail) detail.open = true;
  entry.input.scrollIntoView({ block: 'center', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  entry.input.focus({ preventScroll: true });
}

function renderWarnings() {
  const holder = $('#plan-warnings');
  holder.replaceChildren();
  for (const warning of plan.warnings) {
    const row = document.createElement('div');
    row.className = 'warning-message ' + warning.severity;
    const message = document.createElement('p');
    message.textContent = warning.message;
    row.append(message);
    const field = warning.fields.find((key) => fields.has(key) || key === 'back');
    if (field) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = 'Show field';
      button.setAttribute('aria-label', 'Show ' + (META_BY_KEY.get(field)?.label || 'rear opening'));
      button.addEventListener('click', () => focusField(field));
      row.append(button);
    }
    holder.append(row);
  }
}

function renderDimensions() {
  const dimensions = plan.dimensions;
  const values = {
    width: dimensions.caseWidth,
    height: dimensions.caseHeight,
    depth: dimensions.caseDepth,
    'pcb-front': dimensions.pcbFront,
    'pcb-back': dimensions.pcbBack,
    'pin-rear': dimensions.pinRear,
    'button-rest': dimensions.buttonRest,
  };
  for (const [key, value] of Object.entries(values)) $('#dim-' + key).textContent = format(value);
  const badge = $('#draft-badge');
  badge.textContent = !plan.valid ? 'Review dimensions' : plan.hasChanges ? `${plan.changed.length} changed` : 'Base dimensions';
  badge.classList.toggle('changed', plan.hasChanges && plan.valid);
  badge.classList.toggle('invalid', !plan.valid);
  renderSketch();
}

function renderSketch() {
  const p = plan.parameters;
  const d = plan.dimensions;
  const finite = (value, fallback) => Number.isFinite(value) ? value : fallback;
  const width = Math.max(5, Math.abs(finite(d.caseWidth, 51.3)));
  const height = Math.max(5, Math.abs(finite(d.caseHeight, 33.4)));
  const scale = Math.min(205 / width, 152 / height);
  const cx = 143;
  const cy = 124;
  const sx = (x) => cx - finite(x, 0) * scale;
  const sy = (y) => cy - finite(y, 0) * scale;
  const x = sx(width / 2);
  const y = sy(height / 2);
  const w = width * scale;
  const h = height * scale;
  const radius = Math.min(Math.abs(finite(p.corner_radius, 3.5)) * scale, Math.min(w, h) / 2);
  const boardW = Math.max(0, finite(p.pcb_keepout_width, 44.53)) * scale;
  const boardH = Math.max(0, finite(p.pcb_keepout_height, 27.66)) * scale;
  const mounts = [-1, 1].flatMap((xSign) => [-1, 1].map((ySign) => {
    const x0 = xSign * finite(p.mount_hole_pitch_x, 40) / 2;
    const y0 = ySign * finite(p.mount_hole_pitch_y, 24) / 2 + finite(p.mount_hole_y_offset, 0);
    return `<circle cx="${sx(x0)}" cy="${sy(y0)}" r="3.4" fill="none" stroke="#79cce0" stroke-width="1.1"/>`;
  })).join('');
  const caps = (p.button_centers_y || BASE_PARAMETERS.button_centers_y).map((buttonY) => {
    const capW = Math.max(.1, finite(p.cap_width, 4.6)) * scale;
    const capH = Math.max(.1, finite(p.cap_height, 2.6)) * scale;
    return `<rect x="${sx(p.button_x) - capW / 2}" y="${sy(buttonY) - capH / 2}" width="${capW}" height="${capH}" rx="1.8" fill="#e4c64f" fill-opacity=".45" stroke="#e4c64f"/>`;
  }).join('');
  const glassW = Math.max(.1, finite(p.glass_width, 24.5) - 2 * finite(p.window_overlap_x, .3)) * scale;
  const glassH = Math.max(.1, finite(p.glass_height, 16.5) - 2 * finite(p.window_overlap_y, .2)) * scale;
  const depth = Math.max(2, Math.abs(finite(d.caseDepth, 12.2)));
  const zScale = Math.min(105 / depth, 9);
  const z0 = 302;
  const z = (value) => z0 + finite(value, 0) * zScale;
  const stackTop = 63;
  const stackH = 120;
  const pcbFront = z(d.pcbFront);
  const pcbBack = z(d.pcbBack);
  const pinRear = z(d.pinRear);
  const rearFace = z(depth - finite(p.cover_face, 1.2));
  $('#dimension-sketch').innerHTML = `<svg viewBox="0 0 446 248" role="img" aria-labelledby="sketch-title sketch-description">
    <title id="sketch-title">Draft front layout and button stack</title><desc id="sketch-description">Case ${format(d.caseWidth)} by ${format(d.caseHeight)} by ${format(d.caseDepth)} millimeters. PCB front is ${format(d.pcbFront)} millimeters behind the outer face. This drawing describes the plan and is not printable geometry.</desc>
    <defs><clipPath id="draft-front-clip"><rect x="30" y="39" width="230" height="171"/></clipPath><clipPath id="draft-stack-clip"><rect x="279" y="41" width="140" height="160"/></clipPath></defs>
    <text x="42" y="23" class="sketch-label">Front layout</text><text x="293" y="23" class="sketch-label">Side stack</text>
    <g clip-path="url(#draft-front-clip)"><rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${radius}" fill="#2c414d" stroke="#b4c1c9" stroke-width="1.5"/>
    <rect x="${cx - boardW / 2}" y="${cy - boardH / 2}" width="${boardW}" height="${boardH}" fill="none" stroke="#6d8998" stroke-dasharray="3 3"/>
    <rect x="${sx(p.glass_center_x) - glassW / 2}" y="${sy(p.glass_center_y) - glassH / 2}" width="${glassW}" height="${glassH}" rx="2" fill="#22323c" stroke="#79cce0"/>${caps}${mounts}</g>
    <path d="M${x} 218v6m0-3h${w}m0-3v6" fill="none" stroke="#6c8d9d"/><text x="${cx}" y="240" text-anchor="middle" class="dimension-value">${format(d.caseWidth)} mm</text>
    <g clip-path="url(#draft-stack-clip)"><rect x="${z0}" y="${stackTop}" width="${depth * zScale}" height="${stackH}" rx="2" fill="#293e4b" stroke="#b4c1c9" stroke-width="1.2"/>
    <rect x="${z0}" y="${stackTop}" width="${Math.max(.3, finite(p.face, 1.2)) * zScale}" height="${stackH}" fill="#aab8bd"/>
    <rect x="${rearFace}" y="${stackTop}" width="${Math.max(.1, finite(p.cover_face, 1.2)) * zScale}" height="${stackH}" fill="#718a98"/>
    <rect x="${pcbFront}" y="${stackTop + 15}" width="${Math.max(1, pcbBack - pcbFront)}" height="${stackH - 30}" fill="#79cce0" fill-opacity=".55"/>
    <path d="M${z0 - 8} 103H${z(d.buttonRest)}M${z(d.buttonRest)} 103H${pcbFront}" stroke="#e4c64f" stroke-width="4"/>
    <path d="M${pcbBack} 157H${pinRear}" stroke="#79cce0" stroke-width="2"/>
    <path d="M${pcbFront} 53v140" stroke="#79cce0" stroke-dasharray="3 3"/><text x="${pcbFront + 4}" y="49" fill="#79cce0">PCB</text></g>
    <path d="M${z0} 218v6m0-3h${depth * zScale}m0-3v6" fill="none" stroke="#6c8d9d"/><text x="${z0 + depth * zScale / 2}" y="240" text-anchor="middle" class="dimension-value">${format(d.caseDepth)} mm</text>
    <text x="267" y="205" font-size="9">Z=0</text>
  </svg>`;
}

function renderDownloads() {
  $('#selected-back-stl').href = './cad-v3/STL/' + state.back + '.stl';
  $('#selected-back-label').textContent = BACK_LABELS[state.back];
  $('#download-notice').hidden = !plan.hasChanges;
  $('#downloads-badge').textContent = plan.hasChanges ? 'Original base files' : 'Base files';
  $('#native-badge').textContent = plan.hasChanges ? 'Original base geometry' : 'Native CAD v3';
  $('#native-note').textContent = plan.hasChanges
    ? 'The 3D view keeps the original CAD v3 dimensions. Your changes appear in the draft. Assembled physical fit is unverified.'
    : 'Drag to orbit; scroll or pinch to zoom. The stand is shown separately. Assembled physical fit is unverified.';
}

function update(activeInput) {
  plan = evaluatePlan(state);
  renderControls(activeInput);
  renderWarnings();
  renderDimensions();
  renderDownloads();
  $('#handoff-text').value = makeHandoff(state);
  $('#copy-fallback').hidden = true;
  modelView?.update();
  storeDraft();
}

function downloadText(content, filename, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

async function copyHandoff() {
  const text = makeHandoff(state);
  try {
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard not available');
    await navigator.clipboard.writeText(text);
    $('#copy-handoff').textContent = 'Copied';
    feedback('Handoff copied. Include the settings JSON when handing off the plan.');
    setTimeout(() => { $('#copy-handoff').textContent = 'Copy handoff'; }, 2000);
  } catch {
    const textarea = $('#handoff-text');
    textarea.focus();
    textarea.select();
    let copied = false;
    try { copied = document.execCommand('copy'); } catch { /* Offer manual selection below. */ }
    if (copied) feedback('Handoff copied.');
    else {
      $('#copy-fallback').hidden = false;
      feedback('Handoff selected. Press ⌘C or Ctrl+C to copy.');
    }
  }
}

function bindControls() {
  $$('[name="use-case"]').forEach((input) => input.addEventListener('change', () => {
    if (!input.checked) return;
    state.useCase = getPreset(input.value).useCase;
    update();
  }));
  $('#back-choice').addEventListener('change', (event) => {
    state.back = event.target.value;
    update();
  });
  $('#exploded-view').addEventListener('change', (event) => {
    state.exploded = event.target.checked;
    update();
    modelView?.fit();
  });
  $('#show-stand').addEventListener('change', (event) => {
    state.showStand = event.target.checked;
    update();
    modelView?.fit();
  });
  $('#reset-view').addEventListener('click', () => {
    state.exploded = false;
    state.showStand = true;
    update();
    modelView?.setView('angle');
  });
  document.addEventListener('click', (event) => {
    const reset = event.target.closest('[data-reset]');
    if (!reset) return;
    const key = reset.dataset.reset;
    if (key === 'back') state.back = getDefaultState().back;
    else if (key === 'use-case') state.useCase = getDefaultState().useCase;
    else if (META_BY_KEY.has(key)) state.parameters[key] = DEFAULTS[key];
    update();
    feedback((META_BY_KEY.get(key)?.label || (key === 'use-case' ? 'Purpose' : 'Rear opening')) + ' reset.');
  });
  $('#reset-all').addEventListener('click', () => {
    state = getDefaultState();
    update();
    modelView?.setView('angle');
    feedback('Plan and view reset to the CAD v3 base.');
  });
  $('#save-plan').addEventListener('click', () => {
    try {
      localStorage.setItem(STORAGE + 'saved', makeSettings(state));
      $('#load-plan').disabled = false;
      $('#storage-status').textContent = 'Saved in this browser. Download settings to move this plan elsewhere.';
      feedback('Plan saved in this browser.');
    } catch {
      feedback('Browser storage is unavailable. Use Save settings JSON instead.', true);
    }
  });
  $('#load-plan').addEventListener('click', () => {
    const saved = readStored('saved');
    if (!saved) {
      feedback('No readable saved plan. Import a settings JSON or save this draft first.', true);
      return;
    }
    state = saved;
    update();
    modelView?.fit();
    feedback('Saved plan loaded.');
  });
  $('#import-settings').addEventListener('change', async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      if (file.size > 1024 * 1024) throw new Error('Use a settings JSON smaller than 1 MB.');
      let parsed;
      try { parsed = JSON.parse(await file.text()); } catch { throw new Error('The file is not valid JSON. Choose a workbench settings file.'); }
      if (!isSettingsObject(parsed)) throw new Error('Expected workbench settings with a parameters object and schema version 1.');
      state = normalizeState(parsed);
      update();
      modelView?.fit();
      feedback('Settings imported. Review the draft warnings before regenerating CAD.');
    } catch (error) {
      feedback(error.message || 'Could not load this settings file.', true);
    } finally {
      event.target.value = '';
    }
  });
  $('#copy-handoff').addEventListener('click', copyHandoff);
  $('#download-handoff').addEventListener('click', () => downloadText(makeHandoff(state), 'OLED-CAD-v3-' + state.useCase + '-handoff.md', 'text/markdown;charset=utf-8'));
  $('#download-settings').addEventListener('click', () => downloadText(makeSettings(state), 'OLED-CAD-v3-' + state.useCase + '-settings.json', 'application/json;charset=utf-8'));
  $$('[data-view]').forEach((button) => button.addEventListener('click', () => {
    if (button.dataset.view === 'fit') modelView?.fit();
    else modelView?.setView(button.dataset.view);
  }));
  $$('[data-zoom]').forEach((button) => button.addEventListener('click', () => modelView?.zoom(button.dataset.zoom === 'in' ? 1.2 : 1 / 1.2)));
  $$('[data-check]').forEach((input) => {
    try { input.checked = localStorage.getItem(STORAGE + 'check:' + input.dataset.check) === 'true'; } catch { /* Checklist still works without storage. */ }
    input.addEventListener('change', () => {
      try { localStorage.setItem(STORAGE + 'check:' + input.dataset.check, input.checked); } catch { /* No hardware state depends on this note. */ }
    });
  });
}

function createModelView() {
  const holder = $('#model-canvas');
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' });
  } catch {
    showFallback();
    return null;
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setClearColor(0x26363f, 0);
  holder.append(renderer.domElement);
  const scene = new THREE.Scene();
  const group = new THREE.Group();
  scene.add(group);
  const camera = new THREE.OrthographicCamera(-60, 60, 40, -40, .1, 1000);
  camera.up.set(0, 1, 0);
  const orbit = new OrbitControls(camera, renderer.domElement);
  orbit.enableDamping = false;
  orbit.enablePan = true;
  orbit.minZoom = .3;
  orbit.maxZoom = 8;
  const ambient = new THREE.HemisphereLight(0xf0f7ff, 0x354650, 2.2);
  scene.add(ambient);
  const key = new THREE.DirectionalLight(0xfff8df, 3);
  key.position.set(-55, 70, -100);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x8ed9ee, 1.4);
  fill.position.set(55, -20, 50);
  scene.add(fill);
  const geometries = new Map();
  const getGeometry = (name) => {
    if (!geometries.has(name)) {
      const values = MODELS[name]?.positions;
      if (!values) throw new Error('Missing native mesh: ' + name);
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(values, 3));
      geometry.computeVertexNormals();
      geometry.computeBoundingBox();
      geometries.set(name, geometry);
    }
    return geometries.get(name);
  };
  const material = (color) => new THREE.MeshStandardMaterial({ color, roughness: .62, metalness: .03 });
  const materials = { front: material(0xe8e7df), back: material(0x708a99), cap: material(0xe4c64f), stand: material(0x91a2ab) };
  let front;
  let back;
  let stand;
  let caps;
  try {
    front = new THREE.Mesh(getGeometry('front'), materials.front);
    back = new THREE.Mesh(getGeometry(state.back), materials.back);
    back.rotation.x = Math.PI;
    stand = new THREE.Mesh(getGeometry('stand'), materials.stand);
    stand.rotation.x = Math.PI;
    caps = BASE_PARAMETERS.button_centers_y.map(() => {
      const mesh = new THREE.Mesh(getGeometry('button-cap'), materials.cap);
      mesh.rotation.x = Math.PI;
      return mesh;
    });
    group.add(front, back, stand, ...caps);
  } catch {
    renderer.dispose();
    holder.replaceChildren();
    showFallback();
    return null;
  }
  function draw() {
    renderer.render(scene, camera);
  }
  orbit.addEventListener('change', draw);
  function updateModel() {
    const exploded = state.exploded;
    front.position.set(0, 0, exploded ? -10 : 0);
    back.geometry = getGeometry(state.back);
    back.position.set(0, 0, 12.2 + (exploded ? 15 : 0));
    caps.forEach((cap, index) => {
      cap.position.set(BASE_PARAMETERS.button_x, BASE_PARAMETERS.button_centers_y[index], 1.9 - (exploded ? 16 : 0));
    });
    stand.visible = state.showStand;
    stand.position.set(BASE_PARAMETERS.case_width + 14, 0, 7);
    group.updateMatrixWorld(true);
    draw();
  }
  const direction = new THREE.Vector3(-.37, .27, -1).normalize();
  let center = new THREE.Vector3();
  function fit() {
    group.updateMatrixWorld(true);
    const box = new THREE.Box3();
    for (const mesh of [front, back, ...caps, ...(stand.visible ? [stand] : [])]) box.expandByObject(mesh);
    center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const aspect = Math.max(.2, holder.clientWidth / Math.max(1, holder.clientHeight));
    const radius = Math.max(size.x / aspect, size.y, size.z, 35) * .72;
    camera.left = -radius * aspect;
    camera.right = radius * aspect;
    camera.top = radius;
    camera.bottom = -radius;
    camera.zoom = 1;
    camera.updateProjectionMatrix();
    camera.position.copy(center).addScaledVector(direction, 200);
    orbit.target.copy(center);
    camera.lookAt(center);
    orbit.update();
    draw();
  }
  function setView(view) {
    if (view === 'front') direction.set(0, 0, -1);
    else if (view === 'back') direction.set(0, 0, 1);
    else direction.set(-.37, .27, -1).normalize();
    fit();
  }
  function zoom(factor) {
    camera.zoom = THREE.MathUtils.clamp(camera.zoom * factor, .3, 8);
    camera.updateProjectionMatrix();
    draw();
  }
  function resize() {
    if (!holder.clientWidth || !holder.clientHeight) return;
    renderer.setSize(holder.clientWidth, holder.clientHeight, false);
    const aspect = holder.clientWidth / holder.clientHeight;
    camera.left = -camera.top * aspect;
    camera.right = camera.top * aspect;
    camera.updateProjectionMatrix();
    draw();
  }
  holder.addEventListener('keydown', (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    const offset = camera.position.clone().sub(orbit.target);
    if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
      event.preventDefault();
      const angle = event.shiftKey ? .2 : .09;
      if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') offset.applyAxisAngle(new THREE.Vector3(0, 1, 0), event.key === 'ArrowLeft' ? angle : -angle);
      else {
        const right = new THREE.Vector3().crossVectors(offset, camera.up).normalize();
        offset.applyAxisAngle(right, event.key === 'ArrowUp' ? angle : -angle);
      }
      camera.position.copy(orbit.target).add(offset);
      direction.copy(offset).normalize();
      camera.lookAt(orbit.target);
      orbit.update();
      draw();
    } else if (['+', '=', '-', '_', 'Home'].includes(event.key)) {
      event.preventDefault();
      if (event.key === 'Home') fit();
      else zoom(event.key === '-' || event.key === '_' ? 1 / 1.15 : 1.15);
    }
  });
  renderer.domElement.addEventListener('webglcontextlost', (event) => {
    event.preventDefault();
    showFallback();
  });
  new ResizeObserver(resize).observe(holder);
  updateModel();
  fit();
  resize();
  return { update: updateModel, fit, setView, zoom };
}

function showFallback() {
  $('#model-canvas').hidden = true;
  $('#model-fallback').hidden = false;
  $$('[data-view], [data-zoom]').forEach((button) => { button.disabled = true; });
  $('#exploded-view').disabled = true;
  $('#show-stand').disabled = true;
  $('#reset-view').disabled = true;
}

const draft = readStored('draft');
if (draft) {
  state = draft;
  restored = true;
}
buildParameterControls();
bindControls();
$('#load-plan').disabled = !readStored('saved');
if (restored) $('#storage-status').textContent = 'Previous draft restored in this browser.';
if (window.matchMedia('(max-width: 760px)').matches) $('#handoff-panel').open = false;
update();
modelView = createModelView();
