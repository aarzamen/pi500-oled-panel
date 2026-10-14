"""Generate the original case/stand without private paths or PCB redistribution."""
import argparse
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import hashlib
import json
import shutil
import sys
import tempfile
import uuid

import cadquery as cq
from lxml import etree as ET
import numpy as np
import trimesh

from common import load_config, box, rounded_box, shape_info, volume_intersection
from enclosure import build_enclosure, cap_in_assembly, connector_guide
from hardware import load_hardware
from stand import build_stand, case_pose

ROOT = Path(__file__).resolve().parent
PROJECT_NAME = 'OLED-case-CAD-v3.3mf'
M = 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'
P = 'http://schemas.microsoft.com/3dmanufacturing/production/2015/06'
REL = 'http://schemas.openxmlformats.org/package/2006/relationships'


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def native_mesh(shape):
    vs,fs=shape.tessellate(.015,.12)
    mesh=trimesh.Trimesh(np.array([v.toTuple() for v in vs]),np.array(fs),process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent
    return mesh


def stl_shape(shape,path):
    cq.exporters.export(shape,str(path),tolerance=.01,angularTolerance=.1)
    mesh=trimesh.load_mesh(path,process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent, path
    assert np.all(mesh.nondegenerate_faces()) and len(mesh.split())==1,path
    assert abs(mesh.bounds[0,2])<1e-5,path
    return mesh


def xml(root):
    return ET.tostring(root,encoding='UTF-8',xml_declaration=True,pretty_print=True)


def mesh_xml(mesh,pid):
    root=ET.Element('{'+M+'}model',nsmap={None:M,'p':P},unit='millimeter')
    rs=ET.SubElement(root,'{'+M+'}resources')
    ob=ET.SubElement(rs,'{'+M+'}object',id=str(pid),type='model')
    el=ET.SubElement(ob,'{'+M+'}mesh')
    vertices=ET.SubElement(el,'{'+M+'}vertices')
    for v in mesh.vertices:
        ET.SubElement(vertices,'{'+M+'}vertex',dict(zip(('x','y','z'),[format(float(t),'.12g') for t in v])))
    triangles=ET.SubElement(el,'{'+M+'}triangles')
    for f in mesh.faces:
        ET.SubElement(triangles,'{'+M+'}triangle',dict(zip(('v1','v2','v3'),[str(int(t)) for t in f])))
    return xml(root)


def meta(parent,key,value):
    return ET.SubElement(parent,'metadata',key=key,value=str(value))


def write_project(meshes,path,profile_path):
    main=ET.Element('{'+M+'}model',nsmap={None:M,'p':P},unit='millimeter',requiredextensions='p')
    ET.SubElement(main,'{'+M+'}metadata',name='Application').text='BambuStudio-02.06.01.55'
    ET.SubElement(main,'{'+M+'}metadata',name='BambuStudio:3mfVersion').text='1'
    ET.SubElement(main,'{'+M+'}metadata',name='Title').text='OLED case - CAD v3'
    ET.SubElement(main,'{'+M+'}metadata',name='Description').text='Original OLED enclosure and stand; case-only two-plate print project; standard cooldown and unload.'
    resources=ET.SubElement(main,'{'+M+'}resources')
    build=ET.SubElement(main,'{'+M+'}build')
    settings=ET.Element('config')
    model_rels=ET.Element('{'+REL+'}Relationships',nsmap={None:REL})
    archive={}
    # First plate: front, one dual-knockout cover, four independent keys.
    # Second plate: the optional matching stand, preserving the user's case work.
    specs=[('front',80,105,1),('back-dual-knockouts',150,105,1)]
    specs += [('button-cap',205,85+10*i,1) for i in range(4)]
    specs += [('stand',390,105,2)]
    plate_objects={1:[],2:[]}
    objects=[]
    for index,(name,x,y,plate) in enumerate(specs,1):
        pid,oid=2*index-1,2*index
        entry=f'3D/Objects/object_{index}.model'
        ob=ET.SubElement(resources,'{'+M+'}object',id=str(oid),type='model')
        ob.set('{'+P+'}UUID',str(uuid.uuid5(uuid.NAMESPACE_URL, f'oled-case-cad-v3:{index}:object')))
        cs=ET.SubElement(ob,'{'+M+'}components')
        co=ET.SubElement(cs,'{'+M+'}component',objectid=str(pid),transform='1 0 0 0 1 0 0 0 1 0 0 0')
        co.set('{'+P+'}path','/'+entry)
        co.set('{'+P+'}UUID',str(uuid.uuid5(uuid.NAMESPACE_URL, f'oled-case-cad-v3:{index}:component')))
        item=ET.SubElement(build,'{'+M+'}item',objectid=str(oid),transform=f'1 0 0 0 1 0 0 0 1 {x} {y} 0',printable='1')
        item.set('{'+P+'}UUID',str(uuid.uuid5(uuid.NAMESPACE_URL, f'oled-case-cad-v3:{index}:item')))
        mesh=meshes[name]
        archive[entry]=mesh_xml(mesh,pid)
        ET.SubElement(model_rels,'{'+REL+'}Relationship',Target='/'+entry,Id=f'rel-{index}',Type='http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel')
        conf=ET.SubElement(settings,'object',id=str(oid))
        objname=f'CAD v3 - {name}' if name!='button-cap' else f'CAD v3 - button {index-2}'
        meta(conf,'name',objname);meta(conf,'extruder',1)
        ET.SubElement(conf,'metadata',face_count=str(len(mesh.faces)))
        part=ET.SubElement(conf,'part',id=str(pid),subtype='normal_part')
        meta(part,'name',objname);meta(part,'extruder',1)
        meta(part,'matrix','1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1')
        ET.SubElement(part,'mesh_stat',face_count=str(len(mesh.faces)),edges_fixed='0',degenerate_facets='0',facets_removed='0',facets_reversed='0',backwards_edges='0')
        plate_objects[plate].append((oid,9000+index))
        objects.append({'object_id':oid,'part':name,'plate':plate,'label':9000+index})
    for plate_no,entries in plate_objects.items():
        plate=ET.SubElement(settings,'plate')
        meta(plate,'plater_id',plate_no)
        meta(plate,'plater_name','CAD v3 case + four keys' if plate_no==1 else 'CAD v3 matching stand')
        meta(plate,'locked','false')
        meta(plate,'filament_map_mode','Auto For Flush')
        meta(plate,'filament_maps','1')
        meta(plate,'filament_volume_maps','0')
        for oid,label in entries:
            instance=ET.SubElement(plate,'model_instance')
            meta(instance,'object_id',oid);meta(instance,'instance_id',0);meta(instance,'identify_id',label)
    archive['3D/3dmodel.model']=xml(main)
    archive['3D/_rels/3dmodel.model.rels']=xml(model_rels)
    archive['Metadata/model_settings.config']=xml(settings)
    config=json.loads(Path(profile_path).read_text())
    end=config['machine_end_gcode']
    if 'M140 S0' not in end or 'M104 S0' not in end or 'M620 S255' not in end or 'M140 S90' in end:
        raise ValueError('Public profile requires normal bed/hotend cooldown and filament unload')
    content_types=b'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/><Default Extension="config" ContentType="application/octet-stream"/><Default Extension="png" ContentType="image/png"/><Default Extension="gcode" ContentType="text/x.gcode"/></Types>'
    archive['Metadata/project_settings.config']=json.dumps(config,indent=2).encode()
    archive['[Content_Types].xml']=content_types
    root_rels=ET.Element('{'+REL+'}Relationships',nsmap={None:REL})
    ET.SubElement(root_rels,'{'+REL+'}Relationship',Target='/3D/3dmodel.model',Id='rel-1',Type='http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel')
    archive['_rels/.rels']=xml(root_rels)
    with ZipFile(path,'w',ZIP_DEFLATED) as z:
        for name,data in archive.items():
            entry=ZipInfo(name,date_time=(2026,10,14,0,0,0))
            entry.compress_type=ZIP_DEFLATED
            z.writestr(entry,data)
    return objects


def geometry_checks(parts, c, caps, hardware=None):
    """Check our native solids; optionally compare the user-supplied PCB STEP."""
    pressed = [cap_in_assembly(parts['button-cap'], c, i, c['cap_travel_check'])
               for i in range(4)]
    pose = case_pose(c)
    checks = {
        'cap_front_mm3': [volume_intersection(s, parts['front']) for s in caps],
        'pressed_cap_front_mm3': [volume_intersection(s, parts['front']) for s in pressed],
        'neighbor_cap_mm3': [volume_intersection(caps[i], caps[i + 1]) for i in range(3)],
        'front_cover_mm3': volume_intersection(parts['front'], parts['back-dual-knockouts']),
        'stand_front_mm3': volume_intersection(parts['stand'], parts['front'].moved(pose)),
        'stand_cover_mm3': volume_intersection(parts['stand'], parts['back-dual-knockouts'].moved(pose)),
        'stand_caps_mm3': [volume_intersection(parts['stand'], s.moved(pose)) for s in caps],
        'stand_connector_mm3': [volume_intersection(parts['stand'], connector_guide(c, i).moved(pose))
                                for i in range(2)],
        'open_connector_mm3': [volume_intersection(
            parts['back-upper-open' if y > 0 else 'back-lower-open'], connector_guide(c, i))
            for i, (x, y) in enumerate(c['header_centers'])],
    }
    if hardware is not None:
        fixed = hardware['fixed']
        checks.update({
            'front_hardware_mm3': volume_intersection(parts['front'], fixed),
            'cover_hardware_mm3': {n: volume_intersection(parts[n], fixed)
                                   for n in parts if n.startswith('back-')},
            'cap_fixed_hardware_mm3': [volume_intersection(s, fixed) for s in caps],
            'pressed_cap_fixed_hardware_mm3': [volume_intersection(s, fixed) for s in pressed],
        })
        glass_info = shape_info(hardware['components']['glass'])
        glass_z = sum(row[2] for row in glass_info['bounds']) / 2
        probe = rounded_box(c['glass_width'] - 2 * c['window_overlap_x'],
                            c['glass_height'] - 2 * c['window_overlap_y'], .65,
                            glass_z + .05, glass_z + .15, c['glass_center_x'], c['glass_center_y'])
        checks['display_throat_outside_glass_body_mm3'] = probe.cut(hardware['components']['glass']).Volume()

    def require_zero(values):
        if isinstance(values, dict):
            for v in values.values():
                require_zero(v)
        elif isinstance(values, list):
            for v in values:
                require_zero(v)
        elif abs(values) >= 1e-5:
            raise ValueError(f'Unexpected modeled intersection: {values} mm3')

    require_zero(checks)
    closed = [volume_intersection(parts['back-dual-knockouts'], connector_guide(c, i))
              for i in range(2)]
    if not all(v > 50 for v in closed):
        raise ValueError('Closed knockout panels must obstruct the modeled connector paths')
    checks['closed_connector_mm3'] = closed
    checks['knockout_membrane_mm'] = c['knockout_membrane']
    physical_pcb = box(c['pcb_keepout_width'], c['pcb_keepout_height'], c['pcb_front_z'], c['pcb_back_z'])
    arm_outer = (c['case_width'] - 2 * c['wall']) / 2 - c['fit']
    compression = c['fit'] + c['snap_engagement']
    checks['snap_compression_mm'] = compression
    checks['compressed_arm_pcb_mm3'] = []
    for sign in (-1, 1):
        arm = box(c['snap_thickness'], c['snap_width'],
                  c['snap_shoulder_z'] - c['snap_lead_height'] - .05, c['cover_inside_z'] + .12,
                  sign * (arm_outer - c['snap_thickness'] / 2 - compression), 0)
        checks['compressed_arm_pcb_mm3'].append(volume_intersection(arm, physical_pcb))
    require_zero(checks['compressed_arm_pcb_mm3'])
    clearance = arm_outer - c['snap_thickness'] - compression - c['pcb_keepout_width'] / 2
    if clearance < .25:
        raise ValueError('Compressed snap arm has insufficient modeled PCB clearance')
    checks['compressed_arm_radial_clearance_mm'] = clearance
    for x, y in c['header_centers']:
        probe = rounded_box(c['knockout_width'] + .6, c['knockout_height'] + .6,
                            c['knockout_radius'] + .3, c['case_depth'] - .2,
                            c['case_depth'] - .05, x, y)
        require_zero(probe.cut(parts['back-dual-knockouts']).Volume())
    return checks


def validate_reference_rotation(source, hardware, c):
    """Compare glass against an independent proper 180-degree rotation."""
    raw = cq.importers.importStep(str(source)).val()
    original_glass = sorted(raw.Solids(), key=lambda s: s.BoundingBox().xlen, reverse=True)[1]
    expected = original_glass.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, c['pcb_back_z']))
    actual = hardware['components']['glass']
    error = actual.cut(expected).Volume() + expected.cut(actual).Volume()
    if abs(error) > 1e-5 or abs(actual.Center().y + original_glass.Center().y) > 1e-5:
        raise ValueError('Reference must use a rigid 180-degree X rotation with negated Y')
    return {
        'rotation_axis': [1, 0, 0], 'rotation_degrees': 180,
        'matrix': [[1, 0, 0], [0, -1, 0], [0, 0, -1]], 'determinant': 1,
        'symmetric_difference_mm3': error, 'source_y_negated': True,
    }


