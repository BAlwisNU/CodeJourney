import { useRef, type ReactNode } from 'react'

import { usePrefersReducedMotion } from '../lib/motion'

/**
 * A card that leans toward the pointer.
 *
 * Gives the flat panels on the landing page the same depth as the world flying
 * past behind them, so the two layers read as one scene rather than content
 * pasted over a wallpaper. The lit edge tracks the pointer too -- rotation
 * alone reads as a glitch; rotation plus a moving highlight reads as a
 * physical object catching the light.
 *
 * Everything per-frame is written straight to the element's inline custom
 * properties. No state, so moving the mouse across a grid of these does not
 * re-render the page.
 */

type TiltProps = {
  children: ReactNode
  className?: string
  /** Maximum lean, in degrees, at the corners of the card. */
  max?: number
  /** How far the card lifts toward the viewer while pointed at, in px. */
  lift?: number
  /**
   * Element to render as. The wrapper has to be a valid child of whatever it
   * sits in -- a `div` between a `ul` and its `li`s is invalid HTML, and
   * assistive tech stops treating the list as a list.
   */
  as?: 'div' | 'li' | 'article'
}

export function Tilt({ children, className = '', max = 7, lift = 12, as: Tag = 'div' }: TiltProps) {
  const ref = useRef<HTMLElement>(null)
  const reduced = usePrefersReducedMotion()

  const set = (el: HTMLElement, rx: number, ry: number, mx: number, my: number, z: number) => {
    el.style.setProperty('--rx', `${rx.toFixed(2)}deg`)
    el.style.setProperty('--ry', `${ry.toFixed(2)}deg`)
    el.style.setProperty('--mx', `${mx.toFixed(1)}%`)
    el.style.setProperty('--my', `${my.toFixed(1)}%`)
    el.style.setProperty('--lift', `${z}px`)
  }

  const onMove = (event: React.PointerEvent<HTMLElement>) => {
    const el = ref.current
    if (!el || reduced) return
    const box = el.getBoundingClientRect()
    // -0.5 .. 0.5 from the centre of the card.
    const px = (event.clientX - box.left) / box.width - 0.5
    const py = (event.clientY - box.top) / box.height - 0.5
    // Y movement tips the card back (negative rotateX), X movement turns it.
    set(el, -py * max * 2, px * max * 2, (px + 0.5) * 100, (py + 0.5) * 100, lift)
  }

  const onLeave = () => {
    const el = ref.current
    if (!el) return
    set(el, 0, 0, 50, 50, 0)
  }

  return (
    <Tag
      ref={ref as React.Ref<never>}
      className={`tilt ${className}`.trim()}
      onPointerMove={onMove}
      onPointerLeave={onLeave}
    >
      <div className="tilt-inner">{children}</div>
    </Tag>
  )
}
