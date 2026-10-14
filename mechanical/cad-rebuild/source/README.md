# Editable CAD source

Run `export_design.py` with Python 3.12 after installing `requirements.txt` in a
virtual environment. The full kit README has setup and assembly instructions.

The default writes a new `cad-v3-output` directory in the current directory.
`--output`, `--parameters`, `--profile`, `--no-preview` and `--replace` are
available; use `--help` for details. `--replace` refuses nonempty directories
without this generator's marker. All work is staged before an existing marked
output is replaced.

`common.py`, `enclosure.py` and `stand.py` retain the original CAD v3 construction.
`parameters.json` contains its dimensions and measurement provenance.
`hardware.py` is an optional validator for a separately supplied, hash-checked
Hellfire community STEP. It never supplies or redistributes that file.
`preview.py` renders only authored enclosure/stand parts. `package.py` creates
the reviewed public ZIP and digests. `test_export.py` exercises relocated source,
exact mesh preservation, native geometry, project identity, safe output handling
and bad hardware-hash rejection.

The generator checks cap and shell clearance, conservative compressed latch-arm
clearance, score membranes, connector envelopes and stand fit. Optional hardware
checks add the separate reference's fixed components and glass. These checks
cannot establish physical fit, button feel or material behavior.

Original project code/design is MIT licensed. The bundled Bambu-derived profile
is covered separately by its upstream notice in `profiles/README.md`.
