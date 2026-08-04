import { useEffect, useMemo, useState } from 'react'

import { usePrefersReducedMotion } from '../../lib/motion'
import {
  buildTrace,
  defaultThreshold,
  sourceLines,
  thresholdRange,
  type Comparison,
} from '../../lib/listTrace'

/**
 * The filter loop, running where you can watch it.
 *
 * Everything above this on the page is still reading. This is the first place
 * the lesson does something: the same loop, drawn as boxes, stepping one line
 * at a time with the cursor, the test result, and the collector all visible at
 * once. The four things a student has to hold in their head are on the screen
 * instead.
 *
 * Two controls, and both exist to be argued with rather than admired:
 *
 *   the threshold   changing it re-traces immediately, so "which ones are
 *                   short?" becomes a thing you set rather than a thing you
 *                   are told.
 *   `<` vs `<=`     the lesson's own warning, made clickable. Reading that
 *                   they differ is easy to nod along to; watching one item
 *                   move between the kept and skipped piles is not.
 *
 * The items come from the lesson's own code block, so the boxes hold the same
 * quests the reader has just been looking at.
 *
 * Motion is load-bearing here rather than decoration -- an item *travelling*
 * into the collector is the thing being taught -- so `prefers-reduced-motion`
 * turns transitions off but never removes a state. Every colour is paired with
 * a shape or a mark for the same reason: kept and skipped must not be
 * distinguishable by hue alone.
 */

const TICK_MS = 950

