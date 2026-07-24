# The theme × concept grid

**This is the most important artefact in the project.** If it's good, everything
downstream works. If it's an afterthought, nothing downstream can save it.

*Status: Week 2 deliverable. Cell 1 (Games × Lists) is built and seeded. The
other 29 are specified below and need writing.*

---

## The rule

> **The theme determines the data shape and the problem — not the strings.**

This is the way this project quietly fails: you build everything, and the themes
turn out to be variable names.

```python
# NOT a themed exercise:
"Write a function that adds two numbers. Call them quest_1 and quest_2."
```

That is a generic exercise wearing a hat. A marker sees through it instantly, and
so will a participant — which means the study measures nothing, because the
manipulation didn't happen.

The test for any cell below: **if you strip the theme, does the problem change?**
If only the identifiers change, the cell is wrong and needs rewriting.

Each theme generates a genuinely different data structure. That's what makes
theme choice change *what you build*, not *what you name it* — and it makes
curriculum design tractable: a 5×6 grid to fill in, not an open-ended writing task.

---

## Worlds and the shapes they generate

| World | Data shape | Concepts it naturally teaches |
|---|---|---|
| 🎮 **Games & quests** | Records with state | Lists, filtering, booleans, min/max |
| 🏆 **Sports & leagues** | Aggregation over groups | Dicts, counting, grouping, file I/O |
| 🚀 **Space missions** | Sequences & order | Lists, ordering, running totals, formatting |
| 🎧 **Music & playlists** | Pairings & patterns | Dicts of lists, sets, matching |
| 📖 **Stories & words** | Generation & transformation | Strings, functions, randomness |

These are concrete and playful: things a beginner can picture and wants to see
working. **Nothing here asks a student to disclose anything about themselves** —
that framing was tried and dropped.

---

## The grid

30 cells. ✅ = built and seeded.

### 🎮 Games & quests — *records with state*

| Concept | Exercise | What the data looks like |
|---|---|---|
| Lists ✅ | **The quest log** — which quests expired unfinished | `[{name, due_day, done}]` |
| Dicts | **Inventory** — do you have what the recipe needs? | `{item: count}` |
| Loops | **Boss fight** — how many turns until it drops? | hp, damage per turn |
| Strings | **Save-game names** — parse `"lvl12:rogue:840xp"` | `["lvl12:rogue:840xp", ...]` |
| Functions | **Character sheet** — `attack()`, `defend()`, `level_up()` | stats + helpers |
| File I/O | **The high score table** — read scores, rank them | `scores.txt` |

### 🏆 Sports & leagues — *aggregation over groups*

| Concept | Exercise | What the data looks like |
|---|---|---|
| Lists | **Top scorer** — most goals across a season | `[{player, goals}]` |
| Dicts | **The league table** — points per team from results | `[{home, away, score}]` → `{team: pts}` |
| Loops | **Winning streak** — longest unbeaten run | `["W","W","D","L", ...]` |
| Strings | **Match report** — format a results summary line | grouped totals |
| Functions | **One `tally` for three questions** | `[records]`, key fn |
| File I/O | **The season file** — read a CSV, build the table | `season.csv` |

### 🚀 Space missions — *sequences & order*

| Concept | Exercise | What the data looks like |
|---|---|---|
| Lists | **Flight plan** — waypoints in order, total distance | `[{waypoint, km}]` |
| Dicts | **Planet lookup** — details by name | `{planet: {...}}` |
| Loops | **Fuel check** — does it make it, or run dry? | `[burns]`, tank |
| Strings | **Mission log** — build timestamped entries | events + times |
| Functions | **Trajectory** — compose `legs()`, `total()`, `longest()` | flight plan |
| File I/O | **Telemetry** — read a log, find the anomaly | `telemetry.txt` |

### 🎧 Music & playlists — *pairings & patterns*

