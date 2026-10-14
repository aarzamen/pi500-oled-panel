# OLED Maker Workbench

A focused workspace for printing the native CAD v3 OLED case, planning a measured
variant, or handing the design to another coding agent.

## Use it

Open the [public workbench](https://oled-case-workshop.annonable.chatgpt.site).
For offline use, download the
[complete ZIP](https://github.com/aarzamen/pi500-oled-panel/raw/refs/heads/main/maker-workbench/oled-maker-workbench.zip),
extract it and open `index.html`. Its code, native previews and printable files
are included. The legacy browser editor is `classic.html` in the same package.

Choose a Pi status panel, bench controls, a sensor station, or a plan for another
board. The purpose presets keep the same measured base geometry. Select one back:
both rear panels intact, lower open, or upper open. Download the matching native
STL/STEP files, print four caps, or use the complete kit/Bambu project.

Controls update your dimension plan and fit feedback immediately. Every field has
a reset; Reset all returns to the measured base. More detailed board, screw and
connector fields open below the basic wall and rounding controls. Save settings,
load them later, or download/copy a coding-agent handoff.

## Base files and custom plans

The 3D printable preview and native downloads show the **published CAD v3 base**.
Changing plan dimensions updates the sketch, stack calculations and handoff. It
does not silently turn the base STEP into an edited design. Download the editable
STEP base for your CAD application, or give an agent the handoff and parameters
to regenerate a reviewed variant with the included native generator.

The [classic editor](https://oled-case-workshop.annonable.chatgpt.site/classic.html)
provides the earlier broader browser design tool with live custom STL export.
Its provisional dimensions and geometry differ from native v3. It has no native
STEP export. Keep each design's matching parts together.

## Fit and sourcing

CAD v3 is a prototype; physical assembled fit remains unverified. Read the
[fitment notes](https://github.com/aarzamen/pi500-oled-panel/blob/main/docs/fitment.md)
and [module sourcing](https://github.com/aarzamen/pi500-oled-panel/blob/main/docs/hardware-sourcing.md).
The difficult button stack, nearest-housing-edge datum, rear DuPont openings,
mounting uncertainty and latch/PCB interaction are included in each handoff.

Files are hosted directly. The
[model-posting kit](https://github.com/aarzamen/pi500-oled-panel/blob/main/docs/model-posting.md)
provides Printables and MakerWorld instructions and draft listing copy. No model
listing is implied; assembled print/photos are still needed for a tested posting.

## Develop

Development needs the [source repository](https://github.com/aarzamen/pi500-oled-panel/tree/main/maker-workbench).
The offline ZIP contains the compiled app and print files. In a repository
checkout, open its `maker-workbench` folder with Node.js 22 and npm installed:

```bash
npm ci
npm test
npm run build
```

The build reads the native kit's exact binary STLs and verified manifest, bundles
Three.js with the interface into one HTML file, preserves the classic editor, and
packages the offline files. `site/` is generated output. The editable planner and
handoff logic is in `planner.js`; interface source is in `app.js`, `template.html`
and `workbench.css`.

Original code and docs are MIT. Three.js and embedded classic libraries retain
their [notices](https://github.com/aarzamen/pi500-oled-panel/blob/main/case-playground/THIRD-PARTY-NOTICES.txt)
(also `THIRD-PARTY-NOTICES.txt` beside the offline `index.html`); Bambu-derived settings
retain the separate notice in the CAD kit. See
[project credits](https://github.com/aarzamen/pi500-oled-panel/blob/main/CREDITS.md).
