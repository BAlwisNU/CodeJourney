import { useEffect, useRef, useState } from 'react'

/**
 * The top-right "page flick": a compact control that expands on hover (or focus,
 * or tap) into a set of view tabs, and pops the chosen view into place.
 *
 * It is hover-to-expand for the mouse, but must never be hover-ONLY -- a control
 * you can't reach without a pointer is a control some students can't reach at
 * all. So it also opens on keyboard focus and on click/tap, and every tab is a
 * real button in the tab order.
 *
 * `views` drives both the tabs and (via the parent) which subpage is shown.
 */

import { Icon, type IconName } from './Icon'

export type ViewDef = { key: string; label: string; icon: IconName }

export function PageFlick({
  views,
  active,
  onChange,
  onLogout,
}: {
  views: ViewDef[]
  active: string
  onChange: (key: string) => void
  onLogout: () => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Close when focus or a click leaves the control, so it doesn't hang open.
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDocClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [])

  const current = views.find((v) => v.key === active) ?? views[0]

  return (
    <div
      ref={ref}
      className={open ? 'flick open' : 'flick'}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        className="flick-handle"
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={() => setOpen((o) => !o)}
        onFocus={() => setOpen(true)}
      >
        <span className="flick-icon" aria-hidden>
          <Icon name={current.icon} size={18} />
        </span>
        <span className="flick-current">{current.label}</span>
        <span className="flick-chev" aria-hidden>
          <Icon name="menu" size={16} />
        </span>
      </button>

      <div className="flick-panel" role="menu" aria-label="Switch view">
        {views.map((view) => (
          <button
            key={view.key}
            role="menuitemradio"
            aria-checked={view.key === active}
            className={view.key === active ? 'flick-tab on' : 'flick-tab'}
            onClick={() => {
              onChange(view.key)
              setOpen(false)
            }}
          >
            <span className="flick-tab-icon" aria-hidden>
              <Icon name={view.icon} size={18} />
            </span>
            <span>{view.label}</span>
          </button>
        ))}

        <div className="flick-sep" />

        <button className="flick-tab quiet" role="menuitem" onClick={onLogout}>
          <span className="flick-tab-icon" aria-hidden>
            <Icon name="logout" size={18} />
          </span>
          <span>Log out</span>
        </button>
      </div>
    </div>
  )
}
