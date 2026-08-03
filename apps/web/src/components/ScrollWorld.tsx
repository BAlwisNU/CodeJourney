import { useEffect, useRef } from 'react'

import { usePrefersReducedMotion } from '../lib/motion'

/**
 * The fly-through.
 *
 * A single fixed canvas behind the landing page, holding a small 3D world the
 * camera flies through as you scroll: a tunnel of code-shaped rings, a starfield
 * that stretches into streaks when you scroll fast, and drifting fragments of
 * Python that pass either side of you.
 *
 * The technique is the one behind scroll-scrubbed product pages -- the camera
 * genuinely moves through a space, and scroll is nothing more than the clock
 * that drives it. Everything here is real perspective projection (`scale =
 * focal / depth`) rather than layered parallax images, which is why near shards
 * slide past the edges of the screen instead of merely getting bigger.
 *
 * Deliberately dependency-free. A WebGL library would render this more cheaply,
 * but it would be the single largest thing in the bundle on a page whose whole
 * promise is "nothing to install, opens instantly" -- so: 2D canvas, a few
 * hundred points, and one projection function.
 *
 * Cost control, because this runs on student laptops:
 *  - one rAF loop, cancelled whenever the tab is hidden or the world scrolls
 *    off screen;
 *  - point counts scale with viewport area and drop on coarse-pointer devices;
 *  - React never re-renders -- the loop owns the canvas and nothing else.
 */

// --- world constants -------------------------------------------------------
// World units are arbitrary but chosen so that z ~= 800 renders at roughly 1:1
// with CSS pixels, which makes the shard font sizes below readable numbers.

/** Camera focal length. Larger = flatter, more telephoto; smaller = fisheye. */
const FOCAL = 820
/** Depth of the world. Anything that passes the camera wraps back to here. */
const DEPTH = 2800
/** Nearest renderable depth. Inside this, perspective scale explodes. */
const NEAR = 70
/** How far the camera travels over one full page scroll. */
const FLIGHT = 6200
/** Forward drift with no scrolling at all, so the page is never frozen. */
const IDLE_SPEED = 26

// Ring size is a legibility decision, not a taste one: a ring only reads as a
// ring while it fits on screen. At this half-width one stays whole until it is
// about 540 units out, so most of the corridor is recognisable shapes rather
// than the stray diagonals you get from rings that are always overscanned.
const RING_GAP = 175
const RING_HALF_W = 470
const RING_HALF_H = 290

/** Tints, as bare `r,g,b` so alpha can be varied per point. Matches :root. */
const TINTS = [
  '124, 156, 255', // --accent
  '167, 139, 250', // --accent-2
  '34, 211, 238', // --accent-3
  '52, 211, 153', // --pass
]

/**
 * The debris is Python, not lorem noise. Someone who squints at the background
 * should see the language they are about to learn.
 */
const GLYPHS = [
  'def', 'for', 'if', 'while', 'return', 'print', 'True', 'False', 'None',
  'range', 'len', 'in', 'not', 'elif', '{ }', '( )', '[ ]', ':', '==', '+=',
  '#', '->', 'self', 'import', '0', '1', '"..."',
]

type Star = { x: number; y: number; z: number; size: number; tint: string }
type Shard = { x: number; y: number; z: number; text: string; tint: string; spin: number; rate: number }
type Ring = { z: number; phase: number; tint: string }

const rand = (min: number, max: number) => min + Math.random() * (max - min)
const pick = <T,>(list: T[]) => list[(Math.random() * list.length) | 0]
const clamp01 = (n: number) => (n < 0 ? 0 : n > 1 ? 1 : n)

