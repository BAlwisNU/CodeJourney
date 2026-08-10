import { useEffect, useRef } from 'react'

import { usePrefersReducedMotion } from '../lib/motion'

/**
 * The ground you are travelling across.
 *
 * The landing page used to be deep space: a near-black field with a distant
 * globe and a corridor of editor windows flying past. Technically the nicest
 * thing on the site and completely unwelcoming — the first thing a beginner
 * saw was cold, empty and far away.
 *
 * So the camera has come down to the surface. A lit horizon sits behind
 * everything, and scrolling walks you across it: the ground drifts, the sky
 * drifts more slowly, and the sun's glow breathes. The fly-through canvas
 * (ScrollWorld) still runs above this, where its drifting panes of syntax now
 * read as things moving through the sky of a world rather than debris in orbit.
 *
 * Three layers, each moving at its own rate, because that is what makes a flat
 * picture read as distance:
 *
 *   sky     barely moves — it is far away
 *   sun     breathes on its own clock, independent of scroll
 *   ground  moves most, and lifts slightly, so you feel carried forward
 *
 * The artwork is one 118 KB WebP. It is decorative and never carries meaning,
 * so it is aria-hidden and the page reads identically without it.
 */

/** How far the ground shifts across a full page scroll, in pixels. */
const GROUND_TRAVEL = 190
/** The sky's share of that. Small — distance is the whole point. */
const SKY_TRAVEL = 46

export function WorldSurface() {
  const groundRef = useRef<HTMLDivElement | null>(null)
  const skyRef = useRef<HTMLDivElement | null>(null)
  const still = usePrefersReducedMotion()

  useEffect(() => {
    // Someone who asked for less motion gets the scene, lit and still. The
    // picture is the welcome; the drifting is only the flourish on top.
    if (still) return

    let frame: number | null = null

    function apply() {
      frame = null
      const doc = document.documentElement
      const travelled = window.scrollY
      const total = Math.max(1, doc.scrollHeight - window.innerHeight)
      const t = Math.min(1, travelled / total)

      // translate3d rather than top/background-position: it runs on the
      // compositor, so this never costs a layout on a page that is already
      // painting a canvas every frame.
      if (groundRef.current) {
        groundRef.current.style.transform =
          `translate3d(0, ${(-t * GROUND_TRAVEL).toFixed(1)}px, 0) scale(1.08)`
      }
      if (skyRef.current) {
        skyRef.current.style.transform =
          `translate3d(0, ${(t * SKY_TRAVEL).toFixed(1)}px, 0)`
      }
    }

    function onScroll() {
      if (frame === null) frame = requestAnimationFrame(apply)
    }

    apply()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      if (frame !== null) cancelAnimationFrame(frame)
    }
  }, [still])

  return (
    <div className={still ? 'ws-surface is-still' : 'ws-surface'} aria-hidden>
      {/* Colour behind the plate, so the page is never a white flash while the
          image decodes and never a hard edge above it on a tall window. */}
      <div className="ws-sky" ref={skyRef} />
      <div className="ws-sun" />
      <div
        className="ws-ground"
        ref={groundRef}
        style={{ backgroundImage: 'url(/world/surface.webp)' }}
      />
      {/* Fireflies over the near hills. Six, not sixty: the point is that the
          world is alive, and a swarm would pull the eye off the headline. */}
      <div className="ws-motes">
        {Array.from({ length: 6 }).map((_, i) => (
          <span
            key={i}
            style={{
              left: `${8 + i * 16}%`,
              animationDelay: `${i * 2.3}s`,
              animationDuration: `${13 + (i % 3) * 4}s`,
            }}
          />
        ))}
      </div>
      <div className="ws-veil" />
    </div>
  )
}
