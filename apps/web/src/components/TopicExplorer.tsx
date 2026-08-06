import { useRef, useState } from 'react'

import { CURRICULUM, CURRICULUM_BY_KEY, LEVELS } from '../lib/curriculum'
import { Tilt } from './Tilt'

/**
 * The landing page's answer to "yes, but what would I actually learn?".
 *
 * Rendered inside the expanded Python row of the language list, under that
 * row's one-line description. Pick a topic, see the path through it: four
 * branches from foundations to applied, and the modules on each. Only the live
 * language gets one; the "coming soon" rows keep their sentence alone.
 *
 * Everything comes from lib/curriculum.ts --
 * the same data the signed-in topic pages render -- so this cannot drift into
 * advertising a curriculum that doesn't exist.
 *
 * Deliberately no per-module "playable now" badge. `slug` is close enough to
 * a built-exercise marker to be tempting (68 of 69 modules have one) but not
 * close enough to put in front of a prospective user, and a badge that is
 * wrong on one row is worse than no badge at all. The counts below are derived
 * from the module list itself, so they are true by construction.
 *
 * Note for anyone adding entrance animations here: do NOT use `data-reveal`.
 * That observer only sees the elements present at mount, and this panel swaps
 * its contents on every click -- new cards would never be revealed and would
 * sit at opacity 0. The panel uses a CSS animation keyed on the topic instead,
 * which re-runs on each switch.
 */

export function TopicExplorer({ compact = false }: { compact?: boolean } = {}) {
  const [openKey, setOpenKey] = useState(CURRICULUM[0].key)
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([])
  const topic = CURRICULUM_BY_KEY[openKey]
  const index = CURRICULUM.findIndex((t) => t.key === openKey)

  // A tablist owes the user arrow keys -- Tab moves between widgets, arrows
  // move within one. Without this it is a row of buttons wearing tab roles.
  function onKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    const last = CURRICULUM.length - 1
    let next = -1
    if (event.key === 'ArrowRight') next = index === last ? 0 : index + 1
    else if (event.key === 'ArrowLeft') next = index === 0 ? last : index - 1
    else if (event.key === 'Home') next = 0
    else if (event.key === 'End') next = last
    if (next < 0) return
    event.preventDefault()
    setOpenKey(CURRICULUM[next].key)
    tabRefs.current[next]?.focus()
  }

  return (
    <div className="tex">
      {!compact && (
        <p className="tex-label">Pick a topic to see the path through it</p>
      )}

      <div className="tex-tabs" role="tablist" aria-label="Python topics" onKeyDown={onKeyDown}>
        {CURRICULUM.map((t, i) => {
          const selected = t.key === openKey
          return (
            <button
              key={t.key}
              ref={(el) => {
                tabRefs.current[i] = el
              }}
              type="button"
              role="tab"
              id={`tex-tab-${t.key}`}
              aria-selected={selected}
              aria-controls="tex-panel"
              // Roving tabindex: one stop for the whole group, not six.
              tabIndex={selected ? 0 : -1}
              className={selected ? 'tex-tab on' : 'tex-tab'}
              onClick={() => setOpenKey(t.key)}
            >
              {t.label}
              <span className="tex-tab-count">{t.modules.length}</span>
            </button>
          )
        })}
      </div>

      {/* Keyed on the topic so React remounts it, which restarts the entrance
          animation on every switch. */}
      <div
        key={topic.key}
        className="tex-panel"
        id="tex-panel"
        role="tabpanel"
        aria-labelledby={`tex-tab-${topic.key}`}
        tabIndex={-1}
      >
        {!compact && <p className="tex-intro">{topic.intro}</p>}

        <div className="tex-branches">
          {LEVELS.map((level, i) => {
            const modules = topic.modules.filter((m) => m.level === level.key)
            if (!modules.length) return null
            return (
              <Tilt key={level.key} className="tex-branch-tilt" max={5} lift={10}>
                <article className="tex-branch" style={{ '--step': i } as React.CSSProperties}>
                  <header>
                    <span className="tex-branch-num" aria-hidden>
                      {i + 1}
                    </span>
                    <div>
                      <h4>{level.label}</h4>
                      {!compact && <p className="tex-branch-hint">{level.hint}</p>}
                    </div>
                  </header>
                  <ul>
                    {modules.map((m) => (
                      <li key={m.id}>
                        <span className="tex-mod-title">{m.title}</span>
                        {!compact && <span className="tex-mod-blurb">{m.blurb}</span>}
                      </li>
                    ))}
                  </ul>
                </article>
              </Tilt>
            )
          })}
        </div>

        {/* Both numbers are counted from the curriculum rather than written
            out, so adding a topic or a module can't leave this sentence
            quietly wrong. */}
        <p className="tex-foot muted small">
          {compact
            ? `${topic.modules.length} modules, foundations through applied`
            : `${topic.modules.length} modules in ${topic.label}, foundations through applied — and ${CURRICULUM.length - 1} more topics beside it.`}
        </p>
      </div>
    </div>
  )
}
