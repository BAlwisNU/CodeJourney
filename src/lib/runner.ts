/**
 * Main-thread client for the Pyodide worker.
 *
 * Owns the timeout policy. If the worker doesn't answer in time we terminate it
 * and build a result that looks exactly like the server's timeout result -- same
 * shape, same phase, same message. The student sees one explanation for
 * "your loop never ends", whichever path produced it.
 */

import type { HarnessResult } from './types'

const RUN_TIMEOUT_MS = 5000

let worker: Worker | null = null
let nextId = 0

function spawn(): Worker {
  return new Worker(new URL('./pyodide.worker.ts', import.meta.url), {
    type: 'module',
  })
}

function timeoutResult(): HarnessResult {
  // Mirrors _timeout_result() in apps/api/app/services/grading.py. If you change
  // one, change the other -- this is the one place the shared harness can't
  // enforce agreement for us, because timeouts are enforced by the environment
  // rather than by the harness.
  return {
    phase: 'timeout',
    error: {
      type: 'Timeout',
      message:
        'Your program was still running after 5 seconds, so it was stopped. ' +
        'This usually means a loop that never ends.',
      line: null,
      traceback: '',
    },
    stdout: '',
    tests: [],
    passed: false,
    summary: { passed: 0, total: 0 },
  }
}

export function runInBrowser(
  source: string,
  entrypoint: string,
  tests: unknown[]
): Promise<HarnessResult> {
  if (!worker) worker = spawn()
  const active = worker
  const id = String(nextId++)

  return new Promise((resolve) => {
    const timer = setTimeout(() => {
      active.removeEventListener('message', onMessage)
      // Kill it. This is the whole reason the worker exists.
      active.terminate()
      // Next run gets a fresh worker, which means paying the Pyodide load cost
      // again. That's the correct trade: an infinite loop is rare, and a
      // terminated interpreter can't be trusted to still be sane.
      worker = null
      resolve(timeoutResult())
    }, RUN_TIMEOUT_MS)

    function onMessage(event: MessageEvent) {
      if (event.data.id !== id) return
      clearTimeout(timer)
      active.removeEventListener('message', onMessage)
      if (event.data.ok) {
        resolve(event.data.result as HarnessResult)
      } else {
        resolve({
          phase: 'harness_error',
          error: {
            type: 'PlatformError',
            message:
              "Something went wrong on our end, not in your code. Try Run again.",
            line: null,
            traceback: String(event.data.error),
          },
          stdout: '',
          tests: [],
          passed: false,
          summary: { passed: 0, total: 0 },
        })
      }
    }

    active.addEventListener('message', onMessage)
    active.postMessage({ id, source, entrypoint, tests })
  })
}

/** Start loading Pyodide early, so the first Run isn't a 10MB wait. */
export function warmUp(): void {
  if (!worker) worker = spawn()
}
