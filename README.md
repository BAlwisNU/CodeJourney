# CodeJourney

Teaching beginners Python through concrete, playful projects — quests, league
tables, space missions — and by explaining what happened when their code breaks
instead of just saying "wrong."

**The reframe this repo is built around:** this is not a platform with an
evaluation attached. It is a claim — *concrete, engaging framing improves novice
engagement and persistence* — plus the minimum infrastructure needed to test it.
Every feature that serves neither the claim nor the usability study is cuttable.

Start with [`docs/architecture.md`](docs/architecture.md) and
[`docs/theme-concept-grid.md`](docs/theme-concept-grid.md). The grid is the most
important artefact in the project.

---

## The two bets

The idea makes two claims, and they are unequal:

- **Bet A — concrete, engaging framing increases motivation and persistence.**
  This is the contribution, so **this is what the evaluation must test.** Papert's
  "meaningful artefact" meant *interesting to make* — turtles, machines — which is
  exactly this, and better supported than the autobiographical framing this
  project originally proposed and has since dropped.
- **Bet B — layered feedback, visualisation, and Parsons problems help novices.**
  Well-evidenced and unoriginal. Keuning, Guo and Denny established it; Python
  Tutor, Runestone, CodeHS and Replit built it. This is machinery, not
  contribution.

The gap in Bet A is survivable — but only by being honest about it and then
testing it. Evaluating "is the code editor usable" evaluates Monaco.

---

## Quick start (no Docker)

Fastest path to a running app. Uses SQLite, so it needs no database server and
no Docker. Everything through Week 2 works this way.

```bash
# 0. Once. Use 3.12 -- it matches Pyodide's CPython, and psycopg has no 3.13/3.14
#    wheel yet. Any 3.12.x is fine.
python3.12 -m venv .venv
.venv/bin/pip install -e "apps/api[dev]"

# 1. API, on SQLite
cd apps/api
export DATABASE_URL="sqlite:///./codejourney.db"
export ENVIRONMENT=development
../../.venv/bin/python -m app.seed                    # 2 users, 1 exercise pair
../../.venv/bin/python -m uvicorn app.main:app --reload --port 8000

# 2. Web, in a second terminal
cd apps/web && npm install && npm run dev
```

Then open **http://localhost:5273**.

The port is pinned to 5273 (`strictPort` in `vite.config.ts`) rather than Vite's
default 5173. If 5273 is busy the dev server **fails loudly instead of moving to
the next free port** — that is deliberate. A drifting port lands you on one some
other project used, and a stale browser tab reloading against this server
produces confusing `outside of Vite serving allow list` errors naming a project
you aren't even working on.

Seeded logins — `student@example.com` / `instructor@example.com`, both
`password123`.

**Run** works fully (Pyodide, in your browser). **Submit** works via `LocalRunner`,
which executes student code in a subprocess on the API host. That is **not a
sandbox** — it refuses to start outside development and is replaced by
`DockerRunner` in Week 3.

### With Postgres and the real sandbox (Week 3+)

Needs Docker. Postgres is what you'll run the study on; SQLite is for local dev.

```bash
docker compose up -d db
docker build -t codejourney-sandbox:3.12 packages/harness   # the sandbox image
# then drop the DATABASE_URL export above and use the compose default
```

### Tests

No database or Docker needed — the suite runs on SQLite (see `tests/conftest.py`).

```bash
.venv/bin/python -m pytest apps/api/tests -q   # 106 tests
cd apps/web && npm run typecheck && npm run build
```

`tests/test_harness.py` covers the keystone. **Keep it green** — the shared
harness is what stops Run and Submit disagreeing.

### Troubleshooting

| Symptom | Cause |
|---|---|
| `No module named 'psycopg'` | You're on Python 3.13/3.14 — no wheel yet. Use 3.12, or SQLite as above. |
| First **Run** hangs a few seconds | Pyodide is a ~10MB download. It warms up on page load and is cached after. |
| CORS error in the browser | The API isn't in development mode. `ENVIRONMENT=development` allows any localhost port. |
| `docker: command not found` | Only needed from Week 3. The SQLite path above needs neither Docker nor Postgres. |
| `outside of Vite serving allow list`, naming a path from a **different project** | A stale browser tab from that project, reloaded against this server. Open http://localhost:5273 fresh, or hard-reload (Cmd-Shift-R). Nothing is wrong with this repo. |
| `Port 5273 is already in use` | Intentional — see above. Find it with `lsof -nP -iTCP:5273 -sTCP:LISTEN`, or change `server.port` in `vite.config.ts`. |

---

## The five-stage flow

`Connect → Plan → Create → Test and improve → Reflect`, from the proposal's
methodology. Create and Test share one page — you write and run in the same
editor, and splitting them would mean navigating away from your code to see
whether it worked.

