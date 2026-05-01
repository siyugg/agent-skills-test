import React from "react";

/** Left column — top: collapsible inbox markdown editors. */
export function InboxRequirements({ items, inboxError, onItemsChange, onRequestGenerate }) {
  const updateContent = (name, content) => {
    onItemsChange(items.map((it) => (it.name === name ? { ...it, content } : it)));
  };

  return (
    <section className="panel inbox-panel" aria-labelledby="lbl-inbox">
      <div className="panel-head">
        <h2 id="lbl-inbox">Inbox requirements</h2>
        <p>
          One section per inbox file. Qwen chat appends structured notes here; refine then run the agent.
        </p>
      </div>
      <div className="panel-body">
        {inboxError ? (
          <p className="empty">{inboxError}</p>
        ) : !items.length ? (
          <p className="empty">No inbox files in bundle.</p>
        ) : (
          items.map((d, i) => (
            <details key={d.name} className="inbox-section" open={i === 0} data-inbox-name={d.name}>
              <summary>{d.name}</summary>
              <textarea
                className="inbox-edit"
                aria-label={d.name}
                value={d.content ?? ""}
                onChange={(e) => updateContent(d.name, e.target.value)}
                onKeyDown={(ev) => {
                  if ((ev.ctrlKey || ev.metaKey) && ev.key === "Enter") {
                    ev.preventDefault();
                    onRequestGenerate();
                  }
                }}
              />
            </details>
          ))
        )}
      </div>
    </section>
  );
}
