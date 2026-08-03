# Architecture

CodeJourney is not a platform with an evaluation attached. It is a claim —
*concrete, engaging framing improves novice engagement and persistence* — plus
the minimum infrastructure needed to test it. Every decision below follows from
that. When a feature and the claim compete, the claim wins.

**Note on the pivot.** This project previously framed exercises around the
student's own life (autobiographical themes). That framing has been dropped. The
claim is now about *concrete, playful context* versus *abstract statement of the
same problem* — quests and league tables against "a list of records".

The experimental machinery is unchanged and still applies: `pair_id`,
`theme_variant`, and counterbalancing all work exactly as before, because the
comparison is still themed-against-generic. What changed is what "themed" means.
If anything the new claim is easier to defend, since situational-interest and
context-personalisation effects in novice programming are better evidenced than
autobiographical framing ever was.

---

## Logical separation, monolithic deployment

The design has a Feedback service, a Hints service, a Grading service and an
Analytics service. They are **Python modules in one FastAPI app**, not separate
deployments.

Three part-time second-years cannot run a microservice estate in eight weeks and
also write thirty exercises. Splitting them would buy independent scaling that
nobody needs at N≈30 participants, and cost service discovery, inter-service
auth, distributed tracing, and four deploy pipelines.

Keep the logical boundaries in the diagram — they're real, and they're enforced
by module structure. Describe the deployment as *logical separation, monolithic
deployment*. That is a mature architectural choice with a name, not a compromise
to apologise for.

**The one genuine exception is the sandbox.** Untrusted code must not share a
process with the API. That boundary is not negotiable and it is the only one.

---

## The divergence rule

This is the most important rule in the codebase.

Student code runs in two places:

| | Where | Trusted? | Graded? | Why |
|---|---|---|---|---|
| **Run** | Pyodide, in the browser | No | No | Instant, zero server cost, infinite scale. Untrusted is fine — they can only fool themselves. |
| **Submit** | Sandbox container, server-side | Yes | Yes | The only verdict that counts. |

The split is good design. It also creates a specific, project-threatening
failure mode:

> **Pyodide's Python and the server's CPython are not the same Python.**
> Different tracebacks, no threading, some stdlib missing, different float and
> dict edge cases. A student runs their code, sees green, submits, sees red —
> and gets a red they cannot explain.

That breaks "failure is teachable" at exactly the moment the pitch is being
tested, and it reads as a bug in the platform rather than a lesson. Four
defences, in order of importance:

### 1. One harness, both environments

[`packages/harness/harness.py`](../packages/harness/harness.py) is executed
verbatim in Pyodide *and* in the sandbox. The browser bundles it via a `?raw`
import at build time; the Docker image `COPY`s it. Neither side has its own copy.
If grading logic ever disagrees, it is because the interpreters disagree — never
because we wrote it twice.

### 2. Pinned in lockstep

Pyodide 0.27.x ships CPython 3.12, so the sandbox runs `python:3.12-slim`.
These two versions are pinned in `apps/api/app/config.py` and
`apps/web/src/lib/pyodide.worker.ts` and **must be bumped together**. `/health`
returns both so the frontend can assert the pair matches.

### 3. Function-based tests, never stdout matching

Tests call a named `entrypoint` and compare return values. Stdout comparison
would be the single largest source of divergence — print formatting, float repr,
and trailing whitespace differ subtly between the two. Returning values
sidesteps all of it. Float comparison carries a tolerance for the same reason
(see `_compare`).

### 4. Divergence is an incident, not a grade

When Submit receives `client_results` for identical code and the verdicts
disagree, the server sets `Submission.divergence_flag` and logs at ERROR.

**`divergence_flag` should always be false.** If it is ever true:

- it is a platform fault, never a student fault;
- those rows need inspecting, and probably excluding, before Week 8 analysis;
- it is a bug to fix that week, not a curiosity.

Stale verdicts are never sent — the client only attaches `client_results` when
the code that produced them is byte-identical to the code being submitted.
Otherwise the incident signal fills with false alarms and stops being worth
watching.

---

## The Submission table is the research dataset

Not application plumbing. `apps/api/app/models.py` is written around the Week 8
analysis, in Week 1, on purpose — the standard way a project like this fails is
discovering in Week 7 that it logged the wrong things.

