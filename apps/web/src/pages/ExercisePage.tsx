import Editor from '@monaco-editor/react'
import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { FlowNav } from '../components/FlowNav'
import { HintPanel } from '../components/HintPanel'
import { Markdown, highlightPython } from '../components/Markdown'
import { TestResults } from '../components/TestResults'
import { api } from '../lib/api'
import { runInBrowser, warmUp } from '../lib/runner'
import { useAutosave } from '../lib/useAutosave'
import type {
  BranchLink,
  Exercise,
  HarnessResult,
  SubmitResponse,
} from '../lib/types'

export function ExercisePage() {
  const { slug = '' } = useParams()
  const [exercise, setExercise] = useState<Exercise | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [code, setCode] = useState('')
  const [result, setResult] = useState<HarnessResult | null>(null)
  const [submitState, setSubmitState] = useState<SubmitResponse | null>(null)
  const [busy, setBusy] = useState<'run' | 'submit' | null>(null)
  const [error, setError] = useState<string | null>(null)

  // The "show me the answer" reveal. Deliberately separate from the hint ladder:
  // the ladder stops short of the answer, and this is the student choosing to
  // step past it. Fetched on demand and verified server-side before it arrives.
  const [answer, setAnswer] = useState<string | null>(null)
  const [answerBusy, setAnswerBusy] = useState(false)
  const [answerError, setAnswerError] = useState<string | null>(null)
  // The speed bump before the reveal. It used to be window.confirm(), which is
  // an OS dialog dropped into the middle of the most considered moment in the
  // product -- and one that cannot say, in the app's own voice, what is about to
  // happen or why the hints are worth trying first.
  const [askingForAnswer, setAskingForAnswer] = useState(false)
  const answerRef = useRef<HTMLElement | null>(null)

  // One hint display, fed by two sources: the ladder pushing one after a failed
  // submit, and the student pulling one with the button. Whichever raised the
  // level most recently wins; the ratchet means it only ever climbs.
  const [hint, setHint] = useState<{
    level: number
    text: string | null
    exhausted: boolean
  } | null>(null)
  const [hintBusy, setHintBusy] = useState(false)
  const [hintError, setHintError] = useState<string | null>(null)

  // Practice the tutor built off THIS lesson -- shown as links at the top and
  // bottom-right so a learner can jump to a branch from its parent, not only
  // from the chat where it was made.
  const [branches, setBranches] = useState<BranchLink[]>([])

  // The last browser verdict, kept so Submit can send it for divergence
  // checking. Only valid for the exact code that produced it -- see below.
  const lastRun = useRef<{ code: string; result: HarnessResult } | null>(null)

  useEffect(() => {
    warmUp() // start the ~10MB Pyodide download now, not on first Run
    let cancelled = false

    async function load() {
      try {
        const data = await api.exercise(slug)
        if (cancelled) return
        setExercise(data)

        // Restore whatever they last had in the editor. Falls back to the
        // starter code on a first visit, or if the draft fetch fails -- an
        // unreachable draft must never leave someone with an empty editor.
        let restored = data.starter_code
        try {
          const draft = await api.getDraft(slug)
          if (draft && draft.code) restored = draft.code
        } catch {
          /* keep the starter code */
        }
        if (cancelled) return
        setCode(restored)

        // Opening the sitting starts the time-on-task clock server-side. It has
        // to happen on mount rather than on first Run: the interval before the
        // first Run is thinking time, and thinking time is exactly what the
        // theme hypothesis predicts will differ between conditions.
        const session = await api.startSession(slug)
        if (!cancelled) setSessionId(session.session_id)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err))
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [slug])

  // Any practice already branched off this lesson, so the links can show on
  // arrival -- not just after making a new one this session.
  useEffect(() => {
    let cancelled = false
    api
      .branches(slug)
      .then((b) => !cancelled && setBranches(b))
      .catch(() => {
        /* links are a bonus; never block the exercise on them */
      })
    return () => {
      cancelled = true
    }
  }, [slug])

  const autosave = useAutosave(
    (value: string) => api.saveDraft(slug, value),
    // Nothing to save against until the exercise has loaded.
    { enabled: Boolean(exercise) }
  )

  function handleCodeChange(value: string) {
    setCode(value)
    autosave.schedule(value)
  }

  async function handleRequestHint() {
    if (!sessionId || hintBusy) return
    setHintBusy(true)
    setHintError(null)
    try {
      const res = await api.requestHint(slug, sessionId)
      setHint({ level: res.level, text: res.hint, exhausted: res.exhausted })
    } catch (err) {
      setHintError(err instanceof Error ? err.message : String(err))
    } finally {
      setHintBusy(false)
    }
  }

  async function handleShowAnswer() {
    setAskingForAnswer(false)
    setAnswerBusy(true)
    setAnswerError(null)
    try {
      const { solution } = await api.showAnswer(slug)
      setAnswer(solution)
      // The flow-nav shortcut lives at the top of the page; bring the reveal
      // into view so the skip actually lands somewhere visible.
      requestAnimationFrame(() =>
        answerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      )
    } catch (err) {
      setAnswerError(err instanceof Error ? err.message : String(err))
    } finally {
      setAnswerBusy(false)
    }
  }

  function loadAnswerIntoEditor() {
    if (answer == null) return
    setCode(answer)
    autosave.schedule(answer)
  }

  async function handleReset() {
    if (!exercise) return
    const ok = window.confirm(
      'Start again from the original code? What you have written will be lost.'
    )
    if (!ok) return
    await api.resetDraft(slug)
    setCode(exercise.starter_code)
    setResult(null)
    setSubmitState(null)
  }

  async function handleRun() {
    if (!exercise) return
    setBusy('run')
    setError(null)
    try {
      const harnessResult = await runInBrowser(code, exercise.entrypoint, exercise.tests)
      setResult(harnessResult)
      lastRun.current = { code, result: harnessResult }

      // Log the Run as behaviour. Iteration is most of the learning signal, and
      // a dataset of only Submits would show the outcome with the process cut
      // out. Fire-and-forget: a logging failure must never block a student.
      if (sessionId) {
        api
          .submit({
            exercise_id: exercise.id,
            session_id: sessionId,
            code,
            run_mode: 'run',
            client_results: harnessResult,
          })
          .catch(() => {})
      }
    } finally {
      setBusy(null)
    }
  }

  async function handleSubmit() {
    if (!exercise || !sessionId) return
    setBusy('submit')
    setError(null)
    // Make sure the draft matches what's being graded before we send it.
    autosave.flush()
    try {
      // Only send the browser verdict if it was produced by the code being
      // submitted. Sending a stale verdict would raise false divergence alarms
      // and pollute the incident signal -- which needs to stay trustworthy,
      // because it's how we find out the two Pythons have drifted.
      const client =
        lastRun.current?.code === code ? lastRun.current.result : null

      const response = await api.submit({
        exercise_id: exercise.id,
        session_id: sessionId,
        code,
        run_mode: 'submit',
        client_results: client,
      })
      setSubmitState(response)
      setResult(response.test_results)
      // The ladder may have pushed a hint. Fold it into the shared display, but
      // never clear an existing one -- the ladder is a ratchet.
      if (response.hint) {
        setHint({
          level: response.hint_level,
          text: response.hint,
          exhausted: response.hint_level >= 4,
        })
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(null)
    }
  }

  if (error && !exercise) return <p className="panel panel-error">{error}</p>
  if (!exercise) return <p className="muted">Loading…</p>

  return (
    <div className="exercise-page">
      <FlowNav current="create" slug={slug} />

      {branches.length > 0 && (
        <div className="branch-banner">
          <span className="muted small">Practice you built from this lesson:</span>
          {branches.map((b) => (
            <Link key={b.slug} to={`/exercise/${b.slug}`} className="branch-chip">
              {b.title}
              {b.status === 'solved' && (
                <span className="branch-done" aria-hidden>
                  {' '}
                  ✓
                </span>
              )}
            </Link>
          ))}
        </div>
      )}

      <div className="exercise">
      <section className="prompt">
        <h1>{exercise.title}</h1>
        <div className="prompt-body">
          <Markdown source={exercise.prompt_md} />
        </div>
      </section>

      <section className="workspace">
        <Editor
          height="420px"
          defaultLanguage="python"
          theme="vs-dark"
          value={code}
          onChange={(value) => handleCodeChange(value ?? '')}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            scrollBeyondLastLine: false,
            tabSize: 4,
            // The starter code's docstring is the task, and it was running off
            // the right edge with only a horizontal scrollbar to find it --
            // """Return the names of quests that aren't done and are past thei|
            // A beginner reading their own editor should not have to scroll
            // sideways to discover what they were asked to do.
            wordWrap: 'on',
            padding: { top: 14, bottom: 14 },
          }}
        />

        <div className="actions">
          <button onClick={handleRun} disabled={busy !== null}>
            {busy === 'run' ? 'Running…' : 'Run'}
          </button>
          <button
            className="primary"
            onClick={handleSubmit}
            disabled={busy !== null || !sessionId}
          >
            {busy === 'submit' ? 'Checking…' : 'Submit'}
          </button>
          <SaveBadge state={autosave.state} />
          <button type="button" className="link" onClick={handleReset}>
            Start again
          </button>
        </div>

        {/* One explanation, not two. TestResults said the same thing again a
            few hundred pixels below ("Hit Run when you want to see what your
            code does... nothing here is graded"), so a student read the same
            reassurance twice and neither one felt worth reading. */}
        <p className="muted small">
          <strong>Run</strong> is instant and private. <strong>Submit</strong> is
          the one that counts, as many times as you like. Your code saves itself
          as you type.
        </p>

        {error && <p className="panel panel-error">{error}</p>}

        {submitState?.passed && (
          <div className="panel panel-pass solved">
            {/* A small moment of celebration. Solving your first program is a
                genuinely big deal and the interface should act like it --
                but it stays a one-off flourish, not a points economy. */}
            <div className="confetti" aria-hidden>
              {Array.from({ length: 14 }).map((_, i) => (
                <span
                  key={i}
                  style={{
                    left: `${(i * 7 + 4) % 100}%`,
                    animationDelay: `${(i % 5) * 0.08}s`,
                    ['--spin' as string]: `${(i % 2 ? 1 : -1) * 180}deg`,
                  }}
                />
              ))}
            </div>
            <h3>Solved it. All checks passing.</h3>
            <p>
              {submitState.attempt_number === 1
                ? 'First try. '
                : `${submitState.attempt_number} attempts — every one of them counted. `}
              Worth talking it through and noting what tripped you up while
              it&rsquo;s fresh.
            </p>
            <Link className="btn btn-primary" to={`/exercise/${slug}/reflect`}>
              Reflect on this →
            </Link>
          </div>
        )}

        <TestResults
          result={result}
          translatedError={submitState?.translated_error}
        />

        {!submitState?.passed && (
          <div className="hint-control">
            <button
              type="button"
              onClick={handleRequestHint}
              disabled={hintBusy || !sessionId || hint?.exhausted}
            >
              {hintBusy
                ? 'Finding a hint…'
                : hint
                  ? 'Another hint'
                  : 'Need a hint?'}
            </button>
            {hint?.exhausted && (
              <span className="muted small">
                That&rsquo;s the last hint — the worked answer is just below.
              </span>
            )}
            {hintError && <p className="panel panel-error small">{hintError}</p>}
          </div>
        )}

        {hint && <HintPanel level={hint.level} hint={hint.text} />}

        {/* Offered only once the hints have run their course. Before that the
            link is not shown at all rather than shown-and-refused: a control
            that exists to tell you no is worse than no control. */}
        {!submitState?.passed && (submitState?.attempt_number ?? 0) >= 6 && (
          <div className="answer-control">
            {answerBusy ? (
              // The wait is real work, not a spinner's worth of nothing: the
              // server solves the exercise fresh and runs that answer through
              // the marker -- hidden tests included -- before it is shown. Saying
              // so turns a delay into the reason the answer can be trusted.
              <div className="answer-working">
                <span className="answer-working-bar" aria-hidden>
                  <span />
                </span>
                <p className="muted small">
                  Working it out, then running it through the marker so
                  you&rsquo;re not handed a guess…
                </p>
              </div>
            ) : askingForAnswer ? (
              <div className="answer-ask">
                <p className="answer-ask-title">Show the worked answer?</p>
                <p className="muted small">
                  It&rsquo;s yours to see — you&rsquo;ve earned it. Just know the
                  hints get more specific each time you try, and that is the part
                  that actually teaches you this one.
                </p>
                <div className="answer-ask-actions">
                  <button type="button" className="btn" onClick={handleShowAnswer}>
                    Show me anyway
                  </button>
                  <button
                    type="button"
                    className="linkish"
                    onClick={() => setAskingForAnswer(false)}
                  >
                    I&rsquo;ll keep trying
                  </button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                className="link"
                onClick={() => setAskingForAnswer(true)}
              >
                Stuck? Show me the answer
              </button>
            )}
            {answerError && <p className="panel panel-error small">{answerError}</p>}
          </div>
        )}

        {answer != null && (
          <aside className="panel answer-panel" ref={answerRef}>
            <h3>
              The worked answer
              <span className="badge badge-quiet">checked against the tests</span>
            </h3>
            {/* Highlighted with the same renderer the lessons use. A worked
                answer shown as flat grey monospace is the one code block in the
                product a student most needs to read line by line. */}
            <pre className="answer-code md-code" data-lang="python">
              <code>{highlightPython(answer)}</code>
            </pre>
            <div className="actions">
              <button type="button" className="primary" onClick={loadAnswerIntoEditor}>
                Put it in my editor
              </button>
              <button type="button" className="link" onClick={() => setAnswer(null)}>
                Hide
              </button>
            </div>
            <p className="muted small">
              Reading a worked answer is fine — the real learning is typing it out
              and understanding each line. Try re-solving it from scratch after.
            </p>
          </aside>
        )}

      </section>
      </div>

      {branches.length > 0 && (
        <Link
          className="branch-fab"
          to={`/exercise/${branches[branches.length - 1].slug}`}
          title="Open the practice you built from this lesson"
        >
          <span className="branch-fab-label">Your practice</span>
          <span aria-hidden>↗</span>
        </Link>
      )}
    </div>
  )
}


function SaveBadge({ state }: { state: 'idle' | 'saving' | 'saved' | 'error' }) {
  if (state === 'idle') return null
  const label =
    state === 'saving'
      ? 'Saving…'
      : state === 'saved'
        ? 'Saved'
        : "Couldn't save — we'll keep trying"
  return (
    <span
      className={`save-badge save-${state}`}
      // polite: a save indicator changing should never interrupt someone
      // mid-sentence in a screen reader.
      aria-live="polite"
    >
      {label}
    </span>
  )
}
