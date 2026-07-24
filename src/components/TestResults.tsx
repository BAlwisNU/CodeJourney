import type { HarnessResult } from '../lib/types'

/**
 * L0 of the hint ladder: run output and test results. Free, immediate, always.
 *
 * The rendering rule throughout: never show a bare traceback as the primary
 * message. A novice reading "IndexError: list index out of range" learns
 * nothing; the raw text stays available behind a disclosure for the curious and
 * for instructors, but it is not what greets them.
 */
export function TestResults({
  result,
  translatedError,
}: {
  result: HarnessResult | null
  translatedError?: string | null
}) {
  if (!result) {
    return (
      <p className="muted">
        Hit <strong>Run</strong> when you want to see what your code does. As many
        times as you like — nothing here is graded.
      </p>
    )
  }

  if (result.phase === 'syntax_error') {
    return (
      <div className="panel panel-error">
        <h3>Python couldn&rsquo;t read your code</h3>
        <p>
          {translatedError ??
            "There's a typo somewhere that stops Python understanding the file."}
        </p>
        <RawDetail error={result.error?.traceback} />
      </div>
    )
  }

  if (result.phase === 'missing_entrypoint') {
    return (
      <div className="panel panel-error">
        <h3>That function isn&rsquo;t there yet</h3>
        <p>{result.error?.message}</p>
      </div>
    )
  }

  if (result.phase === 'timeout') {
    return (
      <div className="panel panel-error">
        <h3>Your program didn&rsquo;t stop</h3>
        <p>{translatedError ?? result.error?.message}</p>
      </div>
    )
  }

  if (result.phase === 'harness_error') {
    return (
      <div className="panel panel-error">
        <h3>That one&rsquo;s on us</h3>
        <p>{result.error?.message}</p>
        <RawDetail error={result.error?.traceback} />
      </div>
    )
  }

  const { passed, total } = result.summary
  // A test that threw is the commonest failure a novice hits, and it's the one
  // where a raw traceback helps least. Lift the translation to the top rather
  // than leaving it buried in a per-test detail block.
  const threw = result.tests.find((t) => t.status === 'error')

  return (
    <div className="panel">
      <h3>
        {passed} of {total} checks passing
      </h3>

      {threw && translatedError && (
        <div className="translated-banner">
          <h4>What went wrong</h4>
          <p>{translatedError}</p>
          <RawDetail error={threw.error?.traceback} />
        </div>
      )}

      {result.stdout && (
        <pre className="stdout" aria-label="Program output">
          {result.stdout}
        </pre>
      )}

      <ul className="tests">
        {result.tests.map((test, index) => (
          <li key={index} className={`test test-${test.status}`}>
            <div className="test-head">
              <span className="test-icon" aria-hidden>
                {test.status === 'pass' ? '✓' : test.status === 'fail' ? '✗' : '!'}
              </span>
              <span className="test-name">{test.name}</span>
              {test.hidden && <span className="badge">hidden</span>}
            </div>

            {test.status === 'fail' && !test.hidden && (
              <dl className="test-detail">
                <dt>Given</dt>
                <dd><code>{test.args}</code></dd>
                <dt>Expected</dt>
                <dd><code>{test.expected}</code></dd>
                <dt>Got</dt>
                <dd><code>{test.actual}</code></dd>
              </dl>
            )}

            {test.status === 'fail' && test.hidden && (
              <p className="test-detail muted">
                This one checks an edge case we&rsquo;re keeping to ourselves.
                Think about the unusual inputs.
              </p>
            )}

            {test.status === 'error' && (
              <div className="test-detail">
                <p>
                  Your code stopped with a <code>{test.error?.type}</code>
                  {test.error?.line != null && <> on line {test.error.line}</>}.
                </p>
                <RawDetail error={test.error?.traceback} />
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

function RawDetail({ error }: { error?: string }) {
  if (!error) return null
  return (
    <details className="raw">
      <summary>Show me the raw error</summary>
      <pre>{error}</pre>
    </details>
  )
}
