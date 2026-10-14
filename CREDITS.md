# Credits and provenance

## Builder and AI collaboration

**Aaron Arzamendi** is the builder and maintainer. He supplied the hardware,
physical design direction, measurements, fit feedback and device tests.

**OpenAI Codex and ChatGPT** assisted with the Pi software, browser design tools,
native CAD construction, geometry checks, documentation and publication. Codex
used CadQuery to build the v3 case and stand as editable native solids, then
checked exported STEP/STL and software slicing. These checks do not replace
Aaron's physical assembly and print validation.

**Anthropic Claude** contributed to earlier CAD and coding collaboration, as
credited by the maintainer. This credit records that collaboration without
assigning a specific current v3 file or test to Claude.

This project grew through AI-assisted coding and measured physical iteration.
The working software, editable geometry, receipts and fit limitations are
included so others can inspect and continue it.

## Hardware and design references

- **Hellfire — “OLED | 0.96 | 4 button,” April 8, 2025**, from the
  [GrabCAD community library](https://grabcad.com/library). The maintainer supplied
  `0.96Oled_W_4_Buttons.step` and its author screenshot. The author described rough
  caliper measurements and later noted button size/position corrections. It
  informed the hardware envelope; physical measurements override it where
  available. The exact model-page URL and redistribution terms are unverified.
  The original and derived hardware solids stay outside the public kit. The
  [CAD README](mechanical/cad-rebuild/README.md#reference-provenance-and-licenses)
  records the original file hash for optional validation.
- [SSD1306/SH1107 snap-fit OLED case and stand on MakerWorld](https://makerworld.com/en/models/1227573-ssd1306-sh1107-oled-display-case-snap-fit-stand#profileId-1272300)
  inspired the earlier case/stand experiments. Native v3 case and stand geometry
  is newly constructed project work. This link does not grant rights to that
  model or distribute its files.
- The workshop retains the builder-supplied `screeen1.stl` and
  `096+4btn+-+bat_stls.zip` comparison assets and shape references. A supplied
  Raspberry Pi camera case inspired its side-catch arrangement. The original
  authors and redistribution licenses for those supplied references were not
  established. Their inclusion in the earlier workshop does not make them MIT;
  see [workshop notices](case-playground/README.md#source-and-licenses).
- [ACEIRMC Amazon B0GWQPY2C7](https://www.amazon.com/dp/B0GWQPY2C7) is the module
  source identified by the builder. [Sourcing notes](docs/hardware-sourcing.md)
  distinguish its listing from other variants and candidates.

## Artwork, photographs and software

The builder identifies the startup subject as **George**. The original 128×64
artwork is preserved unchanged in
[george-startup.png](oled_panel/assets/george-startup.png), reused from his
Meshtastic Tracker work. Its historical filename used “wolf”; George is the
builder's identification. This publication adds no generated replacement.

The board photographs are supplied by the builder. Workshop screenshots and
native case/stand renders are project-generated illustrations. Renders show
geometry and are labeled separately from actual print evidence.

The runtime uses Pillow, psutil, luma.oled, gpiozero and lgpio. The browser workshop
uses JSCAD, Three.js, fflate and build tooling; its embedded copies retain
[third-party notices](case-playground/THIRD-PARTY-NOTICES.txt). Native CAD generation
uses CadQuery/Open CASCADE, with Trimesh and related libraries for validation and
preview generation; installed dependencies retain their upstream licenses.

The bundled Bambu print settings derive from **Bambu Studio** and its official
X1 Carbon presets. They retain the
[separate upstream notice and provenance](mechanical/cad-rebuild/source/profiles/README.md),
including the AGPL license text. They are not covered by the project's MIT grant.

Original project code, case/stand geometry and documentation use the
[MIT license](LICENSE), copyright 2026 Aaron Arzamendi. Attribution to an AI tool
or a reference creator does not transfer rights to third-party source material.
