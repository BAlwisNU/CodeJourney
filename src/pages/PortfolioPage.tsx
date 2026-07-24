import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../lib/api'
import type { Portfolio } from '../lib/types'

const CONCEPT_LABELS: Record<string, string> = {
  lists: 'Lists',
  dicts: 'Dictionaries',
  loops: 'Loops',
  strings: 'Strings',
  functions: 'Functions',
  file_io: 'Files',
}

/**
 * The digital portfolio: what they made and how they got there.
 *
 * Attempt counts are shown next to the finished code on purpose. A portfolio of
 * only final answers is a transcript; showing that something took eleven goes is
 * the evidence of progress the proposal is actually after, and it quietly makes
 * the point that struggling is normal.
 */
export function PortfolioPage() {
  const [data, setData] = useState<Portfolio | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .portfolio()
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  if (error) return <p className="panel panel-error">{error}</p>
  if (!data) return <p className="muted">Loading…</p>

  return (
    <div className="dash">
      <header className="dash-head">
        <div>
          <h1>{data.display_name}&rsquo;s portfolio</h1>
          <p className="muted">
            {data.solved === 0
              ? 'Once you solve something it appears here, with the code you wrote and what you learned.'
              : `${data.solved} solved, across ${data.total_attempts} attempts. Every one of those attempts counted.`}
          </p>
        </div>
        <Link className="link" to="/exercises">
          Back to your work
        </Link>
      </header>

      {data.concepts_touched.length > 0 && (
        <section className="panel">
          <h2>What you&rsquo;ve covered</h2>
          <div className="chips">
            {data.concepts_touched.map((concept) => (
              <span key={concept} className="badge">
                {CONCEPT_LABELS[concept] ?? concept}
              </span>
            ))}
          </div>
        </section>
      )}

      {data.entries.length === 0 && (
        <p className="panel muted">
          Nothing here yet. <Link to="/exercises">Pick a project</Link> and this
          fills itself in.
        </p>
      )}

      {data.entries.map((entry) => (
        <article key={entry.exercise_id} className="panel pf-entry">
          <header className="pf-head">
            <div>
              <h2>{entry.title}</h2>
              <p className="muted small">
                {CONCEPT_LABELS[entry.concept] ?? entry.concept}
                {' · '}
                {entry.solved_at
                  ? `solved in ${entry.attempts} ${entry.attempts === 1 ? 'attempt' : 'attempts'}`
                  : `${entry.attempts} ${entry.attempts === 1 ? 'attempt' : 'attempts'} so far`}
              </p>
            </div>
            {entry.solved_at ? (
              <span className="badge badge-done">Solved</span>
            ) : (
              <Link className="link" to={`/exercise/${entry.slug}`}>
                Carry on
              </Link>
            )}
          </header>

          {entry.code && (
            <details className="pf-code">
              <summary>The code you wrote</summary>
              <pre>{entry.code}</pre>
            </details>
          )}

          {entry.reflection && (
            <div className="pf-reflection">
              <h3>What you wrote about it</h3>
              {entry.reflection.what_i_tried && (
                <p>
                  <strong>Tried:</strong> {entry.reflection.what_i_tried}
                </p>
              )}
              {entry.reflection.where_i_got_stuck && (
                <p>
                  <strong>Stuck on:</strong> {entry.reflection.where_i_got_stuck}
                </p>
              )}
              {entry.reflection.how_i_fixed_it && (
                <p>
                  <strong>Fixed by:</strong> {entry.reflection.how_i_fixed_it}
                </p>
              )}
            </div>
          )}
        </article>
      ))}
    </div>
  )
}
