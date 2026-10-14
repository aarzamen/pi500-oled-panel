"""Integration tests for the portable case-only exporter.

Run with Python 3.12 after installing requirements.txt. Tests use real exported
solids and meshes in an isolated directory; they never write into this kit.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

import cadquery as cq
from lxml import etree as ET
import numpy as np
import trimesh


SOURCE = Path(__file__).resolve().parent
PART_SHA256 = {
    'front': 'a01b2e8d8b9a3221aeb547a27ac6d7e8a939f86e114a16b1c65d64f51247437d',
    'back-dual-knockouts': '3e436336ea0fcf9ad9f30a5e2cb98b1e17ede12d280cc1f8185169d7f2b7cf83',
    'back-lower-open': '9dbbbeff0643472fc532057a97a09ca50226c74eed8489ad0f9c694bd7e44593',
    'back-upper-open': '50ca7889118cfefe82932a881a5e8cfc15fcbda5769feabbc526d7eb34ddf34b',
    'button-cap': '8f7b895ff55436e64f83ec8ba8d73415498702e15f341648c05fd411ab48b90e',
    'stand': '9d3571efb509cd8529861dccc5783c66ee5ccc308ad8252d64cfc5829b7b9852',
}
M = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}


class ExportTests(unittest.TestCase):
    def test_selected_parameters_and_profile_survive_next_rebuild(self):
        with tempfile.TemporaryDirectory(prefix='oled-cad-selected-') as temp:
            root = Path(temp)
            parameters = json.loads((SOURCE / 'parameters.json').read_text())
            parameters['stand_clearance'] = 0.5
            parameter_path = root / 'custom-parameters.json'
            parameter_path.write_text(json.dumps(parameters))
            profile = json.loads((SOURCE / 'profiles' / 'x1c-abs-standard.json').read_text())
            profile['filament_colour'] = ['#FF0000']
            profile_path = root / 'custom-profile.json'
            profile_path.write_text(json.dumps(profile))
            first = root / 'first'
            result = subprocess.run(
                [sys.executable, str(SOURCE / 'export_design.py'), '--no-preview',
                 '--parameters', str(parameter_path), '--profile', str(profile_path), '--output', str(first)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            second = root / 'second'
            result = subprocess.run(
                [sys.executable, str(first / 'source' / 'export_design.py'), '--no-preview', '--output', str(second)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((first / 'STL' / 'stand.stl').read_bytes(),
                             (second / 'STL' / 'stand.stl').read_bytes())
            with ZipFile(second / 'OLED-case-CAD-v3.3mf') as archive:
                actual = json.loads(archive.read('Metadata/project_settings.config'))
                self.assertEqual(actual['filament_colour'], ['#FF0000'])

    def test_package_contains_public_payload_and_verified_manifest(self):
        with tempfile.TemporaryDirectory(prefix='oled-cad-package-') as temp:
            root = Path(temp)
            (root / 'STL').mkdir()
            (root / 'STL' / 'front.stl').write_bytes(b'public-case')
            (root / 'README.md').write_text('case kit')
            (root / 'private.step').write_bytes(b'exclude unrelated input')
            (root / 'STEP').mkdir()
            (root / 'STEP' / 'enclosure-with-hardware.step').write_bytes(b'exclude reference geometry')
            (root / 'source' / '.venv').mkdir(parents=True)
            (root / 'source' / '.venv' / 'private.txt').write_text('exclude environment')
            result = subprocess.run(
                [sys.executable, str(SOURCE / 'package.py'), '--kit', str(root)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            archive_path = root / 'OLED-case-CAD-v3-public.zip'
            with ZipFile(archive_path) as archive:
                names = set(archive.namelist())
                prefix = 'OLED-case-CAD-v3-public/'
                self.assertEqual(names, {prefix + 'README.md', prefix + 'STL/front.stl',
                                         prefix + 'SHA256SUMS.txt'})
                for line in archive.read(prefix + 'SHA256SUMS.txt').decode().splitlines():
                    expected, name = line.split('  ', 1)
                    self.assertEqual(hashlib.sha256(archive.read(prefix + name)).hexdigest(), expected)
            expected = (root / 'OLED-case-CAD-v3-public.zip.sha256').read_text().split()[0]
            self.assertEqual(hashlib.sha256(archive_path.read_bytes()).hexdigest(), expected)

    def test_relocated_source_generates_exact_case_without_hardware_input(self):
        with tempfile.TemporaryDirectory(prefix='oled-cad-test-') as temp:
            root = Path(temp)
            source = root / 'relocated-source'
            shutil.copytree(SOURCE, source, ignore=shutil.ignore_patterns('__pycache__', '.venv'))
            result = subprocess.run(
                [sys.executable, str(source / 'export_design.py'), '--no-preview'],
                cwd=root, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            output = root / 'cad-v3-output'
            self.assertFalse((output / 'reference').exists())
            for name, expected in PART_SHA256.items():
                with self.subTest(part=name):
                    stl = output / 'STL' / (name + '.stl')
                    self.assertEqual(hashlib.sha256(stl.read_bytes()).hexdigest(), expected)
                    mesh = trimesh.load_mesh(stl, process=True)
                    self.assertTrue(mesh.is_watertight)
                    self.assertTrue(mesh.is_winding_consistent)
                    self.assertEqual(len(mesh.split()), 1)
                    self.assertTrue(np.all(mesh.nondegenerate_faces()))
                    self.assertAlmostEqual(mesh.bounds[0, 2], 0, places=5)
                    native = cq.importers.importStep(str(output / 'STEP' / (name + '.step'))).val()
                    self.assertTrue(native.isValid())
                    self.assertEqual(len(native.Solids()), 1)
            assembly = cq.importers.importStep(str(output / 'STEP' / 'enclosure-only.step')).val()
            self.assertTrue(assembly.isValid())
            self.assertEqual(len(assembly.Solids()), 6)
            report = json.loads((output / 'evidence' / 'geometry-checks.json').read_text())
            self.assertEqual(report['hardware_reference']['status'], 'not-requested')
            self.assertAlmostEqual(report['dimensions']['case_width'], 51.3)
            self.assertAlmostEqual(report['dimensions']['case_height'], 33.4)
            self.assertAlmostEqual(report['dimensions']['case_depth'], 12.2)
            self.assertEqual(report['print_rotation']['rotation_axis'], [1, 0, 0])
            self.assertEqual(report['print_rotation']['rotation_degrees'], 180)
            self.assertEqual(report['print_rotation']['determinant'], 1)
            with ZipFile(output / 'OLED-case-CAD-v3.3mf') as archive:
                config = json.loads(archive.read('Metadata/project_settings.config'))
                end = config['machine_end_gcode']
                self.assertIn('M140 S0', end)
                self.assertIn('M104 S0', end)
                self.assertIn('M620 S255', end)
                self.assertNotIn('M140 S90', end)
                main = ET.fromstring(archive.read('3D/3dmodel.model'))
                self.assertEqual(main.get('unit'), 'millimeter')
                self.assertEqual(len(main.findall('m:build/m:item', M)), 7)
                settings = ET.fromstring(archive.read('Metadata/model_settings.config'))
                self.assertEqual(len(settings.findall('plate')), 2)
                parts = ['front', 'back-dual-knockouts'] + ['button-cap'] * 4 + ['stand']
                for index, part in enumerate(parts, 1):
                    model = ET.fromstring(archive.read(f'3D/Objects/object_{index}.model'))
                    vertices = np.array([[float(v.get(axis)) for axis in ('x', 'y', 'z')]
                                         for v in model.findall('.//m:vertex', M)])
                    triangles = np.array([[int(t.get(axis)) for axis in ('v1', 'v2', 'v3')]
                                          for t in model.findall('.//m:triangle', M)])
                    stl = trimesh.load_mesh(output / 'STL' / (part + '.stl'), process=True)
                    self.assertTrue(np.allclose(vertices, stl.vertices, atol=1e-9, rtol=0))
                    self.assertTrue(np.array_equal(triangles, stl.faces))

    def test_existing_directory_is_preserved(self):
        with tempfile.TemporaryDirectory(prefix='oled-cad-existing-') as temp:
            output = Path(temp) / 'existing'
            output.mkdir()
            sentinel = output / 'user-file.txt'
            sentinel.write_text('keep this file')
            result = subprocess.run(
                [sys.executable, str(SOURCE / 'export_design.py'), '--output', str(output), '--no-preview'],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(), 'keep this file')
            self.assertEqual(list(output.iterdir()), [sentinel])

    def test_wrong_hardware_hash_fails_before_output(self):
        with tempfile.TemporaryDirectory(prefix='oled-cad-hash-') as temp:
            root = Path(temp)
            wrong = root / 'wrong.step'
            wrong.write_text('This is not the attributed original STEP.')
            output = root / 'output'
            result = subprocess.run(
                [sys.executable, str(SOURCE / 'export_design.py'), '--output', str(output),
                 '--hardware-step', str(wrong), '--no-preview'],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('SHA-256', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
