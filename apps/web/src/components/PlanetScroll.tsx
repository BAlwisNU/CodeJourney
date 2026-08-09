import { useEffect, useRef, useState, type ReactNode } from 'react'

import { usePrefersReducedMotion } from '../lib/motion'

/**
 * The landing page, as faces on a slowly turning surface.
 *
 * Each section sits on one face of a cylinder lying on its side. Scrolling
 * turns the cylinder rather than moving the page, so a section rises over the
 * horizon, squares up to you, and rolls away underneath as the next one comes
 * up -- the feeling of travelling over the surface of something round rather
 * than down a document.
 *
 * The geometry is one line: put face `i` at `rotateX(i * STEP) translateZ(R)`
 * and turn the whole rotor by `-progress * (N-1) * STEP`, and face `i` squares
 * up exactly when the rotor reaches its angle. R is derived rather than picked
 * -- for faces one viewport tall to sit edge to edge without overlapping, the
 * radius has to be `(height / 2) / tan(STEP / 2)`, so it is recomputed whenever
 * the window resizes.
 *
 * An arc, not a full circle. There is no wrapping round the back to the start,
 * because a landing page has a beginning and an end and pretending otherwise
 * would hide the call to action at the bottom.
 *
 * The hard constraint this shape imposes: **a face cannot scroll**. Whatever is
 * on a slide has to fit one viewport, or it is simply cut off. That is a
 * content rule, not a styling one, and it is enforced in the stylesheet by
 * slide-scoped overrides rather than by hoping.
 *
 * Falls back to an ordinary stacked page under `prefers-reduced-motion` and on
 * short viewports, where a viewport-per-section would be unusable. Every slide
 * is in the DOM in reading order in both modes, so nothing here is load-bearing
 * for content ever reaching anyone.
 */

/** Degrees between one face and the next. */
const STEP = 34

const clamp01 = (n: number) => (n < 0 ? 0 : n > 1 ? 1 : n)

export function PlanetScroll({ slides }: { slides: ReactNode[] }) {
  const reduced = usePrefersReducedMotion()
  const wrap = useRef<HTMLDivElement>(null)
  const [angle, setAngle] = useState(0)
  const [radius, setRadius] = useState(1400)
  // Short viewports get the flat page: a slide that has to fit 100vh has
  // nothing to work with at 600px, and the effect is not worth an unreadable
  // page.
  const [flat, setFlat] = useState(true)

  useEffect(() => {
    const measure = () => {
      const height = window.innerHeight
      setFlat(reduced || height < 620 || window.innerWidth < 760)
      // Faces one viewport tall, sitting edge to edge on the curve.
      setRadius(height / 2 / Math.tan((STEP / 2) * (Math.PI / 180)))
    }
    measure()
    window.addEventListener('resize', measure)
    return () => window.removeEventListener('resize', measure)
  }, [reduced])

  useEffect(() => {
    if (flat) return
    let raf = 0
    const onScroll = () => {
      if (raf) return
      raf = requestAnimationFrame(() => {
        raf = 0
        const el = wrap.current
        if (!el) return
        const travel = el.offsetHeight - window.innerHeight
        const progress = clamp01((window.scrollY - el.offsetTop) / Math.max(1, travel))
        setAngle(progress * (slides.length - 1) * STEP)
      })
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [flat, slides.length])

  if (flat) {
    return <>{slides.map((slide, i) => <div key={i} className="slide-flat">{slide}</div>)}</>
  }

  return (
    <div
      className="planet"
      ref={wrap}
      // One viewport of scroll per slide, which is what makes the turn feel
      // like it is driven by the scroll rather than merely triggered by it.
      style={{ height: `${slides.length * 100}vh` }}
    >
      <div className="planet-stage">
        <div
          className="planet-rotor"
          // Negative: a face sits at rotateX(i * STEP), so the rotor has to turn
          // the opposite way for face i to square up when the angle reaches
          // i * STEP. With the sign the other way the two disagreed -- the
          // opacity maths said a face was front while the transform had it 66
          // degrees away, so every slide rendered edge-on and invisible.
          style={{ transform: `translateZ(${-radius}px) rotateX(${-angle}deg)` }}
        >
          {slides.map((slide, i) => {
            // How far this face is from squared-up, in degrees.
            const off = i * STEP - angle
            const away = Math.abs(off)
            // Past a right angle a face is edge-on or behind; nothing to draw.
            if (away > 88) return null
            const facing = Math.cos((off * Math.PI) / 180)
            return (
              <section
                key={i}
                className="planet-face"
                style={{
                  transform: `rotateX(${i * STEP}deg) translateZ(${radius}px)`,
                  // Fades and softens as it turns away, so the one you are
                  // meant to read is unmistakably the one squared up to you.
                  opacity: Math.max(0, facing) ** 1.6,
                  filter: `blur(${Math.min(6, away / 9)}px)`,
                  // Only the face in front can be clicked. Otherwise a link on
                  // a slide edge-on to the camera is still a hit target sitting
                  // invisibly over the one being read.
                  pointerEvents: away < STEP / 2 ? 'auto' : 'none',
                }}
              >
                <div className="planet-face-inner">{slide}</div>
              </section>
            )
          })}
        </div>
      </div>
    </div>
  )
}