| Concept | Exercise | What the data looks like |
|---|---|---|
| Lists | **Most played** — which track tops the list | `[{track, plays}]` |
| Dicts | **Shared taste** — tracks two playlists have in common | `{person: [tracks]}` |
| Loops | **The rhythm** — build a repeating pattern | beats per bar |
| Strings | **Setlist printer** — numbered, padded, tidy | `[tracks]` |
| Functions | **Matching** — `overlap()`, `unique_to()`, `merge()` | two playlists |
| File I/O | **The library** — read tracks, group by artist | `library.txt` |

### 📖 Stories & words — *generation & transformation*

| Concept | Exercise | What the data looks like |
|---|---|---|
| Lists | **Word counts** — longest, shortest, average | `[words]` |
| Dicts | **Word frequency** — which word appears most | text → `{word: n}` |
| Loops | **Story generator** — build lines from word banks | `[[words], [words]]` |
| Strings | **Title case, properly** — transform a passage | text |
| Functions | **The generator** — `line()`, `stanza()`, `story()` | word banks |
| File I/O | **The manuscript** — read a file, summarise it | `story.txt` |

---

## Scoping: you do NOT need 60 exercises

**Worth catching now, because it's a factor-of-two error waiting to happen.**

The grid is 30 themed exercises. Every exercise used in the within-subjects
comparison also needs a **generic twin** — same concept, same data shape, same
tests, same difficulty, only the framing stripped. Twin all 30 and you're writing
60 exercises, with test cases and three authored hint levels each. That is not
happening in eight weeks, and if it's attempted, the exercises will be bad —
which is worse than having fewer, because bad exercises can't test the claim.

**They don't all need twins.** Only the **study set** does.

| Set | Count | Purpose |
|---|---|---|
| **Study set** | ~6 pairs = **12 exercises** | The experiment. Rigidly matched twins. Counterbalanced. |
| **Platform set** | ~18 themed only | Everything else students work through. No twins needed. |
| **Total** | **~30 exercises** | Matches the original estimate. |

Six pairs is enough for a within-subjects design with N≈10 (each participant sees
three themed and three generic, order counterbalanced) and it keeps twin-matching
tight enough to defend. Twinning everything would produce sixty mediocre
exercises and a weaker study.

**Suggested study set** — one per concept, so concept is held constant across
conditions and can't confound the result:

| Concept | Themed | World |
|---|---|---|
| Lists ✅ | The quest log | 🎮 Games |
| Dicts | The league table | 🏆 Sports |
| Loops | Fuel check | 🚀 Space |
| Strings | Setlist printer | 🎧 Music |
| Functions | The generator | 📖 Stories |
| File I/O | The season file | 🏆 Sports |

---

## Rules for writing a twin

The twin is the control condition. If it differs from its themed partner in
*anything* but framing, the study measures that thing instead.

Must be **identical**:

- concept and data shape
- `tests` — the same `args` and `expected`, verbatim
- number of visible vs hidden tests
- hint ladder depth, and hint *specificity* at each level
- starter code structure and comment density

Must **differ**:

- the prompt's framing and narrative
- the entrypoint and variable names (a generic exercise can't be called
  `expired_quests` — that would leak the world into the control)

The trap: **writing worse hints for the generic twin.** It happens without anyone
deciding to do it — the themed version is more fun to write, so it gets more care.
Then the study finds that themed exercises help, and what it actually found is
that better hints help. Compare the two hint sets side by side before freezing.

See `apps/api/app/seed.py` for the built pair — the two are deliberately
line-for-line parallel.

---

## Who writes these

**Team member C**, and their job looks lightest and isn't.

Thirty good themed exercises with hidden test cases, three authored hint levels
each, and six rigidly matched twins is brutal, invisible labour that appears
nowhere in a Gantt chart. It also **determines whether the central claim can be
tested at all**.

Do not let C become "the one who does the report."

The content track runs *parallel* to the build track from Week 1 — see the
timeline in [`README.md`](../README.md). Exercises written in Week 6 are exercises
that get piloted by nobody.
