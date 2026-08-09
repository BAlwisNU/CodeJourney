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

/** Distance between one tile and the next, in world units. */
const GAP = 1000

/** How far in front of the camera a tile sits when it is the one to read.
 *
 * Kept small on purpose. Perspective scales a tile by P / (P + FOCUS), and
 * that scale applies to everything drawn on it -- at FOCUS 340 the tile
 * rendered at 0.779 and the body text, authored at 17px, arrived on screen as
 * 13.2px. Type does not get to be a different size just because it is on a
 * card in a 3D scene. At 120 against a 1500 perspective the tile renders at
 * 0.926, so the page reads at very nearly the size it is written at. */
const FOCUS = 120

/** How far either side of the reading position a tile stays fully lit.
 *  Without a plateau the two nearest tiles cross over at the same opacity and
 *  there is a moment, mid-handover, when nothing on screen is properly
 *  readable. This holds the arriving tile up while the last one drops away. */
const PLATEAU = 400

/** How far past the plateau a tile takes to fade out entirely. */
const FADE = 900

/** How far the world turns over the whole journey, in degrees. Small: you are
 *  flying towards it, and a world that spins while you approach reads as a
 *  fairground ride rather than a planet. */
const TURN = 34

const clamp01 = (n: number) => (n < 0 ? 0 : n > 1 ? 1 : n)

export function WorldScroll({ slides }: { slides: ReactNode[] }) {
  const reduced = usePrefersReducedMotion()
  const wrap = useRef<HTMLDivElement>(null)
  // 0 at the top of the page, 1 at the bottom.
  const [travelled, setTravelled] = useState(0)
  const [flat, setFlat] = useState(true)
  const [size, setSize] = useState({ globe: 460, radius: 620 })

  useEffect(() => {
    const measure = () => {
      const w = window.innerWidth
      const h = window.innerHeight
      setFlat(reduced || w < 900 || h < 640)
      // The globe is sized from the viewport so the whole arrangement scales
      // together; the orbit clears its surface by a fixed margin so the tiles
      // always stand off it rather than cutting into it.
      // Big enough to fill the space behind the tiles: it is the thing you are
      // flying towards, so it should read as a surface below and ahead rather
      // than as a ball on the screen.
      const globe = Math.max(h * 1.6, w * 1.0)
      setSize({ globe, radius: globe / 2 })
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
        setTravelled(clamp01((window.scrollY - el.offsetTop) / Math.max(1, travel)))
      })
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      window.removeEventListener('scroll', onScroll)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [flat, slides.length])

  // How far the camera has flown into the scene.
  const camZ = travelled * (slides.length - 1) * GAP

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
        {/* The world ahead. It sits deep in the scene and drifts as you travel,
            so the tiles arrive out of it rather than in front of a backdrop. */}
        <div
          className="gs-globe"
          style={{
            width: size.globe,
            height: size.globe,
            transform: `translate(-50%, -50%) translateZ(${-1500 + travelled * 820}px) rotateZ(${travelled * TURN}deg)`,
          }}
          aria-hidden
        />

        <div className="gs-space">
          {slides.map((slide, i) => {
            // Where this tile is relative to the camera. Negative is in front;
            // it starts far away and comes towards you as you scroll.
            const z = camZ - i * GAP - FOCUS

            // Behind the camera, or so far off it is a speck: nothing to draw.
            if (z > 40 || z < -GAP * 2.4) return null

            // How close it is to the reading position: 1 across the plateau,
            // falling to 0 over FADE either side.
            const off = Math.abs(z + FOCUS)
            const near = clamp01(1 - Math.max(0, off - PLATEAU) / FADE)

            return (
              <div
                key={i}
                className="gs-tile"
                style={{
                  // Dead centre. Offsetting them left and right made the
                  // incoming ones visible early, but at the cost of the one
                  // you are actually reading never being where you are
                  // looking. The next tile is directly behind this one and
                  // arrives as this one fades.
                  transform: `translateZ(${z}px)`,
                  // Two fades multiplied: distance from the reading position,
                  // and a short one over the last stretch before it passes the
                  // camera. Without the second a tile snapped from fully lit to
                  // gone the instant it crossed z = 0. The second is short
                  // because the reading position is now only 120 out, so a long
                  // one would start dimming the tile while you were reading it.
                  opacity: (near ** 1.4) * clamp01(-z / 130),
                  filter: `blur(${(1 - near) * 5}px)`,
                  // Only the one at the reading position takes clicks.
                  pointerEvents: near > 0.86 ? 'auto' : 'none',
                  zIndex: Math.round(near * 100),
                }}
              >
                <div className="gs-face">{slide}</div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
