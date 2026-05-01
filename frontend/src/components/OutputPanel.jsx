import React from "react";

/** Right column: Run agent, logs, run outbox + bundle snapshot. */
export function OutputPanel({
  config,
  genError,
  runLogs,
  showLogs,
  genMeta,
  running,
  runFiles,
  bundleOutbox,
  onRunAgent,
  onResetInbox,
}) {
  const openaiReady = config?.generate_backend_ready && config?.openai_configured;

  return (
    <section className="panel output-panel" aria-labelledby="lbl-out">
      <div className="panel-head">
        <h2 id="lbl-out">Output</h2>
        <p>
          Agent run results — sections start collapsed. <strong>Run agent</strong> calls the pi-agent job with
          your <strong>OpenAI API</strong> credentials.
        </p>
      </div>
      <div className="panel-body">
        <div className={"err-box" + (genError ? " show" : "")}>{genError}</div>
        <div className="toolbar">
          <button type="button" className="btn" disabled={!openaiReady || running} onClick={onRunAgent}>
            {running ? (
              <>
                <span className="spinner" /> Running…
              </>
            ) : (
              "Run agent (OpenAI)"
            )}
          </button>
          <button type="button" className="btn btn-secondary" onClick={onResetInbox}>
            Reset inbox
          </button>
        </div>
        <div className="gen-meta">{genMeta}</div>
        <div id="run-outbox-root">
          {!runFiles.length ? (
            <p className="empty">No output yet. Run the agent.</p>
          ) : (
            runFiles.map((f) => {
              const isImg = f.kind === "image" && f.base64 && f.mime;
              return (
                <details key={f.name} className="out-file">
                  <summary>{f.name}</summary>
                  {isImg ? (
                    <div className="out-img-wrap">
                      <img
                        className="out-img"
                        src={"data:" + f.mime + ";base64," + f.base64}
                        alt={f.name}
                      />
                    </div>
                  ) : (
                    <pre className="out-pre">{f.content || ""}</pre>
                  )}
                </details>
              );
            })
          )}
        </div>
        <div className={"log-box" + (showLogs ? " show" : "")}>{runLogs}</div>
        <div className="subhead">Bundle snapshot</div>
        <div id="bundle-outbox-root">
          {!bundleOutbox.length ? (
            <p className="empty">No bundled outbox.</p>
          ) : (
            bundleOutbox.map((d) => (
              <details key={d.name} className="out-file">
                <summary>{d.name}</summary>
                <pre className="out-pre bundle-pre">{d.content || ""}</pre>
              </details>
            ))
          )}
        </div>
      </div>
    </section>
  );
}
