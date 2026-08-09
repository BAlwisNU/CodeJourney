import { useEffect, useRef, useState, type ReactNode } from 'react'

import { usePrefersReducedMotion } from '../lib/motion'

/**
 * A world you orbit, with the page mounted on it.
 *
 * There is a globe in the middle of the screen and each section is a tile
 * standing off its surface, spaced evenly around the equator. Scrolling turns
 * the world, so a tile swings round from behind, squares up to you out in
 * front of the globe, and carries on round the other side. You are outside
 * looking in, not inside looking out.
 *
 * Two things make a tile read as attached to the world rather than floating in
 * front of it: it is placed at `translateZ(R)` where R is bigger than the
 * globe's radius, so it genuinely stands proud of the surface; and a short stem
 * runs from the tile back down to the surface, which is the part that sells it.
 *
 * Tiles are sized in viewport units and do not scroll -- whatever is on one has
 * to fit it. Slide-scoped rules in the stylesheet enforce that.
 *
 * Falls back to an ordinary stacked page under `prefers-reduced-motion` and on
 * anything too small to hold a globe and a readable tile at once. Every section
 * is in the DOM in reading order either way.
 */

/** How far we look down on the ring, in degrees.
 *
 * This is the composition dial. A tile's height above the world's centre is
 * `R * sin(TILT)`, so a shallow tilt leaves the tiles sitting low and running
 * off the bottom of the frame; too steep and they float above a horizon you
 * can no longer see. 40 puts the tile in the upper middle with the curve of
 * the world filling the space beneath it. */
const TILT = 40

const clamp01 = (n: number) => (n < 0 ? 0 : n > 1 ? 1 : n)

export function WorldScroll({ slides }: { slides: ReactNode[] }) {
  const reduced = usePrefersReducedMotion()
  const wrap = useRef<HTMLDivElement>(null)
  const [angle, setAngle] = useState(0)
  const [flat, setFlat] = useState(true)
  const [size, setSize] = useState({ globe: 460, radius: 620 })

  const step = 360 / slides.length

  useEffect(() => {
    const measure = () => {
      const w = window.innerWidth
      const h = window.innerHeight
      setFlat(reduced || w < 900 || h < 640)
      // The globe is sized from the viewport so the whole arrangement scales
      // together; the orbit clears its surface by a fixed margin so the tiles
      // always stand off it rather than cutting into it.
      // The world is deliberately bigger than the frame: we sit above it and
      // see its upper curve, so it reads as a world rather than as a ball. The
      // ring of tiles clears the surface by a small margin, so they stand ON
      // it rather than floating at a distance from it.
      const globe = Math.max(h * 1.5, w * 0.95)
      setSize({ globe, radius: globe / 2 + 70 })
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
        setAngle(progress * (slides.length - 1) * step)
      })
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [flat, slides.length, step])

  if (flat) {
    return <>{slides.map((s, i) => <div key={i} className="slide-flat">{s}</div>)}</>
  }

  return (
    <div
      className="gscroll"
      ref={wrap}
      style={{ height: `${slides.length * 100}vh` }}
    >
      <div className="gs-stage">
        {/* The world itself. Behind the orbit, so a tile at the front passes
            in front of it and one at the back goes behind. */}
        <div
          className="gs-globe"
          style={{ width: size.globe, height: size.globe }}
          aria-hidden
        />

        {/* The ring is tilted so we look down on the world's shoulder; each
            tile then counter-rotates by the same amount so it stands upright
            off the surface instead of lying flat on it. */}
        <div
          className="gs-orbit"
          style={{ transform: `rotateX(${TILT}deg) rotateY(${-angle}deg)` }}
        >
          {slides.map((slide, i) => {
            // Shortest angular distance from squared-up, so the tile that has
            // come all the way round is treated the same as one that has not
            // left yet.
            const raw = (i * step - angle) % 360
            const off = raw > 180 ? raw - 360 : raw < -180 ? raw + 360 : raw
            const away = Math.abs(off)
            if (away > 100) return null
            const facing = Math.cos((off * Math.PI) / 180)
            return (
              <div
                key={i}
                className="gs-tile"
                style={{
                  transform: `rotateY(${i * step}deg) translateZ(${size.radius}px) rotateX(${-TILT}deg)`,
                  opacity: Math.max(0, facing) ** 1.5,
                  filter: `blur(${Math.min(5, away / 14)}px)`,
                  // Only the tile you are looking at takes clicks; the others
                  // are edge-on and would otherwise sit invisibly over it.
                  pointerEvents: away < step / 2 ? 'auto' : 'none',
                  zIndex: Math.round(facing * 100),
                }}
              >
                {/* Runs from the back of the tile down to the surface. This is
                    the part that makes it read as mounted rather than hovering. */}
                <span className="gs-stem" aria-hidden />
                <div className="gs-face">{slide}</div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