| Stage | Route | What happens |
|---|---|---|
| **1. Connect** | `/exercises` | Pick a theme, pick a project |
| **2. Plan** | `/exercise/:slug/plan` | Lesson, quiz, Parsons warm-up |
| **3–4. Create & test** | `/exercise/:slug` | Monaco, Run/Submit, error translation, hint ladder |
| **5. Reflect** | same page | Journal: tried / stuck / fixed |
| — | `/portfolio` | Everything you've made, with the effort it took |
| — | `/instructor` | Class analytics (instructors only) |

**Nothing in Plan is a gate.** The lesson, quiz and warm-up can all be skipped,
and the quiz can be failed outright without blocking the editor. It is
scaffolding, not a checkpoint — gating the exercise on a quiz score would punish
exactly the students who most need the practice.

---

## Layout

```
packages/harness/harness.py   THE keystone. Runs in Pyodide AND the sandbox,
                              unmodified. Neither app owns a copy.
apps/api/                     FastAPI. Feedback/hints/grading/analytics are
                              MODULES, not services. One deployment.
  app/models.py               The research dataset. Read the header comment.
  app/seed.py                 The built exercise pair. Read it before writing
                              any exercise.
  app/services/grading.py     LocalRunner (dev, unsandboxed) + DockerRunner.
apps/web/                     React + Vite + Monaco + Pyodide (in a Worker).
apps/mobile/                  Expo companion. Week 5. Never executes code.
docs/                         Architecture and the grid.
```

---

## Three things not to break

**1. The divergence rule.** Pyodide's Python and the server's CPython are not the
same Python. One shared harness, versions pinned in lockstep, function-based
tests, and `Submission.divergence_flag` if they ever disagree. A flagged row is a
platform incident, never a student error. Full reasoning in
[`docs/architecture.md`](docs/architecture.md#the-divergence-rule).

**2. Reflections never touch an LLM.** A journal invites honesty about struggle,
and some students will write things they would not want machine-read. Keeping the
AI's eyes on code only is what makes "no psychological judgements" structural
instead of aspirational. There is no `sentiment` column on `Reflection` and there
must never be one.

**3. The world determines the data shape, not the strings.** `quest_1` is a
generic exercise wearing a hat. If stripping the world doesn't change the
problem, the exercise is wrong.

---

## Timeline

Build and content tracks run **in parallel from Week 1**. Exercises written in
Week 6 get piloted by nobody.

| Week | Build | Content |
|---|---|---|
| 1 | **Ethics submitted**, repo, CI, docker-compose, auth | World × concept grid designed |
| 2 | Monaco + Pyodide run loop, end-to-end, one hardcoded exercise | 10 exercises |
| 3 | Server-side submit + test harness + results UI | 20 exercises |
| 4 | Error translation table + hint ladder | 30 exercises + test cases |
| 5 | Reflection + portfolio + Parsons + **Expo companion** | Pilot with 2 friendly students |
| 6 | Mastery + recommender + instructor dashboard + Python Tutor embed | **Freeze** |
| 7 | **Evaluation with real participants** — a real week, not a squeeze | — |
| 8 | Analysis + write-up + presentation | — |

> **Ethics approval is submitted in Week 1 or the project dies in Week 7.** It
> takes weeks, it handles personal reflections, and it possibly involves sending
> code to a third party. It is blocking, and it is not code — no amount of
> building unblocks it.

### Team split

- **A — execution + assessment.** Sandbox, harness, error translation, hints. The
  hard core.
- **B — frontend.** Editor, lessons, Parsons, portfolio, dashboards, Expo companion.
- **C — content + learning design + backend CRUD + evaluation instruments.**

**C's job looks lightest and isn't.** Writing 30 good themed exercises with hidden
test cases is brutal, and it determines whether the central claim can be tested at
all. Do not let C become "the one who does the report."

---

## Evaluation

You **cannot** demonstrate learning gains in 8 weeks with N≈10. Don't try — an
underpowered study gets torn apart. What you can do:

- **Usability:** SUS questionnaire + think-aloud. N=8–12 finds most usability
  problems — a well-established result, which makes the small N a *justified
  design choice* rather than an apology.
- **The claim test:** within-subjects, themed vs generic version of the same
  exercise. Measure time-on-task, completion, hint depth, and self-reported
  motivation (IMI). **Counterbalance the order** — `User.counterbalance_group` is
  assigned once at registration and never recomputed.

The schema was designed around this analysis in Week 1. See
[`apps/api/app/models.py`](apps/api/app/models.py).

---

## Deliberately not built

Step-through visualiser (embed Python Tutor — Guo's paper's whole point is that
it's embeddable), gamification beyond a progress bar, discussion forum (use the
institution's), peer feedback, notifications, admin panel, Redis, real-time
anything.

That's ~40% of the original scope with close to zero pedagogical value lost.
Forums and badges are the classic student-project scope-killers: lots of code,
thin contribution, nothing to write about.