export function ListLab({ items, name }: { items: string[]; name: string }) {
  const [threshold, setThreshold] = useState(() => defaultThreshold(items))
  const [op, setOp] = useState<Comparison>('<')
  const [at, setAt] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [probe, setProbe] = useState<number | null>(null)
  const reduced = usePrefersReducedMotion()

  const trace = useMemo(
    () => buildTrace(items, threshold, op),
    [items, threshold, op]
  )
  const lines = sourceLines(threshold, op)
  const range = thresholdRange(items)
  const step = trace[Math.min(at, trace.length - 1)]
  const last = at >= trace.length - 1

  useEffect(() => {
    if (!playing) return
    if (last) {
      setPlaying(false)
      return
    }
    const timer = setTimeout(() => setAt((n) => n + 1), TICK_MS)
    return () => clearTimeout(timer)
  }, [playing, at, last])

  /** Any change to the test invalidates the run in progress. */
  function retune(change: () => void) {
    setPlaying(false)
    setAt(0)
    setProbe(null)
    change()
  }

  const stateOf = (index: number) => {
    if (step.collected.includes(index)) return 'kept'
    if (index < step.decided) return 'skipped'
    if (index === step.index) return 'current'
    return 'waiting'
  }

  return (
    <section className={reduced ? 'panel lab is-still' : 'panel lab'}>
      <header className="lab-head">
        <span className="lab-badge">
          <i aria-hidden />
          Interactive
        </span>
        <h2>Watch it run</h2>
        <p className="muted small">
          The same loop, one line at a time. Change the test and it re-runs —
          the point is to disagree with it and see what happens.
        </p>
      </header>

      <div className="lab-grid">
        <div className="lab-pane">
          <div className="lab-pane-bar">
            <span className="lab-pane-title">the loop</span>
            <span className="lab-pane-tag">python</span>
          </div>
          <pre className="lab-code">
            {lines.map((line, i) => (
              <span
                key={i}
                className={i === step.line ? 'lab-line is-on' : 'lab-line'}
              >
                <span className="lab-caret" aria-hidden>
                  {i === step.line ? '▸' : ''}
                </span>
                <span className="lab-lineno" aria-hidden>
                  {i + 1}
                </span>
                {line || ' '}
              </span>
            ))}
          </pre>
        </div>

        <div className="lab-stage">
          <div className="lab-shelf">
            <p className="lab-label">
              <span className="lab-var">{name}</span>
              <span className="lab-hint">
                {probe === null ? (
                  'click a box to look inside'
                ) : (
                  <>
                    <code>
                      {name}[{probe}]
                    </code>{' '}
                    is “{items[probe]}”
                  </>
                )}
              </span>
            </p>

            <ul className="lab-row">
              {items.map((item, index) => (
                <li key={index}>
                  <button
                    type="button"
                    className={`lab-box is-${stateOf(index)}`}
                    onClick={() => setProbe(probe === index ? null : index)}
                    aria-pressed={probe === index}
                  >
                    {/* Paired with the colour so the two decided states are
                        never distinguishable by hue alone. */}
                    <span className="lab-stamp" aria-hidden>
                      {stateOf(index) === 'kept'
                        ? '✓'
                        : stateOf(index) === 'skipped'
                          ? '✕'
                          : ''}
                    </span>
                    <span className="lab-value">{item}</span>
                    <span className="lab-len" aria-hidden>
                      len {item.length}
                    </span>
                  </button>
                  <span className="lab-index" aria-hidden>
                    {index}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="lab-flow" aria-hidden>
            <span className={step.line === 3 ? 'lab-arrow is-on' : 'lab-arrow'}>
              append
            </span>
          </div>

          <div className="lab-shelf lab-shelf-out">
            <p className="lab-label">
              <span className="lab-var">short_ones</span>
              <span className="lab-hint">
                {step.collected.length} item
                {step.collected.length === 1 ? '' : 's'}
              </span>
            </p>
            <ul className="lab-row lab-out">
              {step.collected.length === 0 ? (
                <li className="lab-empty">nothing collected yet</li>
              ) : (
                step.collected.map((index) => (
                  <li key={index}>
                    <span className="lab-box is-kept is-landed">
                      <span className="lab-stamp" aria-hidden>
                        ✓
                      </span>
                      <span className="lab-value">{items[index]}</span>
                    </span>
                  </li>
                ))
              )}
            </ul>
          </div>
        </div>

        {/* aria-live so the narration is read out as it changes -- it carries
            the actual explanation, and the boxes beside it are decoration to
            anyone using a screen reader. */}
        <p className="lab-note" aria-live="polite">
          {step.test !== null && (
            <span className={step.test ? 'lab-verdict ok' : 'lab-verdict no'}>
              {step.test ? '✓ True' : '✕ False'}
            </span>
          )}
          <span className="lab-note-text">{step.note}</span>
        </p>
      </div>

      {/* A scrubber, not a readout: the run is short enough that jumping back
          to the step you half-followed is the natural thing to want. */}
      <ol className="lab-rail">
        {trace.map((_, i) => (
          <li key={i}>
            <button
              type="button"
              className={i === at ? 'is-at' : i < at ? 'is-past' : ''}
              onClick={() => {
                setPlaying(false)
                setAt(i)
              }}
              aria-label={`step ${i + 1} of ${trace.length}`}
              aria-current={i === at}
            />
          </li>
        ))}
      </ol>

      <div className="lab-controls">
        <div className="lab-transport">
          <button
            type="button"
            className="lab-btn lab-icon"
            onClick={() => {
              setPlaying(false)
              setAt((n) => Math.max(0, n - 1))
            }}
            disabled={at === 0}
            aria-label="previous step"
          >
            ◀
          </button>
          <button
            type="button"
            className="lab-btn"
            onClick={() => {
              setPlaying(false)
              setAt((n) => Math.min(trace.length - 1, n + 1))
            }}
            disabled={last}
          >
            Step ▶
          </button>
          <button
            type="button"
            className="lab-btn lab-play"
            onClick={() => (last ? (setAt(0), setPlaying(true)) : setPlaying(!playing))}
          >
            {playing ? '❚❚ Pause' : last ? '↻ Run again' : '▶ Play'}
          </button>
          <button
            type="button"
            className="lab-btn lab-ghost"
            onClick={() => {
              setPlaying(false)
              setAt(0)
            }}
            disabled={at === 0}
          >
            Reset
          </button>
          <span className="lab-step-count">
            {at + 1}
            <i>/{trace.length}</i>
          </span>
        </div>

        <div className="lab-tune">
          <span className="lab-tune-label">keep when length is</span>
          <span className="lab-seg" data-on={op}>
            {(['<', '<='] as Comparison[]).map((choice) => (
              <button
                key={choice}
                type="button"
                className={op === choice ? 'is-on' : undefined}
                onClick={() => retune(() => setOp(choice))}
                aria-pressed={op === choice}
              >
                {choice}
              </button>
            ))}
          </span>
          <label className="lab-slider">
            <input
              type="range"
              min={range.min}
              max={range.max}
              value={threshold}
              onChange={(e) => retune(() => setThreshold(Number(e.target.value)))}
              aria-label="length threshold"
            />
            <b>{threshold}</b>
          </label>
        </div>
      </div>
    </section>
  )
}
