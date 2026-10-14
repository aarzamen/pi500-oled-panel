import json
import math
from pathlib import Path
import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib


def load_config(path=None):
    path = Path(path) if path else Path(__file__).with_name('parameters.json')
    c = json.loads(path.read_text())
    c['pcb_front_z'] = c['face'] + c['measured_switch_top_height'] + c['cap_flange_depth'] + c['cap_release_gap']
    c['pcb_back_z'] = c['pcb_front_z'] + c['pcb_thickness']
    minimum = c['pcb_back_z'] + c['header_rear_projection'] + c['rear_clearance'] + c['cover_face']
    c['case_depth'] = math.ceil((minimum - 1e-9) / c['layer_height']) * c['layer_height']
    c['cover_inside_z'] = c['case_depth'] - c['cover_face']
    c['post_base_height'] = c['pcb_front_z'] - c['face'] - c['post_height']
    c['mount_centers'] = [(sx*c['mount_hole_pitch_x']/2, sy*c['mount_hole_pitch_y']/2+c['mount_hole_y_offset']) for sx in (-1,1) for sy in (-1,1)]
    c['header_centers'] = [(c['header_x'],c['header_y']),(-c['header_x'],-c['header_y'])]
    assert c['post_base_height'] >= 0
    assert c['cover_seam_z'] > c['pcb_back_z'] + 0.3
    assert 0 < c['knockout_membrane'] < c['cover_face']
    return c


def box(w, h, z0, z1, x=0, y=0):
    assert z1 > z0
    return cq.Workplane('XY').box(w,h,z1-z0,centered=(True,True,False)).translate((x,y,z0)).val()


def rounded_box(w, h, r, z0, z1, x=0, y=0):
    assert z1 > z0 and 0 <= r < min(w,h)/2
    q = cq.Workplane('XY').box(w,h,z1-z0,centered=(True,True,False))
    if r:
        q = q.edges('|Z').fillet(r)
    return q.translate((x,y,z0)).val()


def cylinder(radius,z0,z1,x=0,y=0):
    return cq.Workplane('XY').circle(radius).extrude(z1-z0).translate((x,y,z0)).val()


def fuse(shapes):
    shapes=list(shapes)
    assert shapes
    return shapes[0].fuse(*shapes[1:]).clean() if len(shapes)>1 else shapes[0]


def volume_intersection(a,b):
    q=a.intersect(b)
    solids=q.Solids()
    if solids and not q.isValid():
        raise RuntimeError('The CAD kernel returned an invalid collision result')
    return sum(s.Volume() for s in solids)


def shape_info(s):
    b=Bnd_Box()
    BRepBndLib.AddOptimal_s(s.wrapped,b,False,False)
    lohi=b.Get()
    lo,hi=lohi[:3],lohi[3:]
    return {'valid':s.isValid(),'solids':len(s.Solids()),'volume_mm3':s.Volume(),'dimensions_mm':[hi[i]-lo[i] for i in range(3)], 'bounds':[list(lo),list(hi)]}
