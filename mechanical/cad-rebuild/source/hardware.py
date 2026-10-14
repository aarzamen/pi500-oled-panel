"""Calibrated reference geometry from the user-supplied community OLED STEP.

The input is an approximate model, not a manufacturer drawing. Corrections are
local: mounting features are relocated intact, and each switch is separated
before its XY position and measured front height are applied. The original STEP
is only read. Returned shapes use the enclosure's rearward-positive Z axis.
"""

import hashlib
import math
from pathlib import Path

import cadquery as cq

from common import box, cylinder, shape_info


SOURCE_PCB_THICKNESS = 1.6
SOURCE_BUTTON_X = 15.0
SOURCE_BUTTON_YS = (8.7, 3.033333333333333, -2.633333333333333, -8.3)
SOURCE_MOUNT_CENTERS = ((-20.5, -12.0), (-20.5, 12.0),
                        (20.5, -12.0), (20.5, 12.0))
SOURCE_SWITCH_TOP_Z = 4.3
MOUNT_PROFILE_RADIUS = 1.21
GEOMETRY_TOLERANCE = 1e-6


def _solid(shape, name):
    solids = shape.Solids()
    if len(solids) != 1 or not shape.isValid() or shape.Volume() <= 0:
        raise ValueError(f'{name} must be one valid, nonempty solid')
    return solids[0]


def _pcb_envelope(board):
    """Extract the original PCB perimeter, filling its internal holes only."""
    slab = board.intersect(box(60, 50, 0.7, 0.9))
    horizontal = [f for f in slab.Faces()
                  if f.geomType() == 'PLANE' and f.BoundingBox().zlen < 1e-7]
    if not horizontal:
        raise ValueError('Cannot find the source PCB outline')
    face = max(horizontal, key=lambda f: f.Area())
    wire = face.outerWire().translate((0, 0, -face.Center().z))
    return _solid(cq.Solid.extrudeLinear(wire, [], (0, 0, SOURCE_PCB_THICKNESS)),
                  'PCB envelope')


def _relocate_mount_features(board, centers):
    """Move each complete local hole/pad profile, including both PCB faces.

    The imported fused solid represents the copper-pad boundaries as shallow
    R1.2 surface recesses. Copying its local BREP preserves that representation
    and the R1.0 through bore without adding invented protruding metal rings.
    """
    if len(centers) != 4:
        raise ValueError('Exactly four mounting centers are required')
    centers = tuple(tuple(float(v) for v in p) for p in centers)
    if any(len(p) != 2 or not all(math.isfinite(v) for v in p) for p in centers):
        raise ValueError('Mounting centers must be finite XY pairs')

    outline = _pcb_envelope(board)
    for x, y in centers:
        column = cylinder(MOUNT_PROFILE_RADIUS, 0, SOURCE_PCB_THICKNESS, x, y)
        if column.cut(outline).Volume() > GEOMETRY_TOLERANCE:
            raise ValueError(f'Mounting bore/pad at {(x, y)} intersects the PCB border')
    for i, (x, y) in enumerate(centers):
        if any(math.hypot(x - qx, y - qy) <= 2 * MOUNT_PROFILE_RADIUS
               for qx, qy in centers[i + 1:]):
            raise ValueError('Mounting features overlap')

    if all(math.dist(old, new) < GEOMETRY_TOLERANCE
           for old, new in zip(SOURCE_MOUNT_CENTERS, centers)):
        return board

    old_columns = [cylinder(MOUNT_PROFILE_RADIUS, -0.15, 1.7, x, y)
                   for x, y in SOURCE_MOUNT_CENTERS]
    profiles = [_solid(board.intersect(column), 'Source mounting profile')
                for column in old_columns]
    # Restore FR4 at every old location before cutting any calibrated location;
    # the old and new circular neighborhoods may overlap.
    filled = board.cut(*old_columns).fuse(*[
        cylinder(MOUNT_PROFILE_RADIUS, 0, SOURCE_PCB_THICKNESS, x, y)
        for x, y in SOURCE_MOUNT_CENTERS
    ]).clean()
    new_columns = [cylinder(MOUNT_PROFILE_RADIUS, -0.15, 1.7, x, y)
                   for x, y in centers]
    moved_profiles = [profile.translate((new[0] - old[0], new[1] - old[1], 0))
                      for profile, old, new in zip(profiles, SOURCE_MOUNT_CENTERS, centers)]
    return _solid(filled.cut(*new_columns).fuse(*moved_profiles).clean(),
                  'Board with calibrated mounting features')


