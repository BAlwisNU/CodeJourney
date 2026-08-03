/**
 * A small, consistent line-icon set, replacing the emoji pictographs that read
 * as childish against a dark, professional UI.
 *
 * All icons share one grammar: a 24x24 box, no fill, `currentColor` stroke,
 * round caps and joins. That consistency is the whole point -- a page of icons
 * that share a stroke weight and corner radius looks designed; a page of emoji
 * looks assembled from whatever shipped with the OS. Colour and size come from
 * CSS (the icon inherits `color`), so the same icon works in a nav link, a
 * 56px tile, or a muted caption without edits here.
 */

import type { SVGProps } from 'react'

export type IconName =
  | 'games'
  | 'sports'
  | 'space'
  | 'music'
  | 'stories'
  | 'generic'
  | 'home'
  | 'projects'
  | 'progress'
  | 'bolt'
  | 'reorder'
  | 'watch'
  | 'journal'
  | 'logout'
  | 'menu'

const PATHS: Record<IconName, React.ReactNode> = {
  // worlds -----------------------------------------------------------------
  // Games & quests -> a target: objectives to hit.
  games: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <circle cx="12" cy="12" r="4.5" />
      <circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" />
    </>
  ),
  // Sports & leagues -> a medal.
  sports: (
    <>
      <circle cx="12" cy="14.5" r="5.5" />
      <path d="M9 9.2 6.5 3M15 9.2 17.5 3" />
      <path d="M12 12.3l.9 1.8 2 .3-1.45 1.4.34 2-1.79-.94-1.79.94.34-2L9.1 14.4l2-.3z" />
    </>
  ),
  // Space missions -> a planet with an orbit ring.
  space: (
    <>
      <circle cx="12" cy="12" r="5" />
      <ellipse cx="12" cy="12" rx="11" ry="4" transform="rotate(-22 12 12)" />
    </>
  ),
  // Music & playlists -> beamed notes.
  music: (
    <>
      <circle cx="7.5" cy="17" r="2" />
      <circle cx="17" cy="15" r="2" />
      <path d="M9.5 17V7l9.5-2v10" />
      <path d="M9.5 8.5 19 6.5" />
    </>
  ),
  // Stories & words -> an open book.
  stories: (
    <>
      <path d="M12 6.5C10 5 6.5 5 4.5 6v12c2-1 5.5-1 7.5.5" />
      <path d="M12 6.5C14 5 17.5 5 19.5 6v12c-2-1-5.5-1-7.5.5" />
    </>
  ),
  // Plain practice -> a plain list.
  generic: (
    <>
      <path d="M8 7h11M8 12h11M8 17h11" />
      <path d="M4.5 7h.01M4.5 12h.01M4.5 17h.01" />
    </>
  ),

  // navigation -------------------------------------------------------------
  home: (
    <>
      <path d="M3.5 11 12 4l8.5 7" />
      <path d="M5.5 9.5V20h13V9.5" />
      <path d="M10 20v-5h4v5" />
    </>
  ),
  projects: (
    <path d="M3.5 7.5a1 1 0 0 1 1-1h4.2l2 2h8.8a1 1 0 0 1 1 1V18a1 1 0 0 1-1 1h-15a1 1 0 0 1-1-1z" />
  ),
  progress: (
    <>
      <path d="M4 20h16" />
      <path d="M7 20v-6M12 20V7M17 20v-9" />
    </>
  ),

  // landing features -------------------------------------------------------
  bolt: <path d="M13 3 5 13h5l-1 8 8-11h-5z" />,
  reorder: (
    <>
      <path d="M4 8h11M4 16h11" />
      <path d="M18.5 6v12M18.5 6l-2.2 2.4M18.5 6l2.2 2.4M18.5 18l-2.2-2.4M18.5 18l2.2-2.4" />
    </>
  ),
  watch: (
    <>
      <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  journal: (
    <>
      <path d="M6 3.5h9.5a2 2 0 0 1 2 2V20a1 1 0 0 1-1 1H6a1.5 1.5 0 0 1 0-3h11" />
      <path d="M6 3.5A1.5 1.5 0 0 0 4.5 5v13" />
      <path d="M9 8h5" />
    </>
  ),

  // controls ---------------------------------------------------------------
  logout: (
    <>
      <path d="M15 5.5H6.5A1.5 1.5 0 0 0 5 7v10a1.5 1.5 0 0 0 1.5 1.5H15" />
      <path d="M14 12h7M18 8.5l3.5 3.5L18 15.5" />
    </>
  ),
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
}

export function Icon({
  name,
  size = 24,
  ...rest
}: { name: IconName; size?: number } & SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      focusable="false"
      {...rest}
    >
      {PATHS[name]}
    </svg>
  )
}
