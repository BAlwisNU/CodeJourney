/// <reference lib="webworker" />
/**
 * Pyodide runner. Runs in a Web Worker, deliberately.
 *
 * Two reasons, and the second is the real one:
 *
 *  1. Loading Pyodide is ~10MB of WASM. On the main thread that's a frozen tab.
 *
 *  2. A novice's first while-loop is an infinite while-loop. Python running on
 *     the main thread cannot be interrupted -- the tab locks and the only way
 *     out is closing it, which loses their code. In a worker, the main thread
 *     can call terminate() and the loop dies. "You wrote a loop that never
 *     ends" is a lesson; "the page froze and ate your work" is not.
 *
 * The harness is imported as a raw string from packages/harness/harness.py --
 * the SAME file the server executes. Bundling it at build time (rather than
 * fetching it) means the two cannot drift apart between deploys.
 */

import { loadPyodide, type PyodideInterface } from 'pyodide'
// ?raw is typed by vite/client -- see "types" in tsconfig.json.
import harnessSource from '@harness/harness.py?raw'

// Must match the pinned CPython on the server. See apps/api/app/config.py and
// docs/architecture.md, "The divergence rule". Bumping this without bumping the
// sandbox image is how run and submit start disagreeing.
const PYODIDE_VERSION = '0.27.2'
const INDEX_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`

let pyodide: PyodideInterface | null = null

async function boot(): Promise<PyodideInterface> {
  if (pyodide) return pyodide
  pyodide = await loadPyodide({ indexURL: INDEX_URL })
  // Register the shared harness as an importable module inside the Pyodide FS.
  pyodide.FS.mkdirTree('/harness')
  pyodide.FS.writeFile('/harness/harness.py', harnessSource as string)
  pyodide.runPython(`import sys; sys.path.insert(0, "/harness")`)
  return pyodide
}

export type RunRequest = {
  id: string
  source: string
  entrypoint: string
  tests: unknown[]
}

self.onmessage = async (event: MessageEvent<RunRequest>) => {
  const { id, source, entrypoint, tests } = event.data
  try {
    const py = await boot()

    // Pass data in via globals rather than string-interpolating it into Python.
    // Interpolating student code into a Python source string would break the
    // moment their code contains a quote -- and it would be injection, in a
    // context where the "attacker" is only ever fooling themselves but the
    // resulting error message would be incomprehensible.
    py.globals.set('__cj_source', source)
    py.globals.set('__cj_entrypoint', entrypoint)
    py.globals.set('__cj_tests', py.toPy(tests))

    const result = py.runPython(`
import json, harness
json.dumps(harness.run_tests(__cj_source, __cj_entrypoint, __cj_tests.to_py()))
`)
    self.postMessage({ id, ok: true, result: JSON.parse(result as string) })
  } catch (error) {
    // Reaching here means Pyodide itself failed -- a load error, an OOM. This is
    // never the student's fault, so it must not be rendered as their mistake.
    self.postMessage({
      id,
      ok: false,
      error: error instanceof Error ? error.message : String(error),
    })
  }
}
