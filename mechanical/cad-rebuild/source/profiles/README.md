# Portable Bambu settings

`x1c-abs-standard.json` is a flattened Bambu project configuration for an X1
Carbon with a 0.4 mm nozzle, Generic ABS, 0.20 mm layers, three walls, 20% infill
and supports. Personal paths and account identifiers are excluded.

Its machine end sequence comes directly from the normal X1 Carbon 0.4 mm vendor
template installed with Bambu Studio 02.06.01.55, dated 20240528. It turns the bed
off (`M140 S0`), uses the vendor filament-unload sequence (`M620/M621 S255`), and
turns the hotend off (`M104 S0`). The maintainer's custom 90°C hold sequence is
retained separately in the local package.

Exact template path relative to the installed application's resource directory:

```text
profiles/BBL/machine/Bambu Lab X1 Carbon 0.4 nozzle template machine_end_gcode.json
```

`provenance.json` records the template's name and SHA-256. Upstream resources are
maintained by [Bambu Lab in Bambu Studio](https://github.com/bambulab/BambuStudio/tree/master/resources/profiles/BBL).
The vendor-derived settings/G-code are covered by Bambu Studio's upstream
[AGPL-3.0 license](https://github.com/bambulab/BambuStudio/blob/master/LICENSE),
copied as `LICENSE-BambuStudio-AGPL-3.0.txt`; they are not relicensed under the
case project's MIT terms. Review and re-slice the project for the actual machine
and material before printing.