| Analysis needs | Column |
|---|---|
| time-on-task | `seconds_since_exercise_start` |
| completion | `passed`, first occurrence per (user, exercise) |
| hint depth | `max_hint_level`, plus `HintEvent` for the full ladder |
| condition | `theme_variant` |
| pairing | `Exercise.pair_id` |
| counterbalancing | `User.counterbalance_group` |

Three decisions worth defending in a viva:

**`theme_variant` is denormalised onto `Submission`.** The condition is frozen at
write time rather than joined through `Exercise` at analysis time. If an
exercise is ever re-themed or re-paired mid-study, joining would silently rewrite
history.

**Time is computed server-side.** `ExerciseSession` opens when the editor mounts,
not on first Run. A client clock is adjustable, and this is a dependent variable.
More importantly, the gap before the first Run *is* thinking time — precisely the
interval the theme hypothesis predicts will differ.

**Runs are logged, not just Submits.** Iteration is most of the learning signal.
A dataset of Submits only shows outcomes with the process cut out.

---

## Consent is opt-in, reversible, and never gates access

Three rules, encoded in the schema and in `tests/test_accounts.py`:

**1. Consent never gates the platform.** A student who declines gets the entire
site — every exercise, hint, draft and journal entry. Making study participation
a condition of access would be coercive: someone who needs the exercises for
their course cannot meaningfully refuse, so their "consent" would not be consent
at all. An ethics committee should reject that design, and it would be the right
call. `consented_at` governs *analysis*, not *access*.

**2. Silence is not consent.** The signup checkbox is unticked by default, and
`consent_to_research` defaults to `False` server-side. Consent has to be an
action someone took, not one they failed to avoid.

**3. Withdrawal is one toggle, and it costs nothing.** It lives on
`/account`, next to the explanation. Withdrawing removes them from the analysis
and **does not** delete their work or their progress — leaving the study should
never cost someone the thing they came for. `consent_withdrawn_at` is recorded
separately from nulling `consented_at`, so the audit trail distinguishes "never
consented" from "consented, then withdrew". A right to withdraw that leaves no
evidence it was exercised is not much of a right.

Week 8 analysis must filter on `consented_at IS NOT NULL`. Data from
non-consenting users exists in the database — they are using the platform, and
it has to work — but it is not yours to analyse.

---

## The dashboard must not show participants their own dependent variables

`GET /progress` deliberately omits **time-on-task** and **hint depth**.

Both are Week 7 dependent variables. Showing a participant their own values
creates measurement reactivity: someone who can see *"you used hint 4"* is under
quiet pressure to avoid hints next time, and someone watching a timer works
differently from someone who isn't. The study's own instrument would start
biasing the thing it exists to measure.

Completion is different — a student obviously knows which exercises they've
solved, so surfacing it adds no distortion. It is shown.

Instructors see both numbers in the Week 6 dashboard, where reactivity isn't a
concern because the instructor isn't the participant.

`tests/test_progress.py::test_dependent_variables_are_not_exposed_to_the_participant`
asserts this and will fail if either is ever added to the payload.

This is also why the dashboard has a progress bar and nothing else — no points,
badges or streaks. Gamification was cut for scope, but it would have been wrong
here anyway: extrinsic reward is a confound in a study whose dependent variable
includes *intrinsic* motivation (IMI).

---

## `Exercise.pair_id` is the experiment

A themed exercise and its generic twin share a `pair_id`: same concept, same data
shape, same argument lists, same expected values, same hint ladder depth. **Only
the framing differs.**

Without this column there is no within-subjects comparison — only two unrelated
piles of exercises. If the twins differ in difficulty, the study measures
difficulty. If the twins' hints differ in quality, it measures hint quality. The
discipline of keeping the pair identical in every respect but framing is what
makes the result mean anything.

See [theme-concept-grid.md](./theme-concept-grid.md).

---

## Reflections never touch an LLM

Enforced structurally, not by policy.

A learning journal invites honesty about struggle, and some students will write
things they would not want machine-read. The proposal promises the system makes
no psychological judgements. Keeping the AI's eyes on **code only** is what makes
that promise structural instead of aspirational.

Concretely:

- `Reflection` has no `sentiment`, `flags`, or `summary` column, and must not
  gain one. Adding one is the first step toward breaking the guarantee.
- No service outside the reflection module reads `Reflection.body` except to
  render it to its author or to an instructor with access.
