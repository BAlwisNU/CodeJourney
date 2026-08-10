import { useState } from 'react'

import { API_BASE, token } from '../lib/api'

/**
 * Writing a project its own course.
 *
 * The library teaches lists and loops in the abstract — quests, league tables,
 * a quest log. That is fine, and it is not what somebody who came here to build
 * a running tracker asked for. This asks the coach to design a ladder of
 * lessons for *their* project and then write each one, set in their own world,
 * with functions they could paste straight into the thing they are making.
 *
 * Reported as it happens, because it genuinely takes minutes: every lesson is
 * a model call plus a real harness run proving the answer passes before it is
 * shown. A progress bar would be a lie about a process whose steps have names,
 * so the names are shown instead — the plan first, then each lesson ticking off
 * as it lands.
 *
 * Each lesson is committed as it passes, so closing the tab half way keeps the
 * three that finished rather than losing all six.
 */

type Planned = { title: string; concept: string }

export function CourseBuilder({
  projectId,
  projectTitle,
  onFinished,
}: {
  projectId: string
  projectTitle: string
  /** Fired once at the end, so the board can reload with the new lessons. */
  onFinished: () => void
}) {
  const [busy, setBusy] = useState(false)
  const [plan, setPlan] = useState<Planned[] | null>(null)
  const [done, setDone] = useState<string[]>([])
  const [skipped, setSkipped] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)

  async function build() {
    setBusy(true)
    setError(null)
    setPlan(null)
    setDone([])
    setSkipped([])

    try {
      const response = await fetch(
        `${API_BASE}/projects/${projectId}/course/stream`,
        {
          method: 'POST',
          headers: { Authorization: `Bearer ${token.get() ?? ''}` },
        }
      )
      if (!response.ok || !response.body) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload?.detail ?? 'Could not start writing the course.')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let carry = ''
      for (;;) {
        const { done: finished, value } = await reader.read()
        if (finished) break
        carry += decoder.decode(value, { stream: true })
        const lines = carry.split('\n')
        // The tail may be half a line; keep it for the next read.
        carry = lines.pop() ?? ''
        for (const line of lines) {
          if (!line.trim()) continue
          let event: Record<string, unknown>
          try {
            event = JSON.parse(line)
          } catch {
            continue
          }
          if (event.type === 'planned') setPlan(event.lessons as Planned[])
          else if (event.type === 'lesson') setDone((d) => [...d, String(event.title)])
          else if (event.type === 'skipped')
            setSkipped((s) => [...s, String(event.title)])
          else if (event.type === 'error') setError(String(event.message))
        }
      }
      onFinished()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  if (!busy && !plan) {
    return (
      <div className="course-offer">
        <p className="course-offer-title">
          Want lessons written for <strong>{projectTitle}</strong>?
        </p>
        <p className="muted small">
          Your coach will design a short course — four to seven lessons, in
          order, each one about your project rather than about quests. It takes
          a couple of minutes, because every lesson is checked before you see it.
        </p>
        <button type="button" className="btn btn-primary" onClick={() => void build()}>
          Write my lessons
        </button>
        {error && <p className="panel panel-error small">{error}</p>}
      </div>
    )
  }

  return (
    <div className="course-run">
      <p className="course-run-head">
        {plan
          ? `Writing ${plan.length} lessons for ${projectTitle}`
          : 'Sketching the course…'}
        <span className="muted small">
          {plan ? ` ${done.length} of ${plan.length} done` : ''}
        </span>
      </p>

      {/* The plan, with each lesson ticking off as it is written and checked.
          Named steps rather than a percentage: these have names, and watching
          them land is the only honest account of a two-minute wait. */}
      {plan && (
        <ol className="course-steps">
          {plan.map((step) => {
            const built = done.includes(step.title)
            const failed = skipped.includes(step.title)
            const state = built ? 'is-done' : failed ? 'is-skipped' : ''
            return (
              <li key={step.title} className={`course-step ${state}`}>
                <span className="course-tick" aria-hidden>
                  {built ? '✓' : failed ? '–' : ''}
                </span>
                <span className="course-step-title">{step.title}</span>
                <span className="course-step-concept muted small">{step.concept}</span>
              </li>
            )
          })}
        </ol>
      )}

      {!plan && <div className="course-wait" aria-hidden />}

      {skipped.length > 0 && !busy && (
        <p className="muted small">
          {skipped.length === 1 ? 'One lesson' : `${skipped.length} lessons`} didn&rsquo;t
          come out right and were left out. The rest are ready.
        </p>
      )}
      {error && <p className="panel panel-error small">{error}</p>}
    </div>
  )
}
