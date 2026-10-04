# OLED Case Workshop

**[Open the public OLED Case Workshop](https://oled-case-workshop.annonable.chatgpt.site)** — a 3D print screen case maker for the HW-937AB OLED module.

For offline use, download the [complete workshop package](oled-case-workshop.zip), extract it, and open `oled-case-playground.html` in Chrome, Edge, or Safari. It contains the complete app and works offline; no install or server is needed. The tested browser is Chromium.

## Control levels and resets

- **Easy:** two linked sliders for wall thickness and edge rounding, plus the
  screen style, button style, outer bezel, and closing mechanism.
- **Intermediate:** individual part sizes, PCB screw/post diameters, bezels,
  opening sizes, and inspection views.
- **Expert:** all controls, including feature positions, clearances, catch geometry,
  mounting-post enablement, and wireframe view.

Changing levels preserves the design. Every dimensional slider has a visible
**↺** reset. It restores that field to the selected starting preset, shown above
Whole-case adjustments. **Reset all** restores the complete selected preset;
choose **Original footprint** to return to the original starting design.
Settings files now retain the starting preset. Older files use Original footprint
as their reset baseline. There is also a reset for exploded-view separation.

The Easy sliders use percentages: **100%** means the selected starting preset.
Wall scale links the shell wall, front face, rear plate/wall, outer sleeve wall,
and screen rim in their starting proportions. Sleeve clearance is kept separate.
Rounding scale links body, cover, bezel, window, button and rear-opening radii.
Clip spring thickness, PCB posts, screw holes, positions and fit clearances remain
independent. The case can grow to preserve the PCB/feature clearance; the panel
lists those adjustments. Some values are limited or rounded to preserve material
and mesh stability. A linked reset retains the grown outer envelope; Reset all
restores its size too. Intermediate and Expert allow individual overrides.

If a linked combination cannot produce a valid solid, the editor restores the
last valid design and its starting preset, with an explanation. Advanced invalid
combinations leave the last valid shape visible and disable export until corrected.
The current triangulator rejects a few proportional rounding combinations; see
Verification below. These are not exported as broken STL files.

## Use

1. Choose a starting preset, then adjust dimensions in millimeters. Drag to orbit, scroll to zoom, or use Front / Back / Fit.
2. Switch between assembled, exploded, and print layouts. **Original STL** shows the unchanged original shell and bezel. **ZIP reference** lets you inspect all five original parts from the supplied archive individually. Generated exports are disabled in both fixed reference views.
3. Select **Snap-fit**, **Slip-fit**, or **Screw-fastened** under **Back cover & fit**. Adjust shell depth, cover depth, engagement, and clearance independently.
4. Under **PCB mounting screws**, set **Standoff outside diameter** and **Screw-hole diameter**. **Inspect mounting posts** turns the shell over and hides the cover. Hole diameter means the modeled pilot bore; choose it for the actual screw and printed material.
5. Under **Rear connector opening**, set width, height, horizontal/vertical offsets, and corner radius. **Inspect rear opening** isolates the cover. The gap passes straight through the backplate; all top case walls stay continuous.
6. Choose window and button styles separately, or use **ZIP face style** to apply the supplied ZIP's beveled window and rounded key strip together. Selecting a screen or button style loads its starting feature dimensions. The screen shifts left when needed to clear the selected buttons. **Button protrusion** adjusts how far separate keys stand above the face.
7. Use **Download print set** for separate front / outer bezel / back STL files, plus the optional button strip, settings, a design brief, and fit notes. Individual STL buttons are also available. Save and load JSON settings to keep variations. Older settings load with the new rear-opening defaults; the retired top-notch dimensions are discarded.

The standoff and screw-hole diameters are independent; combinations leaving too little post material or touching buttons are rejected. Wider posts may require narrower buttons or moving features. PCB post centers and 3 mm post height remain fixed.

The outer bezel, screen bezel, body corners, window corners, button corners, and body/cover edge rounding have separate controls. Invalid combinations display an explanation and disable exports while leaving the last valid shape visible.

## What the model represents

The user's `screeen1.stl` contains a 56 × 38 × 9.343 mm sleeve and a 51.104 × 33.163 × 6.041 mm front shell. It is preserved in `reference/`. The editable model reconstructs its footprint, screen opening, four integral button tabs, and four PCB mounting locations. It is not a direct deformation of the source mesh.

The default rear gap is **24 × 7 mm**, centered at X 0, Y +10.5 mm in front-view coordinates. It is intended for the full row of straight DuPont housings exiting along the PCB normal. It also clears intervening cover lips and flanges. Resize and position it to match the real connector row. The optional eight-way connector guide has a fixed approximate 2.54 mm pitch and position; moving the opening does not move the guide. Rear vents omit slots near this gap to preserve material.

The new default shell is **8 mm deep**, giving the approximate 45 × 28 × 1.6 mm board and cover lip room to coexist. The guide places the PCB on the 3 mm bosses, at Z 4.5–6.1 mm for the default face; the lip starts at Z 6.2 mm. These board dimensions and stack clearances still need measurement on the physical module. Resizing the shell does not scale the PCB or its mounting-hole spacing.

### Supplied ZIP face options

`096+4btn+-+bat_stls.zip` provides a different enclosure with a beveled window and separate rounded keys. Its front (`obj_2…_1.stl`) and button strip (`obj_4…_2.stl`) were measured from the triangles. The editable options reproduce the shape concept and dimensions below, adapted to this shell and PCB mount layout:

- Window throat: 25.16 × 14.20 mm, 1 mm corner radius, 1.5 mm 45° entry bevel. The original file also has an internal collar; this reconstruction uses this shell's face structure.
- Button apertures: 5.2 × 3.2 mm, 1.1 mm corner radius, 0.6 mm entry bevel.
- Separate keys: 4.6 × 2.6 mm with 7.4 × 5.4 × 0.4 mm retaining flanges, joined by thin 1 × 0.25 mm bridges. The preset uses 0.3 mm side clearance and 1.2 mm exposed protrusion.
- The source's slightly irregular pitch is regularized to 5.95 mm; button column position stays at X 13.75 mm to clear this model's mounting posts. Switch contact and travel still require a physical fit check.

The original flexing-tab style remains selectable. A separate key strip must be fitted from inside before mounting the PCB. Its retaining flanges point toward the PCB; the keys project through the face. It appears as a fourth exported STL when enabled.

### Cover closures

The back cover and closure details are new designs:

- **Snap-fit:** two flexible side arms and lead-in hooks engage matching shell windows. Remove the outer sleeve to access and press both releases. Static clearance checks do not simulate arm flexing during insertion or release with the PCB installed. The supplied Raspberry Pi camera enclosure inspired the side-catch arrangement.
- **Slip-fit:** a clearance lip locates the cover. It has no latch or guaranteed holding force.
- **Screw-fastened:** matching external ears provide 2.3 mm cover clearance holes and 1.6 mm blind shell pilots, intended as an M2 starting point. Check pilot sizing and screw length with the printed stack. Sleeve reliefs are generated if the sleeve is enabled.

**Print the matching front and back together.** The snap windows, registration geometry, and screw ears are absent from the original STL; this is not a verified drop-in cover for the existing print. Check the PCB, switch travel, connector, and solder-joint clearances before printing a full set. Snap flexibility and holding force depend on material and layer direction and have not been physically tested.

Exports use millimeters and start at Z=0. Cover and sleeve are flipped face-down; the optional button strip is flipped with its retaining flanges on the bed and keys pointing upward. The raised screen rim can require support under the front face; inspect slicer orientation, bridges, and supports before printing. View transforms and colors do not affect export geometry.

Exports are binary **STL**, in millimeters. **STEP export is not supported** by this polygonal editor.

Live-site ZIP downloads were verified in Chrome. Codex's in-app browser canceled
the downloads during this review; open the public site in Chrome if saving is
blocked. A download-request notification means the browser received the request,
not that a file was saved.

## Included files

- `oled-case-playground.html`: self-contained interactive app.
- `starter-snap-print-set.zip`: default generated STL set and its settings.
- `starter-zip-face-print-set.zip`: beveled-window set with the separate rounded button strip.
- `reference/screeen1.stl`: unchanged initial user-supplied reference.
- `reference/zip-meshes.json`: all five exact source meshes, with provenance and rigid-transform metadata; `extract-zip-reference.py` reproduces this asset.
- `reference/096+4btn+-+bat_stls.zip`: unchanged reference for the optional window and button-strip shapes.
- `THIRD-PARTY-NOTICES.txt`: licenses for embedded JSCAD, Three.js, and fflate libraries. No redistribution license is asserted for the supplied reference models.

## Verification and development

From this directory, run `npm ci`, `npm run build`, and `npm test`. `npm run package` refreshes the complete offline ZIP. `node verify-browser.mjs` runs offline Chromium UI/export checks when Playwright's Chromium is installed.

Geometry tests cover presets, all three closures, parameter changes, measured post/hole sections, blind hole floors, unobstructed rear connector passages, continuous top walls, oriented watertight connected meshes, non-overlapping assembled parts, approximate PCB clearance, positive hook retention, and STL dimensions. Browser checks cover controls, invalid states, source view, exports, settings round trips, persistence, clipboard feedback, and mobile overflow. Exported preset STLs also passed independent Trimesh checks for watertightness, winding, single-component solids, positive volume, and bed placement.

No physical print, snap-force test, or hardware fit has been performed for the new geometry. The hosted and offline editors share the same source. They generate case meshes in the browser and make no changes to the installed OLED software. Settings are saved locally in the browser or downloaded as JSON; this editor does not upload them.

## Source and licenses

This folder is maintained with [Pi 500 OLED panel](https://github.com/aarzamen/pi500-oled-panel).
Project JavaScript, HTML, and documentation follow the repository MIT license.
JSCAD, Three.js, and fflate keep their own notices, included in the standalone HTML
and `THIRD-PARTY-NOTICES.txt`. The two supplied reference models are included for
comparison and provenance; no author or redistribution license was established
for those assets, and the repository MIT license does not relicense them.

In supporting browsers, the editor exposes `get_case_design` and
`configure_case_design` through WebMCP. These read or configure the visible model;
they do not control a printer or publish files. Invalid geometry restores the
previous design. Standard browser controls work without WebMCP.

### Usability update verification (2026-10-03)

The core suite passed 17 model scenarios and 143,832 assertions. Linked-control
checks exercised 94 states and validated 315 meshes. Four known numerical rejects
are recorded explicitly: Original rounding 90% and 110%, ZIP rounding 95%, and
Slim slip fit with wall and rounding both at 150%. Failed linked updates restore
the previous valid design; this path was checked in the browser at ZIP 95%.

Browser checks covered live slider editing, tier visibility without design loss,
per-field and whole-preset resets, ordinary decimal/negative typing, all five
presets and three closures, both independent screen/button styles, both source
views, all five ZIP reference parts, assembled/exploded/print layouts, invalid
export blocking and recovery, settings save/load, individual STL and ZIP downloads,
and desktop/mobile layouts. Downloaded ZIP-style parts were independently checked
with Trimesh: all four are closed, consistently wound, single solids with positive
volume and print-bed Z=0. The original shell/bezel and all 7,744 ZIP source triangles
were checked against their source files after rigid positioning transforms.
