"""Render the exported native meshes; no illustrated or inferred geometry."""
from pathlib import Path
import argparse
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray, vtk_to_numpy
import numpy as np
import trimesh


COLORS = {'front': '#e8e7df', 'back': '#596b76', 'key': '#d9a94e',
          'stand': '#667b87'}


def paint(ax, mesh, color, shift=(0, 0, 0), pose=None, alpha=1):
    q = mesh.copy()
    if pose is not None:
        q.apply_transform(pose)
    q.apply_translation(shift)
    if not hasattr(ax, '_geometry'):
        ax._geometry = []
    ax._geometry.append((q, color))
    return q.bounds


def render_geometry(entries, direction, up):
    """Render with a depth buffer so internal parts cannot draw over the face."""
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(*matplotlib.colors.to_rgb('#f5f5ef'))
    vertices = []
    for mesh, color in entries:
        points = vtk.vtkPoints()
        points.SetData(numpy_to_vtk(np.asarray(mesh.vertices), deep=True))
        triangles = np.c_[np.full(len(mesh.faces), 3), mesh.faces].astype(np.int64)
        cells = vtk.vtkCellArray()
        cells.ImportLegacyFormat(numpy_to_vtkIdTypeArray(triangles.ravel(), deep=True))
        data = vtk.vtkPolyData(); data.SetPoints(points); data.SetPolys(cells)
        normals = vtk.vtkPolyDataNormals()
        normals.SetInputData(data); normals.SetFeatureAngle(35)
        normals.SplittingOn(); normals.ConsistencyOn()
        mapper = vtk.vtkPolyDataMapper(); mapper.SetInputConnection(normals.GetOutputPort())
        actor = vtk.vtkActor(); actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetColor(*matplotlib.colors.to_rgb(color))
        prop.SetAmbient(.24); prop.SetDiffuse(.76)
        prop.SetSpecular(.18); prop.SetSpecularPower(32)
        prop.SetInterpolationToPhong()
        renderer.AddActor(actor)
        vertices.append(mesh.vertices)
    points = np.concatenate(vertices)
    center = (points.min(axis=0)+points.max(axis=0))/2
    view = np.asarray(direction, float); view /= np.linalg.norm(view)
    forward = -view
    right = np.cross(forward, up); right /= np.linalg.norm(right)
    effective_up = np.cross(right, forward)
    relative = points-center
    x, y = relative@right, relative@effective_up
    camera = renderer.GetActiveCamera()
    camera.SetPosition(*(center+view*150))
    camera.SetFocalPoint(*center); camera.SetViewUp(*up)
    camera.ParallelProjectionOn()
    camera.SetParallelScale(max(np.ptp(y), np.ptp(x)/1.5)/2*1.16)
    for offset, intensity in ((np.array([-40, 55, -80]), .9),
                              (np.array([65, 20, 35]), .55)):
        light = vtk.vtkLight(); light.SetLightTypeToSceneLight()
        light.SetPosition(*(center+offset)); light.SetFocalPoint(*center)
        light.SetIntensity(intensity); renderer.AddLight(light)
    window = vtk.vtkRenderWindow(); window.SetOffScreenRendering(1)
    window.SetSize(1050, 700); window.SetMultiSamples(8)
    window.AddRenderer(renderer); renderer.ResetCameraClippingRange()
    window.Render()
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(window); capture.SetInputBufferTypeToRGB()
    capture.ReadFrontBufferOff(); capture.Update()
    rendered = capture.GetOutput()
    width, height, _ = rendered.GetDimensions()
    pixels = vtk_to_numpy(rendered.GetPointData().GetScalars()).reshape(height, width, 3)
    result = pixels[::-1].copy()
    window.Finalize()
    return result


def finish(ax, bounds, elev, azim, title, subtitle):
    if title == 'Matching stand':
        direction, up = [65, 100, 65], [0, 0, 1]
    elif title == 'Exploded assembly':
        direction, up = [-70, 25, -20], [0, 1, 0]
    else:
        direction, up = [-30, 25, -90], [0, 1, 0]
    ax.imshow(render_geometry(ax._geometry, direction, up))
    ax.axis('off')
    ax.set_facecolor('#f5f5ef')
    ax.set_title(title, loc='left', pad=25, fontsize=15,
                 fontweight='bold', color='#203941')
    ax.text(0, 1.04, subtitle, transform=ax.transAxes, fontsize=10,
             color='#526269')


