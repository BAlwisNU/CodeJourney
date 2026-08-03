import { useEffect, useState } from 'react'

/**
 * Motion primitives shared by the landing page's 3D layer.
 *
 * Two rules the whole file exists to enforce:
 *
 *  1. `prefers-reduced-motion` is honoured in JavaScript, not just CSS. The
 *     fly-through is a canvas animation loop -- a CSS `animation: none` cannot
 *     switch it off, so the loop has to ask.
 *  2. Nothing here re-renders React on scroll. Per-frame work writes to the DOM
 *     directly (transforms, custom properties); React only ever sees the
 *     once-per-page-load facts.
 */

const REDUCED = '(prefers-reduced-motion: reduce)'

export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(REDUCED).matches,
  )

  useEffect(() => {
    const mq = window.matchMedia(REDUCED)
    const sync = () => setReduced(mq.matches)
    sync()
    mq.addEventListener('change', sync)
    return () => mq.removeEventListener('change', sync)
  }, [])

  return reduced
}

/**
 * Reveals anything tagged `data-reveal` as it enters the viewport. One observer
 * for the whole page rather than a ref per element: the landing page has a few
 * dozen of these and they are all the same effect.
 *
 * The revealed state is an inline custom property, `--reveal: 1`, and NOT a
 * class. It has to be somewhere React does not manage. An element whose
 * `className` is driven by React state -- the language rows, which toggle
 * between `world` and `world on` -- gets that attribute rewritten wholesale on
 * every re-render, which silently deleted a `.revealed` class added from here
 * and left the row stuck at `opacity: 0` forever, because the observer had
 * already stopped watching it. Inline style is untouched by React on these
 * elements, so it survives.
 *
 * Elements start hidden in CSS, so if IntersectionObserver is missing they must
 * be revealed unconditionally -- a page of invisible text is a worse failure
 * than a page with no entrance animation.
 */
export function useRevealOnScroll(enabled = true): void {
  useEffect(() => {
    const nodes = Array.from(document.querySelectorAll<HTMLElement>('[data-reveal]'))
    const reveal = (el: HTMLElement) => el.style.setProperty('--reveal', '1')
    const showAll = () => nodes.forEach(reveal)

    if (!enabled || !('IntersectionObserver' in window)) {
      showAll()
      return
    }

    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          // Stagger by position within the parent so a grid of cards arrives as
          // a wave rather than a single slab.
          const el = entry.target as HTMLElement
          const siblings = el.parentElement?.children
          const index = siblings ? Array.prototype.indexOf.call(siblings, el) : 0
          el.style.transitionDelay = `${Math.min(index, 6) * 70}ms`
          reveal(el)
          io.unobserve(el)
        }
      },
      // Fire a little before the element is fully on screen, so the motion has
      // finished by the time it is in comfortable reading position.
      { rootMargin: '0px 0px -10% 0px', threshold: 0.06 },
    )

    nodes.forEach((n) => io.observe(n))
    return () => io.disconnect()
  }, [enabled])
}