def load_hardware(source, c):
    """Return components, stationary compound, moving regions, and metadata.

    ``c`` is the dictionary returned by ``common.load_config``. Moving regions
    are conservative switch keepouts above the measured stationary height;
    the rough source STEP does not model each switch's internal moving parts.
    """
    source = Path(source)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    expected_digest = c.get('source_sha256')
    if expected_digest and digest != expected_digest:
        raise ValueError('Hardware STEP SHA-256 differs from the configured source')
    if abs(float(c['pcb_thickness']) - SOURCE_PCB_THICKNESS) > GEOMETRY_TOLERANCE:
        raise ValueError('This source STEP requires a 1.6 mm PCB thickness')

    imported = cq.importers.importStep(str(source)).val()
    solids = imported.Solids()
    if len(solids) != 2 or not imported.isValid():
        raise ValueError('Expected the supplied STEP to contain two valid solids')
    board, glass = sorted(solids, key=lambda s: s.BoundingBox().xlen, reverse=True)
    bb = board.BoundingBox()
    if abs(bb.xlen - 44) > 1e-5 or abs(bb.ylen - 27) > 1e-5:
        raise ValueError('The source PCB outline differs from the expected 44 x 27 mm')

    top_height = float(c['measured_switch_top_height'])
    fixed_height = float(c['measured_switch_fixed_height'])
    if not (0 < fixed_height < top_height and
            top_height <= SOURCE_SWITCH_TOP_Z - SOURCE_PCB_THICKNESS + GEOMETRY_TOLERANCE):
        raise ValueError('Measured fixed/top switch heights are outside the source model')
    button_x = float(c['button_x'])
    button_ys = tuple(float(y) for y in c['button_centers_y'])
    if len(button_ys) != 4 or not all(math.isfinite(v) for v in (button_x, *button_ys)):
        raise ValueError('Exactly four finite button XY positions are required')

    switch_cutters = [box(6.02, 3.22, SOURCE_PCB_THICKNESS,
                          SOURCE_SWITCH_TOP_Z + 0.01, SOURCE_BUTTON_X, y)
                      for y in SOURCE_BUTTON_YS]
    source_switches = [_solid(board.intersect(cutter), f'Source switch {i + 1}')
                       for i, cutter in enumerate(switch_cutters)]
    board_without_switches = _solid(board.cut(*switch_cutters).clean(),
                                   'Board and header without switches')
    centers = c['mount_centers']
    # Relocate in source coordinates, then use a physical rotation. Both
    # source Y and Z change sign when the PCB front faces enclosure -Z.
    source_centers = sorted((float(x), -float(y)) for x, y in centers)
    calibrated_board = _relocate_mount_features(board_without_switches, source_centers)

    transform_z = float(c['pcb_front_z']) + SOURCE_PCB_THICKNESS

    def to_enclosure(shape):
        return shape.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, transform_z))

    components = {'board_and_header': to_enclosure(calibrated_board),
                  'glass': to_enclosure(glass)}
    stationary = list(components.values())
    actuators = []
    split_z = SOURCE_PCB_THICKNESS + fixed_height
    top_z = min(SOURCE_PCB_THICKNESS + top_height, SOURCE_SWITCH_TOP_Z)
    for i, (switch, source_y, target_y) in enumerate(
            zip(source_switches, SOURCE_BUTTON_YS, button_ys), 1):
        delta = (button_x - SOURCE_BUTTON_X, -target_y - source_y, 0)
        fixed = _solid(switch.intersect(box(60, 50, SOURCE_PCB_THICKNESS, split_z)),
                       f'Fixed switch {i}').translate(delta)
        moving = _solid(switch.intersect(box(60, 50, split_z, top_z)),
                        f'Moving switch region {i}').translate(delta)
        fixed, moving = to_enclosure(fixed), to_enclosure(moving)
        components[f'switch_{i}_fixed'] = fixed
        components[f'switch_{i}_actuator'] = moving
        stationary.append(fixed)
        actuators.append(moving)

    fixed = cq.Compound.makeCompound(stationary)
    if not fixed.isValid() or any(not shape.isValid() for shape in components.values()):
        raise ValueError('Calibrated reference contains invalid native geometry')
    metadata = {
        'units': 'mm',
        'source_filename': source.name,
        'source_sha256': digest,
        'source_attribution': 'User-supplied community approximation attributed to Hellfire',
        'calibration_complete': bool(c.get('calibration_complete', False)),
        'coordinate_transform': {
            'rotation_axis': [1, 0, 0], 'rotation_degrees': 180,
            'translation': [0, 0, transform_z],
            'pcb_front_z': float(c['pcb_front_z']),
            'pcb_back_z': float(c['pcb_front_z']) + SOURCE_PCB_THICKNESS,
        },
        'nominal': {
            'pcb_width': 44.0, 'pcb_height': 27.0,
            'pcb_thickness': SOURCE_PCB_THICKNESS,
            'mount_centers': [list(p) for p in SOURCE_MOUNT_CENTERS],
            'mount_hole_pitch': [41.0, 24.0],
            'mount_bore_diameter': 2.0,
            'mount_surface_pad_diameter': 2.4,
            'mount_surface_recess_depth': 0.03,
            'button_x': SOURCE_BUTTON_X, 'button_centers_y': list(SOURCE_BUTTON_YS),
            'switch_envelope_xy': [6.0, 3.2], 'switch_top_height': 2.7,
            'glass_bounds_source': [[-16.9, -9.5, 1.6], [7.6, 7.0, 2.6]],
            'header_pitch_approximate': 18 / 7,
            'header_pin_count': 8,
            'header_rear_projection': 4.4,
        },
        'calibrated': {
            'mount_centers': [list(map(float, p)) for p in centers],
            'mount_hole_pitch': [float(c['mount_hole_pitch_x']), float(c['mount_hole_pitch_y'])],
            'button_x': button_x, 'button_centers_y': list(button_ys),
            'button_y_positions_origin': 'Approximate source STEP centers, with Y negated by the physical 180 degree X rotation; not physically measured',
            'switch_top_height': top_height, 'switch_fixed_height': fixed_height,
            'switch_top_trim': SOURCE_SWITCH_TOP_Z - top_z,
            'pcb_keepout_xy': [float(c['pcb_keepout_width']), float(c['pcb_keepout_height'])],
            'physical_header_pitch': float(c['header_pitch']),
            'physical_dupont_array_width': 8 * float(c['header_pitch']),
        },
        'uncertainties': [
            'Community STEP approximates the hardware; it is not a manufacturer drawing.',
            'Regions above the measured stationary height are conservative moving keepouts; '
            'the source includes part of its nominal metal chamfer in those regions.',
            'Mount pad profiles are relocated from the imported fused solid, which represents '
            'them as shallow surface recesses rather than protruding copper.',
            'Header geometry retains the source approximate pitch; connector ports must also '
            'clear the physical 2.54 mm DuPont array and wiring.',
            'Physical assembled fit and dimensions not explicitly measured remain unverified.',
        ],
        'components': {name: shape_info(shape) for name, shape in components.items()},
        'stationary': shape_info(fixed),
    }
    return {'components': components, 'fixed': fixed, 'actuators': actuators,
            'metadata': metadata}
