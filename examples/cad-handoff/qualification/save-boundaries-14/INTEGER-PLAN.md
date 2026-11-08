# Correct the authored integer control before interpreting it

Declared after observing payload-3 and before preparing/running integer-4.
The 60000..60005 USERI5 values in payload-2/3 are outside signed 16-bit
range. Autodesk's HEADER reference assigns USERI1..5 group code 70; its
group-value reference assigns 60..79 to 16-bit integers. The observed
-5536..-5531 are exactly input minus 65536, already visible on native import.
That is not evidence of loss of valid input. Retain the original records.

- https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-DXF/files/GUID-A85E8E67-27CD-4C59-BE61-4DC9FADBE74A.htm
- https://help.autodesk.com/cloudhelp/2026/ENU/AutoCAD-DXF/files/GUID-2553CF98-44F6-4828-82DD-FE3BC7448113.htm

Prepare twelve successor sources from exact payload-3 sources, changing only
the raw USERI5 value span to 6000..6005. Rebind the proposal source hash and
regenerate its exact source-preserving candidate. All XDATA, XRECORD and
application registration sentinels remain literal. Also use five copies of
the first used source with USERI5 -32768, -1, 0, 1, 32767. Freeze every input
before native execution. Use the same completed probe, controller, image,
selected settings and explicit source-version exports, plus fresh import.

Acceptance is literal sentinel preservation (including USERI5) in every
returned file and native observation; keep unchanged strict reports even
if these selected fields survive. No missing XRECORD or registration waiver.
All sources are exposed authored diagnostic revisions, not held-out evidence.
