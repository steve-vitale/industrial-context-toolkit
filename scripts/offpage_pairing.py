"""The cross-sheet off-page pairing rule: which off-page connector on one sheet continues on which connector of
another, read only from the connectors' printed text and each sheet's supplied identity.

    result = pair(connectors, sheets)   # {"pairs", "status", "names", "candidates"}

connectors: [{"id", "sheet", "text"}] -- every unpaired off-page connector of the set; text is what is printed on
            it (reference and description).
sheets:     {sheet: {"number": drawing number or registered sheet id, "title": title block, "system_code": code}};
            every field optional.

A connector NAMES a sheet when that sheet's number is printed on it: literally, separator tolerant ('P-204' reads
'P 204', 'P204', 'P\N{EN DASH}204' and an unreadable character between the parts, never 'P-2045' or 'XP-204'),
leading zeros ignored ('120-1' reads '120-01'). A number that is a single numeric run ('180', a drawing registered
without sheet numbers) must follow a drawing word (PID, P&ID, DWG, DRAWING, SHT, SHEET), and then names every sheet
of that drawing. Candidates, strongest first (each is a pair's `method`):

  reciprocal_supplied_numbers        x on sheet A names B, and y on B names A;
  one_way_number_plus_sheet_title    x names B; y names no sheet of the set and no drawing, and carries every word
                                     (at least two) of A's title;
  one_way_number_plus_system_code    x names B; A has no supplied number; y names no sheet of the set and the system
                                     code printed before its drawing reference is A's system code.

x must name exactly one sheet of the set. Candidates are taken strongest method first, then by description
similarity (word overlap of the two texts with the references removed), each connector pairing once. A choice is
never made by input order: when a connector's best candidates are equally good, none of them pairs and every end of
that tie stays unpaired with the tied candidates named, for a person to decide. Each pair records its method,
`alternatives` (how many other candidates either end had) and evidence (what each end printed, the similarity, and
chosen_by: "only candidate" or "highest description similarity"). Every pair is a review candidate, never an
established continuation.

Where this sits: scripts/build_twin.py pairs connectors inside its own model build (references written like
"PID 140-1", reciprocal or with a matching system code; it breaks similarity ties by order) and is hash-pinned and
left as it is: it is the first pass. This module is the one cross-sheet rule every later caller applies to what
that pass leaves: import_drawing_set.py (supplied drawing numbers, titles and system codes) and one_map.py (printed
references against the registered sheet ids). Measured on the public OPEN100 sheets 0-5 against a key read from the
drawings' printed references: examples/own-drawing/offpage-key.json, checked by scripts/test_offpage_pairing.py.
Pure, stdlib only, no model calls.
"""
import re

METHODS = ("reciprocal_supplied_numbers", "one_way_number_plus_sheet_title", "one_way_number_plus_system_code")
TITLE_STOP = {"PID", "P&ID", "DRAWING", "DWG", "SHEET", "SHT", "REF", "SEE", "FROM", "TO", "THE", "AND", "OF", "FOR"}
WORD_STOP = {"TO", "FROM", "THE", "OF", "AND", "&", "PID", "P&ID", "SYSTEM", "SYS", "DWG", "DRAWING", "SHT", "SHEET",
             "REF", "SEE"}
DRAWING_WORD = r"(?:P\s*&?\s*ID|DWG|DRAWING|SHT|SHEET)"
SEP = r"[^A-Z0-9\n]{0,3}"
ANY_REFERENCE = re.compile(DRAWING_WORD + SEP + r"\d")
CODE_BEFORE = re.compile(r"(?<![A-Z0-9])([A-Z]{2,6})" + SEP + r"P\s*&?\s*ID" + SEP + r"\d")


def number_pattern(number):
    """A supplied drawing number as a literal, separator- and leading-zero-tolerant pattern (module docstring)."""
    runs = re.findall(r"[A-Z0-9]+", str(number or "").upper())
    if not runs:
        raise ValueError(f"drawing number {number!r} has no letters or digits")
    parts = ["0*" + (r.lstrip("0") or "0") if r.isdigit() else re.escape(r) for r in runs]
    body = SEP.join(parts)
    if len(runs) == 1 and runs[0].isdigit():
        return re.compile(DRAWING_WORD + SEP + body + r"(?![A-Z0-9])")
    return re.compile(r"(?<![A-Z0-9])" + body + r"(?![A-Z0-9])")


def words(text):
    t = re.sub(r"(?<=[A-Z])-(?=[A-Z])", "", (text or "").upper())  # BY-PASS -> BYPASS
    return {w for w in re.findall(r"[A-Z][A-Z0-9.&]*", t) if w not in WORD_STOP and len(w) > 1}


def title_words(text):
    return {w for w in re.findall(r"[A-Z][A-Z0-9&]{2,}", (text or "").upper()) if w not in TITLE_STOP}