def export_to(destination, c, profile, hardware=None, hardware_source=None, preview=True):
    parts = build_enclosure(c)
    parts['stand'] = build_stand(c)
    caps = [cap_in_assembly(parts['button-cap'], c, i) for i in range(4)]
    checks = geometry_checks(parts, c, caps, hardware)
    for folder in ('STL', 'STEP', 'source', 'evidence'):
        (destination / folder).mkdir()
    printable, step_checks = {}, {}
    for name, shape in parts.items():
        if not shape.isValid() or len(shape.Solids()) != 1:
            raise ValueError(f'{name} must be one valid native solid')
        step = destination / 'STEP' / (name + '.step')
        cq.exporters.export(shape, str(step))
        loaded = cq.importers.importStep(str(step)).val()
        difference = abs(loaded.Volume() - shape.Volume())
        if not loaded.isValid() or len(loaded.Solids()) != 1 or difference > max(.001, shape.Volume() * 1e-6):
            raise ValueError(f'{name} STEP round-trip failed')
        step_checks[name] = {'valid': True, 'solids': 1, 'volume_difference_mm3': difference}
        # Proper rigid rotation: (x,y,z) -> (x,-y,case_depth-z), determinant +1.
        print_shape = shape.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, c['case_depth'])) \
            if name.startswith('back-') else shape
        printable[name] = stl_shape(print_shape, destination / 'STL' / (name + '.stl'))

    assembly = cq.Assembly(name='OLED_case_CAD_v3')
    assembly.add(parts['front'], name='front', color=cq.Color(.87, .88, .87))
    assembly.add(parts['back-lower-open'], name='back_lower_open', color=cq.Color(.24, .30, .33))
    for i, cap in enumerate(caps, 1):
        assembly.add(cap, name=f'key_{i}', color=cq.Color(.81, .62, .29))
    assembly_path = destination / 'STEP' / 'enclosure-only.step'
    assembly.export(str(assembly_path))
    reloaded = cq.importers.importStep(str(assembly_path)).val()
    if not reloaded.isValid() or len(reloaded.Solids()) != 6:
        raise ValueError('Case-only STEP assembly must contain front, one cover, and four caps')
    reference_status = {'status': 'not-requested', 'geometry_redistributed': False,
                        'note': 'Hardware collision checks require a separately supplied original STEP.'}
    if hardware is not None:
        reference_status = {
            'status': 'passed', 'geometry_redistributed': False,
            'source_sha256': digest(hardware_source),
            'proper_rotation_check': validate_reference_rotation(hardware_source, hardware, c),
            'components': hardware['metadata']['components'],
            'uncertainties': hardware['metadata']['uncertainties'],
        }
    report = {
        'units': 'mm', 'physical_fit_status': 'unverified',
        'dimensions': {k: c[k] for k in ('case_width', 'case_height', 'case_depth', 'pcb_front_z',
                                        'pcb_back_z', 'post_height', 'post_base_height',
                                        'measured_switch_top_height', 'measured_switch_fixed_height')},
        'parameters': c, 'parts': {n: shape_info(s) for n, s in parts.items()},
        'checks': checks, 'hardware_reference': reference_status,
        'step_round_trip': step_checks,
        'enclosure_assembly': {'file': 'STEP/enclosure-only.step', 'valid': True, 'solids': 6,
                              'hardware_included': False},
        'print_rotation': {'rotation_axis': [1, 0, 0], 'rotation_degrees': 180,
                           'determinant': 1, 'translation': [0, 0, c['case_depth']]},
        'print_stl_sha256': {n: digest(destination / 'STL' / (n + '.stl')) for n in printable},
        'tools': {'python': sys.version.split()[0], 'cadquery': cq.__version__, 'trimesh': trimesh.__version__},
    }
    report['project_objects'] = write_project(printable, destination / PROJECT_NAME, profile)
    for f in ROOT.iterdir():
        if f.is_file() and f.suffix in ('.py', '.json', '.txt', '.md'):
            shutil.copy2(f, destination / 'source' / f.name)
    shutil.copytree(ROOT / 'profiles', destination / 'source' / 'profiles')
    # Carry the selected inputs into the new kit so its next rebuild agrees.
    (destination / 'source' / 'parameters.json').write_text(json.dumps(c, indent=2) + '\n')
    shutil.copy2(profile, destination / 'source' / 'profiles' / 'x1c-abs-standard.json')
    readme = ROOT.parent / 'README.md'
    if readme.is_file():
        shutil.copy2(readme, destination / 'README.md')
    license_file = ROOT.parent / 'LICENSE'
    if license_file.is_file():
        shutil.copy2(license_file, destination / 'LICENSE')
    if preview:
        from preview import render_preview
        render_preview({n: native_mesh(s) for n, s in parts.items()},
                       [native_mesh(s) for s in caps], c, destination / 'assembly-preview.png')
    (destination / 'evidence' / 'geometry-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    (destination / '.cad-v3-output.json').write_text(json.dumps({'generator': 'OLED case CAD v3', 'version': 1}) + '\n')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('cad-v3-output'),
                        help='New local output directory (default: cad-v3-output in the current directory)')
    parser.add_argument('--parameters', type=Path, default=ROOT / 'parameters.json')
    parser.add_argument('--profile', type=Path, default=ROOT / 'profiles' / 'x1c-abs-standard.json')
    parser.add_argument('--hardware-step', type=Path,
                        help='Optional original Hellfire STEP, checked by SHA-256; never copied or exported')
    parser.add_argument('--replace', action='store_true',
                        help='Replace an output bearing this generator marker; other nonempty directories are refused')
    parser.add_argument('--no-preview', action='store_true', help='Skip PNG rendering')
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if output == ROOT or output in ROOT.parents:
        parser.error('The output must not replace the source directory or its parents')
    if output.exists() and any(output.iterdir()):
        marker = output / '.cad-v3-output.json'
        if not args.replace or not marker.is_file():
            parser.error('Output is nonempty; choose a new directory or use --replace on a generated output')
        try:
            if json.loads(marker.read_text()).get('generator') != 'OLED case CAD v3':
                parser.error('Output marker does not belong to this generator')
        except (ValueError, OSError):
            parser.error('Output marker is invalid')
    c = load_config(args.parameters)
    hardware = None
    try:
        if args.hardware_step is not None:
            hardware = load_hardware(args.hardware_step, c)
        output.parent.mkdir(parents=True, exist_ok=True)
        # Build first. A failed validation leaves the prior output untouched.
        with tempfile.TemporaryDirectory(prefix='.oled-cad-build-', dir=output.parent) as temp:
            staging = Path(temp) / 'kit'
            staging.mkdir()
            report = export_to(staging, c, args.profile, hardware, args.hardware_step, not args.no_preview)
            if output.exists():
                shutil.rmtree(output)
            staging.rename(output)
    except (ValueError, OSError, AssertionError, RuntimeError) as exc:
        parser.exit(1, f'Export failed: {exc}\n')
    print(json.dumps({'output': str(args.output), 'parts': list(report['parts']),
                      'hardware_reference': report['hardware_reference']['status'],
                      'physical_fit_status': 'unverified'}, indent=2))
    return report


if __name__ == '__main__':
    main()

