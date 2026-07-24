import { useState } from 'react'

import { api } from '../lib/api'
import type { Parsons as ParsonsData, ParsonsCheck } from '../lib/types'

/**
 * Parsons problem: put the shuffled lines in order.
 *
 * Move up / move down buttons rather than HTML5 drag-and-drop. Drag-and-drop is
 * the obvious choice and the wrong one here: it is unusable with a keyboard,
 * poor with a screen reader, and fiddly on a phone -- and the phone matters
 * because the Week 5 companion is meant to carry exactly this activity. Buttons
 * work everywhere, for everyone.
 *
 * Distractor lines are mixed in, so "use every line" is not a valid strategy.
 * Lines are set aside rather than deleted, since deciding a line doesn't belong
 * is part of the exercise and should be reversible.
 */
export function Parsons({ data }: { data: ParsonsData }) {
  const [used, setUsed] = useState<string[]>([])
  const [pool, setPool] = useState<string[]>(data.shuffled_lines)
  const [result, setResult] = useState<ParsonsCheck | null>(null)
  const [busy, setBusy] = useState(false)

  function take(line: string) {
    setPool(pool.filter((l) => l !== line))
    setUsed([...used, line])
    setResult(null)
  }

  function putBack(index: number) {
    const line = used[index]
    setUsed(used.filter((_, i) => i !== index))
    setPool([...pool, line])
    setResult(null)
  }

  function move(index: number, by: number) {
    const next = [...used]
    const target = index + by
    if (target < 0 || target >= next.length) return
    ;[next[index], next[target]] = [next[target], next[index]]
    setUsed(next)
    setResult(null)
  }

  async function check() {
    setBusy(true)
    try {
      setResult(await api.checkParsons(data.id, used))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel parsons">
      <h3>Warm up: put it in order</h3>
      <p className="muted small">{data.prompt}</p>

      <div className="parsons-cols">
        <div>
          <h4>Available lines</h4>
          <ul className="parsons-pool">
            {pool.map((line) => (
              <li key={line}>
                <button type="button" onClick={() => take(line)}>
                  <code>{line}</code>
                  <span className="add" aria-hidden>
                    +
                  </span>
                </button>
              </li>
            ))}
            {pool.length === 0 && (
              <li className="muted small">All used — check your order.</li>
            )}
          </ul>
        </div>

        <div>
          <h4>Your program</h4>
          <ol className="parsons-used">
            {used.map((line, index) => (
              <li
                key={`${line}-${index}`}
                className={
                  // Only ever mark the correct prefix. Marking individual wrong
                  // lines would give away the arrangement -- the same restraint
                  // the hint ladder shows.
                  result && index < result.correct_prefix ? 'ok' : undefined
                }
              >
                <code>{line}</code>
                <span className="parsons-controls">
                  <button
                    type="button"
                    onClick={() => move(index, -1)}
                    disabled={index === 0}
                    aria-label="Move up"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    onClick={() => move(index, 1)}
                    disabled={index === used.length - 1}
                    aria-label="Move down"
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    onClick={() => putBack(index)}
                    aria-label="Take out"
                  >
                    ×
                  </button>
                </span>
              </li>
            ))}
            {used.length === 0 && (
              <li className="muted small">Add lines from the left.</li>
            )}
          </ol>
        </div>
      </div>

      <div className="actions">
        <button
          type="button"
          className="primary"
          onClick={check}
          disabled={busy || used.length === 0}
        >
          {busy ? 'Checking…' : 'Check order'}
        </button>

        {result?.correct && (
          <span className="parsons-verdict ok">
            That&rsquo;s the shape of it. Now write it yourself →
          </span>
        )}
        {result && !result.correct && (
          <span className="parsons-verdict">
            {result.correct_prefix === 0
              ? 'Not yet — have another look at which line comes first.'
              : `The first ${result.correct_prefix} ${
                  result.correct_prefix === 1 ? 'line is' : 'lines are'
                } right. Keep going from there.`}
          </span>
        )}
      </div>
    </section>
  )
}
