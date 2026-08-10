import { useEffect, useRef, useState } from 'react'

/**
 * How far through the reading you are.
 *
 * The lesson is one continuous scroll, and deliberately so — it used to
 * paginate and that was removed because it put a third layer of navigation on a
 * screen that already had stage tabs and sub-tabs (see LessonBody). The problem
 * that left behind is orientation, not navigation: measured on the demo lesson
 * the reading is 4.7 screens with nothing telling you whether that is nearly
 * over or barely started.
 *
 * So this reports position without adding anywhere to click. A hairline that
 * fills as you read, and the section you are in — which is the question people
 * actually have ("how much more of this?"), answered without giving them a
 * control to operate.
 *
 * Deliberately not a percentage. A number that says 38% invites you to watch
 * the number instead of reading the words.
 */
export function ReadingProgress({
  target,
  sections,
}: {
  /** The scrolling lesson body to measure. */
  target: React.RefObject<HTMLElement | null>
  /** Headings in order, for naming where you are. */
  sections: string[]
}) {
  const [progress, setProgress] = useState(0)
  const [current, setCurrent] = useState(0)
  const frame = useRef<number | null>(null)

  useEffect(() => {
    const el = target.current
    if (!el) return

    function measure() {
      frame.current = null
      const node = target.current
      if (!node) return

      const box = node.getBoundingClientRect()
      const viewport = window.innerHeight
      // How much of the lesson has passed the top of the viewport, as a share
      // of the distance there is to travel. Clamped, because over-scroll and
      // rubber-banding both push this past its ends.
      const travelled = -box.top
      const distance = Math.max(1, box.height - viewport)
      setProgress(Math.min(1, Math.max(0, travelled / distance)))

      // The heading nearest the top of the screen without being below it —
      // which is the section you are reading, not the one coming up.
      const headings = [...node.querySelectorAll<HTMLElement>('.ls h3')]
      let index = 0
      headings.forEach((heading, i) => {
        if (heading.getBoundingClientRect().top < viewport * 0.35) index = i + 1
      })
      setCurrent(index)
    }

    function onScroll() {
      // Coalesced to one measurement per frame: this runs on every scroll event
      // and getBoundingClientRect forces layout.
      if (frame.current === null) frame.current = requestAnimationFrame(measure)
    }

    measure()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (frame.current !== null) cancelAnimationFrame(frame.current)
    }
  }, [target, sections.length])

  if (sections.length < 2) return null

  const name = current === 0 ? sections[0] : sections[current - 1]

  return (
    <div className="readbar" aria-hidden>
      <div className="readbar-track">
        <span style={{ transform: `scaleX(${progress})` }} />
      </div>
      <p className="readbar-where">
        <span className="readbar-name">{name}</span>
        <span className="readbar-count">
          {Math.min(Math.max(current, 1), sections.length)} of {sections.length}
        </span>
      </p>
    </div>
  )
}
