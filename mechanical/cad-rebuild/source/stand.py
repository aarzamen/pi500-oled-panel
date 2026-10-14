"""Native two-rail cradle for the rebuilt OLED enclosure.

Enclosure coordinates are X left/right, Y bottom/top, and Z front/rear.
Print coordinates are X left/right, Y front/back, and Z up; the front of
the display faces positive print Y.  ``case_pose`` applies the same pose
used to construct the cradle, so assembly and collision checks agree.
"""

import math

import cadquery as cq

from common import fuse, rounded_box


def stand_dimensions(c):
    """Return the construction dimensions without modifying the config."""
    width = float(c['case_width'])
    height = float(c['case_height'])
    depth = float(c['case_depth'])
    clearance = float(c['stand_clearance'])
    tilt = float(c['stand_tilt_degrees'])
    if min(width, height, depth) <= 0 or clearance <= 0:
        raise ValueError('Case dimensions and stand clearance must be positive')
    if not 0 <= tilt <= 30:
        raise ValueError('This stand supports a rearward tilt of 0 to 30 degrees')

    d = {
        'rail_width': 6.0,
        'rail_center_x': width / 2.0 - 3.0,
        'rail_corner_radius': 1.0,
        'front_jaw_height': 7.0,
        'back_jaw_height': 12.0,
        'front_jaw_thickness': 2.4,
        'back_jaw_thickness': 2.8,
        'floor_thickness': 2.4,
        'base_width': width + 5.5,
        'base_depth': 36.0,
        'base_thickness': 2.8,
        'base_corner_radius': 3.0,
        'base_overlap': 0.6,
        'case_bottom_y': -height / 2.0,
        'front_inner_z': -clearance,
        'back_inner_z': depth + clearance,
        'case_translation_y': 4.0,
        'tilt_degrees': tilt,
        'cable_notch_width': 26.0,
        'cable_notch_front_y': -4.0,
    }
    d['rail_bottom_y'] = d['case_bottom_y'] - d['floor_thickness']
    d['front_outer_z'] = d['front_inner_z'] - d['front_jaw_thickness']
    d['back_outer_z'] = d['back_inner_z'] + d['back_jaw_thickness']
    d['cradle_gap'] = d['back_inner_z'] - d['front_inner_z']
    theta = math.radians(tilt)
    # Raise the lowest, rear corner of the cradle into the base by 0.6 mm.
    d['case_translation_z'] = (
        d['base_thickness'] - d['base_overlap']
        - math.cos(theta) * d['rail_bottom_y']
        + math.sin(theta) * d['back_outer_z']
    )
    return d


def case_pose(c):
    """Map an enclosure solid into its seated, rearward-leaning position.

    Use ``shape.moved(case_pose(c))`` for a case or other object already
    expressed in enclosure coordinates. The unrotated case bottom is
    Y=-case_height/2 and the front face is Z=0.
    """
    d = stand_dimensions(c)
    return cq.Location(
        cq.Vector(0, d['case_translation_y'], d['case_translation_z']),
        cq.Vector(1, 0, 0),
        90.0 + d['tilt_degrees'],
    )


def _pose_yz(y, z, d):
    """Transform one side-profile point into print coordinates."""
    angle = math.radians(90.0 + d['tilt_degrees'])
    return (
        math.cos(angle) * y - math.sin(angle) * z + d['case_translation_y'],
        math.sin(angle) * y + math.cos(angle) * z + d['case_translation_z'],
    )


def _side_profile(points, rail_x, rail_width):
    """Extrude a Y/Z outline along X, centered on one cradle rail."""
    return (
        cq.Workplane('YZ', origin=(rail_x - rail_width / 2.0, 0, 0))
        .polyline(points)
        .close()
        .extrude(rail_width)
        .val()
    )


def _cradle(rail_x, d, pose):
    bottom = d['case_bottom_y']
    floor_bottom = d['rail_bottom_y']
    front_height = d['front_jaw_height'] + d['floor_thickness']
    back_height = d['back_jaw_height'] + d['floor_thickness']
    rail_width = d['rail_width']
    radius = d['rail_corner_radius']

    floor = rounded_box(
        rail_width, d['floor_thickness'], radius,
        d['front_outer_z'], d['back_outer_z'],
        x=rail_x, y=(floor_bottom + bottom) / 2.0,
    )
    front = rounded_box(
        rail_width, front_height, radius,
        d['front_outer_z'], d['front_inner_z'],
        x=rail_x, y=floor_bottom + front_height / 2.0,
    )
    back = rounded_box(
        rail_width, back_height, radius,
        d['back_inner_z'], d['back_outer_z'],
        x=rail_x, y=floor_bottom + back_height / 2.0,
    )
    return fuse((floor, front, back)).moved(pose)


def build_stand(c):
    """Build one native CAD solid, resting flat at print Z=0.

    The 6 mm corner cradles keep the central X=-12..12 connector path
    open. Their floor seats the case bottom, and the two inner jaw faces
    leave ``stand_clearance`` on each side of the case depth. Sloping
    wedges below each cradle and triangular rear struts connect to the
    base without an unsupported horizontal cradle floor.
    """
    d = stand_dimensions(c)
    pose = case_pose(c)
    base = rounded_box(
        d['base_width'], d['base_depth'], d['base_corner_radius'],
        0, d['base_thickness'],
    )
    # This opening reaches beyond the rear edge, leaving two rear feet.
    notch_rear = -d['base_depth'] / 2.0 - 4.0
    notch_front = d['cable_notch_front_y']
    notch = rounded_box(
        d['cable_notch_width'], notch_front - notch_rear, 1.4,
        -1.0, d['base_thickness'] + 1.0,
        y=(notch_front + notch_rear) / 2.0,
    )
    base = base.cut(notch).clean()
    parts = [base]
    base_join_z = d['base_thickness'] - d['base_overlap']

    for side in (-1, 1):
        rail_x = side * d['rail_center_x']
        parts.append(_cradle(rail_x, d, pose))

        # Fill under the angled floor. The upper edge overlaps the
        # rounded cradle by 0.4 mm while remaining below the case seat.
        front_top = _pose_yz(d['rail_bottom_y'] + 0.4, d['front_outer_z'], d)
        back_top = _pose_yz(d['rail_bottom_y'] + 0.4, d['back_outer_z'], d)
        floor_support = _side_profile(
            [back_top, front_top,
             (front_top[0], base_join_z), (back_top[0], base_join_z)],
            rail_x, d['rail_width'],
        )
        parts.append(floor_support)

        # The whole rear strut lies behind the rear jaw's inner plane.
        # Its upper point is inside the rear jaw, giving a real overlap.
        support_z = d['back_inner_z'] + d['back_jaw_thickness'] * 0.6
        rear_top = _pose_yz(d['case_bottom_y'] + d['back_jaw_height'] - 1.0,
                            support_z, d)
        rear_front = _pose_yz(d['rail_bottom_y'] + 0.2, support_z, d)
        rear_foot_y = -d['base_depth'] / 2.0 + 3.5
        rear_strut = _side_profile(
            [rear_front, rear_top, (rear_foot_y, base_join_z)],
            rail_x, d['rail_width'],
        )
        rear_strut = cq.Workplane(obj=rear_strut).edges('|X').fillet(0.65).val()
        parts.append(rear_strut)

    result = fuse(parts).clean()
    if not result.isValid() or len(result.Solids()) != 1:
        raise RuntimeError('Stand construction did not produce one valid solid')
    if abs(result.BoundingBox().zmin) > 1e-6:
        raise RuntimeError('Stand construction did not rest at print Z=0')
    return result
