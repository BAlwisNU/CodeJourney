import { useRef } from 'react'

import { usePrefersReducedMotion } from '../lib/motion'

/**
 * The hero's 3D deck: three panels floating at different depths, showing the
 * whole product in one glance -- code, the traceback it produced, and the
 * sentence CodeJourney turns that traceback into.
 *
 * The snippet and its translation are copied verbatim from the first sample in
 * ErrorDemo, which is itself copied from the rule table in
 * apps/api/app/services/translate.py. Three places now show this string; all
 * three have to move together, and inventing a nicer-sounding one here would
 * make the hero a lie.
 *
 * The deck leans with the pointer as a single rigid body -- the panels keep
 * their relative depths, which is what makes it read as one object in space
 * rather than three images sliding independently.
 */

const CODE = ['quests = ["Slay the dragon"]', 'print(qwests)']

const TRACEBACK = [
  'Traceback (most recent call last):',
  '  File "main.py", line 2, in <module>',
  '    print(qwests)',
  '          ^^^^^^',
  "NameError: name 'qwests' is not defined",
]

const TRANSLATION =
  'You’ve used the name “qwests”, but Python hasn’t seen it before. Either it’s spelled differently from where you created it, or it hasn’t been created yet.'

export function HeroDeck() {
  const ref = useRef<HTMLDivElement>(null)
  const reduced = usePrefersReducedMotion()

  const onMove = (event: React.PointerEvent<HTMLDivElement>) => {
    const el = ref.current
    if (!el || reduced) return
    const box = el.getBoundingClientRect()
    const px = (event.clientX - box.left) / box.width - 0.5
    const py = (event.clientY - box.top) / box.height - 0.5
    el.style.setProperty('--dy', `${(px * 26).toFixed(2)}deg`)
    el.style.setProperty('--dx', `${(-py * 16).toFixed(2)}deg`)
  }

  const onLeave = () => {
    const el = ref.current
    if (!el) return
    // Back to the resting three-quarter view, not to flat-on. The deck is
    // meant to look like an object sitting in the world at all times.
    el.style.setProperty('--dy', '0deg')
    el.style.setProperty('--dx', '0deg')
  }

  return (
    <div className="deck" onPointerMove={onMove} onPointerLeave={onLeave} aria-hidden>
      <div className="deck-stage" ref={ref}>
        <article className="deck-panel deck-code">
          <header className="deck-bar">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
            <span className="deck-file">main.py</span>
          </header>
          <pre>
            {CODE.map((line, i) => (
              <div key={line} className={i === 1 ? 'deck-line bad' : 'deck-line'}>
                <span className="deck-num">{i + 1}</span>
                <span>{line}</span>
              </div>
            ))}
          </pre>
        </article>

        <article className="deck-panel deck-trace">
          <span className="deck-tag fail">What Python said</span>
          <pre>{TRACEBACK.join('\n')}</pre>
        </article>

        <article className="deck-panel deck-plain">
          <span className="deck-tag pass">What that means</span>
          <p>{TRANSLATION}</p>
        </article>
      </div>
    </div>
  )
}
