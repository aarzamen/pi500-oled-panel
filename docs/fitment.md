# PCB and enclosure fitment

**CAD v3 is a prototype for the next assembled fit print.** The builder's older
empty case snaps smoothly and fits its original stand. With the board installed,
the button stack prevented correct closure. Those observations prompted the
deeper v3 case; they do not prove its assembled fit.

The source PCB is a rough community model rather than a factory drawing. Combine
it with the actual board measurements below and remeasure uncertain values before
altering a dimension. See [sourcing and variants](hardware-sourcing.md).

## Dimension basis

All dimensions are millimeters.

| Feature | Current basis | Remaining uncertainty |
| --- | --- | --- |
| PCB outline | Community STEP: 44 × 27; seller module: 44.53 × 27.66 | Physical outline not measured; larger seller envelope used for snap-arm keepout |
| PCB thickness | STEP: 1.6 | Physical measurement pending |
| Mount-hole pitch | User: approximately 40 × 24 | Low caliper battery limited precision; community model has about 41 × 24 |
| Released moving button peak above front PCB surface | User: 2.65 | Used to set the PCB depth |
| Fixed metal housing above front PCB surface | User: 1.8 | Not the released moving contact height |
| PCB right edge to nearest fixed housing edge | User: 4.75 | This is **not** the moving button's center |
| Button X center | 22 − 4.75 − 3 = 14.25 | Uses the STEP's 44 mm board width and estimated 6 mm housing width; do not silently substitute the seller outline |
| Button Y centers | STEP estimates, rigidly rotated for assembly | Physical pitch and column position need confirmation |
| Display glass | STEP: 24.5 × 16.5, with estimated height and offset | Confirm glass and illuminated area on the physical module |
| Rear pins | STEP estimates; connector envelope uses 2.54 mm pitch | Confirm pin length, solder and all eight straight connector housings |

The seller and STEP dimensions are separate evidence. The v3 keepout provides a
conservative envelope, while the switch-center derivation still uses the reference
outline. Treat an unexpected fit as a measurement to resolve, not a reason to
scale the whole model.

## Button depth drives the PCB position

The front exterior is assembly Z=0 and positive Z goes into the case. Current
parameters give this released stack:

```text
front face            1.20
cap release gap       0.30
retaining flange      0.40
released actuator     2.65
                     ----
PCB front at Z        4.55
PCB thickness         1.60
PCB back at Z         6.15
```

The cap contact rests at Z=1.90, touching the modeled released actuator peak.
The flange has 0.30 mm clearance behind the face, and the collision check exercises
0.35 mm of inward travel. This checks geometric space; actual switch actuation,
feel and return need the assembled print.

The post has a 2.668484 mm exposed section on a 0.681516 mm raised base above
the 1.2 mm front face. Moving the PCB by changing only the exposed post can preload
the keys or separate their contacts. Recalculate the complete stack when changing
cap, face, button or PCB height.

The body is 51.3 × 33.4 × 12.2 mm, with 1.6 mm walls and 1.2 mm front/rear faces.
The closed rear face begins at Z=11.00. Modeled pins reach Z=10.55, leaving
0.45 mm when no connectors are attached. Straight DuPont housings require an open
rear panel; this pin-only clearance does not enclose attached plugs.

## Openings, screws, cover and stand

- **Screen:** 23.9 × 16.1 mm throat, adding 0.3 mm overlap at each horizontal
  glass edge and 0.2 mm at each vertical edge. Confirm that it clears the active
  image and avoids loading the glass.
- **Keys:** 4.6 × 2.6 mm shafts with 0.25 mm side clearance; four independent
  caps with 7.6 × 5.1 × 0.4 mm retaining flanges. Print all four, and check each
  moves and releases without leaning against its aperture.
- **Mounts:** 4 mm post outside diameter, 5 mm base diameter, and 1.55 mm blind
  pilots 2.4 mm deep. Pilot diameter is a modeled hole, not a promised screw thread
  size. Select a short screw for the actual printed material and PCB stack; it must
  clamp the board without bottoming, cracking the post or reaching the front.
- **Header:** two opposite rear panel positions, each 23 × 6.4 mm. Intact panels
  have an inside score and continuous 0.4 mm outer membrane. Remove the required
  panel with the cover detached, or print that side already open. The top wall
  remains continuous. An unused panel may stay closed.
- **Snap fit:** 0.7 mm flexible arms, 0.3 mm nominal engagement and 0.2 mm locating
  clearance. Calculated fully compressed-arm clearance to the PCB envelope is
  0.385 mm. This static collision check does not establish spring strength or
  latch holding force in a particular material.
- **Stand:** v3's matched cradle is 12.7 mm deep, providing 0.25 mm per side for
  the 12.2 mm body, with a 20° rearward lean. A central rear notch allows the
  connector path. Do not assume the old shallow stand accepts this deeper case.

The lower/upper opening filenames refer to **assembled** Y coordinates. Cover
STLs are rotated 180° about X for printing, so Y reverses in the bed view. The
hardware, keys and display were also aligned with a proper rigid rotation.
Keep this handedness intact when editing the design; see the
[kit orientation notes](../mechanical/cad-rebuild/README.md#download-and-print).

## First assembled fit checklist

Record the CAD revision, material, printer, layer height, screw dimensions and
any adjustments. Use the matching v3 front, one back, four caps and stand.

- [ ] Measure board outline, mounting pitch, switch positions and header side.
- [ ] Dry-fit the PCB on all four mounts; no bending or forced screw alignment.
- [ ] Check screw clamping and depth before closing the cover.
- [ ] Check each unpressed cap and its inward travel with the board secured.
- [ ] Check the image is fully visible and the face is not pressing the glass.
- [ ] Close the empty case, then the assembled case; both latches must retain it.
- [ ] Verify each cap releases immediately with the cover latched.
- [ ] Fit all eight DuPont housings through the correct rear opening.
- [ ] Check stand seating, cable clearance and stability with the connected harness.
- [ ] Photograph the assembled v3 print and record the pass/fail result before
      claiming fit or posting a tested print profile.

Change one identified fit variable at a time. An empty-case latch test cannot
substitute for closure with the PCB, screws and buttons installed.

## Tools and evidence

Use [native parameters](../mechanical/cad-rebuild/source/parameters.json) and the
[CAD generator](../mechanical/cad-rebuild/source/README.md) for this design. Its
[geometry receipts](../mechanical/cad-rebuild/evidence/geometry-checks.json)
and [slicer receipts](../mechanical/cad-rebuild/evidence/slicing-check.json)
record software checks. The separate [browser workshop](case-workshop.md)
retains its earlier 40 × 23 mm post pitch, 3 mm post height and provisional board;
it is useful for experiments but does not regenerate v3.
