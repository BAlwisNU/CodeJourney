import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import type { ExerciseProgress } from '../lib/types'

/**
 * A 3D "coverflow" of the languages. Swipe, drag, arrow-key, or click a side
 * tile to bring a language to the front; the focused language's topics are
 * rendered below by the parent.
 *
 * A language can be `locked` -- content (and, more fundamentally, an execution
 * engine) isn't built yet. Locked tiles still receive focus so a screen reader
 * and a keyboard user can read "coming soon", but they don't navigate anywhere,
 * because there is nowhere to go. Pretending otherwise would be a dead link
 * dressed up as a feature.
 *
 * The 3D is real (perspective + rotateY). Under prefers-reduced-motion the
 * global rule drops the transition so tiles snap rather than glide.
 */

export type Lang = {
  key: string
  short: string // monogram shown on the tile: "Py", "C++", "HTML", "SQL"
  name: string
  blurb: string
  locked: boolean
  exercises: ExerciseProgress[]
  solved: number
  total: number
}

export function LanguageCarousel({
  langs,
  focused,
  onFocus,
}: {
  langs: Lang[]
  focused: number
  onFocus: (index: number) => void
}) {
  const navigate = useNavigate()
  const drag = useRef<{ x: number; moved: boolean } | null>(null)
  const [dragDx, setDragDx] = useState(0)
  const suppressClick = useRef(false)

  const clamp = useCallback(
    (i: number) => Math.max(0, Math.min(langs.length - 1, i)),
    [langs.length]
  )
  const go = useCallback(
    (delta: number) => onFocus(clamp(focused + delta)),
    [focused, clamp, onFocus]
  )

  function onPointerDown(e: React.PointerEvent) {
    drag.current = { x: e.clientX, moved: false }
    ;(e.target as HTMLElement).setPointerCapture?.(e.pointerId)
  }
  function onPointerMove(e: React.PointerEvent) {
    if (!drag.current) return
    const dx = e.clientX - drag.current.x
    if (Math.abs(dx) > 6) drag.current.moved = true
    setDragDx(dx)
  }
  function onPointerUp() {
    if (!drag.current) return
    const dx = dragDx
    setDragDx(0)
    if (dx <= -60) go(1)
    else if (dx >= 60) go(-1)
    const wasDrag = drag.current.moved
    drag.current = null
    if (wasDrag) suppressClick.current = true
  }

  function activate(index: number, lang: Lang) {
    if (suppressClick.current) {
      suppressClick.current = false
      return
    }
    if (index !== focused) {
      onFocus(index)
      return
    }
    if (lang.locked) return // nowhere to go yet
    const next =
      lang.exercises.find((e) => e.status === 'in_progress') ??
      lang.exercises.find((e) => e.status === 'not_started') ??
      lang.exercises[0]
    if (!next) return
    navigate(
      next.status === 'in_progress'
        ? `/exercise/${next.slug}`
        : `/exercise/${next.slug}/plan`
    )
  }

  useEffect(() => {
    const el = document.querySelector('.carousel')
    if (!el) return
    let cooldown = false
    function onWheel(e: Event) {
      const w = e as WheelEvent
      if (Math.abs(w.deltaX) <= Math.abs(w.deltaY)) return
      w.preventDefault()
      if (cooldown) return
      cooldown = true
      setTimeout(() => (cooldown = false), 260)
      go(w.deltaX > 0 ? 1 : -1)
    }
    el.addEventListener('wheel', onWheel, { passive: false })
    return () => el.removeEventListener('wheel', onWheel)
  }, [go])

  return (
    <div className="carousel-wrap">
      <button
        className="carousel-arrow left"
        onClick={() => go(-1)}
        disabled={focused === 0}
        aria-label="Previous language"
      >
        ‹
      </button>

      <div
        className="carousel"
        role="group"
        aria-roledescription="carousel"
        aria-label="Languages"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'ArrowRight') go(1)
          if (e.key === 'ArrowLeft') go(-1)
        }}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div className="carousel-stage">
          {langs.map((lang, i) => {
            const offset = i - focused
            const dragShift = dragDx / 22
            const abs = Math.abs(offset)
            const hidden = abs > 2
            const pct = lang.total ? Math.round((lang.solved / lang.total) * 100) : 0
            const next =
              lang.exercises.find((e) => e.status === 'in_progress') ??
              lang.exercises.find((e) => e.status === 'not_started') ??
              lang.exercises[0]

            return (
              <button
                key={lang.key}
                className={`tile ${offset === 0 ? 'front' : ''} ${lang.locked ? 'locked' : ''}`}
                aria-hidden={hidden}
                tabIndex={offset === 0 ? 0 : -1}
                aria-label={
                  lang.locked
                    ? `${lang.name}, coming soon`
                    : `${lang.name}, ${lang.solved} of ${lang.total} done`
                }
                onClick={() => activate(i, lang)}
                style={{
                  transform: `
                    translateX(${offset * 60 + dragShift}%)
                    translateZ(${-abs * 140}px)
                    rotateY(${offset * -32}deg)
                    scale(${offset === 0 ? 1 : 0.9})`,
                  opacity: hidden ? 0 : offset === 0 ? 1 : 0.55,
                  zIndex: 10 - abs,
                  pointerEvents: hidden ? 'none' : 'auto',
                }}
              >
                <span className="tile-glow" aria-hidden />
                <span className="lang-badge" aria-hidden>
                  {lang.short}
                </span>
                <span className="tile-name">{lang.name}</span>

                {lang.locked ? (
                  <span className="soon-pill">Coming soon</span>
                ) : (
                  <span className="tile-ring" aria-hidden>
                    <svg viewBox="0 0 36 36">
                      <circle className="ring-bg" cx="18" cy="18" r="15.9" />
                      <circle
                        className="ring-fg"
                        cx="18"
                        cy="18"
                        r="15.9"
                        strokeDasharray={`${pct}, 100`}
                      />
                    </svg>
                    <span className="ring-label">
                      {lang.solved}/{lang.total}
                    </span>
                  </span>
                )}

                {offset === 0 && !lang.locked && next && (
                  <span className="tile-cta">
                    {next.status === 'in_progress'
                      ? 'Carry on →'
                      : next.status === 'not_started'
                        ? 'Start →'
                        : 'Revisit →'}
                  </span>
                )}
              </button>
            )
          })}
        </div>
      </div>

      <button
        className="carousel-arrow right"
        onClick={() => go(1)}
        disabled={focused === langs.length - 1}
        aria-label="Next language"
      >
        ›
      </button>

      <div className="carousel-dots" role="tablist" aria-label="Choose a language">
        {langs.map((lang, i) => (
          <button
            key={lang.key}
            role="tab"
            aria-selected={i === focused}
            aria-label={lang.name}
            className={i === focused ? 'dot on' : 'dot'}
            onClick={() => onFocus(i)}
          />
        ))}
      </div>
    </div>
  )
}
