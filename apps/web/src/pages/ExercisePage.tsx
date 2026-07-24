import Editor from '@monaco-editor/react'
import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'

import { FlowNav } from '../components/FlowNav'
import { HintPanel } from '../components/HintPanel'
import { Journal } from '../components/Journal'
import { Markdown } from '../components/Markdown'
import { TestResults } from '../components/TestResults'
import { api } from '../lib/api'
import { runInBrowser, warmUp } from '../lib/runner'
import { useAutosave } from '../lib/useAutosave'
import type { Exercise, HarnessResult, SubmitResponse } from '../lib/types'

export function ExercisePage() {
  const { slug = '' } = useParams()
  const [exercise, setExercise] = useState<Exercise | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [code, setCode] = useState('')
  const [result, setResult] = useState<HarnessResult | null>(null)
  const [submitState, setSubmitState] = useState<SubmitResponse | null>(null)
  const [busy, setBusy] = useState<'run' | 'submit' | null>(null)
  const [error, setError] = useState<string | null>(null)

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

  const autosave = useAutosave(
    (value: string) => api.saveDraft(slug, value),
    // Nothing to save against until the exercise has loaded.
    { enabled: Boolean(exercise) }
  )

  function handleCodeChange(value: string) {
    setCode(value)
    autosave.schedule(value)
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
      <FlowNav current={submitState?.passed ? 'reflect' : 'create'} slug={slug} />

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

        <p className="muted small">
          Run is instant and private. Submit is the one that counts — and you can
          submit as many times as you want. Your code saves itself as you type.
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
              Worth writing down what tripped you up while it&rsquo;s fresh.
            </p>
          </div>
        )}

        <TestResults
          result={result}
          translatedError={submitState?.translated_error}
        />

        {submitState && (
          <HintPanel level={submitState.hint_level} hint={submitState.hint} />
        )}

        <Journal exerciseId={exercise.id} />
      </section>
      </div>
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