export function ScrollWorld() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const reduced = usePrefersReducedMotion()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d', { alpha: true })
    if (!ctx) return

    // A coarse pointer means a phone or tablet: smaller GPU, no pointer
    // parallax to drive anyway, and a battery that has to last the lecture.
    const lite = window.matchMedia('(pointer: coarse)').matches

    // --- populate the world ------------------------------------------------
    // Spread is in world units, wide enough that shards pass outside the frame
    // rather than all converging on the vanishing point.
    const area = window.innerWidth * window.innerHeight
    const density = clamp01(area / (1440 * 900))
    const starCount = Math.round((lite ? 130 : 300) * (0.55 + 0.45 * density))
    const shardCount = Math.round((lite ? 18 : 42) * (0.55 + 0.45 * density))

    const stars: Star[] = Array.from({ length: starCount }, () => ({
      x: rand(-1900, 1900),
      y: rand(-1200, 1200),
      z: rand(NEAR, DEPTH),
      size: rand(0.7, 2.1),
      // Mostly white with the occasional coloured one -- an evenly tinted
      // starfield reads as confetti rather than depth.
      tint: Math.random() < 0.24 ? pick(TINTS) : '226, 233, 250',
    }))

    const shards: Shard[] = Array.from({ length: shardCount }, () => ({
      x: rand(-1500, 1500),
      y: rand(-950, 950),
      z: rand(NEAR, DEPTH),
      text: pick(GLYPHS),
      tint: pick(TINTS),
      // `spin` is the current angle, `rate` how fast it turns. Slow: a
      // background that tumbles is a background you keep looking at.
      spin: rand(-0.35, 0.35),
      rate: rand(-0.12, 0.12),
    }))

    const rings: Ring[] = Array.from({ length: Math.ceil(DEPTH / RING_GAP) }, (_, i) => ({
      z: NEAR + i * RING_GAP,
      phase: rand(0, Math.PI * 2),
      tint: TINTS[i % TINTS.length],
    }))

    // --- canvas sizing -----------------------------------------------------
    let width = 0
    let height = 0
    let dpr = 1

    const resize = () => {
      // Cap DPR at 2: a 3x phone screen triples the fill cost for a starfield
      // nobody can resolve at that density anyway.
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      width = window.innerWidth
      height = window.innerHeight
      canvas.width = Math.round(width * dpr)
      canvas.height = Math.round(height * dpr)
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()

    // --- camera ------------------------------------------------------------
    let fly = 0 // smoothed scroll contribution
    let cruise = 0 // constant forward drift
    let prevZ = 0
    let warp = 0 // recent forward speed, drives the star streaks
    let camX = 0
    let camY = 0
    let aimX = 0
    let aimY = 0
    let last = performance.now()
    let raf = 0

    const onPointer = (event: PointerEvent) => {
      // Pointer steers the camera sideways, within a small envelope. Enough to
      // feel like you are leaning into the world; not enough to make the text
      // in front of it appear to slide around.
      aimX = (event.clientX / width - 0.5) * 320
      aimY = (event.clientY / height - 0.5) * 200
    }

    const projectedScroll = () => {
      const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight)
      return clamp01(window.scrollY / max)
    }

    const roundRect = (x: number, y: number, w: number, h: number, r: number) => {
      const radius = Math.max(0, Math.min(r, w / 2, h / 2))
      ctx.beginPath()
      ctx.moveTo(x + radius, y)
      ctx.arcTo(x + w, y, x + w, y + h, radius)
      ctx.arcTo(x + w, y + h, x, y + h, radius)
      ctx.arcTo(x, y + h, x, y, radius)
      ctx.arcTo(x, y, x + w, y, radius)
      ctx.closePath()
    }

    const frame = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000)
      last = now

      // Exponential smoothing rather than a fixed lerp factor, so the feel is
      // identical at 60Hz and 120Hz.
      const ease = 1 - Math.exp(-dt * 5)

      fly += (projectedScroll() * FLIGHT - fly) * ease
      cruise += dt * IDLE_SPEED
      const camZ = fly + cruise

      // Signed, so scrolling back up streaks the stars the other way rather
      // than dropping the effect entirely.
      const speed = (camZ - prevZ) / Math.max(dt, 0.001)
      prevZ = camZ
      warp += (Math.max(-4200, Math.min(speed, 4200)) - warp) * (1 - Math.exp(-dt * 9))

      camX += (aimX - camX) * ease
      camY += (aimY - camY) * ease

      const cx = width / 2
      const cy = height / 2

      ctx.clearRect(0, 0, width, height)

      // The world is loudest behind the hero and steps back as you get into
      // reading material -- text has to win once there is text to read.
      const depthIn = projectedScroll()
      ctx.globalAlpha = 0.55 + 0.45 * (1 - clamp01(depthIn * 1.5))

      // Vanishing-point glow. Sells the tunnel as having somewhere to go.
      const glow = ctx.createRadialGradient(cx - camX * 0.2, cy - camY * 0.2, 0, cx, cy, Math.max(width, height) * 0.42)
      glow.addColorStop(0, 'rgba(124, 156, 255, 0.22)')
      glow.addColorStop(0.5, 'rgba(167, 139, 250, 0.07)')
      glow.addColorStop(1, 'rgba(11, 13, 19, 0)')
      ctx.fillStyle = glow
      ctx.fillRect(0, 0, width, height)

      // --- rings -----------------------------------------------------------
      // Drawn first and furthest back: the corridor everything else sits in.
      for (const ring of rings) {
        let rz = ring.z - camZ
        // Wrap by whole world-depths so a ring that passes the camera reappears
        // at the far end. `while`, not `if`: one fast flick of a trackpad can
        // move the camera further than DEPTH in a single frame.
        while (rz < NEAR) { ring.z += DEPTH; rz = ring.z - camZ }
        while (rz > DEPTH + NEAR) { ring.z -= DEPTH; rz = ring.z - camZ }

        const s = FOCAL / rz
        // Fade in from the far plane, and back out as it swallows the screen.
        const alpha = clamp01(1 - rz / DEPTH) * clamp01((rz - NEAR) / 300) * 0.78
        if (alpha <= 0.004) continue

        ctx.save()
        ctx.translate(cx - camX * s * 0.5, cy - camY * s * 0.5)
        ctx.rotate(ring.phase + camZ * 0.00013)
        ctx.strokeStyle = `rgba(${ring.tint}, ${alpha})`
        ctx.lineWidth = Math.max(0.6, 2 * s)
        roundRect(-RING_HALF_W * s, -RING_HALF_H * s, RING_HALF_W * 2 * s, RING_HALF_H * 2 * s, 90 * s)
        ctx.stroke()
        ctx.restore()
      }

      // --- stars -----------------------------------------------------------
      // Streak length is tied to how fast the camera is actually moving, so
      // flicking the page produces a genuine warp and idling produces points.
      const streak = Math.max(-1, Math.min(1, warp / 2600)) * 260
      for (const star of stars) {
        let rz = star.z - camZ
        while (rz < NEAR) { star.z += DEPTH; rz = star.z - camZ }
        while (rz > DEPTH + NEAR) { star.z -= DEPTH; rz = star.z - camZ }

        const s = FOCAL / rz
        const x = cx + (star.x - camX) * s
        const y = cy + (star.y - camY) * s
        if (x < -80 || x > width + 80 || y < -80 || y > height + 80) continue

        const alpha = clamp01(1 - rz / DEPTH) * clamp01((rz - NEAR) / 260)
        if (alpha <= 0.01) continue

        if (Math.abs(streak) > 8) {
          // Clamp the tail's depth: scrolling upward puts it in front of the
          // camera, where the projection scale runs away.
          const sBack = FOCAL / Math.max(NEAR * 0.8, rz + streak)
          ctx.strokeStyle = `rgba(${star.tint}, ${alpha * 0.75})`
          ctx.lineWidth = Math.max(0.5, star.size * s * 0.9)
          ctx.beginPath()
          ctx.moveTo(cx + (star.x - camX) * sBack, cy + (star.y - camY) * sBack)
          ctx.lineTo(x, y)
          ctx.stroke()
        } else {
          ctx.fillStyle = `rgba(${star.tint}, ${alpha})`
          ctx.beginPath()
          ctx.arc(x, y, Math.max(0.4, star.size * s), 0, Math.PI * 2)
          ctx.fill()
        }
      }

      // --- code shards -------------------------------------------------------
      // Sorted far-to-near so nearer, brighter fragments overlap the ones
      // behind them the way solid objects would.
      const visible: Array<{ x: number; y: number; s: number; a: number; shard: Shard; rz: number }> = []
      for (const shard of shards) {
        let rz = shard.z - camZ
        while (rz < NEAR) { shard.z += DEPTH; rz = shard.z - camZ }
        while (rz > DEPTH + NEAR) { shard.z -= DEPTH; rz = shard.z - camZ }

        shard.spin += shard.rate * dt
        const s = FOCAL / rz
        const x = cx + (shard.x - camX) * s
        const y = cy + (shard.y - camY) * s
        if (x < -260 || x > width + 260 || y < -260 || y > height + 260) continue

        const a = clamp01(1 - rz / DEPTH) * clamp01((rz - NEAR) / 400)
        if (a <= 0.015) continue
        visible.push({ x, y, s, a, shard, rz })
      }
      visible.sort((a, b) => b.rz - a.rz)

      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      for (const item of visible) {
        const size = Math.max(6, 34 * item.s)
        if (size < 5) continue
        ctx.save()
        ctx.translate(item.x, item.y)
        ctx.rotate(item.shard.spin)
        ctx.font = `600 ${size}px ui-monospace, "SF Mono", Menlo, monospace`
        // Near shards get a bloom; distant ones do not, because shadowBlur is
        // the single most expensive thing on this canvas.
        if (!lite && item.s > 0.75) {
          ctx.shadowColor = `rgba(${item.shard.tint}, ${item.a * 0.7})`
          ctx.shadowBlur = 18 * item.s
        }
        ctx.fillStyle = `rgba(${item.shard.tint}, ${item.a})`
        ctx.fillText(item.shard.text, 0, 0)
        ctx.restore()
      }

      ctx.globalAlpha = 1
      raf = requestAnimationFrame(frame)
    }

    // --- lifecycle ---------------------------------------------------------
    const start = () => {
      if (raf) return
      last = performance.now()
      raf = requestAnimationFrame(frame)
    }
    const stop = () => {
      if (!raf) return
      cancelAnimationFrame(raf)
      raf = 0
    }

    const onVisibility = () => (document.hidden ? stop() : start())

    window.addEventListener('resize', resize)
    document.addEventListener('visibilitychange', onVisibility)
    if (!lite) window.addEventListener('pointermove', onPointer, { passive: true })
    start()

    return () => {
      stop()
      window.removeEventListener('resize', resize)
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('pointermove', onPointer)
    }
  }, [reduced])

  // Under reduced motion the world is dropped entirely rather than rendered
  // still: a frozen starfield is just visual noise behind the text.
  if (reduced) return null

  return (
    <div className="sw" aria-hidden>
      <canvas ref={canvasRef} className="sw-canvas" />
      <div className="sw-veil" />
    </div>
  )
}
