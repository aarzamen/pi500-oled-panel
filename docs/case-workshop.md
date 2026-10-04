# 3D print screen case maker

**[Launch OLED Case Workshop](https://oled-case-workshop.annonable.chatgpt.site)**

The workshop designs a front shell, optional outer bezel, and matching back cover
for the HW-937AB OLED board used by this project. It runs in the browser and exports
STL files in millimeters. It is separate from the OLED's Pi runtime.

## Make a case

1. Start with **Original footprint**, **Rounded**, **Slim slip fit**, **Screw cover**,
   or **ZIP face style**. The last option adds a beveled window and a separate
   four-key strip based on the supplied alternate reference model.
2. Set the body and face dimensions, then choose the window/button style.
3. Under **PCB mounting screws**, adjust post outside diameter and screw-hole
   diameter. The latter is the printed pilot bore, not a nominal thread designation.
   **Inspect mounting posts** isolates the inside of the front shell.
4. Under **Rear connector opening**, align the gap over the full straight DuPont
   row. It passes through the backplate; there is no top-wall cable notch.
   The optional PCB/pin guide is approximate and stays fixed as the gap moves.
5. Choose the closing mechanism and clearance. Use **Assembled**, **Exploded view**,
   and **Print layout** to inspect the parts.
6. Download the print set. When rounded keys are enabled, it includes a separate
   button-strip STL. Import each part separately into the slicer and inspect
   orientation, bridges, supports, and dimensions.

**Save settings** downloads a JSON design that can be loaded later. Older designs
keep their compatible dimensions and receive the new rear-opening defaults.
Invalid combinations disable export and explain which dimensions need adjustment.

## Fit before committing to a full print

The initial generated shell is 51.1 × 33.16 × 8 mm. It keeps the reference's 40 × 23 mm
PCB post spacing and 3 mm post height. Post and screw-hole diameters are adjustable.
The provisional board is 45 × 28 × 1.6 mm; measure the real board, solder joints,
connector housings, and switch stack.

Print the matching front and rear parts together. The new snap catches and
registration features are absent from the original printed shell, so the new
cover is not a verified drop-in replacement. Check snap insertion/release with the
PCB installed, key travel, and printed screw fit. Slip-fit has no positive latch.

The software checks closed, connected meshes and sampled assembly clearances.
These checks do not establish physical fit, snap strength, or print success.

## Offline files and development

- [Workshop README and source](../case-playground/README.md)
- [Complete offline package](../case-playground/oled-case-workshop.zip)
- [Default snap-fit STL set](../case-playground/starter-snap-print-set.zip)
- [Beveled-window and rounded-key STL set](../case-playground/starter-zip-face-print-set.zip)
- [Library notices](../case-playground/THIRD-PARTY-NOTICES.txt)

The offline HTML has the same controls and built-in geometry code as the public
site. For development, use the npm build and verification commands in the workshop
README. The existing OLED v0.1.0 release assets remain separate from this case tool.
