# Printables and MakerWorld posting kit

Prepared 2026-10-14. This is listing copy and a publication checklist; no model-platform listing has been submitted.

**Recommendation:** publish the CAD v3 listing after a complete print fits the intended board, all four buttons operate, and the cover stays latched. Keep the prototype wording until that evidence exists. MakerWorld currently requires a real printed-object photo for the model gallery, including listings with raw files; renders alone are insufficient. Its print profiles additionally require a photo printed using that profile. [Model guidelines](https://wiki.bambulab.com/en/makerworld/tutorials/model-upload-guidelines), [profile guidelines](https://wiki.bambulab.com/en/makerworld/tutorials/print-profile-upload).

## Ready-to-paste title

**0.96-inch four-button OLED case and stand — CAD v3 prototype**

After assembled fit checks, remove “prototype” and add the tested board identification to the description. Describe it as a compact module case; the builder's current module appears to be the most compact of the variants he owns.

## Ready-to-paste description

A compact enclosure and tilted stand for the small eight-pin, 0.96-inch OLED module with four buttons used by the Pi 500 OLED Panel project. The enclosure measures **51.3 × 33.4 × 12.2 mm**. It includes a matching front, snap cover, four separate button caps, and a stand, with rear connector-opening alternatives.

**CAD v3 prototype:** geometry and slicing have been checked. A successful print assembled with the board, button operation, and latch retention have not yet been demonstrated for this revision. The standalone OLED software has been physically tested on a Pi 500; that does not establish fit for this case.

This design targets the builder's small **HW-937AB-style module**. The builder identifies the [ACEIRMC five-pack of 0.96-inch SSD1315 yellow/blue OLED modules with four buttons](https://www.amazon.com/dp/B0GWQPY2C7) as the purchased module. The seller specifies a **44.53 × 27.66 mm** module, eight pins at 2.54 mm pitch, and four independent key interfaces. The community PCB STEP used by the CAD has a **44 × 27 mm** outline; the larger seller envelope is used conservatively for latch-clearance checks. Confirm the dimensions on your actual board. See the [sourcing and variant fit notes](https://github.com/aarzamen/pi500-oled-panel/blob/main/docs/hardware-sourcing.md).

Screen diagonal alone does not establish compatibility: other 0.96-inch boards, 1.3-inch boards, and four-pin modules can have different board outlines, mount positions, buttons, and headers. An I2C display label does not establish that the buttons share the display's four wires; this module has separate K1–K4 connections. Compare your board with the fit notes before printing or buying.

Print one front, one chosen back, **four button caps**, and the stand. Use the matching CAD v3 parts together. Fit the caps from inside, then fit the board and cover. The dual-knockout back has two scored 0.4 mm membranes with 23 × 6.4 mm openings intended for eight straight DuPont connectors exiting through the rear. Choose the relevant opening for your header orientation. Check that the caps release freely and the board does not obstruct either snap arm. Confirm orientation, supports, and material in your slicer; final tested print settings will accompany physical print evidence.

Editable native STEP files, STL parts, a Bambu Studio project, portable CAD source, and design previews are included in the [CAD v3 kit](https://github.com/aarzamen/pi500-oled-panel/tree/main/mechanical/cad-rebuild). The [live OLED Case Workshop](https://oled-case-workshop.annonable.chatgpt.site) and [offline workshop ZIP](https://github.com/aarzamen/pi500-oled-panel/raw/refs/heads/main/case-playground/oled-case-workshop.zip) provide a separate browser editor that exports STLs; its generated cases also require fit checks. The browser editor does not regenerate these native CAD v3 files.

The [project repository](https://github.com/aarzamen/pi500-oled-panel) includes the Pi 500 runtime, wiring, recovery instructions, and validation notes. The enclosure's mechanical compatibility and the software's supported hosts are separate questions.

**Credits:** Aaron Arzamendi supplied the physical design direction, measurements, and physical tests. OpenAI Codex/ChatGPT assisted with native CAD, code, and verification. Anthropic Claude contributed to earlier CAD and coding collaboration. Hellfire's rough community PCB reference informed the mechanical work; that PCB file and derived hardware assembly are not included because redistribution terms are unverified. The earlier [SSD1306/SH1107 snap-fit case and stand](https://makerworld.com/en/models/1227573-ssd1306-sh1107-oled-display-case-snap-fit-stand#profileId-1272300) inspired the project. The published native case and stand are newly constructed geometry.

Project originals retain the repository's **MIT license** and copyright notice. Third-party references retain their own rights.

## Category and tags

Choose the closest available **electronics / display enclosure** category on each platform. Suggested tags: `oled`, `0.96 inch`, `ssd1315`, `hw937ab`, `four buttons`, `electronics`, `enclosure`, `case`, `stand`, `raspberry pi`, `pi500`, `snap fit`, `dupont`. These are recommendations, not a verified list of current picker labels.

## Upload files

Upload individual STLs so users can select parts without unpacking the full kit:

- `STL/front.stl` — one front.
- `STL/back-dual-knockouts.stl` — default back; one required.
- `STL/back-lower-open.stl` and `STL/back-upper-open.stl` — alternative backs; choose one back total.
- `STL/button-cap.stl` — print four copies.
- `STL/stand.stl` — one stand.
- `STEP/enclosure-only.step` and individual STEP parts — editable enclosure geometry.
- `OLED-case-CAD-v3.3mf` — standard Bambu Studio project; publish its print profile after print/photo evidence.
- Public kit ZIP, fit/assembly README, and MIT license notice.

Use the [kit README and downloads](../mechanical/cad-rebuild/README.md) for the current ZIP, previews, validation receipts, and standard Bambu project. Add a **Bambu Studio print profile** after printing with its normal cooldown/unload settings and photographing the result. MakerWorld defines a print profile as a Bambu Studio project containing geometry and printing settings; a generic geometry-only 3MF would instead be a raw model file. [Upload instructions](https://wiki.bambulab.com/en/makerworld/tutorials/how-to-upload-models).

## Cover and gallery order

1. A real photo of this revision assembled on its stand, with the intended board installed. Use this as the published cover.
2. Complete printed parts before assembly; every required part visible.
3. Exploded CAD preview, clearly captioned **CAD render**.
4. Board front/back photos with identification, pin labels, and a ruler.
5. Dimension/clearance preview showing the mounting posts and button contact surfaces.
6. Rear photo showing straight DuPont housings, the selected opening, and the retained top walls.
7. Short clip of all four button presses/releases and the latched cover with the board installed.
8. Workshop screenshot with the live editor link; caption it as the separate browser design tool.

Use the kit's original rendered previews while preparing the draft. They show design geometry and cannot substitute for print photos. Keep photos of earlier revisions labeled with their revision.

## Fit evidence to record

The mounting pitch is approximately **40 × 24 mm**. The measured switch peak is **2.65 mm** above the PCB when released; the fixed housing is **1.8 mm** high. The **4.75 mm** measurement is from the PCB right edge to the **nearest fixed switch-housing edge**. The modeled exposed post is **2.668484 mm** above a **0.681516 mm** base. Confirm these against the actual board, including the board outline and header orientation.

Record the printer, nozzle, layer height, material, successful printed revision, latch engagement with the PCB installed, full button travel/release, and connector clearance. Use a final fit photo and button/latch clip before changing the prototype status.

## Platform license and originality checks

Preserve MIT for the original source and CAD kit. Printables' free-model terms name Creative Commons, GNU, and BSD choices but do not explicitly establish an MIT picker option; its current license list has expanded since those terms. Verify the actual picker when posting. If MIT/custom licensing is unavailable, the maintainer must deliberately choose any additional platform model license before submission; this document does not grant one. Keep the MIT notice in downloads. [Printables terms, sections 2.1–2.4](https://www.prusa3d.com/page/terms-of-service-of-printables-com_231249/), [Prusa's 2026 license update](https://blog.prusa3d.com/open-community-license-v1-1-the-new-plugin-system-more-examples-and-your-questions-answered_137202/), [MIT text](https://opensource.org/license/mit).

For MakerWorld, the supplied provenance supports **Original** for this newly constructed case/stand geometry, with the inspiration credit above. If uploaded geometry is actually modified from someone else's model, use **Remix**, link the exact source page, and verify its license permits the derivative. Inspiration credits alone do not establish redistribution rights. Upload only the original enclosure assets and previews from the public kit. MakerWorld requires the correct upload type and license. [Upload instructions](https://wiki.bambulab.com/en/makerworld/tutorials/how-to-upload-models), [model guidelines, updated 2026-07-29](https://wiki.bambulab.com/en/makerworld/tutorials/model-upload-guidelines).

Use an ordinary free listing for the proposed GitHub/Printables/MakerWorld distribution. Any platform license selection should reflect the continuing MIT release and the planned cross-platform distribution.
