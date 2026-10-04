# OLED Case Workshop

**[Open the public OLED Case Workshop](https://oled-case-workshop.annonable.chatgpt.site)** — a 3D print screen case maker for the HW-937AB OLED module.

For offline use, download the [complete workshop package](oled-case-workshop.zip), extract it, and open `oled-case-playground.html` in Chrome, Edge, or Safari. It contains the complete app and works offline; no install or server is needed. The tested browser is Chromium.

## Use

1. Choose a starting preset, then adjust dimensions in millimeters. Drag to orbit, scroll to zoom, or use Front / Back / Fit.
2. Switch between assembled, exploded, and print layouts. **Original STL** shows the unchanged source geometry for comparison; exports are disabled in that view.
3. Select **Snap-fit**, **Slip-fit**, or **Screw-fastened** under **Back cover & fit**. Adjust shell depth, cover depth, engagement, and clearance independently.
4. Under **PCB mounting screws**, set **Standoff outside diameter** and **Screw-hole diameter**. **Inspect mounting posts** turns the shell over and hides the cover. Hole diameter means the modeled pilot bore; choose it for the actual screw and printed material.
5. Under **Rear connector opening**, set width, height, horizontal/vertical offsets, and corner radius. **Inspect rear opening** isolates the cover. The gap passes straight through the backplate; all top case walls stay continuous.
6. Choose window and button styles separately, or use **ZIP face style** to apply the supplied ZIP's beveled window and rounded key strip together. Selecting a button style loads its starting dimensions. **Button protrusion** adjusts how far separate keys stand above the face.
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

## Included files

- `oled-case-playground.html`: self-contained interactive app.
- `starter-snap-print-set.zip`: default generated STL set and its settings.
- `starter-zip-face-print-set.zip`: beveled-window set with the separate rounded button strip.
- `reference/screeen1.stl`: unchanged initial user-supplied reference.
- `reference/096+4btn+-+bat_stls.zip`: unchanged reference for the optional window and button-strip shapes.
- `THIRD-PARTY-NOTICES.txt`: licenses for embedded JSCAD, Three.js, and fflate libraries. No redistribution license is asserted for the supplied reference models.

## Development and verification

From this directory, run `npm ci`, `npm run build`, and `npm test`. `node verify-browser.mjs` runs offline Chromium UI/export checks when Playwright's Chromium is installed.

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
