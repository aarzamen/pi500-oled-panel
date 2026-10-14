"""Native CAD case with independent keys and two sealed header knockouts."""
import cadquery as cq
from common import box, rounded_box, cylinder, fuse


def ring(w,h,r,thickness,z0,z1):
    return rounded_box(w,h,r,z0,z1).cut(rounded_box(w-2*thickness,h-2*thickness,max(0,r-thickness),z0-0.1,z1+0.1)).clean()


def xz_prism(points, width):
    return cq.Workplane('XZ').polyline(points).close().extrude(width).translate((0,width/2,0)).val()


def make_cap(c):
    flange=rounded_box(c['cap_flange_width'],c['cap_flange_height'],1.2,0,c['cap_flange_depth'])
    key=rounded_box(c['cap_width'],c['cap_height'],0.55,c['cap_flange_depth']-0.02,c['cap_total_depth'])
    return flange.fuse(key).clean()


def cap_in_assembly(cap,c,index,travel=0):
    # Flange lies behind the face, with keys projecting toward the viewer.
    rear=c['face']+c['cap_release_gap']+c['cap_flange_depth']+travel
    return cap.rotate((0,0,0),(1,0,0),180).translate((c['button_x'],c['button_centers_y'][index],rear))


def knockout_tool(c,x,y,full_open=False):
    z=c['cover_inside_z']
    if full_open:
        return rounded_box(c['knockout_width'],c['knockout_height'],c['knockout_radius'],c['pcb_back_z']+.1,c['case_depth']+.1,x,y)
    # Inside score groove leaves a continuous outer membrane. No through slots.
    outer=rounded_box(c['knockout_width']+2*c['knockout_score_width'],c['knockout_height']+2*c['knockout_score_width'],c['knockout_radius']+c['knockout_score_width'],z-.05,c['case_depth']-c['knockout_membrane'],x,y)
    center=rounded_box(c['knockout_width'],c['knockout_height'],c['knockout_radius'],z-.1,c['case_depth']+.1,x,y)
    return outer.cut(center).clean()


def build_enclosure(c):
    w,h,r=c['case_width'],c['case_height'],c['corner_radius']
    wall,face,seam=c['wall'],c['face'],c['cover_seam_z']
    iw,ih=w-2*wall,h-2*wall
    ir=max(.5,r-wall)
    outer=rounded_box(w,h,r,0,seam)
    cavity=rounded_box(iw,ih,ir,face,seam+.1)
    front=outer.cut(cavity)
    sw=c['glass_width']-2*c['window_overlap_x']
    sh=c['glass_height']-2*c['window_overlap_y']
    aperture=rounded_box(sw,sh,.65,-.1,face+.1,c['glass_center_x'],c['glass_center_y'])
    front=front.cut(aperture)
    cuts=[]
    for y in c['button_centers_y']:
        cuts.append(rounded_box(c['cap_width']+2*c['cap_side_clearance'],c['cap_height']+2*c['cap_side_clearance'],.55+c['cap_side_clearance'],-.1,face+.1,c['button_x'],y))
    front=front.cut(*cuts)
    posts=[]
    for x,y in c['mount_centers']:
        base=cylinder(c['post_base_diameter']/2,face-.02,face+c['post_base_height'],x,y)
        post=cylinder(c['post_diameter']/2,face+c['post_base_height'],c['pcb_front_z'],x,y)
        boss=base.fuse(post)
        pilot=cylinder(c['pilot_diameter']/2,c['pcb_front_z']-c['pilot_depth'],c['pcb_front_z']+.05,x,y)
        # A shallow relief accommodates the reference board's mounting recess.
        relief=cylinder(1.25,c['pcb_front_z']-.12,c['pcb_front_z']+.05,x,y)
        posts.append(boss.cut(pilot,relief))
    front=front.fuse(*posts).clean()

    shoulder=c['snap_shoulder_z']
    window_low=shoulder-c['snap_lead_height']-.1
    window_high=shoulder+.12
    for sign in (-1,1):
        window=box(wall+0.4,c['snap_width']+.6,window_low,window_high,sign*(w/2-wall/2),0)
        front=front.cut(window)
    front=front.clean()

    depth,inner=c['case_depth'],c['cover_inside_z']
    back_outer=rounded_box(w,h,r,seam,depth)
    back_cavity=rounded_box(iw,ih,ir,seam-.1,inner)
    back=back_outer.cut(back_cavity)
    lip_z0=c['pcb_back_z']+.35
    lip_w,lip_h=iw-2*c['fit'],ih-2*c['fit']
    lip_r=max(.5,ir-c['fit'])
    lip=ring(lip_w,lip_h,lip_r,0.9,lip_z0,seam+.12)
    # A ledge bridges the fit gap between the guide lip and cover walls.
    # Keep this ledge clear of the flexible arms too.
    ledge_outer=rounded_box(iw+.04,ih+.04,ir+.02,seam,seam+.3)
    ledge_inner=rounded_box(lip_w-1.8,lip_h-1.8,max(.4,lip_r-.9),seam-.1,seam+.4)
    ledge=ledge_outer.cut(ledge_inner)
    arms=[]
    for sign in (-1,1):
        # Remove the guide ring near each flexible arm so it cannot shorten
        # the cantilever or couple the arm to a stationary side rail.
        gap=box(wall+3,c['snap_width']+1.0,lip_z0-.1,seam+.4,sign*(w/2-wall),0)
        lip=lip.cut(gap)
        ledge=ledge.cut(gap)
        arm_outer=iw/2-c['fit']
        arm_inner=arm_outer-c['snap_thickness']
        shaft=box(c['snap_thickness'],c['snap_width'],window_low+.05,inner+.12,sign*(arm_outer+arm_inner)/2,0)
        tip=iw/2+c['snap_engagement']
        points=[(arm_inner,window_low+.05),(arm_outer,window_low+.05),(tip,shoulder-.25),(tip,shoulder),(arm_inner,shoulder)]
        if sign<0:
            points=[(-x,z) for x,z in points[::-1]]
        hook=xz_prism(points,c['snap_width'])
        arms.append(shaft.fuse(hook))
    back=back.fuse(lip,ledge,*arms).clean()
    for x,y in c['header_centers']:
        back=back.cut(knockout_tool(c,x,y)).clean()
    variants={'back-dual-knockouts':back}
    for x,y in c['header_centers']:
        name='back-upper-open' if y>0 else 'back-lower-open'
        variants[name]=back.cut(knockout_tool(c,x,y,True)).clean()
    cap=make_cap(c)
    out={'front':front,'button-cap':cap,**variants}
    for name,s in out.items():
        assert s.isValid() and len(s.Solids())==1,(name,s.isValid(),len(s.Solids()))
    return out


def connector_guide(c,index):
    x,y=c['header_centers'][index]
    return box(8*c['header_pitch'],4.2,c['pcb_back_z'],c['case_depth']+15,x,y)


if __name__=='__main__':
    from common import load_config,shape_info,volume_intersection
    import json
    c=load_config()
    parts=build_enclosure(c)
    print(json.dumps({n:shape_info(s) for n,s in parts.items()},indent=2))
    for name in ('back-dual-knockouts','back-upper-open','back-lower-open'):
        print(name,'front collision',volume_intersection(parts['front'],parts[name]))
