import { API_BASE, token } from './api'

/**
 * Reading a streamed reply, and making it look like someone writing.
 *
 * Two jobs, and the second one is the interesting half.
 *
 * **Reading.** The API streams newline-delimited JSON over a plain POST rather
 * than Server-Sent Events, because `EventSource` cannot set an Authorization
 * header and this API is bearer-token only. So: fetch, take the body reader,
 * split on newlines, parse each line.
 *
 * **Smoothing.** Measured against the real API, a short reply arrives in about
 * two large chunks, not word by word. Painting those straight to the screen
 * gives a blank pause and then a wall of text appearing at once — which looks
 * *worse* than a spinner, because the interface lurches. So text lands in a
 * buffer and is revealed at a readable rate.
 *
 * The rate adapts. A fixed characters-per-second would make a long reply take
 * longer to display than it took to generate, which is the failure mode of
 * every fake typewriter effect: the machine finished and is pretending it
 * hasn't. Instead the backlog is always cleared within DRAIN_MS, so a big
 * buffer moves fast and a trickle stays gentle, and the animation ends when the
 * content does.
 */

export type StreamEvent =
  | { type: 'thinking' }
  | { type: 'text'; value: string }
  | { type: 'done'; [key: string]: unknown }
  | { type: 'error'; message: string }

/** Slowest the reveal ever goes, in characters per second. */
const FLOOR_CPS = 220
/** However big the backlog, it is cleared within this many milliseconds. */
const DRAIN_MS = 320
/** One animation frame, near enough. */
const TICK_MS = 16

/**
 * Releases buffered text at a readable, self-adjusting rate.
 *
 * Kept as its own object so the reveal logic can be reasoned about without the
 * networking around it, and so `finished` gives the caller one thing to await.
 */
function reveal(onText: (soFar: string) => void) {
  let pending = ''
  let shown = ''
  let closed = false
  let timer: number | null = null
  let settle: (() => void) | null = null

  const finished = new Promise<void>((resolve) => {
    settle = resolve
  })

  function step() {
    if (pending.length === 0) {
      timer = null
      if (closed) settle?.()
      return
    }
    // Enough characters to clear whatever is waiting within DRAIN_MS, but never
    // slower than the floor. Both ends matter: the floor stops a one-word reply
    // creeping out, the ratio stops a long one lagging behind the model.
    const toClearBacklog = Math.ceil(pending.length / (DRAIN_MS / TICK_MS))
    const atFloor = Math.ceil((FLOOR_CPS * TICK_MS) / 1000)
    const take = Math.max(1, atFloor, toClearBacklog)
    shown += pending.slice(0, take)
    pending = pending.slice(take)
    onText(shown)
    timer = window.setTimeout(step, TICK_MS)
  }

  return {
    push(chunk: string) {
      pending += chunk
      if (timer === null) step()
    },
    close() {
      closed = true
      if (timer === null && pending.length === 0) settle?.()
    },
    /** Resolves once the stream has closed *and* the buffer has drained, so a
     *  caller clearing its "writing" state doesn't cut off the last words. */
    finished,
  }
}

/**
 * POST to a streaming endpoint and report each event.
 *
 * Text is buffered and released through `onText` as a growing string — the
 * caller renders it directly rather than concatenating, so a re-render mid
 * stream can never double up.
 */
export async function streamChat(
  path: string,
  body: unknown,
  handlers: {
    onText: (soFar: string) => void
    onThinking?: () => void
    onDone?: (payload: Record<string, unknown>) => void
    onError?: (message: string) => void
  }
): Promise<void> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token.get() ?? ''}`,
    },
    body: JSON.stringify(body),
  })

  if (!response.ok || !response.body) {
    // Try for the API's own wording before inventing any.
    let detail = 'I could not reach my brain just then. Try again in a moment.'
    try {
      const payload = await response.json()
      if (typeof payload?.detail === 'string') detail = payload.detail
    } catch {
      /* Not JSON. The default above is already a sentence. */
    }
    throw new Error(detail)
  }

  const stream = reveal(handlers.onText)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let carry = ''

  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      carry += decoder.decode(value, { stream: true })
      const lines = carry.split('\n')
      // The last piece may be half a line; keep it for the next read.
      carry = lines.pop() ?? ''
      for (const line of lines) {
        if (!line.trim()) continue
        let event: StreamEvent
        try {
          event = JSON.parse(line)
        } catch {
          continue // A malformed line is not worth failing the turn over.
        }
        if (event.type === 'text') stream.push(event.value)
        else if (event.type === 'thinking') handlers.onThinking?.()
        else if (event.type === 'error') handlers.onError?.(event.message)
        else if (event.type === 'done')
          handlers.onDone?.(event as Record<string, unknown>)
      }
    }
  } finally {
    stream.close()
  }

  await stream.finished
}