def pair(connectors, sheets):
    """-> {"pairs": [{"a", "b", "sheet_a", "sheet_b", "method", "description_similarity", "alternatives",
    "evidence"}] in decision order, "status": {connector id: "paired" or why it is unpaired},
    "names": {connector id: [sheets of the set its text names]}, "candidates": {connector id: [candidate partners]}}."""
    patterns = {s: number_pattern(v["number"]) for s, v in sheets.items() if (v or {}).get("number")}
    ids = [c["id"] for c in connectors]
    if len(set(ids)) != len(ids):
        raise ValueError("connector ids must be unique")
    by_id = {c["id"]: c for c in connectors}
    text = {c["id"]: (c.get("text") or "").upper() for c in connectors}

    def stripped(cid, *sheet_keys):
        t = text[cid]
        for s in sheet_keys:
            if s in patterns:
                t = patterns[s].sub(" ", t)
        return words(t)

    named = {c["id"]: sorted(s for s, p in patterns.items() if s != c["sheet"] and p.search(text[c["id"]]))
             for c in connectors}
    found = {}
    for x in connectors:
        if len(named[x["id"]]) != 1:
            continue
        a, b = x["sheet"], named[x["id"]][0]
        meta_a = sheets.get(a) or {}
        tw = title_words(meta_a.get("title"))
        for y in connectors:
            if y["sheet"] != b or frozenset((x["id"], y["id"])) in found:
                continue
            ny, evidence = named[y["id"]], {"a_names": sheets[b]["number"]}
            code = CODE_BEFORE.search(text[y["id"]])
            if ny == [a]:
                method = METHODS[0]
                evidence["b_names"] = meta_a["number"]
            elif not ny and not ANY_REFERENCE.search(text[y["id"]]) and len(tw) >= 2 and tw <= words(text[y["id"]]):
                method = METHODS[1]
                evidence["b_carries_title_words"] = sorted(tw)
            elif not ny and not meta_a.get("number") and meta_a.get("system_code") and code \
                    and code.group(1) == str(meta_a["system_code"]).upper():
                method = METHODS[2]
                evidence["b_system_code"] = code.group(1)
            else:
                continue
            wx, wy = stripped(x["id"], b, a), stripped(y["id"], a, b)
            sim = round(len(wx & wy) / len(wx | wy), 2) if wx | wy else 0.0
            found[frozenset((x["id"], y["id"]))] = (METHODS.index(method), -sim, x["id"], y["id"], method, sim,
                                                    evidence)
    candidates = sorted(found.values(), key=lambda c: c[:4])
    partners = {}
    for c in candidates:
        partners.setdefault(c[2], []).append(c)
        partners.setdefault(c[3], []).append(c)
    taken, tied, pairs = set(), {}, []
    for rank, neg, xi, yi, method, sim, evidence in candidates:
        if {xi, yi} & (taken | set(tied)):
            continue
        # a rival still open, or itself undecided in a tie, could be the real partner; only taken ends are out
        open_rivals = [c for c in partners[xi] + partners[yi] if c[2:4] != (xi, yi) and not {c[2], c[3]} & taken]
        group = [c for c in open_rivals if c[:2] == (rank, neg)]
        if group:  # equally good candidates: never decided by input order; every end waits for a person
            ends = sorted({e for c in [(rank, neg, xi, yi)] + group for e in c[2:4]})
            for e in ends:
                tied[e] = [o for o in ends if o != e and by_id[o]["sheet"] != by_id[e]["sheet"]]
            continue
        taken |= {xi, yi}
        evidence = dict(evidence, description_similarity=sim,
                        chosen_by="only candidate" if not open_rivals else "highest description similarity")
        pairs.append({"a": xi, "b": yi, "sheet_a": by_id[xi]["sheet"], "sheet_b": by_id[yi]["sheet"],
                      "method": method, "description_similarity": sim,
                      "alternatives": max(len(partners[xi]), len(partners[yi])) - 1, "evidence": evidence})
    status = {}
    for c in connectors:
        n, cid = named[c["id"]], c["id"]
        status[cid] = ("paired" if cid in taken else
                       f"unpaired: tied with equally likely candidates ({', '.join(tied[cid])}); a person says which "
                       "pairs with which" if cid in tied else
                       "unpaired: its candidates paired elsewhere or wait on a tie" if partners.get(cid) else
                       "unpaired: names no sheet of this set" if not n else
                       "unpaired: target sheet is in this set but no matching connector was found" if len(n) == 1
                       else "unpaired: names more than one sheet in this set")
    candidates_of = {cid: sorted({e for c in cs for e in c[2:4] if e != cid}) for cid, cs in partners.items()}
    return {"pairs": pairs, "status": status, "names": named, "candidates": candidates_of}
