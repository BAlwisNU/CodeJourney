import { useCallback, useEffect, useRef, useState } from 'react'

export type SaveState = 'idle' | 'saving' | 'saved' | 'error'

const DEBOUNCE_MS = 1200

/**
 * Debounced autosave for the code editor.
 *
 * Saves ~1.2s after typing stops. Long enough not to POST on every keystroke,
 * short enough that a closed laptop rarely costs more than a sentence.
 *
 * Two things this handles that a naive debounce doesn't:
 *
 *  - A save in flight when the component unmounts (navigating away mid-type)
 *    would otherwise be dropped, losing the last edit. `flush` fires the pending
 *    save immediately, and the exercise page calls it on unmount and on tab hide.
 *
 *  - `pagehide` rather than `beforeunload`, because iOS Safari never fires
 *    `beforeunload` when a tab is backgrounded or the app is switched away from
 *    -- which on a phone is how most sessions actually end.
 */
export function useAutosave(
  save: (value: string) => Promise<unknown>,
  { enabled = true }: { enabled?: boolean } = {}
) {
  const [state, setState] = useState<SaveState>('idle')

  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pending = useRef<string | null>(null)
  // Held in a ref so the effect below never re-subscribes when the caller passes
  // a new closure on each render.
  const saveRef = useRef(save)
  saveRef.current = save

  const run = useCallback(async () => {
    const value = pending.current
    if (value === null) return
    pending.current = null
    setState('saving')
    try {
      await saveRef.current(value)
      setState('saved')
    } catch {
      // Deliberately quiet: a failed autosave is not something to interrupt
      // someone mid-thought about. The indicator turns amber, the next
      // keystroke retries, and an actual Submit surfaces any real problem.
      setState('error')
    }
  }, [])

  const schedule = useCallback(
    (value: string) => {
      if (!enabled) return
      pending.current = value
      if (timer.current) clearTimeout(timer.current)
      timer.current = setTimeout(run, DEBOUNCE_MS)
    },
    [enabled, run]
  )

  const flush = useCallback(() => {
    if (timer.current) {
      clearTimeout(timer.current)
      timer.current = null
    }
    void run()
  }, [run])

  useEffect(() => {
    const onHide = () => {
      if (pending.current !== null) flush()
    }
    window.addEventListener('pagehide', onHide)
    document.addEventListener('visibilitychange', onHide)
    return () => {
      window.removeEventListener('pagehide', onHide)
      document.removeEventListener('visibilitychange', onHide)
      // Unmounting with an edit still queued would silently drop it.
      onHide()
    }
  }, [flush])

  return { state, schedule, flush }
}
