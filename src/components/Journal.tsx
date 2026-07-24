import { useEffect, useState } from 'react'

import { api } from '../lib/api'
import type { Reflection } from '../lib/types'

/**
 * The learning journal.
 *
 * Three questions, saved explicitly with a button rather than autosaved. Code
 * autosaves because losing it is pure damage; prose is different -- someone
 * half-writing a sentence about a hard week should get to decide whether it's
 * recorded at all.
 *
 * Nothing written here is ever sent to an LLM, and it is excluded from the
 * research data entirely. See apps/api/app/routers/reflections.py.
 */
export function Journal({ exerciseId }: { exerciseId: string }) {
  const [tried, setTried] = useState('')
  const [stuck, setStuck] = useState('')
  const [fixed, setFixed] = useState('')
  const [existing, setExisting] = useState<Reflection | null>(null)
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    let cancelled = false
    api
      .reflections(exerciseId)
      .then((entries) => {
        if (cancelled || entries.length === 0) return
        const entry = entries[0]
        setExisting(entry)
        setTried(entry.what_i_tried)
        setStuck(entry.where_i_got_stuck)
        setFixed(entry.how_i_fixed_it)
        // Already written something? Show it rather than making them hunt for it.
        setOpen(true)
      })
      .catch(() => {
        // A journal that fails to load must not block the exercise.
      })
    return () => {
      cancelled = true
    }
  }, [exerciseId])

  async function handleSave() {
    setBusy(true)
    setSaved(false)
    try {
      const entry = await api.saveReflection({
        exercise_id: exerciseId,
        what_i_tried: tried,
        where_i_got_stuck: stuck,
        how_i_fixed_it: fixed,
      })
      setExisting(entry)
      setSaved(true)
    } finally {
      setBusy(false)
    }
  }

  const empty = !tried.trim() && !stuck.trim() && !fixed.trim()

  return (
    <section className="panel journal">
      <button
        type="button"
        className="journal-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span>
          <strong>Your journal</strong>
          {existing && <span className="badge badge-quiet">saved</span>}
        </span>
        <span aria-hidden>{open ? '−' : '+'}</span>
      </button>

      {open && (
        <div className="journal-body">
          <p className="muted small">
            Writing down what tripped you up is how it sticks. Private to you and
            your instructor &mdash; never read by an AI, and never part of the
            research data.
          </p>

          <label className="field">
            What did you try?
            <textarea
              rows={2}
              value={tried}
              onChange={(e) => setTried(e.target.value)}
              placeholder="I started with a for loop over the goals…"
            />
          </label>

          <label className="field">
            Where did you get stuck?
            <textarea
              rows={2}
              value={stuck}
              onChange={(e) => setStuck(e.target.value)}
              placeholder="I couldn't work out why the last test kept failing…"
            />
          </label>

          <label className="field">
            How did you fix it?
            <textarea
              rows={2}
              value={fixed}
              onChange={(e) => setFixed(e.target.value)}
              placeholder="Turned out 'due today' isn't overdue, so I needed < not <=…"
            />
          </label>

          <div className="actions">
            <button
              type="button"
              className="primary"
              onClick={handleSave}
              disabled={busy || empty}
            >
              {busy ? 'Saving…' : existing ? 'Update' : 'Save'}
            </button>
            {saved && <span className="muted small">Saved.</span>}
          </div>
        </div>
      )}
    </section>
  )
}