- The error translator and hint services receive tracebacks and code. Never prose.

This is also the cheapest possible answer to an ethics reviewer, which matters
in Week 1.

---

## The reflection tutor is a separate feature, walled off from the journal

The Reflect stage has two things on it, and confusing them would break the rule
above:

- **The journal** (`Reflection`, above) — private tried/stuck/fixed prose, never
  machine-read.
- **The tutor** (`services/tutor.py`, `routers/tutor.py`) — an opt-in
  friendly-teacher chat the student *starts*, scoped to the lesson and their
  code. It gauges how secure they feel and can offer to build extra practice.

The tutor is the one place an LLM enters the platform, so the boundary is drawn
sharply and structurally:

- Everything the model is told is assembled server-side in `_build_context` from
  the **exercise** and the student's **own submissions** (their code and how the
  attempts went). The browser can send only the visible conversation, so a page
  cannot inject instructions or smuggle other data in.
- It **never reads `Reflection`**. The journal and the tutor share a screen and
  nothing else; the tutor code has no access path to the journal to begin with.
  `test_tutor.py::test_tutor_never_receives_the_private_journal` asserts a saved
  journal entry cannot appear in the tutor prompt.
- Any generated practice exercise is run through the **real harness** before it
  is stored (`generate_exercise`), so a student who accepts an offer can always
  finish what they open. A model that can't produce a solvable exercise yields a
  gentle apology, never a broken lesson.
- No `ANTHROPIC_API_KEY` ⇒ the tutor is off and its endpoints degrade to a
  friendly "not switched on yet" note rather than a 500. The key is read from the
  environment and never committed.

Generated exercises are `theme=GENERIC`, `variant=GENERIC`, with an `ai-` slug
prefix so they are distinguishable from the taught curriculum in the data.

---

## The hint ladder

```
L0  run output + test results          free, immediate
L1  translated error                   automatic on any exception
L2  location                           after 2 failures or 5 min idle
L3  conceptual                         after 4 failures
L4  structural pseudocode skeleton     after 6 failures
L5  instructor flag
--  the answer                         never
```

Thresholds are per-exercise overridable via `Exercise.hint_thresholds`. That is
not a nice-to-have: it makes escalation speed a manipulable variable, which turns
the platform into a research instrument rather than a fixed opinion about
pedagogy.

The ladder is a **ratchet** — it never goes down within an exercise. Otherwise a
student could peek at L4, reset, and the mastery penalty would measure nothing.

---

## Error translation: table first, LLM second

Cost is not the problem (~30 students × 50 exercises × 5 hints ≈ 7,500 calls ≈
pocket change). **Latency and hallucination are.**

So: a deterministic table of ~25 rules covers the overwhelming majority of novice
errors. `NameError` → "You used a name Python hasn't seen yet." An LLM handles
only the long tail, if there's time.

Faster, cheaper, more reliable, and far more defensible in a report than "we
asked a model." The harness returns structured `{type, message, line}` rather
than a rendered traceback string specifically so the table can pattern-match
without re-parsing.

---

## Bearer tokens, not session cookies

The Expo companion has no cookie jar and no same-site story. Cookie sessions
would force a second auth path in Week 5. Tokens cost nothing now.

This is the general rule for the companion: **the API is designed today as if the
mobile app already exists.** That is what makes it a ~4-day job in Week 5 instead
of a three-week one.

**The companion never executes code.** No Monaco, no Pyodide. It carries lessons,
Parsons problems (touch is genuinely *better* for drag-to-order), the journal,
portfolio, and progress. Putting an editor on a phone is how this project dies.

---

## What we are deliberately not building

Cut, and defended as future work:

- **Step-through visualiser.** Guo (2013)'s entire point is that Python Tutor is
  embeddable. Building one means `sys.settrace`, heap serialisation, aliasing,
  and rendering — Guo spent a decade on it. **Embed the iframe.** Two paragraphs
  in the report about why reuse was the right call, and a headline feature for free.
- **Gamification** beyond a progress bar.
- **Discussion forum** — use the institution's.
- **Peer feedback**, **notifications**, **admin panel**.
- **Redis**, and real-time anything.

Forums and badges are the classic student-project scope-killers: lots of code,
thin contribution, nothing to write about. Roughly 40% of the original scope is
gone here with close to zero pedagogical value lost.
