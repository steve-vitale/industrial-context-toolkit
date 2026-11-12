You are re-checking items that an earlier reading of a piping and instrumentation diagram (P&ID) flagged as uncertain.

Each numbered image is a crop of the same sheet. In image N, the RED rectangle marks item N: one symbol the earlier
reading reported. Thin BLUE rectangles, if any, mark other symbols the earlier reading reported nearby. The list
below gives, for each item, the class and tag the earlier reading gave it.

Classes (the same definitions the earlier reading used):
- tank: vessels, tanks, heat exchangers, columns and other large process equipment.
- pump: pumps, compressors, blowers.
- valve: any valve symbol (manual, control, check, relief, motor-operated) drawn in a line.
- instrumentation: instrument bubbles (circles, circles-in-squares) carrying a tag such as TE, PT, FT, MOV, TCV.
- inlet/outlet: off-page connectors / continuation flags at the edge of the drawing that name another drawing or system.
- general: other in-line symbols (reducers, flanges, strainers, spectacle blinds, etc.).
- Not symbols: line bends, line crossings, flow arrows, the drawing border, the title block, notes and plain text.

For each item, give exactly one verdict about what is inside its RED rectangle:
- "confirm": a symbol is there and the earlier class is right.
- "correct": a symbol is there but it belongs to a different class; give that class.
- "reject": no symbol of any class above is there (only text, a bend, an arrow, the border, empty paper).
- "duplicate": the symbol inside the red rectangle is the same drawn symbol as one marked by a blue rectangle.

Judge only the red rectangle. Do not report other symbols, and do not move or resize any rectangle.
"confidence" is your own 0-1 estimate that your verdict is right. If you cannot tell, say "confirm" with a low
confidence.

Return ONLY a JSON object (no prose, no code fences) with this exact shape:

{"items": [{"n": 1, "verdict": "confirm | correct | reject | duplicate", "class": "the class you see, or null",
            "confidence": 0.0, "reason": "a few words"}]}

Items:
