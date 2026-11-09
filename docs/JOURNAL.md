# Build journal

Entries describe their historical snapshots. Local receipts, review conversations, intermediate render packages
and sealed trial evidence are not included here. A historical verification statement is not a current result.
AI coding agents (Claude Code, and later Codex) wrote most of the code and first drafts; I set the direction and
checked the results.

How this project was built and why each choice was made, written as it happens. Results are in the README and
`out/`. This file is the reasoning behind them.

Each entry: **What** (one line) · **How** (the method, concretely) · **Why** (the reasoning, including what we rejected) ·
**Lesson** (what generalizes beyond this project) · **At your plant** (how to apply it to a real site; full guide in [AT_YOUR_PLANT.md](AT_YOUR_PLANT.md)).

---

## 1. Start with a sketch that runs end to end

**What:** a hand-built model of the Tennessee Eastman plant, plus one script that turns it into every output format.

**How:** one JSON file describes the plant: units, streams, instruments, valves, and where each item came from. A
Python script (stdlib only) reads that file and produces:
- SVG graphics with tag IDs embedded in each element
- an Ignition tag/UDT import file
- a PI Builder-style asset sheet
- a plain-language review sheet for operations

**Why:**
- **One model, many outputs.** If the SVG, the Ignition tags and the PI hierarchy were each built separately, they'd
  drift apart. With one source, a correction made once shows up everywhere.
- **Build the output end first.** Before asking any AI to read a drawing, we need to know exactly what shape its
  answer must take. The hand-built model defines that target. It also becomes the answer key when we score
  extraction later.
- **Tags inside the graphics.** Every element carries a `data-tag`, so connecting live data is a mapping step,
  not a redraw.
- **Stdlib only.** Anyone can run it with no install friction.

**Lesson:** the first render had instruments clipped at the canvas edge and drawn over pipes. Every structural check
passed (unique tags, valid references, ISA letters matching the measured variable), but no check could see layout.
Someone had to look. *Checks prove what they check, and nothing more.*

**At your plant:** define the target format first: your tag convention, your asset hierarchy levels, and which attributes Ignition or PI needs. Then capture a few sheets by hand into exactly that format. That becomes both your spec and your answer key. Always have a person look at rendered output; structural checks miss layout and meaning. See [AT_YOUR_PLANT.md](AT_YOUR_PLANT.md) §2.

---

## 2. Plan the whole arc before building more

**What:** decided who this is for, what counts as proof, and what's out of scope, before writing more code.

**How:** wrote down the constraining questions (audience, which drawings, which platforms, who reviews, which AI
tools, what budget) and answered each one. Then researched every assumption the plan rested on, before building
anything that depends on it.

**Why:** the expensive mistakes in a project like this are wrong *assumptions*, not wrong code. Three assumptions
failed under research:

| Assumption | What research showed | What we changed |
|---|---|---|
| We'd score AI extraction against our own answer key | A public dataset (PID2Graph) has independently annotated real P&IDs, including the open OPEN100 reactor design | Score against third-party ground truth. A number we define ourselves is weaker evidence |
| SVGs can be pasted into PI Vision | PI Vision stopped supporting plain custom SVG import (2023+) | Graphics go to Ignition Perspective (it keeps SVG element ids, so styles can bind to tags); PI gets the asset hierarchy |
| We could demo on both platforms for free | There's no free PI environment for individuals (only a 45-day developer trial); Ignition has a free, resettable trial | Ignition carries the "it actually loaded" proof; the PI output is clearly labeled as not import-tested |

**Lesson:** check vendor reality before promising a workflow. Half a day of research removed a deliverable that
would have been impossible.

**At your plant:** before promising anyone a workflow, confirm three things:
- what your platform versions actually import (Ignition, PI AF, PI Vision);
- whether your drawings are intelligent P&IDs you could export instead of reading as images;
- what your security policy allows to leave the network.

Any one of these can change the plan. See §1 and §5.

---

## 3. Write the fairness rules before running any comparison

**What:** Claude, GPT and Gemini will read the same drawings. The rules for comparing them are fixed in advance.

**How:**
- same images, same prompt, same output schema, same scorer
- record which model and access path produced every run
- report first-try scores, not the best of several attempts
- repeat runs to show variance
- report real and synthetic drawings separately

**Why:** comparisons drift toward whatever the author hoped to find. Fixing the rules before seeing results is the
cheapest guard against that. The tools are also reached through different paths (subscriptions, an API), so we
record the path and say so wherever it could explain a gap.

**Lesson:** decide how you'll judge before you see the answer.

**At your plant:** when you evaluate vendors or models, give each one the same sheets, including your worst scans. Score them against the same hand-built key and agree on the scoring rules before the demo. Vendor demos on hand-picked drawings tell you little.

---

## 4. Work within the hardware you have

**What:** the scoring dataset is one 9.3 GB zip. The build machine has about 11 GB free, and Ignition needs room
too.

**How (planned):** a zip file keeps its table of contents at the end. We read just that part over HTTP range
requests, then fetch only the entries we need (the OPEN100 subset and the real P&IDs).

**Why:** buying disk or cleaning up would also work, but pulling only what you need is the habit that scales.
Datasets in this field are large, and most projects need a small slice of them.

**Lesson:** constraints are design inputs, not blockers.

**At your plant:** the equivalent constraints are bandwidth, data-egress policy, and whether a cloud model may see your drawings at all. Design for the narrowest one first: send only the sheets in scope, redact title blocks if policy requires, or use an on-premises model. See §5.

---

## 5. Check the answer key against a source, with a checker you've tested

**What:** the 37 instruments and valves in the seed model were checked against the open Tennessee Eastman source
code. 36 matched and 1 was wrong.

**How:**
- The original 1993 paper is paywalled. The simulation code the research community uses (`teprob.f`, Braatz group,
  open license) lists every measurement and valve, with units, in its header comments.
- `scripts/verify_te_source.py` downloads that file and parses the list.
- It compares each model item's name and units, then writes a verification record into the model: status, source,
  date, the exact source line, and the old value whenever something was corrected.
- Run it again any time; correction history is kept.

**Why a script and not a careful read:**
- A script can be rerun, and anyone can audit it.
- It also hands the operations review a list in which every row already says where it came from.

**The checker needed checking too:**
1. **First run:** it flagged "Separator temperature" as wrong because the source abbreviates it to "Sep Temp".
   That was a false alarm.
2. **First fix (wrong):** a stop-word list that was too aggressive, which threw away the very words being compared.
3. **Second fix:** abbreviation handling, plus a small stop-word list.
4. **Negative control:** we then planted three deliberate errors (a wrong unit, the wrong equipment, an unrelated
   name). It caught all three. A checker that only ever says "confirmed" proves nothing.

**What it found:** measurement 22 (TI-122) was in the model as the *condenser* cooling-water outlet temperature.
The source calls it the *separator* cooling-water outlet temperature. Many write-ups say "condenser" because the
cooling-water valve (XMV 11) is labeled "condenser cooling water flow". The model now uses the source's name.
Which equipment the tag belongs to is left as an explicit open question for operations review.

**Bonus:** the source also gives each composition analyzer's sampling period and dead time (6 minutes for
reactor-feed and purge-gas analysis, 15 minutes for product analysis). These map directly to tag scan settings,
so they're now in the model.

**Lesson:** verify the verifier. Test a checker with known-bad input before you trust its "all clear". And when
the source itself is ambiguous, record the question; don't quietly resolve it.

**At your plant:** your sources disagree too. That includes the drawing vs the DCS tag list vs the historian vs the maintenance asset register. A small script that cross-checks extracted tags against those lists does the same job as `verify_te_source.py`, and the mismatches it finds are often real documentation gaps, not AI errors. Test the script with planted errors before trusting it. See §1 and §4.

---

## 6. Take 0.2% of a 9.3 GB dataset

**What:** we pulled the 12 real P&IDs from the PID2Graph dataset (the OPEN100 reactor design drawings, plus their
answer keys) out of a 9.3 GB zip. We downloaded 19.5 MB.

**How:**
- The server supports HTTP range requests: "send me bytes X to Y".
- A zip file stores its table of contents at the end. `scripts/fetch_pid2graph.py` wraps the remote file in a small
  seekable reader, so Python's standard `zipfile` module can read that table of contents over the network (10 MB
  for all 74,655 entries).
- It then fetches only the entries we ask for. Nothing else is downloaded.

**What the listing showed (worth knowing before writing a scorer):**
- **Contents:** the archive has the 12 OPEN100 drawings, 500 synthetic drawings from an earlier dataset (Dataset-P&ID),
  500 PID2Graph synthetic drawings, and tiled "patched" copies of all three for model training.
- **Not in the public archive:** the paper's 60 annotated real industrial P&IDs. That leaves OPEN100 as the only real,
  inspectable test set.
- **Answer-key format:** each drawing comes with a `.graphml` graph. Nodes are symbols with a class and a bounding box.
  The 8 classes are connector, crossing, arrow, instrumentation, valve, inlet/outlet, general and background. Edges
  are the lines between symbols.
- **No text in the key:** the drawings carry real tags (MOV 1113, TCV 1115, TE 111216A), but the answer key doesn't
  record any text. Tag reading can't be scored against this key. The TE plant (entry 5) is where tag accuracy gets
  measured.

**Why it matters:**
- The extraction prompt's output schema has to map onto these 8 classes, or the score is meaningless.
- That's decided now, before any model runs, so no one can tune the mapping after seeing results (entry 3).

**Lesson:** read the answer key's format before building the thing it grades.

**At your plant:** you'll rarely have a third-party answer key. Hand-annotate 3–5 sheets yourself, including a bad scan, and decide up front what counts as a match. Do you need the exact tag text, the right symbol class, the right equipment, the right connection? Decide before the first model run. See §2.

---

## 7. Fix the scoring rules first, then test the scorer until it can't be fooled

**What:** a scorer that grades any model's extraction against the PID2Graph answer keys, written and tested before
a single model ran.

**How:**
- **Profile the key.** It has 10 classes, not 8. Four are drawing plumbing (2,408 line-bend points, 734 line
  crossings, 451 flow arrows, 48 drawing frames). Six matter for a twin: instruments (350), valves (257), other
  inline symbols (234), off-page connectors (96), tanks and vessels (35), pumps (16).
- **Detection.** Score only the six asset classes, matching predicted boxes to key boxes by overlap. Two thresholds:
  - strict IoU ≥ 0.5, the object-detection standard;
  - rough IoU ≥ 0.1, "in about the right place", because vision models give loose coordinates.
- **Connectivity.** Score at the asset level: which tanks, pumps, valves and instruments connect, tracing through
  the line-bend and crossing points. That's what a twin needs.
- **Controls.** Five tests on every drawing: a perfect answer (built from the key itself), an empty answer, every
  class deliberately wrong, every box moved half a sheet, and half the symbols dropped.

**What the controls caught:**
1. **First rule:** "the predicted box centre lands near the key box". With every class wrong, it still gave
   **15–32% credit**, because a mislabeled valve landed in the neighbouring instrument's zone and small symbols sat
   inside a tank's large box.
2. **Tightened version:** still 3–20%. The rule itself was wrong, not the setting. Switched to IoU.
3. **My own control was weak:** the "moved" test also shrank every box to 1×1, which can never overlap anything
   under IoU, so it passed for the wrong reason. Fixed to keep box sizes.
4. **One honest chance floor:** drawing 6 contains two identical reactor-coolant-pump details half a sheet apart.
   Shifting every box half a sheet lands one detail on the other: strict score 0, rough score 8.8%. So the rough
   score carries a small chance floor on repetitive sheets. It's documented, not hidden.

**Why this matters more than the model comparison itself:** a loose scorer flatters every model at once, and it
flatters weak ones most. Without the controls, a model that labeled everything wrong would have scored 15–32%.

**Lesson:** test the grader before you grade. Positive controls prove it can say yes; negative controls prove it
can say no. Both are needed.

**At your plant:** before trusting any accuracy number from a vendor or an internal pilot, ask how a match is
decided, and ask what a deliberately wrong answer scores under the same rules. If nobody has tried, try it. Also
decide which symbol classes matter for your use. Scoring line-bend points next to pumps inflates or deflates
results for reasons that don't matter to operations.

---

## 8. Define "done well" first, then guard the definition from the people chasing it (us)

**What:**
- Three runs of three frontier models (Claude, GPT via Codex, Gemini) on 12 real drawings: first try, an identical
  repeat, and a prompt revision.
- An open-weight model (Gemma 4 31B) as a stand-in for what a plant could run fully offline.
- The evaluation rules that make those numbers worth anything. They're written up in full in
  [EVALUATION.md](EVALUATION.md).

**How we define "done well":** not "a high score".
- The outcome is a reviewed asset model that costs operations less time than building it by hand, with no more
  errors.
- Every metric is a proxy for that, so each one is listed with what it *can't* see. Rough detection can't judge
  graphics precision; strict detection can't tell whether a class matters to operations; nothing on the public
  dataset can judge tag text.
- The last word belongs to the operations review: what a person who runs the unit still had to fix.

**How (the anti-Goodhart rules, each one used in this project):**
1. **Rules written before results.** The scorer's rules are dated and were committed before any model ran.
2. **The grader was tested before it graded.** A deliberately wrong answer scored 15–32% under the first scorer; it
   scores about 0 now (entry 7).
3. **No single headline.** Precision and recall, strict and rough, per class, and connectivity separately.
4. **Noise measured before claims.**
   - The identical repeat run showed Claude and Codex move about ±0.03 between runs, so their 0.85 vs 0.87 is a tie.
   - First-try Gemini moved ±0.13, which is how we found its problem.
5. **Failures count as zero.** No tool looks better by crashing quietly.
6. **First try stays the headline.** Every later change is labeled as a change.
7. **Tune on one set, report on another, and admit it when we didn't.**
   - Prompt v2 was written after seeing first-try results on all 12 drawings. That breaks the held-out rule in
     spirit.
   - Why we think the bias is small: the change was format-only, applied to every tool, and barely moved the two
     tools without the format problem.
   - Still, from now on any change is tuned on a declared development set and checked once on a sealed set nobody
     has looked at.
8. **Don't teach to the answer key.** Every model scores poorly on the key's catch-all class `general`
   (F1 0.11–0.45), because "general" means whatever the annotators decided. We could tune prompts to guess their
   habits and the score would rise. A digital twin would gain nothing. We report it and leave it alone.
9. **Price the gain.** Time and cost per sheet sit next to every score.

**What the numbers say (12 real drawings; details in EVALUATION.md §4):**

| Tool | Found + right class: first → repeat → v2 | Connections (v2) |
|---|---|---|
| Codex (gpt-6.1-sol) | 0.87 → 0.87 → 0.85 | 0.53 |
| Claude (claude-opus-5-5) | 0.85 → 0.85 → 0.85 | 0.42 |
| Gemini (gemini-3.1-pro-preview) | 0.44 → 0.57 → 0.74 | 0.24 |

- **Gemini's gap was mostly format, not vision.** On 5 of 12 drawings it wrote box coordinates in a different axis
  order (y before x). Those drawings scored about 0 as delivered and 0.60–0.92 with the axes swapped back.
  - Prompt v2 replaced the bare `[x, y, x, y]` list with named fields (`x_min`, `y_min`…). The collapses
    disappeared, and its score went from 0.44 to 0.74.
  - The first-try number is still the headline. In production, a silently wrong format would have put every box in
    the wrong place.
- **Everyone is near-perfect on instruments and off-page connectors (0.98–0.99), and everyone misses more than half
  of the connections** (recall 0.17–0.44). Topology is where people stay in the loop.
- **Twelve drawings from one public design** is enough to see patterns, not enough to rank tools for a different
  drafting style.

**Why the rules matter more than the ranking:** for each of these numbers, it was easy to find a way to make it
look better without making the result more useful: a looser grader, a best-of-three run, quiet failures, tuning to
the key's quirks. The rules exist because the person chasing the metric (here, an AI agent and me) is the one most
likely to fool themselves.

**Lesson:** write down what "done well" means in operational terms, pick proxies with their blind spots named, and
decide how you'll catch yourself gaming them, all before the first result arrives.

**At your plant:** the same rules apply whether you evaluate a vendor, a cloud model, or an open-weight model you
run offline:
- **Weight the measures by your goal.** A tag list cares about instrument recall and tag text; graphics care about
  box precision; analytics care about connectivity (see EVALUATION.md §3).
- **What doesn't flex:** rules before results, controls on the grader, measured noise, failures counted, a held-out
  check, and a person with the final say. Those are governance, and they shouldn't bend to the use case or to a
  deadline.
- **Re-run the same suite for every change:** model, prompt or fine-tune. Keep the scorecards as the change record.
  That's how AI tooling fits inside MOC instead of around it.
- **Sensitive drawings and open-weight models:** an open-weight model can run with no network at all.
  [AT_YOUR_PLANT.md §6](AT_YOUR_PLANT.md) covers what that takes and roughly what it costs.

---

## 9. Ask the offline question with data, not opinions

**What:** Gemma 4 31B, an open-weight model a plant could run with no network connection, went through the same
evaluation as the cloud models.

**How:**
- Same prompt v2, same 12 drawings, same scorer.
- Run through Google's hosted copy of the open weights. That's the cheapest way to see the model's behaviour before
  anyone buys a GPU.

**What happened, reported the way the rules require:**
- **First try:** 5 of 12 calls hit the 30-minute timeout and scored zero, for 0.25 "found + right class". That
  number stays the headline.
- **Retry with a 90-minute timeout, labeled as a retry:** 2 of the 5 finished in about 4 minutes each. The other
  three (drawings 0, 9, 10) timed out again, the same three both times.
- **Where it completed:** high precision (when it names a symbol, it's usually right) and low recall (it misses
  most). About 0.53 "found" F1 across the 9 completed drawings, against about 0.90 for the frontier models.

**Why it matters:**
- **For plants that can't send drawings out,** this is the honest trade-off today: a ~30B open model gives up a
  lot of accuracy out of the box on this task, and it stalls on some dense sheets.
- **That doesn't make it the wrong choice.** It means the decision needs numbers. Annotating your own sheets and
  tuning the model (AT_YOUR_PLANT.md §6) is how the gap usually narrows, and this same suite is how you'd prove it
  narrowed.

**Lesson:** "can we run it offline?" is a measurable question. Measure it with the same rules as everything else,
including the failures, before anyone signs a hardware purchase order.

**At your plant:**
- **Before sizing hardware,** run your 3–5 annotated sheets through candidate open-weight models on rented or
  hosted compute. It costs dollars, not a GPU purchase.
- **Record timeouts and stalls as failures,** not as missing data. A model that hangs on your densest sheets will
  hang in production too.
- **Decide what you'll accept before you look.** Write down the accuracy threshold and the share of sheets that
  must complete before results come in. Otherwise the procurement decision turns into goalpost-moving (§2 of
  EVALUATION.md).

---

## 10. Checkpoint: what works, what doesn't yet, and how round 2 will be judged

**Where things stand:**
- **Works:** extraction by four models, scored honestly; a generator that turns a plant model into SVG graphics,
  Ignition tags and UDTs, a PI AF sheet, and an operator review sheet.
- **Not built yet:** the step that turns *extraction output* into a plant model (equipment hierarchy, instruments
  attached to their equipment, streams from connections, sheets stitched together). Without it the demo stops at
  "here is what the AI found" instead of "here is your digital twin". Round 2 builds it.
- **Biggest weakness measured so far:** connections. Every model misses most of them (recall 0.12–0.55). Process
  topology is what makes a twin more than a parts list.

**The goal, written down before round 2 started ([GOAL.md](GOAL.md)):** produce a digital twin starter kit that
needs as little human correction as possible, and that says where to look.

**The primary score, review load,** is literally that: the corrections a reviewer must make (delete, add, relabel,
fix a link) per 100 items on the drawing. Round-1 baseline: about 49–61 on the held-out drawings for the two best
models.

**How we avoid overtraining to our own scorecard:**
- **Three fixed splits:**
  - drawings we may inspect and tune on;
  - sealed drawings from the same design;
  - sealed drawings from a *different* drafting style, chosen by a fixed random seed and never opened.
- **No drawing-specific rules,** a frozen grader, and every method reported including the ones that don't help.
- **Wins must clear the measured run-to-run noise.** A gain that holds on the same-style holdout but not on the
  different-style one is reported as overfitting, not success.

**Lesson:** decide what "better" means, and how you'll catch yourself gaming it, before you start making things
better.

**At your plant:** the equivalent of the sealed sets is a few areas of the site nobody tunes on. If the tool gets
better on the pilot unit but not on a unit drafted by a different contractor in a different decade, it learned the
pilot, not the job.

---

## 11. Round 2: let code do the geometry, then judge it on drawings nobody tuned on

**What:**
- Three methods built in parallel: tiling, a computer-vision line tracer, and a converter that turns extracted sheets
  into a twin starter kit.
- All judged on review load, the corrections a reviewer must make per 100 drawing items.
- Scored on two sealed sets: same-style drawings and a different drafting style.

**How:**
- **Rules first.** The goal, the score, the splits and the decision rule were committed before any method existed.
  The final method list and the decision rule were committed again before any holdout run (`docs/GOAL.md`).
- **Tiling:** each sheet is cut into four overlapping tiles, so models see small symbols at full size. The tiles are
  stitched back with seam-aware de-duplication. The grid was chosen by running the stitching on the answer key
  itself (a perfect model still loses ~10% of links at 2×2 seams), not by sweeping grids against the score.
- **Line tracing:** an AI model finds the symbols. Code erases them from the image, joins the remaining ink into
  line networks, blocks undetected valves from passing a connection through, and links assets that share a network.
  No AI, about 0.3–30 seconds per sheet (mean 13; `out/costs.md`).
- **The converter** builds the hierarchy, Ignition tags, PI AF rows, per-sheet SVGs at the extracted positions, and a
  review queue with the least certain items first.

**Results (holdout A, the same style; holdout B, a different style; lower is better):**
- **Tiling + tracing (M3) won for every model on holdout A, and held on holdout B.**
- **Codex:** 48.8 → **17.8** on holdout A, and 67.0 → 20.7 on holdout B.
- **Claude:** 61.1 → 32.4 on A, and 76.6 → 16.5 on B.
- **Gemini:** 75.9 → 40.2 on A, and 92.7 → 38.3 on B.
- Full table, including every loss: `GOAL.md` → Results.

**Why it worked:** connections are two-thirds of the work and the models' weakest skill, but lines are geometry.
Giving the geometry to deterministic code and keeping AI for "what is this symbol and what does its tag say" plays
to each side's strength.

**What didn't go to plan, kept on the record:**
- **Tiling made Claude worse on the six development drawings and better on both holdouts.** Small development sets
  mislead; that's why the decision is made on the holdout.
- **On the different-style set,** plain tracing beat tiling + tracing for Codex. The pre-registered rule still picks
  M3, and the difference is reported.
- **The twin's parent assignment got slightly worse** on holdout A (90.9% → 87.0%), even as the connection score
  improved a lot. The tracer links every asset on a shared pipe network, which is what the score counts but not what
  "which equipment is this instrument on" needs. **A better score did not automatically mean a better twin.**
- **Two small engineering catches:**
  - Windows line endings silently changed a prompt file's bytes between branches. The wording was identical, but it
    broke "same prompt for every run". Caught by the hash in each run record, and fixed by pinning the files to LF.
  - The review-queue CSV needed a byte-order mark, or Excel garbles tags like "ESS–HTR–180".

**Lesson:** decide the rules before you look, measure on what you didn't tune on, and keep a second measure that
the first can't fool. The connection score improved by a lot. The twin measure caught where that improvement didn't
translate.

**At your plant:**
- **Split the work by what it is.** Reading symbols and text: AI. Following lines, checking tag syntax,
  cross-referencing the DCS: code. Deciding: people.
- **Judge any tool on areas of the site nobody tuned on,** and keep an outcome measure, such as "did the
  instrument land under the right equipment in the asset framework", next to whatever accuracy number a vendor
  quotes.

---

## 12. Round 3 setup: point people at the problems, fix what the better score broke, spend nothing new

**What:** two goals for round 3, set before any work:
1. **A confidence marker:** every symbol and link gets a risk rating and a green / amber / red tier, so reviewers
   spend their time where the problems are.
2. **A fix for the twin regression from round 2:** instrument parents chosen by following the drawn line, not by
   "shares a pipe network with".

**How (the process steps, in order):**
1. **Pre-register before building.** The success tests went into `GOAL.md` and were committed first:
   - **Errors caught early:** the share of all mistakes that land in the riskiest 20% of items. A random order
     catches 20%, and the model's own confidence ordering is the bar to beat.
   - **Green tier:** its precision, and how much work it removes.
   - **Calibration:** error rates must rise from green to amber to red.
   - **The parent fix wins only if it beats both earlier twins** on the sealed drawings (87.0% and 90.9%).
2. **No new spend.** The constraint was set by the project owner: "we have plenty of data." Every signal comes from
   runs that already exist: three models × whole-sheet and tiled passes × the traced lines. No new model calls of
   any kind in round 3.
3. **Independent signals instead of self-reported confidence.** Two of the three models report 0.9–1.0 confidence
   for nearly everything, which ranks nothing. Independent evidence is more honest. Do two different models agree on
   this symbol? Does the same model agree with itself across two passes? Is the symbol actually sitting on a drawn
   line? Is the tag well-formed or a placeholder?
4. **Parallel builders in isolated copies of the repo.** One builder per goal, each tuning on the six development
   drawings only. Results get verified, then each method is scored once on the sealed sets.
5. **Housekeeping done safely.** The round-2 workspaces linked to the shared dataset folder. Removing a workspace
   carelessly can follow such a link and delete the real data, so the links were removed first, the data was
   confirmed intact, and only then were the workspaces deleted.

**Why:**
- **Review time is the real cost.** Ranking items so people check the riskiest first turns "review everything" into
  "review what matters". That's the difference between a tool that saves a plant time and one that just moves the
  work.
- **The parent fix closes the loop on round 2.** A better primary score must not be allowed to quietly make the
  twin worse.

**Stated limitation (written before results):** a risk rating can only rank what the system *found*. It can't point
at a symbol the system missed entirely, so a person still scans each sheet for gaps, and the review queue says so.

**Lesson:** decide how you'll know the marker helps (errors caught per hour of review) before you build it, or
you'll end up admiring a colour scheme.

**At your plant:**
- **Set the review budget first.** For example: "a reviewer checks the riskiest 20% closely and batch-accepts the
  green items".
- **Then measure how many real errors that budget catches,** on units nobody tuned on.
- **Sample the green items from time to time** (spot-check a few percent), so the green tier keeps earning its
  trust.

---

## 13. Round 3 results: a review queue that points people at the problems, and a fix that only half-generalized

**What:** two round-3 results, scored once each on drawings nobody tuned on, with no new model spend.

**1. The confidence marker. Mostly a success, with one important failure.**
- **What it is:** every symbol and connection gets a risk score and a green / amber / red tier with a plain-language
  reason ("the other models didn't find this symbol here; no tag was read").
- **How the risk is judged:** by independent checks, not by asking the model how sure it is:
  - Do the other models agree?
  - Does the same model agree with itself across whole-sheet and tiled passes?
  - Is the symbol on a drawn line?
  - Is the tag well-formed?
  
  A small formula, fit only on the six development drawings, weighs the checks. Each check can only raise risk.
- **Result:**
  - Across 24 holdout comparisons (4 methods × 3 models × 2 holdouts), the riskiest 20% of items held two to four
    times as many errors as ranking by the model's own confidence, in 23 of them.
  - Green items were 94–100% right and made up roughly half to three-quarters of everything.
  - Error rates climb from green to amber to red everywhere.
- **The failure:** the best model with the best method (Codex, tiling + tracing) on the same-style holdout. There
  the rating caught 40% of errors in the riskiest 20%, against 43% for Codex's own confidence. The tiers were still
  calibrated, but the ordering added nothing.
- **Why:** the strongest signal is "the other models didn't find it", and the best model is often right where the
  others miss. Agreement is evidence, not proof, and it punishes the model that's right alone.

**2. The twin's parent fix. Fixed for this drafting style, not in general.**
- **What changed:** each instrument's parent is now chosen by following the drawn line.
- **Same-style holdout:** 92.2% right, against 87.0% (round 2) and 90.9% (round 1).
- **Different-style holdout:** 67.6%, against 70.8% for the round-2 rule.
- **What the review queue does with it:** where the two rules agree, accept; where they disagree, flag for review.

**Why it matters:** review time is the cost. The twin's queue now reads: 377 red items to look at closely, 676
amber to check quickly, and 1,833 green to batch-accept with spot checks, out of 2,886 items across 12 sheets. Not
"review all 2,886".

**Lessons:**
- Honest uncertainty comes from cross-checks, not from a model's own score. Self-confidence ended up with zero
  weight.
- Pre-registering "must beat the model's own confidence on both holdouts" is what exposed the one failure that
  mattered. An average across all combinations would have hidden it.
- A fix that wins where you tuned it and slips on a new drawing style is a partial fix. Say so.

**At your plant:**
- **Before anyone batch-accepts the "green" pile,** measure its error rate on units nobody tuned on, and keep
  spot-checking it after go-live.
- **Ask what the tool's confidence is based on.** If the answer is "the model says it's sure", that's not enough.
- **Expect agreement-based checks to under-trust your best source.** A drawing reading that no other source
  confirms might be the one that's right. Route it to a person rather than rejecting it.

## 14. The Ignition build: the twin in a real gateway, judged by the gateway

**What:** the twin now runs inside an Ignition 8.3 gateway:
- the Tennessee Eastman plant, live from the open simulation data, with alarms;
- the extracted 12-sheet twin, honestly "not connected";
- one Perspective screen per drawing.

A verifier checks the running gateway against nine checks drawn from how Ignition itself judges data. Before its
results counted, it had to catch five faults planted on purpose. It caught all five, and all nine checks pass.
Details and receipts: [IGNITION_BUILD.md](IGNITION_BUILD.md).

**How:**
- **Everything is scripted against the gateway's REST API:** backup first, then an OPC connection to a small replay
  server, a separate `Twin` tag provider, one tag import, and the screens.
- **The verifier never reads our own files alone.** It exports the configuration back from the gateway, and it reads
  live values the way any outside system would: through the gateway's encrypted OPC UA server.
- **Quality as truth:**
  - The 36 tags fed by the replay must read Good.
  - The one instrument with no data in the replay (agitator speed) and the 359 placeholders must not.
  - A "Good" on a tag with no source is the worst failure a twin can have: it looks fine and is invented.
- **Alarms proven, not assumed:** the verifier switches the replay to fault 6 (loss of A feed) and watches the
  reactor pressure alarm go active, using setpoints from published sources only.

**Why:** the extraction work produced files. A digital twin is the running system. "The import said success" and
"the gateway holds what we meant" turned out to be different statements, several times.

**What went wrong, and what each mistake taught:**
- **Twice, "accepted" was not "working".**
  - The gateway saved a connection with a missing settings block (HTTP 200), which then failed at runtime.
  - An alarm expression read fine but was evaluated only once at startup: it would never have turned true in a
    fault.

  Neither shows up until you check the running state.
- **I blamed the gateway, wrongly.** I briefly recorded "changing a tag's type breaks it" as an Ignition bug. A clean
  reproduction in a throwaway provider showed the real cause was my expression. The claim came out.
- **The verifier changed what it verifies.** Its "can this client write at all?" test wrote to a review field, and
  Ignition stores that write as configuration, so the next fidelity check failed. Fixed by writing a probe tag
  outside the twin.
- **A refused write proves nothing on its own.** The read-only check uses a write-capable account on purpose, and
  first proves that account *can* write somewhere. Otherwise "write refused" might only mean "this user has no
  rights".

**Lessons:**
- Verify the running system, not the deployment receipt.
- Every check needs a case it must fail on. The planted faults are what make the nine passes mean something.
- When the evidence contradicts your story, rewrite the story, including the parts you already wrote down.

**At your plant:**
- **Run the same checks on your own twin or SCADA build.**
  - Export the configuration back and diff it against what was approved (that's Management of Change evidence).
  - Make sure no tag without a live source can read Good.
  - Prove each critical alarm on a replayed event before go-live.
- **Keep the twin's tags in their own provider,** read-only at three layers (device, connection, tag). Give the build
  account its own security level, not an administrator role.
- **Approve OPC UA client certificates by fingerprint.** Don't accept them all.
- **Take a gateway backup before every import, and keep the config in version control.** Then "what changed and
  when" has an answer.
- **Treat engineering ranges and alarm setpoints as engineering data with a source.** Where none exists (spans
  here), label the value as assumed and send it to operations to confirm.

## 15. Counting the cost, and a loose-ends sweep

**What:**
- Every recorded cost and time figure is now in one place, [COSTS.md](COSTS.md), generated from the run records
  rather than typed in.
- A sweep fixed the gaps a newcomer or reviewer would hit: a missing data download, stale plan rows, two
  contradictions, undocumented settings, no test command, no CI.

**How:**
- `scripts/cost_report.py` reads every run record and writes `out/costs.md`. Its total ties to the Gemini spend
  ledger to the cent: $16.57 of the $25 cap.
- Two independent read-only reviews ran in parallel, one on costs and one on loose ends. Their findings were checked
  against the files before anything was changed.

**What the cost picture says:**
- **Machine cost is small.** Model calls cost cents per sheet, roughly $200–$600 per thousand sheets at API prices.
  Compute is about a day of unattended runtime per thousand sheets.
- **People are the cost.** The declared method still needs about 16–40 corrections per 100 items, and the minutes per
  correction were never measured here. COSTS.md shows how to size it, with the assumption labeled.
- **Two vendors' costs aren't known.** Claude and GPT ran on flat subscriptions. Claude's tool reports an
  API-equivalent figure ($36.37); GPT's reports nothing, so no figure is claimed for it.

**What was wrong:**
- **Token counts were never saved,** so past runs can't be re-priced at new rates. Every run records them from now on.
- **Two numbers in the docs didn't match the data:**
  - the line tracer's "2–18 seconds per sheet" (actually 0.3–30);
  - an unsourced "for weeks" in the README's first paragraph.

  Both are fixed.
- **The tutorial's Ignition step needed simulation files no script downloaded.** It worked only on the machine that
  built it. There is now a fetch script with pinned checksums.

**Lesson:** "every number traces to a file" has to include the cost numbers. A cost claim nobody can recompute is a
guess with a dollar sign.

**At your plant:**
- **Before a pilot, write down what you'll measure:** minutes per sheet by hand (the baseline) and minutes per
  correction for reviewers. Those two numbers decide the business case. Machine cost almost never does.
- **Ask any vendor for per-sheet cost and per-sheet time from their own logs,** split into machine and reviewer time.
  If they can't produce it, they haven't measured it.

## 16. Can someone else run it? Rebuilding the gateway by hand

**What:** a test of whether the Ignition result can be shared, not just shown:
1. I backed up the gateway, then deleted the twin's tag provider, its OPC connection and its project.
2. I rebuilt the twin through the web UI only (create a provider, create a connection, import a project), plus one
   tag import, using only files committed in the repo.
3. The verifier ran its full set against that gateway. All nine checks passed, including the fault-replay alarm.

The steps are now [IGNITION_QUICKSTART.md](IGNITION_QUICKSTART.md).

**Why:** "it works on my gateway with my scripts" isn't the same as "you can load it". The scripted build might
have been doing something the files alone don't carry.

**What it showed:**
- **The UI wizard fills in every connection setting the REST API made me copy by hand** (journal 14, lesson 1).
  Someone using the UI never meets that trap.
- **The 8.3 web UI imports projects but not tags.** Tags go in through the Designer or the REST API. The quickstart
  says which path was tested (REST) and which is standard but untested here (Designer).
- **Names are part of the interface.** The provider must be `Twin` and the connection `TE-Sim`, because the screens
  and alarm expressions refer to them. The quickstart says so up front.

**Lesson:** a deliverable is only shareable if someone else's path through it has been walked once, start to finish,
from the published files.

**At your plant:** when an integrator hands over a twin or SCADA project, rebuild it from the handover package on a
clean test gateway before go-live, and run your acceptance checks there. Anything that only works on their machine
shows up then, not during commissioning.

## 17. Closing the loop: operations corrections and real data points flow back into the twin

**What:** the two missing halves of "a twin operations can use":
- the review comes back;
- the instruments get real data addresses.

`scripts/apply_review.py` reads a filled-in review sheet. `scripts/map_points.py` reads a plant I/O list. Both
update the asset model, both write a change record, and regenerating carries the result into Ignition, PI AF and the
screens. Details: [REVIEW_LOOP.md](REVIEW_LOOP.md).

**How:**
- **The review sheet is the interface operations already use:** a spreadsheet with confirm / correct / reject, show
  on screen, and alarm priority.
- **Every row is checked before anything changes.** Unknown items, unknown fields and corrections with no value are
  refused and listed, so a bad sheet can't half-apply.
- **The sheet round-trips.** It comes back pre-filled with earlier decisions, and re-applying it changes nothing.
- **Mapping matches tags after normalizing spelling, and never guesses.** It reports four worklists: mapped; on the
  drawing but not in the I/O list; in the I/O list but not on the drawing (is the drawing out of date?); and
  ambiguous.
- **The demo uses a synthetic I/O list, labeled as such.** It maps 24 instruments on sheet 0 and finds 2 points not
  on the drawing. It also hits one real ambiguity: the drawing shows `FT 1401` on two symbols.
- **In Ignition, 24 tags read live and 335 stay honestly Bad.** The verifier checks both, and that each tag's
  `ReviewStatus` matches the model's decision.

**Why:** the alarm rule is the design decision worth noting. A reviewer may set the priority of an alarm that has a
published setpoint. Removing an alarm, or adding one without a setpoint, changes what alarms the plant has. Those
requests are recorded for a change review and not applied. A spreadsheet should never be able to silently delete a
safety alarm.

**What went wrong:**
- **My first "keep corrections" rule broke the round trip.** Re-applying a regenerated sheet was refused for asking
  for a correction value it didn't need. The test caught it.
- **The first format check measured the wrong thing:** it counted every line after an insertion as changed. Also
  caught by the test, which was then fixed to compare a real diff.

**Lesson:** the review loop is a data pipeline with a person in it. It needs the same guards as any import: refuse
bad rows, apply the same input once, and leave a record.

**At your plant:**
- **Treat the review sheet and the I/O list as controlled inputs,** with a named reviewer and a dated record.
- **Read "in the I/O list but not on the drawing" as a drawing-update worklist.** In a 40-year archive it will not
  be empty.
- **Keep alarm creation and removal on the change-review path,** whatever tool proposes them.

## 18. Old scans: where the method breaks, and which part breaks

**What:** round 4. A pre-registered test of the declared method on holdout-A drawings degraded to three scan
qualities: photocopy, old scan, bad scan. The degradation keeps geometry fixed, so the original answer keys still
apply. The levels were set by eye before any model saw them. GPT and Claude only; Gemini was left out to keep spend
flat.

**Result:**
- **Photocopy quality: no consistent change.**
- **Old scan: review load about 3×** (GPT 17.8 → 51.5).
- **Bad scan: about 4×** (72.6).
- **The models' symbol reading degraded gently; the code line tracer collapsed.** At the worst level, connections
  fell to about 0.2, below the models' own untraced links.
- **The models aren't the main cause.** Feeding the same degraded-image symbols to the tracer on the clean image
  brings connections back to 0.53–0.63.

**Why it matters:** this is the "40-year archive" question with a number on it. The part of the pipeline that looked
strongest on clean drawings, deterministic code, is the most brittle on old paper. A lesson about tuning, not about
AI.

**What I didn't do:** tune anything. An image clean-up step, or a rule to skip tracing on poor sheets, is a new
method and would need its own sealed test.

**Lesson:** test the conditions you'll actually deploy into before claiming a number. Decompose the failure so the
fix goes to the right part.

**At your plant:**
- **Sort the archive by scan quality first.** Clean CAD exports and good scans can use the full pipeline.
- **For poor scans, budget 3–4× the review time,** or add an image clean-up step and prove it on your own sheets.
- **Rescanning the worst sheets may be cheaper than reviewing them.**

## 19. Making it shareable: one command, a 30-second demo, and two bugs only the verifier saw

**What:**
- `scripts/demo.py` goes from a clone to a live, verified twin in one command (given a gateway's settings).
- A 30-second animation for the README (`docs/demo.gif`), made from the repo's own screens: the drawing and the
  extraction, then the mapped sheet in Ignition, then the Tennessee Eastman plant through a fault until the alarm
  turns red.
- A before/after image of a real drawing with every extracted symbol coloured by review risk.

**Two bugs the verifier found that nothing else would have:**
- **Rebuilds weren't reproducible.** The project zip stored the time each file was written, so every rebuild looked
  like a configuration change. V9 (the gateway config matches a commit) failed on a build where nothing had changed.
  Now the timestamps are fixed and builds are byte-identical.
- **A fresh build once lost data silently.** One build in about eight imported "1,093 of 1,093" into a provider still
  starting up, and the tag overrides (ranges, units, alarms) never landed. V1 found 113 differences. The build now
  reads its import back with V1's own comparison, re-imports once if needed, and fails loudly otherwise.

**Lesson:** a check that runs every time beats a fix you can't reproduce. The rare failure is the one that reaches
production.

**At your plant:** make the acceptance checks part of every deployment, not just the first one, and keep their
receipts. Intermittent "it imported fine" failures only show up when something checks every time.

## 20. A one-click demo, built and tested without being able to run Docker

**What:** an optional way to run the twin with no setup. Install Docker Desktop, double-click `start-demo.bat`, and
the plant screen opens in the browser. Three containers:
- the official Ignition image, restoring a prepared demo backup on first start;
- two small containers running the data servers, so nobody needs Python.

`fault-demo.bat` trips the alarm, and `stop-demo.bat` stops it. The guide is
[docker/README.md](../docker/README.md), written for someone who has never used a terminal.

**How, under a constraint:** Docker Desktop installed fine on the build machine, but its Linux layer needed a
restart. The machine was unattended and 600 miles from its owner, so a restart was not an option. Instead:
- **The demo backup came from a second, throwaway Ignition** run natively on the same machine, built with
  `build_gateway.py --demo-backup`. Its temporary API key and permission level were deleted before the backup was
  downloaded through the web UI. `prepare_demo_backup.py` then set a neutral gateway name, because the download
  carried the machine's hostname. It refuses if any API key, extra user or personal string remains.
- **The whole demo is tested on GitHub's own machines,** which have Docker. A workflow starts it from nothing, opens
  the screens in a real browser, and checks three things:
  - 36 live values on the plant screen;
  - 24 live and 12 "not connected" on sheet 0;
  - the reactor pressure alarm turning red in the fault replay.

  **The record, and the bug it found.** Each change now starts three independent fresh copies, and the results are
  posted publicly.
  - The first 9 starts had 2 failures, both at the alarm step.
  - Once the check reported what the screen showed, the cause was clear. Switching to the fault recreated the replay
    container, so Ignition had to rebuild its OPC UA session: usually in about 25 seconds, once not within 2
    minutes.
  - **The fix is how a real plant behaves:** the data source changes mode without dropping the connection. The
    replay now switches live from a control file.
  - Every start since has passed, with the alarm at 26 seconds each time.
- **The Windows launchers were tested locally,** with a stand-in `docker` command and the throwaway gateway answering
  the "is Ignition up?" check.

**What testing caught:**
- **A demo that worked 7 times in 9.** "Usually works" isn't one click for a newcomer, and running it three times
  per change is what made the 2 failures visible.
- **The window title "P&ID" broke the start script for everyone.** In a batch file, `&` means "and then run".
- **A build setting was read before it was loaded,** so the first throwaway build still pointed at `localhost`.
- **I was about to document that restarting resets Ignition's 2-hour trial.** Earlier the same day, a restart had
  shown the opposite. The guide gives the real steps instead.

**Lesson:** "easy for anyone" is a claim like any other. It needs the same from-nothing test as the code: a check
that starts where a newcomer starts and looks at what they would see.

**At your plant:** for a pilot, give operations and reviewers the twin in a form they can start themselves on a test
machine, and keep it from a throwaway, credential-free build. The fastest way to collect operator feedback is to
remove the setup between them and the screen.

## 21. Screens an operator could use, and which model made which call

**What:** the first screens were correct and nearly useless: the drawing, with a number on every instrument, all
with the same weight. The new ones are a first pass at an operator display, generated from the twin in the ISA-101
style ([OPERATOR_SCREENS.md](OPERATOR_SCREENS.md)):
- a plant overview with one tile per unit, each with its key values, an analog indicator and a trend;
- a screen per unit, the alarm list, and the schematic;
- the 12 extracted drawings, now shown as the **original** drawings, greyed, with live values on top.

Grey means normal, amber means a value has left its normal band, and red is only for a real alarm.

**How, and the one inference that carries it:** an alarm says when it's too late; a band says "this isn't normal".
TE has no published operating envelopes, so `normal_bands.py` learns them from the normal run, the way the scorer
was built: rules first, then a test the rules never saw.
- **Fit:** mean ± K standard deviations on the first half of the normal run.
- **K chosen on the second half,** which the fit never saw. K = 6 is the smallest width with under 0.5% false flags
  on every tag. At K = 3, some value would be amber in 27% of normal samples, which operators learn to ignore.
- **Then the fault run, which chose nothing.** The A feed leaves its band in the same sample the fault starts; the
  pressure alarm comes **294 plant-minutes later**. Nothing was flagged in the 8 hours before the fault.
- **The gateway does the logic, not the screen:** each tag got `OutOfNormal` and `State` members, so anything reading
  the tags agrees with the colours. V8 now checks it: nothing flagged in normal running, the A feed flagged before
  the alarm, the pressure red at the alarm.

**Which model did what** ([MODELS.md](MODELS.md)), written down now, though it should have been from the start. Several models were compared only where it mattered most: reading the drawings. Everything else was
built by one model, Claude, through Claude Code. The judgement calls on these screens (which values represent each
unit, the display spans, the layout) are Claude's alone. They're labelled that way on every screen and are the first
thing an operator should change.

**What went wrong:**
- **The gateway ran out of memory, and it looked like a caching bug.** Images inside the views (5.2 MB) exhausted the
  trial gateway's 1 GB heap while it built each browser's copy of the project. Open screens kept their old views, and
  I first blamed the browser. The gateway log said `OutOfMemoryError`. Screen-resolution drawings and small thumbnails
  brought it to 2.4 MB.
- **Trends showed upsets that never happened.** Gaps in history (a stopped replay) drew as drops to zero. They now
  use raw points and skip bad quality.
- **A PowerShell edit corrupted the source,** turning "·" into "Â·" on screen: Windows PowerShell 5 read UTF-8 as the
  old Windows code page and wrote it back with a byte-order mark. Files are now edited with tools that keep UTF-8.

**Three overclaims, corrected:**
- **"Played the operations reviewer"** (corrected earlier the same day, commit 475c122). Nobody with TE process
  knowledge has reviewed the model, so the README now says the review is not done.
- **"The 3,000 kPa shutdown alarm never activates."** The data never goes above 3,000.0, so it seemed safe. On the new
  screens it went active at exactly 3,000.0: Ignition's above-setpoint alarm fired at equality. The claim had been
  inferred, never watched; the verifier stops looking seconds after the first alarm.
- **Authorship at that historical snapshot:** Claude wrote the initial code, while Codex supplied extraction
  results. Later revisions include OpenAI/Codex code and documentation work under Steve Vitale’s guidance.

**Lesson:** a claim about what a system does is a prediction until something has watched it happen. The screens
watched things the checks never looked at: a limit at equality, a gateway out of memory, a trend inventing upsets.
Walking the screens through a fault, as an operator would, belongs in the test plan next to the automated checks.

**At your plant:** generate the first screens, then spend the saved time with operators. Have them pick the key
values, and learn normal bands from your own historian, per operating mode. Count false flags on held-out data before
anyone sees the colour; a band that's amber every shift is worse than none.

## 22. Put the process on the overview, then make the unit pages earn the click

**Date:** 2026-10-10. **Status:** implemented and checked locally; native Ignition and browser validation remain
unrun. No deployment or successful remote push is claimed.

**What:** the three-unit mimic has become the six-unit **Overview**, with one consistent navigation bar and
more detailed unit graphics. A follow-on request for the maximum available instrumentation expanded the work:
all 52 recorded channels now have display/mapping entries, alongside the explicitly unconnected agitator.
The overview stays selective; the unit pages carry the full readings, trends, state and source context.

**The local sequence, checked against the available commit history:**
1. **October 8, `20aa7cd`:** the baseline carried the operator screens, normal bands and trend historian in the
   Docker demo backup. That is the starting point for the later local mimic work.
2. **October 10, `3b97ecb`:** the first read-only mimic covered the reactor, condenser and separator. Its alignment
   revision put readings into equipment-grouped rows, with each numeric value and engineering unit in one binding.
   Local tests and approximate SVG renders supported that checkpoint; neither established Ignition or browser
   runtime behavior.
3. **October 10, this revision:** the process picture moved into the normal application path, then the detail
   inventory expanded to every available replay channel. The current implementation and verification notes are in
   [PROCESS_MIMIC.md](PROCESS_MIMIC.md) and [INSTRUMENT_COVERAGE.md](INSTRUMENT_COVERAGE.md).

This checkout has shallow history. The first two items are inspectable commit checkpoints; the third records the
current local work rather than inventing additional published milestones.

**How:**
- **Show the whole process first.** The compact 1600 × 930 Overview contains feed U-100, reactor R-101,
  condenser E-101, separator V-101, compressor K-101 and stripper C-101, with all 13 seed-model stream directions.
  Its 21 headline readings are deliberate display choices pending operator review. The branches, recycle and
  external boundaries remain visible without putting every instrument on the first screen.
- **Give each destination one name.** Every shared header uses Overview, Feed, Reactor, Condenser, Separator,
  Compressor, Stripper, Alarms and Drawings in the same order. There is no extra Mimic tab; `/mimic` remains a
  compatibility alias to Overview. Equipment and neighboring-unit links support drilldown, while the full schematic
  remains a reference drawing. The tab order does not imply that this branched process is one serial train.
- **Make detail mean more process context.** Unit pages combine equipment-specific graphics, measured level where
  available, recorded-output gauges, and all tag rows with the existing state and history configuration. Boundary
  cards and connection stubs identify each modeled stream's source and destination and its currently mapped scalar
  readings. A boundary with no mapped instrument says so. Utility instruments are identified separately because
  the source model supplies no utility endpoints; the drawing does not invent piping to fill that gap.
- **Count channels before claiming complete coverage.** The seed has 37 model records, including three analyzer
  groups. The replay has 41 XMEAS channels and 11 XMV channels: 52 unique recorded columns. Sixteen analyzer
  components were previously undisplayed. They now have source-indexed sibling paths, completing the 19 analyzer
  components without changing the original scalar paths. The resulting 53 detail rows represent 52 mapped channels
  and SC-212 explicitly unconnected. New suffixes such as AI-123-B are project-assigned identifiers, not newly
  discovered physical instrument tags.
- **Keep timing with the measurement.** Feed and purge analyzers show their 6-minute sample periods and 6-minute
  dead times; product analyzers show 15 minutes for each. A replay row every 3 minutes does not make those readings
  instantaneous. Source index, component and review metadata travel with the added channels.
- **Preserve the existing meaning.** All 36 legacy normal bands are unchanged, including K = 6. Added components
  use that existing calibration rather than retuning it to flatter the expanded display. Existing alarm limits,
  read-only behavior and parent analyzer review exclusions remain in force. Normal bands are display aids, not
  site-approved operating limits.
- **Keep uncertainty visible.** Bad-quality, missing, nonnumeric and nonfinite readings remain unknown. Vessel
  fills become hatched and output gauges hide their fill. Zero remains zero, and an off-scale percentage keeps
  its number even when the graphic is clamped. Value and State quality are checked independently. History retains
  raw points and ignores bad quality, avoiding the false drops to zero found in entry 21.

**What needed correction along the way:**
- **A plausible feed label was assigned to the wrong unit in an early selection.** FI-104 sounds like it belongs
  with the other feeds, but the seed assigns it to stripper C-101 on S4. The final selection follows that ownership
  and keeps U-100's three actual feed readings together.
- **The expanded overview became too large.** The layout was reduced to a compact overview with 21 essential
  readings; the additional cooling, utility, analyzer and final-element detail belongs on the unit pages. Complete
  instrumentation coverage does not require every value to compete for attention on the first screen.
- **The first aggregate test run could not complete.** This environment lacked `asyncua` and `cv2`. Temporary PyPI
  installs of asyncua 2.1.0 and opencv-python-headless 5.0.0.93 supplied those dependencies, then the full runner
  passed. The repository's pinned requirements were not changed, and this was not an exact-lockfile reproduction.

**What the drawing still cannot prove:** it is a **replay-only, read-only** display. Static stream lines follow the
seed model; topology and equipment geometry remain **unverified pending operations review**. Recorded XMV outputs
are not measured valve-position feedback. XMV12 is absent from the replay, so SC-212 remains not connected and the
agitator stays static. Level percentages are measurements on a display scale, not calculated liquid volumes.

TI-122 remains a useful test of that discipline. The published source calls it **separator cooling-water outlet
temperature**; the seed retains its E-101 ownership while operations review is open (entry 5). The disagreement is
kept visible. A condenser graphic cannot turn it into a verified condenser process temperature.

**Evidence and limits:** this revision has its own local results, separate from the earlier prototype's receipts:
- **15 focused process-display tests passed** in the historical local run.
- **All seven aggregate test scripts passed, with no skips**, in that local run. These include source-channel coverage and compatibility checks.
- The gateway builder completed in **write-only** mode, and the proposed project export was checked for
  deterministic generation. The normal and fault replay fixtures passed their recorded SHA-256 checks.
- Normal, fault and bad-quality static renders were generated for the Overview and reactor detail. They are
  approximate offline SVG/PNG renders, not browser or gateway screenshots.

**Still unrun:** Ignition import, native Perspective/Jython execution, live OPC bindings, native historian
behavior, browser interaction/layout and operator acceptance. The earlier Chromium launch was blocked by the
environment's socket restrictions. Local configuration checks do not replace any of these stages, and previous
gateway receipts cover previous builds only. The preceding GitHub push attempt returned HTTP 403; no push retry,
deployment or public release was performed for this revision.

**Why:** the useful progression is from a complete data model, to readable measurements, to a process picture
that helps someone decide where to look next. The instrumentation request exposed an important distinction:
covering every model record had still left recorded analyzer components unused. A channel inventory caught that
without forcing all 52 values onto the overview or inventing measurements that do not exist.

**Lesson:** check completeness against the source channels, then choose visual detail for the decision each page
supports. Better-looking equipment can make a viewer assume more has been verified; improve the evidence labels
alongside the graphics. Local generation, automated checks, runtime observation and operations acceptance remain
separate milestones.

**At your plant:** agree on the overview-to-unit navigation with operators, then reconcile every available source
channel against the display inventory, including individual analyzer components and their timing. Keep unmapped
signals and uncertain ownership visible. Walk the whole path on an authorized development gateway with normal,
fault and bad-quality data, and have a process reviewer confirm the connections independently of the screen's
appearance.

**Preserving the handoff:** a historical shallow-checkout restore initially failed when it traversed
history before the baseline; retaining the known boundary allowed an exact restore. The lesson is to test
a restore, not just archive integrity. Those private handoff files are not included here.

## 23. Put measurements where operators look, then separate the plant-specific layout

**What:** operator feedback was that each unit page still spread readings away from the process. A complete table
was not enough to show what was measured and roughly where. All six unit pages now begin with a compact annotated
process diagram. Plain-language names and value plus engineering unit are primary; project tags are smaller.
Dashed leaders associate vessel pressure, temperature and level with approximate regions, stream measurements with
their mapped streams, and composition groups with their sample stream. The full inventory and history remain below.

The reactor was rendered and reviewed before applying the same visual grammar to the other units. Feed A/D/E stay
in order; reactor feed flow and A–F composition stay on S6; separator liquid readings remain on bottom S10; stripper
S10 enters above S4, with S5 overhead and S11 product below. All 52 available source channels remain accessible;
SC-212 has no replay source and stays explicitly unknown. Recorded valve outputs never become measured feedback.

**Evidence and limits:** this correction inspected pixels from the repository's generated overview and from
[Singhal & Seborg (2006), Figure 1, p.603](https://sites.me.ucsb.edu/~ceweb/faculty/seborg/pdfs/Singhal_JPC.pdf).
The latter is a published control-strategy schematic, not the original 1993 P&ID or proof of physical instrument taps.
It supports coarse regions and branch order. Exact tap and along-stream valve/instrument order remain approximate.
No source utilities, pumps or bypasses were added to the seed topology. Utilities without modeled endpoints appear
as nearby context, without invented pipes. TI-122 retains the source name “Separator Cooling Water Outlet Temp”
and disputed E-101 ownership. The published purge branch appears on the separator side of the compressor; the seed
still assigns S9 to K-101. That disagreement is visible rather than silently resolved by moving a measurement.

**What changed in the method:** this project should support different plant types, not accumulate TE-specific
screen logic. New labels, rectangles, routes, region anchors, uncertainty and source attribution live in additive
`data/te_display_layout.json`; the process facts remain in the original model. Shared unit rendering accepts a
layout parameter. The small display contract checks referenced units, streams and measurements, finite geometry,
association evidence and conflicts. Unknown direction draws no arrow; TE explicitly opts into its existing seed
from/to adapter, still unverified. Unknown equipment types receive a neutral symbol; unmapped values remain UNKNOWN.
A synthetic water-utility fixture exercises the same renderer with different IDs, topology and units. This checks
a presentation seam only: it does not establish broad industrial coverage or make the TE replay/export adapters generic.

**Lesson:** completeness, spatial readability and generalization are separate tests. Keep association evidence
separate from drawing coordinates, preserve unresolved data, and validate a second process through the same renderer
before calling a configuration seam reusable. Plant labels and layout are configuration; process topology, real data
mapping and operations acceptance remain site-specific work.

**Verification:** detailed local render receipts are not included in this publication. All six units have normal, fault and
bad-quality SVG/PNG renders. These are approximate offline renders, not browser screenshots or Perspective runtime
validation. No gateway import, live OPC operation, public action, spending or GitHub retry is part of this correction.

Local verification for this correction: **19 focused process-display tests passed**, **26 display-contract checks
passed**, and **all eight aggregate test scripts passed with no skips** using the previously documented temporary
dependencies. Repeated project generation produced the same ZIP hash. Independent pixel review covered all six
normal diagrams and representative bad-quality views; the final pass moved the stripper S10 caption clear of a
leader and gave unmapped-stream notes clearance from arrows and measurement cards. An overlap regression test protects the stripper overhead note. Native Ignition/Jython, live bindings, browser layout
and operations acceptance remain unrun. Private handoff artifacts are omitted from this publication; no remote push was claimed at that stage.

---

## 24. Try a separately labeled collection before claiming a general method

**What:** the next test should show someone adapting this code to their own drawings, and find what the first
workflow missed. We used an already labeled public collection, **PID2Graph Synthetic**, with the same existing
scorer and `twin-1` converter/exporters. It is a separate synthetic collection from OPEN100 and the Dataset-P&ID
holdout already used in round 2, but shares the PID2Graph distribution and ontology. It is not real-plant evidence.
No second model comparison was run: the selected first-round Codex `gpt-6.1-sol` model and original whole-sheet
prompt were retained.

**What the data actually contained:** archive inspection found 250 complete JPEG/GraphML pairs, correcting the
500-complete-drawings statement in entry 6. Development sheets 0 and 1 took 1,575,041 source bytes, or 12,201,709
range bytes including the archive index and block overhead. Reserved 2 and 3 were not downloaded or opened.
The JPEG format exposed an existing PNG-only assumption; the adapter now normalizes without resizing and records
source and converted hashes. The license is CC BY-SA 4.0, with attribution to the dataset authors and Steven
Baltakatei Sandoval's symbols. Source drawings and answer keys remain gitignored, with a bounded fetch manifest.

**First isolate the plumbing:** ground-truth labels were converted into the existing prediction format. This
oracle-label path passed all 43 scored assets and 65 collapsed links into a valid twin and draft SVG, Ignition,
PI and review files. Zero adapter-consistency corrections is expected; it is not an extraction accuracy claim.
Neither sampled key contains instrumentation labels. Tag text and flow direction are absent from the keys, so
all 43 oracle tags and all 65 directions remain unknown.

**Then run the selected model:** the subscribed Codex CLI could not initialize because its runtime filesystem was
read-only. A documented writable-runtime retry failed before inference as well. Those failure receipts were kept.
Two fresh native workers used the same selected model, exact prompt and images, with no ground-truth context.
This changed transport and wrapper instructions; reasoning settings are unverified/inherited. It is not a claim
of bit-for-bit reproduction of the old CLI execution.

| Development sheet | Located symbols | Source-class F1 | Connection TP / predicted / key | Review corrections / key items |
|---|---:|---:|---:|---:|
| 0 | 20 / 20 | 0.450 | 19 / 19 / 38 | 30 / 58 |
| 1 | 22 / 23 | 0.400 | 25 / 26 / 27 | 17 / 50 |
| Combined | 42 / 43 | 0.424 micro | 44 / 45 / 65 | 47 / 108 (43.52 per 100) |

**The useful failure:** 24 of those corrections are source-class disagreements, not independently proven physical
misinterpretations. Twenty are source `general` versus more specific model classes. The original prompt's equipment
definitions and the source's broad General category are not interchangeable. We kept both classes and the original
score, rather than learning a post-hoc remap from the answer key. The other corrections are one missed symbol,
21 missed links and one false link.

A second concrete gap is line semantics: the source has 221 solid and 29 non-solid edges, while the current
prediction/scoring contract collapses those into untyped adjacency. Every original edge style is now preserved
in a local sidecar; it is not silently interpreted as process versus signal flow. The generated model's structure
can be valid while its equipment roles, ownership, tags and directions remain unreviewed.

**What changed:** a small dataset config, bounded fetch/normalization adapter, source/hash checks, nine controls,
reproducible reports and `docs/ADAPT_LABELED_DATASET.md`. Structural validation runs before export. A separate
operational-readiness gate uses the existing review workflow and refuses `--require-reviewed` while ontology,
line semantics, operations decisions and site-specific live-data requirements remain unresolved. Default exports
are explicitly review drafts. No confidence calibration from OPEN100 is applied to this new domain.

**Lesson:** generalization begins with agreeing what a label means. Preserve the source vocabulary, model
interpretation and uncertain semantics independently. Freeze a domain-reviewed mapping and test it prospectively
on untouched data; do not rewrite the score after seeing the answer. These two development sheets identify gaps,
not broad performance. Nine adapter tests and the frozen scorer's controls pass; the review-required gate fails
closed without changing existing outputs. No gateway/PI import, deployment, public upload or API spending occurred.

---

### Documentation maintenance — 2026-10-10

The README animation caption now separates OPEN100 extraction with synthetic point mapping from the hand-built
TE process model/HMI with recorded fault replay. A third track identifies the two-development-sheet PID2Graph
Synthetic adaptation and its unresolved review gates. No new performance result or user decision is attributed.
The process-display verification summary now identifies the spatial and adaptation stages and distinguishes the
historical eight-script pass from the current rerun: 19 focused tests, 26 display-contract checks, nine separate
adapter tests and all eight aggregate scripts passed without skips using the unchanged repository dependency pins.
The initial rerun lacked cv2/asyncua because the earlier temporary dependency directory was absent; that failure
was preserved before restoring dependencies into a new temporary directory. Detailed command/output receipts are local and are not included in this publication. Runtime validation,
operations acceptance, and the prior GitHub HTTP 403 blocker remain unchanged. This is local documentation
maintenance only: no code behavior change, new extraction, generated image package, public action or push retry.

---

## 25. Flag a real review ambiguity without turning it into a confirmation

**Review outcome — 2026-10-10:** retain both FT 1401 symbols, flag the ambiguity for drawing-owner
clarification and block automatic signal assignment. This does not settle physical identity or count.

**Evidence:** the publisher's native 2604 × 1744 raster for PID 140-1-A contains two adjacent circles labeled
FT / 1401. The retained extraction has S0-IN002/s7 and S0-IN003/s8; the demo I/O CSV contains only one synthetic
FT-1401 row. Detailed local crop evidence is not included here. Raw extraction `runs/r2-tiles-trace/codex/0.json` is absent;
no extraction replay or vector-original verification is claimed.

**Applied effect:** a dry-run-checked, two-row OPS_notes-only review records the scoped outcome. Both symbols remain, both verification and review statuses remain `unverified`, and neither
has a data_point. No correction, merge, rejection, screen/alarm decision or MOC request was applied. The existing
review format has no clarification status enum, so no new engineering status was invented. An explicit leading
`NEEDS CLARIFICATION:` note is now echoed in the queue's `why_check_this` column when regenerated; original risk
scores, tiers and order remain intact. Only the queue was regenerated, with original newline style retained.

**Aftereffect and unknowns:** the current mapper dry run still reports FT-1401 row 26 as ambiguous between both
IDs; existing mapping output is byte-identical. Physical-device count/identity, tag correctness, parent/line
connectivity, line/signal semantics and real I/O address remain unresolved. Drawing-owner identity/contact,
clarification answer and resolution date are unknown. No external clarification was sent. Subsequent assignment
requires evidence and a separately authorized judgment identifying the target; this note is not such authority.

**Verification:** exact before/after records and full-file hashes, dry-run/application logs and a bounded CSV
are saved with the decision. Regression controls cover notes-only isolation, unverified/no-address retention,
visible queue flagging and idempotent round-trip. No gateway work, live mapping, public action, spending or push
retry occurred; the prior HTTP 403 blocker is unchanged. Local restoration was checked separately; those handoff artifacts are omitted here.
All eight aggregate test scripts passed with no skips using unchanged dependencies in
an isolated temporary environment; detailed local logs are not included. This does not establish runtime or operator acceptance.

---

## 26. Correct MS 14010 as text without approving the device interpretation

**Review outcome — 2026-10-10:** a field-scoped review corrected the MS 4010 identifier to MS 14010.
It did not approve function, classification or signal mapping.

**Applied effect:** S0-IN019/s39 now reads MS 14010. The existing review tool gained an optional
`identifier_text` scope with regression controls. Its matching derived loop changes from 4010 to 14010;
the exact mirrored description and hierarchy display cache change with it. The scoped decision is recorded
per field and in history, while whole-record review and verification remain `unverified`. Source extraction
provenance keeps MS 4010. No function, class, parent, connection, I/O or confidence interpretation is approved
or recomputed. The FT 1401 pair, its clarification flags and unmapped state are unchanged.

**Verification and limits:** normal CSV review dry run and application, exact before/after paths and hashes,
focused regression tests and all eight aggregate scripts passed without skips. Local read-only SVG, queue,
PI AF and Ignition JSON exports were regenerated, retaining unverified status and placeholder addresses.
No gateway import, production deployment, mapping application, spending, external contact or public push
occurred. The existing HTTP 403 limitation is unchanged. A historical local restore check established recoverability, not publication or runtime/operator acceptance.

---

## 27. Review the MS 14010 callout as a valve without inventing a signal

**Review outcome — 2026-10-10:** a field-scoped review associated the existing MS 14010 callout
with an existing valve, without approving a measured variable or signal.

**Applied effect:** the existing S0-IN019/s39 callout is associated by a field-scoped review with the
existing S0-VL013/s38 valve. Both source symbols remain distinct; no valve is created or merged.
The unsupported `moisture` variable becomes `unknown`, its method records the missing source legend,
and its current role becomes `valve callout`. The reusable `valve_association` scope accepts only
`parent=<existing parent valve>;variable=unknown` and refuses reassignment, mapped records, semantic
expansion, or screen/alarm decisions. `reviewed_valve_association` is the reviewed callout reference;
`parent`, `parent_method` and connectivity remain the original inferences. Raw extraction class,
provenance, geometry, confidence, risk, and the existing valve record are unchanged. No MS expansion,
valve subtype, actuator/control function, or signal type is inferred.

**Boundaries:** MS 14010, loop 14010, earlier identifier review and FT 1401 clarification are preserved.
Whole-record verification and operations review remain unverified. The source instrumentation collection
and class are retained as drawing-symbol provenance, not a claim that the callout is a measured process
variable. Local Ignition output uses a metadata-only Callout_Valve type without PV/OPC parameters;
PI output uses a String metadata attribute with no PI Point reference. The queue calls it a valve callout.
Point mapping refuses callouts even when an I/O row pins an asset ID; assigning a signal needs separate
review. No current mapping output is changed, and no gateway import or deployment is performed.

**Verification:** scoped isolation, idempotence/queue round-trip, refusal controls, metadata-only exports
and tag/asset-ID mapping guards pass focused regression. The first aggregate attempt retained two missing
import failures (cv2/asyncua); unchanged dependency pins were then restored into a temporary directory.
The final aggregate receipt records all eight scripts passing without skips. This establishes local model
and export checks, not runtime/operator acceptance. Local restoration was checked separately. No external contact, spending,
public push, or retry of the existing HTTP 403 failure occurred.

---

## 28. Regenerate current gateway artifacts and prepare isolated runtime acceptance

**2026-10-10:** regenerated `PIDTwin.zip` and `twin_provider.json` locally from the reviewed
MS 14010 valve-callout model at `3205ce8ea203d5e6e36fa8174cd58d85d40bf07e`, using only the
supported `--write-only` path after auditing its return before gateway/account/access operations.
The export contains all 23 views and 1,082 tag/history/expression bindings, all resolving offline;
53 TE instances retain 52 recorded channels plus unavailable SC-212. The 910 OPEN100 instances
include a metadata-only MS 14010 callout, 24 existing synthetic mappings, and 334 placeholder PVs.
Both FT 1401 records remain unmapped and flagged for clarification in the source.

**Local verifier corrections:** V2 previously reconciled only the 37 unexpanded seed items and
misclassified 16 added analyzer channels as orphans. It now derives expectations from the channel
expansion and independently rejects invented callout PVs or OPC assignments. V3 derives unit
coverage from source rather than held instances, excludes only source-reviewed valve callouts
from PV completeness, and requires the explicit NOT CONNECTED plus spatial UNKNOWN indicators
for source-unavailable SC-212. Ordinary unmapped instruments still require their quality-bearing
bindings. An outdated display-code comment was corrected without changing generated output.

**Checks:** ten new offline regressions include deterministic write-only generation under blocked
Gateway/network entry points, resource/route/tag checks, field-review lineage and negative semantic/
quality controls. All nine aggregate scripts pass without skips using the unchanged pinned temporary
dependencies in an isolated temporary environment. JSON/ZIP shape checks are not an Ignition-native schema
validation. Synthetic quality objects and generated views are not runtime evidence.

**Handoff and blocker:** [current-source handoff](IGNITION_ACCEPTANCE.md) describes the browser
acceptance checklist. Detailed local receipts are not included in this publication.
Compose still restores the untouched historical `docker/twin-demo.gwbk`; that backup and old
screenshots/receipts do not validate these artifacts. Java 21/Chromium are available, but no container
engine or running gateway exists here; desktop is offline and no saved coding environment is
available. No gateway start/import, license acceptance, credential/account change, external contact,
spending, public push or retry of the existing HTTP 403 failure occurred. Runtime and operator
acceptance remain unestablished. Local restoration was checked separately.


---

## 29. Give readers a bounded replication path, with or without the author

**2026-10-11:** added `docs/REPLICATE_AT_YOUR_PLANT.md` as the plant-reader entrypoint, linked from
the README. The path starts with public-data file generation in a disposable checkout, distinguishes
the manual TE seed from OPEN100 extraction and the two-sheet Synthetic development exercise, then
lists required site inputs, adapter work, review/mapping precautions, target-system requirements,
acceptance evidence and stop conditions. Optional assistance is a possible bounded scope, not an
offer of availability, pricing or production approval.

**Inspection findings carried into the docs:** OPC mapping replaces prior mappings across non-rejected
instruments; `--sheets` only scopes missing-I/O reporting. Dry-run output is a report, not a full diff.
PI export retains placeholder point references, independent of OPC mappings. Both replay servers
bind all interfaces with anonymous lab endpoints. Generic file exports are drafts without a blanket
operational gate; full-suite current-artifact checks need cached TE replay data. New-site input,
ontology, signal semantics, type/range verification and local inference are not turnkey adapters.
Directly misleading onboarding statements were corrected in README, IGNITION_QUICKSTART, REVIEW_LOOP
and TWIN_OUTPUTS; historical evidence and earlier journal entries remain intact.

**Validation:** checked the 16 relative links in the new guide, all 10 fenced Python command script
paths and five source/example inputs. Seven argparse invocations were accepted using isolated AST
extraction of the scripts' parser definitions, without importing or executing their entry points.
The first validation harness missed the review parser's `datetime` dependency; adding that standard
library binding fixed the harness, and the rerun passed. `git diff --check` passed. This is command
and file inspection, not execution of the documented workflow or a fresh test-suite pass. This documentation/parser check itself ran no generator,
model call, dependency installation, gateway/PI import, replay server, security change or public action.
Existing generated outputs in the working checkout were not changed. The separately authorized
isolated reproduction below has a distinct scope.

**Independent file-only replication check:** a separate reviewer executed the guide's seed generation,
copied OPEN100 model generation, blank-review dry run and synthetic point-mapping dry run against
a fresh archive of `4566e87` in a temporary directory. Python 3.12.14 ran with `-I -S`, a stripped
environment and an audit hook denying socket/urllib requests. All four commands returned zero.
Seed generation wrote seven SVGs and its exports; copied-model generation wrote twelve sheet SVGs
and its exports. The blank review applied/refused zero decisions. The mapping preview reported
24 mapped, 12 sheet-0 model records without a proposed mapping, two points absent from the drawing and
one ambiguity. Working source models and the copied model after dry runs were hash-verified unchanged.
Detailed local logs are not included. This validates those
four file-only paths on that Python version, not extraction, full-suite tests, model services,
native import, runtime behavior or engineering acceptance.

**Evidence boundary:** inspected baseline `4566e87` is the offline-verified local gateway handoff.
Current native Ignition runtime/browser acceptance and PI import remain not run; operations acceptance
is also outstanding. Historical Docker backup/receipts do not validate the current artifacts. The
previous public push was blocked by HTTP 403, and no retry occurred. The guide is local documentation
until separately published; it does not establish production readiness or new extraction performance.

---

## 30. Harden the replication path before wider use

**2026-10-11:** local follow-on hardening from documentation baseline `c774b63` addresses the
three concrete replication hazards recorded in §29. Its earlier observations remain historical;
the contracts below supersede the replace-all mapper, post-write validation and implicit test prerequisites.
No engineering review decisions, signal identities, source model or committed gateway artifacts changed.

**Mapping:** partial updates now preserve omitted mappings. Destructive replacement requires
`--replace-all` and is restricted by `--sheets` when supplied; unresolved, ambiguous or blocked rows
refuse replacement. Unknown/rejected explicit asset IDs do not fall back to tags. Duplicate target
rows, missing address values and invalid/out-of-scope targets reject the complete transaction.
A sheet filter does not disambiguate globally duplicated tags. Dry-run writes nothing and includes
complete before/after mapping snapshots and added/changed/removed entries; `--json` exposes the same
report for machine inspection. Partial mode preserves prior mappings for unresolved rows and may still apply resolved rows while
reporting unmatched or ambiguous rows, so exit zero is not full row reconciliation. Address checks
establish nonempty fields, not valid OPC syntax, connectivity or signal identity. Units, types, scaling and real-world
signal correctness remain outside the mapper's validation.

**Export gate:** seed and extracted models are structurally checked and every export rendered in
memory before output directories, files or stale SVG cleanup are touched. Invalid structure or
unrenderable required fields raises an actionable error; the CLI returns nonzero without changing
existing exports. Unknown semantics are preserved. This is not an atomic multi-file filesystem
transaction: a later disk/permission error can still leave a partially written bundle, and structural
success does not establish native-schema compatibility or operational approval.

**Tests and CI:** `--source-only` explicitly runs nine stdlib/committed-fixture scripts and names its
four exclusions; it never claims a full-suite pass. Default/`--full` runs all thirteen registered
scripts and requires dependencies plus checksum-verified cached TE data. Missing prerequisites exit
2 before any test script; test failures exit 1. `--check-prerequisites` does not run tests. The runner
never installs, downloads or silently skips. The existing CI job now stages the two public TE fixtures
through the checksum-verifying fetcher before `--full`; triggers, actions and permissions are unchanged.
That workflow edit was inspected locally, not executed on hosted CI.

**Independent integration evidence (Python 3.12.14):**

- `python -S scripts/run_tests.py --source-only`: 9/9 scripts passed. Separately, a source-only temporary
  checkout without ignored TE data passed the same nine scripts; full preflight there correctly
  reported the missing cache instead of passing. Source-only is deliberately narrower evidence.
- `python scripts/run_tests.py --full --check-prerequisites`: initially exited 2 for missing `cv2` and
  `asyncua`; cached `d00_te.dat` and `d06_te.dat` hashes passed. No full-suite scripts ran in that attempt.
- A new disposable virtual environment was then created under the integration receipt directory.
  `python -m pip install --index-url https://pypi.org/simple -r requirements.txt` installed the repository's
  unchanged pins (`numpy==2.4.6`, `pillow==12.2.0`, `opencv-python-headless==5.0.0.93`, `asyncua==2.1.0`,
  `cryptography==49.0.0`) and resolver dependencies. Exact installed versions and the initial blocker
  were retained. This was explicit test-only setup, not a test runner side effect or global installation.
- Using that environment in a temporary copy of the final working source and existing verified TE
  cache, `python scripts/run_tests.py --full --check-prerequisites` exited 0, followed by
  `python scripts/run_tests.py --full`: **13/13 scripts passed, zero failures or skips**. All six changed
  implementation/regression scripts were byte-compared to the shared checkout afterward. The full
  run occurred on the copy so any normal-band regeneration did not touch shared outputs.
- A separate comparison generated seed and reviewed OPEN100 exports with both baseline `c774b63`
  and the candidate in temporary destinations: **all 25 files were byte-identical**. Existing review
  controls, new invalid-model no-write cases and current-artifact controls passed. FT 1401 remains two
  unverified, unmapped records with clarification notes; MS 14010 remains an unverified metadata-only
  valve callout, without PV/OPC parameters or PI Point references.
- `python -S scripts/map_points.py out/twin/r2-tiles-trace/codex/plant_model.json
  data/io_lists/open100_sheet0_demo.csv --sheets 0 --dry-run --json` produced a valid partial plan:
  24 mapped rows, two unmatched rows, one FT 1401 ambiguity and **zero mapping changes**. Neither FT
  record nor the valve callout gained a mapping. SHA-256 checks confirm the reviewed source model,
  current gateway ZIP/provider and existing untracked process-mimic patch were unchanged.
- `git diff --check` and checks of all 100 relative links in the four affected user-facing guides passed.
  Replication, review-loop, twin-output and README instructions now describe
  the new contracts, explicit setup and remaining gates. Test logs, package versions, baseline export
  hashes and protected-file hashes are retained in the separate integration receipt for the handoff.

**Limits:** no model calls, extraction rerun, gateway start/import, PI import, live process connection,
security change, public push or production action occurred. The only networked setup in this pass was
installation from official PyPI into the disposable test environment. Native runtime/browser, PI and
operations acceptance remain not run. The prior public HTTP 403 blocker was not retried. These results
establish local offline hardening and repeatability, not publication, new extraction performance or
plant readiness.

---

## 31. Add a bounded local drawing-intake path

**2026-10-11:** local follow-on from `55f5734` adds `scripts/import_site_drawing.py` for
one locally supplied PNG plus an **existing extraction JSON**, described by a
`site-drawing-intake-1` manifest. It does not read a PDF, obtain extraction, call a model,
trace lines, apply the trained confidence model, score a drawing or connect process data.
The detailed manifest and command recipe is in [Replicate at your plant](REPLICATE_AT_YOUR_PLANT.md#bounded-local-intake-one-png--an-existing-extraction).

**Contract:** input filenames need not match or be numeric. The manifest records drawing ID,
revision, original page and supplied producer claims; optional register fields remain supplied
claims. The importer accepts only the existing six symbol classes and supported normalized boxes,
rejects malformed/duplicate-key/non-finite JSON, duplicate or unsafe IDs, bad geometry/confidence,
unknown endpoints, duplicate undirected links and self-links. It refuses unsupported text that
could become a spreadsheet formula or invalid XML. Source fields it does not interpret remain
in the preserved original JSON; they are not silently promoted into engineering semantics.
PNG checks cover bounded dimensions/container structure/CRCs, **not compressed pixel decoding**,
readability or revision authority. This is a narrow input boundary, not a hostile-file security certification.

**Publication and evidence:** `--check-only` writes nothing and tests inputs only, not conversion or
rendering. A normal run requires a new output directory with an existing parent, stages beside it,
validates/renders before publishing, and refuses existing destinations. Concurrent writers to the
same destination are unsupported. The bundle retains original manifest/PNG/extraction bytes,
SHA-256 hashes and implementation hashes, a normalized run record, and bundle-relative model/source
references. It contains an unverified model, review CSV, SVG and draft Ignition/PI exports. Original
manifests may expose private paths; keep sources private and review the entire bundle before sharing.
All items remain unverified and unmapped. Supplied confidence and the inherited 0.75 highlighting
rule are explicitly uncalibrated; blocked operational-readiness metadata is descriptive, not an
interlock in other tools. Site ontology, tag/role/parent heuristics, signal identity, native import
and operational acceptance still require separate qualified review.

**Determinism fix discovered during review:** importing the converter no longer imports OpenCV/numpy
unless the along-line rule is requested. Three linked/owner distance ties now use stable symbol keys.
Independent review also found a forked instrument chain whose parent changed with Python's hash seed;
linked-parent adjacency traversal now has stable ordering. This preserves its first-found-branch
heuristic and existing method labels. Repeatable selection does not resolve engineering ambiguity
or establish a better parent assignment.

**Final independent evidence (Python 3.12.14):**

- `python -S scripts/test_site_drawing_intake.py`: **18/18 tests passed**, including original-source
  hashes, malformed input/no-publish controls, escaping/rejection, image structure, check-only,
  repeated-bundle byte equality, and distance-tie/forked-chain fixtures across multiple hash seeds.
- In an isolated copy using the existing disposable test environment and cached TE data:
  `python -S scripts/run_tests.py --source-only`: **10/10 scripts passed**;
  full prerequisite check passed, then `python scripts/run_tests.py --full`: **14/14 passed**,
  zero skips/failures. Source-only remains deliberately narrower. Tested implementation files were
  byte-compared with the shared checkout after the run.
- Additional independent checks rejected nested duplicate keys, malformed/multiple JSON documents,
  duplicate manifest keys and symlink/dangling-symlink destinations without publishing output.
  Accepted quotes/angle brackets/Unicode rendered parseable SVG, with no formula-prefixed CSV cells.
  A simulated final rename failure removed staging and published no destination.
- Converter comparison against `55f5734`: all nine full models were identical under hash seed 1
  for retained OPEN100 provenance reconstruction and both available Synthetic development sources
  (oracle/native), each under linked, nearest and along-line rules. Six linked/nearest comparisons
  were also identical under seed 2. Historical raw OPEN100 extraction runs were absent, so its
  reconstruction used retained symbols/links from the committed model rather than claiming a raw-run
  replay. No baseline parent changes were observed in these cases; the synthetic tie fixtures do
  intentionally replace previously hash-dependent choices with stable, still-unverified choices.
- SHA-256 checks confirm the reviewed OPEN100 model, current gateway ZIP/provider and pre-existing
  untracked process-mimic patch are unchanged. `git diff --check` and relative guide links passed.
  Receipts are retained separately from the repository for the private replication handoff.

**Limits:** no dependency installation, download, model/extraction run, gateway start/import,
security change, public push or production action occurred. Native Ignition runtime/browser,
PI import and operations acceptance remain **not run**. This is local intake/review plumbing and
regression evidence, not plant-readiness evidence or a new extraction/generalization result.

---

## 32. Connect the remaining local replication handoffs

**2026-10-11:** local follow-on from `1e0618b3` adds four bounded pieces, developed in
parallel and reviewed together. These close local workflow gaps; they do not establish
plant readiness or replace native target-system and human acceptance.

- **Single-PNG extraction handoff:** `site_extraction_workflow.py` prepares an arbitrary
  local PNG and drawing/revision/page identity, freezes the existing
  `synthetic-adaptation-whole-sheet-v1` recipe, and collects a matching preserved record
  into the local intake. The pinned original prompt, `gpt-6.1-sol`, whole-sheet input
  and linked-parent conversion are deliberately distinct from the M3 tiled/traced
  benchmark method. Prepare/check/collect make no model or network call. The separate
  `execute` path reuses the existing strict Codex adapter, requires independently
  authorized transmission, preserves failed/incomplete attempts, and never retries
  automatically. Native replay retains its transport/reasoning deviation; fixtures
  remain synthetic. No new extraction was executed. The job and importer now record
  the PI helper hash alongside their generator/converter provenance.
- **PI-only mapping:** `map_pi_points.py` accepts exact instrument IDs and supplied
  archive/point/type/UOM/reviewer evidence. It never derives PI identities from OPC
  mappings. Dry-run exposes complete before/after snapshots and changes; partial
  updates preserve other PI mappings, while explicit replacement removes omitted
  mappings. Invalid or blocked rows reject the plan without changing the model.
  Generation preserves legacy CSVs, adds a mapping reconciliation file, and adds an
  explicitly `UNVALIDATED` candidate CSV correcting only the known type-column header.
  The remaining native PI Builder column/row contract, type/UOM compatibility,
  actual import and read-back remain unverified. Reviewer fields are attestations,
  not authenticated approval.
- **Ignition acceptance preflight:** an offline read-only tool verifies the exact 51
  manifest-listed build inputs, three artifacts and bound browser contract. Candidate
  identity includes the manifest hash, so changed source provenance rejects old
  observations even when export bytes are unchanged. Required input paths cannot be
  omitted or substituted. Historical check/handoff drift is reported separately.
  Future sample validation distinguishes 52 recorded TE and 24 mapped OPEN100 Good
  paths from SC-212 Bad and 334 non-Good placeholders; unknown values and absent source
  timestamps remain unknown. The callout has no PV path. Local sample validation
  cannot authenticate capture provenance or promote any native stage to accepted.
- **Future review-effort protocol:** `review_effort.py` supplies a blank registration,
  strict local record validation and descriptive assignment/pair summaries. It keeps
  preparation/review/total labor, independent residual-critical-error audit evidence,
  failures, abstentions and missing observations distinct. It rejects altered protocol
  hashes and mixed synthetic/human labels. The protocol addresses eligible information,
  reviewer independence, counterbalancing and same-task learning contamination. It is
  an administration kit: no human trial, time-saving, quality-equivalence, ROI or
  operator-usability result is claimed.

The [replication guide](REPLICATE_AT_YOUR_PLANT.md), [extraction handoff](SITE_EXTRACTION_WORKFLOW.md),
[PI mapping guide](PI_MAPPING.md) and [review-effort protocol](REVIEW_EFFORT_PROTOCOL.md)
describe the commands, boundaries and remaining gates.

**Independent integration evidence (Python 3.12.14):**

- In a fresh source-only copy containing tracked and proposed files but no ignored TE
  or Synthetic raw cache, `python -S scripts/run_tests.py --source-only` passed
  **14/14 scripts**. A separate copy using the existing disposable environment and
  SHA-256-verified TE cache passed prerequisite checks and the full cached-data suite:
  **18/18 scripts**, zero failures or skips. No dependency installation or download
  occurred. All 68 Python source/test files were byte-compared to the final tested copy.
- Focused standard-library controls passed: **15 workflow**, **14 PI mapping**,
  **25 acceptance preflight**, **14 review-effort**, and **18 intake** tests. These
  include explicit fake-process execution failures/retries, malformed input/no-write,
  source/prompt drift, duplicate JSON keys, stale/missing candidate evidence,
  unavailable-quality handling and synthetic-versus-human labeling. Fake subprocess
  output in test logs is not evidence of a real model call.
- All **25 existing seed/reviewed OPEN100 export files** were byte-identical to the
  `1e0618b3` generator outputs. Only the two new extracted-model PI staging/reconciliation
  files were added in temporary destinations. The actual reviewed MS 14010 callout
  rejects PI assignment and retains a metadata-only `Callout_Valve` UDT with no PV,
  OPC parameters or PI reference. Both FT 1401 records remain separate, unverified,
  unmapped clarification items.
- Existing public Synthetic development sheet 0 and its retained native response
  replayed through prepare/collect without a model call. The resulting one-sheet
  bundle retained source/implementation hashes and native recipe deviation, with
  6 equipment, 1 instrument, 9 line items, 4 off-page connectors and 19 extracted
  links; all remain unverified/unmapped. This checks local plumbing only, not new
  extraction accuracy or generalization.
- Exact current artifact preflight passed **51 required inputs and 3 artifacts**.
  The older runner hash in the historical handoff correctly reports **DRIFT**;
  historical receipts were not rewritten. Upstream generation is outside that
  manifest's direct input scope. The unchanged artifacts need no regeneration for
  this code-only handoff. `--require-native` exits **3**, keeping every native stage
  **NOT RUN**. With TE cache absent, preflight exits **2** rather than downloading
  data or treating missing evidence as acceptance.
- Protected reviewed-model/current provider/project/pre-existing patch hashes are
  unchanged. Relative guide links and `git diff --check` passed. Final logs and hash
  receipts are retained with the separate private replication handoff.

**Limits:** no new model/extraction execution, dependency installation, download,
gateway start/import, PI import/read-back, process connection, security change,
participant contact, human trial, public push or production action occurred.
Native Ignition/browser acceptance, licensed PI acceptance and actual human-effort
or operator-usability outcomes remain **NOT RUN**. The previous public HTTP 403
blocker was not retried. Local tests and authenticated-looking supplied strings
cannot waive engineering, data-sharing, change-control or operational approvals.

## 33. Preserve engineering text at the export and review boundaries

The release-candidate checks exposed three bounded defects in supplied-model
exports and the operations review loop. This pass fixes those defects without
changing the engineering interpretation or using a live service:

- **SVG serialization:** use XML attribute quoting for model-derived string
  attributes, including the complete provenance-based group identifier. Seed tag
  and asset labels are escaped as text too. Quotes, ampersands and angle brackets
  remain the supplied engineering text after XML parsing; they cannot become new
  attributes or elements through string interpolation.
- **Review CSV text:** spreadsheet-active strings and control-containing cells are
  prefixed with an apostrophe at serialization. Leading apostrophes are encoded
  too, preserving distinct source spellings. This covers both review sheets and
  all their cells, including notes, identifiers and descriptive fields. The model
  is not rewritten. Unchanged encoded notes are recognized against the model on
  reapplication, preserving review history and literal text. Identifier spellings
  must identify exactly one record; ambiguous raw/encoded spellings are refused.
  Edited notes are taken as written, as explained in [the review guide](REVIEW_LOOP.md).
- **Mapped callouts:** a scoped valve-association correction refuses any existing
  OPC `data_point` or PI `pi_point` before model or history mutation. It neither
  silently discards the mapping nor creates a metadata-only callout that invalidates
  the retained PI mapping. Separate authorized mapping review is still required.

**Local regression evidence (Python 3.12.14):**

- Nine new standard-library boundary tests passed. XML parser assertions check
  preserved values and attribute sets; no supplied script was executed in a browser.
  CSV tests cover each column in both review formats, notes/history round trips,
  literal apostrophes and ambiguous identifiers. Mapping tests preserve the full
  model on refusal and verify that an existing PI mapping remains exportable.
- Existing review-loop controls passed **48/48**, generation validation **8/8**,
  and PI mapping **14/14**. The new boundary script is registered in both aggregate
  modes. An isolated tracked-source copy passed **15/15 source-only scripts**.
- The initial full-suite prerequisite check reported missing `cv2` and `asyncua`
  and ran no test scripts. A separately authorized temporary virtual environment
  then installed the exact repository requirements and resolver dependencies from
  official PyPI. With existing TE cache files verified against their recorded
  SHA-256 values, the isolated full cached-data suite passed **19/19 scripts**.
  No global packages or cached source data were changed or downloaded.
- Regenerating the existing seed and reviewed OPEN100 models into temporary
  directories produced **27/27 byte-identical export files** compared with the
  `b13d8e5` generator. The intentional CSV encoding changes affect supplied text
  requiring protection; these baseline files required none. Committed models,
  generated outputs and the pre-existing process-mimic patch were untouched.

**Limits:** these are offline serialization and regression checks, not a broader
security audit or native acceptance. No model API call, gateway operation, PI
import/read-back, process connection, credential change, publication or production
operation occurred. Native Ignition/browser, PI and human-effort acceptance remain
**NOT RUN**.

## 34. Prospective frozen Synthetic 2/3 transfer check

On 2026-10-11, a separately named trial consumed the two previously unopened
PID2Graph Synthetic sheets 2 and 3. Original freeze `75d6306` preceded image
acquisition. Effective freeze `00540b1` amended only the reasoning declaration
before inference: omit the override and record unverified/inherited reasoning.
Original protocol, config and acquisition evidence were preserved. The explicitly
selected gpt-6.1-sol, exact original prompt, whole-sheet method and scorer stayed
unchanged. There was no new model comparison, tuning, answer repair or retry.

Both first native outputs were sealed before parent-authorized unblinding at
17:48:50 UTC. The unchanged scorer ran once at 17:50:36 UTC. Result: **73 corrections
/ 158 key items = 46.20 per 100**, comprising 2 missed symbols, 17 source-class
relabels, 3 false links, 51 missed links and no false symbols. The model located
47/49 symbols; rough source-class F1 was 0.625. Connection precision/recall/F1 were
0.951/0.532/0.682 (58 correct / 61 predicted / 109 key links). Both attempts
succeeded; no malformed symbols were counted.

These are published-label disagreements, not independently verified engineering
errors. Fourteen relabels involve the source's heterogeneous `general` class.
The key contains no instrument or off-page positive examples. Original edge
styles remain in local annotation context, but the frozen adjacency score drops
solid/non-solid distinctions. Neither semantics nor operational interpretation
was corrected from these held-out results. Both sheets are now consumed;
prospective validation of a changed method needs new data.

Observed durations of 103/111 seconds are approximate parent-observed worker
intervals, not inference-only latency. Selection/timestamps are parent-recorded
evidence, not independently authenticated provider telemetry. Subscribed native
execution used no separately invoked paid API; actual token/compute cost was
unmetered and remains unknown, not free or $0. Backend revision, actual reasoning
level and worker tool traces
were not independently verified. Isolation was procedural. Public-model training
contamination cannot be excluded. These two synthetic sheets do not establish
real-plant accuracy, actual human-effort savings or operational readiness.

Local regression checks passed **15/15 source-only scripts**, **19/19 full
cached-data scripts**, and **18/18 separately invoked synthetic harness tests**.
No new dependency installation or TE download was needed. Development artifacts,
protected method bytes and the unrelated process-mimic patch were untouched.
No gateway/PI operation, operational export, public push, paid API request or
production action occurred. The previous publication blocker was not retried.

See [results and public-evidence limits](PID2GRAPH_RESERVED23_RESULTS.md) and
[summary metrics](../out/pid2graph_reserved23_summary.json). The sealed local evidence and trial-specific
protocol/configuration/harness are not included; this public checkout cannot reproduce the exact trial.

---

## 35. Test the packaged demo after the source checks pass

**What:** on 2026-10-12, fixed a missing Docker dependency exposed by clean-image
browser testing, then verified the repaired demo in three independent starts.

**How:** the published source passed all 20 offline test scripts, but its
[first Docker run](https://github.com/steve-vitale/pid-to-digital-twin/actions/runs/38194280260)
failed all three browser checks. The replay server called the new `te_channels`
helper, which was present in the checkout but absent from the image's `COPY` list.
The container logs reported `ModuleNotFoundError`.

Added a regression that reconstructs the Dockerfile's copied files in a temporary
directory, imports the real server modules in an isolated Python process, and
exercises the real 52-channel replay mapping. It failed before the fix and passed
after adding the missing `COPY`; SC-212 remains unavailable. No dependency stubs
or source-checkout fallback hide a missing packaged module.

At repair commit `36038390cfacb7e19cc1f714ef2b8adeb651a56c`, the
[offline CI run](https://github.com/steve-vitale/pid-to-digital-twin/actions/runs/38195512089)
passed **20/20 scripts**, and the
[Docker/browser run](https://github.com/steve-vitale/pid-to-digital-twin/actions/runs/38195512100)
passed **all three independent starts**. Each browser check reported 29 overview
numbers with zero bad-quality overlays; the fault-6 alarm check passed after
26 seconds.

**Why:** source-level tests could import a neighboring file that the shipped image
never contained. The repair keeps packaging and functional dependency checks
together without changing process semantics or weakening the browser check.

**Lesson:** exercise the files actually shipped, and retain a failing regression
before applying the fix. Passing offline tests and passing a clean-start demo
answer different questions.

**At your plant:** repeat acceptance against the exact deployment artifact and
record its identity. This Docker result covers the **historical packaged demo**
restored from `docker/twin-demo.gwbk`. Native Ignition/browser acceptance of the
**newly generated 23-view project** remains outstanding, as does licensed PI
import and read-back. The [current-source handoff](IGNITION_ACCEPTANCE.md)
keeps those gates separate; a working demo does not establish plant readiness.

## 36. Bring the reviewed work onto one branch and make the next step explicit

**2026-10-12:** the reviewed public branch (`e565c74`) and a later Docker-guide edit made on another checkout were
brought together on one working branch, without rewriting any published commit. No private conversation or
gateway backup was added.

**What a Windows run of the tests showed at that point:** a disposable copy of the reviewed source, using the
SHA-256-verified TE cache and the pinned package versions, regenerated 23 views and 23 routes. Source-only checks
passed 12/15 and the full suite 16/20. The failures were a filename that Windows doesn't allow, two tests that need
symlink rights Windows hadn't granted, and the packaging test's isolated Python process correctly refusing a
user-site package. None of the checks was weakened to make them pass; entry 38 fixes the portability problems.
This result didn't replace the Linux CI run (20/20) or the historical Docker starts (3/3).

**Direction kept:** the engineering judgement is the point of the project: instrument positions and connection
boundaries, realistic process placement, uncertainty linked to its source, and an overview whose unit screens add
useful detail. It stays an open-source method that readers can evaluate and adapt themselves. No further model
comparison is planned for the second dataset. A 3D walkthrough was considered and deferred until native acceptance
of the 2D screens was finished. Recorded TE replay and synthetic OPEN100 values establish neither responsive
physics nor plant readiness.

## 37. Take a cold-reader documentation review seriously

**2026-10-13:** a cold-reader review, done from GitHub alone with no access to the working machine, read the
replication docs at `e565c74` and asked whether a competent engineer could follow them from a fresh checkout. Two findings mattered most. The
quickstart warned about versions, but its import steps could still pair the committed historical project ZIP
with the current tag provider. And the full-suite instructions skipped the step that regenerates the project ZIP.
Neither was a claim that a check passed without evidence; both were places where a careful reader could still go
wrong.

Both are fixed in release v1.2.0: the quickstart now makes you pick one set of files before importing, and the
README's full-suite block lists every step in order. The other findings (a real-candidate recipe beside the offline
preflight, an own-dataset handoff contract, and a domain warning beside the batch advice in the twin outputs guide)
are still open.

**Lesson:** a warning at the top of a page doesn't help if the numbered steps below it contradict it. Readers follow
the steps.

## 38. Import the current project into a real gateway, and watch what the offline checks could not

**2026-10-12/13:** the 23-view project finally ran in Ignition. Steve authorized Docker and an isolated test
target, so the whole current source went into a **disposable Ignition 8.3.10 container** (trial, fresh volume,
port bound to localhost only, removed afterwards), fed by the replay image built from `docker/sim.Dockerfile`.
No real plant, controls or site gateway was involved. The first import found that every live reading on the
new screens was broken. Nothing offline had caught it.

**What the gateway showed first.** The import itself was clean: 1,118 tags with zero read-back differences, and
the 23 views exported back identical. V1 to V7 passed, and the gateway's own OPC UA server read 52 TE values and 24
mapped OPEN100 points Good. Yet the overview showed `null` in every reading, each under Perspective's red error
marker, and the vessels said ERROR ([screenshot](screenshots/native-before-fix-overview-transform-parse-error.png)).
Opening the marker gave the cause: *Error_Configuration: Parse Error in script transform*. Perspective stores a
script transform as the body of `def transform(self, value, quality, timestamp):` and compiles it as written. The
generators stored the body unindented. All **580 of 580** script transforms failed to parse.

The offline preview and tests had run the same code, but they indented it themselves before executing it. So
they tested a version of the code that Ignition never sees. The historical October 8 screens did not have this
problem because they used Ignition's built-in format transforms, not scripts. The scripts arrived with the
October 10 process mimic, which had never been imported.

**The fixes, each with a test that fails on the old code:**
- One choke point (`build_hmi.tag_binding`) now stores every script transform as an indented body. The offline
  harness compiles stored code exactly as Perspective does, so an unindented body now fails offline too. An
  artifact test parses all exported transforms under the Perspective signature. Run against the old export,
  580 of 580 fail.
- The drawing sheets and the schematic used a numeric format transform, which turns a value with no data into
  the literal text `null`. Unmapped placeholders now read **not connected**, in muted italics, and mapped points
  without Good data read **UNKNOWN**. The tag binding stays, so a placeholder that ever read Good would show its
  number and fail V4 instead of being hidden. The test covers all 334 placeholders.
- TI-109's band was invisible. Its real normal band, 120.28–120.52 °C, sat on an indicator stretched to its 175 °C
  shutdown limit, so the band took 0.4% of the width
  ([before](screenshots/native-before-fix-reactor-rows-TI-109-band.png), [after](screenshots/native-reactor-rows-bands-normal.png)).
  The indicator now draws an alarm limit only when it lies within 10 band half-widths. PI-107's limits still
  appear; TI-109's limit stays in the text column and in the State colour. This reverses an earlier Claude-only
  display choice, and operations should confirm it.

**Steve's October 8 question, answered.** He had asked why many tags registered as null and whether the normal
bands were right, since most looked like missing data. To see what he saw, the historical backup was restored into
a second disposable container. On those screens the agitator SC-212 read `null`
([screenshot](screenshots/historical-oct8-reactor-sc212-null.png)), and every unmapped drawing instrument read
`null`: **359** placeholders then, 12 on sheet 0 alone ([screenshot](screenshots/historical-oct8-sheet0-placeholders-null.png)).
None of these was a broken tag. Each one has no data source: SC-212's channel (XMV 12) is not in the published
replay, and the drawing instruments have no I/O mapping. Ignition reads them Bad, as it should, and the format
transform printed that as `null`. Today the count is **334**: 24 instruments have since been mapped to synthetic
demo points, and MS 14010 became a metadata-only callout with no PV. The census from the final run:

| Group | Count | Gateway quality | Shown on screen |
|---|---|---|---|
| TE recorded channels | 52 | Good | numbers |
| OPEN100 mapped (synthetic demo points) | 24 | Good | numbers |
| SC-212, no replay channel | 1 | Bad | NOT CONNECTED and UNKNOWN / no replay source |
| OPEN100 placeholders, no I/O mapping | 334 | Bad | not connected |
| False-good placeholders | 0 | | |

The bands are right where data exists. All 52 recorded channels have a band learned from the normal run, and
SC-212, with no data, has none. In normal replay the gateway flagged 0 of 52 values. Early in the fault, 16
values were outside their band before any alarm. At the alarm, 25 were outside their band, PI-107 among them,
and PI-107 was red. On the screen, though, only TI-109's band really looked missing, for the reason above. I
can't be sure that is what Steve saw on October 8. A freshly started demo also shows short trend history for its
first minutes.

**The final run.** Everything above was repeated from scratch on commit `485f000` (published as `34b4ef5`; see [commit identity](IGNITION_ACCEPTANCE.md#result)): a pristine archive, the same
write-only build (provider `f735cebe…` unchanged, project ZIP `1a6ce79c…`), and a fresh container. The receipt is
[`native-current-20261013.json`](../out/ignition/gateway/receipts/native-current-20261013.json). The tools are in
`scripts/ignition/acceptance/`.

| Check | Result | Evidence |
|---|---|---|
| Import fidelity (V1), both directions | PASS: 1,253 tag nodes and 23 views, 0 differences; exported views identical JSON | receipt `verifier.V1`, `exports` |
| Reconciliation (V2) | PASS: 53/53 TE, 910/910 OPEN100; MS 14010 metadata-only | receipt `V2` |
| Binding resolution (V3) | PASS: 1,082 bindings on 23 views | receipt `V3` |
| Quality honesty (V4) | PASS: 76 fed Good, SC-212 and 334 placeholders Bad, 0 false-good | receipt `V4`, `census.normal` |
| Liveness (V5), plausibility (V6) | PASS: 76 of 76 changed; 52 inside range | receipt `V5`, `V6` |
| Read-only (V7) | PASS: probe write accepted, two twin writes refused (BadUserAccessDenied) | receipt `V7` |
| Alarm pipeline (V8), recorded fault 6 | PASS: A feed flagged first; PI-107 active 0.5 s after crossing 2,895 kPa | receipt `V8` |
| Perspective transforms run | PASS after fix: 0 parse errors in the gateway log, 0 `null` on 23 routes | `native-overview-normal.png` |
| Direct load and reload of all 23 routes | PASS 23/23 | receipt `browser` |
| Every navigation target clicked | PASS 277/277; Back after each 277/277; Back/Forward chain 6/6; repeated clicks; 0 console errors | receipt `browser` |
| `/mimic` is the same overview | PASS: identical view; no second tab | contract, test |
| Desktop layout 1600 × 930 | PASS: unit pages scroll to their inventory and history rows | `native-reactor-rows-bands-normal.png`, `native-stripper-normal.png` |
| 390 px layout | **PARTIAL:** every route reachable by two-way scrolling and touch, but it is a fixed 1600 px control-room layout, not a phone layout | `native-overview-390px.png` |
| Quality transition: replay stopped | PASS: 52 TE values went Uncertain; screens read UNKNOWN with hatched vessels and "Outside band: unknown" | `native-overview-replay-disconnected.png` |
| Recovery | PASS: 52 Good again within about 14 s of restart | `native-overview-replay-recovered.png` |
| Fault replay on screen | PASS: amber values before the alarm, PI-107 red at the alarm, alarm table populated | `native-overview-fault-early.png`, `native-overview-fault-alarm.png`, `native-reactor-fault-alarm.png`, `native-alarms-fault.png` |
| MS 14010 callout | PASS: no value label, PV or OPC address; both FT 1401 records keep separate placeholders | receipt `exports`, `native-sheet0-not-connected.png` |

*(Note added with entry 47: the `native-*.png` screenshots named in this table were replaced by the entry 47 run of the corrected build. The originals from this run are in the repository history at commit `f5c270e`.)*

**What went wrong on the way, besides the product bugs.** My first scroll test said the unit pages could not
scroll, and I nearly "fixed" that. Git Bash had rewritten the route argument into a Windows path, so the browser
had opened a missing page. Re-run correctly, the pages already scroll; no change was made. The browser harness also
counted Perspective's own hidden page chrome ("by null") as a broken value at 390 px; it now reads only the view.
And a path-conversion bug in my scratch orchestration wrote one run's verifier credential to the wrong folder, so
the post-import stages were run again on the same fresh gateway. The import itself was not repeated.

**Also observed, not changed:**
- The header counts *tags* in alarm, so it read "Alarms: 1" while the table listed two active alarms on PI-107.
- With the replay stopped, "Alarms: 0" stays Good, because no alarm is active on uncertain data. The values
  around it all read UNKNOWN. Whether stale data should raise an alarm is an operations decision, not a screen edit.
- The gateway logged "Received event for missing view TE/Alarms" after navigating away from the alarm table. No
  visible effect was seen.
- Setup differs from a site in three ways: the API key was provisioned into the disposable gateway's config files,
  HTTP was used on localhost, and the verifier ran inside the container's network namespace so the OPC UA server
  could stay bound to localhost.

**Windows test portability, same pass.** On a plain Windows shell the suite failed 4 of 15 source-only scripts
and 5 of 20 full scripts. The fifth, not seen in the earlier desktop run, was a test reading a child process's
output as UTF-8 while Windows wrote its ANSI code page. The fixes: portable SVG filenames (identifiers keep their
XML escaping; distinct names, collision checks); symlink controls that skip only that sub-case, only on Windows
error 1314, with a printed SKIP that the runner counts; `-E -P` instead of `-I` for the packaging probe, plus an
assertion that the checkout is not on the path; and the UTF-8 request. After: Windows 15/15 and 20/20 with two
symlink sub-cases explicitly skipped (the runner withholds "suite passed"); a Linux Python 3.12 container 15/15
and 20/20 with no skips.

**Lesson:** an offline check that adjusts its input before testing it is checking a different system. The
gateway was the first thing that ran the generated code unmodified. It also showed that "honest" quality can
still read as broken: Bad was the right quality for those 334 instruments, and `null` was the wrong way to show it.

**At your plant:** import the exact candidate into a disposable development gateway before anyone reviews the
screens. Click every link, stop the data source, and watch what an operator would see. Keep "no data source" and
"broken" visibly different. None of this establishes operator usability, responsive physics, PI integration or
plant readiness. The screens were checked against recorded replay and synthetic points only.

---

## 39. Prototype: a 3D tour generated from the same contract as the screens (proof of concept)

**2026-10-12, built on a separate local branch and merged as a proof of concept on 2026-10-13 (entry 49); not
reviewed by operations.** Steve asked whether a Blender 3D tour of the process would help operations training. Native
acceptance still came first; this entry scopes the idea and records a small build that ran.

**What:** a generator that turns the TE seed model and the 2D display layout into a 3D scene, rendered headless in
Blender, with a camera that walks the units in flow order and tag markers coloured from the recorded fault-6
replay. Plan: [3D_TOUR_PLAN.md](3D_TOUR_PLAN.md).

**How:** `scripts/build_3d_scene.py` reads `data/te_process_model.json`, `data/te_display_layout.json`, the committed
normal bands and the published alarm setpoints. It validates the layout with the same contract check the 2D
renderer uses, derives a scene (`out/3d/te_scene.json`) and writes a self-contained Blender script. Blender 5.2.2 LTS,
the official portable ZIP with its checksum verified, rendered ten stills in about 20 seconds and a 361-frame
low-resolution walkthrough in about two minutes on a GTX 1060. The same scene exports to a GLB with each marker's tag
id in its node extras. `scripts/test_build_3d_scene.py` (40 checks at the time) runs the generated script against a
stub `bpy` and fails when a deliberate break marks every tag connected.

**What is data and what is Claude's:**
- From data: which units, streams and tags exist; tag ownership; the 26 stream/unit associations already reviewed
  for the 2D cards; the seed flow directions (then unverified; checked against the simulator source in entry
  42) and the flow order derived from them; every colour (replay samples 150, 200 and 258 against the existing
  bands and the 2895 kPa published limit); SC-212 not connected; TI-122's disputed owner.
- Claude only: every shape, size, height, nozzle, pipe route and marker height; the plan scale (2D seed pixels ×
  0.03 m); the camera stops and the choice of fault samples. These are placeholders, labelled as such in the scene
  data, on the ground plane and in a caption on every frame. Nothing was compared with another model or reviewed by
  an operator.

**Why:** the tempting version is a nice-looking model built by hand in Blender. It would drift from the screens on the
first correction, and it would look more certain than the drawing allows. Generating it from the screens' own
contract keeps one source of truth, and the drift checks fail before anything is drawn. A P&ID gives topology, not
geometry, so the honest scene is schematic: plausible shapes in the 2D arrangement, every dimension declared a
placeholder. The OPEN100 twin was not used then: its 1,881 links had unknown direction and its units are drawing
symbols (entry 48 later read direction from the drawings and gave OPEN100 its own structure-only tour).

**Recommendation recorded in the plan:** rendered video for training material now, because a fixed, captioned video
is hardest to mistake for an engineering model and needs no runtime or gateway change; an interactive viewer (from the
same GLB) once a site has verified geometry and instrument locations.

**Lesson:** a 3D view adds no process information; it adds credibility, which is the risk. Label the placeholders in
the artifact itself, not only in the documentation, and generate the scene from the same contract as everything else.

**At your plant:** the software is the cheap part. The cost is real geometry (a 3D design model, scan, plot plan or
walkdown), instrument locations from isometrics or the field, an operator-written tour script, and keeping it current
under management of change. Walk it down with an operator before anyone trains on it.

---

## 40. Check the 3D render procedurally, then make it an orientation tour (proof of concept)

**2026-10-12, same local branch; not reviewed by operations or a process-safety engineer.** Steve asked for three
things:
1. a way to verify the render procedurally against the Ignition/PI asset framework and the P&ID;
2. a version for orienting new operators, or existing operators on a new process;
3. emphasis on the highest-risk elements, tied to what public accident data shows.

**What:**
- `scripts/verify_3d_render.py`: four groups of checks.
  - Accuracy against the Ignition gateway import, the seed UDT export, the PI AF sheet and the Perspective
    bindings.
  - Topology derived from the 3D pipe ends, markers inside equipment, and the tour as a valid walk.
  - Trace of each tag to a P&ID drawing.
  - Legibility from Blender's own measurement of each still: projected label boxes, raycast occlusion and WCAG
    contrast from the rendered pixels.
- A narrated orientation tour: captions, an SRT and an offline synthetic voice.
- Emphasis, from data, on the unit carrying published shutdown limits (R-101) and on the unit where fault 6 shows first
  (U-100).
- One cited public incident per stop, from a prototype keyword match over a compiled corpus of public agency records
  (CSB, OSHA, EPA RMP; [HAZARD_CITATIONS_DESIGN.md](HAZARD_CITATIONS_DESIGN.md)).

**What the checks found in the first prototype** (reproduced with `--label-layout legacy` and measured by the same
code):
- 25 label overlaps, 166 labels under 20 px at 1080p (the smallest 4.6 px), 241 under 4.5:1 contrast, and 105
  labels or markers hidden by geometry.
- Two tag markers (FI-106, AI-123) were **inside** the reactor shell. A fixed offset from the riser pushed them in.
- Two pipes (S4, S11) ended 0.8 m off the stripper, because nozzles on a thin column were spread sideways.

The legibility numbers were visible by eye. The buried markers and floating pipe ends were not; they were found by
the occlusion raycast and by deriving each pipe's endpoints from geometry.

After the fixes, all 16 checks passed on all 10 stills. Every scene tag maps 1:1 to its Ignition path and PI AF
attribute; the 16 extra analyzer component channels in Ignition are explained.

**The E-101 / K-101 case, honestly:** Steve saw those two labels "overlapping". The strict overlap test did not flag
them: they sat 13 px apart on one baseline and read as one string. Looking at the crop, I added two checks:
- a crowding rule for plate-less labels closer than one line height;
- occlusion sampled over a grid of points on each label instead of its centre.

With those, the case is caught (crowded, 11 px text, contrast 2.9 and 3.2:1, a pipe hiding a third of K-101). The
rules were written after seeing the defect, so this shows they catch it now. It does not show they would have found
it first.

**P&ID trace, honestly:** 0 of 37 TE tags trace to a drawing, because the TE model was built from a paper. All 37
are declared seed and checked against `teprob.f`. The check also reads the extracted twin's drawing id and bbox, so
an extracted plant would report real coverage.

**How the fixes work:**
- **Labels per still.** A still shows only the labels it needs.
- **Fixed screen size.** Labels are scaled to a fixed on-screen size and sit on dark plates.
- **Greedy declutter.** Placement avoids other labels, every marker and the caption band. The rectangle code is
  shared with the verifier.
- **View choice.** Cameras are fitted to each unit's shape, markers and battery limits. The renderer takes the
  first of seven candidate views that hides the fewest markers, by raycast.
- Pillow re-read the same pixels and agreed with Blender's contrast to 0.00. OCR was not run; tesseract is not
  installed and was not added.

**What is data and what is Claude's:**
- **From data:** every number in the narration and captions (streams in and out, normal bands, published limits,
  first band exits and counts in the recorded fault-6 replay, values at the alarm sample), the emphasis, and the
  incident URLs exactly as recorded.
- **Claude only:**
  - the one-sentence role of each unit and the connecting prose;
  - the choice of 3-5 citations per equipment kind from the heuristic's shortlist, and their one-line summaries;
  - the label sizes, thresholds and candidate views.

  Every caption says the script is Claude's and not operator-reviewed. The video's audio track is titled as a
  synthetic voice.

**Voice:** Windows' built-in System.Speech (SAPI), offline, one WAV per segment, timed into the video. ffmpeg, which
was already installed, muxes it with soft subtitles. The narration runs about 640 seconds, longer than my word-count
estimate of 466 seconds; the timeline uses the measured WAV lengths.

**Why:**
- A 3D render adds credibility faster than it adds information, so it needs checks that do not depend on someone
  looking.
- An orientation tour is only safe if its numbers cannot drift from the screens. So the narration is generated from
  the same files as the screens and the Ignition and PI exports, and the verifier proves the 1:1 mapping.
- The hazard emphasis keeps the data-backed parts (limits, first warning) apart from the heuristic part (public
  incidents). The heuristic produced false positives: NTSB's Asiana 214 matched "tower".

**A wording slip, caught before the final render:** my first summaries or captions for seven incidents said more than
their records do: most stated CSB recommendations as findings ("dead legs in feed piping caused..."). The emphasis
label also said "HIGHEST CONSEQUENCE", which the data does not show; it now says "PUBLISHED SHUTDOWN LIMITS". All were
rewritten and the tour was re-rendered.

**Lesson:** a verifier written after seeing a defect needs to say so. Separately, the two most important defects
here (buried markers, pipes ending in air) were invisible in the stills and were caught only by checks that reason
about geometry.

**At your plant:** a tour script for real operators must be written or reviewed by an operator. The hazard emphasis
should come from the site's PHA/HAZOP. Public incidents can illustrate it; they cannot rank it. Run the verifier
whenever the twin, the Ignition tags or the PI AF model change, because the tour is only as right as the 1:1 mapping.

---

## 41. Review: clean up the 3D stills before rendering any more video (proof of concept)

**2026-10-12, same local branch; review stills only, not reviewed by operations.** Steve looked at the reactor still
from entry 40 and said "it kinda looks like we need quite a bit of cleanup and review". The full video render that
was running was stopped and its partial output deleted. The review became ten rules:
- focus per stop and 3-4 key tags;
- one pill label system;
- pipes coloured by service on two racks;
- recognizable equipment and an eye-height camera;
- a corner badge instead of per-frame disclaimers, and a two-line caption;
- natural, short narration;
- operating alarm vs shutdown limit kept apart;
- a reactor-apt citation.

A second round from Steve asked for:
- the process flow made visible;
- a "why each piece exists" card at each stop;
- essential-function animations later;
- a lockout/tagout version designed now.

**What was built:** the redesign in [3D_TOUR_PLAN.md](3D_TOUR_PLAN.md#review-redesign-2026-10-12). Only five stills
were rendered: overview, reactor stop, fault 6 at the high alarm, a flow legend, and a LOTO mockup. The verifier
gained three checks: no pill on the focus unit's silhouette, no all-caps runs, and the review's 18 px minimum. It
also now checks that inferred utilities and valve symbols map to contract final elements. All 17 checks passed on
the five stills; the first prototype's layout, measured the same way, failed 3.

**What I got wrong first, and fixed before reporting:**
- Overlay cards rendered pale grey. Swapping a plate's mesh dropped its material.
- The flow legend's plate came out too short. Blender does not re-evaluate hidden text, so the bounding box was stale.
- The ground grid showed as one big cross. The texture used object coordinates on a scaled plane.

None of these was caught by a check; they were seen by looking at the stills. The legibility checks then caught three
pills at 16.2 px (text with no descenders measures shorter). The pills were enlarged; the threshold was not loosened.

**Limits, honestly:**
- PI-107's 2,895 kPa g is the operating high alarm the Ignition screens use. 3,000 kPa g and TI-109's 175 °C are
  the simulator's published shutdown points, shown only on fault stills.
- TI-109 has no operating alarm, so at the normal reactor stop its pill shows no limit. That is my reading of "the
  shutdown limit only on the fault stop".

**Purpose cards:** at the time, paraphrased by Claude from the published TE description (Downs & Vogel 1993), with
the paper not in this repo. The text check in entry 43 found errors in them (the purge placed at the compressor,
the stripper overhead missing from the feed header); since the merge every card takes its purpose sentence from
`data/te_unit_purposes.json`, which cites the simulator lines it restates (entry 42).

**Reactor citation aptness:** the corpus has no gas-phase reactor incident. Kuraray (a reactor taken above its
pressure limit; the CSB asked for the limit to be made clear to operators) now leads. Bayer CropScience is kept,
phrased generally.

**Naming:** the incident corpus was compiled in a separate, private project. Nothing in this repository names it,
reads it at build time or depends on it; only public agency records were used, and the curated result is committed.

**LOTO:** a design section and a mockup still. Every isolation point is inferred from the seed model and marked `*`;
the numbers are list order, not an isolation sequence. The still says it is not a procedure, and points to OSHA 29
CFR 1910.147, the site's verified P&IDs and an authorized person.

**Lesson:** checks of legibility and accuracy do not catch "looks like scaffolding". A person looking at one still
found more than the 17 checks did. Keep both, and render a handful of stills for review before rendering minutes of
video.

**At your plant:** design reviews of training visuals belong with operators early, on stills, before anyone spends
render time or narration on them. A LOTO view built from a P&ID alone is a sketch; the isolation list comes from the
energy-control program.

---

## 42. Verify the TE topology against the simulator source

**What:** every unit, stream, flow direction and tag-to-unit assignment in the Tennessee Eastman model was checked
against the simulator code. Until now only tag names and units had been checked (entry 5); the topology was a
hand-built seed that every screen inherited. Result, over 56 elements (6 units, 13 streams, 37 tags): **51
confirmed, 4 corrected, 1 unresolvable.**

**How:**
- `scripts/verify_te_topology.py` reads `teprob.f`, the same open Downs & Vogel code entry 5 used, and pins its
  checksum. It does not use a hand-typed table of the answer. It reads the code itself:
  - the component balances (`YP(I+9)=FCM(I,8)-FCM(I,9)-FCM(I,10)-FCM(I,11)` is the separator: stream 8 in,
    9, 10 and 11 out) give each internal stream's source and destination;
  - the state mapping (`UCLS(I)=YY(I+9)`) and variable suffixes give which holdup is which unit;
  - each pressure-driven flow line (`DLP=PTS-760.0`, then `IF(DLP.LT.0.0)DLP=0.0`) gives a direction that cannot
    reverse, and valve-set flows are never negative;
  - the `XMEAS(n)=`, `XCMP(n)=XST(i,k)` and `VPOS(k)` lines give what each measurement and valve acts on;
  - the header comments give each internal stream's published number.
- The second source is the revised TE code by Bathelt, Ricker and Jelali (2015), `temexd_mod.c` from
  [N. L. Ricker's TE archive](https://depts.washington.edu/control/LARRY/TE/download.html) (paper:
  [IFAC-PapersOnLine 48(8), 309-314](https://doi.org/10.1016/j.ifacol.2015.08.199)). Its header documents the states,
  measurements and stream names in words. It cross-checks every holdup and stream number teprob.f gives (all agree).
  It also supplies the one fact teprob.f doesn't state: the numbers of the two streams with no instrument (5,
  stripper overhead; 7, reactor effluent). Without it, those streams are reported unresolvable.
- The model's own `type` field maps units to source roles; no unit ID is hard-coded. Corrections are written into
  the model with the old value kept under `previous`, the same way `verify_te_source.py` does it. The full table
  is [`out/te_topology_check.md`](../out/te_topology_check.md).

**What it found:**
- **Corrected: the purge.** The seed drew the purge (S9) leaving the compressor. In the code the purge flow is
  driven by separator pressure (`DLP=PTS-760.0`), carries separator vapour composition, and is subtracted from
  the separator balance, independently of the compressor. S9 now starts at V-101, and its three tags (FI-110,
  FV-206, AI-129 with its seven component channels) moved from K-101 to V-101. Entry 23 had already noticed the
  published schematic disagreed and left it flagged. The code settles it.
- **Resolved: TI-122 stays on the condenser.** The source header calls XMEAS 22 the *separator* cooling-water
  outlet temperature. But it is the outlet of the circuit whose flow is XMV 11 ("Condenser Cooling Water Flow") and
  whose inlet is disturbed by IDV 5 ("Condenser Cooling Water Inlet Temperature"). Its heat term
  `QUS=UAS*(TWS-TST(8))` exchanges heat with the reactor effluent, which is where the condenser sits. The revised
  code names it "Condenser cooling water outlet temperature". The "separator" label comes from where the code books
  the duty: in the separator's energy balance, because the simulator has no condenser vessel. The open question
  from entry 5 is closed and kept in the model as `resolved_question`.
- **Unresolvable: PI-116.** Both sources call XMEAS 16 "stripper pressure", but the code computes it from `PTV`,
  the feed-header pressure. The simulator has no separate stripper vapour space. The code and the names point at
  different units, so the script keeps it on C-101 and flags it. The screens say so.
- **Confirmed with caveats.** The condenser and compressor have no holdup in the simulator; their positions come
  from the heat term and the compressor curve. The split of streams 7 and 8 at those machines (S7/S7b, S8/S8b) is
  the published flowsheet's drawing: the code has one flow for each. Which segment FI-105 is on is therefore a
  model choice. The compressor recycle valve HV-205 spills flow back around the machine, and the code computes
  that only as a reduction of net flow, so no spill-back stream exists to assign it to. FI-119 "steam flow" is
  computed from the stripper heat duty.
- **Plain-language purposes.** `data/te_unit_purposes.json` did not exist on any branch. It now holds one
  sentence per unit. Each one restates cited simulator lines and carries line numbers against the pinned checksum.
  A test confirms every cited line still says what is quoted, so the purposes can't drift from the source unnoticed.
  The 3D tour draft's narration predates this and should take its purpose text from here.

**Downstream:** stream directions now live in the model (`direction: forward`), so the display's "seed direction"
adapter was removed. The screens now say "TOPOLOGY VERIFIED AGAINST SIMULATOR SOURCE" where they used to say
UNVERIFIED. They keep the caveats that are still true: tap positions and along-line order are not in the source.
The separator page gained the purge route, its two cards and the purge analyzer. The compressor page lost them.
SVGs, Ignition tags, the PI sheet, the review sheet and the 23-view project were regenerated. Ten TE tag paths
moved, so the native gateway acceptance from entry 38 covers the build before this change, not this one.

**Tests:** `scripts/test_te_topology.py` (20 checks, in the full suite). Two kinds of control matter most:
- **Wrong models must be rejected.** Reverse a stream, move a stream's endpoint, put the purge back on the
  compressor, move a reactor tag or valve to another unit, give an instrument the wrong stream. Each one is
  corrected or flagged.
- **The check must read the code.** Edit the simulator text and the conclusions must follow. Point the condenser
  heat term at another stream and E-101 and TI-122 lose their confirmation. Reverse the purge pressure difference
  and S9 becomes unresolvable. Move the purge into the header balance and S9 becomes unresolvable while the
  pressure driver still says separator. Change both and it is corrected to the header.

**Why a script that reads the code, not a careful read of the code:** a reviewer can rerun it and audit every
row. Each row names the code line that decided it. When the source is split, the script says so instead of
picking a side quietly.

**Lesson:** "verified" needs a scope. Entry 5 verified names and units, and the topology underneath stayed a
guess while every screen drew it. When two parts of one source disagree (a header label and the equation behind
it), the deciding rule has to be explicit and applied the same way everywhere. Here it is: the code's location
plus a majority of documented names; where they split, the element stays flagged. The same rule that confirms
TI-122 leaves PI-116 unresolved. It was written while looking at both cases, so it is not pre-registered.

**At your plant:** the equivalent of `teprob.f` is whatever system already computes the process: a simulator
model, the DCS configuration, or the historian's tag-to-unit hierarchy. Check the drawing-derived topology
against it mechanically, and keep the disagreements as a list for the process engineer. What still needs a person
here: PI-116's owner; whether the S7/S7b and S8/S8b splits and FI-105's segment match how a real plant would draw
them; and every tap position, size and pipe route, none of which any simulator records.

---

## 43. Check the PI files against what AVEVA publishes, and get ready for a first human review

**2026-10-13:** three gaps a reviewer would point at first. The PI AF files have never been in a PI system. The
3D tour's text has never been checked against a source. And no one with operations knowledge has looked at
anything. None of the three is closed. Each is now smaller, and what remains open is written down.

**PI without a licence.** The free route is gone. The PI Developers Club, which included a personal development
PI System and a 45-day free trial, was retired on January 1, 2026. What remains is partner agreements, paid Flex
test credits, or a university's academic licence ([PI_MAPPING.md](PI_MAPPING.md) lists the terms and sources;
nothing was signed up for). So the check stays offline, against what AVEVA itself publishes: three course
workbooks and an Apache-2.0 AF export in AVEVA's own SDK samples. The sheet headers are mostly in screenshots, so
they were read by OCR and checked by eye. The results, now in `data/pi_builder_reference.json` with a page for
each entry:
- `AttributeType` is the documented column. `AttributeValueType`, which the legacy staging CSV still writes, appears
  nowhere. The candidate CSV's one correction was right.
- `%`, `kW` and `m3/h` match the vendor export's abbreviations exactly. `degC` does not: the vendor writes `°C`.
  `kg/h`, `kPa g`, `kscmh` and `mol%` are not in the sample, which covers only 33 UOM classes. Most likely
  `kscmh` (a TE unit) and the gauge pressure need custom UOMs at a site.
- The TE sheet names six element templates it never defines. The extracted twin's attributes have no units at all,
  while the vendor workbook says "Always assign a unit of measurement!"
- The AF XML schema types `Type`, `DefaultUOM` and `ConfigString` as plain strings. Adding an AF XML export and
  validating it against the schema would not have caught any of the above.

`scripts/check_pi_export.py` reports those findings with their evidence and fails only on internal
inconsistencies. Its test plants each error class to show the check catches it.

**The 3D tour's text.** The purpose cards were checked against Ricker's revised simulator code and against open
papers that restate Downs and Vogel. That check found the same purge error as the TE topology work, which used
the original Fortran: the compressor card said the purge leaves at the compressor, and both codes draw it from the
separator. The cards now take their sentences from the verified TE file. The public-incident citations were read
against the CSB and OSHA pages. Seven needed a correction or a missing detail, and the six EPA RMP links did not
resolve to their records. The biggest: Tesoro Anacortes ruptured during a
maintenance stream switch, not "during a restart". The Williams Geismar link returned 404. And the Bayer summary said more than its
cited page does. The fixes wait as a patch for the clean merge ([drafts/3d-tour/REVIEW_NOTES.md](../drafts/3d-tour/REVIEW_NOTES.md)).
An OCR read-back of the five stills found one real legibility problem. In the tour's typeface, 1, I and l look
alike. Every tag ID the whole-frame read missed was one of those confusions: `Pl-107`, `Tl-109`, `E-10I`.

**The first human review.** [docs/review-kit/](review-kit/README.md) is a one-sitting kit with two tracks that
must not mix. Anyone can check that text matches the drawing, that boxes sit on symbols, and that labels can be
read. Only an operations person can say whether a line, an alarm limit, an isolation point or a hazard is right.
Track A findings go in as notes or identifier-text-only corrections, never as `confirm`, so the record cannot
later pass for an operations review. The timing log uses the review-effort protocol's fields, but one sitting is
a pilot, not the study.

**Follow-up, same day: fix the exporter, not just the report.** The PI files are now PI Builder sheet schema v2:
- `AttributeType` replaces `AttributeValueType`.
- `°C` replaces `degC`.
- The four units with no vendor evidence are written to `custom_uoms.csv` with a definition, never assumed. Gauge
  pressure and standard volume flow each get their own class with no conversion, because converting either needs a
  local reference: the atmosphere, or the standard conditions.
- The six TE element templates are defined at the top of the sheet.
- Attribute descriptions move to their own file. A full OCR pass over the workbooks found no attribute description
  header, so writing one would have been a guess.
- Placeholder rows are left unselected, so PI Builder won't publish them.

`IMPORT_STEPS.txt` gives the publish order. The offline check now passes the TE sheet with a single instruction
(create or map four units) and flags any selected placeholder as an error. It's still not import-tested; every
generated file says so.

**Lesson:** "we can't test it without a licence" was half true. The import can't be tested, but the vendor's own
published material settled the header question and found a unit spelling no test of ours could have flagged.

**At your plant:** run `check_pi_export.py`, then pull your own UOM classes out of PI Builder before mapping
anything. The vendor sample is a subset; your UOM database is the authority.

---

## 44. One plant, end to end: draw the TE model in the house style and read it back

**What:** 2026-10-13. The extraction (OPEN100) and the live twin (Tennessee Eastman) were on two different plants,
so "drawing → extraction → twin → live values" had never been shown on one plant. The plan called for extracting a
TE drawing in phase 3; it was never done. Now the verified TE model is drawn as three P&ID sheets in the house style
learned from OPEN100, read back by the frozen method, diffed against the model, exported, and matched to the replay
server's live points.

**How:**
- `scripts/draw_pid_from_model.py` renders the sheets (PNG and SVG) and emits answer keys in the PID2Graph schema
  from the same model, with each symbol's printed text and the model item it draws. What is drawn comes only from
  `data/te_process_model.json`; where it goes comes from a drafting layout (`data/te_pid_layout.json`). The generator
  refuses a layout that drops a model item, draws one twice, or names a tag the model doesn't have. Cooling water,
  steam and the compressor bypass are lines the model has no stream for, so the key marks them as drafting additions.
- The style is measured, not asserted: `scripts/style_fidelity.py` runs the same measurements on the 12 OPEN100
  sheets and the 3 generated ones. 32 of 36 generated values sit inside the OPEN100 range; the four outside are
  symbol counts and one ink figure, because the model holds no drains, vents or manual valves.
- The key is checked against the pixels: the code line tracer, given only the key's symbol boxes and the image,
  recovers exactly the key's links on all three sheets. The first version failed this on two sheets: an equipment
  box drawn to the centre of its outline let the wall's outer edge join three lines, and a bubble placed inside the
  reactor's box hid its leader. Both were drawing bugs, fixed in the generator, not in the tracer.
- Extraction: method M3 unchanged (2×2 tiles, prompt v2, tracer defaults), GPT and Claude, 5 runs each on the clean
  sheets and 3 each on the round-4 degraded copies (`degrade_scans.py --src`, same levels and seeds). No Gemini.
  84 sheet runs, no failed tile.
- Scoring: the frozen scorer for symbols and connections, plus the project's first tag-text score
  (`scripts/score_te_roundtrip.py`): matched by position, compared after dropping case and separators.
- `scripts/te_model_diff.py` lists what a reviewer would correct against the verified model; `scripts/te_live_check.py`
  matches the extracted tags to the replay server's points and reads them twice.
- Midway, the topology check (entry 42) moved the purge stream and its three tags from the compressor to the
  separator. Sheet 102 was regenerated with the purge leaving the separator, the 27 runs made on the old sheet 102
  were set aside by image checksum, and sheet 102 was re-run under every label. Sheets
  101 and 103 came out byte-identical, so their runs stood.

**What it found** (details in [EVALUATION.md §6](EVALUATION.md#6-one-plant-end-to-end-tennessee-eastman)):
- On clean sheets both models read every one of the 43 printed tags in every run. Review load 2.1 (GPT, all 5 runs)
  and 2.2 (Claude, 2.1–2.6), almost all of it the agitator motor reported as an extra symbol.
- Text fails before shapes. At the old-scan level GPT still found every symbol and line but read only 56% of tags
  exactly (FI as PI, LI as LE, FV as PV). At the bad-scan level GPT read 14% and Claude 49%.
- In one bad-scan run Claude rotated the three feed valve tags (FV 203 read as FV 201, FV 201 as FV 202, FV 202 as
  FV 203). Each is a real tag, so a tag-only diff passes it and the live check binds all three to moving points. Only
  the position-aware score catches it.
- For the declared chain (GPT, clean, run 1), the reviewer diff has 10 corrections. Feeding the key in as a perfect
  extraction leaves 9 of them, so they come from the converter and the model's conventions, not from the reading. The
  feed header drawn as an in-line mixer becomes a line item, so its six feed-line items get the reactor as owner. Two
  extra unit links come from lines that share pipe at the header and the bypass.
- 36 of the extracted twin's 37 tags resolve to replay points and all 36 moved; SC-212 has no recorded data.

**Why:**
- **Generate, don't look for a picture.** A drawing generated from the verified model in a learned house style is
  closer to what a plant would actually do than any diagram we could find: most sites have an instrument list long
  before they have trustworthy drawings, and generated sheets can be redrawn in each site's own style.
- **Call it a round trip.** The drawing and the key come from the same model, so the scores can't say how well this
  reads a real plant's sheets. They measure reading fidelity on clean house-style drawings: an upper bound. The
  tracer check and the generator's refusals keep the key honest about what is drawn, not about the plant.
- **Replicates, not a single run.** Five clean and three degraded runs per model show the spread. GPT's clean runs
  scored identically; Claude's degraded runs varied by several points.
- **The perfect-reader diff** separates the converter's errors from the models'. Without it, the feed-header ownership
  errors would have looked like reading errors.
- **Rejected:** fixing `build_twin.py` so a tagged in-line mixer becomes a unit. That would tune the converter to the
  one drawing we generated, and it would change the OPEN100 twin. The diff reports it instead. Also rejected:
  importing the extracted twin's tags into a gateway here, because the disposable gateway was in use by another
  workstream at the time.

**Lesson:** on clean drawings the reading is nearly solved and the remaining work is in the converter's rules and the
model's conventions. On poor images the dangerous error is a misread that is still a valid tag, and only checking
against position (a walkdown, a loop check) catches it. A live value that moves proves the binding exists, not that
it is right.

**At your plant:** if you have no usable drawings, generate them from your instrument index in your own house
style, label them "not a drawing of record", and walk them down under your management of change before anyone
relies on them. Use the generated sheets and their keys to measure your extraction method on your own style before
you trust it on your scans. And never accept an I/O binding because the value moves: loop-check it.

---

## 45. Start from the data: assess both datasets first, then make every correction travel

**What:** a written Stage 0 for each dataset (where the data came from, what is checked, what is inferred, how sure
we are per element class), a machine-readable list of every stage after it, and an orchestrator that shows which
outputs are stale after a correction and rebuilds them.

**How:**
- [DATA_LINEAGE.md](DATA_LINEAGE.md) lays out Tennessee Eastman and OPEN100 as staged pipelines: input, treatment,
  output, confidence carried forward, and who or what checked it. The numbers come from files already in the repo:
  37 TE tags checked against the simulator source (36 confirmed, 1 corrected), units and streams not yet checked on
  this branch, OPEN100 review load 17.8 per 100 on sealed drawings, and 2,886 twin items, all unverified.
- [`pipeline/stages.json`](../pipeline/stages.json) lists the 13 stages with their real scripts, inputs, outputs,
  prerequisites and the provenance fields each output carries. `scripts/pipeline.py` hashes each stage's inputs,
  code and config into a lock file when it builds the stage; `status` marks a stage stale when any of them changed;
  `rebuild --from <stage>` re-runs it and everything downstream; `confidence` rolls the per-element fields
  (source check, review status, risk tier, tag status) up per dataset.
- `scripts/provenance.py` reads one item's provenance from fields the models already carry. The seed exports now
  end each Ignition tag's documentation and each PI attribute's description with
  `source check: … | ops review: …`, the way the extracted twin's exports already did. Two new generators are
  labelled proof of concept in their own files: the overview mimic as layout data, and 3D scene data with
  inferred LOTO candidates.
- `scripts/test_pipeline.py` copies the repo to a temp folder, moves FI-110 from K-101 to V-101 with
  `apply_review.py` (one part of the purge correction the topology check makes), rebuilds from the model, and checks the move in
  the Ignition tags, the PI sheet, the review sheet, the mimic layout and the scene data. It also checks that no
  script changed and that a second rebuild writes identical bytes.

**What the test found:** the overview mimic picked its readings from a hard-coded list per unit. With FI-110 moved
in the model, the reading's tag path followed the model (`TE_Plant/V-101/FI-110`) but the reading was still drawn
beside the compressor. The topology branch had to edit that list by hand to move the purge. The fix is small: the
list still chooses *which* readings the overview shows, and the model decides *where* each one is drawn. With the
old placement put back, the propagation check fails on exactly that reading.

**Why:**
- **Changes at the start have to be cheap.** The review day will correct things in the models. If each correction
  also needs hand edits in four generators, corrections stop happening, or they happen in one output and not the
  others. A stale flag after the correction and one rebuild command make the cheap path the right one.
- **Confidence has to be visible before results are.** It is easy to read a polished screen as a validated one.
  Every output inherits its inputs' confidence, and the replay, the mimic, the 3D data and the LOTO candidates say
  "proof of concept" in their own files. They are there to iterate on.
- **Who checked matters as much as what was checked.** The rollup counts a review as an operations review only
  when the reviewer string names an operations role. A confirmation by anyone else, including me, keeps its label
  in every output. This trusts the string; nothing authenticates it.
- **Rejected:** a general workflow engine (more machinery than 13 stages need), timestamps instead of hashes (a
  checkout changes them; Windows and Linux line endings are normalised before hashing instead), and rewriting the
  generators to emit provenance (a one-line passthrough where a format has a free-text field was enough).

**What it does not do:**
- Two stages need the TE replay download (the normal bands and the gateway kit). They show `NEVER BUILT HERE` in
  this checkout: their committed outputs predate the lock, and I have not rebuilt them through the orchestrator.
- Extraction, scoring and the twin build are "recorded" stages. They need model calls or run records that are not
  committed, so the lock accepts their committed outputs as the record. It does not re-run them.
- "Fresh" means rebuilt from current inputs, not correct.

**Who did what:** Claude (Claude Code) wrote the manifest, the orchestrator, the tests, the docs and this entry
from my direction. No second model reviewed it, and I have not walked the lineage myself yet; that walk is the
review day ([review-kit/FOLLOW_THE_DATA.md](review-kit/FOLLOW_THE_DATA.md)). The source-only suite passed 16/16 on
Windows with two symlink sub-cases skipped by the platform. The full suite was not run in this checkout because the
TE replay files are not downloaded here.

**Lesson:** a pipeline that regenerates outputs from one model can still hide hand-kept copies of that model. Here
it was a per-unit list in a screen generator. The way to find them is to change one fact upstream and check every
output for it, rather than read the generators.

**At your plant:** write each source's Stage 0 before building anything: who owns it, what checks it, what is
inferred, and how sure you are per element class. Then make sure every correction goes into the source, not an
output, and that one command shows what a correction left stale. When a reviewer signs off, record their role with
the decision, so a document-control check never reads as an operations approval.

---

## 46. More drawings with tag text, five runs per model, and a kit for the first timed review

**2026-10-13.** Reviewers of the results could point at four gaps. Holdout A is six drawings. Tag reading had never
been scored, because the OPEN100 keys carry no text. Claude against GPT was called a tie or a win from single runs.
And review time, the number the cost case rests on, was never measured. This entry closes the first three as far
as public data allows, and prepares the fourth.

**Finding drawings with tag truth.** The PID2Graph paper's 60 industrial P&IDs aren't public. Dataset-P&ID has text
labels, but they are random strings, its licence forbids sharing adaptations, and its drawings are already holdout
B. The DEXPI standards initiative publishes example and training P&IDs with their DEXPI XML (CC BY 4.0, on GitLab
now; the old GitHub repositories point there). The XML carries every item's class, its drawn shape and position, its label
text and the piping topology, which is all an answer key needs. One example also ships a CAD tool's equipment,
instrument and valve lists for its two drawings. The selection rule took every complete DEXPI 1.3 example sheet
plus that one: three XML-keyed sheets (49 symbols, 60 links, 33 tags) and two list-keyed sheets (145 identifiers).

**The adapter, and what the oracle check caught.** `scripts/adapt_dexpi.py` places each shape-catalogue symbol by
its position, rotation, mirroring and scale, rasterises the published SVG or PDF, and writes keys in the PID2Graph
format so the frozen scorer reads them unchanged. Drawing the key boxes over each render and scoring the key against
itself found three problems before any model ran: a column section drawn inside its column counted as a second
tank; flanges and blinds, drawn as a single stroke, had zero-area boxes that can never match; and one instrument
label's third line (an area prefix) had joined its tag. All three were fixed and recorded in the pre-registration,
which was committed before the first model call (`bd7d7ff`).

**Replicates.** Five fresh runs of the declared method per model on holdout A and on the DEXPI sheets, Claude and
GPT only. Gemini wasn't run, on Steve's direction; its earlier numbers stay, labelled as earlier runs. 220 records,
no failures, and every record reports the same model IDs as round 2.

- **Holdout A:** GPT 20.1, Claude 29.8 review load. GPT is better by more than run noise on these six drawings (9.8
  points, interval 7.3–12.2), but resampling the drawings gives −4.5 to +26.5 for the gap, so across drawings like
  these it is a tie. The pre-registered rule made that call before the numbers existed, which is the only reason I
  trust it: the runs-only interval is the more flattering one, and I would have been tempted to lead with it.
- **Noise was underestimated.** Round 2 assumed "about 1 point" between runs, from one repeat on the development
  set. Five runs give a standard deviation of 1.4–1.9 points. Round 2's single runs were a lucky draw for GPT (17.8,
  below its five-run interval) and an unlucky one for Claude (32.4, above). The round-2 verdict, a ~30-point gain
  from tiling plus tracing, is far outside that and stands.

**DEXPI: worse, and partly for a reason the key decides.** Review load was 95.4 (GPT) and 61.8 (Claude), against
about 20–30 on holdout A. Much of it is what counts as a symbol. Equipment nozzles are drawn as little stubs with
labels (N1, N2), but DEXPI treats them as parts of the equipment, and the key followed DEXPI. GPT reported them as
symbols in three of five runs on the reference sheet and not in the other two; the tracer then attached lines to
each one. Its review load on that sheet swung between about 33 and 145. A single run would have shown either
number, and either would have been wrong as a summary. The small sheets also amplify: on a 21-item sheet each
correction is about 5 points.

**Tag text, finally measured.** On the reference sheet both models read all 20 tags exactly, including two-line
instrument bubbles. Across the three XML sheets: GPT 29 of 33, Claude 28 of 33, identical in every run. The misses
share a cause: vertical valve labels, a two-line equipment label, and a control-valve number drawn on a separate
actuator bubble. On the list-keyed sheets GPT found all 145 identifiers in every run and Claude 99.4% on average. A
cross-sheet control showed why that is an upper bound: valve numbers repeat between the two sheets, so a short
identifier can match by coincidence.

**A bug in my own report, caught by reading it.** The first replicate summary called the tag difference "different"
under the runs interval. Every run had the same score, so the interval had zero width and excluded zero trivially.
The script now says "no run-to-run variation" in that case, with a test, and the commit says when and why.

**The review kit.** Review minutes stay unmeasured: no reviewer timed anything, and inventing a number would undo
everything above. `out/review_kit/sheet-8/` packages the smallest holdout-A sheet's review queue (88 rows) with the
drawing, the overlay, a timer that records only pseudonymous start/pause/stop timestamps, a summary that refuses an
unfinished log or a reordered sheet, and a draft study protocol whose design decisions are deliberately blank. One
sitting gives one reviewer's minutes on one sheet: a first observation, not a saving.

**What this doesn't fix.** Five DEXPI sheets from one publisher are clean, vector-drawn and small; they test a third
drafting style and tag reading, not real archives. The sample of drawings, not of runs, is still the limit on every
model comparison. Nothing was tuned on these results: a key that counts nozzles, or a tracer that ignores stubs on
equipment, would be a new method needing new drawings.

**Lesson:** report the interval that answers the question you are asking. "Would it change if I ran it again?" and
"would it hold on other drawings?" have different answers here, and only the second one matters to a plant.

**At your plant:** run the selected method several times on your pilot sheets before believing a single score; a
bimodal result (like the nozzles) is a sign that a definition, not the model, needs a decision. Write down which
drawn things are symbols for you before scoring anything. And time the first review: it costs one sitting and
replaces the most important assumption in the cost case.

---

## 47. Count what the bands detect, and make lost data an alarm

**2026-10-13.** Three gaps a reviewer would point at first. The fault demo showed one easy fault and called the
bands an early warning. When the replay stopped, every value read UNKNOWN while the header still said "Alarms: 0".
And the header counted tags in alarm, not alarms. A fourth: at 390 px the screens were a 1600 px control room you
scroll around in.

**How often do the bands detect a fault?** I fetched the rest of the Braatz set (44 files; every one is
byte-identical to the Braatz group's own archive at MIT, which I checked before recording the checksums) and wrote
the rule down before scoring any fault file: the plant is flagged when any of the 52 channels is outside its band,
and a fault counts as detected at the first post-onset sample that starts 3 flagged samples in a row (9 minutes).
Nothing was tuned on fault data; the bands are the shipped ones (K = 6). False alarms were measured on normal
running the bands never fitted on: the separate normal training run and the fault-free first 8 hours of all 21
fault runs, 193 plant hours in all.

| | Shipped bands | PCA T² baseline |
|---|---|---|
| Faults detected | **17 of 21** | 19 of 21, of which 3 are probably chance (below) |
| Median delay, detected faults | 48 min | 84 min |
| False alarms, held-out normal data | **0 in 193 h** (95% upper bound about 0.37 a day) | 5 in 216 h, 1.04% of samples flagged |

The bands miss faults 3, 9 and 15, which I had named as expected misses before scoring (the literature widely
reports them as near-invisible in these variables), and 19, which PCA misses too. Slow faults are late: fault 21 is
flagged after 26.5 hours. PCA T² is my own reimplementation (numpy, parallel analysis, F threshold), not a
literature number; I couldn't verify a published table's exact values from a primary source, so none is quoted.
Its "detections" of faults 3, 4 and 15 come after 18 to 34 hours with 2–8% of samples flagged, which is close to
its own false-alarm rate, so I count them as chance. On fault 4 the bands are clearly better (6 minutes, through
TI-109). Details: [EVALUATION.md section 4b](EVALUATION.md#4b-fault-detection-with-the-normal-bands-tennessee-eastman-all-21-faults).
The first tags to leave their band are reported per fault by tag. They don't depend on which unit a tag belongs
to, so the topology correction in entry 42 doesn't change them.

**Lost data is now an alarm, of its own kind.** Two expression tags count the fed values that are not Good, one
per data connection (52 replay values, 24 demo points). Each carries a "Data source lost" alarm. ISA-18.2 treats
this as a diagnostic, not a process alarm: it says the operator has lost sight of the process. So the header now
has three boxes: "Process alarms: N", a data-source box that turns dark slate and reads DATA SOURCE LOST, and
"Outside band". Process alarms now count each configured alarm once, so PI-107's two alarms count as two, which is
what the alarm table lists. Two choices here are mine alone and need operations: the diagnostic priority (Medium)
and the dark slate colour. Neither the setpoints nor any process alarm changed.

**"Not connected" and UNKNOWN now look the same everywhere.** Before, the same no-source agitator read NOT
CONNECTED in its table row and UNKNOWN in its label beside the reactor drawing, and a mapped drawing value with no data looked like a
normal white label. Now there are two states with one look each: *not connected* (no data source configured;
muted italic on white, dashed border) and *UNKNOWN* (a source is configured but nothing Good is arriving; muted on
grey). The rationale is ISA-101's intent, stated rather than quoted: one documented style in which an indication
means the same thing on every screen, quality never mistaken for a value, and alarm colours kept for alarms.
Exception, recorded in a test: two schematic labels with alarms keep their alarm colour binding, because a label has
one background.

**A narrow overview.** `/m` is a 390 px view: process alarm count, data source and band count first, then the active
alarm list, then the six units stacked in process order with the same key values as the overview, coloured the
same way. The control-room views are unchanged in layout and still 1600 px; the tiles link to them.

**Merged first.** Midway, the topology check (entry 42) moved the purge and its tags from the compressor to the
separator. I merged that branch before the gateway run and regenerated the provider, project and drawings instead of
merging generated files. The auto-merged provider would have been wrong: its new data-source expression still
pointed at the purge tags' old compressor paths.

**What the gateway found.** The first import held both data-source alarms active with a count of 0. Ignition's
AboveValue mode is inclusive (the 3,000 kPa shutdown alarm firing at exactly 3,000.0 had already shown that, and I
didn't apply it), so a setpoint of 0 meant "0 or more". The setpoint is now 0.5, with a test. Walking the screens
with the replay stopped showed every band indicator drawing its pointer at the scale minimum, which reads as a real
low value; it is now hidden without Good data. And the Alarms page still said "the only alarms are the published
ones", which stopped being true. All three were fixed before the final run of commit `4a00c35`.

| Check | Result |
|---|---|
| V1–V8 | PASS: 1,256 tag nodes and 24 views, 0 differences; 1,448 bindings; 76 Good, 335 Bad as designed; writes refused; PI-107 alarm 0.5 s after crossing |
| Routes and navigation | PASS: 24/24 load and reload; 284/284 clicks, Back after each, 0 console errors |
| Replay stopped / restarted | PASS: diagnostic fires, header DATA SOURCE LOST, 52 UNKNOWN; clears within about 25 s of restart |
| Demo points stopped / restarted | PASS: second diagnostic fires and clears |
| Header vs alarm table | 40/40 samples through the fault, 29/30 through a loss and recovery. The miss, and one capture, fell within about 2 s of an alarm changing state: the header polls every second, the table refreshes every two |
| Process alarm active when data is lost | Observed: PI-107's alarm stays active on its last value while PI-107 reads UNKNOWN. Ignition's default; whether stale data should hold, clear or suppress a process alarm is an operations decision |
| `/m` at 390 × 844 | PASS: no horizontal scroll, alarms first, honest UNKNOWN and DATA SOURCE LOST |

The `native-*.png` screenshots now show this build; entry 38's originals are in the history at `f5c270e`.
Receipt: [`native-current-20261013-alarms.json`](../out/ignition/gateway/receipts/native-current-20261013-alarms.json).
Afterwards I removed the containers, the volume, the network, both images and the build cache, and checked that
Docker held nothing. The rollback is in the receipt.

**What went wrong on the way.** Git Bash rewrote a route argument into a Windows path again, the same trap as entry
38: my alarm-count sampler asked the gateway for a project called `PIDTwinC:` for six minutes before I read the
gateway log. My scratch orchestration also had two path bugs that cost one stage-1 rerun. None reached the
committed tools; the sampler is now a `count` mode of the browser harness, added after the run.

**Not established:** real phones (headless Chromium only), operator usability, operations approval of the diagnostic
priority and of process-alarm behaviour on stale data, and anything beyond one simulated operating mode for the
fault evaluation.

**Lesson:** a detection claim needs a denominator and a false-alarm rate measured on data the method never saw,
and both numbers belong in the same sentence. The single fault was true and misleading. On the alarm side, a
quiet header is a claim too: "Alarms: 0" over a screen of UNKNOWN said nothing was wrong, when the truth was that
nothing could be known.

**At your plant:** score the band, or any detector, on every recorded upset you have, with the rule fixed first,
and measure false alarms over weeks of normal running before trusting the colour. Treat loss of a data source as a
diagnostic alarm with an owner and a response, separate from process alarms, and decide with operations what a
process alarm should do while its value is stale.

---

## 48. Give the drawings-only track the deliverables it can support

**What:** the OPEN100 track (12 real drawings, no process data) gets flow direction read from the drawings, the 12
sheets stitched into one plant, a process mimic, a 3D orientation tour and a LOTO isolation view. All of it is
structure. Where the drawings can't supply something, the README matrix says so and says what is missing.

**How:**
- **Direction first, because everything else draws arrows.** The twin's 1,881 connections all said "unknown", and
  the answer keys can't help: every graphml is undirected, and its `arrow` nodes have a position and no
  orientation. `scripts/flow_direction.py` re-traces each sheet with the same tracer and symbols, and checks that the
  links come out identical to the twin's (1,874 of 1,874). It then reads three kinds of evidence. Arrowheads: ink
  sticking out on both sides of a straight run, tapering to a tip. Off-page flags: which end of the pentagon is
  pointed, compared with where the line attaches. Pumps: discharge at the top of the casing. A fourth rule carries
  direction through in-line valves with exactly two connections.
- **The first version over-claimed, and the conflicts showed it.** At first an arrow oriented every symbol behind it
  against every symbol ahead of it. On a header with two outlets, that says outlet A flows to outlet B and back
  again: 380 conflicts, still 237 after instrument links were taken out. The fix split the evidence. "First-hand" means the arrow sits on the pipe between the two
  symbols, with no branch in between. "Across a branch" is the weaker reading. Two more rounds were needed before
  "no branch" meant what it says: instrument taps and arrowheads' own wings had made every pipe look branched, and
  so had three join points stacked on one corner.
- **Checking a direction with no key.** The detector's settings were chosen on sheets 0-5. On the held-out sheets
  6-11 it found 77% of the keys' arrow nodes, with 83% of its detections on one. For direction itself, 65 directed
  links (stratified, fixed seed) were cut out as crops with the two symbols outlined A and B, A picked at random.
  GPT (Codex CLI) and Claude (a fresh claude CLI session) read them blind. Neither disagreed with the code once. Each
  left some unclear, mostly across-a-branch links. Each link carries the lower end of the 95% interval as its
  confidence, not the 100%.
- **Two things the extraction never read.** The equipment schedules printed along the bottom of each sheet
  ("SERVICE: LETDOWN FILTER") say what each piece of equipment is for. Claude transcribed them, and 49 of the 74
  purpose cards come from them. Drawing numbers written with en dashes ("PID 110–1") had defeated the twin's
  connector pairing. Read as numbers, they let 31 more connectors find their sheet: 38 sheet-to-sheet connections
  instead of 7.
- **The screens reuse what exists.** The mimic is built from the TE screens' components and their "not connected"
  transform. The 3D tour uses the 3D branch's renderer, copied byte for byte in its own commit. The LOTO view numbers
  each isolation point on the real drawing.

**Why:**
- A twin without process data is still most of a starter kit. Steve put it plainly: the mimic and the tour don't
  need the data, so show what the two sets we have can do.
- Rejected: drawing every link with an arrow by guessing from layout (left to right, top to bottom). It would have
  looked complete and taught people to trust arrows nobody drew. Two-thirds of the process links stay undirected,
  and the screens show them dashed.
- Rejected: tank nozzle position as direction evidence (bottom inlets are common), and direction on instrument
  links (they carry signals, not flow).

**Lesson:** when there is no key, two independent readings agreeing is the next best evidence. Here it took three
forms: arrowheads and flags agreed on all 70 links where both spoke, two models read blind crops, and the
re-traced links had to match the twin before any direction was trusted. Conflicts are information too. 380 of
them said the rule was wrong, not that the drawings were.

**At your plant:** if you have the drawings and no historian access yet, build the model, the asset framework, the
mimic, the tour and the isolation view now, and add values when the data arrives. Read the equipment schedules on
your sheets. Keep arrows only where the drawing shows them. Treat the isolation list as a reviewer's checklist for
your energy-control procedure (OSHA 1910.147), never as the procedure: a valve the extraction missed is missing from
the list too.

---

## 49. Bring eight lines of work onto one branch, and make every output a stage

**2026-10-13.** Seven branches had been built side by side from the same starting commit, each finished and tested on
its own: the data-lineage spine (entry 45), the topology check (42), the generated TE P&ID (44),
the fault evaluation with the data-loss alarms (47), round 5 (46), the PI and review-kit work (43)
and the OPEN100 structural deliverables (48). The 3D tour (39-41) lived on an unpublished local
branch whose history could not be published. This entry is the merge.

**How:**
- **Real merges, in dependency order:** lineage first (everything else is a stage in it), then the topology check,
  the generated P&ID and the fault work (both already contained the topology check), round 5, the PI and review-kit
  work, and the OPEN100 structural branch last. No branch was rebased.
- **Generated files were never hand-merged.** Where a conflict was in an output (the TE tag export, the PI sheets,
  the reconciliation file), one side was taken and the file rebuilt with `pipeline.py rebuild`. Hand merges were
  only in source and documents.
- **Every branch's outputs became stages** in `pipeline/stages.json`: 39 stages over three datasets (DEXPI joined
  TE and OPEN100). Recorded stages (model calls, downloads) are accepted as the record, not re-run. The
  orchestrator learned two things on the way: a stage can need a Python package (`requires_modules`) or a local
  program named in an environment variable (`requires_env`, used as `$BLENDER_EXE` in the command), so no machine
  path is written into the manifest. 37 of 39 are fresh; the two that need a running Ignition gateway are listed as
  such.
- **The 3D tour came in without its history:** only its current source files were copied from the local branch's
  last commit, the review patch was applied to that copy, two files were replaced by scrubbed versions, and the
  public-hygiene check ran with the private terms supplied from the environment, never written down. Details:
  [drafts/3d-tour/REVIEW_NOTES.md](../drafts/3d-tour/REVIEW_NOTES.md), section 6.

**What the merge itself found** (none of it was a text conflict):
- **A demonstration became a fact.** The lineage test proved propagation by moving FI-110 from K-101 to V-101 on a
  temp copy. The topology check had made that move real, so the test's "before" control failed. The fixture now
  moves FI-105 instead, and says it is a fixture.
- **The same feature twice, under two names.** The P&ID branch and round 5 both added a setting that points the
  extraction scripts at another folder of sheets: `PID_SHEETS_DIR` and `PID_DATA_DIR`. Every script now reads one
  setting and accepts both names.
- **A hash that depended on the operating system.** The generated P&ID's manifest hashed raw bytes, so a Windows
  checkout (CRLF) and a Linux one disagreed about the same files. Text is now hashed with line endings normalised,
  as the orchestrator already did.
- **Two formats meeting.** The PI sheet v2 moved attribute descriptions out of the sheet, and the lineage branch had
  added each item's confidence to those descriptions. The merged exporter keeps both, the propagation test reads the
  v2 layout, and the 3D render verifier compares descriptions with the confidence suffix removed.
- **The accepted gateway build is still the accepted build.** Rebuilt from the merged source on Windows, the project
  ZIP is byte-identical to the one natively accepted (`8982ccd2…`), so the acceptance in entry 47 applies to it.
- **The first CI run after the push found one more.** On Linux the same build writes the same ZIP members, but the
  compressed bytes differ (another zlib build, and the archive records the OS that wrote it), so the orchestrator
  called the gateway stage stale. ZIPs are now hashed by their members. Rendered stills are the other
  non-reproducible output: Blender's renders can differ by a few grey levels between runs, so a rebuild may rewrite
  the JPEGs while the measured label boxes stay identical.
- **The tour's new font measured smaller.** Atkinson Hyperlegible at the old sizes drew labels of 14.9-16.6 px, under
  the 18 px minimum; sizes were scaled by 1.25 and the minimum kept. Rendering all twelve stills (not only the five
  that are committed) found one more defect: a stripper tag sat in the plane of a platform deck, hidden from every
  camera. Both tours share the renderer, so the OPEN100 stills were re-rendered too.

**Numbers, reconciled:** the holdout-A review load is now quoted from the round-5 replicates (GPT 20.1, Claude 29.8,
with run and drawing intervals). The round-2 figures (17.8 and 32.4 with the method, 48.8 for GPT alone) stay where
they are, labelled as the earlier single runs, because the decisions of round 2 were taken on them.

**Why:**
- Branches built in parallel each pass their own tests. What breaks at the merge is an assumption one branch made
  about another: that a correction had not happened yet, that a file format had not changed, that nobody else had
  added the same setting.
- Rebuilding instead of hand-merging outputs is what makes those visible. A hand-merged CSV would have hidden the
  description that moved columns.

**Lesson:** after a merge, rebuild from the source and read the test failures as findings about the merge, not as
noise. Most of what broke here was in tests, hashes and checks rather than product logic, and each would have
silently weakened a check if it had been "fixed" by loosening it.

**At your plant:** when pilot workstreams converge (drawing extraction, historian mapping, screens, a PI structure),
merge them through the same lineage: correct the source, rebuild everything downstream, never edit an output to make
two of them agree, and tie acceptance evidence to file hashes so you can tell whether it still applies after the
merge.

---

## 50. Find the control loops before drawing them: the generated P&ID draws none

**What:** 2026-10-28. The generated TE sheets (entry 44) draw every transmitter and every valve, but no controller and
no signal line. FI-102 sits beside FV-201 and nothing says one drives the other. A practitioner reads that as a
process flow diagram with bubbles on it, not a P&ID, and would be right. Before fixing the drawing, this entry finds
out what the loops actually are and measures how much of them the sheets show. The answer is none of them.

**How:**
- **Source:** `temain_mod.f`, the closed-loop code in the Braatz group's TE archive, the same archive the replay data
  comes from. The GitHub mirror's copy is byte-identical to the archive member (SHA-256 `31b83c17…`, checked
  2026-10-28), so `scripts/fetch_te_data.py` now fetches and verifies it with the other files.
- **Reading it:** `scripts/te_control_loops.py` takes each controller subroutine's error line
  (`ERRn = (SETPT(j) - XMEAS(m))`) for the measurement, and its update line for what it moves: a valve
  (`XMV(k) = XMV(k) + DXMV`) or another loop's setpoint (`SETPT(j) = SETPT(j) + DXMV`), which makes it a cascade.
  The `CALL` lines in the simulation loop give which controllers run and how often. The result is
  `data/te_control_loops.json`, named with the model's tags.
- **Comments ignored on purpose:** the file's comments were copied from one subroutine to the next. "Stripper Level
  Controller" sits on the purge loop and on the reactor cooling loop. Only the code is read.
- **Checked against the data:** that copy of the code is set up for a fault-12 run, so the code alone doesn't prove
  the published files used these loops. Every controlled variable in `d00_te.dat` sits on its coded setpoint: all 19
  within 0.34 standard deviations, 17 within 0.07. The two furthest off are steam flow and stripper temperature,
  inner loops whose setpoints a cascade moves. A negative control rotates the pairings by one place, and 18 of 19
  loops then miss by more than 3 standard deviations.
- **Drawing audit:** for each running loop, an answer key passes if it draws the measurement, a controller with
  matching letters (FIC for a flow), signal lines from measurement to controller and from controller to valve (or
  to the inner controller), and one loop number across all three. Process lines don't count as signals. The test
  file checks the grader before the score: it passes a correctly drawn loop and a cascade, and fails each mistake
  separately.

**What it found** ([`out/te_loop_audit.md`](../out/te_loop_audit.md)):
- **19 loops run:** 11 move a valve and 8 move another loop's setpoint. Three composition loops on the reactor feed
  analyzer trim the A, D and E feed flows. Purge composition trims purge flow. Reactor level trims the A and C feed.
  Reactor temperature trims the cooling water outlet temperature. Product composition trims stripper temperature,
  which trims steam flow. One more controller (separator pressure to purge) is defined but never called.
- **Production rate is set by condenser cooling water.** The stripper product flow loop moves the condenser
  cooling-water valve, not the product valve. The model tagged that valve TV-211, which says temperature control.
- **An override sits on the purge:** separator pressure at or above 2,950 kPa forces the purge fully open, at or
  below 2,300 kPa fully shut, and the controller gets it back when pressure returns to 2,633.7 kPa.
- **Score on the generated sheets: 0 of 19 loops.** Every measurement is drawn (19/19). No controller, no signal and
  no shared loop number (0/19 each).
- **The tags are wrong before anything is drawn.** All 11 valves carry a different loop number from the measurement
  that drives them (FV-201 is moved by FI-102's loop). Two carry the wrong letter: HV-205 (a hand valve on a flow
  loop) and TV-211 (a temperature valve on a flow loop).

**Why:**
- **Measure, then fix.** Drawing controllers without the table would have meant guessing pairings from tag numbers,
  which is how the wrong pairings got there in the first place.
- **The data check is the independent witness.** The code and the drawing share an author's interpretation; the
  recorded run doesn't.
- **Rejected:** fixing the tag numbers in this entry. They run through the Ignition project, the PI sheet, both tours
  and the replay mapping (about 1,300 references), so renumbering is a separate, regenerated change.

**Lesson:** a drawing that shows every instrument can still miss the reason they're there. Count what the sheet says
about control, not what it says about equipment.

**At your plant:** the control narrative is in the DCS configuration, not the drawing. Export the controller list
(PV, OP or cascade target, mode) and audit your P&IDs against it the same way: every loop needs a controller, signal
lines and one loop number. Drawings where indicators sit next to valves with different numbers are the ones to walk
down first.

---

## 51. Draw the control loops, and give each valve its loop's number

**What:** 2026-10-28. Revision B of the generated TE sheets draws all 19 control loops that entry 50 read out of the
closed-loop code, and every control valve now carries the number of the loop that moves it. The loop audit goes from
0 of 19 to 19 of 19. Revision A stays in the repository, because the recorded extraction runs read it.

**How:**
- **Controllers belong to the model.** `scripts/te_control_loops.py --write-model` adds a `controllers` list to
  `data/te_process_model.json`: tag, loop, what it reads, what it moves (a valve, or another controller's setpoint),
  mode, scan period, and the source lines and recorded-data deviation as evidence. Tags follow ISA-5.1: FIC-101 reads
  FI-101. The analyzer that feeds three loops gets component suffixes (AIC-123A, AIC-123D, AIC-123E).
- **One mapping renames the valves.** `scripts/retag_te_valves.py` applies `data/te_retag_2026-10-28.json` to the
  source files that name tags (126 replacements in 16 files: the model, layouts, tour cards, hazard citations, HMI
  unit lists, tests, current-state docs). It refuses a mapping that isn't one-to-one or that would chain. Each renamed
  valve keeps `former_tag`. HV-205 became FV-105 and TV-211 became FV-117: both sit on flow loops. Outputs were rebuilt
  by `scripts/pipeline.py`, never edited.
- **The generator draws what the model says.** Controllers are drawn as DCS functions (a circle in a square, with
  the operator-visible line), joined by dashed signal lines; the two loops that cross sheets (reactor level to the
  A and C feed, stripper product flow to condenser cooling water) end in signal continuation flags naming the other
  sheet, the grid zone and the far end. The layout only gives positions and corner points. The generator refuses a
  controller placed twice or not at all, a model signal not drawn, a signal the model doesn't have, a diagonal
  segment, and a signal line through any symbol or vessel. The first full layout drew clean; the refusal tests break
  it on purpose.
- **Signals stay out of the scored graph.** The frozen scorer counts every edge in a key's graph file regardless of
  its label, and the line tracer follows solid lines only. Putting signal lines there failed the tracer check (18
  untraced links on sheet 101 alone) and would have changed what the round-trip connection score means. Signal lines live in `key.json` as
  `signal_edges` and are scored by the loop audit; the graph file keeps process lines, as the OPEN100 keys do.
  Controllers are in it as symbols, because they are on the drawing.
- **Revision A is kept as evidence.** The recorded extraction, round-trip and twin stages read the 2026-10-13
  sheets. Those sheets are archived in `data/te_pid/rev-a/`, byte-identical to the hashes the lock recorded when the
  runs were made, and a source stage (`te.pid_rev_a`) owns them. The reviewer diff joins old extractions through
  `former_tag`, so all five diffs keep their correction counts (9, 10, 11, 47, 54) and note each valve as "read as
  FV-201, its revision-A tag".
- **Everything downstream rebuilt:** Ignition project, PI sheet, SVGs, mimic, scene, bands, fault detection, both
  tours (the Blender stills re-rendered; the render verifier passes 15 and reports 2 informational, as before) and the
  style check. 40 of 42 pipeline stages are fresh; the two that aren't need a running gateway.

**What it found:**
- **Style fidelity dropped from 32 to 30 of 36.** The instrument share per sheet (0.55 to 0.61) is now above every
  OPEN100 sheet (at most 0.54): the drawing gained 19 controllers but still has none of the block valves, bypasses,
  drains and vents that surround a control valve on a real P&ID. Ink coverage moved into range.
- **The model already knew the answer.** Every pairing was in the code; only the numbering hid it. Once tags follow
  loops, a reader can check a loop by eye: FI-117, FIC-117, FV-117.

**Why:**
- **Rename at the source, rebuild the rest.** Hand-editing about 1,300 references across exports would have left
  some behind; the pipeline found the ones the rename tool didn't own (a sorted list and a spoken "T V 210" in the 3D
  tests).
- **Keep the old evidence honest.** Re-pointing recorded runs at new sheets would have called stale evidence fresh.
  Archiving the exact bytes they read keeps their numbers true and says what they describe.
- **Rejected:** renaming the transmitters to FT (purists draw FT under an FIC). The I letters are the replay points'
  names everywhere; the loop audit and a reader both get the loop from the shared number. Also rejected: drawing the
  purge override from PI-113 as a signal. The code implements it as a latched trip with a hand-back inside the purge
  controller; drawing it properly needs a selector symbol and a cause-and-effect note, not a dashed line.

**Native acceptance, the same evening:** the rebuilt project went into the local disposable gateway with
`build_gateway.py --fresh` (1,121 tags, 0 failures, 0 read-back differences). The verifier caught 5/5 planted faults
and passed V1–V9 on `c15b362`; the browser contract passed 24/24 routes and 284/284 clicks with no console errors;
stopping the replay raised the data-source-lost diagnostic and restarting it cleared it, with the header's count
matching the alarm table in all 24 samples ([receipt](../out/ignition/gateway/receipts/native-revB-20261028.json)).
One snag: Git Bash rewrote the browser contract's route arguments (`/unit/U-100`) into Windows paths;
`MSYS_NO_PATHCONV=1` fixed it.

**Not done here:** the revision-B sheets haven't been read back by the models (a paid, recorded run), the 3D OCR
read-back still describes the old stills, and no control engineer has reviewed the loops. The audit grades the drawing against the code; it doesn't judge the control
strategy.

**Lesson:** a loop table is cheap to read and expensive to guess. Once the drawing came from the table, the drawing,
the tags and every export agreed by construction.

**At your plant:** number control valves by the loop that moves them and draw the controller even when it lives in the
DCS. When you renumber, do it from one mapping table at the source, keep the old tag on each item, and leave dated
evidence pointing at the drawing revision it was made from.

---

## 52. Put each control valve in a station: block valves and a bypass

**What:** 2026-10-28, later the same day. Revision C of the generated TE sheets draws a control valve station around
every inline control valve: a manual block valve on each side and a bypass with a hand-operated globe valve. That is
how a real P&ID draws a control valve, so it can be isolated and pulled while the line runs on the bypass. Style
fidelity goes from 30 to 35 of 36 OPEN100 measurements.

**How:**
- **A layout switch, not model content.** The model holds no manual valves, so the stations are drafting additions:
  `control_valve_stations` in the layout turns them on, and each block and bypass valve is in the key with
  `drafting_addition` set and no model reference. A route opts out with `"station": false` and must give a
  `station_reason`. The compressor's spill-back valve (FV-105) does: it sits inside its own recycle loop.
- **Refuse rather than squeeze.** A station needs a straight run 80 px either side of its valve with nothing else in
  it, and its bypass must clear every symbol. The generator refuses otherwise. The first try failed on paper before
  any code ran: at a 60 px offset, the feed-line bypasses ran through the flow controllers between the feed lines. The
  bypass offset became 45 px and the three feed lines moved apart (330, 590, 850).
- **The pixels still agree with the key.** The bypass joins the line at two tees, so the key's process links change.
  The code line tracer, given only the symbol boxes and the image, recovered every key link on all three sheets,
  bypasses included. New tests check one station per inline control valve, the crowded-station refusal and the
  opt-out reason.
- Revision C, because revision B was already on the public main branch. The loop audit still reads 19 of 19, and
  every downstream stage was rebuilt (42 of 42 fresh).

**What it found:** the remaining style miss is sheet 103's symbol count (37 against an OPEN100 minimum of 40). Real
sheets also carry drains, vents, reducers and line breaks that a process model doesn't hold.

**Why:**
- **A reviewer's first question.** A practitioner looking at a control valve with no block valves sees a drawing
  nobody checked. This is the cheapest fix that answers it honestly, because it's a convention, not process data.
- **Rejected:** adding drains and vents the same way. Where they go depends on line routing and low and high points
  that the model doesn't hold, so placing them would be decoration rather than a convention.

**Lesson:** separate what the process says from what the drafting convention says, and label which is which in the
key. Then a convention can be added everywhere at once without anyone mistaking it for plant data.

**At your plant:** when you generate drawings, apply your drafting standard's conventions (valve stations, spec
breaks, vents and drains at the high and low points your routing defines) as declared rules, not hand edits, and walk
the result down before anyone treats it as a drawing of record.

---

## 53. Carry the October 15 tour review onto the renumbered build

**What:** 2026-10-28. A review of the draft 3D and browser tours on October 15 found confusing callouts on the
separator and compressor, no proper overhead corridor for the recycle, an S-bend, and no cutaway into the feed header
or compressor. Those corrections were made in a separate working copy on the old main branch and never merged. They
are now applied on top of revision C's tags.

**How:**
- Only the source changes were carried over (the tour builders, the browser tour's code, styles and verifier, the
  Blender template and the 3D scene builder, their tests and READMEs, plus a new geometry test). They were taken as a
  patch against the old base and applied with a three-way merge. Every output (pages, stills, audits, label boxes)
  was then rebuilt by the pipeline, not copied, so it carries the new valve tags.
- One conflict, in the 3D tour README: both the October 15 review and the renumbering had rewritten the same
  paragraph. The merged text keeps both. The tour stage now publishes the eight review stills, not five.
- The 3D scene builder is shared with the OPEN100 structure-only scene, so that scene was re-rendered too.

**Result:** the browser tour's verifier passes 38 checks with 5 informational and none failing; the 3D render verifier
fails none; the new geometry test passes; all 42 pipeline stages are fresh. The impeller, rack dimensions and LOTO
locations remain illustrative placeholders, and the stills still need the owner's approval before any video.

**Lesson:** corrections made outside the main line are a liability until they're merged. Carry the source, not the
outputs, and let the pipeline rebuild.

---

## 54. Read revision C back with the same method

**What:** 2026-10-28. The project owner approved paying for the model read-back of the revised drawings. Revision C
(controllers, signal lines, valve stations) was read with exactly the protocol of entry 44: 2×2 tiles, prompt v2, the
line tracer, 5 clean runs and 3 per degraded level per model.

**How:** `scripts/run_te_roundtrip.py` runs every condition and replicate, labelled `tec-*` so revision C's runs never
mix with revision A's `te-*`, and skips anything already done so it can resume. The scorer gained `--keys`,
`--prefix` and `--out`, so each revision is scored against its own sheets. That also exposed a gap from revision B:
the recorded revision-A scoring command had no way to name its keys, and the default folder now holds revision C. Its
recorded command now names `data/te_pid/rev-a`. The revision-A scores themselves were not re-run (their run records
aren't on this machine); they are unchanged.

**What it found (GPT, gpt-6.1-sol through the Codex CLI, and Claude, claude-opus-5-5 through the Claude Code CLI;
42 sheet runs each, no failed tile):**

| Image | GPT, revision A | GPT, revision C | Claude, revision A | Claude, revision C |
|---|---|---|---|---|
| Clean | 2.1 per 100, 100% of tags | 1.26, 100% | 2.2, 100% | 1.38, 100% |
| L1 photocopy | 2.1, 100% | 1.30, 100% | 8.0, 98% | 4.1, 100% |
| L2 old scan | 2.1, 56% | 1.20, 61% | 13.4, 95% | 10.0, 89% |
| L3 bad scan | 16.9, 14% | 14.9, 9% | 17.3, 49% | 15.7, 50% |

- **More symbols didn't make the drawing harder to read.** Revision C has 19 controllers, 30 manual valves and more
  tags, and the clean review load fell. Part of that is denominator: more key items, about as many corrections.
- **Tag text is still what fails on bad scans,** and slightly worse at L3. The controller symbols' smaller text
  (letters above a line, number below) goes first: at L2, 51% of controller tags were misread against 34% of the
  others; at L3, all of them against 87%. A drafting choice (text size inside the DCS symbol) costs readability on
  poor copies.
- **Claude reads tags far better on poor copies** (89% against 61% at L2, 50% against 9% at L3), and its
  controller tags hold up better too (missed at L2: 21% against 7% for other tags; GPT 51% against 34%). One habit
  shows: 13 of its misses read an FI bubble as FT, a transmitter tag, the letters it expects rather than the ones
  printed.
- **Claude's higher review load at L1 and L2 is not worse reading. It comes from the line tracer.** Its connections
  fall to 0.93 at L2 while every symbol is found, with about 30 extra links per run, all whole networks merged into
  one: everything on the reactor wall linked to everything else. Claude's equipment boxes stay tight on degraded
  scans (median vessel box 20,708 px² against GPT's 21,859), sitting just inside the drawn wall, so the tracer
  follows the wall as if it were a pipe. Growing only the equipment boxes by 4 px removes every extra link (sheet
  101: 0.93 to 0.99; sheet 103: 0.86 to 1.00) and changes nothing for GPT. The revision-A Claude scores at L1 and L2
  (8.0 and 13.4) look like the same cause; those run records aren't on this machine, so that is unverified.
- **The scores above stay as measured.** The method is frozen; the tracer fix (pad equipment boxes by the outline
  width before tracing) is a method change, to be measured on every result it would touch, not slipped into this
  one.

**Lesson:** when two models differ on a score that neither model produces (here, connections come from code), look
for the interaction before ranking the models. The difference was in my tracer's assumption about box size.

**At your plant:** when a drawing standard changes (new symbols, new tags), re-measure your extraction method on the
new drawings with the same protocol, and keep the old results tied to the old drawings rather than overwriting them.

---

## 55. Start the real unit: a sourced model and a checked trend

**What:** 2026-10-28. The owner chose the Bayer CropScience residue treater (docs/REAL_UNIT_SELECTION.md). Two pieces
are built: a process model that cites the CSB report for every item, and a digitization of the report's DCS trend
(Figure 11) checked against the report's own text. Details: [BAYER_RT.md](BAYER_RT.md).

**How:**
- **The model** follows Figure 10 and pp. 27-32 and 38-40: units, streams, instruments, valves, the two controllers
  the report describes, three interlocks, limits and the timeline. The report gives no tag numbers, so every tag is
  assigned and marked so. Findings sit on the items they concern: the bypassed minimum-temperature interlock (p. 69),
  the steam block valve found closed (p. 70), the mis-programmed split range (p. 39).
- **The trend** is read from the figure's pixels. Calibration uses only the figure's tick marks and gridlines; the
  figure's dotted failure line then lands 0.1 minutes from 22:33 before any curve is read. Eleven values stated in
  the text and labels are checks, never calibration inputs.
- **Research claims were checked against the PDF before use.** A research pass said "8 injured". The report says six
  volunteer firefighters and two contractors were treated for possible toxic exposure, so the model and the selection
  memo now say that.

**What it found:** 6 of 11 checks passed on the first run. Two failures were my own bugs (the flow classifier caught
the red trace's anti-aliased edge; one check used the wrong time window) and were fixed. The other three are real
disagreements between the figure and the text: the figure's steady pressure is about 25 psig where the text says 22,
and its temperature runs about 2 °C below the text's values near the end. The pressure scale is confirmed by the two
labelled pressures, which both agree, so the replay will use the figure and state the difference.

**Why:**
- **A trend digitized without checks is a drawing of a drawing.** The report's own numbers are the only independent
  reference available, so they test the digitizer instead of tuning it.
- **Rejected:** shifting the pressure calibration by 3 psig to match the text. Two labelled pressures on the same axis
  agree with the figure as calibrated; moving the axis would break them to hide a disagreement in the source.

**Lesson:** when two parts of one source disagree, record both and say which the twin uses. Picking the convenient
one silently is how a replay gains false precision.

**At your plant:** historian exports carry tag names and units, but screenshots of trends in incident reports,
shift logs and old studies don't. When you digitize them, calibrate on the axes, test against every number written
down elsewhere, and keep the error with every value.

## 56. Draw the real unit and check it against the report's own drawing

**What:** 2026-10-28. The residue treater model was checked against the CSB report's Figure 10, a piping layout drawn
by someone else, then drawn by the same generator as the Tennessee Eastman sheets and checked against that figure
again. Details: [BAYER_RT.md](BAYER_RT.md).

**How:**
- **The figure, written down first.** `data/bayer_rt/fig10_inventory.json` records every unit, terminal, line and
  item Figure 10 shows, read from the figure alone. The figure has no tags, so `scripts/compare_bayer_fig10.py`
  checks at the level it is drawn: each line's two ends, and the types and numbers of items on it.
- **The generator grew to fit a real unit:** the model's hand valves and relief valves, a split-range controller
  with three outputs, and interlocks as ISA diamonds with their signal lines, all refused if dropped or duplicated.
  The TE sheets came out byte-identical.
- **The drawing checked twice:** every figure line traced end to end through the drawn sheet's answer key, and the
  pixel line tracer run on the sheet to confirm it reads back exactly the key's connections.

**What it found:**
- **The model, written from the text, got the figure wrong in four places** (first run 10 of 21; 11 of 21 after one
  bug in my checker): the flow transmitter on the wrong line, the discharge off the vessel instead of off the
  return, the two exchanger outlets returning separately, and the utility outlets and the condenser relief line
  missing. All corrected from the figure, each noted on the item: 20 of 21. The one left is a nozzle whose purpose
  the report doesn't state.
- **The drawing agrees with the figure on 15 of 15 lines.**
- **The first layout had three line crossings, and the tracer read each as a junction.** The two parallel exchanger
  legs make the loop non-planar with every terminal at the sheet edge, so the cooler's water connections now end
  in flags beside the exchanger. The tracer then read back exactly the key.
- **The report gives the project a real tie to the incident**, in its own findings: a new control system,
  operators not trained on it, overview screens they asked for that weren't ready for the startup (p. 60), control
  logic not checked before the restart (pp. 35, 38, 39), and a steam flow indication that was wrong (p. 71). That is
  the motivation the series uses, cited by page. The casualties are stated once and nobody is named.

**Why:**
- **Text describes, drawings connect.** The report's prose says what each item does; only the figure says where it
  sits. Every topology error came from writing the model from prose.
- **Rejected:** adding control valve stations to match the TE sheets. Figure 10 draws none and the report doesn't
  describe any; adding them would be drafting the record doesn't support.
- **Rejected:** keeping the crossings and teaching the tracer to skip them. That would change the tracer the TE
  scores were measured with, and a model reading the sheet would still misread them.

**Lesson:** check a model built from a narrative against any drawing of the same thing before using it, even a
simplified one. Half of the first checks failed, all on connections.

**At your plant:** the same split exists between operating procedures and the P&ID. Procedures say what a valve is
for; the P&ID says what line it's on. Check one against the other, item by item, before trusting either.

## 57. Replay the evening through the interlocks

**What:** 2026-10-29. The digitized Figure 11 trend replayed through the residue treater model's three interlocks and
four operating limits, column by column up to the failure, and checked against what the report says happened.
Details: [BAYER_RT.md](BAYER_RT.md).

**How:**
- **Rules as cited data.** `data/bayer_rt/replay_rules.json` states each interlock and limit with the pages behind
  it. The report publishes no interlock setpoints, so each rule carries the bounds the report supports, and a state
  between them is "cannot tell".
- **Bounds, not points.** Every value carries its column range widened by the digitizing error; a condition is met
  or clear only when the whole bound is on one side.
- **The report's account as the check:** five statements about the evening (pump start, flow loss, the
  high-pressure alarm, the relief valve, the safe operating limit), each turned into a test of the derived states.

**What it found:**
- **A digitizer bug first.** The level series had 39 one-column spikes: the blue fringes of the figure's black text
  labels, picked up because the level mask had no minimum component size. Fixed (components of at least 15 px, the
  middle of the clean 10-20 px range), with a test against any one-column spike. The 11 text checks never sampled
  those minutes, which is why they passed with the bug.
- **5 of 5 statements agree,** within two minutes where the statement gives a time.
- **The minimum-temperature condition was met for the first three and a half hours shown,** until about 21:25. The
  report says that interlock was bypassed (p. 69) and the feed had been open since about 4 a.m. (p. 38). (Corrected
  2026-10-29: an earlier wording here said what the interlock "would have" done, an outcome claim this project
  doesn't make; entry 60.)
- **The figure shows two short flow starts after the pump started,** each falling back to zero, before flow was
  established at about 18:25. The report doesn't mention them; the replay records them as the figure shows them.

**Why:**
- **Rejected: picking a setpoint.** 135 C or 50 psig would make every state crisp and some of them wrong in ways
  nobody could see. "Cannot tell" between two cited bounds is the honest output.
- **Not a blind test.** I wrote the rules after looking at the digitized values, so 5 of 5 shows the replay is
  consistent with the report, not that it predicts it.

**Lesson:** a downstream consumer is a test of its input. The replay read every column; the text checks read eleven.
The bug sat in the minutes nobody sampled.

**At your plant:** when you rebuild an event from a trend, publish the bounds and say when a state can't be told.
A timeline that is crisp everywhere has usually guessed somewhere.

## 58. An overview screen for the unit

**What:** 2026-10-29. A generated overview screen of the residue treater, replaying the evening: the kind of screen
the operators asked for and didn't have at the startup (report p. 60). Proof of concept, at
`drafts/bayer-overview/index.html`. Details: [BAYER_RT.md](BAYER_RT.md).

**How:** `scripts/build_bayer_overview.py` writes one self-contained page from the P&ID layout (geometry), the model
(items and tags) and the replay (values, bounds, states). `drafts/bayer-overview/verify.mjs` checks it in headless
Chrome against `replay.csv`, read independently of the page.

**What it found:**
- **Every check passed on the first build, and the page was unusable.** Mimic text came out about 6 px on a desktop,
  and a phone had no readable values anywhere. The checks covered data and layout, not legibility of the drawing.
  Looking at the screens found it; the fix was a "Values now" card that comes first on a phone, larger mimic text,
  and a check that mimic text is at least 11 px on desktop.
- **The "critical decomposition temperature" is also the normal operating temperature** (p. 30). Shown as a crossed
  limit in amber, it would flag normal operation as abnormal, the alarm habit high-performance HMI guidance warns
  against. It is now marked informational in the rules and shown without colour.
- **All 519 rows on the page match the replay file,** and the failure note appears at the last row only.

**Why:**
- **Rejected: a live Ignition screen first.** The project's gateway path exists for TE, but this replay is 519
  points from a figure, not a running process; a static page shows the same states with less to go wrong, and the
  gateway version can follow if the series wants it.
- **Rejected: colouring every interlock that would act.** "Met" is amber because the feed valve should then be
  closed and isn't; "cannot tell" is a dashed outline, so an unknown never looks like an alarm or an all-clear.

**Lesson:** a page that passes every check can still fail the person reading it. Look at it at the sizes people
use, then make what you saw into a check.

**At your plant:** before you trust an overview screen, ask what it shows when a value is uncertain, and whether
anything coloured as abnormal is actually normal operation.

## 59. Walk the report's timeline beside the screen

**What:** 2026-10-29. The six events the report times on the evening (pp. 38-40), each paired with the replayed
overview screen at that moment and with the checks that test it. On the overview page, below the screen; details in
[BAYER_RT.md](BAYER_RT.md).

**How:** `scripts/bayer_walkthrough.py` derives nothing new. A small data file names which checks test which event;
the script places every existing check (11 figure against text, 5 report statements) under exactly one event and
fails if one is missing or doubled. The digitizer now also writes its checks as JSON, so nothing parses markdown.

**What it found:**
- **13 of 16 checks agree; no report statement disagrees with the replay.** The 3 that don't are the
  figure-against-text disagreements from entry 56, now shown at the moment they apply.
- **The report times 3 of the replay's 20 state changes.** The other 17 are listed, not hidden: the two short flow
  starts, the minimum-temperature condition leaving "met" at 21:26, and the pressure condition's brief "cannot tell"
  around the pump start.
- **My own plan's wording was wrong.** It said every derived state would match the report or be a disagreement. Most
  derived changes are neither: the report just doesn't time them. They get their own list.

**Why:**
- **Rejected: a second page.** The timeline already sat under the screen; making it the walk-through kept one page,
  one data source and one verifier.
- **Rejected: nearest event by eye.** Each event shows the replayed column nearest its time, worked out again by the
  verifier from the CSV; the 18:14 event lands on 18:13:54, before the pump start registers, and the page shows the screen time beside the event.

**Lesson:** put every check you already have in the order a reader meets the story, and count what's left over. The
leftover list is where the next question is.

**At your plant:** when an incident timeline is rebuilt from trends, ask for two lists: where the trend and the
written account disagree, and what the trend shows that the account never mentions.

## 60. Let two hostile reviewers read it before anyone else does

**What:** 2026-10-29. Before the project is linked from a public post series, two independent reviewers, a Claude
panel and a Codex (GPT) reviewer, each read the repository and the draft posts cold, playing the commenters a post
like this gets: a controls engineer, a process-safety specialist, an HMI practitioner, an evaluation skeptic, a
hiring manager and the general snark. Every finding was checked against the files before anything changed.

**What it found, and what changed:**
- **An outcome claim I said I'd never make.** BAYER_RT.md and entry 57 said the bypassed minimum-temperature
  interlock "would have held the feed closed" for three and a half hours. That is a counterfactual about the night,
  and the same document says the project makes none. Both now state the condition and the report's facts only; the
  overview's badge says "condition true" instead of "would hold feed closed".
- **A finding listed as a cause that the report says wasn't one.** The split-range programming fault was cited among
  the reasons this unit belongs here; the CSB concluded it was not causal (p. 39, footnote 29). Now said where it's
  cited, and the opening sentence no longer says the report "ties the incident" to control-system findings.
- **Indicators where the figure shows transmitters.** The Bayer field instruments were tagged PI, LI, FI and TI, which
  an ISA-5.1 reader takes for local gauges, while Figure 10 calls them transmitters and two of them feed controllers.
  Retagged PT, LT, FT, TT with `former_tag` kept; the drawing is revision B; every Bayer output rebuilt, all checks
  unchanged (Figure 10 20 of 21 and 15 of 15; walk-through 13 of 16). The TE sheets have the same convention issue
  (an indicator bubble feeding a controller); that retag touches the gateway and the recorded runs, so it is a
  separate decision.
- **README overclaims.** "Sealed drawings nobody tuned on": holdout A chose each tool's method, and round-1 outputs had
  been seen for all twelve sheets, so its numbers are selection numbers. "Every result is repeated": rounds 2 and 4
  were single runs. "19 of 19 loops": the audit reads the key the generator writes, so it's a regression check, not
  evidence a model can read loops off a sheet. "Review load" was described as a reviewer's corrections; it counts
  differences from the answer key, and no review has been timed. Each is now said plainly.
- **Stale facts.** The README's loop row still said revision C hadn't been read back; the revision C scores now have
  their own table beside revision A's; the Bayer work is counted as its own evidence track; "8 of 11 within the pixel
  error" is "within each check's tolerance"; the "5 of 5" report checks are described as five limited consistency
  checks, two of them proxies.
- **Valve stations as a universal rule.** They are a drafting assumption the TE model doesn't contain, and the style
  score measures resemblance to OPEN100, not engineering quality. Now said.

**Why:**
- **Rejected: answering the critiques in posts instead of fixing the repo.** A commenter reads the linked file, not the
  reply.
- **Rejected: one reviewer.** The two overlapped on the biggest points (the counterfactual, the circular 19 of 19) and
  each found things the other didn't: the Claude panel the transmitter tags and stale screenshots, the Codex reviewer
  the non-causal footnote and the holdout-selection history.
- **Stale screenshots.** The README's two overview screenshots predated the valve renumbering and showed two
  retired tags (HV-205, TV-211). They are replaced by revision B captures from the local test gateway: the normal
  overview from the 2026-10-28 acceptance run, and the fault-6 overview captured 2026-10-29 from the same build, with
  reactor pressure past its alarm. The old images stay for the documents that describe the 2026-10-13 run.

**Lesson:** the same document can state a rule and break it a hundred lines later. A reader looking for the break finds
it in minutes; the author, reading for flow, doesn't.

**At your plant:** before a model, a drawing or a screen goes to the people who'll use it, give it to someone whose job
is to find what's wrong with it, and fix what they find in the artifact, not in the cover note.


---

## 61. Tag the TE transmitters as transmitters, and let a stranger's agent check the README

**What:** 2026-10-29. Every TE measurement is now a field transmitter (FT, PT, LT, TT, AT, JT) read by its
controller: FT-101 feeds FIC-101. The generated sheets are revision D. Entry 51 rejected this rename; entry 60's
reviewers made the case for it (an indicator bubble feeding a controller is the first comment a controls engineer
leaves), and the Bayer drawing had already been retagged the same way. Separately, `scripts/check_claims.py` compares
each headline number in the README with the committed file it comes from, and `AGENTS.md` tells a reader's coding
agent to run it.

**How:**
- **The same tool, one more mapping.** `scripts/retag_te_valves.py` now takes `--mapping`;
  `data/te_retag_2026-10-29.json` renames the 25 measurement tags (639 replacements in 49 source files). Instruments
  now keep `former_tag` too, and an item renamed twice keeps the tag it had just before this rename (the valves keep
  their revision-A numbers). Outputs were rebuilt by the pipeline, not edited.
- **Revision C is archived.** Its sheets moved to `data/te_pid/rev-c/` (a new source stage, `te.pid_rev_c`),
  byte-identical to what the revision C read-back stages hashed when they ran; those stages now point there, and
  `run_te_roundtrip.py` takes `--sheets` so a future run names the revision it reads.
- **Old evidence still joins.** The reviewer diffs keep their correction counts (9, 10, 11, 47, 54) through
  `former_tag`. The live check now does the same: 36 of 36 and 16 of 16 extracted tags reach a moving replay point,
  as before.

**What it found:**
- **The live check had been stale since entry 51 without saying so.** Its committed output still showed the old valve
  numbers as replay points, because the stage didn't list the process model as an input: the replay server reads the
  model, but the pipeline couldn't see that. It does now, and the check joins renamed tags explicitly.
- **A text rename can't see code that tests a prefix.** Four places picked tags by their letters (level bands by
  `LI-`, analyzers by `AI-`): after the rename they would have matched nothing and said nothing. The 3D render
  verifier caught one (16 analyzer channels suddenly "unexplained"); a search for `startswith` found the rest. All
  follow the new letters.
- **The published tour pages were a hand copy.** `drafts/interactive-tour/page/` kept the old tags because the stage
  wrote to `out/` and nothing copied it over. The copy is now a step of the stage, and the pages are its outputs.
- **The README's headline F1 was one run's best metric.** "Symbols F1 0.97, connections 0.89" came from the single
  round-2 run (symbols located, class ignored) and sat beside a five-run review load. The five-run means are 0.93
  and 0.87; the README and the deliverables table now say those. The claim checker found it on its first run.
- **7 streams disagree on their tier.** The review queue puts them in amber; the plant model's per-item rollup says
  "n/a", so the pipeline's summary line reads 669 amber against the README's 676. The README matches the queue a
  reviewer works from. Not fixed here.

**Why:**
- **A checker, not another document.** The reviewers' strongest findings were drift: numbers and screenshots that
  stopped matching their sources. `check_claims.py` makes that a test (it runs in CI), and it's what a skeptical
  reader's agent can run in under a minute without trusting the prose. Claims no result file holds are listed as
  "prose only" instead of passing quietly (one: Figure 10's first run, 10 of 21).
- **AGENTS.md asks for nothing on the author's behalf.** It lists the checks and the limits to report, and asks the
  agent to tell its user what fails. A file that steered an agent's verdict would deserve to be ignored.
- **Rejected:** keeping indicator letters for the replay points' names (entry 51's reason). The HMI shows whatever
  the tag is called; there was no reason for the field device's tag to be wrong to keep a display name.

**Native acceptance, the same day:** the revision D project went into the local disposable gateway with
`build_gateway.py --fresh` (1,121 tags, 0 failures, 0 read-back differences). The verifier caught 5/5 planted faults
and passed V1–V9 on `1b9e815`; the browser contract passed 24/24 routes and 284/284 clicks with no console errors; the
header's alarm count matched the alarm table running, stopped and restarted (4/4, 8/8, 12/12). This time fault 6 was
also watched on screen: PT-107 red at 3,000 kPa g, two alarms in both the header and the table. The README's
overview screenshots are from this run ([receipt](../out/ignition/gateway/receipts/native-revD-20261029.json)).
Not read back by the models yet: revision D is a tag-letter change on the sheets revision C's runs already read.

**Lesson:** a pipeline is only as honest as its list of inputs. Two outputs went stale here without anything turning
red, and both times the missing piece was a dependency the code had and the manifest didn't.

**At your plant:** when you retag, search the code for logic that keys on tag letters (alarm grouping, display
filters, historian queries), not just for the tags themselves. A rename tool finds names; it can't find a rule.

---

## 62. Give a stranger's agent the repository and see what it can do

**What:** 2026-10-29. A fresh agent with no context got a clean clone of public main and the brief of another
engineer's coding agent: "can I use this on our own P&IDs to get a starting asset model into Ignition?" It worked
offline, read the agent-facing files, ran what it could and reported where it got stuck. Its findings, checked
against the files, drove this change: a runbook for one drawing, `examples/own-drawing/`, that runs end to end from
a clean clone.

**What it found (each confirmed before changing anything):**
- **No extraction to start from.** The intake tool wanted "an existing extraction", and a clean clone has none
  (model run records aren't committed). The agent had to hand-write one. The example now ships the recorded GPT
  extraction of public sheet 0, made with the method behind the results, and a manifest pointing at the sheet
  already in the repository: two commands give a 445-row review bundle with Ignition tags and PI staging files.
- **A tool listed for your drawings that isn't one.** The README put `build_gateway.py` under "tools for your own
  drawings"; it builds this repository's Tennessee Eastman demo. The Ignition step is now importing the bundle's
  `ignition/tags.json` in Designer, and `build_gateway.py` is listed with the research record.
- **Stale numbers in the file written for agents.** AGENTS.md still quoted the single-run F1 (0.97, 0.89) that
  entry 61 corrected in the README; the claim checker only reads the README. AGENTS.md now names the claims without
  numbers, so there is nothing there to drift. It also said Python 3.11+; the README and CI say 3.10+.
- **Passing tests that print FAIL.** The claim checker's deliberate-failure control printed its table into the
  log. It is now captured and asserted instead.

**What the agent missed, and the runbook says:** the line tracer is not tied to the OPEN100 folder; `PID_SHEETS_DIR`
points it at any folder of PNGs, and with no answer key present it reproduced the recorded 345 links on sheet 0
exactly. It did get one thing right that the README had blurred: the one-sheet workflow
(`site_extraction_workflow.py`) uses a simpler recipe than the results (whole sheet, no tiles, no tracer). The
runbook names both routes and says which one the numbers measure.

**Its verdict, kept as it said it:** the method, the file formats, the review and mapping loop and the checking
habits generalize; the accuracy numbers, the tracer settings and the risk tiers (tuned on OPEN100) and everything
that needs process data don't. About half a day to a day to a reviewed draft of one drawing, most of it review;
days to weeks to a usable Ignition model with real bindings, most of it the plant's own engineering.

**Lesson:** the author can't read their own repository cold. An agent that can is cheap, and it found in five
minutes what a stranger would have found by giving up.

---

## 63. Prove every way in, and time one

**What:** 2026-10-29. The README said the project starts "wherever you are", and only the drawing-image route had
a runnable path. Each other way in the code implied was built out or proven, with a runnable example under
`examples/`, a test, and a row in the README's "Start wherever you are" table. A fresh agent then timed the
drawing route on a sheet it was handed as its own, and a client-facing report was added as the example deliverable.

**What each one showed:**
- **Timing (one model call, approved):** PNG to review bundle in 88 seconds of commands (extraction 36 s, tracing
  4 s, intake under 1 s) on OPEN100 sheet 8, everything first time. Scored afterwards against the sheet's key it
  matched the published mean for that sheet (review load 11.0 against 10.99). The earlier estimate of half a day to
  a day was mine and was wrong: it priced in a stranger learning the repository, not the work. Review time is still
  unmeasured.
- **DEXPI file to twin, no model at all** (`dexpi_to_twin.py`, `examples/from-dexpi`): lossless against the key on
  three public DEXPI sheets (zero corrections, F1 1.0). What it loses is listed: six-class collapse, tees, direction,
  attributes, hierarchy. A drawn label isn't a governed tag: one sheet labels five manual valves with pipe-spec codes,
  and the bundle flags them as duplicates.
- **Written description to exports** (`examples/from-description`): `generate.py` only accepted Tennessee Eastman's
  symbols and hand-placed positions, and treated a valve as a valve only if it had a simulator index. It now takes
  any model in the same schema: more symbol types, valves from `final_elements`, units placed automatically in flow
  order (labelled as such), `--out`. The TE outputs are byte-identical. The first automatic layout put every unit
  off the right edge (a recycle loop inflated the column count) and the second stacked them in one column (utility
  feeds counted as starting points); both were caught by looking at the render, not by a test. The drawing itself
  still needs a hand-written drafting layout, and the guide says so.
- **Loop list to loop audit** (`loop_audit.py`): any `controller,measurement,output` CSV against a drawing key gives
  0 of 19 on revision A and 19 of 19 on revision D, as the original audit does. On revision C it is more precise:
  the controllers were drawn but read indicators, not the listed transmitters, so it says "partly drawn" instead of
  "not drawn".
- **Historian CSV** (`csv_normal_bands.py`, `csv_replay_server.py`): the bands from a CSV export of the TE runs
  match the committed bands within rounding and give the same fault-6 result; a blank or "Bad" cell is served as
  Bad quality, never zero.
- **Vendor evaluation** (`evaluate_vendor.py`): any tool's output scored with a perfect, a deliberately wrong and an
  empty answer beside it, refusing to report if the wrong answer scores above F1 0.10. On the round-5 runs it
  reproduces the published 20.1 exactly.

**Bugs the timing run found:** the scorer's command line scored a run record as zero instead of reading its
`prediction` (it now unwraps it, or refuses a file with no symbols); the runbook didn't say where the manifest goes,
that `--drawings` is the file name, that both commands need the requirements, or that the example's output folder
can't be reused. All fixed.

**Labels:** `data/script_index.json` gives every script a kind (tool, check, support, research record) and each
tool a guide; `docs/SCRIPTS.md` is generated from it and the scripts' own docstrings, and a test fails if a script
is missing, gone, or a tool has no guide: 20 tools, 6 checks, 8 support modules, 76 research scripts.

**The deliverable:** `deliverable_report.py` turns a bundle into the page a client reads first: the drawing with
every extracted item boxed, the 46 of 445 rows to check first and why, the hierarchy, next steps and limits
(`examples/own-drawing/deliverable/REPORT.html`).

**One near miss:** re-running the recorded round-trip scoring to show the scorer change didn't move it emptied the
revision A tables, because those run records aren't in this checkout. Restored from git; the stages whose runs
aren't local were recorded on the strength of the diff (the scoring function is unchanged; only the command line
moved), and that is what this sentence says.

**Lesson:** "it supports X" means nothing until X runs from a clean clone. Every one of the six ways in needed new
code or a fix before it ran on someone else's input, and the one I estimated, I estimated wrong.

## 64. Review everything, measure what the graph says, and widen the corpus until it fails honestly

**What:** 2026-10-29. Every feature now has an entry in `data/features.json` (what it is for, who it serves, its
guide, example outputs and tests), and every review is recorded in `data/reviews.json` with the hashes of the files
it checked, so "proven" means a passing independent review that still matches today's outputs
([FEATURES.md](FEATURES.md)). Four review rounds by fresh Claude agents, with Codex (another model family) on the
opportunity screen and the estimator, recorded 89 findings in rounds 2 to 4 (46 should-fix, the rest nits); every should-fix was fixed or is listed open. Proven features went from 2 to 8 of 16 in
this batch; the rest are in a final confirmation round.

**The statement review measured something the earlier checks couldn't.** Every graph claim rendered as a plain
sentence, and a seeded, stratified sample checked against its source by an independent agent
([statement review](../examples/statement-review/README.md)):
- The Bayer model, written from the CSB report: 5 of 57 sentences don't match their cited source (8.8%, 95%
  interval 3.8–18.9%). Five real model errors that the structural and figure checks had passed.
- The sheet-0 extraction: 3.3% read as written, 40% read as a person would. The extracted "links" mean "on the
  same drawn line network", which is the public answer key's definition, not "a pipe runs between them". Only 5
  of 27 sampled links were next to each other.

**So the graph now has layers** ([GRAPH_EXPORT.md](GRAPH_EXPORT.md#three-layers-for-the-lines)): pipe segments and
their tees (`piped_to`, junctions by kind), line networks (`on_network`), and the network pairs the key scores.
Instrument connections, actuator stems and nozzle stubs are their own edge types, because the first layered review
found them read as pipe (3 of 15 pipe sentences wrong). After the fix a fresh sample had 0 of 15 wrong in every line
layer. That review also caught plant tags read as ISA letters: MSBV, the main steam bypass valve, became "a
moisture valve". Now a tag whose letters start with a system code on its own sheet isn't read as ISA. Each
evaluation now names the layer it measures ([EVALUATION.md §7](EVALUATION.md#7-which-layer-each-evaluation-measures)).
One correction came from outside: the PID2Graph key *is* a graph with connector nodes, so pipe truth can be derived
from it. That gave the first real-world pipe-layer score: OPEN100 development sheets 0.914, holdout 0.898 (only
partly blind, because one error class was first noticed on holdout images).

**The export no longer drops anything silently.** A review found nested records, verification caveats, a second
check's evidence and the model's own notes missing; the TE export went from 336 to 495 claims, and a test now fails if
any sentence in a hand-built model doesn't reach the graph outside the declared exclusions. Two missed cases surfaced
on the way: all 8 TE cascade loops had no `sets_point_of` edge. A `--profile core` export keeps what a change system
needs (identity, settings, impact relations, sources) and counts everything it leaves out.

**The corpus grew until things failed.** Twelve openly licensed families were staged (527 MB, pinned by hash) and 29
cells added to the [matrix](GENERALIZATION.md), each criterion fixed before its run:
- The DEXPI reader read no controller in any DEXPI 1.2 export. After fixes developed on reference files and checked
  once on held-out vendor exports, it reads 43 of 44 across SPPID, Comos, AVEVA and AutoCAD (the held-out score
  before the remaining gaps were fixed is kept in the ledger).
- Historian bands flagged normal running on every real source. A drift-aware default passes PRONTO day 3 and the
  HAI testbed but fails three untouched cyclic sources (1 of 21 runs). Neither method handles cyclic processes yet,
  and the README says so.
- Exported vendor renders and agent-keyed scans fail the pipe layer. Agent-made keys are labelled as weaker than a
  human key and never counted as an independent source.

**Estimates are first drafts and say so:** a banner and grade before the numbers, the assumptions the figure rests
on, and the data to collect (and where) to replace each one, generated from what the run actually used.

**Six people from LinkedIn, role-played:** a solo plant engineer, an Ignition integrator, an energy manager, a
process-safety engineer, a hiring manager and an ML researcher. They found the first screen too dense, the headline
stronger than the evidence ("a tagged asset model for Ignition" when the tags are placeholders), the LOTO warning
three clicks from the artifact, no Windows or scanned-PDF path, and a headline split that is really a same-plant
validation set. The README now opens with what goes in, what comes out and how long, and safety warnings sit on the
isolation CSV and image themselves.

**Recorded, not re-run:** the OPEN100 direction spot check (model calls) was marked current after the twin's
`variable` fields changed for four instruments, because neither of its scripts reads those fields.

**Lesson:** a claim checked only against the thing that produced it isn't checked. The statement review, the corpus
and the role-played readers each found what every internal test had passed.

## 65. Finish the tool handoff and check the public story

**What:** 2026-10-29. Continued the same evening's handoff: scan cleanup, the pipe layer, cyclic historian data,
review metadata, food-plant questions, estimates and reproducible predictions. The aim was a coherent set of
prototype tools a visitor can try and check, with the research record kept distinct from general-purpose tools.
The README links each entry point to a runnable example; [DELIVERABLES.md](DELIVERABLES.md) carries the full output
inventory, [SCRIPTS.md](SCRIPTS.md) identifies the 27 tools, and [FEATURES.md](FEATURES.md) records which exact
examples have passed an independent agent review. That status is software evidence, not a person's sign-off.

**Scan cleanup helps some scans and hurts another.** The optional `scan_cleanup.py` wrapper is now wired into
matrix row 1 and documented in the own-drawing runbook. On the OPEN100 synthetic scans, with answer-key symbols
supplied, network F1 is 0.894 / 0.818 / 0.753 for L1 / L2 / L3; the original tracer gave 0.877 / 0.566 / 0.387.
The real OMRE quadrant goes the other way, 0.561 to 0.522 against an agent-made key. Cleanup stays opt-in; the
original tracer default is unchanged. These are deterministic oracle-symbol checks, not new model-extraction
runs, and do not replace round 4's pre-registered results.

**Pipe scores improved, partly because the scorer was wrong.** DEXPI 1.3 pipe F1 is now 0.916, OPEN100 development
0.931 and validation 0.912. The vendor-render pool is 0.776 and still fails the 0.88 criterion. Its SPPID subset
became development data: the scorer-only junction correction accounts for 0.679 to 0.852, about two thirds of its
total gain to 0.939. Reserved Comos renders still score 0.264; the one AVEVA render has just one pipe segment.
The pooled result mixes splits and is not a held-out accuracy claim. OPEN100 is only partly blind, and the derived
truth changed too. [EVALUATION.md §7](EVALUATION.md#7-which-layer-each-evaluation-measures) gives the current numbers
and limitations. The PID2Graph paper's metric was checked directly: edge mAP on individual graph edges differs
from this project's F1 on network pairs or derived pipe segments.

**Cyclic history is a limited result.** CSV `auto` selects daily-cycle bands only with sufficient periodic evidence;
drift remains the fallback. The 2018 BattLeDIM development windows pass 8 of 14 cases. The reserved 2019 year,
from the same water network, passes only 6 of 19: 13 leaks detected, seven windows with excessive pre-leak flags,
and detections delayed roughly 14 to 120 hours. This is not a new-plant test or an early-warning claim. The guide
now says history can highlight unusual changes. Independent probes also found accepted NaN/infinite timestamps
and finite inputs whose derived values overflowed: these now fail explicitly before writing an invalid report.

**Review information reaches the exports.** The tag-based safety floor marks 25 instruments and moved 22 from
green to amber; it does not catch untagged valves, manual block valves or every NC/MOV/AOV convention. Ignition
types are keyed by kind (12 instead of 37 on the extracted twin), with per-instance engineering units when the
model supplies them. Ignition documentation and PI descriptions carry review status, risk and applicable safety
notes. Unit labels do not perform conversion or validate a source signal's units. Pipeline confidence now names
the seven unrated cross-sheet links that the review queue puts in amber. All 2,886 extracted items remain
unverified until reviewed; risk ranking does not upgrade their verification status.

**The estimator's checks now constrain the calculation.** Redundant electricity forms must constrain the annual
energy actually used, including complete ranges and zero-hour cases. Ambiguous partial load increases are refused
with explicit alternatives. Incremental steam enthalpy can be smaller than gross steam-production heat; the E7
assumption names the actual turbine inlet/outlet boundary. Site notes and measurement provenance survive both
JSON and Markdown. A fresh reviewer reproduced all 12 example files, passed 37 tests, and checked 400 scalar
endpoints and 10,000 mixed saving/load scenarios against the reported intervals. These are first-draft estimates,
not measured plant savings. Ten food-process questions and a multi-site rollup bring the question registry to 50;
the food model and its 24 findings are explicitly illustrative, not evidence from a food plant.

**Fresh reviews found faults the existing suite missed.** The graph validator accepted duplicate edge IDs,
invalid review states and dangling stream endpoints; it now refuses them. All eight TE cascade statements were
being checked against the wrong model field, and nested source paths caused false mismatches: the source checker
now reports 576 matches, seven not checked and no differences on the TE graph, with negative controls. Safety
sentences now identify tag-derived, unverified screening. The sheet-0 population is 1,087 statements (163
attributes, 188 identities, 736 relations); older seeded samples and their measured error rates are retained as
historical samples rather than silently redrawn. A DEXPI report wrongly said unplaced items were excluded from
platform exports; the report now describes the automatic fallback placement that the code actually uses.

**The headline can now be re-scored.** Preserved research working copies contained the round-5 and TE parsed run
records that were missing from the earlier export. Recovered 391 parsed predictions, with raw-byte and exported
hashes in [predictions/RECOVERY.json](../predictions/RECOVERY.json); an independent reviewer verified every source
hash and slim export. Raw model text stays outside git. There are now 1,123 prediction files across 101 labels.
`rescore.py --check` reproduces 30 of 35 result tables, including the round-5 headline replicates and both TE
round trips. Twenty-three match current formats and seven match explicitly supported historical formats; no
metric differences are discarded. Five earlier diagnostic tables still report GAP. A recovery receipt proves
which local records were exported, not provider attestation or a fresh commercial-model run.

**Four LinkedIn readers, role-played by fresh agents:** a solo plant engineer, a controls integrator, a manager and
a skeptic. Their checks removed unmeasured time-saving claims, clarified that the review CSV cannot add an omitted
symbol, corrected an old PI file list and explained that valid CSV review rows can persist even if another row
fails. A rebuilt extraction needs review reconciliation by source symbol IDs; decisions are not automatically
merged. Generic drawing bundles do not generate the research demo's mimic, 3D or LOTO outputs. The delivered
one-page report was regenerated and inspected in a browser with its draft banner and review steps visible.

**Verification and remaining boundaries.** The full matrix is 63 pass / 23 fail / 8 n/a (94 cells), compared with
61 / 24 / 8 before this batch; BattLeDIM 2019 adds one failing cell. Every cell records the current tool hashes,
and all 52 pipeline stages are fresh after rebuilding the affected exports and renders. The claim checker now
also checks the six new README matrix claims against the result JSON. It checks agreement with committed evidence;
the separate rescore check regenerates results from predictions. No commercial extraction, human timed review,
operations review, PI import or own-drawing native gateway import was run in this continuation. Historical native
gateway receipts remain historical. Median-of-three drift smoothing and making scan cleanup the tracer's default
remain unadopted choices; no LinkedIn post was published.

The 55 registered test scripts passed after the final matrix freshness test was rerun (its first invocation
preceded the last cell refresh); two Windows symlink subcases require Linux CI. The claim check reports 41 numeric
matches, one prose-only claim and zero failures. All 16 feature entries have current passing independent reviews
of their registered example outputs, with limitations attached. That does not mean every possible input or
organizational workflow has been validated.

## 66. Keep the questions, answers and next owner together

**What:** 2026-10-29. Extend the tools from producing a draft model to retaining the engineering investigation
around it. The [context register](CONTEXT_REGISTER.md) accepts a model, questions and original local documents,
then keeps answers, explicit assignments, source-match reviews and plant-truth judgments separately. It emits a
readable report, dated history and versioned JSON with enriched graph and questions. No model call or account is
needed. Initial owners and reviewers remain unassigned; the tool does not invent responsibility from a file date.

**The question engine now has a demonstrated return path.** The
[Bayer E18 example](../examples/context-register/bayer/README.md) runs the actual engine and retains a partial
interpretation of the original CSB report's temperature-control narrative. Its six asset/stream references,
three collection prompts, decision rule and limits survive in the register. A description of intended operating
sequence does not establish simultaneous duties, an energy opportunity or savings. Answers do not automatically
complete collection prompts. The example remains proposed, unassigned and unknown for plant truth.

**Expand linked evidence, rather than count the same plant twice.** The
[PRONTO packet](../examples/context-register/pronto/README.md) connects four existing original documents: the
technical report, alarm workbook, operation log and day-3 event journal. It has 22 proposed statements over 21
questions and 11 asset identities. Every original byte hash is checked; the derived transcription key never
substitutes for a missing original. An independent agent checked all 22 facts against the actual cells, records,
PDF text and a separately rendered schematic. Three disabled-limit controls stay disabled; uncertain numerical
units and the FIC301/FIR305/FT302 labels stay unresolved. No alias is guessed. This adds linked-document workflow
coverage within an existing source family, not an independent plant or a human-reviewed answer key.

**A source revision reopens its dependent answers.** Each answer records exact question and asset content,
incident relationships, source revision, raw-byte hash and locator. A refresh compares that snapshot with the
current inputs; an old CSV cannot approve new evidence. Synthetic copies of the PRONTO report reopened exactly
six answers, leaving sixteen unrelated answers current; an alarm-workbook revision reopened seven, leaving
fifteen current. Both retained the decision history. An offline invented packet also exercises accepted source
interpretation, conflicting values, missing data and unanswered questions. Its fictional people and approvals
are explicitly labelled. Plant truth is unknown throughout these examples.

**Independent probes changed the implementation.** Early versions could overwrite a register saved under an
alternate output filename or clobber a source through a hard link. They also accepted correctly rehashed but
malformed historical identities, and silently trimmed an asset ID whose references did not match. Those cases
now refuse before output writes. Exact IDs, attributed dates, record structure and evidence bindings are checked
separately from hashes. History hashes are consistency checks, not signatures or tamper-proof records. Exact
source reversion matches the old snapshot again; there is no watcher, expiry or record of intervening changes.

**A young engineer needs a decision and an organization around the tools.** A fresh reader found that collection
requests, walkdown guidance, mapping previews and technical review already exist. The missing step was a compact
[first-pilot brief](../examples/first-pilot/README.md): choose one operational decision, involve its sponsor and
operator, record a baseline and trial observation under comparable conditions, then decide continue, change
scope, stop or insufficient evidence. The site supplies authority and thresholds. The brief is a manual working
record, with no approval or measured benefit in its blank fields. Retain unsuccessful attempts and a receiving
owner as well as the successful result.

**Maintenance and handoff are explicit.** Refresh deliberately against released source revisions, retain the
register and backups, and hand over stable identities, unresolved states, original evidence and full history.
The neutral interchange is `context-register-1` plus `twin-graph-1`; a receiving system needs a reviewed adapter.
There is no live sync or verified downstream integration. The earlier statement-review CSV remains a separate
workflow with a documented limitation: its semantic statement IDs do not bind a changed source revision, and
those approvals are not migrated into this register.

**Validation boundary:** deterministic software examples and independent agent review. Engineering adoption,
review time, source authority at a real site, operational acceptance and measured business value remain untested.
The next useful evidence is one engineer using the packet for one real decision, including a recorded result
that it did not help. Additional synthetic examples cannot establish that outcome.

All 57 registered test scripts passed locally; two Windows symlink subcases remain for Linux CI. The new controls
include 32 register tests and three example tests. The claim check still reports 41 numeric matches, one prose-only
claim and no failures; the existing 52 pipeline stages remain fresh. All 17 feature entries now have a current
passing independent agent review of their exact registered example outputs. The new receipt also records the
primary-source checks and remaining limits; it is not human adoption or an operational acceptance record.

## 67. Explain the engineering foundation and each piece's job

**What:** 2026-10-29. Reframe the README around engineering context an organization can inspect, maintain and
own. A drawing is one view into the assets, relationships, evidence, open questions and decisions. Future
manufacturing applications are the intended use of that foundation; the present evidence remains the prototype's
public-source software checks and recorded lab demonstrations.

The entry page now explains nine contributions: intake; the asset/relationship model; source review, loop checks
and signal mapping; the question engine; historian analysis and impact estimates; retained context; a bounded
pilot; portable handoff and staging; and reproducibility/change checks. Each contribution links to a runnable
route or its guide. The diagram shows the engineering investigation and its source refresh, with controls records
and recorded data joining the review route. The prose makes clear that a written description needs an authored
model and that historian CSV analysis can be used on its own.

**The organizational transition has a boundary.** The local tools can supply a complete, inspectable packet.
Ongoing shared use adds source authority, identity reconciliation, access, accountable review and decisions across
projects. The README names those responsibilities and the neutral handoff requirements without claiming a hosted
service, authenticated approval, automatic monitoring or an available downstream adapter. No product-specific
commercial material is included in the public repository.

**Reader review changed the copy.** A fresh young-engineer/controls/manager reading removed an unsupported claim
about what most digital-twin projects do first. It also caught wording that could make every input route sound
like a model builder; the final text separates controls and historian analyses from model creation. The old
diagram could imply that an arbitrary drawing bundle produces working screens and inherits the demo's gateway
acceptance. Its replacement and the platform section now keep that lab evidence with its actual demonstration.
The young-engineer and independent technical readers checked the final framing against the guides; 26 links in
the revised material resolve, including the renamed platform-section anchor.

This is documentation work. The claim check still reports 41 numeric matches, one prose-only claim and no
failures. No model, method, benchmark, runtime receipt or tool implementation changed. The legacy statement-review
revision-binding limitation remains documented; this edit does not fix it or upgrade historical approvals. No
LinkedIn post, real-site pilot, measured adoption or downstream import was performed.

## 68. Make source changes and generated outputs fit one reviewed context

**What:** 2026-10-29. Define the organizational lifecycle, close the legacy statement-review evidence-binding gap,
and add a manufacturing source family to the context examples. The intended authority is one central reviewed
context. Specialized tools consume versioned snapshots and return draft outputs, questions and proposed changes
through engineering review. The [lifecycle guide](CONTEXT_LIFECYCLE.md) specifies that contract and distinguishes
the implemented local tools from an organizational service that remains to be built and accepted.

**Documents need different maintenance rules.** Original records keep their bytes, revisions, owners and controlled
references. Generated views keep their source snapshot, recipe, dependencies and release state. Authored documents
need explicitly managed sections, proposed differences and reconciliation of manual or concurrent edits. Incoming
evidence should be visible while review is pending. Local CSV acceptance is provenance, not authenticated authority
in a receiving organization. No document watcher, managed-section merger or live organizational integration was added.

Actual input shapes matter. `generate.py` and `question_engine.py` consume process-model or extracted-twin JSON;
the graph is not their general input. Graph export has no general inverse, and the context sidecar does not update
the original generator model. The guide therefore requires declared projections, loss reports and readback checks.
It sets an acceptance target for one source-backed change through a hub, one generator, reviewed release and the
next revision, including rejection, concurrent edits, interruption and rollback. That organizational-context round
trip has not been performed. An asset-count match would not establish that claims and history survived it.

**Close an actual unsafe reuse path.** The independent pre-change reproduction kept a statement's semantic ID and
text unchanged while moving its source from one document revision/page to another. The old CSV applied successfully.
New packets and browser downloads now bind the complete canonical graph, actual machine-check model, supplied
original image/report bytes and exact statement/source/target/layer details. Apply rereads those files and refuses
any reviewed row with a stale, missing or edited binding before writing output. Sampling preserves bindings;
sampling a legacy packet does not manufacture them. Historical samples and scores remain unchanged and scoreable,
but their unbound verdicts cannot be applied to today's graph. Notes now travel verbatim with checks and events.

Independent adversarial review found two additional clobber cases: sampling onto its own full packet, and a source
image named as a generated crop. Both now refuse without changing input or destination bytes. Render stages its
dynamic crops before collision preflight, including hardlink/symlink aliases. A first collision implementation was
quadratic in file count and made the actual full drawing run impractical on Windows. It now scans paths and file
identities once; a 600-target regression control preserves that bound. Ordinary filesystem failures can still
interrupt publication, so prior records and backups remain necessary.

The [bound sheet-0 packet](../examples/statement-review/bound-sheet0/README.md) retains a new 12-statement sample
over five relationship layers, the original drawing crops, and one explicitly fictional `unclear` verdict. Three
standard-library integration controls exercise actual CLI application, note/value preservation, and refusal after
copied source or graph changes. This is evidence of software behavior, not another accuracy review. Whole-graph
binding is intentionally conservative: unrelated assets, statuses and events reopen the packet. The context
register's separate selective dependencies are unchanged. Hashes are not signatures; exact restoration can match
an old snapshot, and neither tool monitors intervening changes or authenticates a reviewer.

**A different source family exposes a real revision problem.** The new
[NIST SMS Test Bed packet](../examples/context-register/nist-smstestbed/README.md) fetches two published device
configurations, an archived raw operating log and the upstream reuse notice. All four are pinned by immutable
revision, raw hash and byte count, with no originals redistributed. The same machine UUID links the configurations,
but a reused data-item ID changes meaning from tool number to accumulated program time. Observations stay scoped
to each revision. The raw log does not prove which configuration was deployed, so that question stays open.
`UNAVAILABLE`, numeric zero and a single blank program-name space remain distinct. No job or live machine condition
is inferred.

Discovery inspected these facts before packet acceptance criteria were written: this is a development example,
not held-out generalization. Ten proposed answers over eight questions produce five partial and three needs-data
states; all questions need an owner and plant truth remains unknown. Copied older-config, later-config, raw-log and
unrelated-notice changes stale exactly 3/3/4/0 answers while preserving history. Independent review checked ten
primary XML/raw fact groups, original hashes, lifecycle/refusal controls and missing-original failures. The derived
key is never substituted for unavailable original bytes.

The three multi-document context packets are listed separately in `data/corpus.json`. The eight-workflow matrix
still has its existing 94 cells; the new packet is not counted as another extraction benchmark. Its packet-local
registry reuses the pinned-file fetcher without changing existing matrix recipe hashes. Prototype source checks,
independent agent review and a clear integration contract do not establish human adoption, review-time savings or
an organization's continuing document-management outcome.

A young-engineer/engineering-manager reader pass also caught a missing connection to the already implemented
`apply_review.py` model-correction route. The lifecycle table and pilot guide now explain that limited local
return path, its in-place/partial-row behavior and the separate organizational approval needed on transfer.
The README's older class-wide "public drawings only" wording now distinguishes drawing validation from the
other public-record workflows. These edits make existing capabilities discoverable; they add no hub adapter.

All 58 registered test scripts passed locally; two Windows symlink subcases were skipped and remain for Linux CI.
All 17 feature entries have current independent review receipts for their exact registered outputs. The narrow
matrix receipt checks only the added context registry and preserves prior result/review scope; no 94-cell rerun
is claimed. The claim check still has 41 numeric matches, one prose-only claim and no failures, and all 52 pipeline
stages remain fresh. These are offline software checks, with no new operational acceptance or measured adoption.

## 69. Preserve known engineering meaning and retained review history

**What:** 2026-10-29. Two maintenance failures found while following the document-to-maintained-context route:
known unplaced instruments and valves lost their semantic roles at graph export, and a context refresh could
silently replace retained history. The prospective checks are in [GOAL.md](GOAL.md#maintenance-acceptance-retain-unplaced-asset-semantics-and-context-history).
These are development repairs to inspected examples, not new blind extraction results.

The DEXPI reader already retained these items and their source claims. The exporter ignored an explicit
`unplaced.kind`, usually calling the node a generic line item. The original role and controller reference survived
as attributes, but asset queries and plain statements used the wrong role and the known control path was not
traversable. The [actual-source example](../examples/graph-export/unplaced-dexpi/README.md) follows a public
PID Toolbox flow loop and a Comos unplaced instrument through reader model, graph and statements. Placement stays
unresolved. A controller's interpreted output relationship is not a fresh verification of physical signal direction.

An in-memory diagnostic over all 220 already-inspected cached XMLs produced 214 reader models and the same six
known duplicate-ID refusals. Before the repair, 87 of 88 unplaced items lost their declared role: 52 instruments
and 35 final elements, in 55 files across four exporters. Forty-four recorded unplaced control endpoints across
33 files had no corresponding control edge. After the repair, all declared roles and those 44 relationships are
represented, with no new export failure. The exporter adds no unit, physical location or plant-truth verdict.
Original reference claims, source and uncertainty remain. Missing, ambiguous, incompatible or malformed nonempty
references refuse before output writes. Unknown explicit roles retain a generic fallback and their original claim.

No parser, matrix criterion or historical score changed. The existing matrix tool-hash check remains current:
graph export is not an exercised dependency of its current cells. Its 94 cells therefore retain their recorded
63 pass, 23 fail and eight n/a results; no new matrix run or placement pass is claimed. In particular, a retained
unplaced item is still unplaced.

**History needs an explicit continuation.** A real CLI reproduction using the pinned NIST originals first saved ten
proposals, then silently erased them when refreshed without `--register`. A second reproduction replaced an
eleven-decision history with an older ten-decision register. The new guard validates the destination and requires
an explicit register once either decision or ownership history exists. Every retained history must remain an
unchanged ordered prefix of the computed result. Older, divergent or invalid destinations refuse before any write;
a deliberate fork needs a fresh directory. Initial apply into an empty prepared register still works.

The [NIST history check](../examples/context-register/nist-smstestbed/check_history.py) exercises the actual CLI
and originals in disposable folders: omitted-register and older-register refusals preserve all working files,
current-register refresh is byte-idempotent, and an explicitly separate older-history fork works. A synthetic note
revision creates the eleventh proposal; it does not invent a human review. The original documents and historical
packet report remain unchanged. Ownership-only and divergent-history controls belong to the core regression suite.
The guide explains recovery and the difference between continuing and forking.

These guards concern a single local invocation. They add no automatic merge, authenticated authority, concurrent
writer lock, atomic multi-file publication or live integration. Independent review passed 50 graph and 26 history
adversarial controls, the original-source checks and all 31 graph, 43 context and three existing example tests.
The exact nine graph and 17 context outputs have current hash-bound receipts, with the earlier outputs unchanged
and their prior review scope preserved. All 17 feature entries have current software evidence. The full local
suite passed 58 registered scripts with two Windows symlink subcases skipped; Linux CI must check those.

A cold reader clarified drawn connection direction versus logical control roles, and added the exact second-revision
apply command using the retained current register. The neutral lifecycle guide now also explains how existing
systems can retain execution/release authority while reviewed context supports investigation. Outcome learning
requires attributed execution and observations to return. No incumbent connector is supplied. Software preservation
and clearer responsibilities do not establish engineer adoption, review time saved or a successful operational decision.

## 70. Count omitted checks before calling the suite complete

**What:** 2026-10-30. The `8b90d3a` CI run completed all 58 registered scripts successfully, but its final
zero-platform-skip summary was not an exhaustive omission count. At least 12 unittest skips were visible in its
per-script last lines, and the DEXPI oracle printed that its check was skipped before returning normally. Other
successful scripts' stderr was discarded by the wrapper, so the old log cannot establish the total. The local
cached-data run and Linux CI had different coverage. Historical receipts retain their original, limited scope.

The runner now reads unittest's skipped-case totals from both output streams, including failure summaries. Explicit
platform notices identify operating-system restrictions; generic skipped-check notices have their own category.
Platform notices explain unittest cases rather than adding another case count. Additional notices can describe
groups, so they are not another unit-test denominator either. A successful script exit can coexist with omitted
cases. Any reported omission withholds the complete full-suite message; test failure and prerequisite exit meanings
are unchanged. No missing source or dependency is installed or fetched by the runner.

The known oracle early return is now a real unittest skip. This repair does not prove that an arbitrary test
program cannot silently omit work or fabricate a report. Tests with optional original-source caches can still
skip; preflight covers the declared required files and dependencies. Source-only still selects a narrower suite.
The reviewer, replication and entry guides explain those boundaries and how to inspect affected cases with `-v`.

The [offline four-child example](../examples/test-coverage/README.md) executes actual illustrative programs through
the runner: all checks execute; four class/method/subtest skips reported on stdout; a simulated platform restriction
plus an extra check notice; and a failure with a skipped method on stderr. Declared fixture counts are checked
against the real reports and the committed expected JSON. Only test selection and prerequisite discovery are
replaced; process execution is real. These are software controls, not another corpus benchmark or a plant review.

Independent actual-child controls reproduce four incorrect complete-pass cases in the earlier implementation,
including the missing-cache oracle path. The repaired reporting passed 18 independent controls covering class,
setup, method and subtest skips; both streams and multiple summaries; failures/errors/expected failures; genuine
platform-helper behavior under a planted privilege error; generic notices and prose negatives; and source-only,
preflight and exit semantics. The real three-sheet cached oracle also executes without skips, with its six input
cache files unchanged. The core runner controls now include the public process example.

**Make optional source preparation runnable.** Following the skip messages found that the DEXPI guide claimed
PyMuPDF was in `requirements.txt`, although the core file did not list it. A separate `requirements-render.txt`
now pins the locally tested renderer. Rebuilding all five configured public sheets into a disposable directory
with PyMuPDF 1.27.2.3 reproduced all 13 adapted files byte for byte. No source original or existing cache was
overwritten. The guide also replaces its error-free/perfect-conversion wording with the actual oracle-route
scope, points own-CAD users to the reader, and distinguishes ignored originals from committed derived examples.
This changes no adapter rule, drawing, model prediction, answer key, benchmark score or matrix criterion.

All 58 registered scripts passed in the local cached-data run. Its new summary reports two skipped unittest cases,
two platform notices explaining those same cases, and zero additional skipped-check notices; it correctly withholds
the complete-suite message. No optional-cache skip was reported locally. CI and other environments need their own
reports. All 17 feature entries have current independent output receipts; this increment binds the two repo-checks
outputs, 18 supporting files and the reviewed README section. The 94-cell matrix and its tool hashes remain unchanged,
all 52 pipeline stages are fresh, and the claim check still has 41 numeric matches, one prose-only entry and no failures.

## 71. Carry explicit model rejections into the next question screen

**What:** 2026-10-30. Following the review-to-question workflow found that the question engine ignored
`ops_review`. Applying three fictional rejections to the existing synthetic food model left the rejected power
meter, speed drive and heat-recovery unit suppressing questions. The independent baseline reproduction kept all
24 findings unchanged; removing only those three records as a diagnostic control produced 27. K-201 also remained
absent from the existing model-wide C12 question. These are software controls on invented equipment, not a new
plant, human review, corpus family or accuracy measurement.

The engine now builds a separate active projection. Explicitly rejected records cannot trigger or suppress a
question, supply evidence or collection locations, satisfy required model kinds, or carry a relationship path.
Source bytes, rejected records and review history are retained. Non-rejected children remain eligible without a
rejected owning unit, parent or stream; no replacement is inferred. Ordinary unresolved references retain their
previous behavior. Missing/unverified review remains eligible and is not approval. Malformed review metadata
refuses before output writes. JSON and Markdown report the recorded exclusions; empty extra fields are omitted
so the earlier unreviewed screens and roll-up reproduce unchanged.

The [offline refresh example](../examples/opportunity-screen/review-refresh/README.md) uses the actual review and
screen CLIs on a temporary model copy. Rejecting JT-201 adds K-201 to C12's triggers; rejecting SC-203 opens E29 at
K-203; rejecting HX-303 opens E31 and H6 at F-303. It checks the three new finding IDs and C12 membership separately,
repeated-review byte stability, explicit reconfirmation restoring the questions, retained history and unchanged
source bytes. Its committed screen selects only those four question types. The original full food screen and all
other historical outputs retain their original population and evidence scope.

Independent review caught a bypass in the first repair: a supplemental loop row could recreate a rejected drive
as a controller and silence a live measurement question. The guard now checks rejected IDs and tags across model
sections, after accounting for live duplicate identities. A supplemental row does not override rejection. This is
not identity reconciliation: a live duplicate remains eligible and needs an engineer's review. The registered
question-engine script currently passes 51 tests, including the actual CLI packet and the new bypass regression.

A fresh cold reader found an additional documentation trap: when a finding disappears, its old source-manifest
binding is refused as an unknown question. The maintenance guides now say to preserve the previous packet and
manifest, withdraw absent IDs from the current locator bindings, then refresh with the existing register and no
old answer resubmission. Independent actual CLI checks on a temporary Bayer packet verify the refusal preserves
all bytes, the corrected refresh retains the original decision and ownership history exactly, and the removed
question is marked absent with its earlier answer stale. The pinned raw source remains unchanged.

The existing 94-cell matrix does not exercise the question engine, so this change makes no matrix generalization
claim and changes no cell, tool hash or criterion. All 52 pipeline stages remain fresh. Engineer adoption,
review effort and operational value remain unmeasured; the actual first-pilot observation is still open.

Final independent review passed 37 adversarial controls and all 51 registered question-engine cases, independently
reproduced the ten older outputs and the three new packet files, and bound those exact outputs plus the supporting
code and instructions. The local full runner passed all 58 scripts with two Windows symlink unittest cases skipped,
two platform notices explaining those same cases and no additional skipped-check notices. It correctly withholds
a complete-suite claim. CI and optional-source environments require their own coverage report.

**Separate export gap retained as N064.** The independent scope check applied fictional rejections of U-100 and
FT-101 to a copy of the TE model. The legacy seed Ignition exporter still emits that unit instance and instrument
tag, and the PI exporter still selects its element and attribute rows. Their descriptions carry the rejected
review annotation; exclusion is missing. The review-loop guide now limits its export-filtering claim to extracted
twins and states the legacy limitation. No gateway, import or source-model change occurred. The question repair
does not fix those exporters; they are the next concrete maintenance issue, with historical outputs preserved.

## 72. Make a reviewed seed bundle consistent across its outputs

**What:** 2026-10-30. N064 was more than a missing tag filter. An independent actual-CLI reproduction on a
temporary Tennessee Eastman model confirmed that rejected equipment and signals survived in Ignition, PI and
SVG outputs. Removing a unit from the source also left its old SVG in the output folder. These are software
maintenance defects on a simulation fixture, not plant discrepancies. Acceptance was written in `GOAL.md` before
the repair.

The seed generator now excludes explicitly rejected units, instruments, final elements and drawn streams.
Streams incident to rejected equipment also leave the overview, without inventing replacement connections.
Independently eligible children remain under an explicit `_Unassigned` display container: their original OPC
server/item and PI point claims stay unchanged, while exported/display paths change. Names are allocated from
the complete source before filtering, so rejecting a naming competitor cannot rename a surviving signal.
The complete model and its review history remain untouched. Reviewed seed streams now remain in the review CSV;
unreviewed streams retain the historical sheet's scope.

`seed_review_projection.json` explains each exclusion and old/new child path. `seed_export_manifest.json` records
the generated artifacts and their CRLF/LF-normalized content hashes. Later refresh checks those files, renders
the next bundle and retires unchanged obsolete managed files. It refuses manual edits, untracked artifact files,
invalid inventory ownership, known file/parent conflicts and source-model output collisions before writing.
Unrelated non-artifact notes remain untouched. Legacy folders need matching contents or migration to a fresh
dedicated output directory. The inventory is not signed provenance, organizational approval, a concurrent-writer
lock or an atomic filesystem transaction.

Independent adversarial review found four gaps in the first implementation: a hard-linked output could rewrite
an unrelated backup; a parent-path file conflict failed after earlier writes; Windows junctions allowed writes
through an alias; and a model stored at the inventory path could be overwritten. A final Windows control found
that a case-only inventory alias could retire a still-needed unit SVG. Preflight now refuses these cases before
any known fixture byte changes, including conflicting inventory spellings and existing native file aliases.
A distinct Windows short-name alias was unavailable on the host and is not claimed as exercised.

The final independent review passes 44 actual-CLI controls, the public three-file demonstration, all 30 generator
validation cases, 15 any-model cases and 15 PI-export cases. Separate identity controls check duplicate unit types,
colliding member descriptions and orphan names across two owners; surviving address, unit and read-only claims
are compared against the baseline. These are independent coding-agent software checks, not a person's engineering
review or a native platform import.

The [offline worked refresh](../examples/review-and-mapping/seed-refresh/README.md) uses four fictional review
decisions, checks all 13 earlier unreviewed artifact contents unchanged, repeats without changes, refuses a
manual SVG edit, then explicitly reconfirms the records. Original paths return, the obsolete unassigned SVG
is retired and intervening decisions remain in history. A separate cold reader executed the instructions.
The guide explains source-address claims versus deployment overrides, dedicated output ownership and migration.

This repair covers seed SVG/platform generation. Extracted twins retain their existing route, and the separate
gateway demo, P&ID drafting, mimic and 3D tools are outside this change. It supplies no live organizational
adapter, incumbent approval receipt, human adoption measurement or operational outcome.

The final corpus refresh executes 54 cells covering all 47 that depend on the changed generator; the other
40 cells retain their earlier records. Pass/fail criteria and the 63 pass / 23 fail / 8 not-applicable results
remain unchanged. Seed-generated file counts rise by two for the added sidecars, including the per-model DWSIM
counts; these are output-accounting changes, not accuracy gains. The three affected pipeline stages were rebuilt
through their actual declared commands, with no change to existing output contents; all 52 stages are fresh.

The first full-suite run passed 57 of 58 scripts. Its single failure was the older parent review-and-mapping
example's test counting the new independent seed example as parent-generated output. That comparison now excludes
only the named sub-example, whose actual CLI packet is already exercised by the registered generator tests.
The parent's seven cases pass, retaining exact comparison of its own generated files and rejection of unexpected
parent artifacts. No generator, matrix method or expected historical output was changed to resolve this failure.

## 73. Make maintenance records useful without inventing repair effectiveness

**What:** 2026-10-30. The context workflow now includes the original MetroPT-3 description and measured CSV,
already an input to the historian matrix. The question is practical: does a reported failure have enough linked
evidence for a maintenance-effectiveness review, and what record should the engineer request next? This is
development on an existing family, not a new global source family, held-out test or anomaly-method improvement.
Discovery facts were seen before the packet acceptance was written.

The original three-page PDF reports 15,169,480 instances at 1 Hz. The actual released CSV has 1,516,948 data rows,
timestamps extending into September 1 and nonuniform gaps. No downsampling history, timezone or healthy-state
labels are inferred. The PDF enumerates motor current before oil temperature; their named CSV columns appear
in the opposite order. Joining by enumeration would swap meanings. The failure table prints two different rows
as `#1`; its May 29-30 interval carries a literal `30Apr` maintenance note. These source observations remain
separate, without correcting dates or treating an interval end as verified repair completion.

The [maintenance packet](../examples/context-register/metropt3/README.md) has six source-specific questions and
twelve proposed answers. The questions use the existing context format rather than new automatic catalog rules.
Five need data and one is partial; all six need an owner. No human assignment, reviewer, acceptance, plant truth
or maintenance-success verdict is invented. The source-scoped APU identity is not a known serial number/current
train. Concrete collection prompts request the original execution record, affected asset, actual action/times,
resulting configuration and disposition, followed by comparable observations and an attributed effectiveness
review. A maintenance note or copied completed status cannot supply those facts by itself.

Independent primary review inspected all three rendered PDF pages and streamed the complete CSV. All twelve
final values and locators match. It caught four proposed-answer sentences that compared documents while binding
only one source. Each answer now states only its own source's facts; comparison stays in the question and its
collection rule. That scope matters: otherwise changing one document could leave a cross-document assertion
marked current through its unchanged other source. Separate claim slots also prevent a documentation acquisition
claim and released-file observation becoming an invented simultaneous dispute.

The packet retains raw hashes and exact page/table-row/CSV-line locators. The explicit existing fetch command
downloads the archive; offline preparation verifies and extracts only the two pinned original members, refusing
to replace a changed/incomplete cache. Originals stay ignored and unchanged. The default verifier checks their
hashes and computes the full CSV profile without reading the derived key or proposals. Optional PDF text checks
are explicit; table layout was separately inspected. Original-source checks never substitute a committed key.

Actual prepare/apply CLIs verify twelve bindings, byte-identical repetition, retained history and original bytes.
Labelled synthetic PDF/CSV revisions reopen exactly eight/four answers; changing only the effectiveness collection
request reopens its two answers. Stale-answer resubmission and missing originals refuse without output changes.
The registered example script passes six cases locally, including an optional actual-original workflow and
always-offline committed-packet/path controls. Environments without the ZIP report an explicit source-case skip.

Software review reproduced a hard-link defect in the first `check_packet.py --write`: expected-output publication
could overwrite an original after the preservation check and still report success. Both expected destinations
and their ancestors/known input aliases are now checked before either write, and originals are checked again
after publication. These local guards are not a concurrent-writer lock or atomic filesystem transaction.
Final independent software review passes 33 actual-source/CLI controls, including eight expected-publication
cases, and all six registered example tests with no local skips. A private harness's reason-text assertion was
corrected from `hash` to the actual `sha256` refusal text and that already-safe case was rerun; no product change
was made to accommodate it.
A separate cold reader executed the offline commands in fresh paths, reproduced the expected report/register
and could reconstruct the May question and next evidence request. This is AI software/reader evidence, not an
engineer's observed adoption, timed review, executed intervention or operational outcome.

The 94-cell matrix, its methods, scores and tool hashes remain unchanged; its MetroPT result is still a failing
development result. No matrix cell was rerun for this packet-only increment. All 52 configured pipeline stages
remain fresh without a rebuild. The corpus registry adds this linked-context packet separately from its 42
matrix inputs. The central-context/receiving-system adapter and real engineer pilot remain unverified.

The full local runner reports 58 successful script exits, zero failures, two Windows privilege-related unittest
skips and two platform notices explaining those same cases. The MetroPT original-source case executes locally.
This is not a complete-suite pass; CI and source-absent environments need their own omission report.

The first Linux CI run at `700b920` passed 57 scripts and failed the expected-publication regression. Linux
raises `NotADirectoryError` for a child beneath an ordinary file; Windows first reports that child missing and
then reaches the explicit parent-directory check. The unsafe path already refused, but its exception did not
match the intended consistent diagnostic. Preflight now normalizes that Linux error to the same directory
refusal. The real filesystem control is unchanged; a separately labelled Linux-errno control also exercises this
path on Windows. No source/output content, matrix criterion or assertion was relaxed to obtain a pass.

## 74. Keep the toolkit a starting point

The next useful result is an engineer's first evidence and decision packet around one problem. As people and
projects begin relying on it, the company needs a shared home for the information, relationships, decisions,
ownership and history. The toolkit should make that need concrete through useful work, rather than grow into a
local organizational-governance application.

The README now describes that journey explicitly. The pilot guide adds what happens after the first packet;
the context and lifecycle introductions place ongoing organizational responsibility in the company's shared
system. Operational execution can remain in its existing systems, and specialist tools can later consume
released context and return findings for review. No ready receiving-system adapter or measured adoption is claimed.
This increment changes documentation only: existing scripts, schemas, source packets, outputs and matrix results
remain unchanged. Further feature work should earn its place by helping an engineer start or demonstrate the
handoff, rather than recreating the company system inside this repository.

## 75. Make the first useful investigation easy to reach

A fresh local clone produced the public sheet-0 draft bundle, readable report and question screen using four
standard-library commands, without installing packages or calling a model. An independent reader ran the same
path. The screen contains three investigation prompts; its asset references still need checking against the
drawing. This is a demonstration on an existing development sheet, not a new extraction or transfer score, a
timed human review or measured adoption.

The own-drawing runbook now makes that existing path visible: skip dependency installation for the offline
example, create the draft, read the report, screen the model, then choose one relevant question with an engineering
counterpart. Copy its finding ID, asset references and collection requests into the existing private pilot brief.
The next step remains a shared company home for the context and decisions, not additional local governance code.

Two independent readers exposed consequential gaps in the old starter advice. The plant guide called all twelve
OPEN100 sheets sealed holdouts although six were development and six validation, with validation also used for
method selection. It routed authored models through optional drawing generation and paid re-extraction, implied
generic native screens/3D/replay from those models, and asserted review-time savings that nobody measured. It now
separates supported starting routes and static staging from research demos, begins with one question or sheet,
and makes larger annotation studies optional. Hosted Gemma results no longer support local hardware/throughput
advice in this guide. The OSHA reference is qualified to covered processes and linked to the official rule.

The description route now states that drawing checks need Pillow and that layouts can depict explicitly marked
drafting additions. It also narrows the missing-source warning promise to what the exporter actually checks:
signals without simulator references, rather than every item or stream. Engineering must inspect the source
coverage itself. Structured CAD avoids rereading pixels; no universal site accuracy or cost advantage is claimed.

The actual first question screen surfaced an ambiguous H1 sentence, "close it", which could read as an equipment
instruction. The catalog now explicitly closes the screening investigation and says not to operate the station.
Only that decision-rule wording changes in three existing OPEN100 findings; all other JSON fields, triggers,
thresholds and the 29-finding population remain unchanged. The other worked screens and roll-up reproduce; all
51 question-engine controls pass. The comparison helper initially replaced the same generic phrase in other
questions as well; limiting its expected replacement to the exact H1 sentence corrected that helper assertion,
without changing product behavior. The screen guide also explains that closing a screening question never means
operating equipment and stops offering public OPEN100 schedules as inputs to an arbitrary site's model.

Nine source/reader findings are resolved with code inspection and bounded actual CLI evidence. These are AI
reader and software checks, not engineering approval. The change adds no application feature, schema, public
source family or extraction result. Existing matrix results and their tool hashes remain unchanged, with no
matrix-cell rerun; all 52 configured pipeline stages remain fresh. Local verification targets the exercised
starter commands, exact catalog/output diff and existing question tests. CI must report its own actual coverage.

## 76. Keep a vendor controls export intact before inventing a loop

The existing corpus candidate described the Covestro C08 PCS export as two signal loops suitable for the generic
loop audit. Reading the pinned original shows seven connection records around two system functions, with several
links per function. The report does not by itself establish signal direction or cause-and-effect logic. Mapping
it to one controller/measurement/output row per function would discard connections or require an interpretation.
The candidate is now a worked development intake case, not a new row-4 score or source family.

The example retains every field in all seven connection rows, including both sides' identities, drawing references,
blank OPC addresses and source report-date serials. A standard-library checker compares the transcription to the
original workbook and verifies the instrument workbook and licence against existing byte/SHA-256 pins. Optional
fetch uses the existing downloader for just those three files. An actual fresh-cache fetch retrieved 329,011 bytes
and passed; matching cached files also pass at a zero download budget. Workbooks are read as ZIP/XML data only.

The first draft wrongly described a C-versus-S disagreement for U0020. The actual source checker refused that
assertion, and a separate controls reader independently found C in both reports. The draft was corrected before
acceptance. The remaining question is supported and bounded: what reviewed records explain U0001's connections,
including two references to a legend sheet, and establish its intended behavior? A legend reference is a request
for context, not proof of a drawing error. The public records do not supply a current governing revision, logic,
setpoints, test evidence or an assigned site owner.

An engineer can carry that question and the source packet into the existing pilot brief without inventing an asset
model or question-engine finding. The guide explains that generated screens need a supported model; manually
authored investigations also belong in the toolkit. When colleagues begin contributing, the next home is the
company's shared context and decision system, with execution remaining in existing operational systems. No local
governance application or receiving-system adapter was added.

Root verification exercises eight actual CLI controls: original/cached success, changed field, omitted row, absent
source, exhausted fetch budget, nonfinite budget and changed original. All pass their expected outcomes; the existing
17 loop-audit tests pass. A separate source reader compares every connection field and reproduces the older revision-A
and revision-D Markdown and JSON reports byte-for-byte. The catalog now says supplied loop list and key/model rather
than claiming knowledge of what a DCS currently runs. Matrix cells, tool hashes and recorded extraction results are
unchanged; its page is re-rendered only for the corrected candidate description. These are software and AI source-reader
checks, not engineering approval, measured adoption or operational benefit.

## 77. Let a first source question precede a measured pilot

Two reader perspectives found the same first-use mismatch. The drawing guide and Covestro intake invited one
useful question, including a manually authored document clarification with no asset model. Their linked brief
still assumed an operational trial: sponsor/operator, baseline, observation and comparable conditions looked
necessary for any packet. Missing fields could stay unknown, but the desk-based source question had no clear
way to record its result and next recipient without appearing to be an incomplete trial.

The same plain brief now starts with a source investigation: question, complete generated finding ID or labelled
manual reference, exact source identities/locators, evidence, missing records, qualified disposition, reviewer/date
and next recipient. Model/context references apply only where used. Unknown ownership or recipient acceptance
keeps the handoff marked needs owner. A source answer does not establish current installed state, governing
authority, operating permission or measured benefit. With no trial, the brief explicitly records trial not run
and benefit not measured instead of inventing a baseline.

If the team chooses a measured pilot, the extension retains the actual comparison, pretrial threshold, resource
and stop conditions, applicable authority and participants, baseline and observation, comparable conditions,
dated decision, fallback and receiving owner. A source disposition cannot satisfy that completion check. The real
site-pilot need N062 remains open. The context register is optional and still requires its supported model/graph
and question identities; a plain document question needs neither a fabricated model nor a new storage service.
The README, drawing bridge and lifecycle introduction use the same source-question-to-company-handoff path.

One independent AI reader filled three private copies: the Covestro manual source question with no model or
trial; the existing generated Bayer E18@model with all six asset references, its proposed partial answer and
three outstanding collection requests; and an explicitly illustrative planned pilot without observations.
The source drafts retain unknown owners and acceptance, and the illustrative trial remains insufficient evidence.
A second AI reader checked the authority/identity boundaries and fifteen relevant links/anchors. Neither
performed new runtime, plant or primary-source runs. Root checks retain sixteen existing pilot-field/completion
phrases and verify that runtime scripts, schemas and example outputs are unchanged.

These are documentation walkthroughs and manual checks, not tests of an automated completion validator or a
human adoption study. No new feature, corpus result, schema, integration or operational outcome is claimed.
Existing benchmark results and matrix cells remain unchanged. The proof of actual engineer use still needs a
real participant and observations; this repair only removes an unnecessary prerequisite for starting.

## 78. Keep the original I/O record behind an address assignment

The address mapper labelled parsed records as CSV rows. A blank line before a quoted multiline record made
those references wrong: records occupying physical lines 3–4 and 6 appeared as rows 2 and 3. The model also
retained no fingerprint of the supplied file. An engineer could inspect an assigned address without being able
to identify the exact original record from that assignment alone. The docstring's promise of live points and
the worklist's inference about what exists in the plant also exceeded what local address assignment proves.

The CLI now reads one raw CSV snapshot, fingerprints those exact bytes and records each parsed record's physical
line span. Assigned OPC mappings carry that fingerprint and span; the plan shows the filename, byte count and
digest. Blank lines, quoted newlines, UTF-8 BOMs and line-ending differences remain part of the source identity.
CSV columns cannot override the computed locator or fingerprint. Direct dictionary callers without source
metadata get explicitly logical row references, without an invented file hash or physical locator.

Matching, partial updates, explicit replacement and refusal policies stay the same. Repeating an identical
application is byte-stable. A prose-only source revision changes provenance without changing the address;
omitted mappings retain their previous evidence in partial mode. Legacy mappings do not acquire reconstructed
evidence. The exact synthetic fixture is pinned to LF in Git so its raw fingerprint reproduces across clones.
PI keeps its separate contract. Generated OPC addresses are unchanged, while the graph retains the new metadata.

The worked example explains what to retain with the investigation: the original I/O file and the reviewed plan.
Reports at the same name are still overwritten on apply, so they are current snapshots rather than a company
decision-history service. Fingerprints establish source identity, not authority, valid signal syntax, connection,
units, scaling or current plant truth. Unmatched records require reconciling both sources. The toolkit prepares
a checkable packet for the company's shared context system; it does not take over that system's responsibility.

The mapper's 26 tests pass. An independent AI controls reader runs 47 actual CLI commands and 166 adversarial
checks, including apply/repeat, source revisions, partial preservation, scoped replacement, atomic refusals,
newline/BOM variants, metadata spoofing and downstream generation/graph retention. Its three-step mapping
example reproduces the new report byte-for-byte with unchanged counts: 25 assignments, 10 model items absent
from this input, two unmatched source records and zero ambiguous rows. A separate AI reader checks the source
handoff and independently exercises dry-run revisions and locators; its apply/overwrite assessment is source-read
only. Root runs all seven worked-example commands; only the mapping report changes among registered outputs.
These are software and AI reader checks on existing public/synthetic inputs, not new corpus accuracy, receiving-
system acceptance, signal verification, human adoption or measured operational value. Matrix results remain
unchanged. Full-suite and CI logs retain their actual omissions separately.

## 79. Show what an incomplete first packet looks like

The starter already permitted a manual source question, a partial answer and an unassigned next owner. The
Covestro intake contained the question and supporting facts; the plain brief contained the fields. A recipient
reader found those instructions coherent, but a newcomer still had to assemble the handoff document. The new
filled brief shows that first result in one place without inventing a completed investigation or an owner.

It keeps the existing U0001 question, complete source identity, original fingerprints and exact workbook cells,
a qualified partial explanation, outstanding records and the next action. The cited records support identities,
function labels and connection references; they do not settle the intended behavior or establish a drawing error.
Reviewer, receiving owner, acceptance, current installed state and authority remain unknown. The trial is not run
and benefit is not measured. No model, generated finding or context-register entry is fabricated for this question.

The packet retains the complete seven-row transcription, unchanged originals, licence and toolkit revision used
for checking. Two commands let a colleague fetch just the three pinned originals into a separate cache and repeat
the existing source check offline. Root executes both from an isolated copy of the five required public files,
with no access to the original workspace's cache: three files, 329,011 bytes, both commands pass. A missing-original
control refuses with exit 2 and no output. This is a minimal receiving-copy software check, not a clean-clone or
human handoff experiment. The checker does not validate the new prose; original-cell review is separate.

The first-pilot guide and source-intake guide link directly to the filled example. A separate AI recipient reader
finds no consequential instruction or identity ambiguity and confirms the unresolved states remain visible. Its
review checks the CSV and document links, not the original workbooks. Source/controls review compares the factual
claims and raw fingerprints against the original records. Neither is engineering approval, observed adoption or
measured benefit. The next company home supplies ongoing access, ownership and decision history; no application,
schema, connector or new company workflow is added. Existing scripts, data, registered outputs, matrix results
and not-tried items are unchanged. No feature-output verdict or generalization result is renewed by this example.

## 80. Refuse a historian timeline that runs backward

The CSV reader checked time syntax and type, but not chronological order. Actual CLI probes accepted descending
and reordered exports and wrote negative detection delays: minus 3 in root's small fixtures and minus 80 in an
independent reader's example. A first-at-or-after timestamp lookup also selected the wrong row in file order.
Duplicate instants were accepted. The replay loader shared the same behavior. Separately, skipping blank CSV
records before counting rows made a physical-line-6 error appear as line 3.

The shared reader now requires strictly increasing parsed time/index values, with no duplicate instants. It
does not sort, deduplicate, aggregate or resample. Timestamp comparison uses the parsed instants, so different
UTC-offset strings for the same instant are duplicates; uneven increasing intervals and original value/text
associations remain supported. Record parsing retains physical spans through blank lines and quoted multiline
records. Data errors locate the offending record; an ordering error also cites the previous one. Existing generic
header-format guidance remains separate. Invalid normal or scored CSVs refuse before report creation or replacement,
and replay refuses before constructing its server.

Keep the raw export, prepare a separate chronological copy and record how duplicate records were reconciled with
their source meaning. Passing the check establishes neither clock accuracy nor uniform sampling. Detector windows
still count rows, and replay still advances at its explicit rate. Every existing detector function and constant
outside the reader is unchanged by AST comparison; replay implementation is unchanged below its module docstring.
This is input correctness, not a new anomaly method or a company context-management feature.

The 36 existing and added CSV tests pass, including sixteen band-CLI refusal cases, four replay-CLI refusals and
constructor tripwires. A separate controls reader executes 52 CLIs and 261 checks across order, offset, source-span,
bad-quality, valid-input and no-write cases; another reader checks the engineer's repair instructions. Old/current
valid reports agree byte-for-byte, including the committed TE default JSON and Markdown. Root's first Markdown
comparison omitted the guide's units option and differed only in that label; the corrected documented command
reproduces both outputs. The failed probe is retained separately rather than presented as a product failure.

The affected ten historian matrix cells are rerun against their existing inputs and criteria. All per-run metrics
and verdicts are unchanged; the other 84 cell records remain exact. This is compatibility evidence on previously
inspected sources, not another held-out experiment. Existing detector limitations and failed cells remain visible.

The full local run uses D: for temporary files to avoid C: disk pressure and completes 56 of 58 scripts, with two
unittest skips and two corresponding platform notices. Both failures expose the unchanged DEXPI image-path code's
inability to make relative links from C: sources to D: outputs. With only the temporary-file volume changed back
to C:, the two failed scripts pass all eight and 28 tests respectively. The original full-run failures remain
recorded; this chronology fix does not repair that separate cross-volume limitation. CI has its own exact-commit
result and omissions rather than inheriting a passing label from these focused retries.

A stale ledger marker is corrected too: N057's rolling/drift idea was already tried and implemented in A163/A171, with later cyclic
development in A183/A184. Marking that idea done does not claim the remaining false-alarm and detection gaps are
solved. No other not-tried item, source family, original record, scoring criterion or operational authority changes.


## 81. Make company handoff clear in the feature catalog

The README introduction describes a first engineering packet followed by a shared company home, but the
context-register feature still promised context the team could "maintain and own" and described a persistent
register without that next step. The example's recurring-refresh instruction could reinforce the impression
that local files were the intended long-term organizational system.

The feature now describes preparing a first evidence and decision packet for company handoff. Its result still
names the actual local report, dated records, open questions and portable JSON; the receiving company system
supplies shared access and ongoing governance. The example limits local refresh to packet preparation and
describes later tool use against released company snapshots, with its existing explicit-adapter and no-live-sync
limits retained. The question engine's investigative role and the document-only first-question path remain.

Only five descriptive feature fields change; tools, tests, example outputs, other features and corpus records
remain exact. Catalog generation and a separate AI engineer reader check the wording. This is documentation
clarity, not a feature-output review renewal, implemented connector, human adoption result or new operational
capability. A first useful investigation should make the need for retained company context concrete.


## 82. Keep the drawing with its DEXPI intake

The previous full run exposed a practical handoff failure: the public DEXPI converter could not form a relative
image path between Windows drives. An actual C01 CLI left a prediction and no manifest. The direct XML reader
avoided that exception by recording an absolute image path, but its intake still depended on the original
engineer's file location. Both observations are from local public-source staging, not a site import.

Both routes now retain an exact `<sheet-id>.source.png` beside the prediction and manifest, which reference local
filenames. An engineer can transfer those three files together before running the existing intake. The PNG hash
must match the prediction. An identical retained file is reused; a conflicting file, retained-image symlink or
generated-output/source overlap refuses before replacing generated reports. Use a fresh folder for a changed
drawing. The original XML and attribution remain part of the wider source packet; they are not automatically
copied by this image fix. This is single-writer local staging, not atomic publication of multiple files.

The direct reader prepares its PNG prediction before writing model/report files, so an image refusal no longer
leaves those reports replaced first. Model reading, conversion rules and score criteria are outside this change.
The committed C01 manifest remains an explicitly labelled historical cache-path record; current commands create
the retained-image intake. No original cache record or committed example result is rewritten to improve a score.

Focused controls pass 15 intake tests with one explicit OS symlink-permission skip and all 34 XML-reader tests.
The first matrix unit check correctly reports the 27 dependent cells as stale; its previous cross-drive exception
is absent. All 27 cells are then actually rerun under the existing criteria. Engineering metrics, details and
verdicts are unchanged; the other 67 complete records remain exact. Execution metadata includes 21 per-sheet
runtimes, and two citations move to identical text at new line numbers. Root's first private comparison omitted
the nested runtimes and stopped before publication; the corrected check isolates those exact fields. A separate
matrix reviewer verifies all 94 records and 732 current file hashes, retaining the original 63 pass, 23 fail and
eight n/a verdicts. These sources were already inspected; this supplies no new held-out or generalization result.

An independent controls reader runs 72 actual CLIs and 226 checks across 12 same/cross-drive cases on C01-C03 and
both routes. Relocated intake succeeds while each supplied original image path is unavailable. Source bytes,
prediction objects and XML model/report bytes remain unchanged. The direct reader's prediction text now uses LF
newlines; this formatting difference is kept separate from semantic equality. Two actual symlink controls are
explicitly skipped because Windows denies link creation. Another AI reader checks the transfer instructions.
Neither review supplies human approval, source-engineering correctness or measured adoption.

The full local run with temporary files on a different drive now passes all 58 scripts, including both previously
failing DEXPI/matrix scripts. It reports three unittest skips and two platform notices; notices do not add to the
skip count. The original failed run remains in the earlier chronology record. CI reports its own exact-commit
coverage and omissions. Only the matrix output review is renewed; existing feature/source review scopes remain.
The transfer mechanism prepares a first engineering packet for company handoff and adds no organizational
governance service or ready receiving-system connector.


## 83. Use risk tiers to order review, not accept items

The export guide still called red items more likely wrong than right and told a reviewer to spot-check green
items and accept the batch. The CLI help repeated that green was safe to batch-accept. Those instructions were
stronger than the evidence: the [saved Codex M3 holdout-A result](../out/triage_r2-tiles-trace_holdout-a.json)
records a red-tier observed error fraction of 0.230 across 191 output items. That historical result is not a
new-site calibration. Its truth test covers rough symbol class/location and keyed link endpoints; missing items,
tag text, parents, installed state and operating duty are outside that denominator.

The guide, review loop and actual CLI help now describe priority. A tier accepts nothing; sampling alone does not
accept the unreviewed remainder. Unfamiliar drawings need an agreed review plan against originals. Green does not
establish safety duty: the floor only recognizes its implemented tag/model-field rules on instruments and in-line
items. Independent source review also caught the old zero-weight duplicate-tag statement (its fitted weight is
small but nonzero) and the claim that the score tested correct labels. Both are corrected. The original round-3
goal and fitted threshold-rule text remain historical, with a dated current-use note rather than rewritten rules.
Source review also corrects the displayed holdout-A green-precision lower bound from 94% to 93%: the saved Gemini
M0 result is 93.4%. A dated correction cites that table; no stored result is changed or re-scored. The old round's
"calibration" label is qualified as its tier-order check, not demonstrated probability calibration.

Only the confidence module docstring changes. Removing that module docstring yields the exact old executable AST,
including all function docstrings and constants. Coefficients, thresholds, six recorded model outputs and every
saved triage file remain unchanged. Actual old/current help commands check the exposed wording. The two existing
recorded pipeline stages accept their historical files unchanged using the existing ACCEPT branch, with generation
subprocesses prohibited. The lock changes exactly their two confidence-source hashes; every output hash and other
entry remains exact. Stage notes and the lineage guide explicitly state that no extraction, build or scoring run
was repeated. This is source-binding maintenance, not reproduced extraction or new calibration.

The N054 audit finds a separate unresolved packaging gap. The documented default Ignition preflight exits 2:
its required manifest and browser contract are ignored and not committed. Native acceptance stays NOT RUN, also
when `--require-native` first encounters those missing inputs. The guides now state that limitation, the fixed
TE/OPEN100 scope and conditional held-package arguments. Synthetic tests do not supply actual candidate evidence.
The outdated release-version claim is replaced by instructions to use matching checkout files and record the commit;
the 2026-10-13 native receipts remain specific to their historical candidate.

The own-input contract is exercised separately on a task-owned receiving copy of the existing public OPEN100
sheet and saved extraction: `--check-only` writes no output, the build retains original image/extraction bytes,
and existing-output and duplicate-ID controls refuse. No plant data or model call is involved. Root's first
preflight wrapper wrongly expected a default success and stopped on the actual missing-manifest refusal; that
failed wrapper/output is retained, and the missing evidence stays a gap. No manifest was manufactured to make it pass.

All 45 existing pipeline checks and the existing risk/safety-floor controls pass. The 26 synthetic preflight tests
pass with one explicit Windows symlink skip. A separate AI engineer reader checks what a newcomer would follow;
independent source and provenance readers check the bounded evidence. No feature-output review, corpus score,
held-out result, operator approval or adoption claim is renewed. N054 remains not-done for the complete public
candidate-package recipe; N062 and N063 remain unproven. A first source question or evidence packet needs no gateway.


## 84. Start a refrigeration question with two sourced records

A fresh AI newcomer/recipient reading found no consequential first-use obstacle in the existing source-only brief
and drawing-to-question route. It did not justify another workflow feature. The refrigeration corpus still had a
concrete gap: the worked refrigeration questions used only the illustrative food model.

The new [Millard example](../examples/opportunity-screen/millard/README.md) starts from the official CSB January
2015 safety bulletin, No. 2010-13-A-AL. The PDF's exact bytes are pinned; its original asset URL returned HTTP403,
while the official file.aspx link supplied the 656,148-byte original. A fixed-case standard-library helper checks
the fingerprint offline and fetches missing bytes only with explicit --fetch. Changed local originals refuse,
including with --fetch, rather than being replaced. The original remains outside Git.

The model retains one authored aggregate and a hot-gas main valve from the simplified diagram/narrative. Their
identifiers are local labels, not plant tags. It deliberately does not reconstruct complete piping, devices or
logic. The existing E30 produces one finding over both records with three unanswered collection requests. Its
absence statement refers to this incomplete model, not actual plant absence or confirmed timer initiation.
Only E30 is selected; the other questions and safety functions have not been evaluated here.

The plain first-question brief separates that generated energy prompt from a manually authored question about
applicable controls records. Source review matters: the historical 20-versus-15-minute comparison concerns a
pump-out step, not defrost frequency, energy performance or a safe duration. The partial source explanation does
not complete E30's requests. The recipient, current authority, governing revision and accepted handoff remain
unknown; no operational instruction or configuration change is proposed. The company system owns continuing
stewardship when an actual recipient takes the packet. No context-register expansion or connector is added.

The original was read before choosing the subset, and a private feasibility run preceded the committed screen.
The acceptance note records that sequence. This is development evidence on an additional historical CSB case,
not a new independent source agency, held-out drawing test, full refrigeration model or accuracy improvement.
Independent source reading inspected the full original pages and simplified diagram. Five offline CLIs reproduce
the screen, remove the valve as a labelled anti-trigger, and check original/changed/missing source behavior. Root
runs six actual CLIs including the explicit download and preservation/refusal controls. All 51 existing question-
engine tests pass with the new fixture included. Software and engineer-reader receipts keep their narrower scope;
existing outputs retain their inherited reviews. Full-suite/CI coverage and skips are recorded separately.

The question engine/catalog, all earlier screens, matrix criteria and results are unchanged. Corpus registration
uses a separate question-packet entry outside the eight-workflow matrix. The catalog also binds that manifest
as matrix evidence, so its new metadata requires a narrow independent binding renewal: existing input objects and
all matrix results stay exact, and no cells are rerun. This does not renew the original execution/source audits.
No measured engineer adoption, energy saving, site approval or receiving-company round trip is claimed;
N062/N063 remain unproven.


## 85. Keep the operating context with a normal baseline

N056 proposed fitting longer normal-running windows. The source audit comes first: the inspected PRONTO day2-4
merged originals contain nine separate Normal blocks totaling 11,899 records; the longest is 2,770 one-second
records. A source label is not an operating-mode definition. Measured air/water values differ between and within
blocks, and the operation log separately records nominal settings, health labels and flow descriptions. All 14
original members inspected by the independent source reader match their pins and remain unchanged. No contiguous
qualified multi-day normal baseline is established by that cache subset.

One preliminary identity guess was refused before publication. The log's Test3 Normal row is not the second
merged day2 Normal block: exact raw alignment puts that block later, beside later logged actions. The brief
preserves the supplied labels and asks for reviewed time/identity joins instead of manufacturing a source conflict.

The independent methods review fixed four paired comparisons before new band runs and rejected pooling disjoint
Normal blocks. Preserving timestamp text would not preserve filter dynamics: the row-based drift method treats
those records as adjacent across gaps. No gap policy or detector change was added. For each accepted pair, a
short recent labeled-normal segment fits/selects K before both choices score identical later rows. The earlier
baseline and recent candidate use the same frozen drift method, fit fraction, K search and diagnostic criterion.
All cases are development data already inspected; the recent candidate is shorter in every case. Context, length
and noise history change together, so this is sensitivity evidence, not a causal mode study or prospective rule.

The [comparison](../examples/historian-csv/baseline-context/expected/results.md) retains mixed outcomes: early
baselines meet the diagnostic in three of four cases, recent candidates in two. Day2 pre-fault flags change from
155/181 to 0/181, but day3 leakage changes from 0/150 to 17/150 and day4's second slugging case from 0/1,385 to
895/1,385. Those two recent candidates also miss K's calibration target. Day3 diverted-flow detection moves from
1,922 to 7,290 seconds, near the end of its 7,320-record fault interval; a criterion pass does not establish prompt
detection or causal attribution. Every complete band result, source fingerprint, range, warning and bad-sample
count is retained. Companion log cells and source metadata were added after the first run; all complete scored
case objects stayed exact.

The paired scoring start resets both filters, and three cases reach the fault before 600 good scoring samples.
There is no carried history or extra discarded burn-in. The shorter scoring population is different from the
original matrix: day4's early baseline is clean on the common prefix while its separate original full-score
control remains 492/2,770 flagged. All four full-score controls match the existing matrix metrics. The paired
counts cannot replace those older populations. No method, default, threshold, source label, matrix cell or
headline accuracy changes.

A fresh AI engineering/LinkedIn-reader perspective supports the narrow usefulness of a baseline-applicability
case even when recent data is worse. The resulting plain brief asks which operating/configuration and mapping
records establish comparability and who reviews that choice. Ownership, governing authority and acceptance stay
unknown. It creates no automated baseline selector, local governance service or company connector. Independent
source, methods, software and wording checks retain their separate scopes; repetition and CI coverage are
reported separately from any human outcome. N056 remains open for qualified longer multi-day data; N062/N063
remain unproven.


## 86. Take a written description to one question before drafting

The previous goal turn published the fixed baseline-context investigation; that is completed progress, not a
reason to add another toolkit feature. The next reader pass looks for a consequential obstacle in the existing
on-ramp. The written-description guide has one: it takes an engineer from a sourced model into platform files
and a manually authored drawing layout, then ends without showing the first-question and company-handoff route.
The root guide already explains that route, so this is an entry-guide omission rather than a missing capability
or proof that a real engineer was blocked.

The revised guide puts the existing offline question engine before optional outputs. An actual full screen on
its exact committed Bayer model produces 12 findings; its complete `E18@model` object matches the existing
single-question example. The engineer can take one finding's exact ID, asset references and missing-evidence
requests into the plain brief, retain source revisions and qualified answers, and identify a company recipient.
A source-text clarification can begin without any model. No new drawing, drafting layout, platform import or
model call is needed for this first investigation.

The existing partial-answer example remains an optional worked illustration, not a required local register.
Unknown ownership and acceptance stay visible. Shared maintenance, decisions and history belong in the company's
home as the work grows. This change adds no governance application, adapter, document synchronization or company
round trip. It neither re-audits the historical report/model nor changes the catalog, tools, committed screens,
matrix or accuracy claims. AI reader/CLI checks establish a runnable route, not human adoption or benefit;
N062/N063 remain unproven.


## 87. Take CAD exports to a first question, with their limits

The preceding goal turn published the written-description bridge. This pass checks the two CAD entry routes
against the same first-use purpose. Both guides previously ended at models, bundles and platform exports without
showing the existing question-to-brief and company-handoff route. An independent engineering-reader pass confirms
the omission; this is a guide repair, not a new software capability or observed human adoption result.

Actual offline commands reach the question engine through both representations of public C01. The direct XML
reader's model yields three questions (`C2@model`, `C3@model`, `C9@model`); the converted-key intake bundle yields
one (`C9@model`). The reduced classes, undirected links and omitted controls/attributes differ, so these are not
accuracy scores or evidence that more findings are better. Check each question against its model, conversion
report and original source. Retained DEXPI attributes are not automatically normalized screening fields, and
design values are not measured operating conditions. The source model, catalog and tools remain unchanged.

Public C03 supplies the boundary case: the XML reader succeeds, keeping three streams, one manual valve and one
unplaced item, but has no units or instruments. The question engine refuses that model before publishing output.
The guide now names that limit and directs the engineer to a labelled manual source question in the same plain
brief, rather than inventing equipment or treating conversion success as universal screening compatibility.

The direct guide separates reading and questions from optional graph/platform outputs and offers a screen on the
committed C01 model without downloading XML or running a renderer. Both guides carry exact finding/asset IDs,
source revision/hash/locators, omissions and missing evidence into the existing brief and company handoff. Unknown
ownership and acceptance stay visible; shared maintenance and decisions belong in the company home. No local
register, native import or new connector is required for that first packet.

Independent verification includes seven workflow CLIs with the expected C03 refusal; an earlier unsupported
`--quiet` probe is retained separately as a usage error, not counted as a successful route. The root separately
screens the committed C01 model. These checks do not repeat the historical primary-source, platform, portability
or whole-feature audits. No matrix result, corpus input, generated screen or criterion is changed, and no source
meaning, current plant truth, review-time saving or company round trip is newly established. N062/N063 remain
unproven.


## 88. Reconcile a corpus candidate before calling it independent evidence

The previous goal turn published both CAD question routes. This pass returns to the corpus backlog rather than
inventing another onboarding feature. Its pyTEP candidate calls the package a BSD-licensed independent control
implementation, while a separate registry entry already leaves the Ricker multiloop model's file-level terms
unresolved. A repository label and a separately published implementation are insufficient provenance for the
planned comparison.

The inspected source pin is `7caf477b049a488f819e80802ed4fef85e6a435b`, already retained in the ignored inspection
cache. The old repository URL redirects to `ccreinartz11/pytep`; the registry now links the exact commit. Its root
notice credits DTU under BSD-3-Clause. The simulator README attributes its multiloop strategy to Ricker's 1996
work and distinguishes mode 1 from mode 3's additional override. The model records creator `ricker`. These facts
support describing a Python wrapper using a Ricker-attributed TE configuration, not a newly independent process
family or proof that its control scheme should match the Braatz-based drawings.

No explicit Ricker-file exclusion was found in the inspected license, READMEs or model. The previous registry
phrase asserting such an exclusion had no source citation, so it is replaced with the actual evidence and the
existing unresolved file-level review. This is not a legal conclusion or resolution of that review. It neither
declares the model unusable nor treats the root notice as sufficient to settle its applicability.

One candidate and its corresponding unresolved record change. The generalization page is rendered from the
unchanged matrix; no cell is dispatched and no loop list, new input, benchmark score or derived model is made.
The fetch guide's matching row is reconciled too. Its stale opening no longer calls all added datasets unseen:
later methods used several in development, and the guide now points to their per-method experiment history.
Exact raw cache Git-blob identities match the pinned GitHub objects; SHA-256 fingerprints are retained separately.
Connected source text is used for reading, not as a substitute for raw-byte identity. The original cache remains
unchanged. A separate review checks this provenance correction and renews only the matrix feature's changed
metadata bindings, inheriting earlier substantive/source/execution scopes with their limits.

The next corpus experiment must still choose an applicable source, define its control scheme and operating
scope, map its identities and retain what the comparison cannot represent. This correction adds no toolkit
governance service, receiving adapter, new independent-family result, human adoption or operational benefit.


## 89. Preserve the inputs to the first question

A disposable copy of the Bayer model named `questions.json` exposed an actual first-use defect: writing a screen
to its containing folder replaced the model with the generated questions. Equivalent collisions exist for the
catalog, loop list, repeated schedules and roll-up inputs. Two aliased output files can overwrite each other;
an invalid second destination can also leave a partially replaced report pair. The original repository inputs
were not used as destructive test targets.

The existing question engine now checks its complete pair of destinations before creating a directory or writing
either file. It protects the concrete inputs it read, including optional local I/O descriptions used for mapped
points. Roll-up loading and protection share the same input selection. Resolved paths and existing filesystem
identity cover alternate spellings and links. An ordinary file in the parent chain, non-file destination or
output-output alias is refused. Both strings are rendered before publication, so a rendering exception leaves
the prior pair untouched. This preflight is not a concurrent-writer lock or an atomic two-file transaction.

Normal generation and repeated refresh into an existing folder remain valid when source and report filenames
do not collide. Question rules, catalog, model schemas and committed example outputs are unchanged. Regression
checks exercise source preservation, repeated schedules, implicit I/O reads, links, invalid destinations, render
failures and valid reruns. A Windows file-symlink privilege refusal is recorded as a skipped test rather than a
pass; hardlink and directory-junction checks are separate evidence.

The independent final run executes 47 direct subprocesses plus six child CLIs in the existing review-refresh
example, with 200 assertions. The same Windows file-symlink privilege limit remains explicit. Twelve existing
screen/roll-up files regenerate byte for byte; the existing demonstration checks the three review-refresh
outputs. All 15 registered outputs match the preceding checkpoint. These are compatibility and file-preservation
checks, not a renewed audit of the models' engineering interpretations or catalog sources.

The screen guide also keeps the first-use destination clear: take findings, source revisions, answers and missing
evidence into the plain question brief, then the company's shared context and decision system as colleagues
contribute. This is a repair to the investigation on-ramp, not an extension of the local context register or a
new governance application. No operating benefit, human adoption, receiving-system adapter or accepted company
handoff is established by these software checks.


## 90. Keep the question catalog with the first packet

The source-preservation repair is published before this pass. A fresh engineer-reader check asks what happens
when the first question comes from a company-specific catalog. Five disposable baseline CLI calls demonstrate
that the screen uses the supplied question text but labels the repository default catalog in its JSON, Markdown
and printed screen. Roll-up JSON has the same wrong label. Another catalog can reuse the question ID and silently
substitute its question and decision rule while retaining collection instructions from an earlier screen. A
separate reader reproduces both defects with five actual offline calls on fictional catalog variants.

The existing catalog field now names the actual selected file in screen and roll-up modes. A custom roll-up's
Markdown names it too; paths outside the repository remain filenames rather than private absolute directories.
Before combining findings, the loader compares their embedded question, family, decision rule, benefit and
limits with the selected catalog, and checks emitted collection item/instruction pairs. Visible conflicts are
refused before publishing either report. Missing/non-string question IDs, malformed request lists/items and
conflicting instructions for one selected-catalog request item have explicit refusals as well.

This is not proof of whole-catalog equivalence. Trigger rules, exclusions, some source metadata and the meaning
of quiet/unrun questions are not present in a finding. A missing request may have been satisfied by drawing facts.
The plain first-packet brief therefore retains the actual catalog file, revision and content hash alongside its
source/model references. After rule changes the engineer reconciles the catalog and regenerates the screens;
matching IDs or filenames alone cannot establish the same investigation. That remains a manual evidence step,
without a new schema, local versioning service, approval process or company connector.

All 15 existing opportunity outputs, the committed catalog, question matching and models remain unchanged. The
regressions exercise both custom output modes, compatible catalog copies, visible definition/request conflicts,
malformed records and preservation of existing report pairs on refusal. These software checks establish accurate
attribution and bounded conflict detection for the first handoff, not source authority, a governing revision,
full catalog compatibility, human adoption, engineering approval or operational value.

The independent completed audit runs 54 direct CLIs plus six children in the existing refresh demonstration,
with 205 checks and 29 byte-preserving refusals. Twelve registered report files regenerate exactly and the
wrapper checks its three expected artifacts; all 15 also match the preceding checkpoint. An extra Bayer E18 pair
is separate bridge evidence. Seven accepted residual cases exercise the documented limits rather than passing
them off as whole-catalog validation. A private harness initially compared Windows stdout newlines with report
bytes; that comparison was corrected, its failed attempt retained, and the repeated bounded run disclosed.

The filled Millard brief demonstrates catalog retention with a pinned catalog revision and hash of its committed
LF bytes. This is a catalog citation check, not a new audit of the original incident report or current plant state.


## 91. Start a manufacturing-records question before the local register

The catalog-provenance correction is published before this pass. A fresh controls/early-career reader follows
the existing NIST SMS packet and finds a route gap: fetch leads into model/register preparation and application,
without showing the plain source-question and recipient brief already supported by the pilot guide. That
overstates the setup needed to begin an engineering investigation from configurations and a log.

The NIST guide now starts with a plain manual question: which deployed device configuration and adapter mapping
interpret the selected archive, and what links that revision to the recording time? It uses the existing original
files and source manifest, requires no model, question catalog or register, and asks a controls/configuration or
manufacturing-data owner for the missing records. The register reproduction and history checks stay optional.
The first-pilot and context-example indexes expose the same route and company handoff.

The worked brief preserves the two published meanings of `Hurco04-path_7` under their configuration revisions.
The machine UUID joins the two XML device records; it is absent from the archived log. The independent reader
caught the index's older wording implying that all three records share that UUID, and the index now makes the
distinction explicit. The raw runtime-named row at physical line 46 retains its timestamp and literal zero. Its
name alone does not supply a deployed revision, verified DataItem mapping, units, production result or current
machine condition. The complete supplied log has 363 three-field records and identifies no deployed configuration.

Four connected reads of the pinned upstream files match the cached UTF-8 bytes exactly: 121,831 bytes across
two configurations, the raw archive and the reuse notice. The existing source verifier checks all four pins and
ten explicit original-source groups; the new line-46 citation is checked directly against the original too.
The new brief is AI-authored development documentation selected after these source facts were inspected, not a
held-out result, new source family or added generalization cell. Original files, model, questions, answers and
registered outputs stay unchanged. Existing whole-feature reviews are not renewed by this documentation pass.

A separate reader re-reads the cited XML and complete raw archive, checks the four final documents and their
29 local links, and closes both the route gap and UUID wording finding. That reader runs no feature CLI; the
root separately exercises the existing cached fetch and source-verifier commands. No prepare/apply/history or
full local test-suite rerun is claimed for these prose changes.

Ownership, acceptance, governing authority and deployment remain unresolved. The first packet goes to the
company's shared context and decision system as participation grows; this adds no local governance, adapter,
history service or operating-value claim.

## 92. Keep the starter route and its historical evidence distinct

A completion audit keeps the product boundary at the first useful engineering packet: an engineer starts with
documents, investigates a sourced question and takes the evidence and decisions into the company's shared
system. The existing local register remains optional. This pass adds no application, governance service,
adapter or new corpus input.

The fresh skeptical reader finds a consequential tutorial error. README step 9 used the current TE drawings
with revision-A run labels and historical twin/score destinations. Following it would be a new experiment under
old names, with the scorer's default current keys, rather than a reproduction of the cited evidence. The step now
uses saved-prediction re-scoring against each recorded revision. A future extraction needs a new prefix, unused
outputs and explicit matching keys. No new extraction or commercial-model call is made here.

Two stale guide claims are corrected too. Evaluation section 7 retains the original layered-review result and
adds the completed historical 75-statement r2 review, including its item error and unclear case. Neither is a
measurement of today's full population. The unfinished N059 idea retains its missing model-symbol/scan work
while acknowledging that historical review. The lineage guide now explains the runtime stages' actual lock state:
their accepted entries show fresh declared inputs, with no runtime output files declared. Historical gateway
receipts are separate evidence; freshness neither verifies those receipts nor repeats a gateway run.

The two documented TE commands regenerate revision A in its explicitly supported historical format and
revision C exactly. Re-scoring the saved r2 review reproduces its layer-specific rates. The cached-data suite
also runs all 58 selected scripts with no failures and four skipped unittest cases on this Windows account;
two platform notices explain skips rather than adding cases. This is not a complete-suite or native-runtime
acceptance claim. These checks concern the existing prototype and its records, not engineering approval,
organizational adoption or measured operating benefit. Registered example outputs and their existing
whole-feature reviews remain unchanged by these documentation corrections.

## 93. Bind confidence traces to the drawing bytes

A current reproduction of the complete matrix executes all 94 cells at the previous code revision, with
63 pass, 23 fail and 8 n/a verdicts. Every metric, reason and substantive result matches the committed matrix.
Seven published-reference line numbers move with intervening documentation edits; each is checked against the
same source passage. This is present-day reproduction, not recovery of an unlocated historical command log or
a fresh held-out evaluation.

That verification exposes a separate defect: the confidence trace cache keys the image path, symbols, options
and tracer code, but omits the image bytes. Replacing a private copy of a TE drawing with a blank image at the
same path returns its old 18 networks; a fresh cache returns zero. A synthetic real-tracer control also reproduces
the problem when the revised file retains its timestamp. Missing source images can be hidden by the old cache.

The key now includes the image's SHA256 digest, read before a cache hit. Controls exercise unchanged reuse,
changed-byte retracing, no inherited networks, revised-image reuse and refusal of a missing image. Fitted weights,
thresholds, safety rules, tracing and scoring methods do not change.

The matrix also omitted confidence.py from its tool bindings because the builder imports it dynamically. Three
explicit intake-route declarations add the dependency to exactly 17 cells. Native-reader overrides remain
separate. The currentness check now refuses an omitted required dependency, as well as a changed recorded hash.
This is a maintained declaration of a known dynamic import, not arbitrary dynamic-import discovery. Negative
controls cover changed confidence code and a removed builder binding.

All 17 affected cells are actually re-executed after the fix. Their engineering results are unchanged; the other
77 complete cells are retained exactly from the current whole-matrix run. The resulting 94-cell matrix still
reports 63 pass, 23 fail and 8 n/a. These refreshes are deterministic checks of existing inputs, not 17 new corpus
items, new source families or prospective trials.

Five historical revision-A twins are then rebuilt with separate empty confidence caches from hash-bound preserved
raw run records. Clean images match revision A; degraded cases use the recorded L2/L3 images. Full parsed model
comparisons find no differences after only the exact source-run directory relocation. A private copy of the
current OPEN100 model is re-annotated from preserved extraction records for the public drawings with an empty
cache: zero field differences, with
all three existing ops_review records preserved. Public models are not overwritten. The existing pipeline record
command renews just the two affected recorded stages after these checks; a fresh lock alone does not prove them.

## 94. Design the next connections for a Copilot-only engineer

The connectivity guide starts with an engineer who has company-approved Copilot, restricted installation rights
and sensitive manufacturing records. The first investigation uses explicitly permitted documents and a source
brief, with a manual evidence route where the available experience cannot retrieve them reliably. It does not
require a coding agent, a personal subscription or a local Python installation for that reader.

Primary Microsoft documentation distinguishes selected-file Copilot Chat, organizational grounding, SharePoint
agents and Copilot Studio extensions. The guide keeps their licensing, source permissions, connector policies
and actual channel behavior conditional. An internal MCP server is a later access layer; a local stdio developer
experiment is not a ready endpoint for the documented Studio Streamable transport. No company tenant, account,
private document or live data source is used or configured in this work.

The proposed connection order is approved document revisions, reviewed asset/signal identities, bounded historian
observations, maintenance events and a returned draft finding in the company's review process. Process data does
not establish identity, causation or an accepted decision by itself. Food and beverage examples start with
synthetic or explicitly cleared utility/equipment records. Original quality records and changes to sanitation,
process limits or release decisions stay in the company's existing controlled processes.

The user's operations-network constraint is explicit: some sites permit no ports across IT/OT. The guide now
separates disconnected snapshots, existing one-way replication and an explicitly approved cross-zone service.
An OT-local MCP service does not make cloud Copilot reachable. No tunnel, reverse relay or firewall change is
proposed as a workaround; unavailable or aged observations must remain labelled as such. NIST's published OT
guidance and unidirectional-gateway definition support those distinctions. No network configuration is changed.

The guide distinguishes exact JSON/CSV engineering exports, the proposed additional OKF knowledge bundle, MCP
access and process-data interfaces. Canonical OKF 0.2 and Google's October 22 announcement support the format
direction; no OKF exporter or Google import is implemented or validated here. No MCP server, live connector,
company governance application, compliance certification or measured adoption benefit is claimed. These are
next-step integration instructions and boundaries for the on-ramp, not additional shipped features or corpus runs.

## 95. Separate description interpretation from drawing generation

A reader asks how well a process description becomes a P&ID and whether that result is in the matrix. The matrix
does not measure that complete transformation. Row 5 calls the platform exporter on already structured models;
rows 4 and 8 check loops and known-box tracing on existing drawings. The description guide now maps each claim
to its actual evidence and distinguishes the authored model, authored layout, generated key and rendered image.

The Bayer model's four initial errors, subsequent 20/21 reference comparison and remaining nozzle difference
stay visible. Its 15/15 drawing-line comparison reads the generated routing key. Separate TE/Bayer regression
controls trace the committed PNGs with supplied symbol boxes and compare recovered links with their keys. Those
checks establish different things; neither estimates interpretation accuracy on unfamiliar descriptions or
operator acceptance. The test source contains 18 generator/Bayer controls, five scorer controls and three model
diff controls, not 26 tests of prose-to-P&ID accuracy.

Evaluation section 8 states the missing experiment: freeze allowed source material and independent facts, retain
unknowns and conflicts, freeze interpretation before drafting, assess actual rendered output, exercise deliberate
errors, and report initial submissions separately from corrections. It is a prospective plan, with no new score,
new held-out source or measured review-time claim.

An independent reader checks the two revised documents against their source contracts and saved results. All
112 registered example outputs, matrix criteria, cells and existing whole-feature reviews remain unchanged. This
is a documentation and evaluation-scope correction; no generator, model, layout or answer key is changed and no
new model call or matrix execution is claimed.

## 96. Add bounded read-only access to a first engineering snapshot

An optional MCP server now reads one selected twin-graph-1 file at startup and serves six tools plus a summary
resource. Assets retain their full sourced claims and statuses; relationships retain types and direction;
existing questions retain their evidence requests. Search, relation and question lists have stable offset
pages tied to the same input SHA-256. There is no source fetching, process-data connector, decision acceptance
or write tool. Review events are counted in the summary but are not served by this initial interface.

The official Python SDK is pinned separately so the base toolkit and Copilot reader path need no additional
dependency. Actual SDK checks exercise in-memory, stdio and loopback Streamable HTTP clients in two negotiated
protocol modes, compare the full public example asset/relations/questions, and confirm sessions survive expected
errors. Larger synthetic packets exercise complete traversal beyond each per-call limit. The base suite adds
stdlib packet controls; the optional CI job runs the maintained SDK/transport checks separately.

Independent private review found that a limit on the application JSON alone missed the SDK's duplicated text
and structured content, with escaping enlarging resource results too. The server now constructs and measures
the serialized successful MCP result, including both copies and escaping, with an allowance for pinned SDK
metadata. Actual oversized ASCII and escape-heavy results refuse; accepted Unicode and near-bound results
retain their content. The bound excludes arbitrary outer JSON-RPC request IDs, framing and framework errors.
The original finding, source snapshot and corrected-code review are retained privately; this was a real defect,
not a hypothetical guard. Inputs remain capped at 32 MiB and successful result data at 2 MiB.

Stdio opens no listening port. The optional HTTP listener is fixed to loopback and has no company authentication.
The guide describes it as a developer starter, not a shared service or an endpoint cloud Copilot can reach.
Company access control, published Copilot channels, historian integration and OT network architecture need
separate implementation and acceptance. No firewall, tunnel, tenant or company data is configured. A site that
allows no cross-boundary ports stays disconnected, using only a separately approved released snapshot if allowed.

This adds an access layer to the engineering on-ramp. Existing company systems still own source authority,
permissions, continuing decisions and execution. No new matrix cell, unfamiliar-description generation score,
native import or measured operational benefit is claimed.

## 97. Separate the workflow connection map from example evidence

The user expects the hub-and-spoke matrix to explain what the toolkit actually connects. The front page instead
combines a conceptual workflow diagram, feature examples labelled proven, and a corpus matrix of eight selected
workflows. Those answer different questions. In particular, the written-description feature names an entire
route while its two registered commands require model JSON and a drafting layout that already exist.

Actual local command probes confirm that raw narrative is refused by the export and P&ID commands. A portable
graph is refused by the platform exporter and question engine. Positive controls export the existing authored
Bayer model and validate its authored layout. This is an input-boundary check, not a new interpretation score
or corpus experiment. Original model, layout, graph and generated example bytes remain unchanged.

The README now has a current connection map: assisted description authoring, supported drawing/XML readers,
working-model inputs, the detailed P&ID renderer, one-way graph export, graph-based review/context/MCP tools,
separate measurements, local corrections and the later company-system handoff. Missing raw-text intake,
automatic detailed layout, general graph-to-model conversion and company integration are visible at the relevant
arrows. The authored-layout requirement is distinct from the automatic logical SVG placement in generate.py.

Feature tables now say reviewed example rather than proven. Review selection and recorded output hashes keep
their existing rules; the wording does not imply an automated complete route, universal format compatibility or
plant acceptance. The description feature is named for its actual model-input commands. No review is upgraded,
no source score changes, and no new converter, agent service or shared company hub is claimed by this correction.
The catalog's general review description also drops a universal blind-review claim: the retained records state
their own scopes, including iterative corrective reviews. No historical record is rewritten.

Completing the description route remains implementation work: a company-approved assistant authoring flow must
preserve source locations, unknowns and assumptions, produce valid model/layout inputs, render them, and return
useful validation feedback for review. Its end-to-end evaluation still needs the separate source and rendered
output checks described in evaluation section 8. A documentation caveat does not complete that missing workflow.

## 98. Connect description authoring to the actual review bundle

The standalone renderer needs a model and drafting layout. The missing practical connection was a packaged way
to give an approved assistant the source and format, check its response and run the downstream tools together.
`description_workflow.py` now supplies prepare, check and build commands. Preparation preserves raw UTF-8 source
bytes, numbers the lines and writes a prompt, contract and separate illustrative answer. The engineer uses the
company-approved assistant, then saves its JSON response. The command calls no model API and assumes no working
Copilot tenant or particular file-transfer channel.

Checking requires source spans and exact quotations on represented records, unknowns and assumptions, supported
model references and a bounded layout. Building renders the draft PNG/SVG P&IDs, exports logical/platform staging,
runs the question engine and exports the graph. The bundle keeps the source, authored answer, model and layout,
validation, review instructions and payload hashes together. Existing destinations are refused. It is an initial
review packet; the company retains continuing authority, ownership, decisions and execution.

Actual independent probes caught important errors in the first private candidate. A layout could draw a different
endpoint while the graph retained the model's connection; an unknown stream could be added. An unsupported
controller output key still drew a signal but silently lost its graph edge. Extreme column coordinates reached
a native rendering loop before geometry validation. A model tank could also be drawn as a pump. These cases now
have early consistency/type/bounds checks and regression controls. Tees resolve the parent route's corresponding
upstream/downstream endpoint; paired off-page flags connect complementary route pieces. Ambiguous networks,
unsourced utility routes and unsupported symbol choices return feedback instead of a guessed simplification.
The standalone historical renderer's broader contract and existing outputs are unchanged.

The corrective review also found that an answer could replace the drawing's notes with an operating-approval
label while leaving the model unverified. The first-draft route now requires a fixed DRAFT revision and the four
reference disclaimers on every drawing. This protects the drawing's own status when it travels separately from
the rest of the packet; it is not semantic detection of every misleading statement in arbitrary source text.

Three authored illustrative development fixtures build: a simple water utility, a branch with cooler recycle,
and a two-sheet continuation. The generated branch drawing was inspected, and the tests check preservation,
inventory completeness, native output creation and planted conflicts. They do not measure a model's ability to
interpret unfamiliar prose. A deliberate incorrect equipment name with a genuine quotation still passes the
format check: quotation matching locates evidence, and a person must assess what it supports. Readable labels,
physical nozzle attachment, source authority/completeness and actual plant correctness still require review.
No automatic detailed layout, tenant deployment, operating acceptance or new corpus score is claimed.

## 99. Make corpus contributions and task/model comparisons reproducible

The project already retains public corpora, parsed predictions, scoring controls and an attempts ledger, but
contributors must understand several research-specific entry points to add evidence. The new contribution guide
connects source/key registration, saved model/method answers, offline scoring, failure analysis and baseline
regression checks. PR and corpus-issue templates request provenance, development exposure and regressions. The
benchmark registry is separate from the eight-workflow deterministic matrix and from feature-example reviews.

`benchmark.py` has two task adapters. Drawing extraction uses the existing frozen scorer and vendor controls,
without changing their rules. A first registered snapshot re-scores the saved round-5 Claude and Codex predictions:
five replicates each, six OPEN100 validation drawings. These are historical runs registered retrospectively, with
the original model identifiers, recipe/input fingerprints and dates. Exact provider builds and unrecorded settings
stay unknown; the method includes deterministic tracing. No new model call or held-out experiment occurred.

The description-fact adapter measures only literal selected native-model fields against explicit fact atoms.
It reports categories and missing/unexpected facts separately; a wrong stream endpoint cannot disappear behind
an aggregate of equipment fields. Its initial two cases and three methods are synthetic reference/empty/wrong
controls. The keys derive from the authored reference models, so this is circular scorer development, not
independent evidence about interpretation. Unfamiliar descriptions still need separately prepared source truth.

Comparisons retain task, family, split, evidence type, exact attempted cases, source/key and scoring-code hashes.
Versions, interfaces, prompt/recipe and method settings remain separate. An attempted missing/failed/invalid answer
scores empty; a new case an old run never attempted remains a coverage gap. The old run keeps its comparison
cohort; a run attempting the expanded set gets a different cohort.
The report keeps per-case counts and optional reported resources, with mean/range/SD over repeated runs. It does
not declare a statistically significant winner or pool unrelated tasks into a universal model ranking.

Independent adversarial baseline probes exposed schema-label bypasses of saved metadata checks, hardlink aliases
counted as separate replicates, and contradictory declared interface/tiling settings. The candidate now checks
recorded model/input/prompt/tool and supported settings regardless of the envelope schema, and uses physical file
identity to refuse alias replicates. Metadata remains contributor-declared rather than provider-attested. Keys and
recipes are fingerprinted; changed bytes fail validation instead of being misreported as model performance.
Existing reports are refused as write targets, and CI re-scores the registered snapshots offline. Other toolkit
functions retain their existing tests/matrix evidence and have explicit evaluator gaps; no all-function benchmark
coverage, new corpus family, company acceptance or operational performance is claimed.

## 100. Reproduce benchmark cohorts across Windows and Linux

The first benchmark release passed all 61 CI test scripts (17 unittest cases skipped), but its new registry
step failed to reproduce the committed reports. The scoring-code fingerprint helper normalized declared text
formats but omitted Python. Two unchanged scorer dependencies had CRLF in the Windows checkout and LF in Git;
their raw fingerprints changed cohort IDs on Linux. Main was not promoted after that failure.

Python code now uses the same CRLF-to-LF normalization as other declared text inputs. A regression creates
actual LF and CRLF copies of all six scoring modules, evaluates the complete saved drawing suite with each
code binding, and compares JSON and Markdown exactly. It also checks that a real source edit changes the hash
and binary newline bytes remain significant. The 13 benchmark tests pass locally. The previous four reports
are retained in release evidence; regenerated controls, per-case counts, metrics and run metadata are unchanged.
Only code/cohort/group identifiers and their ordering change. This repair adds no model run, case, source key,
held-out result or new task coverage. The initial failed release and its earlier review remain in history;
portability review and final CI are recorded separately.

## 101. Follow one asset through the connected toolkit

A high-level connection map can still leave a reader unsure what happens to one actual asset. The new P-1
walkthrough follows the existing authored water-utility source through its model records, draft sheet, generated
question E1@P-1 and graph, then explains the first evidence packet and receiving-owner gap. It links the actual
files rather than substituting a presentation mockup for a working output.

A fresh prepare/check/build run reproduced the committed model, graph, questions and drawing. A direct
in-process snapshot-class read returned P-1 and E1@P-1; that is data-path evidence, not a new MCP protocol or
Copilot deployment test. The five evidence requests remain not_on_drawing. No operating history, pump curve,
measured benefit or accepted handoff is supplied. The question engine finds a pattern in the authored model;
it does not establish that a speed drive is absent, that the pump wastes energy, or that a change is justified.

This is a navigation and explanation improvement over an existing authored fixture, not a new public source
family, independently keyed interpretation benchmark or new corpus result. The structure/quotation/layout
checks still need engineering review. Ongoing ownership, governing revisions, access and decisions remain the
company system responsibility. No tool contract, scoring rule, registered output or matrix cell changes.

A fresh independent coding-agent reader, taking a plant-engineer arrival perspective, reproduced all three
workflow commands, checked six in-process snapshot methods and compared seven selected outputs byte for byte.
The reader checked the linked files and rendered drawing/graphic, with no factual blocker. The suggested arrival
improvement was a direct walkthrough link in the accompanying caption. This is a narrow documentation/data-path
review, not human engineering approval, a new protocol test or a renewed review of every feature.

## 102. Separate a source clarification from a model improvement

The MGPI transfer-path case extends description work beyond the authored water-utility fixtures with a
project-authored adaptation of a public CSB report. A separate coding agent made a bounded original-narrative
inventory/key without seeing the initial candidate. Both were frozen before comparison. The author had seen
Figure 3 during scouting, so this is development evidence, not a blind original-description model trial.

The initial adapted input placed a level indicator on the bulk tank, but the permitted paragraph only said
tank. The model followed its supplied input: the source adaptation, rather than language interpretation, was
unsupported. The V1 native comparison retains 26 matched facts and one unexpected placement. The next original
sentence explicitly identifies the bulk tank. V2 enlarges the allowed source/key and adds exactly that fact;
27 matched facts therefore cannot be reported as an algorithm gain. Both versions, their scopes, the first
failed review and post-review exposure remain separate. These are agent keys, not CSB keys or human approval.

The current two-sheet draft bundle is built through prepare/check/build. Distinct chemistry paths and proposed
geometry remain explicit; BL is a scope boundary, not a physical mixing junction. Original report figures are
not republished. Capacities, concentrations and notification-only alarm action remain sourced draft attributes.
The literal native-fact scorer grades none of those attributes. Empty/wrong-endpoint controls are detected, but
a false automatic-shutdown attribute retains a perfect selected-field score. The source inventory contradicts
that planted claim; format checks and selected metrics cannot replace source/engineering review.

The question engine produces zero findings on this sparse model. The case retains a useful manual source
question about operator notification versus automatic unloading shutdown and records the catalog gap as N065.
Current installed state, complete safeguards, accountable owners, company handoff acceptance and benefit remain
unresolved. The new matrix cell measures platform export plumbing only; it supplies no interpretation score.

## 103. Let a new corpus case expose an exporter assumption

The MGPI alias LI_HYPO passed the description contract but its first full build failed in generate.bubble:
splitting a tag into exactly two hyphen-separated parts raised ValueError. The renderer/exporter now preserves
separator-free aliases intact and splits only the first hyphen for conventional two-line labels. Valve labels
retain the complete supplied identity. Standard one-hyphen rendering is unchanged.

An actual CLI regression exercises an underscore alias and a multi-hyphen final-element tag across SVG,
Ignition and PI staging, with unchanged input bytes. The 16 exporter tests pass. The first regression fixture
omitted required source_document metadata and was corrected; that test-construction failure is not attributed
to the exporter repair. The original failing MGPI build is retained privately. Seven existing export commands
were executed through the existing orchestrator on exactly three selected stages; no unrelated recorded,
runtime, 3D or tour stage is asserted to have been rebuilt. Existing registered outputs remain unchanged except
the registry deliberately extended for the new case; dependent freshness returns after the actual exports.

Independent visual review then caught a divider crossing the new single-line alias in the native SVG. The
fallback now omits that divider, while conventional split labels retain their original rendering. The CLI
regression checks the alias has no crossing divider; the repaired native output is rendered again for review.

The code change also made 48 matrix cells stale through their recorded dependency closures. Each was actually
rerun with the existing row/input selectors; the other 47 complete cell records were retained. The final matrix
has 64 passes, 23 failures and eight not-applicable cells. Its additional pass is the MGPI export-plumbing cell,
not an interpretation result. The headline and claim checker's expected count move from 63 to 64 together;
existing drift controls still reject changed results. Historical red cells and evaluation criteria remain.

## 104. Audit the whole toolkit before adding more

The README had become a product introduction, tutorial, feature catalog, research paper, demo gallery and
history at once: 11,264 words. A generated catalog copied twenty wide rows into it on every regeneration.
The user asked for a deep rethink and a whole-toolkit state audit rather than another appended explanation.

Two independent coding agents inspected all twenty catalog features against source, CLI contracts, guides and
tests, with representative offline chains on public/fictional data. Most components are implemented local
prototypes. The integrated company journey is partial/manual: interpretation and drafting, incompatible formats,
source/signal review, native acceptance and receiving-system adapters remain separate. Shared company authority
and execution are external responsibilities by design. Reviewed example files do not imply product readiness.

Disposable-copy probes found concrete source-preservation defects: graph export can replace its source model,
impact estimation can replace a spec named impact.json in its output folder, and CSV-band generation can replace
an input occupying csv_normal_bands.json. Seven multi-appearance OPEN100 items also lose later provenance locators
in graph export. These remain open, with retained private before/after proof and prioritized N066/N067 records.
The vendor report's labor and overlapping-range claims are interpretation defects (N068); its guide is qualified,
but neither report generator nor metric was silently changed. The current-state report distinguishes these bugs
from missing validation, manual inputs, demonstration-specific outputs and planned integration.

The README now introduces one question and routes the reader in about 700 words. docs/README.md owns navigation;
WORKFLOWS.md owns actual format contracts; STATUS.md owns delivery gaps; RESULTS.md owns numerical research
evidence. The feature catalog is a narrower reference, with file/test details folded and 'Example review' labels.
Its generator owns only that reference. Plant/pilot/lifecycle pages no longer duplicate the catalog or main route
tables. MCP status errors and a stale observations-option description are corrected. Historical experiment records
and the benchmark-pinned description guide remain intact. Contribution guidance defines these page responsibilities.

All forty-two original claim definitions, precision/criteria and derivation expressions remain unchanged. Each
now names its publication, and receipts state that source. A claim cannot be satisfied by a matching phrase in
an unrelated page. The fourteen claim tests and five catalog tests pass; the latter includes a real regeneration
that must leave README bytes unchanged. During migration, missing phrases were caught before their destination
was completed. Independent comparison confirms the same forty-one file-backed matches and one prose-only claim.

The deliverables generator now labels its table as TE/OPEN100 demonstration evidence. The existing structural
check was actually rerun through the orchestrator; its first new navigation assertion mishandled capitalization,
was corrected and passed. No research model, scoring threshold, prediction, answer key or benchmark result was
changed. The audit re-scores thirty saved tables (seven historical-format adjustments) and retains five missing-
prediction gaps. It checks matrix freshness rather than claiming a new whole-matrix run.

Independent arrival retesting caught and corrected a new map error: direct DEXPI XML yields a process model,
while the converted-key adapter yields an extracted twin. The canonical table now also states context-register
support for extracted twins and the shipped snapshot-only MCP input. A Copilot-only reader can start with a plain
brief; local software is an optional route. This remains coding-agent review, not measured human usability,
engineering acceptance or operational benefit. Next work should protect evidence before expanding the package.

## 105. Refuse source-output collisions before publication

The whole-toolkit audit found three commands that could successfully replace their own inputs. Independent
disposable-copy probes expanded that finding to graph question/review records, impact constants/catalogs and
both CSV inputs, including differently spelled paths and existing file/directory aliases. These were software
preservation failures, separate from any model accuracy or engineering judgment.

A shared standard-library preflight now checks every active input and the complete output set before the CLI
creates directories or writes a result. Resolved paths catch spelling and directory-link aliases; existing
device/inode identities catch hardlinks. Aliased sibling reports and unusable destination kinds refuse too.
Graph export protects the model, supplied questions and consumed direct review JSON files. Impact estimation
protects the spec and constants, while needs mode protects its catalog. CSV bands protect both supplied CSVs.
Unused options remain unused, and graph check mode remains read-only.

Regression tests assert unchanged source and companion bytes, including a collision with the second report
that previously happened after the first write. Independent actual-CLI probes cover Windows exact, relative,
case, hardlink and directory-junction aliases. File symlinks are unavailable on the local Windows account;
their regression controls run where supported. A reviewer also caught a platform-specific error-message
expectation in the invalid-parent test; it now accepts POSIX ENOTDIR refusal as well as the explicit kind check.
Ordinary full/core graphs, site/default estimates, needs reports and normal/scored CSV methods retain the
original generated bytes in independent old/new comparisons. No formula, threshold, prediction or key changed.

The new import closure made ten historian matrix cells stale. All ten were actually rerun through the existing
row-6 command; the other eighty-five complete cell records remain unchanged. Runtime fields and tool
fingerprints change, and the rendered matrix updates its dates/duration. Independent review caught a TE guide
locator recorded before a four-line documentation insertion; that single cell was actually rerun to update
the locator. Every substantive result, reason and
criterion is retained: 64 passes, 23 failures and eight not-applicable cells overall. This refresh does not show
improved detection or new generalization. The saved task/model benchmark reports remain unchanged.

This is a preflight on stable local paths, not a concurrent-writer lock or a multi-file transaction. A later
I/O failure can still leave a partial report pair. The separate graph loss of additional provenance appearances
(N067) and vendor-report interpretation defects (N068) remain open. Source preservation takes priority over
adding more corpus cases, outputs or integration claims.

## 106. Preserve item appearances through graph and context handoff

The state audit found seven actual OPEN100 items whose later drawing appearances vanished in graph export.
Independent baseline probes also showed that changing a later locator left the exported graph and downstream
context binding unchanged. A zero-attribute item could lose even its primary source. These were evidence losses,
not extraction-accuracy findings.

Full and core exports now keep a separate identity source, the complete ordered item provenance list and the
original source/sources citation fields. Empty records, duplicates and unknown JSON metadata survive unchanged;
malformed later records or invalid supplied geometry refuse before publication. Claim-specific document and
review sources retain their original precedence. Removing only the added evidence fields reproduces the old
example graphs exactly: no engineering values, node/edge identities, claims or review states were corrected.

Statement packets expose every recorded appearance, available crops and explicit missing-image/locator notes.
Complete records remain bound in JSON; the CSV pointer is a readable locator summary. Item appearances do not
establish support for every claim, and one statement still receives one verdict. An independent adversarial
probe found that a missing sheet could select an unrelated image literally keyed None; the crop path now
requires a usable sheet locator. Changes to later appearances invalidate statement and context bindings.
Context preserves evidence metadata opaquely, including nested keys that resemble bookkeeping names.

A second independent CLI probe found that two relations with equal endpoints could share one statement while
only the first edge's evidence was displayed. Relations with different sources or item evidence now receive
separate statement identities and verdict targets; identical evidence can still coalesce. The same guard also
preserves distinct document/review sources when equal attribute wording would otherwise merge their targets.
Regressions check both cases. This does not change the graph's relationships or claim values.
Review also caught a corrected value combined with a separately sourced unit: the sentence showed only the
value's source. Setpoints and limits now combine only equal-source constituents; otherwise each description,
value and unit keeps its own visible source and verdict target.

The offline regression packet selects one existing OPEN100 item with three appearances across sheets 2–4.
It needs no original images or new model calls. All seven affected items were checked separately. The current
snapshot result retains additive evidence without changing its startup-only, read-only contract. Direct XML,
review/mapping and description examples were regenerated through actual CLIs; unrelated outputs remain intact.

Refreshing bindings does not refresh a person's decision. Five context families retain their old registers and
answer sheets, then add explicitly labelled proposals or fictional exercises against current evidence. The old
decision prefixes remain unchanged, and old sheets refuse before writing outputs. The bound statement exercise
likewise retains its complete earlier packet and uses a newly labelled fictional verdict. Historical measured
samples, scores, predictions, benchmark recipes and source/key records remain unchanged.

A fresh reader review caught extraction-priority scores presented as plant-risk statements. The review view
now skips and counts only risk.risk_score, risk.tier, risk.why and risk.tier_before_floor on extracted twins;
the raw graph retains them. The last field records the extraction safety floor, not a plant operating condition.
Authored process-model risk and unknown risk fields remain visible. On the full OPEN100 view this removes exactly
3,037 bookkeeping statements (10,663 → 7,626). All remaining statement identities, wording, ranks and ordering
are unchanged. This is a presentation correction, not an accuracy improvement. Summary image-availability counts
now distinguish drawing references from supplied images and count statement evidence entries, not unique photos.

The repair does not evaluate source agreement, interpretation quality, human review time, company adoption or
plant truth. Vendor-report interpretation (N068), semantic question evaluation and the bounded engineer journey
remain next work. No company system, live process connection or public-post publication is involved.

## 107. Correct vendor-report interpretation without changing its scores

The audit's N068 finding was reproducible in the generated report, not just an old guide: an empty-answer
correction count was described as equivalent manual work, and overlapping run ranges as a tie. Independent
review followed the actual count, matching, interval and bootstrap functions. It also found claims of drawing
readiness from strict IoU, prospective new-sheet performance from empirical resampling, and an unsupported
explanation for a weak sheet. Holdout A was called untouched even though it also informed method selection.

The renderer and guide now state the narrower interpretation. Review load counts keyed differences, not time
or labor savings. Runs 95% is an approximate Student-t interval for a mean under independent/comparable-run
assumptions, not one future run's range. Bootstrap draws only observed sheets and independently selects an
observed run for each sampled sheet; it does not retain whole-run correlations or establish unfamiliar-input
performance. Overlap is not a tie or equivalence test. Strict IoU is a matching threshold, and connection credit
concerns undirected keyed asset-network pairs, not direct adjacency, routing or process truth. Controls probe
declared failures; passing does not establish correct keys or every kind of error. The historical holdout-A label
remains with its method-selection qualification.

Three new cache-free regression controls use the saved report and existing statistics. One explicit synthetic
counterexample has overlapping individual mean intervals while the existing Welch difference interval excludes
zero. These controls do not add a comparison test to the vendor tool or establish which vendor is better.
Scoring/control functions, matching thresholds, normalization, interval calculations, bootstrap draws/seed and
all source keys and predictions remain unchanged.

The original vendor Markdown is retained unchanged under history. Current Markdown is an actual render of the
unchanged historical JSON, with every numeric table row identical. This is not a new scoring or model trial.
Independent CLI re-scoring of thirty saved bare predictions reproduces all values and report fields except the
thirty prediction-file hashes: the saved JSON names original run wrappers, whose parsed predictions are the
committed files. Neither hash set is substituted for the other, and missing original wrappers are not hidden.

The benchmark includes the whole evaluator module in its implementation fingerprint. An actual offline run
therefore creates a new drawing report pair and new cohort/group identities. Its ten run/cohort rows, two
model/method groups and every substantive control/count/metric/input/recipe/model/resource record are retained.
The registry explicitly selects that new pair. All six original benchmark files remain byte-identical, including
the now-historical drawing pair; the four description-report files remain current. No recipe or saved report is
hand-rehashed to conceal implementation drift.

The fifteen affected matrix row-2 cells are actually rerun after the final renderer edit. Their substantive
results and criteria remain unchanged; the other eighty complete cells are retained. An earlier row-2 run and
new benchmark candidate preceded the last wording edit and are retained privately as superseded evidence;
they are not counted as final freshness. The global 64 pass / 23 fail / 8 not-applicable result is unchanged.

These repairs improve how evidence is read, not model accuracy or operational outcomes. The next work remains
one bounded engineer investigation, source-grounded useful/unacceptable question rubrics, and an approved
company handoff. No paid models, new source download, company write, plant import or public post was involved.

## 108. Audit delivery state and remaining source-output writers

A fresh state audit separates the last released evaluator from unfinished local source-support work. The latter
has a packet validator, label scorer, development keys and controls, but no registered suite, run manifests,
published report or completed reader route. It is not an implemented semantic-verification service or a new
model-performance result. The three existing benchmark suites reproduce with the exact released evaluator and
its five dependencies copied from Git; the modified evaluator correctly makes the existing snapshots stale.
Historical reports are retained rather than hand-rebound to the changed code.

The audit inspected the twenty-feature inventory and the contracts of thirty-one tools, checked the existing
registries, and ran representative actual CLIs. One public drawing builds an intake bundle, report and question
screen. The authored illustrative description builds a drawing/graph/staging packet. A planted MGPI false
shutdown again passes structure and five exact-quotation checks, matches all twenty-seven selected facts, and
produces zero question findings. These are software and scoring observations, not human usefulness or plant
validation. The source-support work cannot close the separate useful-question gap merely by grading labels.

Three additional source-output collisions were reproduced on separate disposable copies. The report command
can replace its input plant_model.json with HTML through --out. The loop-audit command can replace its drawing
key with the JSON result when the output prefix resolves to that key. Line enrichment can replace a supplied
drawing image with model JSON. Each command returned success; before/after hashes changed. Original inputs were
unchanged. N069 records these as open defects. N066 remains the completed repair for its three named tools;
its scope is not extended to these newly tested writers. Intentional model-in-place enrichment remains a
different contract that the eventual repair must preserve.

The status page now puts those defects before feature expansion. The current first-use path is a bounded
investigation packet; description interpretation/layout, source judgments and company acceptance still need
people. A portable graph is a one-way snapshot, MCP is local read-only retrieval, and company authority,
operational connectors and maintained-document round trips remain external or unimplemented. The audit adds
no model call, source download, installed-state judgment, company integration or operational-benefit claim.

## 109. Preserve sources across the remaining output writers

N069 began with report, loop-audit and line-enrichment collisions. An independent sweep of the thirty-one
tool contracts reproduced failures in eleven additional writers, including late batch destinations and files
retired by export. Fourteen writers now check active inputs and publication/retirement targets before writes.
The same helper checks resolved paths, hardlink identity and sibling aliases. Intentional reviewed model changes
and model-in-place enrichment remain allowed. Review-kit generation also refuses to replace an existing kit's
review/timer files; an extraction skip outside the repository now prints a bounded path instead of crashing.

Independent actual CLI retests cover the twelve additional failure scenarios, nine advanced alias/batch cases,
and sixty-four initial report/loop/line probes. Ordinary output comparisons retain prior payloads except the
declared generator fingerprint. Fresh-kit history refusal and external-record skipping preserve bytes. These
are stable-local-file preflights, not a concurrent-writer lock, transaction or guarantee for every research script.
No provider model call or plant-system import is involved.

Saved-prediction rescoring actually reproduces thirty tables (seven under explicit historical formatting), with
five missing-prediction gaps. Eleven offline generation commands across seven stages run again. Five recorded
stages accept historical evidence after reviewed publication/skip-wrapper changes and unchanged output hashes;
they are not new extraction trials. Three extraction stages bind zero output files, so their renewal verifies
no raw extraction records. Two replicate stages retain six bound outputs. At that point, of 497 archived pre-refresh files,
493 remain raw byte-identical; the other four are pipeline metadata and TE/Bayer drawing manifests whose only
changed content is generator_sha256. Native-runtime, Blender and browser records remain historical.

Both description bundles are actually prepared and rebuilt to scratch from their unchanged sources and answers.
Their only changed files are the drawing manifest and build inventory, reflecting the changed generator/export
code and manifest hash. Source interpretation, rendered geometry, questions and staging content do not improve.
The lineage guide now states exactly what accepted-record freshness verifies and what it cannot verify.

The full suite then exposed a pipeline integration boundary: unconditional existing-kit refusal also blocked
rebuilding the repository's untouched blank kit. Default make still refuses existing kits. The pipeline now
explicitly opts into refresh-unstarted, which first checks all packet hashes, blank decisions, empty timer,
unchanged draft protocol and absence of unexpected files (the retained README is allowed). Any started, edited or incomplete packet requires a new
folder. This preserves the intentional rebuild path without silently resetting review work.

All eighty-five cells in matrix rows 1–5, 7 and 8 are actually rerun after the final relevant code changes;
the ten row-6 cells retain their previous complete records. Totals remain 64 pass, 23 fail and 8 not applicable.
The criteria and substantive results are unchanged. This refresh tests the affected software paths and current
fingerprints; it adds no unfamiliar-source performance or engineering acceptance claim.

## 110. Separate fixed-claim judgments from useful questions

The MGPI false automatic-shutdown control passes quotations and all twenty-seven selected model facts, while
the question screen returns zero findings. A separate source-support adapter now grades fixed supplied claims
as supported, contradicted or insufficient-evidence. A separate coding agent froze twelve original-source
judgments before candidate/scorer work: six MGPI and six NIST, balanced four per label. The public projection
preserves evidence joins, timestamps and scope, removing private absolute-path metadata. It exposes project
paraphrases that explicitly scaffold distinctions; this is development label classification, not raw-document
comprehension, a blind trial or a model-performance result.

Synthetic controls score reference 12/12, empty 0/12 and each uniform label 4/12. Primary accuracy keeps missing
claims in its denominator; diagnostic F1 can differ on partial answers. IDs, admitted citations and nonempty
reasons are checked structurally. A false explanation can still earn perfect label accuracy; no reason-quality,
source-validity, question-usefulness or plant-truth scoring is claimed. All three previous suites are actually
re-scored into new prefixes with substantive results unchanged. All eight prior report files remain intact;
changed implementation/cohort identities are visible rather than hand-rebound.

The existing first-question route gets a worked MGPI draft: historical notification versus unloading shutdown,
qualified by report scope, with current installed evidence unknown and recipient/reviewer unassigned. It records
no trial, benefit or company acceptance. This makes the human handoff concrete without building a company
governance service. The question catalog is unchanged; N065 still needs useful/unacceptable question keys and
false-positive checks across other sources. A small label task does not close that gap.


## 111. Keep each subject's unanswered fields in the investigation

A source-first question review exposed a prerequisite software defect: H2 could combine header A's pressure
with header B's temperature and remove the supply-condition request. A complete supply could also hide an
entirely unknown sibling; a blank subject alongside a complete one could retain a request with an empty
remaining-fields list. The independent baseline review retained twenty-three actual CLI controls before the
repair. Existing tests passed despite these failures.

Field requests now default to each triggering record independently. Explicit unit scope reads only the finding's
selected owning equipment, with H4's supply temperature and cooler duty declared that way. Supporting context
cannot silently complete an anchor. No owner leaves every unit field unresolved. Every open field request
retains its scope, each subject/field state and locator, and the remaining obligations. Supplied values stay
attributed; a value on one subject can coexist with the same field missing on another. Empty/whitespace schedule
values now count as blanks, while zero, false and case-insensitive lookup remain supported.

Readable screens, graph attachment, context reports and per-site/finding roll-ups preserve those distinctions.
Roll-up controls reject missing/invented subject coverage and scope conflicts before changing reports. Legacy
screens remain readable without claiming that their omitted scope proves the current behavior; regenerate them
under the reviewed catalog. New fictional regression fixtures establish software behavior, not source truth,
useful questions or physical/temporal equivalence. No trigger, benefit or decision rule is added.

The actual prior screens and both description bundles are regenerated from unchanged models/sources/answers.
Earlier bytes are retained in Git and private comparison evidence; existing context proposals/decision history
are unchanged. The MCP sample is read again from the graph with the refreshed questions. The broader useful-
question rubric remains open: original-source review does not justify a universal alarm checklist. E5 can
settle a fan-curve request from HP/RPM alone, and H3's hours/power fields need separate review (N071). Schedule
replacement and unresolved fact/schedule conflicts remain documented limits. This repair closes N070 only.

Final independent retests retain eighty-six actual CLI calls and thirty-nine assertions; fourteen public
screen/roll-up reports reproduce. The question suite passes 76 tests with one Windows symlink skip; the context
suite passes 45. The full cached-data runner reports 63/63 scripts, five unittest skips and two explanatory
platform notices. Four registered benchmark suites reproduce; the unchanged matrix/pipeline inventories remain
fresh. A separate reader independently rebuilds all sixty-three description files and checks the application
snapshot fingerprint. These are bounded software observations, not an engineer trial or native plant acceptance.


## 112. Keep candidate facts separate from collection and review

Actual baseline CLIs show E5 dropping its curve/input request from HP/RPM alone and H3 dropping its hours
request from kW/HP alone. An independent reviewer freezes a primary-source-informed collection rubric before
seeing catalog/software candidates. The revised requests distinguish nameplate/design information, matched
fan/system evidence, actual operation over a stated period, and heat-source compatibility. E5 now requires
further study and reviewed constraints before a drive quote; its similarity relation is not a site estimate.
H3 keeps the 150 C threshold as an explicitly unvalidated catalog heuristic and treats absent temperature as
unknown. Both question triggers and their benefit wording stay unchanged.

Evidence-only `show_fields` retains candidate facts with their subject, original value and source locator,
without counting them toward required fields or settling document suitability. The fictional example retains
the fan's HP/RPM, heater's kW/HP and stated 60 C load, while seven distinct collection/review tasks stay open.
Actual-power-only, bare hours, curve references/flags, wrong-asset/unreadable references and richer raw facts
likewise do not replace missing review/basis/coverage. Original units can be retained without demanding both
HP and kW or equating shaft output to measured electrical input. No automatic artifact approval or conversion
is added. Existing required-field behavior remains separate; additional review uses `also_needs`.

Independent consumer probes expose opaque value loss: recursive context bookkeeping removal strips
`status: estimated`, `status: unreadable`, period/asset context and vendor metadata from supplied fact values.
Opaque claim values and candidate/field evidence now survive unchanged and their qualifiers affect the
context evidence binding. Other probes expose erasure of always-open tasks during roll-up and an unexplained
unit-scope request with no owner. The corrected roll-up rejects omitted unconditional collection tasks before
writes; no-owner evidence-only requests retain the reason. Malformed metadata refuses, while generic context
continues to preserve caller-supplied unverified information without reapplying the question catalog.

The new example's actual screen, graph and context commands run offline. Both questions remain unanswered,
need owners and have no decisions or source-operating records. An independent reader follows that route and
finds all seven requests and five supplied candidate values/locators retained. This is an AI reader/software
observation, not an engineer adoption or usefulness trial. The normal published screens remain byte-identical;
both description bundles are actually rebuilt from unchanged sources/answers, with only their build inventories
changing. Research metrics, existing context decisions and benchmark reports remain unchanged.

Final local checks pass all sixty-three cached-data test scripts, with five unittest skips and two explanatory
platform notices. The question suite has 84 tests with one Windows symlink skip; the context suite has 48.
Four registered benchmark suites reproduce; the unchanged matrix and 52 configured pipeline stages check fresh.
Independent software evidence comprises ninety-seven actual CLI calls and 195 substantive controls. Source/UI,
reader-route and artifact-lineage scopes are recorded separately; none establishes human usefulness or
engineering/plant acceptance.


## 113. Refresh the whole-toolkit audit with failing handoffs

Steve asks for the whole state of the union, including half-built work. The audit freezes code baseline
3d93c5f (2026-10-30 20:19 Central), rather than relying on the earlier handoff or a count of green feature labels.
Three fresh coding-agent reviewers inspect the entry journey, implementation contracts and evaluation; the
maintainer separately runs current offline checks. Public input/output records remain unchanged.

Actual fictional-model CLIs expose unlogged alarm metadata loss during unrelated review and native tag renaming
that leaves a controller's measurement reference dangling. Generic pump ratings satisfy E2's BEP-labelled
request; E1 loses pump-curve/efficiency obligations and E4 loses its efficiency request with HP alone. All these
review/screen commands report successful execution; existing tests do not establish these collection semantics.
The E5/H3 repair did not certify the remaining catalog. The new failures stay open as N072/N073.

A private-copy key edit still passes matrix freshness: ordinary consumed sources/keys are not bound, despite
current recorded code dependencies (N074). An accepted illustrative context answer remains current after graph
asset/claim rejection because record-level status is ignored; the right semantic rejection policy needs explicit
design rather than treating every review event as new evidence (N075). Context answer values/verdicts remain in
the sidecar, outside the snapshot server; virtual stream identities also lack node-only asset/filter access
(N076). This is a partial local readback bridge, not permission to build a company governance service.

The current registries and four saved benchmark suites reproduce; saved predictions reproduce thirty tables
with five missing-prediction gaps retained. Matrix totals stay 64 pass/23 fail/8 n/a; no new matrix/model run or
generalization gain is claimed. The public status now leads with open defects and actual maturity; earlier
repairs move behind a disclosure instead of dominating the current-state page. The documentation review finds
no missing local paths among 285 checked across 22 guides, without checking anchors. The main remaining product
evidence is still one engineer/recipient investigation, useful source-backed question evaluation and a scoped
company handoff. No human, plant, Copilot tenant or company acceptance is inferred from this audit.

The fresh full cached-data runner passes all 63 scripts with five unittest skips, two explanatory platform
notices and no additional skipped-check notices. The notices do not increase the skipped-case count. The
new audit probes still fail; script-exit success does not establish the contracts they expose. MCP runtime
was not rerun in this audit, and its prior transport evidence remains separate.


## 114. Preserve evidence and references through model review

The whole-toolkit audit's N072 cases become the next correction, before further corpus or feature breadth.
An independent reviewer freezes a consumer contract before seeing the candidate. Native instrument/final-element
tags are live identities, including records with auxiliary IDs; extracted twins instead keep stable asset IDs.
Corrections now migrate supported controller/interlock/limit/unplaced-control and line-layer references together,
with exact paths and old/new values in history and records. Source quotations, provenance, former tags, physical
point mappings and unrelated metadata stay intact. Sheet targets are frozen before application; collisions,
chains/swaps and contradictory edits refuse, while historical aliases permit unchanged replay only.

TE alarm knowledge no longer mutates then strips supplied fields. The declared simulator's matching XMEAS(7)/
XMEAS(9) reference is read as a literal without importing gateway configuration. Supplied setpoint metadata takes
precedence; missing/empty/null/unrecognized values remain unresolved. Requested priority with unresolved basis
goes to change review without inferring installed absence. No alarm or setpoint is executed or changed.

Fresh adversarial probes find related failures in the first candidate: Boolean alarm classification, contradictory
row notes/decisions, dated receipt overwrite even on unchanged replay, repeated contradictory assignments in one
cell and duplicate identity headers. Their first failures remain preserved. Corrections retain standalone receipt
pairs, select fingerprinted names for different same-date results and reuse identical replay. CSV/JSON ambiguity
refuses before source mutation. These are local single-invocation protections, not atomic publication or locking.

Final independent behavior review retains 71 actual CLI invocations against one frozen implementation: positive
native graph/C2/generation, two-step rename and historical replay, metadata/receipt preservation, ambiguity and
output-alias controls, plus extracted stable-ID/scoped correction. The original TE detailed layout actually
refuses a retagged model; explicitly changing its two signal endpoints makes --check pass while every other
layout value and derived loop flag stays unchanged. That is a manual companion correction, not an automatic
layout migration or an engineering layout acceptance.

The new fictional native example shares its initial model with twenty actual-CLI regressions, retains thirteen
live reference migrations and three expected output artifacts. Its original source words and unreadable metadata
remain visible. Separate drawing/display layouts, external loop/mapping records, prior snapshots and context need
explicit reconciliation/regeneration/refresh. No new corpus source family, model performance, human usefulness,
native platform, Copilot tenant or company-governance acceptance follows from these controls. N073 remains the
next collection-semantic defect; N074-N076 and the larger engineer/company trials remain open.

The first full run reports 63/64: an older extracted-example test recursively counts the new native subfolder
as outputs its extracted recipe should reproduce. The two recipes now have explicit test ownership; the native
test also pins its complete six-file inventory and all three expected artifacts, so the partition does not
silently omit those files. The original failure remains recorded before the targeted and full retests.

Final local cached-data rerun passes all 64 registered scripts, with five unittest skips, two explanatory
platform notices and no additional skipped-check notices. Four saved benchmark suites and thirty saved-
prediction tables reproduce; five prediction gaps remain. Recorded matrix code bindings and all 52
configured pipeline stages check fresh; no matrix or provider run is added.


## 115. Repair the audit gaps with owned workstreams and independent handoffs

Steve asked for every gap to have an agent and work in motion. Three implementation workstreams own questions,
evaluation and context/retrieval; the integration workstream owns description review, company acceptance,
documentation and release. Each implementation received a separate coding-agent cross-review. All unfinished,
non-rejected historical ideas also have workstream owners; rejected methods were not reactivated. Real engineer,
recipient, company/native-system and Copilot observations remain separate external requirements.

**A249 — N073/N079.** E1/E2/E4 and H4 no longer let scalar ratings erase larger curve, efficiency, BEP or duty
collection tasks. Candidate facts remain available with their qualifiers. All fifty default triggers and benefit
objects remain unchanged. The source-scoped MGPI recipe retains known historical answers and endpoint/function
distinctions; its two authored questions are not a generic new alarm classifier or evidence of usefulness.
Default MGPI still yields zero findings. Field intake merges disjoint additions and refuses ambiguous case keys,
conflicting values, duplicate JSON keys and previously ignored native-model schedules.

Fresh service-order probes find another real failure: opposite contradictory service order changes eligibility.
N079 now refuses that ambiguity, or requires an exact source-bound candidate selection with supplied basis and
draft/reviewed provenance. The three existing OPEN100 spelling choices are explicit drafts; original service
transcriptions remain intact. No declaration grants organizational approval. Independent review retains 62
question/graph CLIs across the N073/N079 controls and complete public reproductions, with prior harness errors
separate. Its new context bridge initially strips structured declaration status: the minimal opaque-evidence
repair preserves the full value and binding. A separate reviewer checks that repair with nine CLIs/35 checks.

**A250 — N075/N076.** Explicit record/claim rejection participates in context dependencies; ordinary/unrelated
bookkeeping does not. A changed bound snapshot reopens its answers, while exact restoration can restore prior
currentness. Historical decisions, source verdicts and ownership remain intact. The server reads a deliberately
selected, hash-bound context sidecar at startup, never a pointer supplied by graph content. Three additional
read-only tools expose retained context IDs, current/source/ownership data and paged full decisions, including
removed questions. Exact virtual stream identities work through asset, relation and question operations.
Independent controls retain 17 CLIs/92 checks, actual SDK/stdio/loopback tests and the separate N079 bridge
follow-up. This supplies no shared authorization, source fetching, live data or company deployment.

**A251 — N074.** Actual matrix runs now bind declared source/key bytes, directory inventories, registry entry,
runner and imported tools. Text hashes normalize CRLF; binary hashes preserve raw bytes. Missing committed or
partially missing inputs refuse; entirely absent optional caches are explicitly UNVERIFIED unless strict
--require-inputs is requested. Bindings captured before/after each run refuse mutation, rather than backfilling
hashes onto historical results. Root independently runs a water-export cell plus six CLI freshness controls and
an uppercase-XML inventory/change/removal oracle.

Follow-up review catches platform-dependent glob matching: Linux would omit seventeen uppercase .XML consumers.
The initial 474-second matrix run is stopped and retained before any matrix publication. Its wrapper's 95-cell
counts describe the previously committed matrix, not completed fresh cells; the private record explicitly says
so. The corrected case-independent inventory retains original path identities and matches all 185 selected XMLs.
The final actual 95-cell run and strict checks reproduce 64 pass / 23 fail / 8 n/a with all substantive cell results
unchanged. Existing failures are assigned bounded source-informed experiments; a rerun is not new generalization.

**A252 — N078.** Description builds now publish interpretation_review.csv and source_coverage.csv. Every supplied
record leaf, nested control/limit value, unknown/assumption and selected source line is exposed; all verdicts
start unreviewed. Nested citations retain their source spans. The false-shutdown control still passes structure
and the limited fact scorer, but its contrary action claim appears beside the same quote. No semantic acceptance
is inferred. A separate reader checks a 73-leaf oracle and actually reproduces all 67 bundle files; all 54 registered
bindings are checked with fresh versus inherited scope explicit. Later catalog-only N080 changes yield no bundle
delta. ACCEPTANCE.md prepares recipient reconstruction, receiving-system/native readback, client permissions and
the next revision; these real exercises remain not run. The main pump walkthrough is corrected from five to
seven requests and links the new review sheets.

**A253 — N081.** The current benchmark check first refuses a legitimately changed guide recipe, then exposes the
changed description-workflow code recipe. Exact historical guide/code bytes from bdf1b41 are retained as .txt
snapshots; original suites, eight manifests and all old reports remain unchanged. Two current suites/eight
metadata manifests point at those identical recipe bytes. Actual re-scoring writes four new report files;
source/key/prediction/model/date/cohort/numerical results remain unchanged. Only declared provenance, submission
and group identities/order change. Independent review covers87 registered files (17fresh/70inherited), exact
archives, report reproductions and tamper refusals. This is not a new model execution or performance improvement.

**A254 — N080.** The remaining field-discharge inventory exposes H1 volume capacity erasing rated steam-flow
collection, E11 design-fluid temperature erasing a surface task and H2 design/Boolean fields erasing supply
conditions. An independent DOE source contract precedes the candidate. Three new always-open review tasks keep
the distinct source/basis obligations while retaining exact candidates. The 105-test question suite passes with
one Windows skip; an independent review uses 36 CLIs, including 27 custom screen/graph/context/rollup/omission controls
and nine complete public reproductions. All 50 triggers/benefits remain exact. Nine named rules now have bounded
collection repairs; the 50-rule/119-request inventory leaves 41 rules' source adequacy and N065 usefulness open.

N080 also changes the graph behind the MCP sample, so its old fingerprint correctly refuses. Actual refresh and
independent protocol verification keep that source dependency explicit. Earlier failures, stale checks and
reviewer harness corrections are retained rather than relabelled as initial passes. Model calls, new original
downloads, company/plant writes and LinkedIn publication were not exercised.

Final local validation: all 64 registered test scripts pass, with five Windows unittest skips, two explanatory
platform notices and no additional skipped-check notices. The notices explain platform skips and are not extra
skipped cases. The 95-cell actual matrix and strict input check pass their reproduction/freshness contracts;
64 pass / 23 fail / 8 n/a remain unchanged as research results. All 52 configured pipeline stages are fresh,
41 numerical README claims match (one additional claim is prose-only), four current benchmark suites reproduce,
and saved predictions reproduce 30 tables (23 MATCH / seven MATCH-OLD), retaining five historical GAPs. Six
independent review records bind the repaired examples. This is local software evidence; actual engineer,
receiving-company, native-system and Copilot tenant acceptance remain unrun.


## 116. Correct collection boundaries after clean CI refuses the first repair candidate

**A255 / N074 follow-up.** Candidate 143fcf8 passes all 64 local test scripts, but the actual clean Linux
[CI run 41163003002](https://github.com/steve-vitale/pid-to-digital-twin/actions/runs/41163003002) passes 63/64:
three Synthetic cells and the TE historian cell report changed input inventories. The snapshot MCP job passes.
Main is not promoted from that failed candidate. The failure exposes two dependency-declaration defects, not
changed workflow scores or a reason to relax their criteria.

The optional Dataset PID collection shares an ancestor with committed OPEN100 sheets; that ancestor cannot
establish the selected collection's presence. Keyed-sheet declarations now identify their own collection boundary.
A wholly absent selected optional collection reports UNVERIFIED, with strict --require-inputs still refusing.
Partial and empty present collections remain stale. TE row 6 reads exactly d00_te.dat through d21_te.dat;
its declaration now binds those 22 runs and retains its five explicit committed reference/publication inputs.
Unconsumed clone README/license files, training runs and Fortran are no longer incidental dependencies of row6.

Fourteen targeted lineage tests pass. Root freezes a separate primary-code contract and executes 53 actual
copied-root freshness CLIs: each of the 22 TE runs is independently changed and deleted, unrelated metadata varies,
selected collection absence with a committed sibling is explicit, partial/empty presence refuses and exact
restoration passes. The first private reviewer fixture omitted a required render timestamp before any CLI;
it is retained and corrected separately, rather than labelled a product failure.

Changing the runner invalidates the earlier matrix bindings. All 95 cells are actually rerun with the final
frozen runner; strict inputs verify and every substantive result remains unchanged: 64 pass / 23 fail / 8 n/a.
No historical bindings are copied onto those results. The initial failed CI and preceding matrix run remain
available. This is software/dependency evidence, not a new model trial or engineering acceptance result.

Final follow-up validation: all 64 local test scripts pass, with five unittest skips, two explanatory platform
notices and no additional skipped-check notices; the 13 frozen code/catalog inputs stay unchanged during the run.
An independent exact tracked-tree fixture adds only the corrected runner/tests, fresh matrix/page and 46 locally
copied checksum-pinned TE setup files. Six actual check CLIs and 20 assertions pass: default mode explicitly
reports 50 cells UNVERIFIED, strict mode refuses absent originals, changed/deleted consumed TE files refuse and
exact restoration passes. All 2,715 other tracked files remain identical to the archive. This Windows inventory
exercise complements the subsequent Linux CI gate; it does not claim that CI has passed or absent data was read.
New C12/E28/H5 quantity/equipment-scope and bound-question re-export defects remain explicit in STATUS.md, with
separately prepared candidates and assigned owners. They are not counted as repairs in this release.


## 117. Keep collection scope and reviewed context bound at handoff

**A256 / N083.** Actual receiving controls expose a graph-export seam: feeding bound enriched questions back
through full/core export drops the complete register binding while retaining answered/current summaries. Changing
the referenced asset does not revalidate that inherited state. The supported complete enriched graph/context pair
continues to validate. The conservative repair refuses marked enriched questions before writing and directs the
reader to that complete pair or explicit refresh with the preserved register. Blindly copying an old binding is
not a repair. An independent reviewer runs 19 actual CLIs, 64 assertions and 3 stdio SDK sessions; the final graph
suite runs 40 cases, 39 pass with one Windows file-symlink skip. Ordinary-question and no-question outputs remain
equal under matched controls. This does not authenticate callers who remove a marker or provide arbitrary state.

**A257 / N084.** Primary-source review and frozen expected/unacceptable controls precede the accepted collection
repair. C12 originally treats current, voltage or bare cumulative energy as enough to quiet power collection.
The first private candidate still quiets apparent kVA/reactive kvar; independent review rejects it, and that
candidate and its failing evidence remain. Accepted v2 retains every supplied electrical signal as a candidate
and always asks for representative real-input quantity, asset, time/conversion basis and suitability. Even a
real-kW label does not establish usable observations. No conversion or data-validity judgment is automated.

E28/H5 originally allow unrelated reset/recovery words to quiet the original train. Their new tasks retain
indications while asking for actual suction membership, every coincident load/approach and recovery coverage.
The governing-temperature constraint is explicitly engineering inference, not a generic warmest-load quotation
or implemented setpoint calculator. Existing conditional benefits remain unchanged. DOE motor-input guidance
and EPA ENERGY STAR dairy guidance inform the bounded contracts; this is not certification of all engineering
or economic closeout wording. Other 47 complete rules and all 50 benefit objects remain exact. The 3 applicability
contracts intentionally change; claiming all 50 triggers unchanged would be false.

Accepted v2 has 16 fresh independent CLIs/61 assertions plus 18 inherited E28/H5 CLIs/36 assertions whose complete
rule objects remain exact. Integration independently reproduces 18 commands/162 assertions and the 108-case question
suite, 107 pass and one Windows skip. Cross-consumer controls retain raw qualifiers and history, stale old answers
when the question contract changes, and refuse omitted always-open tasks. This is source-informed development
evidence, not unfamiliar-source performance or measured usefulness. The catalog now has 50 rules/122 requests;
12 rules have bounded collection reviews, leaving 38 source contracts and N065 usefulness open. N062/N063 actual
engineer, recipient, native-system and Copilot tenant exercises remain unrun.

Only 19 frozen code, guide and artifact paths are initially integrated; all 2,700 other tracked files stay exact.
All 67 description bundle files are actually rebuilt: 65 payloads stay equal and only two build inventories change
for the graph-code fingerprint. Independent output reviews distinguish fresh reproduction from unchanged
authored/history artifacts: opportunity 23/5, description 40/14, context 7/26 and snapshot 0/1 with fresh full SDK
readback. Historical decisions, source packets and the sample's unchanged fingerprint are preserved; a changed
timestamp is not claimed as fresh engineering evidence. Additional independent graph-support reviews cover
ordinary exports and declared refusal boundaries without relabelling every inherited artifact as freshly built.

The 19 integrated paths are disjoint from 853 declared consumed paths across the 95 matrix cells. An actual strict
input check passes, with the existing 64 pass / 23 fail / 8 n/a results unchanged; no matrix binding is backfilled
and no unnecessary whole matrix run is claimed. Model/provider calls, new original-source downloads, plant or
company writes, native imports, network-boundary changes and LinkedIn publication are not exercised.


**Open N085 follow-up.** A record-association contract informed by [HSE functional-safety guidance](https://www.hse.gov.uk/eci/functional.htm)
and [JRC function-identification guidance](https://minerva.jrc.ec.europa.eu/en/shorturl/technical_working_group_2_seveso_inspections/questions_and_tips_for_seveso_inspections_safety_instrumented_functions)
precedes ten actual unchanged-method CLIs on fictional machine records. A local pressure switch leaves the other machine's question open, but an
A-only trip, unrelated trip or ambiguous target can quiet C9 across the model. An explicit supplied shared mapping
is a narrow drawing-coverage control; it is not protection acceptance. The question and independent context
reviewers own the private candidate and negative controls. This reproduced collection gap remains open in this
release. Missing records do not establish absent installed safeguards, and a supplied trip does not establish
adequate or tested protection. No operating recommendation is made.


## 118. Keep machine-specific record review open and make the receiving packet current

**A258 / N085.** The independently frozen record-association contract precedes ten actual unchanged-method
baseline CLIs. A trip on A, a trip on unrelated C, a generic shutdown with unknown target and a contradictory
description/target can each erase C9 collection for other machines. Local switches and explicit shared records
provide controls; none establishes effective installed protection. The original failures and exact source/model
bytes remain. The contract draws on HSE/JRC guidance cited in section 117 and keeps record association separate
from safety design, validation, proof testing and operating authority.

The catalog-only repair retains nearby switch and supplied interlock records as candidates and keeps actual
machine/function/current-record review open for every named machine. It performs no target, owner, approval or
protection inference. C9's catalog still cites no primary safety-design source. Other 49 complete rules and all 50
benefit objects remain exact. The new inventory is 50 rules/123 requests; 13 bounded collection reviews leave 37
source contracts and N065 usefulness open. N062/N063 real engineer/company/native/Copilot acceptance stays unrun.

Isolated independent review executes 21 actual CLIs/96 assertions and three MCP stdio sessions/46 assertions.
Mixed equipment and local/shared/unrelated/unknown/contradictory/rejected records retain source-qualified targets,
cause/effect and draft/false/zero/null values. A prior accepted partial answer becomes stale under the new question
contract while its immutable source, verdict and caveats remain. An old answer sheet and omitted required task
refuse before writes. This is development evidence, not a new source-family or model performance result.

Final integration independently reproduces 19 commands/164 checks, runs 111 question cases (110 pass and one Windows
skip) and passes the pinned MCP2.3 checker. All 67 description files are actually rebuilt: the assisted graph,
questions JSON/readable screen and build inventory change; its other 27 files and the 36-file MGPI bundle stay
exact. Default MGPI still has zero findings. Source/answer/layout, interpretation rows and unreviewed verdicts
are not rewritten or accepted by this change. Existing finding counts alone would not verify these obligations.

All 33 context artifacts and historical decisions remain baseline bytes. The Bayer C9 question genuinely changes
the MCP graph fingerprint from 4cde42f4... to 0cabebf2.... The sample is actually refreshed and read back; its P-1
asset payload and limits remain unchanged. A load timestamp alone is not a semantic or engineering improvement.
Independent registered-output scope remains explicit: question 23 fresh/5 inherited, description 40/14, context 7/26,
and one fresh snapshot source/readback check. Older source/engineering evidence is inherited only at its prior scope.

The author initially invents a downstream test fixture without the required streams list; the tool correctly
refuses it. The original test source/failure and corrected empty-stream fixture are retained. Prior isolated
author/reviewer assumptions about typed target edges and named rollup inputs are also retained as harness
corrections, not product failures. All 150 isolated candidate/proof files and 217 integration before files remain
exact. Only 19 declared integration paths change; all 2,700 other tracked public files remain exact before metadata.
Those paths touch none of the 95 matrix cells' 853 declared consumed dependencies. No matrix binding is backfilled.

**Open N086.** A separate source-identity diagnosis of two previously exposed I01 vendor/reference pairs reads
the actual XML relationships before proposing a repair. It distinguishes an unassociated Comos instrument from
a fabricated location and an AutoCAD instrument-ended segment from a native process stream. Root independently
checks those source relationships. Current reports expose aggregate losses, but unattached identities/attributes
need exact disposition and source tracing. Independent source/key review and a prospective observability contract
are in motion. This neither approves all source keys nor changes historical row 7 criteria/failures. No new held-out
result, blanket XML fidelity pass or source-owner engineering acceptance is claimed.

Model/provider calls, new original-source downloads, plant/company writes, native imports, network-boundary
changes and LinkedIn publication are not exercised. The remaining work keeps its owners and original limits.


## 119. Apply the existing person-field exclusion before metadata reaches receiving tools

**A259 / N087.** Four actual unchanged-tool CLI probes put the same synthetic named-person field beside
eligible engineering metadata in ordinary MetaData and PlantStructureItem records. Ordinary metadata excludes
the value; plant-structure metadata carries it into the model, PLANT graph attributes and snapshot readback.
An initial root narrative says the graph omits it; its exact result rows and saved artifacts contradict that
sentence. The original report and a separate correction remain. A later actual original-reader fixture confirms
the direct PlantInformation XML-attribute route also copies the protected marker. No real personal data is used.

Independent prospective criteria freeze the existing case-insensitive eight-role PERSON_ATTRS policy before
the candidate. The repair applies it before plant-structure values enter metadata and before direct
PlantInformation attributes are copied. Ordinary GenericAttribute empty/missing precedence stays unchanged;
excluded values use the existing person-drop reason. Direct XML attributes are separate occurrences, so the
report adds person_metadata_attributes_excluded only when nonzero and names that separate count in readable
output. Excluded names/values and individual value hashes are not added to that report count. Eligible fields,
whitespace, zero/false-like strings and deliberately unmatched names keep their existing behavior.

The private candidate changes exactly two code/test files. All 2,717 other archive files stay exact. Author
validation executes 23 actual CLIs, including a separate C01 reproduction. Independent review executes 35
product CLIs with 101 assertions and nine actual pinned MCP 2.3 stdio sessions with 75 responses and 249
assertions. Three independent fixtures cover all eight role prefixes and case variants, full/core graph and
graph checks, qualified partial answers, complete selected context/source/decision/ownership history, no-echo
readback and duplicate-ID/alias refusals. The reader suite runs 35 cases with nine explicit optional-cache skips
in the clean archive; the three original/candidate I01 pairs separately reproduce all nine saved model/report
artifacts exactly. This is bounded compatibility evidence, not general XML fidelity or a new held-out result.

The three registered C01 outputs are freshly reproduced. Model and readable report match after LF
normalization; the complete graph differs only in source_model because its fresh output is outside the checkout.
The committed model/report/graph remain unchanged. The feature review excludes independent certification of
the reviewer's previously authored graph guard, while retaining its consumed hash and prior independent scope.
The first reviewer harness confuses raw CRLF and normalized LF hashes and refuses before product execution;
the original source/check and corrected fresh run remain. No product failure is inferred from that harness error.

Regenerate the model, graph and selected context/snapshot when using the updated reader. This change does not
redact original XML or previously generated packets/history. The named-field policy does not detect arbitrary
personal data in free text and does not establish a company permission or sharing decision. Original source
identity, placement, process/control eligibility, historical row 7 criteria and engineering acceptance are unchanged.

A fresh transition from the old leaked graph through a qualified partial answer to the sanitized graph confirms the distinction: six actual CLIs and one targeted MCP stdio session retain the old evidence and verdict, stale the answer and serve the old marker through decision history. The current node is sanitized. A newly regenerated context packet can therefore carry historical excluded values; preserved history needs review before sharing. No automatic historical redaction is implemented.

**Open N088 / N082.** A separate prospective E27 contract reads the existing LBNL dairy guide's floating-head,
minimum-pressure constraint and condenser-fan tradeoff sections before 13 matched unchanged-method baseline
CLIs. Eight violate the uncovered-train minimum: A-only and unrelated reset text, unknown/contradictory targets,
negated/disabled qualifiers and an own-anchor name can suppress B's review. All original fixtures, catalog,
other rules and benefits remain. This is a source/collection association failure, not evidence of plant energy
waste or permission to adjust a control. No E27 candidate or additional bounded source-review completion is
accepted here; 13 named rules have bounded collection reviews and 37 source contracts remain.

**Open N086.** Independent exact-occurrence review retains original false-match failures and a namespace-scope
failure. A strictly namespace-free diagnostic must disclose/refuse the original Comos schema-location attribute
rather than silently count it as supported. A future typed source-record contract must preserve original expanded
namespaces, opaque qualifiers, mapping uncertainty and never-reviewed removal history through graph/context/MCP.
No new whole-source fidelity score, source-owner acceptance or source-record consumer feature is claimed.

The root integration actually reruns all 13 matrix cells consuming dexpi_reader.py. Their complete substantive
results remain unchanged apart from timing and current code bindings; all 82 other complete cells remain exact.
The matrix still records 64 pass / 23 fail / 8 n/a, with criteria, source/key records and runner unchanged.
No bindings are backfilled and no failed cell is relabelled as passing because the metadata policy was repaired.

No provider/model call, new original-source download, company/plant/native write, network-boundary change or
LinkedIn publication is performed. Source interpretation and real engineer/company acceptance remain open.


## 120. Keep qualified private fields and condenser-train review at their source boundaries

**A260 / N089.** Original CLI probes demonstrate that a qualified Name can bypass the existing named-person
GenericAttribute policy, including when a canonical Name says Description or TagNameAssignmentClass. In the
latter case the protected synthetic value becomes a native unit ID before output filtering. The candidate
inspects every expanded-local Name designation and excludes the entire protected GA at the common eligibility
boundary before ga(), ga_lang() or native tag/title/fact derivation. This conservatively applies the existing
eight-role policy; qualified unknown fields acquire no process semantics. Raw tree/counts, missing/empty native
Value precedence and eligible neighboring values survive. No actual personal data is used.

The independently frozen reader/test candidate passes62author CLIs/271assertions and40reader tests with9explicit
archive-cache skips. Independent review executes90fresh CLIs/249assertions and22actual pinned MCP2.3stdio
sessions/199responses/655assertions. It follows seven unseen fixtures through full/core graphs and complete
selected context, sources, ownership and decision history. Six exposed original XMLs retain18complete artifacts;
the prior N087 fixtures retain9. Registered C01 model/report reproduce after LF normalization; its complete graph
differs only in the declared external source_model display path. Initial author/reviewer harness assumptions and
their original failures remain preserved separately; no product failure is inferred from those corrections.

This extends the bounded field policy, not arbitrary-text personal-data detection. Preserved registers can
still carry earlier excluded values into regenerated decision history. Regeneration does not scrub that history;
review retained evidence before sharing. The prior N087 acceptance retains its original narrower scope.

**A261 / N088.** Thirteen unchanged-method E27 baselines preserve eight train-coverage failures. A reset label
for A, unrelated C, an unknown or contradictory target, negated/disabled text or text on A's own name can quiet B.
The catalog-only repair removes that global quiet condition, shows supplied reset records as candidates and
keeps train membership/operating basis open for every applicable condenser, including an explicit shared reset.
The engine, other49complete rules and all50benefit objects remain exact.

The selected primary source is Brush, Masanet and Worrell, LBNL-6261E (2011), printed pp.62,65, independently
read in the official EPA ENERGY STAR distribution. It discusses conditional compressor/condenser-energy tradeoffs
and minimum-pressure demands. It does not prove this example's train membership, mode or savings. The conservative
association rule is software/engineering reasoning, not a verbatim source mandate or control-design approval.

Independent checks follow scope, canonical pointers, raw supported qualifiers, exact source/catalog identity,
full graph/context and actual pinned stdio readback. Changed sources/catalogs stale old answers while retaining
history; old CSVs, omitted tasks and missing/swapped sources refuse before writes. Screens and rollups are indexes:
retain original site/model packets for complete evidence. Matching names or pointers alone are not source equality.
The root's three persistent regression methods use identical corrected test bytes against both catalogs:
the released catalog fails and the candidate passes. An initial test harness used an ignored status field and
wrongly excluded diagnostics; the original code/results and corrected fresh runs remain. Only tests change there.

The six documented example producers are actually rerun, changing four food-screen/rollup outputs only. The private
question suite runs114cases successfully with one explicit optional-cache skip. The current inventory is50rules,
124collection requests and14bounded collection reviews;36rules still need source-adequacy review. N065human
usefulness and N062/N063real engineer/recipient/company/Copilot acceptance remain unobserved.

N086 source-record capture stays open. Its initial prospective inclusion/namespace/snapshot/mapping contract
was rejected before implementation; clarifications retain units/provenance metadata and separate raw retention
from native mappings. Unknown source structure must not invent process topology or company authority. Neither
repair changes historical corpus criteria or establishes unfamiliar-source/model performance.

Final integration runs all64cached test scripts successfully: five explicit Windows unittest skips and two
platform notices remain separate counts. All frozen tested inputs stay exact during the run. The13actual
reader-dependent matrix cells retain their complete substantive results, while82other cell objects stay exact;
the matrix remains64pass/23fail/8n/a with unchanged criteria. Independent matrix review checks124conditions and
all95declared input bindings. Its append-only review renews the current generated matrix evidence after testing.
Only review metadata, the generated feature page and this validation paragraph change after the full suite;
all tested product code, inputs and generated engineering outputs stay exact. The affected metadata checks pass.
The seven repository checks also pass:41numeric claims agree with their evidence, one remains prose-only,
52pipeline stages are fresh, four benchmark suites reproduce and30saved-prediction tables regenerate
(23MATCH/sevenMATCH-OLD). Five historical prediction gaps remain explicit; no commercial model is rerun.

No provider/model call, new original-source download, company write, live native import, firewall/tunnel change
or LinkedIn publication is performed.

## 121. Make owned revisions the foundation for cross-team work

**A262.** The lifecycle guide now organizes company context into owned published scopes with explicit
dependencies. Record-type authority can remain in existing systems. Native IDs are packet-local; source-revision
identities are not engineering merge keys. The company supplies reviewed engineering identities, access and
release authority. Conflicting proposals and outdated bases need reconciliation, not a last-writer decision.
The guide distinguishes this intended company pattern from the toolkit's current local mechanisms and caps.

A connected fictional pump example follows a note from revision A to B through actual questions, source-bound
decisions, explicit refresh and selected snapshot readback. A dependent answer becomes stale while a separately
sourced answer stays current; earlier evidence, ownership and decisions remain. The real generated E1 finding
is unanswered. The manual source questions, invented actors and incompatible raw units are labeled explicitly.
This is software accounting, not a reviewed engineering correction or company acceptance.

An initial portable packet worked after local copying but changed ten raw-byte comparisons under normal Git
text conversion. Its bounded earlier acceptance and original failing controls remain preserved. The revised
example pins raw input/worked bytes locally and retains all original notes, the selected catalog, native models,
context history and exact handoff hashes. Independent Windows review verifies108index and216checkout comparisons
with no mutations,12selected-pair validations,20product CLIs and4actual stdio sessions/62responses, including
4mixed-pair startup refusals. These counts describe the example's controls, not human or organizational trials.

Root integration also exposed a different-drive Windows output failure: os.path.relpath cannot represent an
output on another drive. That original failure and a separate root-test API harness mistake are retained.
The narrow output-path correction, persistent source-change/Git regression and optional SDK CI step are reviewed
separately before release. Existing product model, graph, question, context and MCP implementations are unchanged.

**Open N094.** Integration owns a four-packet Process/E&I/Maintenance and second-site exercise, with independent
Context/retrieval criteria and actual review. It must show explicit company-supplied identities, genuinely
selective dependency refresh, preserved same-field conflicts and complete bounded handoffs. The company route's
simultaneous-writer, stale-head, permissions, release, recovery and real-recipient tests remain external work.
The exercise is not yet included in the public toolkit or evidence of large-team capacity. N062/N063 and N086 remain open.

Root integration runs all65cached test scripts successfully in350.55s, with five explicit Windows unittest skips,
two platform notices and no additional skipped-check notices. Every tracked and new public input stays exact
during the run. The new persistent regression actually runs the revision journey, checks complete selected-pair
bindings/history and protects54raw inputs/worked files through108Git-index and216checkout comparisons plus12pair
validations. A separate different-drive run performs17producer CLIs and two pinned stdio sessions/31responses,
including both mixed-pair startup refusals. This is a local fictional workload, not company capacity or benefit.
Subsequent edits are documentation and append-only review metadata; product code, fixtures and worked raw pins
remain the tested bytes. No matrix method/input/output changes or model reruns are required for this example.

## 122. Keep departmental context separate while making dependencies reviewable

**A263 / N094.** A four-packet fictional exercise extends the local revision journey to Process, E&I,
Maintenance and a second site. Each keeps its graph, questions, sources, owner and register. A supplied teaching
map relates three Site A P-1 references to one canonical fixture identity while keeping Site B separate. Equal
tags do not drive an automatic join, and the index is not a supported federation schema or identity resolver.

Process and E&I explicitly stage the same published basis bytes. A source-only revision stales their two
dependent answers after actual refresh; E&I's separately sourced loop answer, Maintenance and Site B remain
current after their own real refreshes. E&I graph/question/asset/relation content stays exact in this fixture.
A real configuration change could legitimately reopen more answers; whole-document pins are not field-level
impact analysis. Earlier decisions, source evidence and ownership remain complete, with plant truth unknown.

Two distinct attributed answers propose `200 kPa` and `220 kPa` against the same source, question, claim and base. Both
remain proposed/partial with different reviewers and one question owner. Forward and reversed input orders keep
the complete proposal records and disputed state; neither selects an accepted winner. This is local string-value
dispute accounting, not engineering unit inference, simultaneous-writer control or company change approval.

The 97-file example retains 33 input fixtures, 61 worked files and 3 ordinary entry files. Independent review executes
38 fresh and 38 relocated producer/check/refusal CLIs, two complete stdio sessions with 24 responses and 101 assertions,
and two mixed-pair startup refusals. Two further SDK inventory sessions make six protocol operations. Its 391 independent
saved-result checks cover full bodies, histories, source pins and 27 closed local links. All original author and
prior example proofs remain unchanged; this is fictional development evidence, not a new source-family/model score.

Actual Git controls check all 97 index and checkout identities across two ingest and two checkout settings,
including 94 raw-pinned evidence files and 3 ordinary LF entries. The original driver CRLF bytes and declared LF
identity are distinguished explicitly; no source pin is recalculated to hide conversion. Independent review
retains a real default-Git failure on deeply nested Windows paths, then validates a shorter path with spaces.
The separately reviewed README paragraph advises a short Windows clone path. No global Git configuration changes.

The observed workload records packet/source bytes and command times only. Its two stale/three current denominator
belongs to the source-refresh stage, before later reviews and proposals. Shared publication copies count in each
recipient's source-byte total. None of these observations establishes throughput, large-company capacity, human
review savings, installed conditions or company acceptance. N062/N063 remain open; N094 closes only this bounded
composition exercise. The existing core graph, context, question and MCP implementations are unchanged.

## 123. Preserve committed byte contracts without rewriting the evidence

**A264 / N095.** The first A263 full-suite run preserves a real failure: 63 of 66 scripts pass, with three
failures and unchanged inputs during the run. Default Windows Git checkout had converted 20 unpinned contracts
to CRLF. Statement-review and impact outputs then differed from regenerated LF bytes; the drawing truth check
rejected its generator hash before reaching similarly changed model/layout dependencies. Canonical c6 Git blobs
still match every saved contract. The failed suite, exact inputs and complete logs remain unchanged.

The repair appends 12 scoped LF rules: three generated statement-review files, twelve generated impact/needs
files, and five current drawing generator/model/layout dependencies. It changes no producer, verifier, golden,
manifest, source pin, model value or metric. Each affected working file is rematerialized from its original Git
blob only after checking the failed-run raw hash and exact CRLF-to-LF equality. Those 20 Git blobs stay unchanged.

Private actual old checkouts pass all three affected test modules with autocrlf=false and reproduce all three
failures with true. Both repaired modes pass the complete 13/39/32-case modules with no added skips. The new
standard-library/Git regression checks 40 indexed and 80 checkout identities, existing raw packets and ordinary
text/binary negative controls. Separate real drawing API calls retain current successes, historical refusals
and genuine dependency-tamper refusals. Independent review repeats a fresh true checkout, all three workflows,
the new regression and seven API controls. Original setup errors remain separate from product failures.

**Open N096.** A separate probe finds an external-input contract mismatch: the writer's existing sha_file folds
CRLF pairs before hashing text, while drawn_truth checks raw bytes. Four actual writer runs succeed and generate
identical six-file outputs; the LF control verifies, but model-only, layout-only and combined CRLF inputs reject
their newly generated manifests. Real model/layout edits remain refused. The separately frozen private verifier
candidate uses the unchanged writer policy, with genuine edits, other whitespace and historical versions still
requiring refusal. It is not included in N095; independent repair acceptance and current-code matrix validation
remain separate gates. Raw original-document hashes and controlled source references are not normalized.

A fresh reader review also finds two practical gaps in the team guide: no actionable manual/Copilot route and
no record of who notices, sends and acknowledges a later publication. The revised README links one existing
first-question brief per owned scope and gives a human-maintained publisher/consumer/location/trigger/receipt
row. It explains the actual `200 kPa` to `220 kPa` draft-basis change without making it an installed setting.
This is company-owned manual coordination, not an implemented notification service. Independent document review
checks the route, source meaning and links; all 94 raw evidence pins and executable example bytes stay exact.

The successor full run passes all 67 scripts in 391.37 seconds, with five explicit Windows unittest skips,
two platform notices and no additional skipped-check notices. All tracked and new public bytes stay exact during
the run. The original failed 63/66 run remains intact. Root selected readback also passes on a different drive
with spaces in the path: 38 producer CLIs, two stdio sessions with 24 complete responses and both mixed-pair
refusals. Later changes are documentation/review metadata only; executable code, fixtures, contracts and source
values remain the tested bytes. N096's private correction is independently accepted separately, and public
source-capture corrections remain unaccepted until their own current-candidate review.

## 124. Verify a generated drawing with the writer's own text identity

**A265 / N096.** Four matched writer runs on the public Bayer model produce identical six-file outputs. The
canonical LF control passes topology verification with 40 items, 49 segments and 7 junctions. Model-only,
layout-only and combined external CRLF inputs instead reject their own freshly generated manifests. The writer
already folds CRLF pairs to LF when hashing these text dependencies; the verifier compared raw bytes. Separate
post-generation model and layout edits correctly refuse. All original commands, inputs, outputs and failures stay
preserved. This is a compatibility defect, not a new drawing-accuracy result or an operating observation.

The two-file repair changes only the verifier comparison to call the unchanged writer helper and clarifies its
docstring. Three new regression methods leave the previous 32 tests and helpers unchanged. The identical new
test bytes fail on the original with seven newline subcase failures; the corrected complete module passes all
35 tests. Its eight generator/model/layout newline combinations run the actual writer and verifier, compare
complete returned truth and six output files, and retain 21 negative guards. Real content changes, extra spaces,
bare CR, extra LF, missing/wrong hashes, historical revisions and altered key networks remain refused.

Independent review repeats the matched original/candidate runs and inspects the retained complete artifacts.
The existing helper performs no JSON-semantic, Unicode or general whitespace normalization. No writer, source
document, raw pin, manifest schema, public API, golden or criterion changes. Root integration adopts the current
033ec65 base only after proving the consumed methods match the private c6d70f2 baseline. Its current complete
35-case run passes without skips; matrix and whole-suite evidence are refreshed separately before publication.

Root actually reruns every cell whose declared dependencies include the changed verifier: 25 cells in four
command groups. All substantive values, reasons, details, source/key inventories, runner and registry bindings
remain exact. The only changes are the frozen execution-timing paths and the new verifier code binding; 70
other complete cell objects stay exact. Four intermediate matrix/page snapshots and command receipts are
retained. Historical TE revisions A/C keep their original refusal reasons. Counts remain 64 pass, 23 fail and
8 not applicable. No cell binding is backfilled and no failed cell is promoted because the text identity was fixed.

Independent receiving review checks all four complete snapshots and their rendered pages, the exact declared
cell sets and all 95 current input bindings. The root full suite then passes all 67 scripts in 445.33 seconds,
with five explicit Windows unittest skips, two platform notices and no additional skipped-check notices. Public
source bytes remain unchanged during that run. The later review append and generated feature index are metadata;
the tested methods, fixtures, source bindings and matrix artifacts stay exact. This does not establish company
capacity, concurrent editing, engineering acceptance or operational benefit.

A later private check helper reuses the producing log's filename and overwrites its complete bytes after the
independent review has inspected and hash-checked them. The original 4,826-byte transcript is explicitly recorded
as lost; its historical hash, command receipts, four snapshots and review stay unchanged. Under a separately
frozen recovery contract, root repeats the same 25 cells in a scratch directory with exclusive per-group logs
and complete snapshots. All substantive comparisons use the original criteria; all 2,876 public files stay
byte-identical throughout. Strict checks again verify all 95 input bindings. Independent receiving review
accepts the new retained transcript and snapshots. This diagnostic repeat neither reconstructs the lost log nor
replaces the original published timings, and adds no independent trial or performance claim. Later check logs
are isolated from producing logs; the first loss and the failed publication guard remain part of the record.

## 125. Keep native intake exclusions consistent through drawing diagnostics

**A266 / N090–N093.** Existing source probes expose four separate intake failures: a drawing metadata value
without a Name can raise TypeError, an unkeyed plant-structure value can become a fabricated `null` key,
duplicate-ID errors can echo an excluded identifier, and the optional PNG diagnostic inventory can derive a
label from a protected field. Deliberately nonstandard records nested inside protected metadata can also enter
native traversal. Original failing commands and output/sentinel records remain preserved.

The native-only correction keeps the existing named-role field policy. Missing metadata Name attributes are
reported as not mapped; empty-value precedence and present empty or literal `null` names remain distinct.
Duplicate validation still runs first and counts distinct duplicated IDs without quoting them. Reader-owned
diagnostics use the original root and expanded-name witnesses before deriving labels or counters. Protected
descendants stay outside native interpretation. Physical records inside that metadata and protected content on
the optional adapter's semantic read paths refuse before output. This is precise unsupported nesting, not a
general schema validator or personal-data detector. Original XML and retained image bytes remain unsanitized.

The independently reviewed private native variant covers 340 finite scenarios, 32 Python API sessions and
27 complete original artifacts. Its earlier short-PNG and full-source-only counting failures remain separate,
with their actual code hashes. The public integration adopts d41c044 explicitly: reader/test and consumed
helpers match the earlier released baseline; the later drawing-verifier function is not reached by the native
network path. No source-evidence module, document-ID feature, transport or source-aware consumer is included.

On the current checkout all 52 reader tests pass with no skips. Six already exposed public inputs reproduce
all 27 complete native artifacts byte for byte. The registered C01 model, report and graph also reproduce in
full, without a graph display-path exception or a golden change. Root actually refreshes the 13 reader-dependent
matrix cells; 82 complete cell objects stay exact. The prospective comparison permits only execution timings,
the reader binding and six exact duplicate-ID messages derived from the original AutoCAD XML. Every other
value, source/key binding, reason, detail and criterion stays exact. Counts remain 64 pass, 23 fail and 8 n/a.

Independent receiving review accepts that functional evidence. Its 343.06-second execution raises a separate
cost question: earlier runs of the same selections completed much sooner. A frozen two-input observation then
finds repeated cap-sized reads and higher traced heap peaks with complete outputs unchanged. Publication was
held pending N100's allocation repair; functional acceptance does not establish acceptable cost,
large-team capacity, actual recipient usefulness or engineering acceptance.

## 126. Bound read requests without reducing source-integrity checks

**A267 / N100.** The native-only candidate passes its functional checks but takes 343.06 seconds to refresh
the 13 affected cells. A separate frozen probe uses the released reader and that candidate on two already
exposed XML inputs. Twenty-eight isolated jobs separate warmups, plain wall/CPU samples, allocation traces,
profiles and source-read witnesses. Complete outputs stay byte exact. Each candidate run requests 268,435,457
bytes seven times even for the 7,477-byte input: once for acquisition and six times for source rechecks.
Separate traces show a cap-sized transient allocation. That evidence justifies investigating the reads;
it does not establish a cause for every part of the matrix runtime or measure company capacity.

The correction adds one private helper and replaces exactly two read expressions. Each request is at most
65,536 bytes and the total acquisition still stops at the existing MAX_BYTES + 1. Positive short reads continue;
only empty bytes mean EOF. Exact original bytes, the 256 MiB input limit, single parse and cached raw hash stay
unchanged. All seven lexical guard sites and their route-dependent order remain; optional PNG routes have more
guard invocations than the two no-PNG examples. Existing error types, causes and late-write prefixes also remain.
There is no stat shortcut, skipped recheck, streaming parser, rollback or atomic-publication claim.

The pretest-frozen two-file variant preserves all 52 earlier test bodies and adds four regressions. The same
new tests on the original include a real public-run oversized-read witness failure and an injected short-read
parse failure; an absent-private-helper failure is recorded separately. All 56 candidate tests pass. Finite
boundary, short-read, I/O and guard controls retain every byte and refusal boundary. Six original inputs retain
all 27 complete artifacts. The 148 matched Python API sessions preserve guard order, full errors and output
prefixes; observer chain and NameError failures remain recorded separately from product behavior.

A new 28-job plan compares the native candidate with its bounded-read successor using identical dependencies.
Every complete artifact stays raw and canonically equal; no sample is discarded. The following are observations
on one Windows host. Plain times are medians of three runs per cell; each heap value comes from a separate traced
run, is Python heap rather than RSS, and is not added to nested profiler times.

| Saved input | Plain median seconds: cap-sized → bounded | Traced peak bytes: cap-sized → bounded |
|---|---|---|
| C01, 445,726 input bytes | 0.480223 → 0.075924 | 273,215,789 → 11,878,464 |
| I04, 7,477 input bytes | 0.422536 → 0.031376 | 268,895,531 → 7,765,931 |

Independent review checks the frozen proof files and recomputes those observations, then executes its own
boundary streams, mid-read faults and matched no-PNG/PNG/retained-image guard cases. It accepts the exact private
successor without a wall-time threshold. The original native functional result, slow execution and first probe
retain their original hashes; none is relabelled as evidence for the successor.

Root separately adopts the successor on d41c044, passes all 56 reader tests with no skips, and reproduces the six
originals/27 raw artifacts and three registered outputs without display exceptions or golden changes. Both
actual corpus-producing groups refresh all 13 declared cells. All 82 other objects and every substantive field,
including the six already corrected duplicate-ID messages, stay exact. Only the frozen timing paths and reader
binding change. Strict checking verifies all 95 input bindings. This is bounded input-handling and compatibility
evidence, not a new extraction score, held-out source family, engineering approval or general scale benchmark.

The complete current repository suite passes all 67 scripts in 774.85 seconds, with five explicit Windows
unittest skips, two platform notices and no additional skipped-check notices. All tracked public bytes remain
unchanged during that run. The later append of two independent review records, feature-index regeneration and
this factual journal note change only metadata; the tested methods, fixtures and corpus artifacts stay exact.
Suite duration is an execution receipt, not a throughput or capacity benchmark.


## 127. Preserve structured source evidence only when explicitly requested

**A268 / N086 / N098 / N099.** A Native interpretation cannot account for every source record merely by counting
placed assets. The opt-in capture path now retains eligible structured XML occurrences, expanded names, parsed
attribute values, source identity and explicit Native assignments. Retained but unmapped occurrences stay visible.
The complete captured packet follows its declared scope and named-field policy; text/tail presence is counted
without retaining its payload, and presentation/geometry exclusions remain explicit. Original XML and images
stay separate. This is source observability, not a new physical model, XML round trip or general PII detector.

The public default stays Native-only. Python callers use the keyword-only builtin boolean `capture_source=True`;
the CLI uses `--capture-source`. Supplying a source document ID without capture refuses before input/output work.
Disabled conversion performs no source capture or backend import. Enabled capture preserves the complete
previously accepted source-bearing output rather than dropping fields to reduce its cost. Source occurrence IDs
bind document identity and raw revision bytes; they do not establish company asset identity or approval.

Pre-publication controls caught unsafe origin equality and mutation before canonical encoding failed. The source
writer now requires exact original handles and admitted fields; foreign, excluded, malformed and callback-bearing
inputs refuse. A write's encoding is checked before changing Native values or provenance generations. Equal values
are not evidence of a shared origin. Earlier failures remain recorded separately from the corrected method.

Independent private receiving checked the exact five-file successor from raw Git inputs. The 56 existing Native
test bodies remain unchanged; the source-only fold case and 38 source tests explicitly enable capture, alongside
11 new mode tests. Four additional enabled-mode bounded-read controls make 110 unit methods with no skips in
that receiving cohort. The complete 27 Native artifacts match the prior default bytes and the complete 27
source-bearing artifacts match the accepted capture baseline; neither comparison strips fields. Separate scoped
projection comparisons remain labelled as projections. Both modes preserve all seven source guard sites, route
order, errors, causes and full late-write prefixes across 296 API sessions and 148 matched comparisons.

These are offline implementation and preservation checks on public/development fixtures. No new model extraction,
held-out drawing family, company source, timed human review or large-team capacity result is established.

## 128. Make the local handoff reproducible without a private cache

**A269 / N097.** The optional local handoff separates an already source-bearing model into a Native projection,
complete policy-filtered evidence packet and hash-bound manifest. Explicit inspection validates the three selected
roles and reports a qualified brief. It never captures a missing source, follows references or grants company
ownership. A later failure can leave a partial prefix; a manifest's presence is not atomic publication or approval.
Ongoing identity, permissions, review and decisions remain responsibilities of the company-managed system.

The public training fixture includes the unchanged 6,144-byte DEXPI reference XML and its saved source-bearing
model, with CC-BY-4.0 attribution and adaptation notices. Native/evidence/manifest example bytes and metadata were
derived independently before actual export and selected-file inspection. The manifest's supplied training scope
and role are data. Complete captured evidence is not every original XML byte or proof of installed equipment.

The earlier private harness depended on a D drive and private fixture selectors. The new portable cohort uses
committed inputs and the caller's temporary directory. Its 12 groups cover complete values/order, strict receiving,
raw/canonical identities, bounded reads, encoded brief limits, Git checkout/relocation and late-write prefixes.
Three added reporting methods keep an unavailable platform subcheck visible and reject unrelated I/O failures.
An initial attribute-file CRLF checkout failure was preserved and corrected by its declared LF policy. Review also
caught archive-smudged base claims and a notice that the suite runner could not count; corrected raw-Git receiving
and the matched notice/error witnesses retain those earlier failures, without changing the utility or its oracles.

Independent receiving ran all 15 methods and separate functional/reporting controls. This Windows account could
not create one native escaping symlink: the runner reports one platform notice, zero unittest case skips and
zero other notices. A separate real junction exercises successful escape refusal. This is not an unqualified
all-checks or cross-platform runtime pass. A fresh private replay also ran the unchanged historical 105-group and
independent 36-group harnesses on the adopted dependencies: 141 groups, 1,292 assertions, 94 real CLI calls and
six large in-process export vectors. Private selectors remain confined to that historical replay, not public CI.

No source-aware graph/context/MCP consumer, shared governance service, live process connector or ontology engine
is added. The toolkit prepares inspectable inputs and an initial engineering packet; the maintained company
record and operational execution remain separate.

## 129. Receive the public source handoff without changing Native results

The public worked trio was derived from data-only expectations before actual export and inspection. Three root
CLI commands reproduce its complete Native/evidence/manifest bytes and entire text/JSON briefs; separate public
XML default/capture readbacks reproduce both complete saved models. An independent reviewer executes the four
selected public readbacks and checks reassembly, raw bindings, license, guides and runner controls. The new
captured fixture is freshly validated; the older three C01 outputs are explicitly inherited unchanged.

The current reader then actually reruns the 13 affected Native-default matrix cells, with both intermediate and
final full snapshots retained. Independent strict canonical comparisons preserve every substantive value, type,
diagnostic and existing source/key binding; all 82 other complete objects stay exact. Only the predeclared timing
fields, reader binding and conservative static source-module dependency change. The unchanged AST recorder
follows lazy imports; its extra source dependency is not evidence that these cells execute capture. Results stay
64 pass, 23 fail and eight not applicable. The separate strict check verifies all 95 declared cached input bindings.

The full cached-data runner exits zero for all 70 registered scripts in one 605.482-second Windows observation:
five unittest case skips, three platform notices and no additional skipped-check notices. The handoff's unavailable
native-symlink subcheck is a notice without a skipped unittest case. All 2,889 public files remain raw-identical
during that run. This is not a complete runtime pass, timed engineer trial or capacity measurement. The four
benchmark suites reproduce; claims match 41 numerical records plus one prose-only record; all 52 pipeline stages
are fresh. Saved predictions reproduce 23 MATCH and seven MATCH-OLD tables, retaining five historical GAPs.

Post-run content review corrects the stale status count, distinguishes implemented capture accounting from
remaining engineering/source acceptance, and makes downstream model eligibility explicit. The runtime log also
exposes an older inaccurate runner banner: full mode does start a temporary loopback OPC UA test service. Its
message and agent instructions are corrected to disclose that service; source-only excludes that integration test.
The correction changes diagnostic text and documentation, not test selection or service behavior. Targeted runner
and metadata checks follow separately; no second local full run is implied. Committed-tree and exact-head CI
verification remain separate publication gates.

## 130. Carry complete finding identities into readable handoffs

**A270 / N101.** An author-led audit from three reader perspectives found a concrete screen-to-brief mismatch:
the first-question guide requires the complete finding ID, but readable screens showed only the catalog rule.
Three actual old CLI runs retain 12 missing full references, including distinct TE findings under the same H4
and C1 headings. The JSON already had the right IDs. This is a presentation defect, not evidence that the questions
were missing, useful to an engineer or accepted by a company.

Each readable finding now carries its exact existing finding reference and ordered asset IDs, explicitly encoded
as a JSON string and array. Backtick-safe code spans and JSON escapes preserve punctuation, Unicode and whitespace.
Rule headings and all existing prose remain. These are local model/screen references, not global company identities;
the guide retains source/model and catalog-version requirements and the manual no-model starting route.

Matched actual production runs cover all 13 committed screens: 13 baseline and 13 candidate commands retain 90
complete files per role. Independently frozen whole-screen expectations verify 99 finding/asset references. The
zero-finding MGPI screen stays exact. Complete question JSON, rules, evidence, requests, ordering, graphs, context
histories and answers stay unchanged. Two actual description builds update their receipts: only the question-engine
code hashes and the assisted screen's artifact hash change. Other description artifacts remain raw-byte exact.
No saved hash is manually restamped. Ordinary stdout and the separate roll-up retain their own matched controls.

A new regression checks both current published description bundles against their five declared producer hashes,
complete artifact sets, raw artifact hashes and retained source/answer bindings. It passes on the old baseline,
rejects both stale receipts after the renderer changes, and passes after actual rebuilds. This checks the declared
publication contract, not transitive dependencies, interpretation accuracy or engineering acceptance.

The shipping tests require whole current goldens, with no fallback to old screens. Targeted private validation
passes 121 question-engine methods with one symlink case skipped, plus all 13 description-workflow methods and
nine independent encoding controls. The nonverbose question-suite log does not retain the skipped OS exception.
An initial regression launch from the scripts directory produced two failures and five errors in repo-relative
fixture paths; that complete failure is retained. Correcting only the caller to the repository root produces the
reported result. Test-oracle and producer-specific Markdown preparation corrections are retained separately.

The current corpus matrix and configured pipeline have no question-engine code binding, so no cells, criteria or
stage records are restamped. No model calls, new source family, measured review time, company transfer or general
question-usefulness result is claimed. Full public-suite, committed-tree and exact-head CI checks remain separate.


## 131. Make tag reading comparable and give new engineers a starting path

**A271 / N102.** The contributor guide named tag reading as a missing task adapter. The existing scorer already
defines two different jobs: strict/lenient text on geometrically matched labelled symbols, and substring recall
against partial identifier lists. The new `tag-reading` task preserves those rules and keeps mode, family,
source/key/protocol and model/method identities separate. It reports counts, real rate denominators and defined
versus total repeats; it does not manufacture tag precision or F1.

The portable example copies thirteen existing DEXPI adaptations and their original license with attribution:
five PNGs, three GraphML keys, three tag keys and two partial lists. All original-source/image pins match the
cache, and all fifty main saved predictions retain their exact image/prompt/method/model/date/resource metadata.
Current converted keys are frozen for exposed development. Matching earlier metric vectors does not authenticate
the exact original historical key bytes or producing converter. No new model run, source family or blind trial
is claimed. The source/provenance manifest is validated on the actual benchmark path, including raw artifact and
license hashes and sizes; ordinary LF fingerprints alone cannot hide fixture corruption.

Independent prospective controls were frozen before implementation. The unchanged scorer reproduces two
identity defects: duplicate IDs can lend text from an ineligible symbol, and an empty matched ID loses its tag.
Only the new geometry task rejects ambiguous IDs across every supplied row, counting the entire invalid answer
as empty. Partial lists retain their existing substring rule without imposing geometry IDs. The old scorer,
predictions and three earlier tasks remain unchanged. Invalid keys and conflicting provenance refuse before
answers are considered; failed/missing attempted answers retain the full truth denominator.

Actual validation retains thirty passing shipping methods, fifty whole saved answers, and independent fifty-three
control groups plus six raw-source controls. The physical escaping-symlink variant could not be created on this
Windows host. A persistent regression now makes that capability skip explicit and can exercise the branch in CI.
A pre-run Git control originally put space-before-tab in the middle of a line; the corrected leading-indent
control and every earlier draft are retained. No failing candidate run is hidden by that correction.

The compact report states metadata once per mode/model/cohort group and uses five-column rate tables. All twenty-four
displayed rates and complete counts/status/limits survive. A formatting-only run matches independently frozen
whole JSON and Markdown; two focused methods pass and the physical-symlink method skips on Windows. Four older
suites were actually re-scored to new prefixes. Independent canonical serialization proves all typed semantic
values unchanged apart from measured implementation fingerprints and their derived IDs/order. Earlier reports
remain unchanged. The root's initial Python equality comparison alone was insufficient to prove numeric type
identity; the independent receiving check closes that proof limitation without repeating producers.

The entry documentation also broadens from an equipment question to an engineering assignment. Leaders can
prepare approved sources, a mentor, a starter workflow and a reviewable first contribution; engineers and interns
can reuse the source-first brief. P&IDs remain a labelled manufacturing branch. The new onboarding guide and
example-series map distinguish working routes from proposals. A generic knowledge/workflow MCP catalogue is
still separate implementation work; the current reader serves selected engineering graphs/context. Company
systems retain identity, permissions, accepted decisions and record authority. No onboarding or productivity
benefit has been measured. Public full-suite, committed-byte and exact-head CI gates remain separate.

A bounded reader audit also checks the task routes and eighteen top-level example guides. The historian
walkthrough now separates offline analysis from optional OPC UA replay and explicitly binds its example
listener to loopback; the replay tool's default is unchanged. Statement review links current steps before
dated results. Three guides distinguish contributor fixture regeneration from a separate working output.
The script-index generator retains complete first sentences rather than clipping three descriptions mid-word.
The contribution guide records the what/why/how standard and keeps unpublished LinkedIn copy in an external
private folder or the ignored local publishing folder; tracked tutorial visualizations remain public.

The public full run finishes with 69 of 70 programs passing, six unittest skips and three platform notices.
Its single failure is the matrix freshness check: the clarified historian guide is a declared input to
row 6 / te-braatz-runs. That dependency was missed during the documentation follow-up. The failed run and all
unchanged input hashes are retained. Reproducing only that cell keeps all 94 other cells and all outcomes
exact: 64 pass, 23 fail and 8 not applicable. Its guide fingerprint, measured timings and the same published
claim's line locator change. Independent receiving first stops on the unanticipated locator shift, then
admits only line 150 to 155 after checking the identical source passage. The strict scratch check verifies
all 95 source bindings. Affected-test and final metadata receiving remain separate; the original full run
is not relabelled a pass, and no model or other corpus cell is rerun for this correction.

## 132. Give engineers a sourced starting map without an asset model

**A272 / N103.** A newcomer can use a selected knowledge packet for a landing map, glossary, source records,
reviewer roles, a starter workflow and one document-only assignment. Three read-only operations work without
an equipment graph and can share the existing MCP entry point with graph/context. Workflow steps remain
reference data. Supplied source-basis agreement is not source truth, permission or acceptance.

Before any producer execution, independent static review froze four cases where early duplicate record/step
checks could mask later local errors or the required record-order tie. The successor validates local/profile
and companion fields first, then record/step uniqueness in original record/schema order. Original body and
controls remain preserved. A separate concern about JSON-looking text being coerced was disproved by the
pinned SDK source: string-annotated fields skip that preparse. Five literal strings became positive controls;
no SDK defect is claimed.

One authorized private run completes eight commands. Four suites report 134 methods: 133 execute and pass;
one existing graph filesystem case skips, with its exact identity absent from the nonverbose log. Three
standalone CLI outputs match independently frozen complete typed/order expectations except runtime load time.
The copied stdout files retain their actual clocks and bytes, separately from fixed-clock test oracles.
Local SDK auto/legacy checks exercise the A/B/C records, complete pages, source qualifiers, raw argument errors,
size guards and old graph/context values. Coverage comes from retained helper assertions and logs, not
fabricated raw RPC transcripts.

The exercise is fictional software evidence, not a customer, source-authority or employee-onboarding trial.
Unknown originals retain null fingerprints; capturing peer memory does not verify its explanation. Company
systems retain identity/access, controlled records, accepted decisions and work execution. Human benefit and
organization-scale capacity are unmeasured. Current-base integration, public review rows, full-suite and
exact-head CI gates remain separate from this private result.


## 133. Audit the broader toolkit and preserve review evidence

**2026-10-31, Central time.** A holistic pass from `1b39115` found that the P&ID and onboarding labels hid
existing modeling, correction, analysis, source-handoff and evaluation paths. The repository is now
**Engineering Context Toolkit** (`steve-vitale/engineering-context-toolkit`). GitHub's stable repository ID and
branch tips were checked before and after the rename; the old Git/API addresses resolve to the same repository.
Active badges, clone instructions and citation metadata use the new address. Historical source URLs, output
records, protocol namespaces and the local working-directory name are retained. Citation metadata no longer
labels moving main as the old 1.0.0 release; users should cite the commit or release actually used.

The README now selects by engineering job and names each work product and boundary. The documentation map
includes experienced engineers and contributors. STATUS separates reproduced implementation failures,
engineering-quality research, optional adapters and actual company acceptance, with earlier repairs retained
in a collapsed reference. These editorial changes do not broaden any tool's input contract.

### Reproduce defects before repairing them

The review-kit baseline accepted changed drawing/overlay/base-queue evidence and non-review columns under the
old bundle identity. Imported timer histories accepted unknown/interior events, invalid transitions or changing
reviewer IDs. The repair verifies all three packet hashes and the manifest digest, preserves source fields
outside the declared OPS columns, and uses the same event/identity/time validation for imported and appended
logs. Rejected appends leave the timer file unchanged. Hash checks do not authenticate a reviewer or source.

A vendor answer with a finite integer coordinate too large for float conversion raised OverflowError and
aborted the report. Adding that exception to the existing malformed-answer guard retains the failed answer as
empty while scoring the remaining answers. Non-object rows were already guarded, and an unused deeply nested
JSON field did not reproduce a parser failure; neither was treated as a new defect. The first new regression
asserted the detailed exception in the wrong output channel; that test-only assertion was corrected to the
saved report diagnostic, retaining the original failed test receipt and product behavior.

CSV replay now defaults to 127.0.0.1, reports the actual chosen interface, rejects nonfinite/nonpositive rates
and checks an invalid start row before server initialization. Other interfaces remain explicit lab choices.
This deliberate default change does not create authentication, encryption or a production OT connector.
Matched baseline probes used a mocked server; the existing targeted smoke exercised local loopback only.

Targeted modules pass 17 review-kit, 14 vendor and 41 CSV tests. The five added review/vendor regressions fail
against the old methods. Fourteen synthetic CLI controls retain the original valid timing/summary and
perfect/empty-answer reports while refusing the eight invalid review cases and retaining the overflow failure.
These are software controls, not observations of real engineering labor or usefulness.

### Refresh only affected evidence, without changing the results

Fifteen scorer-control matrix cells were actually rerun for the changed vendor method. One intake cell and
one historian cell were then actually rerun for their changed guide bytes. The combined 17 cells preserve
their substantive outcomes and diagnostics; the other 78 complete cell objects remain exact. The matrix still
records 64 pass, 23 fail and 8 n/a. Updated timings and source/method bindings are produced by those runs;
the historian claim's locator moves by the four inserted guide lines, with the same quoted passage.

The current OPEN100 saved-answer benchmark is reproduced into a new report pair, retaining the earlier report.
Scores, controls, predictions and recipes remain the same; the implementation fingerprint and derived cohort
identities change. The other four current report pairs retain their bytes. The review-kit pipeline stage is
actually rebuilt in a private scratch root: its seven packet artifacts remain byte-exact and only that stage's
code binding changes. These are fresh offline producing calls, not new commercial-model runs or evidence of
improved extraction accuracy.

The stricter integrity check also required clearer review instructions: save the filled CSV as a separate copy
before editing or spreadsheet autosave, keeping the original packet unchanged. The kit guide and reviewer guide
now state that path, the one-reviewer timer contract and the distinction between integrity and authentication.
The first seven-artifact reproduction remains preserved; the intentional guide change needs its own subsequent
stage binding rather than relabelling that earlier receipt.
That second actual stage preserves the six generated packet files and retains the reviewed manual guide;
only its README output hash changes from the first rebuild. The other 51 stage objects remain exact.

### Complete one authoring and contribution path

The knowledge-only onboarding example gains a six-record private-copy starter and field-by-field guide. The
starter has no original source bytes, engineering answer, assigned owner or verified fingerprint. Local reads
validate structure; they cannot decide source authority or permission. The guide distinguishes record revision
from document revision, evidence pins from dependency links, and explicit restart from automatic synchronization.
Four positive reads, three revision readbacks and five negative refusals exercise the guide's declared behavior.
The earlier 42 example artifacts remain byte-exact.

The worked note uses the existing fictional notices and attributed peer memory: 250 kPa equals 2.5 bar, while
cause, deployment and governing revision remain unknown. An explicitly author-illustrated mentor comment
corrects an overclaim before the revised draft. No real mentor, employee trial, acceptance or onboarding benefit
is implied. Company access, authenticated decisions, work execution and continuing ownership remain in company
systems. The source-adequacy backlog, matrix failures, missing historical predictions and actual company
acceptance are still open; a broader name does not close them.


### Integrated validation and retained file-set failure

The current candidate's full offline run passes 71/71 test programs in 474.024 seconds, with six skipped
unittest cases, three Windows platform notices and no additional skipped-check notices. The skip categories
remain separate; this is not complete runtime, company or engineering acceptance. Publication checks match
41 numerical claims with one prose-only claim; 52 pipeline stages are fresh, the 95-cell matrix is current,
and five current task/model suites reproduce. Saved predictions reproduce 30 tables (23 MATCH and seven
MATCH-OLD); five older tables remain GAP. One stale generated script-summary row was regenerated before the
full run, retaining its initial failed check.

The test process exits zero, but its wrapper's final file-set assertion fails: a parallel read-only browser
retry of two previously inaccessible LinkedIn references creates four untracked capture files inside the
checkout. All 2,978 frozen input files remain raw-byte-exact and none is missing. The four captures are moved
to private storage with their exact hashes preserved, and the original 2,978-file set is checked again before
any publication edits. The original failed wrapper result and logs remain immutable; a separate recovery
receipt records this distinction. No tests are rerun to replace that result. Browser capture files are now
ignored by default, alongside private LinkedIn drafts. The capture-producing research does not add a corpus
case, dependency or product claim to this release.

Only the ignore rule and the STATUS/journal result wording change after that run. Source/implementation,
predictions, scorecards, registered outputs and the other public input bytes remain as tested. Independent
receiving, committed-blob identity and exact-head CI are separate checks.


## 134. Make own-plant transfer explicit and retain function evidence

**2026-10-31, Central time; receiving records continue into November 1 UTC.** Steve identified a framing defect:
case-specific limits had become general statements about what the reader could build. The purpose is to teach
and provide tools for their own plant, using public inputs to demonstrate the method and evaluate its limits.
The README and documentation map now distinguish reusable tools, tutorials that substitute the reader's records,
and case studies/evaluation. The own-P&ID, description and XML routes lead to a sourced draft model: review and
enrich it, supply reviewed signal identities and process records, then connect and maintain the useful parts.
The TE gateway assembly remains a specific reference application, rather than a restriction on the generic tools.

The generated deliverables page now labels what was built in each case. Its rows, source notes, numbers and
internal status keys are unchanged. Missing OPEN100 process data is an input need for that case, rather than a
blanket impossibility. The script inventory separates own-input wrappers from case-study CLIs and describes
direct XML separately from prepared public DEXPI keys. No runtime builder or graph-export algorithm was changed
to obtain these wording improvements. Portable JSON still needs receiving mappings/import acceptance outside
the repository's documented readers.

A second reader pass found two surviving review-priority promises. Own-drawing intake supplies an unranked
sheet; fitted red/amber/green tiers belong to the OPEN100 research workflow. The review guide, archive planning
reference, feature inventory and own-drawing report description now agree. The archive plan's proposed
cross-source reconciliation is explicitly site work. The guide-bound own-drawing and Bayer export matrix cells
were actually rerun after the prose edits; the other 93 complete cell objects and all outcome counts remain
unchanged. A final own-guide clarification prompted one further actual intake-cell refresh, preserving the
previous run. The structural deliverables check was actually rebuilt, retaining the numerical/source criteria.

### Keep labels as candidates rather than answers about actual function

Original ENERGY STAR/LBNL dairy and fruit/vegetable guidance informed prospective expected questions for E29,
E30 and C11. Their prior label-only exclusions could quiet a machine investigation without establishing actual
part-load control, defrost initiation or exhaust strategy. Twenty-one synthetic cases had expectations frozen
before baseline calls. Four later E30 cases isolate a separate anchor-versus-related-defrost interaction;
they remain exposed development cases. All 25 original inputs and observations are retained. The old method
missed 23 expected subjects in 18 cases; three no-anchor controls stayed quiet. This is neither 25 plants nor
a held-out model-extraction benchmark.

The revised rules retain named subjects and shown control/measurement records as candidates, with three open
records-first requests per finding. Initiation differs from termination; humidity is one possible variable,
not a universal control requirement. Per-machine keep-open behavior is conservative authored software policy
informed by the sources, not a quoted source mandate. Source PDF byte equivalence to older downloaded copies
was not established, and no new raw PDF was added.

An opt-in evidence field list preserves literal supplied values, including false, zero, unknown and blanks,
with exact source locators. Native controller/interlock qualifiers use an evidence-only carrier; their ordinary
selector facts remain empty so, for example, a temperature qualifier cannot activate an unrelated heater rule.
The other 47 question objects, all 50 benefit objects, catalog source objects and the 124-request inventory remain unchanged.

Independent private receiving passed 50 CLI sessions and 1,710 bounded checks for the first candidate cohort.
An additional encoding probe then found a real defect: an escaped lone surrogate in a selected value or field
name could truncate questions.json before the encoding error. That candidate was not accepted. The UTF-8 successor
candidate preserves otherwise unencodable values as JSON escapes and rejects invalid UTF-8 field names before
writes. Ten affected follow-up sessions passed 1,187 checks; four complete normal report pairs stayed raw-exact.
The previous cohort was inherited only after an explicit narrow code/encoding audit, not rerun for a new label.
No source-informed check establishes installed function, engineering approval, useful human questions or savings.

### Retain less expanded knowledge at startup

The knowledge reader previously retained every root's expanded dependency paths. It now retains direct basis
diagnostics and computes complete root paths when needed, while eagerly admitting every full record response
before construction returns. Whole-packet validation, error precedence, response limits, path order and deep-copy
isolation remain. Independent controls compared 260 compact complete responses and exercised the actual 2 MiB
boundary, late invalid records and nested mutation isolation. The public module's 29 tests passed after adoption.

On the finite 128-record synthetic chain, median traced peak allocation changed from 6,300,073 to 779,497 bytes;
live traced allocation changed from 6,052,931 to 422,475 bytes. Baseline and candidate each had nine fresh-process
samples across three sizes, not interleaved. Observed constructor time increased on that chain (0.9968 to 1.2133 s).
This trades retained memory for computation; it is not a latency win or a large-company capacity measurement.
The four-team tutorial also gains a compact reading of its existing actual observations: two source-dependent
answers reopen, three independent answers retain status, and a fresh source answer can still leave proposals disputed.

### Preserve the failed historical Docker starts

Node-24 GitHub Action majors replace the earlier forced-Node-20 compatibility path. The CI-only head passes its
tests and MCP jobs, but all three fresh Docker browser starts fail. The frozen October 8 backup requests historic
TE tag spellings absent from the current 52-channel replay. A pinned, opt-in Docker compatibility profile adds
36 literal source-column aliases, preserves the default 52 channels and leaves unavailable SC-212 unfed. Backup
and current model bytes, browser thresholds and fault predicates remain unchanged. Paired values are Double/Good
with identical UTC replay-publication timestamps; no current plant acquisition or identity inference is claimed.

Independent source/receipt review accepted the seven-file repair. Its focused child passed; the wrapper exited
one because two existing band outputs became CRLF. Their full LF text and parsed JSON remained equal; the other
2,979 retained file hashes matched. This is a qualified result, not an all-raw-files pass. Those generated bands
were not adopted. The browser fault diagnostic also stops naming an unrelated positional label as PT-107.
Fresh Docker acceptance remains a separate gate. The two manual current replay stages retain historical receipts
and remain stale after the server edit; historical Docker acceptance cannot renew native-gateway evidence.


### Integrated renderer compatibility check

The first public question-engine module run executes 130 tests: 128 pass, one is skipped and one errors.
All 3,025 public input files remain raw-exact. An existing zero-finding renderer test supplies only families
and sources; the new opt-in renderer lookup incorrectly requires a questions key even though there are no
findings. The original failure is retained. A one-expression fallback to an empty question list restores that
existing API contract. Independent AST receiving confirms no other code delta; full catalogs used by the
previous producers still take the identical branch. Three affected existing/new renderer controls pass.
The prior 16 successful producing calls and separate revised review remain their actual historical observations;
only the two description bundles need new actual builds for the changed implementation-hash leaf.

The review-refresh producer also initially fails its old assertion that rejecting a drive newly adds E29.
That assertion conflicts with the source-informed keep-open policy. The revised exercise instead checks that
K-203 stays in review, SC-203 is present as a candidate before rejection and absent afterward, and only the two
exhaust/recovery findings are newly added. One revised exercise passes; the other 16 calls are not repeated.
Independent receiving checks 92 actual artifacts, 80 non-target finding records, the 38-finding/24-question
rollup and the complete description inventories. Seven unrelated JSON outputs differ only in line endings;
their full LF text/JSON matches and their earlier public raw bytes are retained. Three after-report pairs are
actual outputs at their declared repository-relative input paths, not hand-authored examples.

The two V4 description builds subsequently pass. Independent receiving checks their 67 complete artifacts:
only the two actual build receipts change their question-engine code-hash leaf; the other 65 files and all
3,017 private inputs remain raw-exact. Only those two receipts replace the V3 receipts. Seven feature-review
records distinguish fresh validation from inherited unchanged evidence and disclose source-oracle/prose
authorship. The feature reference registers 346 example files, including seven new corpus result/oracle files;
its input fixtures and historical reports are labelled as such rather than all described as generated outputs.

### Preserve the complete local run and fix guide placement

The integrated offline suite runs all 71 programs in 471.564 seconds: 70 pass and the team-context program
fails its fixed file-count check (98 instead of 97). Six unittest cases are skipped, with three Windows platform
notices and no additional skipped-check notices. All 3,025 public input files remain raw-exact, with no extra
or missing path. The question-engine module, including its 130 tests, passes in this full run.

The added impact explanation belonged outside the byte-pinned example packet. It moves into
[TEAM_CONTEXT_IMPACT.md](TEAM_CONTEXT_IMPACT.md), with relative links and its feature/attempt references updated.
The original 94 evidence files, three packet entry files and cardinality assertion remain; only the already
authorized README link changes. The existing two-test team-context module then passes in 19.034 seconds, with
all 3,025 current files raw-exact. The other 70 programs are not repeated to replace the failed full result.
Current committed-head CI checks the complete suite and optional MCP separately, including their actual skips.
Three fresh Docker starts check the historical compatibility profile; they do not accept a current plant twin
or renew the two stale manual replay stages.

## 135. Keep heating investigations grounded in existing records

The reader's job remains building and maintaining useful context for their own plant. Public case studies
demonstrate the method; reusable tools accept the documented site inputs. This follow-up improves the question
screen and its handoff rather than adding another company record system.

### Separate original prompts from current answers

A fresh reader audit did not establish that the toolkit forces recollection or prevents an answer from existing
records. Six matched context workflows exposed a narrower readout problem: retained screen-time candidate
prompts said the collection request remained open even when the whole question had a later accepted answer.
The report now labels those original candidate facts and states that per-request completion is not tracked there.
All 18 matched JSON outputs remain byte-exact; Markdown differs only in the frozen explanatory sentence.
Question states, source pins, owners and history remain unchanged. The public context-register module passes
53 tests, including the new cross-state regression. These are fictional software dispositions, not accepted
engineering answers or evidence that the supplied records actually settle the investigation.

### Define the heating job before changing its rules

Original DOE/LBNL/EPA source text informs prospective cases for exhaust recovery (E31/H6) and burner operating
basis (E32). The old detectors implement their documented missing-label gates; expanding that job to examine
function, existing coverage and residual basis is a collection-policy improvement, not proof those predicates
were coded incorrectly. One concrete source conflict is repaired: no nearby direct-duct space is not universal
closure when the cited dryer guidance also describes circulating-medium recovery.

Twelve E31/H6 and six E32 cases are frozen before their original baseline calls. The expanded minimum job has
12 missing subject investigations across those observations. Working coverage may reasonably stay quiet in
new-project triage; if displayed, it must be acknowledged without calling for a new retrofit. H6 retains the
named external-duty gate and E32 retains the separate same-unit fuel gate. Product oxygen and foreign-unit
records do not establish combustion basis. Appropriate air/fuel metering, flue analysis or their combination can
inform review; the screen supplies no universal operating setting or new measurement authorization.

The candidate changes only three rule objects. All other 47 rules and all 50 original benefit/source objects
remain exact. E31/E32/H6 retain four/four/three requests, now starting with existing company records and explicit
scope. Eighteen actual candidate calls produce 36 complete reports, 24 findings (22 required subjects and two
optional working-coverage acknowledgments) and four quiet cases. Independent receiving checks the complete
reports, all 108 subject-scoped typed literal rows and the frozen input/method pins without extra product calls.

The portable corpus retains the original 25 function-basis inputs and history and adds 18 heating inputs with a
separate oracle. Its primary oracle retains 77 input literals; ten extra E32 display controls were frozen after
baseline observations but before candidate calls. Of 87 combined inputs, four unrelated/no-anchor values stay
unshown and 83 active values expand to 108 scoped rows. Three after-report pairs are exact copies from those same
18 sessions. These are 43 exposed authored development cases, not 43 plants, independent source families,
held-out model trials or measured engineer usefulness. Source routes disclose that historical PDF byte equivalence
was not established; no original PDF is added. The public guide is intentionally revised while original inputs,
expectations and historical reports remain intact.

The producer audit also identifies a provenance gap for follow-up: description build receipts hash the generator
code but not the selected question catalog. The present comparison separately freezes that catalog and checks
the complete generated bundles; the receipt alone cannot establish which catalog generated their questions.
N104 retains this as a specific future receipt improvement rather than claiming it was fixed here.

### Retain the first integrated producer failure

The first seven of fourteen planned producer invocations succeed as commands. Six comparisons pass, including
all 67 complete description artifacts byte-for-byte. The seventh, the illustrative food screen, produces 31
findings against a prospectively expected 29, so the remaining seven calls are stopped. The two unexpected
subjects are E31/H6 at HX-303: its explicit Native type is `heat_exchanger`, but its name includes "Fryer".
The old missing-recovery predicate incidentally suppressed this false process-equipment anchor. The 18-case
candidate pass did not cover that interaction. The expected 29 food findings, 41 roll-up findings and rejection
exercise are retained; accepting the extra helper subjects would fit the oracle to a failure.

### Repair the role distinction and complete the producing routes

An optional `not_type_text` selector checks only the explicit type. The three heating anchors use a strict
full-string pattern for declared standalone helper roles. Actual dryers with recovery in their names remain
eligible, helpers remain candidate context, and unknown/combined classifications keep the previous name-based
behavior. This is bounded selector policy, not an authenticated plant taxonomy. Before implementation, an
independent regex check found that Python's `$` also accepts a final newline; the shipped expression instead
uses `\Z`. The original proposal/witness remains, with 26 amended vectors and three exact Native controls.

Independent static review accepts the two-line opt-in guard, three anchor fields and one selector-help append.
The other 47 rules, all 50 benefits and remaining catalog content stay exact. The existing 131 test methods and
assertions remain, with the declared selector-key allowance; four methods are added. Their focused execution
passes. Eighteen successor case calls reproduce all 36 earlier reports raw-exact, retaining 108 scoped literal
rows. The three post-food-failure role inputs are separate from the original 43 core development inputs.

Ten successor producer invocations complete their individual checks: food has 29 findings, the roll-up has
41 across 24 questions, and the review exercise retains the same finding IDs while withdrawing rejected
candidates. The food's 20 other findings and roll-up's 21 other question groups remain exact. Two actual
description builds change only the question-engine code-hash leaf in each receipt; their other 65 complete
artifacts remain raw-exact. The four earlier successful screen routes are inherited unchanged. Across the
initial seven and successor ten invocations, 14 unique producing routes are covered with the failed food
observation retained. The aggregate contains 84 freshly produced files and eight inherited files.

The successor's final aggregate wrapper exits one because its copied seven-path allowance omits the two
prospectively allowed description receipts. All ten product invocations and individual comparisons have
already passed. Additive postprocessing checks the retained 92 artifacts and exactly nine declared changed
paths, without another product call or relaxed criterion. Independent receiving confirms that result. Two
inherited metadata labels in the wrapper freeze still name the prior engine/catalog; they remain untouched
and explicitly qualified. The actual consumed files and outer freeze bind the new method/catalog. Seven
ordinary JSON files that differed only in line endings keep their earlier public raw bytes.

### Preserve the full-run failure and correct the remaining legacy expectation

Commit `0884b2b` runs all 71 local programs in 481.100 seconds: 70 pass and the question-engine program fails
one old linked-recovery assertion. Six unittest cases are skipped, with three Windows platform notices and no
additional skipped-check notices. All 3,064 public files remain raw-exact, with no extra or missing path.
Exact-head Linux CI also reports 70/71, with 18 unittest skips and no platform or additional notices; its
benchmark-registry step is skipped after the failure. The separate MCP job records 32 PASS lines, including ten
knowledge sessions, with no skips. None of these results is relabelled as a passing complete suite.

The missed regression still expects a recovery label to silence D-1's E31 investigation. The accepted policy
already retains applicable subjects while asking what existing records establish. The same two-dryer fixture
and CLI now expect both questions and explicitly require HX-1 assets/evidence only for D-1. Independent
policy/static receiving preserves the other 134 methods and the original fixture/invocation. One private
corrected-method test passes; the affected public module then runs 135 tests in 40.981 seconds, passes with
one skip, and leaves all 3,064 inputs raw-exact. Only the test changed before that run; the engine, catalog and
all generated outputs remain exact. The other 70 local programs are not repeated. New committed-version CI
provides the separate complete-suite gate, with its actual skips retained. The follow-up review inherits all
44 opportunity example files and preserves all 195 earlier review records.

## 136. Retain the question rules in the description handoff

An engineer inheriting a description bundle needs its question rules as well as its source, authored model,
drawing and resulting investigations. N104 identified a concrete missing input: the receipt pinned five direct
producer files and generated payloads, but the question engine read a mutable default catalog that the bundle
did not retain. This is a reproducibility gap, not a limit on using the tools for a reader's plant.

### Observe the missing identity before changing the build

Two old native CLI builds use identical source, answer and code, with default catalogs differing only in LF
versus CRLF representation. Both succeed and produce 31 complete files byte-for-byte identical. Both omit the
catalog snapshot and its receipt identity: all four prospective contract assertions are false. The two catalog
hashes differ while their parsed JSON is exact. Independent receiving checks both closed input sets, logs and
whole outputs. This accepts the baseline characterization, not the old provenance contract.

The repair captures one bounded raw catalog before answer inspection or rendering, writes a fixed
`question_catalog.json`, and makes the question subprocess consume that copy explicitly. The receipt records
its relative path, raw SHA-256 and default/custom selection; the complete payload inventory includes the same
raw bytes. The optional keyword-only argument and build-only CLI `--catalog` accept a permitted company copy
in the existing catalog format. `prepare` and `check` remain independent of catalog selection. Original input
filenames and local paths are not added to catalog metadata; the captured content itself is preserved and must
remain in an approved environment.

### Preserve raw evidence and make refusal explicit

The new input has an inclusive 8 MiB limit, acquired through requests no larger than 64 KiB with positive
short-read continuation and cap-plus-one refusal. It requires a finite UTF-8 JSON object without duplicate
properties or a BOM. The unchanged question engine rejects BOM input; the builder refuses it before any
inspection/rendering. Existing source/answer limits and their BOM preservation remain unchanged. A first
private candidate failed static review because acquisition and parse exceptions could expose the original path
or escape the promised `InputError`. The successor translates only that helper's failures to safe literals,
with suppressed exception chaining. Both versions and the static finding remain retained; no candidate was
executed before that correction.

Catalog CRLF bytes are exempt from generated-text folding, just like retained source/answer bytes. Swapping or
removing the upstream after capture does not affect the selected snapshot. A later semantic A-to-B rule change
is visible, while a saved A catalog can replay A's question records under the same engine. Report path captions
follow the existing engine rule: external temporary storage displays basenames; an in-checkout temporary path
can retain a repository-relative prefix. Replay comparisons account only for the declared path labels and the
existing CRLF/hard-break Markdown packaging transforms, not arbitrary cleanup.

Current publication freshness is distinct from historical integrity. The repository's two named default
examples must match today's default catalog as well as their own snapshot/inventory. A catalog-only revision
makes that explicit publication check fail; it does not invalidate a self-consistent historical or custom bundle.
The controls also refuse tampered snapshot identities. None of these hashes establishes authority, source
suitability, company approval or a continuing synchronization service.

### Keep default identity stable across Git checkouts

The default catalog previously had ordinary Git text policy. An isolated Git witness confirms that Windows
checkout could turn it into CRLF while committed raw bundle snapshots retained LF, creating a false freshness
difference. One narrow `/data/questions.json` LF rule now keeps the repository input stable. It does not normalize
company-selected catalogs. The existing checkout test moves that one path from its ordinary controls to its
21 LF targets, retaining the other assertions. A display-only witness wrapper failed after writing its evidence;
the original exit remains and additive receiving verifies the unchanged Git logs and outputs without reruns.

### Rebuild the examples and check the transfer

Two actual successor builds produce 32 assisted and 37 MGPI files. Across the old 67 files, 59 remain raw-exact.
The only changes are the two new raw catalogs and, in each bundle, the question JSON catalog label, Markdown
catalog caption, review instructions and measured build receipt. Whole finding objects, graphs, drawings,
models, layouts, source/answer bytes, review CSVs and platform outputs remain exact. No receipt is restamped.

The 23-method description module and three-method checkout module both pass with zero skips in a separate
staged test workspace. Checkout records 42 indexed and 84 materialization comparisons, with 274 existing raw
packet files retained per configuration. Independent receiving verifies all 69 artifacts and the input guards;
the producer inputs and old 67-file baseline remain untouched. The A/B catalogs are exposed synthetic policy
controls, not new plant sources, model-accuracy runs or measured engineer benefit. Global publication and
committed-version CI are separate gates. No commercial model, company/OT connection or new original-source
download is used in this follow-up.

After the module run, the existing CLI test is strengthened with a filename containing spaces, Unicode and a
backtick, plus checks that the original filename/path are absent from the receipt, question JSON, screen and
review text. The other 22 methods remain exact. That one affected test passes once with no skip in a new
isolated workspace; the original 23-method and three-checkout results are retained and not replayed. This closes
the explicitly named filename dimension without changing the builder or restamping either worked bundle.


## 137. Keep own-plant review and mapping records with the plant packet

Three fresh coding-agent reader/source walks retain the intended payoff: use your own records to build a
sourced draft twin model, review and enrich it, then connect and maintain the useful parts. The README and
tool/tutorial/case distinction already say that. Four case-entry banners now make the same distinction beside
the Ignition quickstart, build record, operator screens and OPEN100 assembly. Their existing bodies and results
remain intact; the own-model route uses reusable generation and tag import rather than the TE gateway builder.

The walk found a real own-input handoff defect. The OPC mapper accepted an external model and I/O CSV but always
wrote its address-bearing Markdown/JSON receipts into the toolkit checkout. Two preserved original-script
calls on fictional inputs show the requested private-directory flag refusing with exit 2, then omitted-flag
application writing two reports into an isolated copied checkout. No company input or public fixture was used
as a mutation target. The contract was written before candidate execution.

The bounded repair adds optional `--record-dir`, consistent with the existing review command. Absolute and
cwd-relative paths select the report folder; omitting it preserves the legacy destination, stem and report
schema. Mapping logic, source locators, partial/replacement rules, stdout, serialization and both prewrite alias
guards remain unchanged. Independent static review recovers the entire original source after removing four
declared replacements. This is output placement, not redaction, permissions or a company records service.

One isolated 33-method mapper run passes with no skips: all 27 original methods remain intact, with six new
methods exercising twelve subprocess cases for chosen private paths, dry-run, invalid plans/targets, aliases
and omitted-versus-explicit default bytes. That last comparison uses the candidate twice; it is not an
old-versus-new runtime comparison. The two original baseline observations and source-equivalence proof are
separate. Independent receiving verifies the saved logs, source pins and unchanged three-file test workspace.
Three additional local integration programs pass; graph export reports one existing case skip. No local full
suite is claimed. Committed-version CI remains a separate gate.

Own-input instructions now carry explicit private review and mapping folders through the working model and
graph handoff. The graph loader reads all JSON review events in its selected directory without checking model
binding: keep an audited model-specific review folder, separate from mapping receipts. Shared item IDs alone
are not a match. The OPC/PI CSV mappers use extracted-twin instrument IDs; authored process-model target fields
remain separately configured. Two source-derived follow-ups retain early Native-input diagnostics (N106) and
review-event model/revision binding (N107); neither has been runtime-reproduced or repaired in this pass.

New untracked default mapping reports are ignored as staging hygiene. Existing tracked historical reports stay
tracked. Reports and stdout still contain addresses and source rows; a gitignore rule is not data protection.
Same-name mapping receipts still overwrite, so choose version folders and retain accepted originals. Known
preflight refusals preserve files, but sequential writes are not atomic or protected against concurrent changes.

Two actual matrix cells refresh the changed guide bindings: own-drawing intake passes; TE recorded fault
comparison retains its failure (18/21 agree, 14/21 detected against reference 17). Other 93 whole cell records
are inherited unchanged; totals stay 64 pass, 23 fail and 8 n/a. Only guide pins, timestamps/durations and
shifted publication line locators change. No model call, new plant corpus, native import, operational approval,
measured reviewer benefit or generalization improvement is inferred from these software/reader checks.

## 138. Explain the Native-model boundary before point mapping

An engineer can generate useful staging from an authored Native process model, but the OPC mapper uses
extracted-twin instrument IDs. The earlier interface exposed that difference as a KeyError rather than a
usable next step. N106 closes this bounded CLI admission gap; it does not add a Native OPC adapter.

Two isolated original calls preserve the baseline: the committed Native model exits 1 with KeyError `id`,
while an ID-based extracted control completes a valid dry-run with exit 0. Inputs and existing private/default
receipt sentinels remain unchanged. These are fictional software controls, not plant connections.

The guard recognizes list-valued units and streams unless metadata explicitly selects extracted_twin.
It runs immediately after JSON loading, before I/O acquisition or mapping. A plain exit 2 diagnostic retains
the model and points to generate.py with an explicit private output folder. It invents no IDs or mappings.
The existing planner, matching, source locators, report routing and serialization remain unchanged.

One private 36-method mapper run passes with zero skips. All 33 earlier test methods remain intact; three
new methods cover Native apply/dry-run, empty/auxiliary-ID shapes and supported extracted-marker/legacy-ID
forms. Independent receiving verifies the logs, source pins and unchanged four-file workspace. No Native
generator is run in this follow-up; its existing staging route is a continuation, not a renewed acceptance.

N107 remains open. Two original graph CLI cases expose foreign-event association through colliding IDs
and preserve genuine earlier history after relocation and renamed current identities. Both calls exit 0;
a future binding repair must reject foreign association without dropping legitimate history. A selected
per-model directory is a documented interim practice, not authenticated model/revision binding.

All ten review/mapping example files are inherited unchanged. No new corpus, model call, engineering
performance, company approval or human benefit is inferred. Current integration and exact-version CI
remain separate release checks.

## 139. Preserve review records before associating their events

A folder and matching item IDs do not establish that a review belongs to the selected model. The original
foreign-event case and genuine earlier-history countercontrol remain retained. The local graph route now
[captures records unbound](REVIEW_HISTORY.md), then attaches only individually supplied associations to exact
model/record bytes. Earlier identifiers, duplicate actions, reviewer fields and unknown content stay intact.
Full and core retain the complete context. A supplied basis is not authenticated ownership or transition proof;
the tool cannot detect a false engineering explanation merely because its hashes match.

The independently received v4 cohort has 13 top-level jobs: 58 unit methods reported, with 57 passed and one
unnamed skip; four no-review outputs match the original raw bytes; six full/core outputs match frozen independent
data oracles; and real 8 MiB/plus-one records verify complete capture and refusal with an unchanged sentinel.
The unnamed skip is not counted as an executed filesystem branch. No original baseline was rerun to refresh it.

The first example-creation attempt stopped because its private workspace omitted dynamically loaded confidence.py.
That harness failure remains preserved. The corrected A2 creation passed, but its model included raw fingerprints
of four CRLF working-code files. Four narrow repository LF pins make those source bytes match Git across checkouts;
they change no code AST or company data. Portable A3 completes seven creation calls and separately refuses the old
A2 manifest against its changed model bytes without replacing output. Five older non-graph files, including both dated records,
remain raw-exact; only the qualified graph and its supplied illustrative association are new example artifacts.

The adopted README then reproduces seven retained files through eight commands in the unfiltered nine-method
report module. It and the three checkout methods pass all 12 tests without skips. Checkout checks cover 25 targets,
50 indexed and 100 checkout comparisons, retaining 275 existing raw-packet files per configuration. Two actual
description builds retain all 67 other complete artifacts; only their two actual graph-producer receipt hashes change.
These are local software checks, not a new corpus, model result, plant acceptance or measured engineering benefit.

N107 is closed only for unbound custody and supplied-association admission. Automatic writer lineage, authenticated
company source/reviewer authority and continuing organizational ownership remain external. The 30 remaining question
source reviews, 23 matrix failures, five historical prediction gaps and unrun human/company acceptance remain open.
Whole-repository integration and exact-head CI are separate release checks.


## 140. Make generated intake JSON portable without normalizing originals

Exact Linux CI at `3100959` failed: 70 of 71 programs passed, and the nine-method report module stopped in its
README graph step because the supplied association did not match the rebuilt model's raw hash. All five
registry suites were skipped after that failure. The earlier local A3 success and its "portable" wording do
not establish cross-platform reproduction; the failed run and its logs remain retained.

Four LF-pinned code inputs were insufficient. The intake writer still emitted platform-default newlines, and
the committed intake manifest had different raw checkout bytes. New intake JSON now uses explicit LF; only
that public example manifest gains a narrow LF checkout rule. Original source bytes are still copied and
fingerprinted exactly. The review command still preserves its supplied model's formatting, and association
checks still require exact captured model/record bytes. No company input is silently normalized.

The extended real-CLI regression first fails once against the original Windows importer on generated CRLF.
The corrected unfiltered intake and checkout modules then pass all 18 plus 3 methods without skips. They check
three exact LF JSON outputs, unchanged originals including Unicode/control-containing CRLF extraction data,
and 26 checkout targets: 52 indexed and 104 materialization comparisons, with 275 raw-packet files retained per
configuration. These are actual software controls, not observations of Linux output or plant data.

Genuine A4 creation completes seven commands and separately refuses the retained A3 association, leaving an
existing sentinel unchanged. Model, normalized source-record and intake metadata differ from A3 only in
`importer_sha256` and `manifest_sha256`. The three generated JSON files are LF; copied originals equal the
actual selected inputs. Five older non-graph files, including both dated records, remain raw-exact. A fresh
individual supplied manifest binds the actual new model; the graph retains the four original qualified events.
All 22 frozen source/input files and 3,071 public file hashes remain unchanged during this producer run.

A separate private-overlay run of the unfiltered nine-method report module passes without skips. Its README
recipe reproduces all seven retained files through eight commands. Five actual matrix CLI runs refresh 42
selected cells; the other 53 whole records remain exact. All 95 cells retain their prior status and metrics:
64 pass, 23 fail and 8 n/a. This is a producer/source-binding refresh, not new corpus or model performance.

Corrected exact-head Linux CI remains a separate gate; the retained failed Linux run is not upgraded by these
local results. No native connection, company approval or measured engineering benefit is claimed.

## 141. Investigate combustion and drum control from service and existing records

An oxygen label does not establish flue-analysis or active trim; a boiler name does not establish a steam-water
drum or require three-element control. Source review of E16/C5 now starts with applicable heat/water service,
existing operating and function records, and the owner of unresolved evidence. Missing fuel records stay
unknown rather than becoming evidence of an unfired unit. Explicit electric/unfired service does not create
compulsory combustion work; an unfired waste-heat boiler can still need drum-level record review.

The [combustion-control tutorial and retained cases](../examples/opportunity-screen/combustion-control-basis/README.md)
show how to substitute the reader's own supported model and take findings, source revisions, uncertainty and
next-owner requests into the company's existing context system. S19's historical boiler figures are not trim
hardware or drum-control upgrade savings. The two rules remove those inapplicable numeric presentations;
DOE's steam sourcebook (S8) supplies the water-level function/applicability basis, and the process-heating tip
(S27) supports alternative air/fuel metering or flue-analysis records. S24 supports the assessment category,
not newly verified exact statistics. The [source map](../examples/opportunity-screen/combustion-control-basis/SOURCES.json)
keeps canonical document locators and raw-byte verification limits explicit.

All 40 original and 40 candidate JSON/Markdown reports remain raw-exact in the cohort. Ten paired fictional
models were authored in stages (six, then two applicability cases, then unfired and unknown-fuel cases); eight
selector controls are separate. Independent candidate receiving checks 197 scoped typed literal rows and
19 E16/17 C5 acknowledgements. These are exposed development controls, not 20 plants or held-out performance.
Supplied false, null, unknown and qualified function claims remain candidates, not accepted installed facts.
Four focused regression methods first fail on the original catalog with 33 assertion/subtest failures and
zero errors, then pass on the candidate with zero skips. One original caller CLI exit 2 and a zero-child
preflight stop remain preserved separately from the intended baseline reports.

Seven affected producer routes retain 79 complete artifacts: 72 raw-exact, three exact whole CRLF-to-LF
canonical JSON comparisons and four actual description catalog/build-receipt updates. The first OPEN100
comparison failure omitted the lazily read I/O-description CSV from its private caller closure; that failed
attempt remains retained. The corrected closure succeeds without repeating the already successful TE/Bayer
routes. These are source-binding refreshes, not new model or corpus-performance results.

The unfiltered question module reports 139 tests: 138 passed, one unnamed skip and zero failures. The checkout
module passes three methods without skips, with 56 indexed and 112 materialization comparisons and 275 existing
raw-packet files retained per configuration. All 3,177 public file hashes and the path set remain unchanged
during these local runs. The skip is not counted as an executed branch; full-repository integration and
exact-head CI remain separate gates. No new MCP runtime, plant connection or human-usefulness trial is claimed.

The engine, other 48 whole question objects and all source objects remain unchanged. The catalog now has
50 rules and 126 collection requests; 22 rules have bounded source-informed collection reviews and 28 still
await original-source adequacy review. Existing function records can be acknowledged without a mandatory
project. Company decisions, approval, installed-state verification and continuing ownership remain external.

## 142. Keep question signal descriptions with explicit source bytes

The original six CLI controls retain a real reader failure: a legacy mapping could silently borrow unrelated
prose from a same-basename checkout CSV, while current physical-line mappings lost optional descriptions.
Addresses remained supplied claims; an absent synthetic label never established real plant data. This was
description/location context, not a demonstrated change in finding eligibility or installed signal identity.

The [own-input tutorial](../examples/opportunity-screen/mapping-descriptions/README.md) now selects retained CSVs
with repeatable `--io-list`. Modern records match raw source bytes, physical spans and the corresponding
identity/address row, including renamed byte-identical files. Explicit legacy row associations remain
`unverified_legacy`; a same-address supplied revision cannot authenticate its historical identity. Wrong or
unselected context stays `unavailable`, and all mapped-signal captions say signal identity unverified. Selected
source qualifications stay with each finding through full/core graph and context semantic readback; the original
mapping source is retained. Complete top-level source context remains readable even when no question fires.

Root-run candidate evidence has 16 CLI calls and 137 checks. Eight new focused methods pass without skips,
including actual mapper-produced multiline evidence and source-status retention in graph/context. The context
module passes 53 methods without skips. Three checkout methods pass without skips, retaining 56 indexed/112
materialization comparisons and 277 raw-packet files per configuration; two synthetic BOM/CRLF CSVs have narrow
raw-byte checkout protection. The other 138 original question methods remain AST-identical; one old ambient-I/O
alias test intentionally becomes explicit selected-input protection. Current OPEN100 reproduction selects its
committed synthetic source; old model mappings do not receive invented historical hashes.

The candidate contract was frozen with original baseline observations exposed. A final written independent
static seal followed the root candidate run; it is post-run source review, not a retroactive pre-call gate.
Private helper/closure stops remain separate from actual product failures.

Three actual producer calls succeed with 71 retained artifacts: two OPEN100 reports and 69 description-bundle
artifacts. All 67 non-receipt description artifacts remain raw-exact; each of two actual build receipts changes
only its engine identity leaf. Root adopts these four current files. The subsequent unfiltered question module
reports 147 tests: 146 passed, one unnamed skip and zero failures; the skip is not an executed branch.
Independent actual controls pass 61 checks without skips: five own-seed screens, a blank legacy-row negative,
full/core carrier readback and selected-source hardlink refusal. A real retained-answer prepare/apply/refresh
sequence becomes stale on a change to only the selected source's raw fingerprint; model, address, description,
association status, byte count and backing record stay unchanged, with decision/owner history preserved. This
is fictional software behavior, not an authenticated company source or accepted engineering answer.
Separate independent docs/test/tutorial receiving passes 175 checks and excludes that receiver's own producer
outputs. Independent producer receiving verifies all 71 complete artifacts, including 29 unchanged ordered
OPEN100 finding IDs, 24 qualified legacy records with actual selected CSV identity, 67 raw-exact description
files and two actual engine-leaf receipt updates. Its 717 checks are receiving controls, not performance.
The root's 16-call candidate evidence is separately independently received without reruns. N108 closes only
for selected-source context and semantic freshness; full-repository integration and exact-head CI remain
separate gates.

Five small exposed fictional tutorial/input files add no plants, held-out model trial or performance result.
The catalog remains unchanged: 50 rules, 126 requests, 22 bounded source reviews and 28 remaining. Engineering
interpretation, authorized source revisions, signal checks and ongoing company ownership remain external.

## 143. Index retained I/O rows without changing source meaning

Repeated row scans made question-source lookup revisit the same captured CSV for each mapped asset. Parser-owned
physical-span and logical-row indexes now retain references to the original records; source selection, row
identity/address checks, ambiguity and supplied/unverified qualifications stay unchanged. Captured contexts are
read-only: reload to refresh. Plain dictionaries retain their scan fallback and selected-source collection
lookup remains O(S). Additional O(N) index memory was not measured.

The [generated-input diagnostic](../examples/opportunity-screen/mapping-descriptions/lookup-scaling/README.md)
retains original/indexed capture-plus-lookup visits of 1,056→64, 16,512→256 and 262,656→1,024 for 32/128/512
fictional records, plus 24,832→448 for a separate 128-record/two-source mixed case. All 28 production artifacts
remain raw-exact, with the same one/two source reads. The original four, corrected four and candidate four are
12 Model API runs, not CLI/model trials. The first counter overcounted a multiline append twice per record;
the corrected C-call hook retained all functional outputs. Independent measurement receiving and separately
frozen 10-seed/84-check controls confirm the bounded work and unchanged semantic behavior.

Two focused regressions fail on the old method with three assertion events and no errors, then both pass on
the indexed method. All 147 earlier methods remain AST-identical. The full module reports 149 tests: 148 passed
and one unnamed skip, not an executed branch. Independent receiving verifies three actual producers: OPEN100's
two files and 67 description artifacts remain raw-exact; two actual build receipts change only the engine leaf.

The portable public harness subsequently passes two CLI invocations/eight additional Model calls. Both methods
reproduce 14 generated-input pins, 28 complete artifacts and all four count rows exactly. Independent receiving
confirms the replay and public protocol. N109 closes bounded record lookup; full integration and exact-head CI
remain separate gates. The three new public files replace no history and commit no large CSV fixtures.

This is instrumented software work, not elapsed-time speed, memory, engineering usefulness, new model results
or supported company capacity. The catalog remains unchanged: 50 rules/126 requests, 22 bounded source reviews
and 28 remaining. An index does not strengthen source authority, historical identity or installed signal truth.

## 144. Carry a source question through review and MCP readback

The own-record reader walk joined the question screen, retained answers and selected MCP access. Its first
relocated-schedule call correctly refused stale source choices: copying the schedules changed their displayed
file identities. An optional top-level `source_label` now lets a working copy preserve its supplied logical
identity. It is not a path to open, an authority claim or permission to reuse changed rows. Actual input paths
remain protected; duplicate labels and stale choices refuse. Default source labels and complete outputs remain
unchanged. Literal Unicode and Markdown punctuation survive field locations and saved-screen rollup.

Independent controls pass 48 checks in eight groups. The unfiltered question module runs 153 tests: 152 pass
and one unnamed test is skipped. All 149 earlier methods remain AST-identical. Three actual normal producers
retain 69 artifacts byte-for-byte; the two actual description build receipts change only the engine identity.

The final public-input/fictional-note exercise completes ten CLI steps with 22 checks. H1/C3 select four findings,
including two unmapped H1 findings. Seven mapping-source carriers retain their qualifications. Changing only
the selected CSV fingerprint in those questions makes the accepted partial H1 answer stale and its current
state unanswered; both decisions and both ownership records remain intact. C3 and the other H1 findings stay
unanswered. A valve-position description never becomes evidence of steam flow.

Three actual SDK stdio sessions make 50 tool calls, retaining complete response envelopes. Readback stays at A
after the selected files are replaced; restart loads B with its stale answer and unchanged history. Graph-only
access retains questions but cannot supply the full register. A mismatched graph/context startup refuses with
exit 2 and empty stdout. No MCP network listener or plant connection is configured for this route. These are
local software checks, not company Copilot, IT/OT, reviewer authority or engineering acceptance.

Earlier observations remain retained: the original relocation refusal, a ten-command intermediate run followed
by a checker error that wrongly assumed only two findings, and an independent caller's incorrect module-root
binding. The final cohort keeps all four findings. N110 closes this bounded portability and reader handoff;
the [own-record tutorial](../examples/opportunity-screen/mapping-descriptions/retained-answer/README.md) explains
the transferable method. Company systems still own maintained records, permissions and release decisions.

## 145. Review valve feedback from existing records

C3 already warned that drawings can omit fitted positioners. Its generic Z-tag suppression nevertheless hid
unresolved valves, while its requests offered a new manual step test and its decision prioritized added feedback.
Independent primary-source review confirms S13's quoted pumping-variability context, but not those blanket actions.
S29–S32 add scoped vendor examples for command/local/returned feedback, endpoint indication and existing diagnostics.
The [tutorial](../examples/opportunity-screen/valve-feedback-basis/README.md) teaches an own-model valve/loop map:
existing source and declared function, uncertainty, and the next record recipient. Company systems own the result.

Six paired fictional models and two separate eligibility controls were pinned before original calls. Eight
original screens match the old predicate but retain only four of ten mandatory source-review occurrences.
Eight matched candidate screens retain all ten and acknowledge two optional working cases; both eligibility
controls stay quiet. All 189 core typed inputs and 36 controller qualifiers survive JSON and decoded Markdown.
Foreign/unknown targets and null/false/zero remain supplied, unverified context. Both per-anchor record reviews
stay open. More findings are not a performance gain, unique diagnosis or engineering acceptance.

The [complete reports and provenance](../examples/opportunity-screen/valve-feedback-basis/history/PROVENANCE.json)
retain the first candidate worker's three successful calls and its external grader failure: it misclassified
the preserved string "unknown" as present rather than the existing blank placeholder state. A saved-data regrade
and five uncalled cases complete the cohort without repeating those three calls or changing the method/oracle.
Other 49 whole rules and all shared sources remain exact. Seven actual producers retain 79 artifacts; 17 actual
files change, including the assisted description's C3 questions/graph and both default catalog snapshots/receipts.
All non-C3 questions and their Markdown blocks remain exact; historical catalogs/decisions are not refreshed.

Three focused methods produce eight assertion events on the old catalog, with no errors, then all three pass.
The first full 156-method run finds one old guard false positive: the newly shown LIC-102 setpoint 50% is supplied
in the unchanged Bayer model. A test-only provenance check now permits only that exact declared token on its
matching controller evidence line; seven negatives still reject altered/unsupported values or references.
The successor full module reports 155 passed and one unnamed skip; 152 earlier methods and all three new methods
remain AST-identical. Checkout controls pass three methods, 60 indexed/120 materialization target comparisons and
277 existing raw-packet files per configuration. All 48 new case files were already LF; one narrow Git policy
preserves their recorded identities, without normalization or global configuration changes. Captured screens
retain their intentional Markdown hardbreaks through two narrowly scoped whitespace attributes.

Original preparation/receiver/observer stops remain separately recorded. N111 closes this bounded source/software
repair, not source authentication, installed-state verification, company acceptance or measured engineer benefit.
The catalog remains 50 rules/126 requests: 23 bounded source-informed collection reviews and 27 still awaiting
original-source adequacy review. Full repository and exact-head CI remain separate integration gates.

## 146. Recapture the whole-graph MCP sample after a source-policy change

The C3 refresh changed the questions attached to the selected Bayer graph while its P-1 asset stayed exact.
Our dependency audit missed the committed sample's scalar fingerprint of that entire graph. Review CI at
`c2bbe0b` caught it in both jobs: 70 of 71 test programs passed, the saved benchmark step was skipped, and the
MCP job printed 27 PASS lines before its final strict sample comparison failed. Two later reader recipes were
skipped. That run remains failed; earlier local success did not establish complete integration.

The default checker still compares the complete committed response, excluding only load time. A separate
explicit [capture command](../examples/internal-mcp/README.md) now runs its one actual SDK stdio exercise and
refuses an existing destination. Independent prospective criteria allow only `snapshot_sha256` and `loaded_at`
to change. The approved SDK 2.3.0 session makes 15 tool calls, one tool listing and one resource read, with six
expected negative tool responses. Full parsed SDK envelopes and the actual generated graph bytes are retained;
the returned fingerprint equals their raw SHA-256. The complete P-1 node, claims, source/status and wrapper
remain exact, including text/structured equality. No in-memory substitute or manually stamped hash is used.

The [actual response provenance](../examples/internal-mcp/sample_provenance.json) records the current model,
questions, recipe and limits. A narrow LF policy preserves the actual response bytes through checkout; company
source originals are not normalized. The unfiltered snapshot module passes 19 tests and checkout passes 3,
with no skips: 62 indexed and 124 materialization target comparisons retain 277 existing raw-packet files per
configuration. All 3,235 public paths and raw files remain unchanged during these two module calls. Mocked
capture-routing/refusal tests are distinct from the actual SDK evidence. The preparation-only SDK source-path
stop is preserved; no capture was repeated. Full repository tests and successor exact-head CI remain separate.

The reader follow-up also distinguishes reusable tools from the Bayer/Tennessee Eastman case records, clarifies
absolute drawing-folder inputs, and separates generic generated tag imports from the demo's provider choice.
These are source/readability corrections, not new runtime, transfer accuracy or usefulness measurements.

A298/N112 closes this bounded sample dependency repair. Load time is not source acquisition time; no source
authentication, company Copilot/IT/OT acceptance, operating permission or measured engineer benefit is claimed.

## 147. Keep typed evidence changes from inheriting an old answer

An accepted answer could remain current after a model or candidate field changed from `false` to `0`.
The evidence fingerprint changed, but refresh compared nested values with Python equality. The same mismatch
affected `true`/`1`, `1`/`1.0` and signed zero, and could admit inconsistent current/context views at readback.
Three comparisons now reuse the existing canonical JSON binding. This is no new numeric or unit interpretation.

The original and matched candidate protocols each make 14 context CLI calls. Four affected answers now reopen,
both bad-pair controls receive specific validator/readback refusals, complete histories stay intact, and 23
positive files remain byte-identical. Benign key order/status, unrelated changes, stale-CSV refusal and exact
reversion keep their existing behavior. Six permanent methods fail the old method with six assertions/no errors
and all six pass the repair.

The [fictional example](../examples/context-register/typed-evidence/README.md) retains original failures and a
documented default reproducer. Its separate actual run makes 14 child CLI calls, with seven complete typed
readbacks and four specific bad-pair refusals. The new integration test separately replays those 14 child calls.
The public modules pass 59 context, 19 snapshot, 2 team-context, 7 context-example and 3 checkout methods: 90
tests without skips. Checkout records 66 indexed/132 materialization comparisons and 287 raw-packet files per
configuration. Independent receiving retains complete inputs, outputs, diagnostics and source guards.

A299/N113 closes this local correctness repair. N114 keeps the unplaced-DEXPI question/handoff route open;
N115 separately records unmeasured latest-answer grouping work. The current N082 count is corrected to 23
bounded source-reviewed rules and 27 remaining; earlier attempt records stay unchanged. No catalog, benchmark
or matrix result changes. Full repository and exact-head CI remain separate, as do company/source authority,
plant truth, operating permission and measured engineer usefulness.

## 148. Carry known unplaced roles into a useful engineering handoff

A reader should be able to start a useful investigation from a known valve before its owning equipment is
established. The public I04 reader model already preserved instrument/final-element roles and a logical
FT-04/FIC-04/FV-04 chain, but the question engine refused it because it lacked placed units and instruments.
The [worked handoff](../examples/graph-export/unplaced-dexpi/question-handoff/README.md) now connects that
supported partial model to a C3 records investigation, a fictional partial answer and retained revision history.

The new Native unresolved-placement route preserves exact identities, selected source qualifiers, assigned-tag
basis and explicit controller endpoints. Unknown ownership stays unknown. Missing, incompatible or duplicate
references refuse before replacing reports; rejected records are not recreated through loop lists. An explicit
unknown role is not promoted from valve-like spelling. Supplemental CSV controllers need authoring/review in
the source model before graph/context handoff. Ordinary placed Native and extracted-twin contracts retain
their existing behavior. The separate public C03 diagnostic now supports C3 for ESV-3712 without inventing
a controller or owning equipment; this does not broaden platform-generator eligibility.

The permanent regression extension contains four methods covering admission, exact relationships, loop-list
controls and answer freshness/history. An earlier matched original/candidate exercise retained the failures;
the canonical-LF public module reports 160 tests with one unnamed skip and no failures or errors.
Checkout checks pass three methods. Canonical LF applies to the two derived model files; the original CRLF
failed input is retained separately, and original source-document hashes keep their byte-exact meaning.

The documented tutorial replay makes six CLI calls and three pure Snapshot pair readbacks. A partial answer
is current on A; separate source and model revisions reopen it as stale/unanswered while retaining complete
decision and ownership history. Model B is an authored fork that changes its declared path and tag basis;
it is not a one-field causal control. Same-path freshness controls are separate regression evidence. The
published 25 selected artifacts are exact copies of the earlier accepted run. Updated presentation metadata
preserves that run's original README and provenance rather than claiming it consumed the later reader guide.

Seven normal producers regenerate the four legacy screens, their food/Bayer rollup and two description
bundles. Of 79 compared artifacts, 77 remain byte-identical; the two actual build receipts change only their
question-engine code hash. The first public description check correctly fails those two stale receipts;
after adopting the actual regenerated receipts, all 23 description tests pass. No receipt is hand-stamped.

A300/N114 closes this local question/handoff gap. The reader guides distinguish reusable tools, substitution
tutorials and public case evidence; an archive-planning page now scopes its clean-drawing assumptions to the
early OPEN100 reference. Catalog rules, original workflow criteria, saved model results and pipeline records
are unchanged. These exposed public/fictional software exercises establish no new plant accuracy, measured
human benefit, authenticated company review or operating acceptance. Full repository and exact-head CI remain
separate integration checks; the company retains source authority, access and continuing ownership.
## 149. Group retained answers after incoming revisions

A four-question fictional packet with three latest answers supplied twelve records to the same latest-answer
sort because current construction repeated it for every question. The repair groups the final latest records
once by exact question ID, after incoming rows. It preserves lexical order, revised-answer references, removed
and owner-only questions, and complete decision and ownership history.

Three additive guards retain the original two semantic passes and the sort-bound failure (12 against a limit
of 3). The grouped method passes all 62 context tests without skips; all 59 prior method ASTs are unchanged.
Existing context-example tests report seven methods with one named optional original-cache skip, while
snapshot (19), pump-revision (2) and team-context (2) pass. The [small structured record](../examples/context-register/grouping-observations.json)
binds actual local results and source hashes. The initial private observer calibration failure is preserved;
its nested site-key collision was repaired before the separately scoped maintainer comparison.

A301/N115 closes this local implementation issue. The public guards reproduce the bounded sort regression,
not every private work-accounting profile. Temporary grouping allocations and unchanged validation, copying
and serialization costs remain. Historical captures/reviews are not rehashed and no fresh normal producer or
SDK sample is claimed. Source counts do not establish timing, memory, human benefit or plant/company capacity;
full repository integration, exact-head CI and independent receiving remain separate gates.

## 150. Review alarm records in their operator and source scope

C8's generic journal request did not retain the supplied record availability, definitions, periods and operator
responsibility needed for a scoped review. The revised question starts with existing philosophy/register,
response and journal/performance records. Shared coverage may be reused; matching labels in foreign site/source
scopes remain unverified. No rate, alarm quality, ownership or compliance verdict is calculated.

The [alarm-record cases](../examples/opportunity-screen/alarm-basis/README.md) retain nine fictional development
models and eighteen fresh complete reports. All 254 typed carrier-field values remain visible, exercising 41
of 50 optional names. Source review is bounded to C8: 24 rules now have collection reviews and 26 remain.
Historical HSE targets stay investigation context; the vocabulary and collection policy are authored, not a
prescribed company schema or proof that supplied approval fields are valid.

Eight closing phrases now explicitly close only the screening investigation; E1 and H5 were clarified in a
separate two-leaf successor after the first six. A final eight-route actual refresh preserves six outputs raw
and changes ten only by the two declared phrase substitutions. Finding IDs, references and benefits remain
unchanged. This adds no source-rule adequacy claim. The Bayer context refresh adds no answer: both prior proposals remain, while changed question content
reopens the current E18 investigation as unanswered/stale, with no owner assigned. Its earlier interpretation is
not declared wrong by that wording change; the old CSV fingerprint remains historical and refuses reuse.

The local question module reports 163 methods: 162 pass and one Windows symlink-privilege case skips, including
all three alarm methods passing. Checkout three pass after stale inventory-count literals are corrected; earlier
failed envelopes/logs are retained. A302 records these finite checks, not operator performance, human usefulness
or plant/company acceptance. Historical catalogs, decisions and all prior reviews remain. Full repository,
pending actual MCP evidence and exact-head CI are separate gates.

## 151. Review compressor recycle from existing records and applicable duty

E6's earlier fixed-month export, generic margin and turndown/upset closure could bypass the actual machine,
service and record basis. The revised question starts with existing records and keeps compressor/valve
identity, source revision, duty and coverage unresolved where supplied claims cannot settle them. Controller
output, actual travel and measured flow remain distinct; nameplate or one sibling trace cannot establish
representative real input power for every machine. Suitable reviewed shared records can be reused.

The [compressor-record tutorial](../examples/opportunity-screen/compressor-recycle-basis/README.md) explains the
own-supported-model route and next process, controls, machinery or record owner. Its [source map](../examples/opportunity-screen/compressor-recycle-basis/SOURCES.json)
separates the DOE/CAC compressed-air guidance from authored collection controls and process-gas applicability.
The screen neither orders a new export/test nor authorizes operation, protection/settings changes or a project.

Three separate cohorts retain 15 original, 15 private-candidate and 15 fresh public-path CLI calls. Each has
18 E6 findings and two quiet cases. The original omits all 24 supplied whole fields from its question-facing
projection; the repair retains all 24 (22 present, two blank) as decoded JSON and readable evidence across
60 subject/field vectors. Fourteen authored record IDs occur in 20 references, including one list shared by
two subjects. These are 15 fictional models, not plants or independent reports. The 80-file packet preserves
30 original and 30 fresh current reports, input models, oracles and post-run metadata without relabelling old captures.

All 18 non-E6 findings in the paired cases remain typed-exact. A separate normal TE regeneration changes
only E6: nine other findings and all IDs remain, and Markdown outside E6 is raw-exact. Static preread caught
a non-scalar prose shape and unconditional shared-scope wording before any candidate calls; the corrected
scalar/shared-scope successor preserves the source criteria, other 49 rules, benefits and shared sources.

The unfiltered local question module runs 164 tests: 163 pass, one unnamed skip, no failures or errors; all
163 prior method ASTs remain unchanged. The new method checks all 15 complete after pairs and typed contexts.
Checkout three pass with 84 indexed and 168 checkout comparisons, retaining 348 raw-packet files per
configuration and the negative text-filter control. Source guards complete before three publication metadata
successors are adopted; original history and all 77 other packet files remain unchanged.

A303 brings N082 to 25 bounded rule reviews and 25 pending within 50 rules/126 requests; N082 stays open.
These are source-informed collection/software checks, not machine protection acceptance, source authentication,
plant or extraction accuracy, measured human usefulness or company approval. Broader freshness, full-repository
integration and exact-head CI remain separate gates.

## 152. Keep stdlib-only tests honest about drawing dependencies

The original standard-library-only run passed 54 of 55 programs and retained one `PIL` import error.
`test_generate_any_model.py` included real PNG drawing and a direct renderer call, so its stdlib-only label
was wrong. It now belongs to full mode, with all 17 drawing test methods unchanged. The full unique set
still contains 71 programs; source-only selects 54 and explicitly excludes dependency-bearing tests.
Full prerequisites now check Pillow before launching children; source-only does not discover dependencies.

The targeted stdlib runner controls pass 19 tests; the drawing module passes all 17 with installed Pillow,
without skips. Three new controls exercise missing-Pillow refusal, source-only independence and full dispatch
exactly once; the earlier 16 runner-control methods remain. The first failure is preserved, and renderer
code and published artifacts are unchanged. The corrected source-only run passes 54 of 54 programs with 22 unittest case skips, three platform
notices and no additional skipped-check notices; all 3,420 watched files stay unchanged. The platform
notices explain case skips and are not added to that count. This narrower result is not a full-suite pass.
Mode-specific results and normal exact-head full CI are separate evidence scopes.

## 153. Bind a frozen model review before scoring supplied labels

The MGPI false-shutdown artifact can still pass the selected-field `native-facts-v1` scorer; that documented
boundary remains. Fixed claim labels already existed, but a reviewer result was not bound to every supplied
model value and its approved claim/source context. The contributor [frozen-model review](../benchmarks/source-support/artifact-values/README.md)
now binds that explicitly reviewed scope before the unchanged `claim-judgments-v1` scorer. It does not discover
claims or grade arbitrary generated models. The manual interpretation-review CSV remains the engineer route.

The two exposed artifacts retain 82 scalar/empty-container entries, 55 provided rows and 14 reviewed groups
each. Roles distinguish source qualifiers, aliases, intent and unknowns; 55 rows are not 55 atomic engineering
claims. Twenty-seven admission vectors contain two valid cases and 25 refusals, including omitted scope,
typed changes, stale source and altered approved context. The historical CSB key contradicts the false
artifact's automatic-shutdown group. A reviewer may correctly label all 14 while that contradiction remains;
citations and nonempty reasons do not establish source support or reason quality.

Six normal public-root CLI scores produce twelve actual reports. Five legacy suites preserve all task
counts, metrics, diagnostics, statuses and attempted sets; only prederived implementation/comparison IDs and
summary order change. Old report pairs and ten versioned snapshots remain. The new report contains fourteen
synthetic reviewer controls: thirteen scored and one invalid-answer/empty-score. The normal six-entry registry
check passes. Independent receiving checks publication and focused tests: four stdlib programs report 63
tests, 62 passed and one unnamed benchmark skip. The original zero-skip observer hold remains; only the
uncalled fourth program resumed. Earlier table-observer failures also remain separate evidence.

A305/N116 closes this bounded evaluation addition. The helper is support, not a new tool or task family.
Source/key review and declared exclusions remain substantive judgments; no current plant truth, authority,
general generator accuracy or human benefit follows. Source-only mode (55 programs), the full suite (72 programs) and exact-head CI
remain separate, unrun integration gates at this entry; old review rows are not rehashed into new acceptance.

## 154. Connect recorded phase calculations to the twin before adding a simulator

2026-11-02. A public post about Pow.Bio's Cassandra/K-log prompted an investigation of quantitative analysis
beside engineering context. The post and its linked race-car model were inspected; the video/runtime were not.
The [analytics guide](PROCESS_ANALYTICS.md) preserves the primary links, attributed claims and adoption boundary.
No linked program was copied and no runtime, dependency, live connector or control interface was added.

The first inventory already found asset models, supplied OPC/PI mappings, historian bands, measured impact and
source-linked questions. The user challenged an unnecessary kinetics prerequisite: those existing pieces should
be used for observed-data jobs. Kinetics or a suitable identified model is conditional on the actual prediction.
The question catalog currently does not determine arbitrary analysis readiness; a plain job-specific brief is
the honest route rather than a claim of automatic kinetics-gap detection.

Kept one bounded addition, `batch_analysis.py`: an elapsed-time batch CSV plus supplied nonoverlapping phase
windows and units produce source-bound summaries and rate integrals with per-signal observed-time coverage.
Optional selection of an existing portable graph resolves exact equipment/instrument IDs and retains its hash
and record statuses. It does not verify installed mappings, units against graph claims or physical relationships.
All supplied originals are read as data; reports do not mutate the graph, working model, context or MCP snapshot.

The [acceptance cases](../examples/batch-analysis/ACCEPTANCE.md) were authored before implementation.
Fourteen stdlib regression methods pass: analytical rectangles/triangles and W/kW conversion, missing/bad/long-gap
observations, separate batches and phases, graph refusals, invalid CLI inputs, exact reports and source/output
preservation. The fictional tutorial has three batches/four windows: feed totals 0.5, 3.5, 2 and unknown kg;
all windows record approximately 1 kWh. The first 13-method run failed two strict floating-point equalities:
1,000 W for an hour computed 0.9999999999999999 kWh. The assertions now allow ordinary floating-point tolerance;
the numerical code and retained report value were not changed to hide that representation difference.

A navigation addition to the existing historian guide correctly made its bound TE matrix cell stale. Removed
only that new navigation paragraph, preserving the historical guide's exact source text and the original matrix;
the documentation index and new canonical analytics guide provide navigation instead. No detector, baseline,
answer key or historical performance result was changed or rerun.

A306 records this addition. New examples remain independently unreviewed; no real fermentation/campaign corpus,
predictive benefit, operator review or plant acceptance is established. The source-only integration suite then
passed 56/56 programs, zero failures, eight skipped unittest cases and three explanatory platform notices.
All 3,587 source files remained byte-identical during that run. Its corpus check verified all 95 locally
available bindings after the historian guide was restored; this did not rerun models or establish new performance.
Subsequent edits only relocate the status note and record these outcomes in the journal/ledger. Full/SDK CI and
independent feature review remain unrun for this local change.

## 155. Qualify recorded data before adding more analysis

2026-11-02. Follow-up to A306 after the user requested continuing gap repairs and the earlier evidence/handoff
gaps. A pre-implementation protocol and retained A306 outputs distinguish an unsupported V2 profile from a
failure of the original strict V1 contract. The new exact signal profile selects linear or previous-value
interpolation and an exact-token external quality filter. Missing choices refuse. Numeric data rejected by its
quality policy never becomes a spanning interval or complete total. All original V1 result fields are retained;
only the implementation fingerprint changes and its Markdown remains byte-identical.

A307 adds exposed quality/interpolation controls: identical 2,6,6 kg/h samples produce 4 kg with previous-value
hold and 5 kg with linear interpolation. A numeric 99 with FAULT quality excludes both adjacent intervals.
Independent source/code and stress review found no blocking core numerical issue. An important source-driven
qualification supersedes an early V2 draft: null quality does not assert that someone prefiltered the series.
It says no external quality filter is selected and quality is unchecked. The legacy JSON `good_samples` field
means admitted numeric samples; the V2 table calls them Accepted. The old draft and observer float-equality hold
remain private records. V1 compatibility and the new qualification controls pass without changing arithmetic.

A308 adds [one measured batch-distillation record](../examples/batch-analysis/public-distillation/README.md),
Arweiler et al., Zenodo version 1.1.3, CC BY 4.0. Original selected CSV/context records retain exact publisher
bytes. The independent key was calculated and separately checked before the toolkit ran. The supplied Operation
partition has 3,512 one-second observations over 3,511 seconds; FT703 integrates to approximately 0.4686131944 kg.
This is numerical evaluation of the published series, not independently weighed mass or a fermentation case.
The authors already filled missing PCS samples and retain anomalies assessed negligible. Normal classification,
complete numerical coverage and absent quality codes do not establish good original sensors. The first log row,
experiment-start event and first sensor record have different clocks; none is guessed as the other's origin.
One explicit fixed-archive recovery also reproduces the selected source bytes without replacing repository data.

Review found the source runner trusted whatever files a manifest happened to list. Two missing-pin controls
failed before repair; the runner now requires all eight runtime files before invoking analysis. Output/cache
paths must be outside the checkout. Source, key and numerical outputs are unchanged. Actual source recovery,
complete report replay and the specific refusal controls are distinguished from general connector acceptance.

A309 uses the [existing context tools](../examples/batch-analysis/context-handoff/README.md), with no new
service: four initial context CLI calls (three successful and one intended stale-CSV refusal) and two pure
Snapshot graph/register readbacks retain a fictional proposed partial answer. Switching the relied-on report
from previous-value to linear reopens it as stale/unanswered while preserving the complete decision/owner
history. Original CSV and graph stay unchanged. Event/recipe/lab/model requests remain explicit. A manual
readiness worksheet separates sample/event time from result availability, exact identity/revision, reviewed
join, units, owner and next step. It implements no automatic lab/event join or kinetic-sufficiency judgment.

The first combined 26-method regression program exposed a test-authoring NameError after the ported context
comparisons had passed: new test code split an existing path test. Moving those statements back fixed the test;
the two affected methods then passed. No product code, data, key or worked output was changed for that repair.
The source-only integration subsequently passes 56/56 programs with zero failures, eight skipped unittest cases
and three explanatory platform notices. All 3,626 source files stay byte-identical during that run. The current
26-method batch program passes through the normal runner; its saved summary is not a separate full-method
transcript. Independent whole-feature receiving covers 45 registered examples and supporting runtime/guides.

A later private-index whitespace preflight correctly flags original CRLF/trailing spaces and an existing blank
EOF line in the anomaly YAML. Only the exact five copied-original paths gain EOL whitespace exemptions; only
that YAML also gains the EOF exemption. `-text` stays unchanged and no source/key/code/report byte changes.
The first failed check and first partial policy check remain retained. The complete change now passes the Git
whitespace check, an unlisted neighboring file still fails, and a fresh targeted three-test Git checkout run
passes. Independent receiving qualifies the pre-policy source suite and these later policy checks separately.
All 235 prior published review objects remain unchanged when adding the new feature review. Full/SDK tests,
new exact-head CI, industrial/fermentation validation and timed human benefit remain unestablished.
## 156. Follow a change beyond the drawing

The five-episode [demo series](DEMO_SERIES.md) presents the existing source/model, process-analysis, onboarding
and owned-team paths around useful engineering jobs. It identifies their separate public/fictional fixtures;
they are not one connected plant application. The root introduction now leads with reusable engineering
knowledge and explains the draft twin model as one foundation rather than the whole outcome.

The new [structural-change tutorial](../examples/engineering-change/README.md) adds a distinct missing episode:
an authored model/layout actually changes from one pump to proposed duty/standby branches. Existing description,
generation, question and context tools do the work; no production implementation changes were required. A/B
source, native answers and the initial semantic key were frozen before the first build. Sources and key came
from the same author; this is development/regression evidence, not independent interpretation accuracy.

The first actual A build correctly generated C9, while the authored key incorrectly expected E1. E1 needs a
discharge control valve and none was specified. We retained the failed expectation and corrected the key rather
than inventing a valve. C9 stays one question while its explicit machine scope expands from P-1 to P-1/P-2.
The independent v4 review checked complete outputs, source meaning and 21 typed pure Snapshot envelopes.
It identified missing final key/runner/catalog custody guards and an exit-only stale-model observer. The
successor guards those bytes, checks both retained catalogs and the exact source mismatch, and adds a
bad-topology build refusal before publication. Another observer had required the word fingerprint; the real
mixed graph/context refusals correctly named the content hash. Those refusals and the corrected observer remain.

Visual inspection moved two authored tee coordinates away from stream labels; source facts and model endpoints
stayed unchanged. The current worked run completed 14 CLI jobs and 56 assertions, including four specific CLI
refusals and both mixed-pair refusals. Both assets content and selected source revision reopen the fictional
partial arrangement answer. One complete proposed decision and one ownership record remain, with plant truth
unknown and no new accepted answer. Ignition/PI gain equipment entries, but templates contain no signals.
Independent successor/public receiving passed the adopted tutorial, artifacts and five-episode navigation.
Four focused programs pass: engineering-change 3, description workflow 23, checkout contracts 3 and runner
controls 19 methods, with no skipped cases. Broader integration and full/SDK CI remain separate.
The subsequent source-only integration passes 56/56 programs, with eight skipped unittest cases, three
explanatory platform notices and no additional skipped-check notices. All 3,660 source files remained unchanged
during that run. Later review/guide/status/ledger metadata is checked separately; current full/SDK CI remains unrun.

No isolation/nonreturn details, sizing, electrical design, protective function or automatic changeover is
invented. Design B is a proposal, not installation/execution evidence. No plant, receiving engineer, company
authorization, operating benefit, unfamiliar-input accuracy or global-scale service has been validated.

## 157. Check the calculation basis before reusing a saved result

The separate [basis checker](../examples/batch-analysis/basis-check/README.md) addresses an explicit lifecycle
boundary: an unchanged report does not show that its CSV, plan or graph still matches. A311 reads only selected
local inputs and the current calculation/validator modules, compares their recorded identities, and reruns the
existing analysis only when every pin matches. A complete typed JSON comparison catches changed result content,
including Python-equal boolean/numeric values and signed zero. The checker writes no files, follows no report
paths and changes no context decision. Calculation and context implementations and earlier outputs are unchanged.

The existing fictional V1 and both V2 reports reproduce. Six other actual CLI controls retain changed CSV,
plan, graph, historical-code pin, result content and missing graph selections, with expected exits 1 or 2.
Changed input whitespace is a raw-byte basis change even when its arithmetic would be unchanged. An old code
pin requests historical review, not a declaration that the old calculation was wrong. Input fixtures keep raw
identity; code pins fold CRLF to LF. Runtime and upstream record qualification remain outside this check.

Two initial new-test failures were authoring errors: the V1 fixture names FT-101 rather than FEED, and setting
an existing 0.0 to 0.0 was not a mutation. The corrected controls use the actual tag and distinct boolean,
signed-zero and integer/float values. No analyzer, source or expected calculation was changed to fix them.
Three focused programs pass 56 methods: existing batch analysis 26, new basis checker 11 and runner controls 19,
without skips. Broader integration and independent review are recorded separately once actually executed.

Anatomy remains an optional authored visual case study, with its MIT attribution and Node/browser requirements
explicit in the dependency guide; it is not a core engineering method or shared toolkit requirement. Remaining
source-question adequacy, model-free contribution history, unsupported formats and company receiving acceptance
are separate gaps; this calculation check does not close them.

Independent prospective checker receiving passed all 37 planned CLI cases once: six matched, sixteen changed
basis/result and fifteen invalid/refused selections. Complete original stdio, distinct process records and the
341-file private closure were retained. Four new/changed example files were directly reviewed; forty-four
unchanged files retain their exact prior passing review. The public nine-case receipt matches its actual run.
The subsequent source-only integration passes 57/57 programs, with eight skipped cases, three explanatory
platform notices and no additional skipped-check notices; all 3,668 captured files stay unchanged. Review and
documentation metadata recorded afterward is checked separately. Full/SDK/CI acceptance remains unrun.

A separate original-source audit identified default E13's blowdown scope/action gap. Root also read the two
captured DOE Tip 9 pages: ordinary manual bottom blowdown and surface-control optimization are distinct.
The [question guide](OPPORTUNITY_SCREEN.md) now states the specific unresolved limitation and records-first
interpretation. The shared catalog/engine and its 25-of-50 source-review count remain unchanged. Frozen
prospective controls and any private candidate work are preparation for a matched repair, not an adopted fix.

## 158. Preserve connections and engineering claims in a smaller graph

A reader-path and contract audit found a functional mismatch in the `core` graph profile. Basic own-drawing
intake contains no line-network membership records, but reduction removed all 345 drawing connections anyway.
Even the enriched saved sheet had two pairs without a selected network. The full export remained intact; the
smaller view could not reconstruct what it had discarded. The original
[core file](../examples/graph-export/sheet0_graph_core.json) remains historical evidence.

The repair removes only ordinary, unreviewed, undirected pairs with an explicit retained network and both exact
memberships. Ambiguous/unrepresented pairs and additional qualifications remain complete original edge objects.
The full graph is validated before projection so an invalid network reference cannot disappear into a passing
output. Core claim filtering elsewhere is unchanged. A first conservative candidate retained every pair because
ordinary extraction-confidence claims use `extracted`, not `unverified`; the failed result was kept and the
predicate corrected to distinguish unreviewed extraction from review decisions.

An adversarial extension then demonstrated nine further failures: topology membership cannot reproduce a
supplied size, fluid, limit, false/zero value, ordered list, custom label/kind or conflicting direction claim.
The final predicate retains those whole pairs too. Only the declared extraction-internal claims and exact
ordinary direction/kind/name values may leave with a represented pair; it does not guess engineering meaning.
The [current core](../examples/graph-export/sheet0_graph_core_v2.json) keeps the two unresolved pairs and removes
343 represented ones: 393 edges and 982 retained claims. Basic intake keeps all 345 pairs and 446 total edges.
These are exposed software controls, not new drawing accuracy or physical impact-analysis results.

Six added graph regression methods cover actual offline intake/export, absent/ambiguous membership, qualifiers,
substantive typed claims and invalid-input refusal. The graph module runs 64 methods with one optional case
skipped. Independent prospective checks include the original failures, unchanged valid full outputs, ordinary
represented reduction, Native streams, off-page pairs, source guards and pure context/Snapshot readback. No model,
SDK transport, plant connection or human-benefit trial is involved.

Two description bundles and three batch reports were actually regenerated after the producer/validator source
changed. Only their code identities changed; all other artifacts and engineering values stayed exact. Fresh
context preparation/application/refresh and stale-sheet refusal produced current expected packets and
[a new fictional answer](../examples/batch-analysis/context-handoff/fictional-partial-v2.csv). The original
answer CSV remains unchanged; earlier packets and reports remain in Git history. Nine calculation-basis controls
were actually rerun. This is a new illustrative source selection, not a repair of an old reviewed fingerprint.

The first broader source-only run reports **55/57**, eight skipped cases and three platform notices. One old
batch regression assumed the validator file identity could not change; the corrected comparison excludes only
the two code fingerprints while keeping every engineering value exact, with current pins checked separately.
The other failure correctly exposed a stale structural-check receipt after a descriptive still-count correction;
that stage was actually rerun rather than its lock being backfilled. Targeted follow-up and final committed-version
CI remain separate evidence from this original failed run.

The targeted follow-up passes the batch module's 26 methods, saved-basis checker 11, description workflow 23,
and pipeline 45/45 checks. The final graph module's 64 methods retain one optional skip. Pipeline status returns
to 50/52 fresh; the two manual runtime stages remain stale. The other source-only programs are not relabelled as
a new full run; normal committed-version CI is the separate complete-suite gate.

The same audit separates current status from retained repair history; clarifies model correction versus context
review, private working paths, approved IT/OT placement, conditional onboarding steps, fixed-case gateway assembly,
optional MCP/local reading and visual evidence labels. The feature catalog now explains its exact example-file
badge predicate instead of implying current implementation/test freshness. No new dependency, company service,
source authority, workflow execution or operational acceptance follows from those documentation changes.

## 159. Review blowdown, valves and tower water from existing records

Original-source review found three collection policies that could lead an engineer beyond the evidence.
E13 confused normally manual bottom blowdown with surface control and let a nearby generic analyzer quiet
the water question. C4 prescribed resize/trim from opening or bypass clues while its benefit excerpt omitted
intervening valve-characterization context. E24 let a generic analyzer settle tower-water coverage and supplied
an incomplete chemistry/water-balance investigation. Its unused absent-meter caption was a static catalog gap,
not an observed emitted assertion that meters were missing.

The [water and valve records tutorial](../examples/opportunity-screen/water-valve-records/README.md) shows the
own-model route and useful contribution: existing function and source basis, unresolved coverage and next
record recipient. [Primary-source scope](../examples/opportunity-screen/water-valve-records/SOURCES.json)
distinguishes bottom/surface duties and proportional boiler control, valve/system characteristics and legitimate
bypasses, and chemistry-constrained tower targets with matching conductivity/water records and loss review.
Source examples do not supply site targets, savings, installed truth or operating authority.

The final catalog changes only E13/C4/E24. Other 47 whole rules and shared catalog records remain exact;
49 benefit objects remain exact. C4's misleading ellipsis is replaced by a qualified paraphrase, with the
original retained. No screening-engine code or new dependency was needed. The catalog still has 50 rules and
126 requests; 28 now have bounded source-informed collection reviews and 22 remain. N065 question usefulness,
human/recipient acceptance and whole-catalog engineering adequacy remain open.

Eight existing fictional E13 cases retain eight original and eight private candidate calls. Twelve valve/tower
cases were frozen before twelve original and twelve private candidate calls. Independent review then froze
five further E13 criteria: proportional control, rate denominators, typed unknowns, a known boiler named steam
generator, and conflicting dry/unknown service. Their five exposed materializations have separate matched
original/successor calls. [Exposure and history](../examples/opportunity-screen/water-valve-records/history/PROVENANCE.json)
retain the exact original reports and distinguish those trials from current-default integration. None is a
new independent plant, blind source or model-accuracy result.

Four initial regression methods fail 39 assertions on the original 20-case catalog. The final five methods
cover 25 cases, complete default report reproduction, selected-field presence and exact typed values,
qualified unknowns and retained history hashes. Minimum/allowed source-job outcomes are separate from exact
saved traces: an adequate existing function may be acknowledged without creating another project. Conservation
of other rules is recorded at adoption; the suite does not prohibit later independently reviewed improvements.

The first root successor copied an old metadata patch's invalid request-location shape rather than the corrected
executed E13 catalog. That failed run remains; the list was restored from the actual executed input. Producer
checks also retained a CRLF-versus-LF observer stop, an authored roll-up argument error, a description invocation
that hid installed dependencies with `-S`, and an unsupported graph-export `--context` argument. These are
separate from the source-job failures and are not relabelled as successful product runs.

Final producer execution uses the catalog's declared LF bytes: 25 case screens, four complete common screens,
one roll-up and six description prepare/check/build calls. Common screens and roll-up match complete earlier
LF text and their original working bytes remain unchanged. Across the two description bundles, 65 of 69
artifacts stay raw-exact; two catalog snapshots and two build receipts are actual successors. Models, geometry,
answers and existing generated questions do not change. Earlier CRLF-bound producers remain distinct evidence.

Three separate fictional context exercises carry old partial proposals through revised E13/C4/E24 questions.
All preserve the complete decision and owner histories, reopen the answer, and refuse the old prepared sheet
before output. The actual context-produced graphs and pure core projections validate, and six selected
full/core Snapshot pairs return complete current/history records. This is local readback, not MCP transport,
authenticated review or company integration. The question module passes 169 methods with one optional skip;
description workflow passes 23 methods. Broader release checks remain separately recorded for their exact source.

## 160. Renew the catalog captured by the equipment-change tutorial

Both ordinary CI runs for `74cf2bd` report **74/75** full cached-data programs: the equipment-change tutorial's
saved catalog still contains the earlier default. Its actual replay correctly consumes the revised default
and the exact-catalog assertion catches the mismatch. The source-only suite excludes this drawing-dependent
program, so its earlier 57/57 result did not cover the failed check. The optional MCP jobs passed separately;
the six-suite comparison step was not reached in either failed run. These results remain failures.

The existing [equipment-change runner](../examples/engineering-change/reproduce.py) was actually executed
again: 14 CLI jobs, including four intended refusals, and 56 checks. Both revision builds capture the exact
current default catalog. Of 20 selected public artifacts, 19 remain raw-identical, including the models,
drawings, generated questions, context and complete prior decision/ownership histories. Only the selected
catalog is replaced from the actual output. [Provenance](../examples/engineering-change/PROVENANCE.json)
retains the original run identity and separately records this successor; original bytes remain in Git history.

The runner, source/key, assertions, calculation/generation code and rules are unchanged. The three targeted
engineering-change tests now pass, including an actual further replay and existing-output refusal. This closes
the missed worked-example dependency rather than relaxing the test, backfilling an old producer receipt or
claiming complete automatic dependency management. Later normal CI belongs to its own commit and run.


## 161. Retain a document-only contribution and reopen its combined source basis

The document-only route could read an authored knowledge packet but required hand editing to retain new
source captures and findings. Added `knowledge_capture.py`: an explicit local change request and selected
complete UTF-8 records become a new packet, exact prior/change copies, readable handoff and hash receipt.
Existing records remain unchanged; new claims are proposed/unreviewed. The snapshot reader and MCP stay
read-only. Authoring an answer, checking its citations, selecting source authority, assigning a real recipient
and recording company disposition remain human/company work.

The fictional fermentation exercise asks whether a recipe target and displayed export establish actual feed
mass. It retains conflicting/missing basis and attributed recollection; a newer export clarifies units/reset
but leaves an observation gap. The old answer reopens, its dependent handoff needs review and a new partial
answer retains the unresolved evidence request. FT-102 is the fictional batch/record identifier, not a verified
instrument tag. Counterfactuals change the recipe and recollection separately; historical snapshot evidence
remains readable and unrelated comparison evidence stays matched.

The recorded fresh case runs 28 actual CLIs (two intended refusals) and passes 16 software checks under criteria
written before execution. Twelve new test methods cover exact CRLF/Unicode/empty captures, existing-output
preservation, bad-base/ID/source/schema/cycle/response refusals, false list values and Markdown as data. A
deliberate wrong authored statement is admitted unreviewed: hashes and locators do not establish support for
prose. Tests and source keys are exposed agent-authored development evidence, not blind plant interpretation
or a human-recipient trial. All earlier attempts and all 116 ideas remain; N062/N063 and 22 source-rule reviews
are still open.

Development receiving caught wrong documentation parent paths; they were corrected. Prospective review also
challenged false list values; all non-list inputs now refuse instead of being converted to empty lists. The case
runner originally reused one log label for success and a later refusal; distinct labels and a duplicate guard
retain all 56 raw streams in the fresh successor. Earlier runs remain private rather than being relabelled as
that run. The handoff puts newly authored findings before retained older claims and shows both their status.

See [the worked contribution loop](../examples/engineering-onboarding/contribution-loop/README.md),
[criteria](../examples/engineering-onboarding/contribution-loop/acceptance.json),
[actual results](../examples/engineering-onboarding/contribution-loop/worked/result.json) and
[provenance](../examples/engineering-onboarding/contribution-loop/PROVENANCE.json).


## 162. Compare selected batch records and recheck the calculation underneath

Added a reusable local `join_batch_records.py` route for explicitly selected batch, phase event, reported
executed recipe, lab and outcome CSVs beside saved batch calculations. The operator-selected manifest names
all files and exact record/window IDs; saved reports never choose paths. The existing basis checker first
checks/reproduces report/CSV/plan/optional graph. Changed upstream files with an unchanged calculation
withhold feed totals; rebuilding produces a new result without replacing the old one.

The fictional source key is independent hand arithmetic: A/B feed2/4kg, reported assay10/12g/L and harvest
volume900/920L. Their recorded differences are2kg/2g/L/20L, with no yield/causal or plant conclusion. The source
and negative criteria were frozen before initial join implementation. Review exposed two source-contract
refinements: analysis files need explicit availability declarations, and recipe revision labels alone need a
selected reported executed recipe and full typed parameters. Original unqualified inputs, refinements and
private first implementation results remain. The later qualification is informed development evidence,
not blind preimplementation validation. Fictional January availability is not the November producer clock.

The decision summary excludes late/unavailable selected values under supplied metadata; the complete audit
and captured originals deliberately retain all selected/unselected/future rows. These are separate roles, not
a leakage-free historical-access study or ready ML dataset. Identity, time, unit, quality, recipe, scale,
method and source gaps block a complete comparison. Exact plan-window/event IDs matter even when all other
event fields match. No automatic latest-result choice, normalization, imputation or semantic verification.

Independent actual controls caught two admission defects: a different event ID with identical values could
substitute for the referenced event, and whitespace-only method/sample/scale metadata could complete the
comparison. The six original baseline calls and outputs remain private. The repairs add exact event-source
binding and strip-aware missing checks without rewriting original lexical fields. The root's first null-quality
test incorrectly retained a disallowed quality CSV column; its test fixture was corrected before checking the
valid null-policy contract. An independent operator later stopped on duplicate log labels; its88actual calls
and stop remain separate from the exclusive final103processcohort and5graphcontrols. No product failure or
reproduction was invented to replace that observer error.

The final exposed software cohort passes its frozen cases, including typedfalse/0 recipe parameters,
availability/chronology, optional graph admission, stale inputs and complete output tampering. The fresh
public exercise runs14CLIs with11checks, including3intended changed-result exits and1existing-output refusal.
All182public outputs and19input/method files are pinned. Sixteen focused test methods cover source arithmetic,
full field/raw capture, negatives, current-code/input reproduction and the actual case replay. Existing
question rules and source-review counts remain unchanged; parallel rule audits are private/unadopted.

This delivers bounded record joins and explicit upstream calculation freshness. Automatic/live ingestion,
continuous source monitoring, accepted investigation/hypothesis outcomes, authenticated company import,
actual recipient usefulness and plant/causal/kinetic acceptance remain open under the standing goal.

See [the tool tutorial](../examples/batch-analysis/record-joins/README.md),
[initial criteria](../examples/batch-analysis/record-joins/ACCEPTANCE.json),
[public actual replay](../examples/batch-analysis/record-joins/worked/result.json) and
[provenance](../examples/batch-analysis/record-joins/PROVENANCE.json).


## 163. Complete the bounded source-policy review without dropping useful signal references

Reviewed the remaining 22 catalog rules against original source material and prospective collection criteria.
The existing question engine now keeps exact service/quantity/time/coverage and source applicability open
while showing supplied candidates. Existing records come first; labels, scalars, unrelated monitoring or a
quiet screen do not establish installed absence, correct operation or approval to modify equipment. All 50 rules
and 126 requests retain bounded collection reviews, not a whole-catalog correctness or usefulness guarantee.

The public tutorial retains 88 unchanged exposed fictional models, their 176 original reports, source identities,
criteria and actual final 176 reports. Original PDFs are not redistributed. Source interpretations and conditional
questions were independently reviewed; E18/E19/E21/E25/E26 benefit wording was qualified without introducing
new site estimates. The other 28 rule objects, shared objects, other 45 benefit objects and structured source/quantitative fields
remain unchanged. Historical S19 experience and unverified S24 figures retain their limitations.

Receiving rejected an E18 residual pairwise-only limit and a C1 change that lost a useful valve-position
diagnostic. Their rejected proposals and matched repairs remain private. Integration then found a second E18
regression: replacing its tasks had dropped existing temperature/flow historian locators. The matched failure
is preserved; exactly two old quantity-aware locators were restored into the new first request. Actual TE and
represented-flow controls preserve supplied quantity-specific signal references and distinguish valve position
from measured flow.
New records-first tasks and process-wide/time-aware constraints remain intact. A cross-rule audit then
reviewed six other removed locator declarations. Five request-location lists now preserve useful lookup or
position-warning behavior; E15/E19 global candidates carry explicit unverified-association qualifications.
E14's old equipment-only lookup was a no-op and remains disclosed rather than being presented as a recovered
measurement. Twelve separate synthetic symbolic-pointer controls retain matched original/successor reports;
there are no actual time series, additional source-reviewed rules or plants. Renderer text now distinguishes
source quotations from contextual paraphrases instead of falsely calling every benefit entry verbatim.

Separate actual publication cohorts retain common-path original runs, adopted-policy runs, the presentation
successor and final locator successor. No earlier run is relabelled as the final method. Current screens/rollup,
description bundles and equipment-change catalog were rebuilt with actual producers. Description examples now
include a C2 measurement-purpose inquiry. The Bayer register keeps both complete proposed decisions and no
ownership history; its earlier partial response was already stale and remains so. Explicit refresh adds no answer,
and the old sheet still refuses. The new local SDK sample was captured rather than given a replacement digest;
its complete asset response is unchanged apart from graph identity and actual load time.

These are exposed source/software controls without model/provider calls or plant data. They do not measure
human effort, savings, generalization or company acceptance. The intended recipient is an engineer or manager;
no actual participant, company tenant, records or access was supplied. Real reconstruction/effort/outcome and
approved receiving-system revision tests remain standing-goal requirements. Investigation/hypothesis outcome
retention and its own-input demonstration also remain work; the batch joins are not a finished investigation.

See [the source-policy tutorial](../examples/opportunity-screen/source-policy/README.md),
[criteria](../examples/opportunity-screen/source-policy/expected/source-criteria.json),
[provenance](../examples/opportunity-screen/source-policy/PROVENANCE.json) and
[current boundaries](STATUS.md#open-work-and-company-handoff).


## 164. Retain an investigation and distinguish missing evidence from a failed explanation

The existing batch join/check, contribution capture and knowledge reader now have a worked investigation
continuation. No new investigation engine, workflow kind, model dependency or approval service was added.
An unbound packet retains an authored recipe-revision hypothesis and planned record check, then records
contrary evidence, a limited proposed disposition, source revisions and the next evidence request.

The fictional FERM-101 source key remains unchanged: A/B recorded feed 2/4 kg, reported concentration
10/12 g/L and harvest 900/920 L. Both batch and reported-executed recipe rows declare RCP-1 revision 3.
That does not support different declared recipe revisions as the explanation; it does not establish actual
process identity or another cause. Later lab 13 g/L and regenerated feed 6 kg are separate source scenarios,
not process interventions. The lab branch explicitly selects its baseline feed/calculation and retains the
changed-feed branch. Final capture includes an actual successful join check bound to the final lab report;
future reuse still needs an explicit current check.

Independent receiving found a real defect despite the first runner's passing mechanical checks: an unavailable
B lab was treated as a method mismatch. The join compared an absent method as None with an admitted method.
Five frozen regression methods retained nine failing assertions. The repair compares known admitted basis
components independently, reports unavailable basis explicitly and preserves observed differences in other
components. Eleven matched whole cases retain exact audits/raw inputs, changing only the method pin and
declared comparison-gap codes. A failing-baseline fixture had skipped cleanup after an assertion; unconditional
cleanup and new matched old/current runs are retained rather than rewriting the original failed observation.

The first 29-call investigation remains separately retained with its semantic failure. The corrected 29-call
successor and final 30-call/24-check run are distinct. Twelve prospective retention criteria were frozen before
implementation; optional typed-profile controls were kept separate. Final independent receiving checks exact
sources, prior packet/claim preservation, complete readbacks, current check binding and genuine new stale-basis
paths. An always-unknown hypothesis is not evidence that a changed source reopened its dependent disposition.

All records remain proposed/unreviewed. A separate deliberately unsupported causal sentence is admitted by
generic capture as unreviewed, demonstrating its semantic boundary. Hypothesis/test/result/disposition roles
are authored prose; the tools do not validate scientific logic, infer omitted dependencies, select an accepted
resolution, watch external files or execute operations. Company systems retain decisions, access and ownership.
No human usefulness, company acceptance, causal/kinetic model or unfamiliar-plant result is claimed.

The public example retains every capture revision, exact source/report/check evidence, readable handoffs and
an own-input template. Raw process argv/logs remain private; public command displays are explicitly templates.
The existing join tutorial was renewed through its actual 14-call/11-check producer after the repair, with the
original method/provenance and a reproducible failing case retained. Older full receipts remain in Git/private
archives. New end-to-end tests cover the complete composition, source-change paths, current final check and
historical failure; earlier methods and all prior ledger/review records remain intact.

See [the investigation tutorial](../examples/batch-analysis/investigation/README.md),
[own-input guide](../examples/batch-analysis/investigation/OWN-INPUT.md),
[prospective criteria](../examples/batch-analysis/investigation/ACCEPTANCE.json),
[actual output manifest](../examples/batch-analysis/investigation/PROVENANCE.json) and
[retained comparison-basis failure](../examples/batch-analysis/record-joins/history/before-comparison-basis/).

## 165. Make the drawing-to-map fixture portable

2026-11-06. Reproduced issue #7 locally by changing the committed sheet from CRLF to LF. Its exact-byte hash
changed from `a23a1786...` to `c5830aa2...`, reproducing the Linux graph assertion. Pin the fixture tree to LF and
regenerate the expected graph; retain exact runtime hashes rather than normalizing every user's source.
All 15 conversion tests then pass; represented counts and reader output are unchanged. The prior assertion and
hashes remain in issue #7/history. Exact-head Linux CI is a separate verification recorded with this delivery.

## 166. Qualify a bounded CAD attribute exchange

2026-11-06. Added `cad_handoff.py` for explicit hash/before-value-bound DXF attribute proposals. Original bytes,
stable IDs and unfamiliar attributes remain; separate before/proposed context snapshots avoid silent graph or
company-system writes. Six regression methods include planted geometry/layer/foreign-attribute/XDATA losses,
stale sources and plans, duplicate/identity edits and output overwrite refusal. The declared decoded entity and
header surface is compared on readback. The writer's two metadata values are reported separately; nested child
entities are compared in their own rows instead of counting their edit twice in the parent's export.

The fixture is authored from the existing fictional replacement scenario, not extracted from plant CAD. The
passing exchange uses ezdxf 1.4.5 on both sides; no native CAD editor or intelligent-P&ID database acceptance,
field truth, opaque-section preservation or automatic synchronization is established. The owning CAD receiver
must still complete the documented open/edit/save/readback and next-revision exercise.

An explicit tutorial mapping also projects before/proposed CAD attributes into actual one-map graphs at the
same fictional position. Original DXFs, source hashes and earlier map remain; the changed reference values are
unverified and prefixed `cad_`, with no inferred pipe/control relationships or installed-record overwrite.
An unmapped identity or changed tag is refused rather than guessed. Saved map diff retains the proposed revision.

## 167. Retain nameplate evidence and OCR failures

2026-11-06. Retained two openly licensed Commons originals: an ABB industrial-machine plate attributed by its
uploader to Berlin-Moabit, and an Electrolux recorder motor. Manifests retain attribution, license and exact bytes.
Six Tesseract 5.4.0.20240606 development attempts include every whole-image/crop/segmentation outcome. Recorder
whole-image PSM3 found no text; crop variants remained unreliable. Industrial PSM3 omitted the numeric data
despite mean word confidence 75.1; PSM6 also remains incorrect/incomplete. Nonempty text is not field acceptance.

Visual candidate sheets retain locators, units and unknown asset association; the plate number is not promoted
to a verified unique installed identity. Sources and candidate readings were exposed during development, with
no independent human key or field-accuracy claim. Four evidence tests bind originals, all attempt outputs and
the CAD packet. No actual human usefulness, company acceptance or measured savings closes N052/N062/N063.

The new maintenance/drawing starting guides reuse existing tools, and the replacement walkthrough reuses the
fictional pasteurizer. Public contact goes only to Steve's LinkedIn. Active post copy/campaign planning belongs
in the separate private writing repository; no post, outreach or schedule is published by this delivery.

## 168. Separate alert detection from delivery and retry the native CAD receiver

2026-11-06. Steve asked to consider alerts as a possible later-product responsibility and clarified installation
permission. The roadmap now distinguishes explicit toolkit comparisons/staleness/review queues from maintained
collection, recipient resolution, delivery, deduplication, acknowledgment and escalation. It defines prospective
end-to-end cases, including missed changes and failed checks, without adding a watcher, event schema or delivery
implementation. Process alarms remain separate. Public plans name no unannounced product; campaign copy remains
in the private writing repository.

LibreCAD 2.2.1.6 installed successfully through winget with the publisher installer checksum verified. This
resolves the earlier installation blocker. Two native dxf2png runs on the retained fictional proposal produce
the same PNG. The second observed exit is 0; the first exit was not captured. Valve/line geometry appears, but
expected title and attribute text is not readable. The cause is not isolated, so this is not a CAD acceptance pass.

GUI startup, visible relaunch and the exposed Raise action were attempted. Accessibility text was available,
but capture timed out and input reported unavailable geometry/an unusable app window. No editor-made edit or
returned DXF was obtained. These failures do not establish that LibreCAD cannot edit the source. Retained
[native receipts](../examples/cad-handoff/native/receipt.json), [image and scope](../examples/cad-handoff/NATIVE_ATTEMPT.md)
separate actual CLI observation from the still-uncompleted native receiving checklist. No company acceptance,
human benefit or new drawing-reader accuracy is inferred.

## 169. Put the manager's decision and receiving work first

2026-11-06. Steve prioritized maintenance and engineering managers as the audience, matching the stated experience.
Added a decision-first guide and a no-install fictional manager packet using the existing pasteurizer tools.
Eight authored department actions retain their source basis and leave named people, dates and actual receiving
acceptance unfilled. The packet distinguishes a resolved serial dispute from the still-incorrect selected CMMS
export, a missing PM row from an absent plant PM, and a green drawing-location row from overall asset readiness.

The case runner executes four existing CLI commands with Python's standard library and verifies the five
declared case facts. Its selected closeout reproduces seven changed/seven unchanged record-item entries, two
reviews not checked here and one open expectation gap. The complete broader queue retains 33 rows, including
green rows; neither total is an action-backlog or asset count. The source manifest and selected method hashes
retain their exact declared scope; they are not a complete environment lock or a claim of original-source truth.

The downloadable ZIP contains an offline browser brief, evidence and manual scope/review/effort forms. Desktop
and mobile checks find all eight actions, resolve local links and make zero HTTP requests. Mobile tables render
as readable cards. No spreadsheet engine, action tracker, company import or alert service is introduced.
The normal CI workflow also runs this stdlib case replay; it is not counted as a real recipient trial.

Removed the unmeasured 15-minutes-per-owner-week estimate from the active operating guide. Refresh cadence,
named owner capacity, first-seen/due dates, complete comparison effort and receiving verification now require
actual observations. Raw queue counts and local rule coverage are not PM compliance, equipment health or a
reliability KPI. The private consulting plan now names the primary audience; no published social material changes.
Real manager usefulness, company correction/readback and a subsequent accepted revision remain N062/N063, not run.

The first CI run passed 88/89 programs but failed the operating-guide check because it required the removed
unmeasured weekly time estimate and universal monthly cadence. Updated that existing documentation check to
require the measured-effort limitation and explicit no-notification boundary instead. Also removed the remaining
monthly instruction and assumed labor replacement from the guide's closing section. The packet runner disables
site packages in its child commands as well as its CI entrypoint; its receipt records that execution flag.

## 170. Let an agent help a manager use the tools immediately

2026-11-06. Steve asked for simulation now and emphasized people pointing their agent at the repository for
self-service help. Added a task-first entry to AGENTS and a linked agent guide: choose from the user's job and
available records, ask only questions that change the next step, do the preparation and return a sourced finding.
No contact, full scope worksheet, repository audit or site-wide model is a prerequisite to a first partial result.

The authored first-use conversation is role-play, not an independent agent session or manager observation.
Its software actions actually run: ordinary export header mapping with retained original row locations, a
two-unit same-tag record comparison without a P&ID, a missing-unit preparation refusal, an authored returned
export and selected change report, plus public-sheet intake/report using a saved reading. Five existing CLI
commands run with site packages disabled; ten exposed case conditions pass. U1's serial disagreement clears
only after the supplied simulated return; U2 stays separate and bare-tag ambiguity remains. The open order is
not used as completed installation evidence, and originals remain unchanged. Source and selected method hashes
are retained with the case; no complete environment lock, arbitrary importer or new autonomous agent is claimed.

An initial example runner assumed a top-level conflicts array; the real graph stores conflict nodes. That
local attempt failed and was corrected against the generated graph before recording a pass. No core tool was
changed. The walkthrough also found and corrected the old clone URL in the active own-drawing instructions
and active opportunity/status links. Company record acceptance, new-image reading, human usefulness/time and
independent agent adherence remain unobserved; N062/N063 stay open. This simulation supports immediate scoped
self-service use without substituting for those later observations.

The first clean-checkout CI passed 88/89 programs and failed the corpus freshness check because correcting
the own-drawing README's clone URL changed a pinned row-3 input. Re-ran only row 3 / own-drawing-extraction:
it still passes with 100 items and 345 links. Refreshed its actual run receipt and matrix page; all 95 declared
cell bindings verify locally. The other 94 cell records were retained rather than assigning them new runs.

That matrix receipt/page change also invalidates the exact-output independent-review badge for the matrix.
The next CI run caught the stale feature-catalog rendering; regenerated it and updated current status to
22/29 reviewed examples. The earlier review remains recorded with changed outputs, rather than self-renewed.
The five-test feature-catalog program passes locally. Moved the two short self-service case replays before
the long full-suite step so their own failures surface promptly in CI.

## 171. Explain why SharePoint access does not require MCP

2026-11-06. Steve asked what MCP adds when Copilot already has SharePoint access. Clarified the default in
the README, agent and manager guides, company connectivity guide and MCP starter: use existing document
retrieval/comparison first. Prepared toolkit reports and tables can remain in SharePoint. MCP is an optional
named tool/record interface; the preparation, explicit identities, source links, comparison rules and upkeep
supply the engineering meaning. Copilot can reason about relationships and compare records without MCP.

The decision table separates document retrieval, prepared-record reuse, repeated typed lookups and separately
implemented live-system operations. Existing connectors/APIs may already suffice. The current starter serves
selected startup snapshots; it does not crawl SharePoint, inherit its permissions, fetch referenced originals,
refresh, run analysis or query/write a CMMS/historian. Freshness/status comes from the prepared packet and
explicit refresh, not the protocol. Company authorization and deployment remain separate implementation work.

Read Microsoft's current organizational-grounding/SharePoint permission and Copilot Studio MCP documentation.
Traced the declared starter methods and actually read P-1 and its relations through the application methods:
the snapshot hash agrees and live=false. No SDK transport, model or tenant was exercised in that check.
All 19 standard-library snapshot controls pass. No new connector, server behavior, model capability or plant
acceptance is claimed; this is documentation of the existing choices and limits.

## 172. Make ordinary maintenance exports a reusable self-service job

2026-11-06 local / 2026-11-07 UTC. Steve asked to address the four remaining self-service gaps without waiting
for employee testers. Added a standard-library intake around the existing one-map comparison. Its explicit
profile maps source headers, date formats, scope, revisions, owners and coverage. It retains exact originals,
CSV-record/physical-line origins, full queue, sourced HTML/Markdown report, proposed action form and file/method
pins. Failed preparation publishes no packet; existing destinations remain intact. No installed truth, company
write, accepted correction, PM/MOC determination or human saving is inferred.

Eight regression methods exercise mapped unfamiliar headers/semicolon/date formats, leading zeros, multiline
origins, scoped identities/open orders, refused duplicate/ambiguous inputs, missing files, output collisions,
tampered previous packets and changed source revisions/authority. The fixed replay makes three real calls to
the reusable CLI: first disagreement, corrected equipment export, another replacement at the same position.
The old packets verify unchanged; a disappeared finding is retained without accepting or closing it, including
a later export that simply omits the closed order. Malformed profile shapes return an input error. The later
replacement raises a new value conflict. Exact output inventories are not authenticated signatures.

Two actual fresh test-agent sessions ran frozen inputs/prompt/key, without inherited conversation. Baseline
8c306d6 prepared its own one-map inputs and used build/check/ask. Candidate d5dde29 used the new intake and
tested missing identity. Both produced the same substantive answer and usable line-2 source references. The
author-scored literal rubric is 10/12 baseline versus 12/12 candidate solely because the baseline numbered
data records from one while the frozen key counted the header. No accuracy, timing or manager-benefit gain is
claimed. Procedural blinding is not filesystem enforcement; exact model/build metadata was unavailable.
Session answers, command records, actual packets and source-read failures remain in examples/agent-rehearsal.
The offline recheck verifies retained artifacts; it neither reruns agents nor independently grades prose.

Actual browser rendering at a 390-pixel viewport was inspected, with no horizontal overflow and working local
source/report links. An initial raw headless screenshot used a wider layout than its captured window and was
not used to infer a CSS defect; explicit Playwright viewport inspection supplied the mobile check.

## 173. Keep the failed CAD receiver visible instead of declaring an exchange

2026-11-06 local / 2026-11-07 UTC. Retried LibreCAD through the computer-use runtime. It launched and exposed a
readable Open Drawing tree after capture failed; repeated filename input failed with unavailable cached element.
No actual edit/save/reopen or returned DXF was obtained. Private directory-picker trees are not published.

A new ordinary-TEXT control renders as boxes through native PNG. Native PDF shows those controls and the
candidate's ordinary title, but not attached attribute values. All five conversions exited 0; this is not a
preservation pass. PDF page dimensions were unexpectedly large; an unbounded raster allocation failed before
bounded Poppler rendering. Inputs, outputs, logs and failure are retained. Published v2.2.1.6 parser source has
no ATTRIB/ATTDEF dispatch and skips unknown entities. This supports an explicitly labeled inference that this
receiving route cannot be assumed to preserve the required attributed profile; it is not a saved-return test.

The fourth gap stays open: qualify a usable attribute-capable receiver with the exact edit/save/close/reopen
and strict returned-DXF comparison. No intelligent-CAD, company acceptance or subsequent accepted revision is
claimed. SELF_SERVICE_GAPS.md keeps this distinction beside the completed intake/rehearsal/repeat-use software.

## 174. Show why a maintenance finding disappeared

2026-11-06 local / 2026-11-07 UTC. Repeat packets pinned implementation and Python metadata but buried changes
in receipts. New controls first produced four errors against the old tool because comparison-basis.json was
absent; the actual failure output is retained. The updated 13-method module passes, including identical-byte
reinterpretation, date meaning changes, synthetic changed/missing method metadata, omitted history and row reorder.

Returned reports now show changed local methods, recorded Python, cutoff and effective field/date/encoding
settings before the findings. Exact added/removed/changed normalized records retain before/after original origins.
Row movement alone does not count as changed content. Unknown older pins report unknown continuity. Hashes are
not signatures or complete environment locks. A changed basis needs explanation, including ordinary corrections;
an unchanged basis does not establish coverage, installed truth or acceptance.

Two actual CLI controls compare with the retained historical initial packet: ignoring Serial under identical CSV
bytes, and a new revision omitting closed WO-801. Both disagreements disappear, both retain the earlier finding
open, both expose actual code changes, and the latter names prior original record 2. Eight exposed conditions pass.
The original historical packet and fresh-agent session artifacts remain unchanged. Current three-revision replay
passes five conditions; frozen session recheck passes. Six delivery-evidence and five feature-catalog methods pass.
No agent rerun, manager benefit, company readback or authenticated correction is claimed. CI also replays both
basis controls on its current environment; final integration evidence is reported separately.

## 175. Obtain a native CAD return without waiving its differences

2026-11-06 local / 2026-11-07 UTC. Public QCAD Professional 3.33.1 portable trials were obtained from the publisher
and used headless with isolated settings. Qt6 exited zero with no scripting handler; the absent Qt6Positioning
candidate dependency is a diagnosis only. Qt5 loaded the documented scripting engine. A first helper confused the
insert-with-attributes enum with the attribute enum, produced an identity error and no return; its failure is retained.

The corrected native helper found the scoped ICT_ID, checked the planned before values, changed MODEL, SERIAL
and SIZE, exported a separate DXF, destroyed the document and imported the returned DXF into a fresh native document.
All six attribute values survived, including stable ID, TAG and VENDOR_NOTE. The independent-format strict comparator
still fails: one DXF version change, one whole-header difference and 333 entity-record differences, 335 total.
These include record/handle rewrites, not 335 demonstrated engineering losses. No comparator rule was relaxed.
No accepted context revision was promoted. Native GUI/display, preservation classification and company acceptance
remain open. The exposed one-fixture API experiment is not a qualified adapter or Community Edition claim.

Publisher archive hashes, actual logs including failures, helper, returned drawing, readback and comparison are retained.
Seven delivery-evidence tests verify bytes, the exact re-comparison and preservation-failure boundary. The optional
wrapper keeps source hash/output guards and refuses process-zero/script-error false success. Its actual rerun reaches
native readback and returns the expected preservation exit 1 with 335 differences. CI checks frozen evidence
without acquiring trial software. No binaries are redistributed. A 390-pixel browser check of the maintenance basis
report shows no horizontal overflow, the omitted prior original row and all five local report links returning 200.

## 176. Turn a failed CAD exchange into a readable receiving packet

2026-11-07. Steve asked to continue improvements. Traced the retained source/return and all 335 strict differences.
The native return keeps all six asset attribute values but changes style references and adds a paper-space viewport;
the raw count cannot be treated as 335 engineering losses. Four new controls first fail against the old tool because
no receiving-review function exists. The original strict comparator and its saved results remain unchanged.

Added `cad_handoff.py review`: retained drawing bytes and plan values, complete strict comparison, source/method/
Python/ezdxf pins, exact attribute outcomes and missing identities, explicit drawing fields, layouts, named table
fields, per-header changes and an indexed queue partitioning every strict entity row. No geometric matching, automatic
handle remap, equivalence normalization or loss waiver occurs. Complex payloads, child ATTRIB details, XDATA and other
objects remain in the full strict queue. Named table fields do not cover full linetype/style behavior. Added/removed
handles are not counts of physical objects. No context version is promoted.

The default native return partitions into 262 added handles, 53 removed handles, 17 changed same-type records and one
handle reused for another type: all 333 entity differences, plus version and header. There are 54 changed header
values and 64 named-table field records to inspect. Three planned attribute edits are observed; foreign values remain.
Reports explain the new viewport, style references, explicit width and attribute-definition flags. They retain raw
exact before/after values without labeling these harmless. Completed reports with differences return exit 1; equality
under the existing plan returns 0 only for the software gate; input/preparation failures return 2 before publication.

Fourteen CAD test methods pass, including moved geometry, changed layers/foreign fields, lost XDATA despite unchanged
drawing-field observations, renamed handles, missing planned edits, malformed plan shapes, output collision and HTML
escaping. Eight delivery-evidence methods pass. Two real CLI replays retain the expected failure exits, satisfy 15
exposed packet/input conditions and preserve source bytes. These are software development controls, not independent
engineering review, human benefit or native interactive/company acceptance. The final packet is inspected at 390
and 1280 pixel viewports: no horizontal overflow, mobile field labels visible, desktop table headers visible, all
five report/source links return 200. A final Markdown control then fails on literal HTML cell content; the
failure is retained. Both formats now escape source HTML syntax, and Markdown includes source/evidence links.
The 14 CAD methods, eight evidence methods and both 15-condition replay runs pass after the repair. Full CI
is a separate final gate.

## 177. Test an explicit native export version without selecting a flattering count

2026-11-07. Reused the official QCAD Professional 3.33.1 Qt5 trial headlessly with isolated settings; no new binary,
account or paid license. A new helper differs only by passing R15 to documented exportFile. Source and three-edit plan
are unchanged. Actual native export and fresh-document import retain AC1015 and all six expected attribute values.
Changed header values fall from 54 to 3, but strict differences rise from 335 to 344: 272 added handles, 53 removed,
17 same-type changes, one reused handle/different type and a whole-header difference. Style changes and an extra
paper-space viewport remain. A raw count is not a severity score or proof of added/lost engineering objects.

Preserved the helper, actual command/log, returned drawing, native readback, summary and hash receipt separately
from the unchanged first return. Offline replay reconstructs the full strict comparison from public fictional inputs.
No comparator rule was relaxed; matching version/attributes does not qualify the exchange, and no context change was
promoted. Native interactive/display, full preservation classification, intelligent-CAD database and company acceptance
remain open. This single exposed fixture does not establish a receiver ranking or a free production workflow.

## 178. Freeze CAD qualification before trying a preservation candidate

2026-11-07. Set the explicit goal to eliminate unexplained handoff differences without tuning to the valve and
to qualify only a stated exchange route. Committed the protocol before candidate implementation or reserved-case
runs. It keeps library save, direct native save and proposed source-preserving field edits separate; the strict
comparator and existing 335/344-difference failures remain intact. Acceptance includes byte-span preservation,
independent reconstruction, native readback/visual/editability, revision conflict controls and actual GUI
edit/save/close/reopen. Four unfamiliar public CAD originals were pinned before method development: three
geometry categories in LibreCAD and an ezdxf hatch example, two upstream projects. No task runs on them yet.

The existing QCAD Qt5 application launched to its first-start dialog, and accessibility text was readable.
Screenshot capture failed with FrameArrived timeout; the indexed click reported coordinate geometry unavailable,
and one observed keyboard recovery reported an unusable app window. UI input stopped. No drawing was opened or
edited, no GUI acceptance inferred, and no method/comparator tolerance was changed. Independent acquisition and
method work can continue; this UI gate remains open.

## 179. Acquire public records across maintenance and engineering categories

2026-11-07. At the user's request, acquired 54 exact original files (114,865,314 bytes) in 14 download groups:
MaintIE/MaintNorm maintenance language, UCI steel energy and synthetic AI4I failures, three equipment nameplates,
four fermentation/reactor laboratory deposits, additional modalities of the existing distillation plant,
IDAES methanol/adsorption examples, and DOE technical references/instructional drawings. Retained primary
metadata, license/attribution, original source URLs, upstream checksums where supplied, SHA256 pins, omissions,
source-family/exposure descriptions and actual discovery failures. No downloaded code, notebook or macro ran.
The existing DEXPI head is unchanged and all 634 files are already held; no duplicate coverage claimed.

Every new file's hash matches. A real empty-directory HTTPS fetch of the steel CSV reproduced its pin; the
54-file cached replay passed with network replaced by a raising function and a zero download budget. A
cross-check caught a Windows default-encoding rewrite of an existing non-ASCII DWSIM member name while appending
pins; restored the original old groups byte-semantically and verified all 12 pre-existing groups unchanged.

Actual admission retained the failures: generator OCR returned no text; traction motor OCR only six characters;
the other motor's 153 characters are unreviewed. Three batch workbooks read as text; one embedded Word object
was explicitly skipped. Four DOE PDFs produced partial text with the affected pages listed. Archives were only
inventoried; lab workbook/historian/model-schema adapters and interpretation keys remain needed before task
scoring. These are acquired-unscored inputs, not new generalization/feature passes, independent plants, completed
maintenance, savings or production acceptance. No CAD reserved input was opened for this admission.

Full CI then caught a provenance failure: adding catalog registration to `fetch_corpus.py` invalidated historical
matrix cells that fingerprint that file. Retained the failed run (PR run 42385590694, 89/90 programs; matrix
freshness failed). Restored the exact original evaluated fetcher and put the new catalog in an opt-in example
wrapper that reuses its unchanged verification functions. Historical cells, result values and bindings are not
rewritten. The new source groups stay outside that matrix. Re-ran the matrix freshness check and acquisition
tests; original admission retained alongside the post-wrapper replay.

## 180. Expand public originals without promoting acquisition into evaluation

2026-11-07. The user requested more public data across all categories. Acquired another 47 original files,
203,089,339 bytes in 15 download groups: historical excavator work orders from official Nestor Git history,
five facility drawing/design/submission PDFs, UCI turbine/Scania/SECOM/naval data, LANL cultivation data,
HistorianRCA data/description/tags/diagram, six Modelica process examples, three instrument photographs and
six additional CAD originals plus their notices. Together with entry 179: 101 files in 29 download groups
(not independent plants), plus the four separately frozen CAD originals. Original downloads remain local.
Pins, primary metadata, rights/attribution, source families, exclusions and admission failures are public.

Retained the original Salina Python trust-chain failure; verified Windows system TLS downloaded the original
successfully without disabling certificate verification. IRIS's linked CAD/photo/P&ID source is restricted
CC BY-NC-ND, so only its metadata/file inventory was retained. KALBRO's API exposed no files. The Nestor data
license remains unresolved; source software rights are not substituted. APS's source GPL notice and UCI page
footer conflict; keep originals local and do not commit derivatives. No commercial reuse clearance is inferred.

Actual admission retains the earlier LANL CSV's UTF-8 failure, one unexpected-width raw Nestor row and two
cleaned rows. Virden has no text layer on all 14 pages; three other facility PDFs have partial text with page
numbers preserved. Parquet framing only was checked; archives were inventoried without reading/extracting
members. CAD contents were intentionally not inspected; filenames/raw hashes do not establish a held-out
qualification split or native compatibility. Nothing downloaded was executed; no package installed.

The first admission and exact method/registry fingerprints remain in history. The current inspector adds
explicit malformed-row warnings without repairing records. All 47 pins match in the network-disabled cached
replay; a fresh empty-directory naval HTTPS download reproduces its pin. All 25 prior pin groups remain
semantically unchanged. The focused fetch module passes 24 tests; the broader local suite stops at missing
TE-cache prerequisites in this separate worktree, so no local full-suite pass is claimed. Existing matrix
code/runner/registry bindings still match; missing optional source caches remain explicitly unverified here.
Exact-head CI is a separate publication check. No new task score, matrix cell, feature pass, plant acceptance
or completed CAD qualification is added by this acquisition.

## 181. Acquire maintenance-linked events, catalog revisions and additional engineering sources

2026-11-07. Continued the user's public-data request with 29 original files, 103,450,866 bytes in ten download
groups: four date-selected TiNA mining-machine partitions and notices, all five files of the current BMS alarm
deposit plus companion notices, two QTE MRO catalog revisions, NASA-hosted milling/C-MAPSS archives, three
EPANET networks and notices, three FreeCAD tutorial originals plus README, USDA/NRCS pumping guidance,
Phoenix pump-nameplate guidance and a historic motor-plate photograph. The three acquisition passes now total
130 files, 421,405,519 bytes in 39 groups, plus four separately frozen DXFs. Dates, revisions and download
groups are not independent plants. Original source files stay local; public pins/primary metadata retain
attribution, source families, rights/exposure limits and actual selection/transport outcomes.

The Mendeley version endpoint returned 404; the working dataset API explicitly returned version 7, which was
pinned rather than assuming the initially browsed version 1. Its two English-named CSVs actually have 35,233
and 36,016 rows, Vietnamese/empty headers and a 12-to-16-column change. This is a catalog, not a linked
installed-equipment/parts-consumption/repair-outcome register; the publisher's million-item title is not the
unique row count of these files. The BMS concept DOI resolves to a newer five-file version, including rejected
ambiguous series, despite the companion README saying four. All publisher checksums supplied match.

All 29 raw pins match in a network-refused cached replay with zero budget and zero network calls. A separate
fresh HTTPS fetch reproduces all five EPANET file pins (56,872 bytes); truncation and same-size mutation controls
are refused. All 40 prior pin groups and the evaluated common fetch/extract/previous-admission methods remain
unchanged. Focused fetch and ledger modules pass 24 and 11 tests. The broader local prerequisite check stops
before running tests because this isolated worktree lacks TE caches; no local full-suite pass is inferred.

No new package was installed or downloaded code executed. Parquet framing/footer checks do not read rows or
labels; outer NASA ZIP inventories leave their nested archives unopened. USDA text extraction yields 208 page
segments and Phoenix one, without diagram/transcription review. The JPG reader's explicit unsupported result
with OCR off remains visible. The 5,038,942,729-byte capacitor archive was excluded after HEAD, not partly
downloaded and called usable. No repository-wide FreeCAD example-data license was found; NASA contributor,
vendor and third-party figure rights are not assumed. These originals stay local; CAD XML/geometry/thumbnails
remain uninspected and outside the existing frozen DXF cohort. No task score, model training, generalization
cell, feature-review pass, plant acceptance or CAD qualification result is added by this acquisition.

## 182. Acquire a predeclared linked public maintenance cohort

2026-11-07. Filled a specific gap left by the category-wide acquisitions: asset, work-order, parts-transaction,
transaction-detail and labor records from one public source system. NYC Parks AMPS is municipal maintenance,
not an industrial plant trial. Selection and field projections were committed before row download: every
work order with `2024-01-01 <= evt_date < 2024-01-08`, regardless of completion or other outcomes, and its
documented related records. The 53 original projected API responses/full metadata files total 2,366,010 bytes:
1,612 work orders, 933 referenced assets, 208 transactions, 263 transaction lines and 5,268 labor entries.
Originals remain local; public records contain pins, queries, selected schemas, aggregate coverage and provenance.
Across four passes: 183 files, 423,771,529 bytes in 40 download groups, plus four separately frozen DXFs.

The first acquisition stopped on HTTP 503 at transaction batch 010; an unchanged retry stopped at asset batch
005. Both incomplete receipts and the original recipe/selection remain in history. Bounded recovery reused
only exact-query responses with matching raw bytes/hash/role, requesting missing queries with finite retries.
No dates, fields, predicates, sorting, ceilings or outcomes were changed to improve coverage. Python 3.14's
initial catalog TLS verification failed; verified system-TLS curl and then working Python 3.13 HTTPS were used,
without disabling certificate checks. Sequential live reads do not establish a transactional/historical snapshot.

All four publisher-described relationships resolve uniquely, with unique/nonempty checked row identifiers and
no unexpected projected columns in this cohort. The transaction-to-work-order link requires the EVNT namespace;
an identical code in another namespace is refused by a fictional control. All 53 raw pins match in the cached
replay with network fetch replaced by refusal, zero calls and zero budget. A separate fresh HTTPS work-order
query reproduces its 653,046-byte pin. Truncation and same-size mutation refuse. Ten fictional controls retain
missing assets as coverage gaps, reject ambiguous keys, foreign parents/entities, outside dates, unexpected
columns and an empty cohort. All 50 prior source pin groups, metadata and five existing method files are unchanged;
acquisition/selection/history/metadata bindings match. CI runs the tiny no-download relationship controls.

There are 1,547 nonempty completion values; the other 65 are missing values at acquisition, not automatically
open/overdue/failed work. Nonempty reopened/correction fields are not interpreted as true flags. Parts movements
may include returns/corrections; cost, hours, units and codes remain uninterpreted pending the source guide and
dictionary. No dataset licenseId was supplied; local records are not republished or assumed public domain.
No package was installed or downloaded code executed. Focused fetch and ledger modules pass 24 and 11 tests;
the isolated Python environment/full-cache prerequisite check stops before running the full suite. Exact-head CI
remains a separate publication check. No model score, verified repair effectiveness, industrial transfer,
new matrix/feature-review result, changed CAD cohort or completed CAD qualification is inferred.

## 183. Preserve DXF value edits and retain the unfinished native qualification gates

2026-11-07. Followed the user's explicit CAD goal with a protocol before development, exact frozen inputs and
methods before reserved execution, and matched library/value-span/native routes. The source-preserving patcher
changes only explicit single-line ATTRIB value bodies; a separate offset-free source/plan reconstruction checks
the result. The original strict comparator and its exclusions are unchanged. This is record-framed DXF with
explicit ICT_ID/TAG, not DWG, a proprietary intelligent-P&ID database or inferred plant connectivity.

Round 1 retains an R12 inspector failure, a literal-brace plain-text harness error, three public-profile refusals,
one public parser failure, native full-save differences and unreadable native images. Its methods/raw results
remain committed. These cases became exposed development/regression. Six replacement authored configurations
and six public originals were committed at d79e437 before the R12 inspection correction. Method 2 was committed
at 8fdc775 before replacement runs. The inspector now projects loaded pre-R2000 records through the R2000 tag
exporter without upgrading source bytes or dropping virtual records. The patcher, comparator and independent
byte checker remain identical to method 1. Twenty-eight CAD tests pass, including planted loss/refusal controls.

All six untouched replacement public files refuse the required asset profile. Their frozen adaptation adds
clearly authored test identifiers/annotations and an unused attribute without overwriting existing values.
The derived manifest was separately bound/committed at 07fd3d3 before candidate execution. All six remain in the
cohort. One ezdxf family is not six independent plants, and the adaptation's library save is not byte preservation
from the untouched original. Previously acquired CAD originals outside this cohort were not silently added.

All 21 candidates (nine exposed, six replacement authored, six public-adapted) pass unchanged strict comparison
with zero unexpected differences and exact byte reconstruction. All 21 library saves fail raw reconstruction;
R12 and nested-dimension strict differences remain visible. QCAD Professional trial 3.33.1 Qt5 native API reads
the candidate values and retained foreign attributes correctly. All 42 native default/R15 full-save returns
still have strict differences; the original valve's 335/344 baseline differences remain failures. Forty-five
new-process stored-value readbacks match (nine development candidates plus 36 replacement returns/candidates).
API fresh-process readback is not an observed native UI edit/save/close/reopen.

The first native development driver's result summarization used a wrong comparison key and exited 1; raw
files/receipts and failed summary remain. Corrected postprocessing checks those files without fabricating a
successful original driver. Fictional revision controls reject two stale proposals without output, retain one
concurrent MODEL conflict, and require a second explicit source-bound plan. Three graph/revision commands pass;
original and selected DXF sources remain exact draft context, not an installed register or authenticated decision.

The first 60 native images have clipped/low-contrast labels and missing Cyrillic glyphs. Display-only diagnostics
were frozen separately and retain all attempts: txt-to-Arial has no RGB effect; native probes identify Standard.
The later Standard-to-Arial/monochrome/native-union-bounds recipe produces 82 images: 12 model, 23 asset-label and
six paper-layout pairs. All commands exit zero and input hashes remain exact. Inspection of all seven contact
sheets plus two final full-resolution candidates and an earlier Cyrillic pilot pair finds readable selected
changed labels, but trial marks obscure others. Five paper pairs have no useful drawing content; the sixth has
viewport examples. All six paper pairs are RGB-identical. No complete readable visual or original-font fidelity
pass is claimed. These already exposed display diagnostics are not new blinded preservation validation.

An offline archive retains 1,189 exact records, 76,110,864 raw bytes, compressed to 11,358,590 bytes, excluding
native software/settings/fonts. The first packaging attempt stopped on an INI file and remains local; its initial
offline replay consequently failed on missing inventory. A control run exposed an unstable informational
save_metadata_changed flag: ezdxf replaces zero creation dates with now during read. A delayed-read diagnostic,
initial successful replay and pre-diagnostic code are retained. The replay now compares every strict field exactly
and reports both informational flags; no strict rule or source byte changes. The final offline replay rebuilds
all 21 exact candidates, re-scores all 63 native comparisons, checks all 45 saved readbacks and revision controls
with zero errors. Four altered/omitted evidence/native-value controls refuse as intended. CI runs the replay and
controls without model/native calls; exact-head CI and the full repository suite remain publication gates.

The Windows app still shows startup/trial-expiry dialogs through accessibility text. Two fresh exact-window
captures time out; no successful drawing interaction was observed. Full CAD qualification therefore remains
unfinished, with readable complete visual review and actual native UI editing/reopen outstanding. No plant data,
operator review, measured human effort, platform import or company/engineering acceptance is established.

## 184. Diagnose blank native layouts without rewriting the qualification sources

2026-11-07. Continued the CAD goal after merging the preservation evidence in PR20, retaining the original
acceptance criteria, frozen methods, source bytes and strict failures. A read-only native block/layout probe
and display plan were committed at bbd53c2 before execution on all 12 replacement source/candidate pairs.
All 24 raw input hashes remain exact. The five authored Qualification sheet layouts contain one display viewport
each in their sources/candidates, but QCAD Professional trial 3.33.1 Qt5 exposes empty imported layout blocks.
Both retained native save formats have different paper/main viewport settings instead of those original display
settings. These are genuine layout-information losses, not just informational metadata differences or blank sources.

Six hypotheses on the already exposed cp1251 source were declared at c25c4b8 and exact working copies bound at
6efea49 before native import: original bytes, library save, add main viewport, add main and restore the original
current handle, change current handle only, and activate the layout only. Both added-main variants expose one
display viewport with original bounds [15, 5, 115, 75]; the other four expose none. A separate rendering recipe
was committed at 3143237 before all ten new native images. Direct inspection of all six paper images shows the
drawing only in the two added-main variants. Their RGB pixels are identical; the other four are identical to the
blank original render. This isolates a main-viewport compatibility dependency among tested revisions of one
exposed drawing. It is not independent validation, proof of a universal CAD rule or a qualified automatic repair.
The primary ezdxf layout-internals and API documentation differ about whether a main viewport is required.
No working copy replaces the original frozen source/generator or changes a preservation result.

The four other images test equal-scale translated long-label source/candidate windows. Every native command
exits zero, retaining input hashes and trial marks. All four were directly inspected: the mark still overlaps
the text at both positions; pre-substitution bounds also do not prove complete substituted-glyph containment.
The long candidate reaches the right frame edge. This recipe remains failed and is not expanded into an
unnecessary full-cohort batch. No mark was removed, masked or suppressed and no output pixels were edited.

The UI attempt sent Return to the observed expired dialog; the old window subsequently disappeared. Launching
the same pre-existing app yielded a fresh native window. Two capture attempts still report window capture timed
out: timed out waiting on channel. Return/raising the new startup dialog does not dismiss it or move the reported
focus from General Properties Handle. Two clicks using freshly observed startup button 6 fail with element 6
is not available in cached app state for qcad.exe. No drawing interaction, edit/save/close/reopen, screenshot,
license change, authentication/security change or company acceptance is claimed. Bounded recovery stops here.

The separate 191,869-byte archive retains 36 exact records (839,158 raw bytes), including all commands/logs,
probe receipts, comparison fields and ten PNGs; native settings/software/fonts are excluded. Its offline check
verifies both archives, all frozen methods/inputs, 12 retained source/candidate/native viewport comparisons,
five losses, six hypothesis outcomes and ten original image pins. An omitted-variant control refuses. Existing
strict comparison/value patcher/byte checker are unchanged. Full native visual/UI qualification remains unfinished;
the new diagnostic is evidence of a failure mechanism, not a new feature or accuracy/generalization pass.

## 185. Acquire industrial batches, alarms and engineering exchange references

The next public-source selection and publisher metadata were committed at 89b3dfe before the declared file
acquisition. All 35 files succeeded: 196,525,541 bytes in nine groups. Five passes now total 218 originals,
620,297,070 bytes in 49 download groups, plus the four separately frozen DXFs. Groups, shuffled representations,
revisions and related systems are not independent plants. No downloaded code, model, solver or CAD application
ran for this acquisition, and no archive was extracted.

The industrial yeast deposit supplies 59 batch metadata rows and 1,090 repeated time-series measurements; its
publisher says only ten batches have the rich process variables and withholds the original operator PDF logs.
ALPI supplies actual industrial packaging alarms, with raw/processed material separately named inside an unopened
archive. Synthetic maintenance/tag Parquet files remain explicitly synthetic and framing-only. UCI quality and
power CSVs supply 1,941 and 9,568 rows respectively, with correct observed widths; power rows are shuffled and
have no timestamps. The IDTA JSON/AASX templates, BioSTEAM system definitions and KSB nameplate photo are
source preparation, not installed records or ready adapters. Photo OCR was off and its unsupported result remains.

NIST CTC drawings and three complete definition/STEP/native-model archives deepen CAD/PMI reference coverage.
Their archive directories are inventoried, while CAD/STEP/geometry/PMI contents remain unopened. These are
mechanical test cases, outside the current ASCII DXF qualification; no frozen CAD inputs, methods, comparison,
failure result or gate changed. The standalone PDFs yielded unreviewed text, not verified graphical annotations.
NIST HEAD requests returned 403 but the predeclared ordinary HTTPS GETs succeeded. ALPI's Python certificate
chain failed; verified Windows curl/Schannel obtained the originals without disabling TLS verification.

All acquired byte/SHA-256 pins match; publisher MD5/SHA-1/LFS pins were checked when supplied. Cached replay
checks all nine groups with zero network calls/fetched bytes. All 18 truncation/same-size mutation controls
refuse. A separate fresh HTTPS acquisition of all five yeast files matches. All 51 prior pin groups and ten
recorded common/CAD methods remain unchanged. The fifth-pass guide links sources, rights and useful next tasks;
its acquisition, admission, verification, selection and baseline are retained.

IRIS-v2 is recorded as an unacquired research lead because CC BY-NC-ND terms do not supply commercial/derivative
example rights. Two CSB pages were unavailable; no reports obtained or counted. Real industrial linked repair
outcomes, reviewed P&ID revisions, native GUI acceptance and customer environment acceptance remain open.
No accuracy, training split, workflow-matrix cell, feature review, reader leaderboard or time-saving claim changes.

Focused fetch and extraction modules pass 24 and 63 tests. Ledger, feature catalog, published-claim bindings,
corpus matrix, reader leaderboard and script index checks pass; published claims match evidence files, without
rerunning models. Changed local documentation links resolve, and all previous pin values compare unchanged.

## 186. Trace native record correspondence without waiving the strict failures

The previous goal turn acquired public sources (PR 22), concrete progress without closing CAD qualification.
This continuation returns to the original protocol. Fresh Computer Use inventories return the same live QCAD
window 429395364 with trial-expiry/startup dialogs, no document and disabled Save. Two captures time out with
window capture timed out: timed out waiting on channel, including fresh window selection before recovery.
Two freshly observed indexed clicks on expiry OK 208 fail with element 208 is not available in cached app state
for qcad.exe. A final text refresh still shows the modal/live window. No restart solely on timeout, screenshot,
drawing interaction, UI-saved return, license, authentication, privacy or security change is claimed.

Plan and 39 authored decoded-graph controls were committed at e62e8d1 before implementing the correspondence
diagnostic. Its matcher, separately coded direct checker, runner and inputs were frozen at e89ad4b before
running the full exposed round-2 cohort. Both software checks are agent-authored; neither is independent
engineering review. Every unique ordered literal body must match, with only own handles and declared pointer
values renamed; the complete reference subset must close. Duplicate bodies, dangling/ambiguous dependencies,
literal XDATA/arbitrary handles, missing/explicit defaults, geometry/style/foreign/unknown changes stay unpaired.
No geometry-nearest match, numeric tolerance, default expansion or comparator exclusion was added.

All 21 candidates remain strict zero. All 42 native returns retain their strict failures and all 16,209 rows,
with separate before/after-side correspondence at every original index. Default saves have 558 unique-body
seeds and 307 closed pairs; R15 has 509 seeds and 276 pairs. Counts aggregate related record occurrences, not
independent plant observations. Even exact candidate controls leave 1,719 before-side records unpaired under
this deliberately conservative unique/reference rule. Unpaired means not proved here, not automatically lost.

The original valve's default return retains 335 differences and thirteen matching table-related records
(nine TABLE, two LTYPE, one STYLE, one APPID). Its R15 return retains 344 and fourteen. Direct tracing of the
same MODEL handle 3E confirms the planned value, plus removal of explicit alignment codes 11/21/31 and addition
of style name textstyle3/code 280 zero. ICT_ID shows the same non-value changes. These go beyond handle
renaming; their visual/engineering effect is not dismissed as harmless defaults.

All 39 controls pass their predeclared pair/strict oracles. The 1,140,924-byte archive retains 64 reports/summary
records (13,008,195 raw bytes), bound to the prior source/return/plan/comparison hashes. Offline replay rebuilds
all 63 results exactly and directly checks every positive pair, all strict indexes/sides and complete cohort
coverage. Fabricated-pair and omitted-report controls refuse. This diagnostic is added to CI; strict comparator,
raw patcher, byte checker, frozen sources and prior results remain unchanged. Actual readable native visuals,
observed UI edit/save/close/reopen and engineering/company acceptance remain unproved. No qualification gain,
new held-out claim, accuracy score or source-preservation method change is inferred.

The unchanged CAD regression module passes 28 tests. Ledger (339 attempts/116 ideas), feature catalog
(22 reviewed of 30, CAD still needs review), matrix bindings, reader leaderboard and 152-script index checks
pass. Diagnostic freeze hashes and all recorded original qualification methods compare exact; new guide links
resolve. Full repository CI remains the separate integration gate for this change.

Before creating the PR, a Git warning prompted actual blob/working-byte comparison: artifact commit 7a637a1
stored a 1,140,911-byte ZIP, while the original remained 1,140,924 bytes with its inventory hash. The general
CAD text rule normalized thirteen CRLF sequences. A binary ZIP override and forced re-add restore the original
bytes; no report, oracle, method or result changes. Both hashes/sizes and the failed commit are retained in the
checkout recovery record. The staged/committed ZIP is checked against its pin before publication.

## 187. Separate equipment-data exchange from native CAD drafting

Steve challenged why a native CAD UI should block the work and requested new designs. The UI gate proves
interactive behavior in a receiving editor; it is not necessary for a source-preserving equipment-data operation.
The original protocol and every native failure remain records. A separate predeclared contract selects immutable
DXF plus source-bound attribute sidecar/form. Native-return-as-proposals is deferred because it needs an explicit
contract for other intentional edits; generating a new drawing is a different existing route, not preservation.

Commit 179c32d freezes acceptance and six fresh same-author procedural sources/keys before implementation.
da9f427 freezes the exchange implementation, controls and runner before execution. The first attempt produces
one strict-zero R12 sidecar edit, then stops when the protective library wrapper correctly refuses its baseline.
The failure receipt discloses that private temporary artifacts were cleaned, not recovered. 0915eaf corrects
only baseline capture to retain raw saves; no exchange tool, comparator, writer, input or key changes. Case 1 is
exposed; all six are software/development validation, not independent plants or blind model tests.

All six complete cases, nine assets and ten edits have zero unexpected strict differences and independent
source-plus-plan reconstruction passes. R12 through R2018, LF/CRLF, cp1251/UTF-8, transformed/multiple blocks,
paper viewport/label, foreign fields and XDATA are covered. The matched library saves all fail raw reconstruction;
R12 has 77 strict rows and five others have zero decoded strict rows. Complete candidates, library baselines,
comparisons, responses and source/key hashes are retained. No native full-save failure is resolved by this design.

The reusable prepare/apply tool regenerates the complete catalog from the current source, validates source and
catalog bindings and explicit before/after/reason fields, then uses the unchanged value-span writer. It retains
exact original returned JSON bytes as well as normalized proposal, source, catalog, plan, candidate and sourced
draft context. Existing destinations, malformed/extra/duplicate/unknown/identity/foreign edits, stale and competing
revisions, binary/unprofiled input, multiline and overlong values refuse. Nine focused tests also exercise actual
CLI application and geometry/layer/foreign/XDATA loss through the strict and separate byte checks.

An actual local browser form downloads three proposed valve edits; that exact download goes through the CLI,
independent reconstruction and a freshly prepared form showing SRC-3, AV-88412 and DN65. Empty/missing-reason
forms refuse. Identity/foreign fields are read-only. A second authored form preserves hostile script-closing text
literally without image creation or execution; a 190-character changed value downloads/applies correctly. At
390/1200 pixels there is no horizontal page overflow. A mobile screenshot was directly inspected. Instrumented
case-6 reload/download requests only its loopback HTML. No CAD geometry/layout appearance was tested by this form.

The connector blocks file: navigation; the following field lookup therefore times out on the earlier page.
Tab close succeeds but explicit new-tab creation fails and a following lookup times out. Ordinary browser
navigation then creates/reopens the candidate form successfully. These tool failures remain in the browser receipt;
the documented verified route is loopback HTTP. No authentication/license/permission change, CAD UI or plant access.

Five actual existing projection/build/change CLIs carry the response to the same fictional valve map position.
Only proposed cad_model/cad_serial/cad_size and source revision change; no installed authority or pipe links are
inferred. The map report and command receipt are retained. Existing 21 source-preserving candidates, 42 native
failures and frozen method bindings remain unchanged. The original native UI/visual/full-save qualification is
still incomplete; the separate bounded metadata exchange is useful without it.

Offline checking reconstructs all six candidates, re-scores retained baselines, regenerates the sample form and
replays both downloaded browser responses against saved returned files. It does not launch a browser or native
CAD. Method-binding/evidence checks were extended after execution without changing the exchange implementation.
The agent guide, supported workflows, status, script and feature catalogs now route this job to the new tool;
CAD still has no independent engineering review. Exact-head CI remains the integration gate.

## 188. Observe native CAD as a receiving check beside source-preserving data exchange

The sidecar route separates metadata entry from CAD resaving; it does not answer whether a recipient can use
the drawing. The pre-execution Linux native plan (`681b33a`) retained that distinction and the full original
qualification gates. Windows capture still failed. An isolated Ubuntu/X11 desktop ran the publisher's pinned
QCAD Professional trial 3.33.1 Qt5 package without changing licensing/security settings or redistributing CAD
software/fonts. The package hash, base/image identities, installed versions and GUI recipes are retained.

On the exposed fictional valve, actual native property controls changed MODEL, SERIAL and SIZE. Native Save As
used its default R27 [2013] DXF. The document closed and reopened; six labeled fields showed planned and unchanged
values and enabled/editable states. A temporary foreign-field edit was visible, then undone and discarded on
Quit. The saved returned DXF remained byte-identical. The app exited normally; a fresh container/native process
opened the retained return and showed the same values. These are Linux UI observations, not native edit/export
API calls, Windows acceptance, independent review or a fresh holdout.

The exact returned file still has **287 strict differences**, including AC1015-to-AC1027 conversion and header,
style/record/layout changes. The unchanged receiving reviewer and conservative correspondence diagnostic retain
every row: 71 source records, 232 returned records, 20 unique-body seeds and 13 closed pairs; the others remain
unpaired, not automatically lost or harmless. The native save is not imported as a preservation pass.

The unchanged value-span candidate has zero unexpected strict differences and passes separate raw reconstruction.
It opens natively with readable valve labels and editable fields. Same-session source/candidate canvas comparison
finds 425 differing pixels within the three changed label area. This exposed diagnostic is not a new frozen visual
equivalence scorer. All 21 previously exposed sources/candidates have native model views; six paper pairs add
12 views. Native input hashes remain unchanged. Five authored paper pairs stay blank. The rotated Cyrillic zoom
does not establish readable canvas glyphs despite correct Unicode in the property field.

The public Layout1 source/candidate pair differs at 13,556 canvas pixels. Two subsequent native opens of the
**same exact original** reproduce those two states: repeat 1 equals the candidate view, repeat 2 equals the
first original view. This rules out attributing that pixel difference to changed candidate bytes. The underlying
receiver/view-state cause remains unresolved. No whole-cohort layout/font pass is claimed.

Failures remain: initial image build on an occupied UID1000; stale X99 lock after same-container restart;
title clicks causing maximization; two accidentally overlapping capture batches (explicitly excluded); early
typing leaving a path suffix in a file dialog; and the first offline replay matching an Attributes popup menu
instead of the actual labeled panel. Corrected capture recipes were committed before their new runs. Completed
GUI batches were then run serially in fresh destinations. The initial impression of missing white linework was
disproved by direct RGB comparison of the checked region, not published as a CAD-loss result.

The first 75.7 MB ZIP is retained locally. A 31.0 MB lossless solid-compressed archive retains the same **842 exact
logical records / 104,277,450 raw bytes**, including failed attempts; all member pins match the initial ZIP.
No CAD executable, font binary, application settings, DBus address or autosave is published. Manual action notes
are explicitly transcribed tool observations, not a continuous event recording. Actual screenshots, native
accessibility output, returned DXF, GUI commands, logs and image frames are separate bound evidence.

Offline replay reconstructs every candidate and retained strict/review/correspondence result, checks exact labeled
native fields and 54 view records, and recomputes the pixel/repeat controls. Five semantic receiving controls reject
stale values, foreign loss, disabled editability, swapped fields and omitted coverage. Separate archive tests reject
traversal, alternate-stream paths, links and omitted members. This runs in the CAD test module without a desktop,
network, Docker or commercial CAD. It verifies retained observations; it does not rerun the native GUI.

Initially adding the two new checks to the original CAD test file triggered its frozen-method binding refusal
before native evidence was scored. That attempted source and failure are retained in Git. The original 28-test
file was restored from its prior commit without changing any freeze; the two new checks now live in the separate
`test_cad_linux_evidence.py` module registered in full mode.

The broad goal remains active: complete readable visual/font acceptance, receiver-state diagnosis and fresh native
validation remain. The useful metadata route, one actual Linux UI sequence and full-save failures are reported
separately. Original protocols, methods, sources, keys and earlier failures remain unchanged; no plant/company
authority, engineering release or timed human benefit is inferred.


## 189. Isolate pointer highlighting before comparing native CAD views

The exposed public paper mismatch now has a bounded explanation. A precommitted plan and
recipe used the same pinned Linux native receiver in a fresh container, copying the prior
terminal-exit configuration locally before startup. Native source/source/candidate openings
ran serially without saving. Seven observed pointer states per opening retain 21 final
screenshots and 42 stable frames. Exact input hashes remain unchanged; native Ctrl+Q and
Docker wait report normal application exit 0. Configuration and licensed binaries remain local.

The initial canvas state matches the old first exact-source repeat exactly. Deliberately
hovering the elliptic viewport matches the old second repeat exactly. Moving through empty
canvas before moving outside removes the highlight: all nine neutral views are identical.
The two old regions account for all 13,556 pixels (6,788 concave + 6,768 elliptic). Explicit
hover over concave text gives a separate 1,076-pixel state, retained rather than mislabelled
as the whole viewport. This was a transient observation-state difference, not evidence of
changed DXF content. QCAD's matching public source changes highlighted display paths' colors;
that source lead preceded the actual control and does not substitute for it.

The 73 exact records are retained in a 2,224,420-byte lossless archive with per-member pins.
An offline successor checker independently decodes frames and replays the full canvas
comparisons against the earlier archive. Five planted receiving errors refuse: changed
pixel, wrong hover state, abnormal exit, omitted case and changed input identity. The new
check is in the separate unfrozen Linux evidence test module; original frozen CAD tests,
comparison, patcher, raw checker and every earlier source/result remain unchanged.

This is development on one exposed drawing in a reused configuration, not fresh validation.
The changed metadata anchor is outside this paper view, so zero paper differences prove no
visible changed-value coverage. Complete readable layouts/fonts, five known original layout
failures, native full-save preservation and fresh native validation remain open. Next work
needs a separately frozen pointer-neutral observation method and reserved inputs, not an
upgrade of these repeated observations to independent qualification or company acceptance.

## 190. Measure native text after the declared display font is active

The next precommitted development plan compares the pinned Linux native receiver's default
font with process-local Standard-to-DejaVu Sans substitution, using three already exposed
authored source/candidate pairs. The API reads native values/font/bounds, activates GUI
documents and positions a common camera; it never edits or saves. Bounds are measured after
the profile starts, united across both versions and padded before each source/candidate pair.
This avoids the earlier use of pre-substitution bounds. The equipment-data agent/local-form
route remains usable without a CAD UI; native delivery checks are a separate obligation.

The original complete batch traversed below the actual canvas; its 18 views/36 frames remain
retained. A correction was committed before repeating. The agent then mistakenly sent Quit
while the corrected capture was live; that process later exited 1, with 14 final views and
28 frames but no completed actions receipt. The interruption was recorded before a fresh
container repeat. Both accepted batches separately reported capture exit 0 before Quit;
the default native process exited normally before the substituted process started. All
359 exact records, including failures, are retained in a 13,612,032-byte lossless archive.
Action notes are transcriptions; actual images, native receipts, per-command captures,
logs and terminal container states are retained separately. No binary/font/settings release.

The accepted matched batches retain 36 views and 144 unique native attribute observations.
All exact field values, including foreign values, match source/candidate snapshots. All
three candidates rebuild with strict zero and independent raw reconstruction zero. Default
Standard.cxf lacks 13 required Cyrillic characters; its native views show question marks.
Mapped native probes resolve DejaVu Sans with Qt coverage of all supplied characters.
Direct assistant inspection of every accepted view finds complete target labels in the
mapped asset views, including Cyrillic, mixed Unicode and both long strings. Overview
labels are too small for character review. Source rotation and some linework/label overlap
remain. The mapping changes typography; intended original-font fidelity is unproved.

All nine mapped source/candidate canvas pairs change pixels only within exact unexpanded
native MODEL bounds. The default long overview has 62 pixels outside its exact MODEL bounds;
a two-pixel expansion contains them, but this is an exposed diagnostic, not an acceptance
tolerance or explanation. The 62 remain unresolved. Full raw pixel totals for all 18 pairs
remain published, with exact and expanded counts. No image was altered to obtain agreement.

The offline checker independently decodes stable frames, recomputes cameras/projections and
all pixel diagnostics, and rejects seven semantic corruptions: planned value, foreign loss,
missing glyph, clipped camera, wrong document, unplanned pixel and omitted view. All four
successor evidence tests pass locally; original frozen CAD tests remain untouched. Offline
replay verifies saved observations, not new native execution or engineering acceptance.
Five original paper-layout failures, native full-save preservation, original typography,
general preparation and separately frozen fresh native validation remain open. These exposed
fixes do not make new holdouts, and the full goal remains active.

## 191. Propose a minimal paper-layout source revision

The precommitted [plan](../examples/cad-handoff/qualification/LAYOUT-PREPARATION-10-PLAN.md)
tests a different design: retain every original CAD record byte and serialize only a newly
proposed main viewport plus HEADER HANDSEED. The source is never library-saved. The rule uses
layout structure and paper settings, not case names. A separate verifier discovers the new
record and reconstructs the exact original without producer offsets/receipts. This is an
explicit proposed source revision, requiring adoption before any new-source attribute plan;
it does not reclassify the original failing file as a preservation pass.

Across all 21 exposed cases, five need a main viewport, 14 remain exact no-ops and two R12
inputs refuse this preparation. Existing R12 metadata exchange remains separate. Five
matched routes per known failure retain original, library save, library add-main with old
current reference restored, minimal preparation and planned attributes on preparation.
The frozen patcher and independent original byte checker give strict0/raw0 on all five
prepared-to-candidate pairs. Seventeen wrong-data/ownership/order/identity/input controls
refuse; an already prepared source is an exact no-op. All strict original-to-route differences
remain visible, including each deliberately added viewport and candidate attribute edits.

The [retained native evidence](../examples/cad-handoff/qualification/layout-preparation-10/README.md)
contains 25 verified-profile paper images and 330 exact native field observations. All five
minimal-preparation paper images are pixel-identical to the library add-main baselines.
Original/library-only layouts stay blank; add-main/prepared/candidate imports expose the
original display viewport bounds and visible source geometry. Direct assistant inspection
of the 25 second-batch images, full decoded RGB identity of all 25 fourth-batch images and
five directly reopened fourth-batch views retain trial marks overlapping content and original foreign/Unicode labels
clipped at the original top viewport edge. This restores display structure; it does not
establish complete readable sheets, original typography or engineering acceptance.

Two earlier wrapper failures remain in Git/evidence. The first native batch started after
a failed configuration copy because PowerShell continued; it was allowed to finish and is
excluded from the declared-profile conclusion. A separately committed fail-closed setup
correction verifies the local and installed configuration hash before any CAD process. The
second batch started after confirmed normal first-container exit and all 26 serial commands
exit0, but later stderr inspection found its command selected a different file from the one
installed. It too is excluded from the intended-settings conclusion; initial claims and
HOST-NOTES are retained and explicitly superseded. A separately committed correction uses
the installed absolute path and a native settings-filename self-report before the frozen probe.
The next creation omitted the image entrypoint override: the desktop launched instead of the
evidence driver. The diagnosis was retained before intentionally stopping that unintended
process (container137/controller1); no native driver/probe ran and all input bytes stayed exact.
The fourth container is inspected for Python entrypoint/image/user/mount/no ports before start.
The actual native selected path and every-command stderr/digests now bind the receiving profile;
settings are never reset between commands. No new UI edit/save operation occurred.
The unchanged first lossless archive retains 911 exact files, 16,275,721 raw bytes in 152,492
compressed bytes. A supplementary archive retains the failed third and receiving fourth batches: 514 exact files, 8,992,287 raw bytes in 146,256 compressed bytes.
Configuration, fonts and publisher binaries are excluded, with digest-only settings receipts.

The first offline replay fails on an informational save-metadata boolean in the exact-no-op
public paper case. Repeated inspection of identical bytes reproduces a loaded TDCREATE clock
tick; the existing recheck documents the same on-read behavior. The failing checker was
committed before correction. The receiving replay now retains/prints saved and observed
booleans while matching every other comparison field, every strict difference and exact raw
reconstruction. No comparator exclusion, image tolerance, source or failed result changes.
Three receiving controls reject omitted native routes, altered native field observations and an installed-but-unselected settings file.

This remains exposed development. The full goal stays active: complete readable receiving
checks, separately frozen reserved public/independently authored validation and the original
native full-save/editability/revision gates still need a complete audit. UI-free equipment
metadata review remains available; this compatibility experiment adds no routine UI dependency.

Local verification passes the five successor Linux evidence tests, all 28 unchanged frozen
CAD tests and all three checkout byte-contract tests. Ledger (344 attempts), feature catalog
(30 features, 22 reviewed) and script index (153 scripts) are current. These local checks
remain distinct from full-suite/exact-head CI and independent engineering review.

A final read-only cross-audit finds the accepted font-9 logs also selected
`/work/qcad-config`. Their copied profile hash is provenance, not proof of loaded
settings. The [erratum](../examples/cad-handoff/qualification/layout-preparation-10/PROFILE-PROVENANCE-ERRATUM.md)
explicitly narrows that claim without changing any old code, freezes, numerical
results, actual images or font/value observations. The current fourth-batch settings
proof applies only to that batch and cannot retroactively qualify earlier runs.

## 192. Check a consultant return against the markups sent out

The [pre-implementation plan](../examples/PID-MARKUP-REVIEW-PLAN.md), commit `2d90314`,
defines a three-way handoff: exact original, exact markups/instructions sent out and exact
returned revision. A separate authored acceptance key was committed at `89c2845` before
the first execution. Existing map revision reports and CAD receiving checks did not compare
an annotation inventory against supplied before/after conditions. The new reusable
[markup-review tool](PID_MARKUP_REVIEW.md) fills that local comparison step without requiring
a full graph, MCP service or CAD UI. It does not read arbitrary drawings or discover markups.

An engineer or approved assistant supplies all annotation interpretations and page/region-bound
original/returned observations. Known Boolean symbol presence and typed directed connections
are distinct from attribute/note values. Missing observations never imply absence; unknown
and conflicting readings, uncertain sheet identity and wrong-baseline requests remain open.
Exact document/reading/request hashes refuse stale evidence. Explicit negatives need a
reviewed-region reason. Every markup, other observed change and other coverage gap reaches
the CSV queue; safety-priority markups remain first even when supported. No row releases a drawing.

The [fictional water-transfer case](../examples/pid-markup-review/README.md) contains seven
markups. The first real CLI run matches the prior key: one supported, two not supported,
one partial, two unverifiable and one original/baseline mismatch. The added bypass valve
exists but its outlet stops short of the tank. Both instrument tags exist but their requested
signal is absent. An unrequested FC-to-FO fail-action change and one missing material reading
are retained separately. A corrected later return supports five requests while keeping the
illegible and wrong-baseline rows open; the earlier packet stays intact. Observations were
authored from the same fictional design, not independently read by a model or real engineer.
This is software behavior, not measured drawing-reading accuracy or a consultant quality study.

Nine source-only regression tests cover these outcomes plus missing absence evidence,
reversed signal direction, conflicting readings, uncertain identity, stale sources/observations,
wrong locators/roles, duplicate sheets, exact typed values, conflicting requests, path escape,
output collision, escaped HTML, portable replay and receipt hashes. Actual Edge browser
inspection followed connector timeouts. It found source labels inside the SVG frame and
seven markup headings; desktop1500/mobile420 both have viewport-equal scroll width. Readable
field/status names, stacked mobile cells and explicit source-flow arrows improve presentation
without changing the key outcomes. Preview dependencies stay outside project requirements.

The manager/agent selectors and consulting starting jobs now surface this specific recurring
job. Company document access and accepted decisions remain with the organization. No source
fetching, automatic PDF/handwriting interpretation, full-sheet preservation, CAD editing or
context-map update is implemented. Original CAD qualification methods/results remain unchanged.

## 193. Test public CAD transfer and find a receiving window contract error

The [public transfer plan](../examples/cad-handoff/qualification/PUBLIC-VALIDATION-11-PLAN.md)
and six selected Git paths were committed at `d1885d0` before inspecting their drawing
contents. The existing adapter/writer/strict checker/native methods were frozen at
`02c8fa2`; derived source/plan hashes at `c28959e` preceded candidate execution. The
cohort covers three LibreCAD and three QCAD categories, selected by a fixed filename-hash
rule. These projects share history; six files are not six independent plants. The QCAD
template supplies layers but no original geometry. Every exact upstream Git blob matches.
All untouched sources refuse the ICT_ID/TAG profile. The unchanged adapter authors test
identities and one unused field; preservation starts at those reserialized derived files.

The final prior-catalog/raw-hash audit corrected the pre-run exposure premise: `aw10.dxf`
and `pe3.dxf` already occur in round-1 admission records. The initial all-six-uninspected
claim was overbroad. The [exposure erratum](../examples/cad-handoff/qualification/public-validation-11/EXPOSURE-ERRATUM.json)
classifies four newly inspected sources and two exposed regression originals, retaining
the fixed six-case cohort and every result rather than replacing cases after outcomes.
Offline receiving binds that classification to the exact earlier catalog. Newly inspected
does not prove independent plant provenance or unknown external/model-training exposure.

All six exact candidates pass the unchanged strict comparison and separate source/plan
raw reconstruction. All six matched library-save baselines pass decoded comparison but
fail exact byte preservation. A network-disabled, normal-user container uses the pinned
Qt5 trial image and explicit selected settings file. It imports, edits, exports default
and R15 returns, destroys/reopens documents and reads them again in a separate process.
Seventy-two stored-field observations match in the first process and 72 in the second.
All twelve full saves still fail strict preservation: 346–436 differences. No row is
waived or subtracted, and API readback is not described as actual native UI acceptance.

The first native asset view exposed a receiving-harness bug. Canonical min/max bounds
were passed directly to a bitmap option expecting X/Y/width/height. The installed native
command's own `-help` output and publisher documentation agree. The original 24 images
remain. The [correction](../examples/cad-handoff/qualification/public-validation-11/WINDOW-CORRECTION.md),
frozen at `26b5372`, converts the command argument without changing canonical frames,
drawings, fonts or marks, and writes a separate 24-view batch. This is exposed observation
development, not a blinded validation of the receiving method. The earlier layout-10
frame claim is narrowed; its exact saved images and matched-pixel numbers remain records
of the actual commands. Image-edge clipping cannot be attributed to the source viewport
from the affected images alone. Inherited geometry crosses some authored labels and
trial marks obstruct content, so correct framing does not establish complete readability.

Six exposed second-revision controls add deliberately unfamiliar attributes and XDATA,
reject old-source and wrong-before plans, preserve the new payloads in a separately bound
proposal, and detect changed geometry/foreign/XDATA values with both strict and raw checks.
The first control attempt misused the complete-file parser on a fragment and failed. The
second exited zero but emitted duplicate-handle warnings because it omitted HANDSEED
advancement; its reported booleans are not accepted as a clean pass. Both remain retained.
The corrected third run advances the deliberate revision seed and has no such warnings.
These added payloads are authored controls, not upstream unknown-field preservation evidence.

The [offline receiver](../examples/cad-handoff/qualification/check_public11.py) reconstructs
exact candidates, re-scores full saved comparisons, checks every stored field, settings
chain, input/image identity and frame command, and regenerates the revision/loss controls.
New regression controls reject missing cases, wrong selected settings, changed unfamiliar
values and incorrect bitmap coordinate semantics. Original strict methods and their tests
remain unchanged. Full CAD qualification, readable receiving UI/editability and explained
native full-save differences remain open; no engineering/company acceptance is inferred.

## 194. Separate CAD save reconstruction from operation and receiving defects

The [root-cause plan](../examples/cad-handoff/qualification/root-cause-12/PLAN.md) precedes new native
execution on all six already exposed public-11 derived inputs. Three serial 48-export experiments retain
no-operation, patched-input, edited-input and second-save branches in default/R15 format. Each branch starts
with a newly imported document, closes/reopens its output and is read again in a separate process. Exact
source/candidate/plan hashes, settings selection, terminal container state, warnings and every output remain.

No-operation first saves have exactly the same per-case strict counts as edited saves: 4,650 rows across
twelve source/format pairs. Second no-operation saves have 6,138 rows. A pre-save therefore does not create
a stable preservation baseline. The unchanged conservative correspondence/checker verifies 370 exact closed
decoded pairs on first saves and 936 on second saves; all 10,788 strict rows remain indexed. Unpaired records
are unresolved, not automatically lost or harmless. Added resources, header defaults and literal style changes
are retained beside handle/owner changes. The proprietary reader/writer implementation is not public core code.

Matched returns isolate a separate defect in the historical API edit harness: addObject(a) defaults to using
current attributes and moves the edited ATTRIB to the current layer. A separately frozen intervention uses
addObject(a,false). All six default-format no-operation -> edited comparisons then have zero strict differences
apart from permitted planned text, as do patched/no-operation -> edited comparisons without a plan. All six
R15 pairs retain one DWGPROPS COOKIE XRECORD difference: groups 41/42 equal each saved file's header TDUCREATE
and TDUPDATE values. Those embedded values remain inside the strict boundary. No metadata exclusion, comparator
or original frozen native harness is changed. This is a successor diagnostic method, not retroactive qualification.

The native warnings prompted a beforeLoad=true constructor hypothesis. A third precommitted control keeps the
preserving operation and logs initial/imported objects. It has the same comparison-count vectors and collision
warnings as attempt-2; initial documents still have 60 objects. The hypothesis is rejected. Public pinned core
code explains that import clears before loading and resource initialization is unconditional in either mode.
This source trace is separate from proof of the proprietary plugin or binary build provenance.

Every observed planned and unchanged field matches: 144 per experiment, with 144 more in its fresh process.
All 48 complete property sets match by native parent/tag in each experiment. Literal array ordering differs
between processes because the query iterates a QSet; that ordering statistic is retained separately and does
not relax strict CAD comparisons. The exposed API runs do not substitute for fresh actual native UI acceptance.

The old font-9 62-pixel failure is localized to one yellow candidate-text row at y=537, just above the geometric
top at y=538.0512493261092. Five frozen raster attempts retain an unsupported QPainter constructor, blank
predictions, a successful yellow-device control and impossible inherited-path element counts, then a working
copy of every native path element through supported RPainterPath getters into Qt paths. Twelve nonempty
width/AA/cap profiles and four additional zero-width hairline profiles fail to reproduce the full original
GUI delta exactly. A stroke/raster explanation remains a hypothesis; the original failure and earlier actual
settings-provenance limitation stay open. Successful process exit, image count or device control is not a pass.

The [cause register](../examples/cad-handoff/qualification/root-cause-12/README.md) connects the previous frame,
hover, glyph, viewport, annotation-layout, configuration, control-handle, Git-conversion and exposure problems
to their source records and distinguishes fixes, limited interventions and unknowns. The independent offline
receiver re-scores all branches, verifies exact candidates, native fields/settings, row indices/conservative
pairs and every raster prediction. Planted controls refuse omitted jobs, unplanned layer/geometry changes and
a forged zero-difference claim. Full native preservation, exact residual rendering, complete readable receiving,
fresh UI/revision qualification and engineering/company acceptance remain unestablished.

## 195. Explain the GUI residual with actual native cubic strokes

The [GUI-scene plan](../examples/cad-handoff/qualification/gui-scene-13/PLAN.md) precedes new native execution
on the already exposed font-9 long source/candidate. The ordinary native GUI canvases and camera reproduce
both historical canvases literally, including 1,978 changed pixels and 62 above the MODEL geometric bounds.
Two successful observed GUI runs preserve that literal canvas equality. No source/candidate byte is changed.

Public QCAD core code supplies a concrete method lead: its ordinary renderer can split a text path into
individual lines and cubic strokePath calls. The first working Qt observer captured lines but omitted the
distinct strokePath entry point. Its exact-state replay still disagreed with the GUI delta at 857 pixels;
a pen-setter counterfactual made no difference. All failures remain, including initial C++ lookup compilation,
launcher library resolution and Qt JSON ABI errors. The original native image and software remain unchanged.

An extended separately frozen observer captures the actual cubic calls and explicit pens. Replaying all
1,193 source / 4,909 candidate yellow-stroke calls in the package's actual Qt 5.14.2 reproduces every original
delta pixel and both colors at every original outside pixel. A second observation of the replayer finds
zero state/primitive discrepancies. A declared removal control eliminates all 62 when curves are omitted;
curve-only replay reproduces their exact colors. The cause is native cubic glyph-stroke ink outside a
geometric bounding box, not an unexplained drawing change or evidence that a larger tolerance is acceptable.

The original failed geometric-bound acceptance result is retained. No mask, original strict comparator,
byte patcher, historical native harness or old test is changed. The historical settings file remains
unrecoverable; new selected-profile hashes and actual RSettings reports are retained. Default-launch stderr
does not emit the old explicit settings line, so that part of the initial plan is reported as a deviation;
old/new literal canvas equality is a separate observed control. Native attribute collections compare by
unique tag with every property intact; process-dependent collection order is not strict CAD normalization.

The [offline receiver](../examples/cad-handoff/qualification/check_scene13.py) checks bounded/hash-bound
archive and trace reconstruction, exact input/plan bytes, selected settings/terminal states, complete
primitive streams and all saved image controls. It does not execute native Qt/CAD. Tests retain the original
evidence suite and add full replay, wrong-pen/viewport and outside-pixel refusal controls. Native full-save
differences/unresolved payloads, complete readable receiving, fresh UI/revision qualification and actual
engineering/company acceptance remain open. This is one exposed diagnostic success, not generalization.

## 196. Separate native save ordering from actual metadata omissions

The [save-boundary plan](../examples/cad-handoff/qualification/save-boundaries-14/PLAN.md) precedes native
execution on the six exposed public-adapted sources. Explicit R15/R21/R24 export writes each source's
actual ACADVER, while default export writes AC1024. Source-version matching still fails strict preservation
with 351, 349, 353, 432, 403 and 424 rows. Empty native exports have 252–262 serialized records; all 32/33
new line-type names already exist in the public native document before source import. Named table/dictionary
associations retain every literal payload/reference difference and are not equivalence or deletion rules.

The declared fixed-hash intervention produces zero strict differences between two independently launched
QT_HASH_SEED=0 processes on all six inputs. Each differs from the unseeded return in 53 resource records.
This locates a bounded Qt hash-order repeatability component. Qt documents the seed for testing/debugging;
it is not a recommended production setting, exact native-original preservation or a new comparator waiver.

Paired authored source revisions distinguish registered application names from used XDATA. A native no-edit
save retains the ordered used string/double/integer payload and the asset attributes but omits a named
root-dictionary XRECORD and unused application registrations. The first USERI5 values 60000..60005 were
outside signed 16-bit range and become input-minus-65536 already on import. This was a flawed control,
not valid-data loss. A separately declared/frozen successor uses 6000..6005 and five boundary values
-32768, -1, 0, 1, 32767. All 17 preserve valid integers and tested fields; all 17 still lose the XRECORD
and unused registration. Public object/custom-property observations cannot establish an opaque plugin's
exact import/export loss stage. That implementation remains unavailable, and the stage is left unknown.

Failures remain visible. A PowerShell edit failed, and the next native run mistakenly used a placeholder;
its controller correctly refused zero observed jobs despite native exit zero. The successor probe was
completed and frozen separately, with identical data bytes. An initial empty-document analysis failed
the existing asset-profile guard. Its generic successor then failed offline reproduction because ezdxf
substitutes current time for a zero creation time. The final descriptive helper retains complete original
HEADER bytes instead; both earlier diagnostics remain. No native run was overwritten or restarted.

The [receiver](../examples/cad-handoff/qualification/check_boundaries14.py) verifies exact source provenance,
frozen inputs/methods, byte-preserving candidates, selected configuration, terminal native identities,
all public properties and 65 strict reports from 63 complete exports/fresh imports. It runs offline and
does not execute CAD. Original strict methods and prior tests are unchanged; new controls refuse omitted
jobs, a forged pass and the incomplete probe, and preserve literal zero-time header bytes. All sources
are exposed/authored diagnostics. Full native-save payload preservation, complete readability, fresh
reserved-source native UI/editability/revision qualification and engineering/company acceptance remain open.

## 197. Trace record interpretation through crossed native routes

The [record-path plan](../examples/cad-handoff/qualification/record-paths-15/PLAN.md) precedes new preparation
and execution on six already exposed adapted originals. Each receives five authored XRECORDs; the paired
foreign source changes only the literal QCAD_OBJECTS root dictionary key. Two originals already have
private records; these are retained and their relocation is explicitly part of the intervention. All
twelve source-preserving candidates pass independent raw reconstruction and the original strict comparison.
The experiment crosses explicitly selected OpenDesign/dxflib importers and exporters, recording every
public document variable/object/attribute before and after export, close/reopen and fresh process import.

The observed boundaries differ. dxflib imports private mixed data by overwriting one document variable
per payload item; only the final real remains. The foreign namespace produces no test variables. The
pinned public importer implements that selection/assignment. OpenDesign exposes all three mixed values
as a public array from either nested namespace, retaining it after export. Its file contains an empty
record; the dxflib writer instead leaves a dangling dictionary reference. All twelve OpenDesign->dxflib
returns show that dangling link. This locates the represented array loss at the export/file boundary
without asserting identity with closed-source code. Scalar integers/reals/private strings can survive,
while group1 strings become1000 and foreign paths move into QCAD_OBJECTS. Scalar equality is not complete
record, scope or CAD preservation. The native-private1000 control is not claimed generic standard support.

The attribute observations locate another incompatibility: all72 dxflib-imported test attributes name
the native model-space block as parent, matching the public addAttribute constructor's current-block
argument. The24 dxflib-written raw sequences contain INSERT/ATTRIB data without the attribute-follow
flag or sequence terminator; the decoded INSERTs lack attached attributes. The existing asset-profile
guard refuses these files rather than inventing identity or returning a zero-difference comparison.

The final controller observes all48 declared jobs:46 exports and46 exact fresh public-inventory repeats,
12 strict comparisons with differences,34 profile refusals and two actual export failures. Both hydraulic
dxflib->OpenDesign branches report Invalid Symbol Table name; both original failures remain.
The controller records cohort_status=differences and exits1 despite completing diagnostic coverage. An
earlier stopped batch retains26 successful exports and their7 strict reports/19 profile refusals, with
no fresh phase. Raw files, phase selection and every receiving disposition remain, including partial files.

Preparation/analysis failures are also retained. A helper name collision was corrected before execution.
The first native run refused two matching importer filters; the next copy omitted empty output folders.
Both failed runs remain; successors use exact filters and a directory/collision preflight. The third
run stopped at the real hydraulic failure. The separately frozen fourth method collects subsequent
job outcomes and derives its fresh subset only from successful export observations, without marking the
cohort successful. The first receiver crashed at a dangling link; it now keeps the path and unresolved
handle. A shadowed local variable miscounted exports as5; the original report remains beside the
count-corrected report, which differs only at5->46. No native execution was repeated for that correction.

The [offline receiver](../examples/cad-handoff/qualification/check_records15.py) verifies raw archive,
frozen methods/inputs, exact namespace pairs/candidates, public properties, selected settings, terminal
states, complete failure coverage and all retained reports. Tests retain prior methods and add omitted
failed-job, lost-order, dangling-reference, attribute-parent and48/46/46 count checks. These are exposed
authored diagnostic results, not fresh qualification. Original strict/byte tools, historical failures,
other unresolved payloads, complete readable receiving, fresh UI/editability/revision gates and actual
company/engineering acceptance remain unchanged and open.

The separately declared and frozen six-job native-name intervention identifies the hydraulic symbol
failure. dxflib retains block name 2/2-directional valve, whereas OpenDesign import sanitizes the slash.
For both exact earlier namespace-source bytes, renaming only that block to 2_2-directional valve permits
OpenDesign export. Unchanged and unrelated-anchor-renamed controls still fail. Before/after-operation
inventories match exactly except the intended name, including recorded IDs/handles, custom properties,
attributes and variables. These inventories do not enumerate complete geometry. Both successful returns
repeat their inventory in a fresh process but still refuse the original asset-profile guard; this is a
bounded causal export diagnosis, not a repair or qualification. Original raw sources are unchanged.
The first offline receiver refused because it counted both debug and warning occurrences of each error;
its source/failure remain beside the correction counting the exact four Export Error warnings. A quoted
one-line attempt to retain that diagnostic failed syntax checking before execution; the scripted successor
retained the actual reproducible receiver failure without rerunning CAD.

## 198. Separate ordinary headers from native dimensional style

The [header plan](../examples/cad-handoff/qualification/header-boundaries-16/PLAN.md) precedes a frozen
26-job observer: the same six exact save14 sources, both importers/writers, and two empty controls.
All157 known variables,22 dimensional variants,24 layout getters and the earlier public inventory
are captured initially, after import/export, close/reopen and fresh process. Actual outcomes retain
25 exports/fresh imports and one known hydraulic symbol-name failure. Original strict receiving gives
6 differences,17 asset-profile refusals and2 explicitly unprofiled descriptive empty controls.

Ordinary imported dimensional values can disagree with the separate dimension style. Saving replaces
several known-variable values with that style. The separately declared/frozen48-job intervention uses
all six sources and both writers, with unchanged, known-only DIMASZ, style-only DIMASZ and unrelated
USERI5 controls. Exact before/after inventories permit only the intended recorded cell. All48 comply;
all48 raw DIMASZ headers follow the style: target-only style9.875 is written and target-only ordinary
known9.875 is overwritten. Unrelated USERI5=1234 persists. All48 fresh public inventories repeat,
while24 strict differences and24 profile refusals remain. This establishes the bounded API direction,
not every application's interactive file-open path or full source/geometry preservation.

The expanded layout fields also expose new failures: only17 of25 first-cohort fresh inventories repeat
exactly. Eight dxflib receiving jobs differ at46 plot/layout leaves. The original analysis refused that
assertion; its source/actual refusal remain. A descriptive successor retains every changed path/value
and labels all eight failed repeats. No field is dropped. Pinned public RLayout constructors leave
primitive plot members without initializers, a source lead consistent with the unreliable observations;
the installed build's exact internal cause still needs a direct control and is not claimed established.

The host daemon was stopped before native launch; the failure remains and state was checked before
starting the existing Docker installation/first container. The first analysis also had a syntax error,
preserved beside its actual refusal and correction. No native run was restarted after a timeout.
All original raw headers, zero-time literals, returned files, known-variable changes,74 original strict
or explicit non-applicable reports, native commands/profile/resource limits and terminal states are
received offline from bounded exact chunks. Old core methods, fixtures and strict failures are unchanged.
Other paper/header/resource causes, complete readable receiving and fresh native UI/editability/revision
qualification remain open. These exposed software controls establish no plant/company/engineering acceptance.


## 199. Check exact ports without confusing structure, engineering and CAD

2026-11-08. The public JSON/symbol-generation discussion raised a concrete missing distinction:
correct instrument tags can still connect to the wrong input. The plan, fixed fictional CSV/text
sources, catalog and separately authored acceptance key were committed at `1e9b761` before the new
checker. The same assistant authored and saw all inputs/key/code; this is exposed development,
not independent human review, blind model evaluation or visual interpretation accuracy.

The standard-library tool checks exact ports, direction, relation and signal medium against supplied
catalog meanings. It retains incomplete coverage, unknown types, uncertain/duplicate identities,
other observed connections and every source binding. The existing markup route gains an optional
port-level fact; its old match semantics and keys remain. All prior CAD comparators/failures are intact.

The actual initial replay matches the frozen key: R1 supported, R2/R3 missing under explicit coverage,
R4 unknown, with old wrong-input C3 and unrequested C4 retained. The separate corrected return supports
R1/R2/R3 while R4 stays unknown; there are no other supplied connections. The controlled old/new fact
representation comparison shows the terminal distinction, not a reader-accuracy improvement.
Eleven new regression methods and nine original markup methods pass. First import syntax failure and
two old packet code-fingerprint replay failures are retained. Both old packets were replayed unchanged:
the only result-value change is the tool source hash; all other old packet bytes except receipts match.
`examples/pid-markup-review/CODE-UPDATE.json` pins the old revision and exact before/after hashes.

Public DEXPI/pyDEXPI and five published engineering-rule examples were reviewed with source/version
fingerprints. No upstream code was copied, adapter claimed or design heuristic made a universal rule.
The manager route provides a correction queue and receiving boundary; actual preparation/review effort,
independent engineering judgment, full image interpretation and CAD qualification remain unmeasured/open.
The registered repository checks and exact-head CI are reported separately from these bounded controls.

## 200. Confirm the installed layout initialization boundary

2026-11-08. The [pre-execution plan](../examples/cad-handoff/qualification/layout-construction-17/PLAN.md)
and [frozen inputs](../examples/cad-handoff/qualification/layout-construction-17/FREEZE.json) precede
four actual native processes. An authored LD_PRELOAD helper forwards the installed constructors;
observation-only, two valid typed plot presets and unrelated tab-order controls use the same six
exposed source bytes and both exact importers. No substitute constructor, source edit or CAD save occurs.

All 272 recorded constructor calls leave the twelve declared plot locations unchanged and reset tab
order. Detached native getters return both exact typed preset patterns. Only default and named C1
variants execute; C2 variants are not observed. All 48 nonempty imports return success. OpenDesign
replaces the presets in 180 imported layout/getter observations; dxflib retains them in 144. Both
empty controls retain another 48. Initial documents retain all 336. Across all 168 matched complete
public-inventory comparisons, 2,355 leaves differ inside targeted getters and zero recorded non-target
leaves differ. IDs/handles/parents/values are preserved; only set traversal order is keyed/sorted.
This inventory does not enumerate complete geometry or opaque payloads, and no hash-seed intervention
is claimed. Invalid/nonfinite observation-only readings remain in the complete raw records.

This is direct installed-library evidence for the bounded initialization gap and receiving boundary.
It does not explain every native save loss or replace the old strict comparisons. The diagnostic
presets are not a production repair. Normal full-application open/initialization/print setup is the
next method candidate; reserved native edit/save/close/reopen, readable receiving and revision checks
remain open. No plant, company or engineering acceptance follows.

The [offline receiver](../examples/cad-handoff/qualification/check_layout17.py) reproduces the complete
diagnosis from 66 exact records (5,544,247 raw bytes, 52,256-byte lossless archive), checking frozen
inputs, compiler/helper identities, actual command/profile/terminal state, every constructor field,
typed getter coverage and every inventory difference. The same assistant authored the experiment and
receiver, so this is exposed software validation, not independent engineering review. Original host
preparation failure metadata, unexecuted preflight snapshots and two reproducible offline receiver
mistakes remain. Neither receiver correction caused a native rerun. Missing/altered calls, fields,
ABI locations, typed getters, import coverage, unrelated differences and qualification claims have
receiving controls. All earlier source/key/profile/comparator files and historical failures remain.

The latest linked [public cross-sheet example](PID_GRAPH_QUESTIONS.md) is recorded separately as a
design input. Current one-map retains reciprocal pairings and separate disagreements. A future
path consumer needs explicit accepted/exploratory traversal rules, conflict-qualified register
projection and source-revision invalidation. A three-sheet exercise is declared as proposed/unrun;
the author's outcomes are not reproduced results. No graph authority, cause-and-effect engine,
DEXPI exchange qualification or new CAD performance is inferred from the post.

## 201. Run cross-sheet questions with explicit review boundaries

2026-11-08. The user requested the identified gaps be addressed and a practical route to paid work.
The [plan, authored schedules, graph assumptions and fixed key](../examples/pid-path-review/PLAN.md)
were committed at `4f58d2a` before implementing the path consumer. The same assistant authors/sees
sources, key and code; this is exposed fictional software development, not independent interpretation.

Code review of the first working prototype found an incorrect media assumption: an off-page pairing
alone was admitted as a process continuation. Its code and actual result remain in `attempt-1`.
The schedules identify process and signal meaning, but the first prepared graph omitted that explicit
declaration. New prepared inputs with source-bound network_kind claims were frozen at `24eed65`.
Original graphs/key remain; the successor still qualifies their omitted meaning. This is a new input
cohort/preparation correction, not a model gain or untouched held-out result.

The [reusable consumer](PID_GRAPH_QUESTIONS.md) reads supported twin-graph-1/2 snapshots with exact
scoped IDs. Reviewed-only and explicit exploratory policies separate physical/logical process and
signal/impulse relationships, retain applicable open conflicts, direction, rejected records, missing
media/source/claim evidence and missing continuations. It returns a readable HTML/Markdown report,
typed source-qualified association register, full structured result and exact retained graph/receipt.
No graph producer or earlier CAD comparator/profile/key is changed. The source originals named in a
graph are not independently fetched or authenticated; original verification remains an intake task.

The actual ten policy/key outcomes match beside the naive unrestricted undirected walk. That baseline
finds all routes, including the known reversed edge, without qualifying disputed or uncertain paths.
The successor blocks the reversed route under both policies. It distinguishes supported local facts
from qualified downstream associations. Correcting the third sheet reopens the old remote answer;
the local answer's basis stays unchanged while two wider register rows change. An unrelated stored
record addition reopens neither. Complete prior packets and their rendered projections re-score on
receipt. New incident-edge/conflict controls reopen affected answers; tampered and rehashed false
answers/projections refuse. Eighteen regression methods pass without skips. Graph/search/history/output
limits refuse oversized scopes rather than publishing truncated negative results.

Browser inspection of generated HTML checked the visible 3 in / 4 in disagreement, both source
locators, review owner and separate item/association status. The initial preformatted layout was
replaced with readable sections and download links; earlier unpublished outputs remain in scratch.
The browser's file-protocol restriction was handled through a temporary loopback-only static server;
an out-of-allowed-root screenshot request refused, and the workspace screenshot succeeded. The server
was stopped after review. This is display QA, not recipient acceptance or a mobile usefulness study.

Public multi-sheet image interpretation and independent source/key review remain unrun. This is not
a consequence/LOTO engine, complete line/valve register, DEXPI export, live watcher, authenticated review
service or native CAD qualification. Existing company/engineering receiving responsibilities remain.

## 202. Make a bounded paid review concrete

2026-11-08. The [service entry](WORK_WITH_ME.md) now leads with a specific maintenance and drawing
information review: one decision/system, agreed source quantities, source-linked findings, owner actions
and one returned-record check. An example scope of three sheets and 25 selected assets is a proposal
to agree, not a tested commercial price, delivery promise or customer outcome.

The [first-assignment package](../examples/consulting-start/README.md) contains a first-conversation
record, source/deliverable/acceptance scope, private quote worksheet and receiving/follow-on review.
It includes preparation, interpretation, review, receiving work and revision effort in the quote basis.
The assessment can finish with owned evidence gaps; client engineering release and authoritative-system
readback remain separate. Repeat paid work and observed receiving needs inform future product choices.
No customer, price, testimonial, measured saving, credential or outreach is invented. Contact remains
Steve's LinkedIn only; unpublished post copy stays outside this repository.

Primary NIST maintenance-decision and work-order-quality publications support the decision-first source
method, not toolkit accuracy or willingness to pay. SBA business-planning resources were checked as a
separate business starting point. Templates are a prepared commercial hypothesis; an actual scoped
quote, paying recipient, observed effort and accepted delivery remain external evidence to obtain.

## 203. Compare connected engineering workflows before expanding the toolkit

2026-11-08. Steve shared Semodia's Flow2MTP-in-Entellia post. The short link initially failed in the
web reader; a public redirect resolved to the Semodia post, whose text was read in the browser and web
reader. No login, outreach, trial, vendor-generated file or full video workflow was executed or evaluated.
The [comparison](COMPETITIVE_WORKFLOWS.md) distinguishes first-party descriptions from independent evidence.
Entellia markets connected engineering and brownfield workflows, Cognite contextualization connects
industrial records, and Siemens advertises a project-connected TIA Portal engineering assistant.
These establish overlap, not a measured growth rate, relative performance, price or customer demand.

The useful additions are explicit engineering handoffs: one unit through successive work products,
behavior requirements separate from topology, applicability checks before pattern reuse, and a named
receiver/version before an export. The new [manual worksheet](../examples/consulting-start/AUTOMATION_HANDOFF.md)
separates owner requirements, supplier responses and actual receiving observations, with source locators,
unknowns, owners and a subsequent revision. It extends the existing scoped consulting package; it is
not a new executable feature, FDS completeness claim, standards adapter or operational control instruction.

The vendor's subscription SLA separately scopes engineering/integration services and requires professional
review. Its PAVIS partnership advertises engineering services too. Review and consulting are therefore
not claimed as uncontested advantages. Discovery now asks which licenses/providers already exist and
what specific work remains undone. The delivery roadmap prioritizes a useful paid review and its receiver
over another format or broad generation feature.

The inspected Flow2MTP page calls a 2025 MTP release current; PI's official announcement is dated
2026-01-20 and releases MTP Specification 2.0. This discrepancy is retained as a reason to settle the
actual target version. No normative text was accessed and no package conformance is claimed.
The prior-art survey is explicitly dated; current runner counts and the prior bcd75f6 release checks
are corrected in STATUS without claiming a new full-suite run for this documentation-only update.

## 204. Review a browser simulator through a real selected calculation

2026-11-08. Steve shared Hazem ElMancy's Flowstead browser post. Its short link was resolved publicly;
the post, upstream README, engine-version record, browser/benchmark guides, selected expected case,
worker client and browser-test code were inspected. Source review was pinned to upstream commit
`c2d431f67673c6dc94d4218a81ed60cd5ae9a6c3`; no code or third-party case was vendored, and no native
simulator build was performed. Numerical execution below occurred in the public browser application.
The [analytics guide](PROCESS_ANALYTICS.md#lessons-from-flowstead-accessible-calculations-with-a-retained-basis)
now distinguishes this candidate external engine/interface from the toolkit's earlier 42-flow-sheet
structural DWSIM exercise, which did not solve the numerical models.

An actual desktop-browser run opened the public site without an account, waited for DWSIM 10.2.12 ready,
loaded its Dew and bubble points example, and pressed Solve. The page reported convergence. Both
stream worksheets displayed 99.97 degrees C; liquid/vapour mass enthalpies were 418.991/2675.531 kJ/kg.
Decimal arithmetic gives a 2256.540 kJ/kg difference. The three selected comparisons agree with the
upstream reference entries within their fixed tolerances; those entries were read before execution,
and their IAPWS attribution was not independently rederived. The
[observation record](../examples/external-simulator-review/flowstead/observations.json) retains that scope.

The object-list pointer click failed because the toolbar intercepted it. Programmatic selection of
the same observed button opened the stream inspector; its Worksheet tab was clicked normally.
Console error-severity progress messages occurred despite convergence. These facts are retained;
no unassisted-pointer or mobile-usability pass is claimed. A malformed browser-find argument was corrected
to the documented text search, with no change to the site or numerical case. The public page was closed.
No full upstream benchmark, live-build correspondence, network/privacy audit, offline-cache check,
file round trip, dynamics, safety calculation or plant applicability was qualified.

The new [manual calculation worksheet](../examples/consulting-start/CALCULATION_REVIEW.md) covers
input/source/units and property-model assumptions, baseline/scenario differences, independent reference
checks, failure cases, receiving open/recompute/readback and revisions that reopen the result.
It is an optional scoped review, not a simulator integration or an established consulting result.
Existing tools, historical outputs, keys and CAD qualification criteria are unchanged.

## 205. Test the normal application initialization path

2026-11-08. The [full-application diagnostic](../examples/cad-handoff/qualification/open-initialization-18/README.md)
compares bare API and normal installed MDI opening after the same full GUI startup. Plan `a876098` and
method freeze `c3ed2e1` precede execution; the six drawings are exact exposed header16/layout17 sources,
not new validation. Three modes per route reuse the pinned forwarding helper and settings input. The
426 actual constructor calls retain the twelve plot locations and reset the unrelated tab-order location.

All six processes complete their 14 jobs. In both routes and at all three stages, 192 of 372 plot getter
observations follow the two diagnostic patterns: 144 from dxflib imports and 48 from empty controls.
The other 180, from OpenDesign file imports, agree across presets. Neither ordinary MDI setup nor eight
installed Print getters repairs that native storage. Print returns agree across presets independently
of these unreliable layout getters. There are 546 complete public-inventory comparisons: no-op/print
produce zero changes, mode comparisons retain 3,189 target leaves, and route comparisons retain 342, all
in the observation-only process pairing. No recorded non-target difference is hidden. Native geometry
and opaque payloads are not completely inventoried.

The ordinary trial notice required acknowledgement. The first controller erroneously matched its hidden
window three more times and was interrupted; all four actions remain. The visible-only controller also
retains Return attempts during the notice's disabled-OK countdown. Every frozen script's final cleanup
fails: the bare path calls an unavailable QtScript quit function; the MDI cleanup iterates closed
wrappers whose documents are already null. All 42 per-job MDI closes returned true, yet their wrappers
remained counted inside the timer callback. Normal external window-close requests end the completed
processes; the original batch exits zero with no restart or OOM. This is not a clean scripted-shutdown
or interactive edit/save/close/reopen pass. Selected working settings hashes before and after actual
close are retained; their contents and all compiled/publisher binaries are excluded from the packet.

The offline receiver recomputes the full tables from retained native records, checks prior identities,
frozen inputs, commands, coverage, constructor bytes and controller/terminal history, and rejects missing
or altered observations. A separate planted unrelated version change remains visible in complete
comparison output. This closes the ordinary-open/getter repair hypothesis on development data, without
changing the strict comparator, old failures or the full qualification criteria. No CAD file was saved
and no reserved result consumed; native preservation, receiving/readability/editability, revision gates
and actual engineering/company acceptance remain open.

An explicit site-package-free check found that the first receiver indirectly imported ezdxf through
an older archive checker. The original source, actual `python -S` stderr and exit are retained. The
corrected bounded archive reader has no such import and passes under `-S`; traversal, duplicate-member
and symlink controls exercise it directly. No native process was rerun and no native observation changed.
Controller exit summaries record observed host-tool results rather than original captured terminal
transcripts; the actual action receipts, startup images and native command/state history remain.

## 206. Develop matched native UI saves without hiding automation failures

2026-11-08. [The declared six-case UI plan](../examples/cad-handoff/qualification/native-ui-pairs-19/PLAN.md)
was committed at 7c1f031 before implementation. Startup/dialog-only preflight completed without a drawing
open/save; its original action-count and modal accessibility timeout remain. Drawing procedure 681deeb and
subsequent separately committed corrections retain a failed empty staging launch, covered-MDI ambiguity and
an overbroad Untitled-title match. Pure control selection now passes both actual retained trees and refuses
missing/duplicate document controls. No case or strict preservation rule was changed to fit the automation.

One no-edit libre-air-water process completed actual native UI Save As, document close/reopen, editable fields
and normal exit. Its three common-frame canvas comparisons have zero changed pixels; its full save still
fails with 300 strict differences. A separate edited process's accessibility focus did not activate the
floating Property Editor: Ctrl+A selected all drawing entities, and the native document remained unmodified
with the original field value. It stopped before save. Corrected actual-field clicking, focus and text checks
were frozen at 639d109 before a continuation in the same process. That recovery completed the planned field
change, native save/close/reopen and normal native exit, while retaining the original failed controller/container.
Both returned files retain 300 source differences and their paired comparison retains 57 entity differences.
These diagnostic observations do not complete the planned clean matched method or qualify a native return.

The [development checkpoint](../examples/cad-handoff/qualification/native-ui-pairs-19/PROGRESS.md) separates
these observations from the fresh 18-process exposed cohort frozen at 5f27559. Historical/recovered jobs are
not adopted into that run. At this checkpoint, portable raw-evidence receiving, complete cohort analysis,
loss controls and CI are unfinished; observations remain local and provisional. All six software candidates
pass unchanged strict/raw checks; the six library saves fail exact byte reconstruction. New reserved evaluation,
complete native readability/editability and revision/foreign-attribute gates, and company acceptance remain open.

### 206 follow-up: receive the completed exposed cohort

All 18 original fresh-cohort controllers, native applications and containers subsequently exited zero.
Seven bounded lossless packets now retain both original failures and the complete cohort; the
[offline receiver](../examples/cad-handoff/qualification/native-ui-pairs-19/README.md) checks source/method
pins, execution/terminal state, UI controls, independent native observations, stored values, full crops
and comparisons. It checks 798 native observations, 60 field panels and 144 views (576 PNG files).
All 12 native full saves still fail: source-to-return counts are 298–377, matched-pair counts 50–53.
The six exact-span candidates retain strict/raw passes; library controls still fail raw reconstruction.

The receiver found two further failures rather than promoting controller exit zero to acceptance.
A shared mutable expected-value dictionary rewrote earlier producer metadata in every edited run:
12 recording failures remain alongside correct independently retained UI/native/DXF before/after values.
The original receiver refusal and source are retained. The original pixel analyzer also refuses exact
camera equality on motion/power last-decimal offsets; its failure/source remain. A diagnostic retains
all original camera values and all 54 fixed-region pixel comparisons. Zero outside-region changes is
observed, with nine comparisons explicitly diagnostic only. No tolerance or image registration was added.

Controls challenge omitted observations/trees/actions, disabled fields, changed source and incorrect
returned values, unsafe/incomplete archives, and an unrelated pixel despite updated capture hashes.
An actual-old-method regression reproduces mutable metadata rewriting beside the successor's preserved
snapshots. Replay Python bindings explicitly normalize CRLF; all native raw evidence stays byte-bound.
The first raw Python binding check exposed the existing cad_handoff.py checkout's CRLF/Git-LF difference;
its original manifest remains locally, and no native measurement or CAD check changed to address it.

A separately committed plan/source review precedes the new absolute-camera control. Pinned public
QCAD source suggests previous-offset floating-point cancellation as a lead, not installed-build proof.
A fresh camera-only process now tests old and direct factor/offset view setters on exposed inputs,
without entity edits or saves. Its actual result, complete repository/CI gates and later six-case
follow-up remain separate. Original full-save failures, reserved/generalization, foreign/other-text,
revision/conflict and engineering/company acceptance gates remain open.


The first full local suite finished 94/95 programs, with seven individual skips and three platform notices.
Exact-head CI [42505046833](https://github.com/steve-vitale/industrial-context-toolkit/actions/runs/42505046833)
failed the same packager check. Its current-only generator assumption was wrong: the first two case
archives used the frozen source already retained under receiver-2. The only packager source change adds
receiver-2 to historical collection; case packing is unchanged. Current repacking reproduces both archives
byte-for-byte. Original inventories, failure logs/command/source and CI step output remain in validation.
The receiver now resolves packager identities to retained frozen sources; unknown identities refuse.

The next complete replay differed in two ancillary candidate save_metadata_changed flags. Installed and
upstream ezdxf1.4.5 setup replaces loaded $TDCREATE with inspection time. A delayed inspection and a
controlled two-clock regression reproduce the effect for identical raw headers. The reporting repair was
committed before regenerating the stable presentation: original summary and actual differences remain,
actual unchanged comparator reports are returned as live diagnostics, and complete raw HEADER bytes
supply the candidate metadata evidence. A changed raw header refuses. No comparator, original source,
byte requirement or native failure was changed. Successor integration/CI results remain separate.

The first camera-only air process subsequently completed normal controller/native/container exit0 and
24views with exact four-file cameras for both recipes. All frozen inputs remain unchanged. This case
reproduces neither original camera failure; it establishes API/terminal behavior only. Full pixel receiving
and the other five camera cases remain unfinished, as does the original qualification objective.


## 207. Receive the first exact-camera repeat and launch the remaining controls

2026-11-08. The previous native-cohort package merged as PR43 after exact-head
pull-request42506688565 and push42506684160 CI both succeeded. Both actual full
suite logs report95/95 programs, zero failures and37 individual skipped cases;
this is not a complete zero-skip suite. Original full-save and recording/camera
failures remain. Local main was verified at merge5a6397e before a separate branch.

The already frozen camera-only design has now received the original air/water
run as a [portable packet](../examples/cad-handoff/qualification/camera-repeat-20/README.md):
86 native observations, four field panels,24 views/96 images and normal exits.
Both recipes repeat exact four-file cameras, and all18 fixed-region comparisons
have zero outside-region changes. Air reproduces neither earlier motion/power
failure; it cannot establish their repair. The same author/agent sees the inputs
and writes the receiver; no independent engineer or reserved evaluation is involved.

Before first pixel comparison,3ad1475 froze source-bound receiving. Its first
actual refusal was an LF reserialization digest compared to the original CRLF
basis; failed command/source remain. Repair90f11ff retains exact source bases and
compares values after their original inventory hashes;19aff8c binds raw checkout
bytes. Subsequent actual direct and separate portable replays pass. Five new
regression methods pass without skips, including an unrelated pixel with updated
full/crop/digests. Visual inspection finds source/adaptation label-symbol overlap
and zoomed annotation clipping; equality does not establish complete readability.

Plan/batch43fec6a froze the remaining five runs before launch. Three processes
are currently live and two queued, with no controller failure at the checkpoint.
Keep their actual handles and complete every old/new comparison before deciding
on the camera method. No CAD file is edited/saved in this follow-up. The unchanged
strict comparator, source-span patcher, original native failures and complete
qualification objective remain; new reserved/full-workflow transfer, foreign/text,
multi-asset and revision/conflict gates are not closed.


The complete CAD evidence module subsequently finished51/51 tests in237.029s,
zero skips and exit0. Actual command, raw test source and stdout/stderr/exit are
retained in camera-repeat-20/validation/integration-1. All original replay and
loss controls pass beside the five new methods. This is not the full95-program
repository suite. Three original native receiving containers remain live; no
camera-cohort success or reserved qualification is inferred from the tests.


### 207 follow-up: reproduce the old drift beside exact absolute cameras

Motion,power and hydraulic subsequently completed original controller/native/
container exits0 and independent portable receiving. Across the four received
cases:344 native observations,16field panels,96views/384images and72pixelpairs.
Every pair has zero outside-region changes. Old zoomTo reproduces motion's two
failed frames and power's one (nine diagnostic pairs); absolute requested/actual
and four-file cameras match exactly on all four cases. This is evidence for the
proposed exposed-development camera procedure, without tolerance or image
alignment. It does not prove installed proprietary internals or new independent
transfer. All original failures remain. Mechanical/template have now started
automatically and are live; both remain required before a cohort conclusion.


### 207 final cohort: retain an observation-channel failure

The last two original runs completed normal native/controller/container exit0.
All six packets are retained. Mechanical receives; template strictly refuses
because it also retains replies/unknown.json: Cannot read request. All86 normal
sequential replies remain, but the observer's QFile open failed at least once.
Its fixed anonymous-error filename can overwrite earlier failures, so total
error history is unknown. A replace/read filesystem race is an unproven lead,
not a confirmed root cause. Original failed command, host exit1, source and
freeze remain in camera-repeat-20/development-3.

Commit04070aa freezes an explicit failed diagnostic before its first run.
Default strict receiving still refuses extra/missing replies. The diagnostic
retains the extra error record as failed and all18 template comparisons as
diagnostic; missing normal replies or other corrupt evidence still refuse.
All108 image pairs have zero outside-region changes,27 diagnostic only: nine
old-camera pairs and18 template pairs. Absolute requested/actual and four-file
cameras match on every retained view. All6 exposed cases/516normal observations,
24fields,144views/576images remain development; five packets receive and one
strictly refuses. Seven focused methods pass in105.456s,0skips,including all6
packet replays, the original refusal and missing-reply refusal in diagnostic mode.
Source comparator/patcher/byte checks and original UI19 evidence remain unchanged.

Next: immutable sequence-bound request/reply transport with retained error
history and fault controls, then a complete corrected fullUI method frozen before
fresh reserved admission. Original full-save, foreign/text, multiasset,
readability/editability, revision/conflict and engineering acceptance stay open.

## 208. Make current scopes discoverable and execute their reproduction paths

2026-11-08. Steve asked for all lessons/gaps, current README/description and clear
organization for other people's agents. The README now surfaces maintenance
intake, markup/port/path checks, CAD metadata and return review, photo/document
preparation, recorded analysis, onboarding and manual consulting/calculation/
automation methods. It distinguishes supplied readings and authored detailed
layouts from executable checking. WORKFLOWS adds the missing CAD/path contracts.
Existing evidence paths remain intact rather than breaking hashes for cosmetic
moves. The repository guide assigns directory/reference ownership; existing
script/feature registries remain canonical, with current CAD evidence registered.

The workflow guide provides seven actual first-result routes, known findings,
source/review boundaries and failure/revision checks. An initial author-run
executes8workflow commands and5regression programs successfully. The portable
cross-workflow runner was then frozen00ebbc7 before execution; all13commands,
eight additional source/result checks and63tests pass with0skips. The existing-
destination control refuses and all399retained files stay byte-identical. Actual
plan/commands/logs/results and metadata readback are retained under
examples/agent-first-use/workflow-check/actual. This is one exposed author-run
software exercise, not independent agent/manager evidence or a measured saving.

The authenticated GitHub CLI updated and read back the description because the
connector exposes no metadata-edit action. It includes records, P&ID/CAD review,
photo/document fields, models/context, recorded data, Ignition/PI, self-service,
onboarding, consulting worksheets and benchmarks. Contact remains Steve's
LinkedIn; no outreach, LinkedIn content planning, simulator/MTP adapter or alert
service was added. CI now runs the portable entry-point check. Current-head CI,
full integration and the native transport repair remain distinct work; useful
reproduction does not close the original CAD qualification or human/site gates.


## 209. Observe installed native bindings before replacing failed observer transport

2026-11-08. Prior goal turn made progress: PR44 merged3ad016f with both exact-head
CI jobs passing and a matching clean main tree. N118 criteria were frozenca96ca0
before implementation: private immutable numbered messages, exact run/wire binding,
complete errors, fail-stop behavior and actual normal/fault receiving. Original
UI19/camera20 and strict CAD/byte methods remain unchanged.

Frozen a720dcf fails before a normal reply: inherited QFile size/error methods are
absent and the error handler itself fails. All81actual files and controller1/
native0/container1 outcomes remain; inspect and normally close the same live
process with a separate cleanup receipt. Frozen e395618 fails on absent QFileDevice.
Its full error/publication failure reach the native console and the client refuses
immediately. Preserve the complete second packet and separate same-process cleanup.
Neither opened or saved a drawing. No attempt was repaired or restarted in place.

Upstream QCAD's5.14.2 project selects generated5.5 bindings; source did not prove
installed availability. Probe a493c4f confirms missing inherited APIs/classes,
working QIODevice parent size/errorString and actual NewOnly collision refusal.
Python through QProcess completes, but codecForName's string overload refuses.
Retain that capability failure. Separately frozen01258ba decodes actual stdout
JSON containing UID1001 and µ valve, plus exact stderr, with QTextStream. Both
probes complete controller/native/container0; probe1's codec check stays failed.
Two hashed probe archives each retain66actual files. Native/client reports agree.

The launcher now distinguishes the shell wrapper from the actual Qt child PID/
start identity. Future pause faults must target that child and retain controlled
UI unavailability; separately resume/close the same process, not restart it.
Eleven mailbox tests and five semantic evidence tests pass without skips. They
challenge changed sources/methods, lost errors, promoted exits and jointly altered
reports beyond an outer inventory. Offline receiving rechecks all four distinct
outcomes. Actual commands, methods, raw console, UI and process/export receipts
remain under observer-transport-21. CI adds those offline checks; current branch
integration is separate from verified PR44 CI.

BRIDGE-PLAN.md is frozen before successor implementation: a pinned local Python
helper owns physical mailbox I/O and reports actual OS errno/stage/path, with a
complete immutable invocation history. QCAD still produces native observations
through observed QProcess/stream APIs; UI controls own drawing work. Never invent
an unavailable QFile code or promote either failed attempt. All original fault,
strict, byte, source, revision and reserved gates remain. The historical camera20
read-open cause, helper implementation and full receiving, corrected-method freeze,
foreign/text/multiple-asset/reserved transfer, complete readability and engineering/
company acceptance remain unfinished. No plant, human-benefit or qualification claim.

## 210. Yield the native event loop and receive the entire transport campaign

2026-11-08. Progress on the active CAD goal, not complete CAD qualification.
The eef0788 Python I/O bridge returns two status observations, then the old UI
routine refuses immediate filename readback. The exact mismatch was not logged.
Later read-only inspection sees the exact filename without retyping. A separately
frozen Cancel times out. The second separately frozen cleanup publishes a run-bound
stop, observes acknowledgement and no live helper, then cancels the still-open
dialog and closes the same unmodified unnamed process normally. Original
controller/host/container exit 1 and native exit 0 remain. All 3407 actual files
and 1645 helper invocations are retained. This supports scheduling interference;
it does not prove Qt internals or turn the failed normal attempt into a pass.

ASYNC-PLAN precedes implementation. Frozen 05628bb fails before helper start:
the installed finished signal is overloaded. The native error supplies the full
signature; separate cleanup verifies the original process/no helper/no dialog
before normal close. Frozen 93cedc9 uses that signature. While its helper waits
for release, the native UI opens a dialog, types the literal filename once,
observes exact completion and cancels. Only then is the helper released. Native
signals retain exact UTF-8 output, actual PID/parent/UID and 1107 timer ticks.
All exits are zero; the drawing stays unnamed and unmodified. Preserve both
probes. API/scheduling evidence is distinct from transport and CAD qualification.

Frozen 4ba46e1 replaces blocking GUI waits with one event-driven helper at a time.
The unchanged Python owner retains exact argument/result/event hashes and actual
OS errors; QCAD supplies read-only observations. Both exposed normal cases pass
complete receiving: 14 replies each, expected editable fields and three absolute
frames, final seal and normal close. Every one of the eleven predeclared fault
profiles retains a failed original attempt and appropriate error/history or
controlled timeout/native-exit evidence. Separate cleanup never restarts a failed
native process or promotes its controller. Thirteen lossless packets retain
3715 files, 35,280,068 raw bytes, 1,330,860 archive bytes and 1123 helper calls.

Offline controls go beyond archive hashes: lost replies/errors/history, wrong
wire/sequence, replaced source/method pins, lost seal, unbound client/native
observations, hidden signal failures, jointly false scheduling reports and
promoted exits refuse after recomputed inventories. Seven complete-campaign and
six predecessor-evidence regression methods pass locally without skips. The
helper's twelve and bounded text observer's three methods also pass; the earlier
two helper-test fixture failures remain in validation/bridge-development-1.
Full local offline validation and exact-head integration/CI are recorded separately.

N118's exposed transport work is complete; N119 tracks the original larger goal.
Next freeze the complete corrected UI method before fresh reserved inputs. Keep
matched no-edit/native-edit/library/value-span routes and original strict/byte
criteria, with foreign/literal/encoding text, multiple assets, actual save/close/
reopen/fresh readback, visual/editability and revision/conflict checks. Original
native full-save losses and camera20's historical read-open cause remain. There
is no human/site benefit or company/engineering acceptance claim.

The experiment README now separates historical failures, probes and the active
successor and links portable replay. The workflow reproduction guide explains
that offline receiving requires no CAD installation, while new native execution
needs a permitted package and a declared compatible lab; the original local
image is not distributed. The public README and GitHub description already
include the maintenance/engineering scopes from PR44. Live metadata readback
confirms those scopes and Steve's LinkedIn; no new commercial feature or outreach
is implied by this infrastructure repair.


## 211. Exercise multiple native assets and prepare an engineering receiving decision

The full-ui-22 plan (31e55e7), two already-exposed authored cases (0aad7b2),
method (113e6e1) and prepared frames/configuration (74b347a) precede native
execution. No fresh reserved cases were admitted. The CP1251 edited run commits
both Cyrillic MODEL changes through observed native Property Editor controls,
saves, closes/reopens, verifies all twelve attribute values and exits normally.
Its complete packet has 2,470 helper calls, 73 observations, eight editable-field
checks and ten model views/40 images. The return still fails strict preservation
with 322 unexpected differences. A matched no-edit process also completes and
has 322; the UTF8/literal-brace edited case completes with 321. All original
native/controller/container/host outcomes remain intact in lossless packets.

The first receiving implementation mistakenly made semantic object key order
significant; its failure/source are retained. The corrected comparison leaves
exact wire bytes and arrays unchanged. A first test invocation hits a local
module-name collision; the next passes twelve actual-packet loss-control methods.
Six inventory/selection and four text/semantic methods pass separately. The
no-edit receiver initially supplies an empty edit plan, which the original
comparator correctly refuses. Retain that failure and use its existing no-plan
contract in the successor; the comparator is unchanged.

The matched native returns differ in 53 entity rows beyond the intended edits.
All 53 have independently checked closed exact decoded correspondences under the
existing reference-aware diagnostic: 50 linetype and three style rows have
changed handle allocation. This explains those paired rows at the declared
decoded level, without waiving strict comparison. Only 14 original-to-return
records have closed correspondences; 79 original/239 returned records remain
unpaired, plus version/header differences. The full native save remains failed;
counts and visible similarity cannot establish preservation or raw-byte equality.
Fresh-process receiving, complete visual/paper checks, revisions/conflicts,
planted CAD losses and final-method reserved validation remain unfinished.

The user refocused the active goal on engineers' and engineering managers' use.
The drawing receiving guide now starts from one transmittal and connects markup
intent, editable-CAD preservation, source coverage, correction actions, review
roles and an authorized receiving decision. A separately frozen rehearsal plan
(a8409ab) and runner (2813444) execute four real CLI calls and 14 checks. Seven
markup outcomes, the unrequested fail-action change, material coverage gap and
separate valve CAD's 335 strict differences remain visible in the worked brief.
The portable markup replay reproduces its full result; an output collision
refuses without changing the first packet. Suggested roles are not assignments.
This is agent-authored simulation, not independent image/engineering review or
measured benefit. The nine-method markup and 28-method CAD modules pass locally.
Broader integration and exact-head CI remain separate.


The first manager brief is retained in drawing-handoff/history/first-brief. Its
successor spells out the actual requests in plain language and places supported
non-safety rows after unresolved items; another real four-command/14-check replay
retains identical comparison facts. The three full-ui-22 packets also reproduce
their complete offline receipts with all original strict failures retained. Local
claim, feature, script, ledger and new-link checks pass; exact-head CI is pending.

## 212. Follow a corrected return and retain an idle-call failure

The engineer/manager rehearsal now follows the same seven requests through the
already exposed corrected consultant return. Plan 3807311 precedes runner
8a1f3a4 and actual execution: three CLI calls / eleven checks pass. Five requests
are supported by current supplied readings; the illegible instruction and
baseline mismatch remain open. A supported safety item still needs review. The
new brief retains both complete packets and evidence, leaves owners/authorized
decisions pending and does not close the separate CAD preservation finding.
Pairing the new drawing bytes with old source-bound readings refuses before a
result is written; the original packet stays byte-exact. This is a fictional,
agent-authored tutorial, not an independent image review or a timed user trial.

The fourth original native packet, the literal-brace no-edit baseline, completes
and rechecks with 2,418 helper calls, 61 observations and ten views/40 images.
It retains 321 strict differences. All four original edited/baseline packets
reproduce offline. The previous published head ed70f9f passes the complete Linux
CI run 42522574770; later changes require their own CI.

Both independently launched full fresh receivers hit the frozen 4,096 invocation
ceiling on call 4,097. CP1251 spends 3,883 calls idle and captures 18/20 views;
literal braces spends 3,871 idle and captures 20/20 but fails before completion.
Exact final call/error records expose admission before result IDs/predecessor
binding, so null IDs and an absent predecessor are preserved, not repaired.
Separate same-process acknowledged cleanup closes each native application with
exit zero; original host/controller/container failure remains one. The separate
failure auditor checks the original successful prefix and final rejection. Eight
altered-evidence controls refuse. The first packager's overlooked duplicate-file
count also refuses; its source and failure are retained beside a separately
declared capacity for both complete mailbox snapshots. No normal receiving or
pixel verdict is issued from either incomplete attempt.

Plan dd7a2d8 declares a waiting helper rather than a larger quota. The original
admission, request revalidation, immutable publication, event/error journal and
wire/invocation limits remain. Six actual subprocess controls pass; the first
test's event-count arithmetic failure is retained as a tool-output observation.
The first native probe completes typing/cancel and a real request but fails while
recording a helper event under an already used field name. Retain its original
failure and same-process cleanup. A separately frozen corrected recorder then
completes: one child stays live through 43.986 seconds of idle/UI activity,
serves the request, and the next child acknowledges cleanup stop. Both probe
histories recheck with six calls, two requests and zero idle events. Full
receiving on both exposed cases is a subsequent separately frozen attempt under
WAITING-METHODS-3; it is not inferred from the probe. N119 remains open for the
original complete CAD, paper/visual, revision/conflict and reserved-case scope.

## 213. Put the actual open evidence questions in front of the manager

The first corrected-return brief counts a coverage gap without naming it and
labels M06 a baseline mismatch without showing the values. Freeze a presentation
plan at 4e00fe5, then runner d395982 before another actual three-command replay.
The successor passes thirteen checks, retaining the original eleven and adding
the exact two evidence questions. M06 requests duty-to-standby, while both the
original and return read standby. FV-101 material is 316 in the original and
unknown in the return because no observation was supplied. Neither item closes
by inference. Each request's current complete checks and source locations are now
also present directly in revision.json. The short brief names the clarification
and missing-reading actions. The prior eleven-check packet remains unchanged;
the complete corrected comparison result is byte-identical between presentations.
No tool comparison, engineering decision, reader accuracy or human-benefit claim
changes. The README and manager/workflow entry points link the more useful brief.

## 214. Complete exposed model receiving and bind projected fields to the DXF

Reuse the frozen correspondence diagnostic on the literal-brace native pair,
pinning inputs at 6c5e27f and runner 6839dc6 before execution. The existing
independent checker closes every paired strict row: 49 linetypes and three styles
have changed handle allocation. Original-to-return still has 321 strict
differences, with only 18 record pairs closed and 75 original/235 returned records
unpaired. The portable checker reconstructs all three reports from committed
sources/archives; no strict row is waived.

Source inspection also finds that project_to_map.py trusts context attributes and
INSERT handles carrying a matching source hash. Freeze a plan at 741cc1f; four
actual controls then pass through the old adapter when they should refuse:
changed MODEL, changed handle, hidden node/mapping and invented reviewed status.
The repair re-reads the retained DXF with the existing parser and requires its
complete exact unverified node set before mapping. Both exposed two-asset encoding
cases retain every field and source byte. A combined 33-method run passes, but
the historical replay correctly refuses the changed frozen original test-module
hash. Restore that module exactly and place the five new methods separately;
those five, 19 runner controls and the complete 21-case native/context revision
replay pass. The first valid-fixture comparison finds CSV checkout line endings;
actual old/current producers emit six byte-identical files for both projections,
and committed CSV records match. All refusals and scope distinctions are retained.

Both waiting native receivers finish with all four files, 115 observations,
eight editable-field checks, 20 views/80 images and zero native/controller/host/
container exits. Each uses 231 helper invocations. The first offline CP1251
receipt refuses because its `0*.json` glob omits command records after 0999;
the original host has 1003 records and a later actual terminal inspection.
Retain the refused receiver/source, freeze the correction at f8e2d43, and receive
canonical contiguous numeric histories beyond 999 and 9999. Six receiver controls
pass and both original native attempts receive without restarting either.

The original exact pixel recipe yields 30 comparisons and zero pixels outside
the predeclared regions. Twenty additional exact pixel identities bind source
to no-edit and candidate to edited views. Actual agent inspection covers all
twenty source/candidate model views: Cyrillic and literal braces remain readable
at detail scale, while overview values are too small and existing linework/axis
intersections remain. The records state the display substitution and agent-only
scope. Complete portable replay rechecks receiving, original matched returns,
pixel results/difference images and inspected-view hashes. Paper/layout, complete
revision/conflict and planted-loss work, final-method freezing and fresh reserved
transfer remain open. Native strict preservation remains failed. CI on 3e61e9f
passes; the later projection/receiving additions require their own exact-head CI.

## 215. Keep the original request visible through a selected CAD revision

The complete adc6af8 commit passes both PR and push Linux CI, including the full
cached-data suite and snapshot MCP jobs. The next bounded development exercise
freezes its plan at 55bfe9b and implementation/method bindings at 04a93e9 before
execution. It reuses both exposed full-ui-22 sources; no reserved input is admitted.

Thirty-two actual CLI calls complete, then reproduce in a second new folder.
Each fictional concurrent return supports one requested MODEL, disagrees with
the other and changes a SERIAL outside the original plan. Both stale hash and
stale before-value proposals refuse without output. A separately bound second
plan explicitly selects the requested MODEL and retains the concurrent SERIAL.
Strict and independent byte checks pass against that selected plan, but one
unexpected SERIAL remains against the original request. Two-asset draft map
projections and their change records retain all fields and both exact sources.
This is supplied fictional branch selection, not an automatic merge, actual
field observation, native human edit or company acceptance.

All twelve individual raw losses are detected: geometry, layer, style, foreign
attribute, foreign XDATA and block geometry on each source. Each yields exactly
one strict difference and an independent byte-reconstruction refusal beside the
passing unchanged candidate. Identity, duplicate-target, newline, ambiguous
serialization and output-collision controls also refuse; existing outputs remain
exact. The manager-facing brief keeps technical selection and the original scope
question separate. Complete source packets, mutations and command outcomes are
retained in `full-ui-22/revision-loss-1`; CI reproduces its stable result.

This completes an exposed software revision/loss rehearsal. Native concurrent
manual-edit receiving, paper/layout, final-method freezing and fresh reserved
transfer remain open. Native full saves still fail the strict preservation gate.

## 216. Check what paper preview changes before using it as an observer

The exact retained CP1251 native UI tree exposes both paper-layout names,
Edit Block and Print Preview; its bytes match the complete receiving archive.
That proves the controls were exposed, not that paper navigation succeeded.
Pinned public QCAD PrintPreview source contains branches that change dimensions,
margins or document acceptance variables. Declining its prompts is therefore not
an adequate source-based argument for unchanged document state. This public
source version is not proof of the installed implementation's identity.

`full-ui-22/PAPER-SOURCE-1.json` retains the primary URL/hash and bound UI member;
the design note requires direct active-layout verification, before/after state
for any print-preview experiment and paper-coordinate regions derived from actual
viewport transforms. Model label regions cannot silently be reused on paper.
Blank equivalent images do not establish readable delivery. No current native
process was touched for this inspection, no paper result is promoted, and the
old missing-main-viewport and plot-storage failures remain open.

## 217. Retain native concurrent changes against the original request

The native revision plan is committed at 7746b1a, adapters/input identities at
aa78808 and derived cases/launch identities at 1fe5a28 before execution. Both
exposed sources complete three actual Property Editor edits, Save As, close/
reopen and normal native/controller/container/host exits. Each retains 159 helper
calls, 79 observations, ten editable-field checks and ten views/40 images.
There is no new reserved source, human operator or plant record.

The actual returns retain the FV-101 MODEL disagreement and FV-102 unrequested
SERIAL. Twenty existing CLI calls produce original-scope reviews, stale-hash/
before refusals, separately bound one-value second proposals and exact-source
draft map changes. Strict/independent bytes pass against each actual native
return; against the original request, 322/321 strict differences remain. These
are not asset counts, and changing the source does not resolve preservation or
authorize the SERIAL. All twenty commands and their stable results reproduce
from the native archives. The manager brief links the distinct decisions.

The first offline replay fails because the file-only archive's restorer omitted
empty protocol directories. Complete failed control logs and the replay tool
observation remain. A separately frozen restorer reuses the original recheck's
declared-directory rule. Native attempts, their archives/identities, original
adapter and strict/byte methods are unchanged. Both original packets replay;
six control methods pass on both, with twelve altered-evidence refusals after
reindexing. The original adapter's experimental check branch remains failed;
`recheck_native_revisions.py` is the corrected public entry point.

Fresh four-file receivers launch separately from exact committed return hashes.
Their completion, model pixel comparisons and visual review are not yet claimed.
Second-revision native receiving, paper/layout, final freezing and fresh reserved
transfer remain open; no engineering or company acceptance follows.

## 218. Put the user's receiving job ahead of native harness development

Steve asks why progress is difficult and whether the approach needs changing.
The markup and CAD checkers already accept user records, but the combined brief
was generated by a fixed rehearsal with hard-coded collateral findings. Repeated
native recorder repairs were consuming the critical path without closing that
own-input workflow gap. Preserve all CAD requirements and evidence, finish the
two current native receivers, and prioritize reusable receiving orchestration.

`scripts/receive_drawings.py` accepts a user's job manifest and invokes the two
existing checkers unchanged. It generates request, collateral-change, missing/
conflicting-evidence, attribute, identity and preservation rows from their actual
results. It retains source checks, real before/returned values, full strict queues,
unassigned roles and pending release decisions. Separate drawings stay separate;
a supplied CAD/readable-sheet association remains explicitly unverified. The
output includes the submitted job and a portable job over the retained sources.

The existing two teaching drawings produce thirteen review items. Seven tests
pass: exact original checker results/findings, portable brief replay, occupied
output preservation, stale later-drawing refusal before publication, duplicate ID
refusal, markup-only execution under `python -S`, and an unverified paired-format
association. These are software checks on exposed fictional records, not new
reader accuracy, timed engineer benefit or engineering acceptance. No native CAD
session is needed. README, agent and receiving guides now point to the own-input
command; the old case runner remains a regression example. Full CAD qualification
remains open and is not redefined around this orchestration improvement.

## 219. Retain the last concurrent receivers and stop expanding the native critical path

The two already-running concurrent four-file receivers completed with native,
controller, container and host exits zero. Each complete packet retains 231
helper calls, 115 observations, eight editable-field checks, 20 views/80 images
and no receiving-process edit. Both replay through the existing corrected
`recheck_native_revisions.check_packet` without launching CAD. External identities
are retained in `NATIVE-CONCURRENT-RETAINED-2.json`.

The unchanged model-view recipe produces 30 comparisons with zero outside-region
pixels and 20 exact source/baseline or candidate/edited frame identities. These
new frames have not had a separate visual inspection. Original 322/321 strict
save-preservation findings remain. Actual second-revision native receiving,
paper/layout, final-method freezing and fresh reserved transfer remain open.
No new native session is started. Prioritize the own-input receiving workflow
and its source-linked engineer/manager results, retaining the research failures.

## 220. Receive a resubmission without losing earlier scope or safety priority

Freeze `RESUBMISSION-PLAN.md` before implementation. The existing receiving
command gains optional `--previous`: verify the earlier inventory, reproduce its
brief from retained inputs, then match findings by drawing ID under the exact
original/instruction scope. Original source/reading changes, request changes and
CAD plan changes remain explicit basis changes. Omitted checks remain unresolved;
a disappeared collateral finding needs a current source-bound observation or
unchanged CAD field evidence. Both packets and a portable previous-packet path
are retained. No named owner or engineering disposition is invented.

The first nested-output control fails: writing a new return inside the previous
packet adds files after the captured-byte check. Refuse overlapping packet roots
before replay/publication. A separate omitted-safety-scope control fails because
its follow-up defaults to normal priority. Retain the earlier safety priority
through missing/changed scope and historical follow-ups. Both observed failures,
baseline commits, commands and corrections are recorded in
`examples/drawing-handoff/RESUBMISSION-CONTROLS.json`.

Fifteen resubmission methods pass, with no skips. They compare the corrected
markup outcomes to the prior authored acceptance key and challenge portable
replay, drawing order, omissions, changed request/original-reading/CAD-plan scope,
missing observations, stale inventory, repinned false findings, nested output,
safety priority and actual markup-only `python -S` execution. Restored CAD fields
use explicit current unchanged-field evidence, and an earlier safety follow-up
survives a later return. The seven earlier
own-input methods, nine markup methods and nineteen runner methods also pass.

The actual resubmission command produces two checks and twelve current review
items, with thirteen previous/current findings. Five requests are supported;
illegibility, baseline mismatch, unknown material and safety review remain. A
current FC observation establishes restoration of the earlier collateral fail-
action change; its engineering disposition remains pending. The separate CAD
preservation queue still has 335 differences. A second actual CLI invocation
from the portable job reproduces the complete brief.
The worked packet was produced at `9b9feb1`; the safety-priority correction at
`93bbe8d` reproduces that complete brief on portable replay. Its original receipt
and method hash remain intact. These are exposed fictional
readings and software revision checks, not new visual-reading accuracy or timed
engineer benefit. Native second revision, paper/layout and fresh reserved CAD
qualification remain open; the underlying strict/byte tools are unchanged.

## 221. Identify the same paper loss in no-edit and concurrent native returns

Inspect the earliest retained original DXF records and complete native returns,
then freeze a post-observation diagnostic before its reproducible audit. This is
exposed-case diagnosis, not a preregistered blind test. The new audit retains all
decoded layouts and raw LAYOUT/VIEWPORT tags, cross-checking raw IDs and owners.
It covers two originals, matched no-edit native returns, actual concurrent native
returns, original-source value candidates and selected second candidates.

Both no-edit and concurrent routes change A3/420x297 settings to A4/210x297 with
changed rotation and omit the original ID3 display viewport. The returned sheet
has only a generated ID1 main viewport. Within each case, no-edit/concurrent
recorded paper inventories are identical. Four missing-display observations are
two drawings on two routes. Layout1 originally has no display viewport and is not
counted as losing one. Both originals also lack an ID1 main viewport, the earlier
layout-preparation dependency; these are known problematic source layouts.

Original-source attribute candidates preserve the original paper records.
Selected second candidates preserve the native source's already changed paper.
Neither outcome repairs a source or accepts the original native round trip.
The full audit reproduces offline; CI adds its complete JSON comparison. Exact
import-versus-save responsibility, current rendered paper acceptance and the rest
of the 322/321 strict queue remain unestablished. No source/comparator is changed.

## 222. Inspect every concurrent source and candidate model view

Actually view all twenty retained concurrent model images: source and candidate
overview, asset1, labels1, asset2 and labels2 for each encoding case. Bind every
view to its original archive-member SHA-256 and decoded pixel hash. The declared
MODEL and SERIAL changes are visible in detail views. The overview text is too
small for field verification; existing CP1251 rotations, line intersections and
the test-profile DejaVu substitution remain explicit limitations. Exact foreign
field values/editability rest on the separate native checks, not screenshots.
No new non-label displacement was observed; the existing frozen pixel results
remain the measured evidence. This is same-agent visual inspection, not an
independent engineering, operator or paper review.

## 223. Run the second revision through unchanged native save and reopen

Freeze exact actual native concurrent returns, selected one-value second plans,
retained candidate bytes and preparation before native execution. The preparation
replays the original complete packets and independently binds each new source to
the original saved native return. Preserve original preparation lineage, all
original UI/observer/resource/configuration methods and strict/byte criteria.

All four matched second-revision runs terminate normally: native, controller,
container and original host zero. No-edit receipts retain 61 observations and
four editable-field checks; one-edit receipts retain 67 observations, six field
checks and one actual committed MODEL correction. Each has ten views/40 images.
Both assets, foreign fields and the fictional concurrent SERIAL remain exact.
Every native save still has 453 unexpected strict differences. Re-saving a native
source is therefore not evidence that strict preservation has stabilized.

The selected source-preserving candidates still match their previously selected
bytes with zero unexpected strict differences and independent source/plan byte
reconstruction. No native differences are imported into those candidates.
Five offline control methods pass: four complete externally pinned packet replays
and ten negative source/plan reindexing, missing MODEL commit, foreign-field
editability and hidden-controller controls. All run without skips in 193.460 s.
No native restart or comparison waiver is used.

Pin both baseline/edit returns before launching the separately declared fresh
four-file receivers. Those two receivers are live; no completion, new pixel or
new visual result is inferred. Paper display, final freezing and fresh reserved
transfer remain open. Original 322/321 and new 453 preservation failures remain.

## 224. Receive actual native corrections under the original request

Use the unchanged own-input receiving command for an initial actual concurrent
return, its actual native second return under the same original drawing/plan,
and a separately identified selected-native-source comparison. Bind supplied
second-return DXFs to their original complete archive members. Four actual CLI
invocations include complete portable replay; no bespoke finding generator runs.

The original-scope resubmission has eight current items: both requested MODELs
are supported in each case, SERIAL remains unrequested in each, and 321/320
original-source strict differences remain. Its basis-change list is empty because
the original source and instructions are unchanged. The selected-source packet
shows the one correct MODEL and 453 strict differences per case. These baselines
answer different questions; their drawing-record counts are not added or used
as counts of assets. Both complete briefs/source histories remain linked.
Authorized receiving and every engineering disposition stay pending. The whole
portable original-scope brief reproduces, retaining both SERIAL findings and
preservation queues. No visual-reading, installed-state or human benefit result
is inferred from this actual software receiving exercise.

## 225. Finish second-revision receiving without changing the method

Both original fresh four-file receiver handles terminate normally with native,
controller, container and host exits zero. Each retains 231 helper calls, 115
observations, eight editable-field checks, twenty views/eighty images and zero
edits. Complete archives and external identities retain the actual executions.
The original second adapter replays both packets. Its unchanged pixel recipe
gives thirty comparisons with zero outside-region pixels and twenty exact frame
identities. The combined offline replayer reproduces both full receipts, all
pixel results/difference images and twenty actually inspected source/candidate
model images. No native process was restarted after an observation wait.

The selected MODEL correction is visible and concurrent SERIAL retained. Existing
CP1251 labels are upside down, geometry crosses text, overview text is too small
for complete field checking and some long literal-brace identity text extends
beyond the fixed detail canvas. Exact complete field identities/editability use
the separate native observations. Do not enlarge cameras or masks to turn these
limits into a readability pass. Every native second save still has453unexpected
strict differences; the completed receiver is not a preservation pass.

## 226. Finish paper observation and retain failed readable delivery

Declare the bounded paper check before execution and pin all fourteen exact
inputs, original-derived frames, driver, configuration identity and native image
at a7c386b. Reuse the existing offscreen native bitmap exporter and corrected
X/Y/width/height conversion; do not build another UI recorder. All fourteen
processes and the original host/container exit normally. Source bytes remain
unchanged. Retain original commands, output/error streams, images and terminal
inspection, excluding configuration contents.

Actually inspect all fourteen images. Twelve case sheets are blank except the
native trial mark: originals, value candidates, no-edit/concurrent returns,
selected second candidates and second native returns. The repeated exposed
public-adapted viewport/text control displays six examples and matches exactly;
it differs from a blank case image at122616pixels. All ten case comparisons have
zero changed pixels, which is equal-blank failure, not readable delivery. The
earlier raw record audit independently retains the original missing-main
dependency and the native loss of the display viewport/settings. No source
repair, typography acceptance or broad vendor failure is inferred.

The full source/provenance/command/pixel replay passes. Two control test methods
pass without skips in10.632seconds: complete original-result reproduction and
four reindexed wrong-camera, omitted-command, failed-container and replaced-source
subcontrols. The engineer/manager scope page separates useful original-request
receiving, source-preserving attribute proposals, failed native full saves and
failed paper delivery. Final-method freeze and newly reserved transfer remain
unfinished; engineering/company acceptance is never inferred.

## 227. Compare exact generated pixels across PNG encodings

The actual427a14b CI job reproduces complete second-receiver reports but fails
regenerated PNG byte equality. Recompute all thirty difference images on Linux,
first with installed Pillow10.2 and then CI's exact pinned Pillow12.2 wheel.
Both original containers terminate0: all thirty PNG encodings differ and all
thirty decoded pixel arrays, modes and sizes match exactly. Retain complete
per-image results and the actual failed-job excerpt. The corrected replayer
compares generated PNG pixels exactly, with original archive/image byte pins
unchanged. Two focused test methods allow alternate compression and reject a
single changed pixel or omitted image. The complete corrected replay passes
locally. New exact-head CI remains required; no native or comparator gate waived.

## 228. Freeze the method and report every reserved case

Commit the final bounded plan/development at e9e5464,55method/contracts freeze
at f5f53ef, all ten admitted input identities at f9f2c4d, and native preparation/
launch pins at392b8b8 before the corresponding executions. Six same-author new
procedural fixtures cover encoding/version/mirror/rotation/foreign/literal cases.
Four public files are selected from pinned metadata before content download,
excluding retained repository DXF blobs. Exact originals/licenses and authored
identity adaptations remain explicit; this is not independent plant truth.

All ten value candidates pass unchanged strict and independent reconstruction.
The matched library baseline has82strict differences onR12 and zero on the
other nine, but all ten fail byte reconstruction. All42applicable planted
losses are detected by both checks; all90refusals preserve existing outputs.
Conflicting returns and selected corrections retain one collateral difference
under every original request, pending decisions and portable brief equality.
The complete second software run and offline reproduction match all results.

Actual native API edit/save/document reopen plus fresh-process reads match the
complete supplied fields on all ten. All40native saves across default/R15 and
no-edit/edit roles fail strict preservation. Thirty actual native model/paper
exports terminate normally with unchanged sources. All images are actually
inspected. The five newly authored paper cases display content, unlike the
older known-problem sheets; no older source is repaired or result replaced.
Small/rotated/overlapping labels, native trial marks and missing Chinese glyphs
prevent complete readable delivery. A pre-publication analysis mistake compared
palette indices before decoding, falsely yielding zero differences; retain that
diagnostic, decode each input first, and cover one-pixel/reindex controls.
No frozen native method, camera, mask, font, strict or byte checker changes.

Complete software/API/render archives and external pins replay offline without
models, network or native calls. Two predetermined actual UI cases are still
running; fresh four-file receiving and final audit remain unfinished. The frozen
UI packager's missing json import is documented; a separate bounded retention
helper packages the unchanged receiver outputs. No whole CAD qualification,
human review-time benefit, plant correctness or company release is claimed.

Final evidence-retention follow-up: complete API comparisons compress losslessly
from55.5MB to138436bytes, with exact original raw SHA/size plus a readable summary.
The new UI archive helper initially omits original runtime cache bytes, so a
standalone replay correctly refuses full-inventory mismatch. Retain those exact
cache bytes in a supplemental bounded archive; restore the exact configuration
only from its already-public pre-final externally pinned parent packet. Every
original inventory file/size/hash is still required by the frozen receiver.
All three completed packets replay: public baseline/edit each298strictdifferences,
authored foreign baseline334. Original native execution and55method hashes are
unchanged; the fourth edited execution is still running. No cache/config omission
is waived and no incomplete packet is silently relabeled complete.

## 229. Complete the reserved UI saves before fresh receiving

The original three-asset edited execution terminates normally without a restart.
All three requested MODEL edits commit, with195helper calls,97observations,
12editable-field checks,14views and56images. It retains334strict differences,
matching its no-edit baseline's count. The public baseline/edit each retain298.
All four original actual UI executions now finish; successful field operation
remains separate from failed full-save preservation.

Retain the fourth original packet plus exact runtime caches beside it. The
unchanged receiver reproduces its complete inventory and result. All55frozen
method identities still match. Pin the four exact returned DXFs, completed parent
archives, prepared source/config identities and fresh-host driver before native
launch at commit e3c7899. Both original fresh four-file receivers then start in
new containers, using the unchanged method. No new source, camera, font or mask
variant is introduced. Their receiving/pixel/actual-visual gates and final CI
remain unfinished. No independent plant or organizational acceptance is inferred.

## 230. Complete fresh public receiving and inspect every model frame

The original reserved public four-file receiver exits normally, with159helper
calls,79observations, four editability checks, twelve views/48images and zero
edits. Complete inventory/source/parent/field/host replay succeeds, retaining
all actual runtime bytes and using the exact already-public configuration.
The frozen pixel method gives nine comparisons with zero outside-region pixels
and six exact identities. Every source/candidate overview/asset/label frame is
actually viewed. The declared QUAL-BEFORE to QUAL-AFTER change and complete
asset labels are visible. The separate long disclaimer is clipped in detail
frames and visible in overview; the label-detail frame also clips the symbol,
which is shown in overview. Font substitution and paper/engineering limits
remain explicit. Original native saves still have298strict differences each.

Bind all six actual images by archive member, original byte hash, decoded pixel
hash, mode and dimensions. Retain the exact original generated difference images;
offline replay reproduces the entire frozen pixel result and exact decoded
pixels/mode/size, with original artifact byte pins unchanged. The completed-case
inventory requires every source/candidate frame, not a favorable subset.
The public full packet and complete pixel/image-binding replay both pass.

Both757a586 CIs now succeed, as does154da39 push CI. Its actual log reports98/98
programs passed, zero failed and37individual unittest cases skipped; the native
handoff/receiving/resubmission programs pass. This is not a zero-skip or engineering
acceptance result. Newer exact-head CI and the still-live three-asset fresh
receiver/pixels/actual-visual checks remain unfinished. No native restart or
qualification promotion is made.

## 231. Finish the declared campaign and retain the visual failure

**Correction in section 232:** the occlusion assessment below is invalid. It is
retained as the original interpretation, not a current CAD defect claim. Complete
execution counts and replay results remain valid.

The original three-asset fresh receiver finishes normally without restart:
303helper calls,151observations,12editable-field checks,28views/112images and
zero edits. Retain its complete packet and original runtime bytes; all source,
return, launch and inventory checks reproduce. All six declared UI executions
are now terminal normal. This is successful execution, not CAD acceptance.

The frozen pixel method reports21comparisons with zero outside-region changes
and14exact counterpart identities. Actual inspection of every one of its14
source/candidate views finds black rectangular occlusions interrupting unchanged
labels/identity and nearby geometry in candidate details. These lie inside the
permitted regions, so zero outside pixels does not reject them. Their rendering
cause is not isolated. Matching counterpart images and stored fields do not
close readable delivery. Retain both the automated result and failed visual
finding; no camera, mask, native source or frozen method is changed.

Combined offline replay completes normally:ten software cases,40actual API
saves,30native renders,six complete UI inventories,30fresh pixel comparisons,
20exact identities and20actually inspected source/candidate image bindings.
All55method identities still match. Add one independent image-attribution test:
copying another real image's valid member/hash/pixels into either the wrong frame
or wrong source/candidate label must refuse. Both negative controls pass. Its
initial import selected the older replay module and failed; explicit loading of
the final module corrects this test harness error without changing frozen code.

The objective audit maps every original protocol criterion and final plan step
to evidence and failed/passed boundaries. N119's declared evaluation is complete
as a negative native qualification. Full-save preservation and complete readable
delivery fail. Useful source-preserving attribute proposals and original-scope
consultant-return verification remain separate supported workflows. No new CAD
recording, source repair or reader redesign is required to publish this outcome.
Exact final-head CI remains the integration gate. Human benefit, engineering
review and company release remain unmeasured.

A separate pipeline status check reports50/52fresh stages;TE live/replay stages
are stale against changed replay-server code. No unrelated TE runtime is started
and no whole-repository freshness claim is made.

## 232. Correct an unsupported image assessment using original pixels

The initial image interpretation in A391 incorrectly reported black occlusions
in foreign candidate views. Reinspect all six actual candidate details at original
resolution and compare exact decoded source/candidate pixels. Complete identity,
TAG, MODEL, serial, DN50 and literal foreign labels are visible; all three MODEL
changes read Unit-18. Source values read Unit-17. Detail differences total218-347
pixels, with bounds around the changed final digit; the overview has36changed
pixels across three assets. This does not support the earlier occlusion claim.
Do not invent a CAD or viewer root cause for an interpretation error.

Retain the invalid visual record, original committed file hash, source commit and
per-frame decoded difference counts/bounds in UI-VISUAL-DIAGNOSTIC.json. Correct
current observations and every front-door claim. Original captured PNG hashes,
decoded pixel hashes, native files, comparison results, masks, cameras and all55
frozen methods stay unchanged. The reporter was wrong; this is not a repaired
native candidate or tuning on reserved results. A392 supersedes A391's visual
conclusion while preserving its valid execution/replay evidence.

The bounded fresh model views succeed. Native full-save preservation and broader
paper/typographic readability failures remain independently evidenced. Final CI
must reproduce the corrected reporting version before completion.


## 233. Investigate selected maintenance histories with source meanings intact

The overnight goal deepens linked maintenance intake rather than reopening CAD.
PLAN and ACCEPTANCE plus the raw-ID baseline were committed before implementation.
Inspect exact public AMPS originals and publisher workbook cells first: booked
hours are an additive signed ledger, corrections must not be dropped, labor rates
are not actual payroll, and parts quantities cannot establish consumption. The
work-order projection lacks current status; missing completion is not open work.
Code meanings without exact definitions stay unknown.

The own-input history CLI accepts configured CSV/JSON assets/orders and optional
transactions/details/labor, preserving scoped identities, original bytes/record
locators, exact recurring groups, source-linked actions and revision evidence.
The first missing-hours test failed because the subtotal was unavailable but no
action was created. Fix it and retain the case. Seventeen methods now pass,
including wrong entities, contradictory detail targets, duplicate keys, signed
corrections, unknown meanings, missing versus zero, changed mappings, tampered
history and corrected/omitted exports. Both CSV layouts and JSON reproduce the
authored facts; portable replay preserves prior packets. No independent human or
agent review, root cause or manager saving is established.

Six separately written original-column development checks pass on 933 assets,
1,612 orders, 208 transactions, 263 details and 5,268 labor entries. There are 177 exact
recurring-work groups and 82 issues, including 65 missing completions. The raw-ID
baseline also has 933 groups in this one-scope source; the fictional cross-scope
case demonstrates the actual distinction without inventing a public accuracy gain.
Actual desktop/mobile pages were visually inspected and search/table/source
navigation exercised. Retain screenshot hashes and failed selector/path attempts.

## 234. Retain the frozen public acquisition failure

Commit d7c5804 and examples/maintenance-history/FREEZE.json freeze code/contracts,
source adapter and original-column audit before reserved content acquisition.
The already selected 2024-01-15 <= evt_date < 2024-01-22 interval stops at HTTP 500
on the fourth asset batch. Five metadata files, work orders and three asset
batches survive locally; no downstream transaction/detail/labor acquisition and
no semantic packet/audit follow. The HTTP error body was not saved. Publish only
sanitized attempts/pins, not source rows/free text or identifier-bearing query
URLs. No alternate cohort or post-outcome tuning. Reserved transfer remains
unverified. The declared stopping rule allows this negative outcome to finish
the bounded evaluation, without pretending it passed or inventing plant evidence.

Discovery routes, canonical workflow/script/feature registries and existing
consulting forms now explain the useful own-input job and supplied meanings.
Independent review, real manager effort and source-owner acceptance remain open.
Full local-suite prerequisites are absent in the isolated worktree; its preflight
is not a suite pass. Source-only results and final exact-head CI are separate
integration checks.


## 235. Correct dependency classification without removing assertions

Local source-only execution passed 74 of 75 programs, with 35 skipped unittest cases
and 3 platform notices. The failure was test_delivery_examples.py: two existing
CAD evidence methods import cad_handoff and ezdxf, contradicting its source-only
classification. Move that whole program to FULL_ONLY_TESTS; retain all assertions
and execute it exactly once in full CI. No source-only success is claimed from
the original failed run. Nineteen runner-control methods pass. Repeat the
corrected source-only dispatch and require new exact-head CI. This is test-runner
classification, not another CAD qualification or an assertion waiver.


## 236. Consolidate the checked public release

2026-11-09 UTC. Inspected actual PR heads, CI, reviews/threads and branch authority.
PR46 merges as 071c2cb, then PR47 is retargeted and merges as 55ec333. The resulting
tree equals checked b200b2f. Merged-main run 42563485293 passes tests and snapshot-MCP.
The checked release suite is 99/99 programs with 37 individual cases skipped, not a
zero-skip or engineering acceptance result. Root main is fast-forwarded; new work
continues on codex/engineering-foundation-cycle. CAD full-save/paper failures and
the AMPS reserved acquisition HTTP500 remain retained negative outcomes.

## 237. Receive one unit and retain the next change

Plan/key/inventory baseline committed 28b9864 before implementation; method and
exposure frozen 2f9ce89 before second-namespace execution. Existing history and
markup packets feed a narrow authored-graph projection, existing context register
and actual Snapshot reader. All selected dossier/request JSON leaves retain
types/status/source pointers; empty objects are explicitly archive-only. Complete
original packets remain portable. No new Native generator step is necessary.

Development and procedural runs each pass 12 checks through 23 real CLI processes;
the separately frozen procedural key passes 8/8. Eight regression methods pass
without skips. The first command-flag mistake, incorrect state rubric and internal
staging/alias refusal are retained in DEVELOPMENT.json, not replaced by success.
The author knew generator/key: this is software procedural variation, not an
independent review, blind drawing read or real-site result. Final integration
checks/CI remain separate. No fresh agent is spawned under the session's rules.

One complete received packet is retained rather than every intermediate copy.
Readback compares complete nodes/relations/questions/sources, ownership and decision
history through the actual receiver; counts alone do not pass. Document-only
same-label byte changes reopen dependent answers/synthesis and leave unrelated
answers current. Changed history/drawings and an omitted note retain stale answers,
conflicts and prior originals. Duplicate/retry/wrong-base, identity/revision,
typed-loss, history reset, missing source, partial receiving and authority inflation
controls refuse. Whole-asset freshness is explicit; this is not field-level impact
analysis. Delivery history is immutable and bounded to eight retained versions.
Company receiving, authentication, continuous refresh, product imports and human
benefit remain unestablished; N052/N062/N063 are unchanged.

## 238. Trace shared lessons without promoting unrun work

2026-11-09 UTC. Web short-link opens failed for ggsbnBw7/gQ4Gb26t; ordinary HTTP
redirects resolved their canonical public posts. Reopened Johannes Van Opstal's
structured-P&ID experiment (existing A352 research/checks) and Davy Demeyer's PaC
post. The latter attribution was missing; it now links to guidance in the existing
competitive-workflows reference. Author-reported autonomous scale and paid POCs
are not independently reproduced or evidence of our own demand/capability.

A397 links all five shared references through existing A352/A354/A356/A357 and the
new bounded foundation A396. No competing capability registry, social draft repo,
LinkedIn publication or outreach is added. PaC and additional standard/simulator
adapters remain deferred pending actual versioned receiving needs and permitted
examples. Alerts remain a managed-service/integration decision. Local software
receiving does not close the open human/company trials.