def render_preview(parts, caps, c, output):
    """Use the same own CAD meshes as the native exports."""
    fig = plt.figure(figsize=(14, 10), facecolor='#f5f5ef')
    fig.suptitle('OLED enclosure · CAD v3', x=.04, y=.975, ha='left',
                 color='#203941', fontsize=24, fontweight='bold')
    fig.text(.04, .92,
             f"{c['case_width']:g} × {c['case_height']:g} × {c['case_depth']:g} mm"
             '   /   case and stand   /   native STEP + STL',
             color='#526269', fontsize=12)
    ax = fig.add_subplot(221)
    bounds = [paint(ax, parts['front'], COLORS['front']),
              paint(ax, parts['back-lower-open'], COLORS['back'])]
    for cap in caps:
        bounds.append(paint(ax, cap, COLORS['key']))
    finish(ax, bounds, -62, -75, 'Case shell and keys', 'Empty display opening; hardware omitted')
    plt.imsave(Path(output).with_name('case-preview.png'),
               render_geometry(ax._geometry, [-30, 25, -90], [0, 1, 0]))

    ax = fig.add_subplot(222)
    bounds = [paint(ax, parts['back-dual-knockouts'], COLORS['back'])]
    finish(ax, bounds, -61, -75, 'Inside the back cover',
           f"Two scored rear panels; {c['knockout_membrane']:g} mm sealed membranes")

    ax = fig.add_subplot(223)
    bounds = [paint(ax, parts['front'], COLORS['front'], shift=(0, 0, -8)),
              paint(ax, parts['back-lower-open'], COLORS['back'], shift=(0, 0, 14))]
    for cap in caps:
        bounds.append(paint(ax, cap, COLORS['key'], shift=(0, 0, -5)))
    finish(ax, bounds, 22, -53, 'Exploded assembly', 'Authored enclosure parts only')

    angle = np.deg2rad(90 + c['stand_tilt_degrees'])
    pose = np.eye(4)
    pose[:3, :3] = [[1, 0, 0], [0, np.cos(angle), -np.sin(angle)],
                     [0, np.sin(angle), np.cos(angle)]]
    theta = np.deg2rad(c['stand_tilt_degrees'])
    tz = 2.8 - .6 - np.cos(theta) * (-c['case_height'] / 2 - 2.4) \
        + np.sin(theta) * (c['case_depth'] + c['stand_clearance'] + 2.8)
    pose[:3, 3] = [0, 4, tz]
    ax = fig.add_subplot(224)
    bounds = [paint(ax, parts['stand'], COLORS['stand']),
              paint(ax, parts['front'], COLORS['front'], pose=pose),
              paint(ax, parts['back-lower-open'], COLORS['back'], pose=pose)]
    for cap in caps:
        bounds.append(paint(ax, cap, COLORS['key'], pose=pose))
    finish(ax, bounds, 20, 64, 'Matching stand',
           f"{c['stand_tilt_degrees']:g}° rearward lean; two rear connector exits")
    plt.imsave(Path(output).with_name('stand-preview.png'),
               render_geometry(ax._geometry, [65, 100, 65], [0, 0, 1]))
    fig.subplots_adjust(left=.02, right=.98, top=.82, bottom=.065, wspace=.04, hspace=.16)
    fig.text(.04, .025, 'Rendered from authored CAD geometry. Physical button feel, latch retention, and assembled fit remain unverified.',
             fontsize=10, color='#526269')
    fig.savefig(output, dpi=170, facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kit', type=Path, required=True, help='Generated kit with individual native STEPs')
    parser.add_argument('--output', type=Path, required=True, help='Destination PNG')
    args = parser.parse_args()
    import cadquery as cq
    from common import load_config
    from enclosure import cap_in_assembly
    from export_design import native_mesh
    c = load_config(args.kit / 'source' / 'parameters.json')
    native = {p.stem: cq.importers.importStep(str(p)).val()
              for p in (args.kit / 'STEP').glob('*.step') if p.stem != 'enclosure-only'}
    render_preview({n: native_mesh(s) for n, s in native.items()},
                   [native_mesh(cap_in_assembly(native['button-cap'], c, i)) for i in range(4)],
                   c, args.output)

