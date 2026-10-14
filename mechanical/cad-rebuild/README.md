# OLED case and stand — CAD v3

Original case geometry for the measured four-button OLED module, with four
independent key caps, two rear header knockouts, and a matching stand. The body is
**51.3 × 33.4 × 12.2 mm**. This is a prototype for an assembled fit print.

Native geometry and slicer acceptance are checked. Physical button feel, latch
retention, screw fit, knockout removal, connector fit, and stand stability remain
unverified. Other board variants need their own measurements.

See the repository's [fitment notes](https://github.com/aarzamen/pi500-oled-panel/blob/main/docs/fitment.md),
[board sourcing notes](https://github.com/aarzamen/pi500-oled-panel/blob/main/docs/hardware-sourcing.md)
and [hardware/software guide](https://github.com/aarzamen/pi500-oled-panel/blob/main/docs/hardware-and-software.md).

![Case and stand rendered from authored CAD](assembly-preview.png)

## Download and print

[Download the complete public kit](https://raw.githubusercontent.com/aarzamen/pi500-oled-panel/main/mechanical/cad-rebuild/OLED-case-CAD-v3-public.zip), or open
[OLED-case-CAD-v3.3mf](OLED-case-CAD-v3.3mf) in Bambu Studio.

- **Plate 1:** front, one back with both rear panels intact, and four separate caps.
- **Plate 2:** the matching stand.

The project uses **X1 Carbon / 0.4 mm nozzle / Generic ABS / 0.20 mm layers / three
walls / 20% infill**, with supports enabled. The public project uses the normal
X1 Carbon end sequence: turn the bed and nozzle off and unload the filament.
The maintainer's separate local package retains the requested 90°C bed hold and
loaded filament. That local custom end sequence is not included in this public
project. Review the printer, material, plate and supports in Bambu Studio, then
slice for your machine before printing. The validation slice is a software check;
no print was sent for this publication.

| File | Use |
|---|---|
| [STL/front.stl](STL/front.stl) | Front shell with mounts and key openings |
| [STL/button-cap.stl](STL/button-cap.stl) | Print four copies; the flange retains each cap |
| [STL/back-dual-knockouts.stl](STL/back-dual-knockouts.stl) | Both rear panels intact |
| [STL/back-lower-open.stl](STL/back-lower-open.stl) | Opening at negative assembly Y |
| [STL/back-upper-open.stl](STL/back-upper-open.stl) | Opening at positive assembly Y |
| [STL/stand.stl](STL/stand.stl) | Stand matched to this deeper case |
| [STEP/enclosure-only.step](STEP/enclosure-only.step) | Front, lower-open back and four caps in assembly coordinates |
| `STEP/*.step` | Six individual native part solids |
| [source/parameters.json](source/parameters.json) | Editable dimensions and measurement provenance |
| [case-preview.png](case-preview.png), [stand-preview.png](stand-preview.png) | Authored case and stand previews; no hardware reference |

The cover STLs are rigidly rotated 180° about X onto their outer faces for
printing: `(x, y, z) → (x, −y, 12.2 − z)`. This is a proper rotation, with
determinant +1. The individual part STEPs retain their assembly coordinates.
The stand STEP and STL both use its flat print orientation. The lower/upper names
refer to assembly Y; rotation for printing reverses the displayed Y side. The
reference module's modeled header maps to negative Y, so the lower-open back is
used in the assembly. Both ports are provided for the alternate cover orientation.

## Assemble and check

1. Put the four caps through the front from inside; keep their large flanges inside.
2. Seat the PCB on the four posts. Confirm that each cap meets its released actuator
   without holding it down, and that all four keys move and return independently.
3. Secure the PCB with suitable short screws. The blind pilots are 1.55 mm diameter
   and 2.4 mm deep; check seating and bottoming with the actual screws.
4. Open the required rear panel while the cover is detached. The inside score leaves
   a continuous 0.4 mm outer skin. Score or snip that skin before removing the panel,
   or print the matching already-open back. Keep the unused panel intact.
5. Close the cover and check both latches, all four keys, and the cable path. The
   side windows provide access to release the latches with a thin tool.
6. Seat the body in the matching stand and check retention, stability, and connectors.

The intact panels clear modeled unconnected pins. Straight DuPont plugs require
the matching panel to be open. Ports are 23 × 6.4 mm; the modeled connector array
is 20.32 × 4.2 mm. Existing shallower-case stands are not the fit reference for v3.

## Dimensions and evidence

| Dimension | Value and basis |
|---|---|
| Body | 51.3 × 33.4 × 12.2 mm, authored design |
| Walls / front / rear face | 1.6 / 1.2 / 1.2 mm |
| Outer corner radius | 3.5 mm |
| Mount-hole pitch | Approximately 40 × 24 mm, user measurement |
| Released actuator / fixed housing above PCB | 2.65 / 1.8 mm, user measurement |
| PCB edge to nearest fixed switch housing edge | 4.75 mm, user measurement |
| Switch X center | 22 − 4.75 − 3 = 14.25 mm; PCB half-width and switch half-width remain reference estimates |
| PCB front behind exterior front | 4.55 mm |
| Exposed standoff / raised base height | 2.668484 / 0.681516 mm |
| Standoff / base diameter | 4 / 5 mm |
| Display throat | 23.9 × 16.1 mm |
| Glass overlap | 0.3 mm per X side; 0.2 mm per Y side |
| Compressed latch arm to PCB envelope | 0.385 mm calculated minimum |
| Stand footprint / rearward lean | 56.8 × 36 mm / 20° |
| Stand cradle / per-side depth clearance | 12.7 / 0.25 mm |

The 4.75 mm measurement is to the **nearest housing edge**, not the switch center.
The 40 × 24 mm hole spacing is approximate; caliper precision was limited by a low
battery. Glass dimensions and height, button Y spacing, PCB thickness and header
geometry remain reference estimates. The source PCB is 44 × 27 mm; a seller-family
44.53 × 27.66 mm envelope is used conservatively for latch clearance. Neither is
a factory drawing for all boards. The source's approximate pin spacing remains
in optional reference checks; the connector openings also allow the 2.54 mm pitch
used in the connector envelope.

The maintainer identified the purchased module as the
[ACEIRMC five-pack, 0.96-inch SSD1315 yellow/blue OLED, Amazon B0GWQPY2C7](https://www.amazon.com/dp/B0GWQPY2C7).
That listing specifies 44.53 × 27.66 mm, eight pins at 2.54 mm pitch, and
independent K1–K4 buttons. The physical PCB outline has not been measured; the
listed envelope is already the conservative keepout used here. Switch X remains
14.25 mm from the 44 mm reference PCB basis, the measured 4.75 mm housing-edge
gap, and the estimated 6 mm switch housing width.

[Geometry receipts](evidence/geometry-checks.json) record native-solid validity,
STEP round trips, STL topology, print rotations, cap travel, latches, knockouts
and stand clearance. [Slicer receipts](evidence/slicing-check.json) record the
public two-plate project's actual software slice. [Publication receipts](evidence/publication-check.json)
record byte preservation, source portability, archive identity and limits.
The six published STLs and individual part STEPs preserve the local CAD v3 bytes.
[Preview caption receipts](evidence/preview-caption-check.json) record checks with
the default dimensions and a temporary edited configuration.

## Reference provenance and licenses

The separate hardware input was supplied by the maintainer as Hellfire's
**“OLED | 0.96 | 4 button”**, dated April 8, 2025, from the
[GrabCAD community library](https://grabcad.com/library). Attribution is based on
the supplied model and author screenshot. It is an approximate community
reconstruction; redistribution permission for that STEP has not been established.
The original `0.96Oled_W_4_Buttons.step`, corrected hardware geometry, and combined
hardware assembly are therefore kept out of this public kit. Obtain the original
from its author or supply your own lawfully held copy for optional validation.

Expected original STEP SHA-256:

```text
ed957ded2c544964b1bec1acb4370eca514f40954b93bac7f33eac63be0a1356
```

The case and stand geometry, editable generator code and documentation are
original project work under the [MIT license](LICENSE), maintained by Aaron
Arzamendi. Codex assisted with the CAD rebuild, checks and publication. Claude
assisted with earlier project collaboration, as credited by the maintainer.
These credits do not transfer rights to the separate community hardware model.
The bundled Bambu-derived settings retain a separate
[upstream license notice](source/profiles/README.md). See the repository's
[CREDITS.md](https://github.com/aarzamen/pi500-oled-panel/blob/main/CREDITS.md)
for project-wide references.

## Regenerate locally

Use Python 3.12 and `uv`. From an extracted kit directory, these commands create
the environment and write a **new** `cad-v3-output` directory. No community STEP,
Desktop project or running printer is needed:

```bash
uv venv --python 3.12 source/.venv
uv pip install --python source/.venv/bin/python -r source/requirements.txt
source/.venv/bin/python source/export_design.py
```

Edit `source/parameters.json` for an intentional new variant, then choose a new
output with `--output ./my-case`. `--replace` accepts only a directory bearing
this generator's output marker; a failed build leaves the earlier output intact.
The `calibration_complete` field records that the listed measurement inputs were
entered; physical assembled fit remains unverified.

For optional collision checks against the separately supplied original reference:

```bash
source/.venv/bin/python source/export_design.py \
  --output ./case-with-reference-checks \
  --hardware-step "$HOME/Downloads/0.96Oled_W_4_Buttons.step"
```

The hash must match before CAD import. The reference receives a rigid 180° X
rotation with negated Y. Checks are written as scalar/metadata evidence only;
the STEP and reference meshes are never copied or exported.

To run the focused source tests and package a reviewed output:

```bash
source/.venv/bin/python -m unittest discover -s source -p 'test_*.py'
source/.venv/bin/python source/package.py --kit ./cad-v3-output
```

`SHA256SUMS.txt` covers the reviewed payload. The ZIP contains that payload
manifest; `OLED-case-CAD-v3-public.zip.sha256` checks the ZIP itself. With the
current pinned environment the six STL exports reproduce the existing bytes.
STEP exports can differ in timestamp headers after regeneration.
