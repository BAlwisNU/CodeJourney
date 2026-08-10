import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'
import type { Reflection } from '../lib/types'

/**
 * Everything you have written, in one place.
 *
 * The journal is written one lesson at a time and, until now, could only be
 * read one lesson at a time -- you had to remember which exercise you were on
 * the day you wrote something in order to find it again. Which is the opposite
 * of what a journal is for: the value is in reading it back and noticing that
 * the thing that stumped you in March is a thing you now do without thinking.
 *
 * Opens over the page rather than replacing it, because reading back is a
 * digression from whatever you were doing, and losing your place on the
 * progress page to take it would be a poor trade.
 *
 * Read-only on purpose. Editing an entry belongs on the lesson it is about,
 * where the code and the tests it describes are also on screen; a diary that
 * let you rewrite history from a distance would be a different, worse thing.
 */
export function JournalDiary({
  titles,
  slugs,
  onClose,
}: {
  /** exercise id -> lesson title, so an entry can say what it was about. */
  titles: Map<string, string>
  /** exercise id -> slug, for the link back to the lesson. */
  slugs: Map<string, string>
  onClose: () => void
}) {
  const [entries, setEntries] = useState<Reflection[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const closeRef = useRef<HTMLButtonElement | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .reflections()
      .then((r) => !cancelled && setEntries(r))
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : String(e)))
    return () => {
      cancelled = true
    }
  }, [])

  // Escape closes, and the close button takes focus on open, so a keyboard
  // user is not left tabbing through the page behind the blur to find a way
  // out of something they just opened.
  useEffect(() => {
    closeRef.current?.focus()
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    // The page behind must not scroll under the overlay.
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = previous
    }
  }, [onClose])

  return (
    <div className="diary-scrim" onClick={onClose}>
      {/* Stops a click inside the sheet from reaching the scrim and closing it
          -- people select text while reading, and a stray drag should not
          shut the thing they are reading. */}
      <section
        className="diary"
        role="dialog"
        aria-modal="true"
        aria-label="Your journal"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="diary-head">
          <div>
            <h2>Your journal</h2>
            <p className="muted small">
              Everything you&rsquo;ve written, newest first. Private to you and
              your teacher — never read by an AI.
            </p>
          </div>
          <button
            ref={closeRef}
            type="button"
            className="diary-close"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </header>

        <div className="diary-body">
          {error && <p className="panel panel-error">{error}</p>}
          {!entries && !error && <p className="muted">Loading…</p>}

          {entries?.length === 0 && (
            <div className="diary-empty">
              <p>
                <strong>Nothing written yet.</strong>
              </p>
              <p className="muted">
                At the end of any lesson there&rsquo;s a journal tab: what you
                tried, where you got stuck, how you fixed it. Three lines is
                plenty, and they add up.
              </p>
            </div>
          )}

          {entries?.map((entry) => {
            const title = entry.exercise_id
              ? titles.get(entry.exercise_id)
              : undefined
            const slug = entry.exercise_id ? slugs.get(entry.exercise_id) : undefined
            return (
              <article key={entry.id} className="diary-entry">
                <header className="diary-entry-head">
                  <span className="diary-when">{longDate(entry.updated_at)}</span>
                  {title &&
                    (slug ? (
                      <Link className="diary-lesson" to={`/exercise/${slug}/plan`}>
                        {title}
                      </Link>
                    ) : (
                      <span className="diary-lesson">{title}</span>
                    ))}
                </header>
                <dl className="diary-fields">
                  <Field label="Tried" value={entry.what_i_tried} />
                  <Field label="Stuck" value={entry.where_i_got_stuck} />
                  <Field label="Fixed" value={entry.how_i_fixed_it} />
                </dl>
              </article>
            )
          })}
        </div>
      </section>
    </div>
  )
}

/** A line of the entry, left out entirely when it was left blank. */
function Field({ label, value }: { label: string; value: string }) {
  if (!value.trim()) return null
  return (
    <>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </>
  )
}

/** "12 March 2026" — a date you can read, not one you have to decode. */
function longDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}
