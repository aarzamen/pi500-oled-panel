#!/usr/bin/env python3
"""Rebuild the fixed ZIP reference meshes without changing the source archive.

From this folder, use a temporary Python 3.12 environment:
  uv run --python 3.12 --with numpy --with trimesh extract-zip-reference.py

Only rigid rotations and translations are applied. Parts remain independent;
their positions do not claim to reconstruct the source enclosure's assembly.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import trimesh


ROOT = Path(__file__).resolve().parent
PARTS = (
    ("back", "ZIP rear shell", "obj_1_096+4btn - bat.stl_4.stl", True),
    ("front", "ZIP front shell", "obj_2_096+4btn - bat.stl_1.stl", True),
    ("tray", "ZIP internal tray", "obj_3_096+4btn - bat.stl_3.stl", False),
    ("buttons", "ZIP four-button strip", "obj_4_096+4btn - bat.stl_2.stl", False),
    ("bracket", "ZIP small bracket", "obj_5_096+4btn - bat.stl_5.stl", False),
)


def extract(source: Path) -> dict:
    result = {}
    archive_sha256 = hashlib.sha256(source.read_bytes()).hexdigest()
    with zipfile.ZipFile(source) as archive:
        for key, label, filename, rotate in PARTS:
            original_bytes = archive.read(filename)
            original = trimesh.load(io.BytesIO(original_bytes), file_type="stl")
            matrix = np.array(
                [[0, 1, 0], [-1, 0, 0], [0, 0, 1]] if rotate else np.eye(3),
                dtype=np.float64,
            )
            positions = original.triangles @ matrix.T
            low = positions.min(axis=(0, 1))
            high = positions.max(axis=(0, 1))
            translation = np.array([-(low[0] + high[0]) / 2,
                                    -(low[1] + high[1]) / 2, -low[2]])
            positions = np.asarray(positions + translation, dtype="<f4")
            dimensions = positions.max(axis=(0, 1)) - positions.min(axis=(0, 1))
            result[key] = {
                "label": label,
                "sourceArchive": source.name,
                "sourceFilename": filename,
                "sourceArchiveSha256": archive_sha256,
                "sourceMeshSha256": hashlib.sha256(original_bytes).hexdigest(),
                "data": base64.b64encode(positions.tobytes()).decode("ascii"),
                "dimensions": dimensions.astype(float).tolist(),
                "triangles": int(len(positions)),
                "watertight": bool(original.is_watertight),
                "windingConsistent": bool(original.is_winding_consistent),
                "components": len(original.split(only_watertight=False)),
                "units": "source STL units; interpreted as millimeters",
                "originalBounds": original.bounds.tolist(),
                "originalDimensions": original.extents.tolist(),
                "orientation": {
                    "description": "90 degrees clockwise in XY" if rotate else "source XY orientation",
                    "rotationMatrix": matrix.tolist(),
                    "translation": translation.tolist(),
                    "formula": "displayPosition = rotationMatrix * sourcePosition + translation",
                    "centering": "independent XY bounding-box center; minimum Z at zero",
                    "assembly": "individual source part; assembly placement is unspecified",
                },
            }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / "reference/096+4btn+-+bat_stls.zip")
    parser.add_argument("--output", type=Path, default=ROOT / "reference/zip-meshes.json")
    args = parser.parse_args()
    result = extract(args.source)
    args.output.write_text(json.dumps(result, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {len(result)} fixed source parts to {args.output}")
    for key, part in result.items():
        dimensions = " x ".join(f"{value:.4f}" for value in part["dimensions"])
        print(f"{key}: {part['triangles']} triangles; {dimensions}")


if __name__ == "__main__":
    main()
