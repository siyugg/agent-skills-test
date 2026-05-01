import React from "react";

/** Center column: skill checkboxes + always-included agent files. */
export function SkillsPanel({ skills, error, selectedIds, onToggle }) {
  return (
    <section className="panel skills-panel" aria-labelledby="lbl-skills">
      <div className="panel-head">
        <h2 id="lbl-skills">Skills</h2>
        <p>
          Checkboxes control <code>skill_*.md</code> files; other <code>agent/*.md</code> files are always
          included in runs.
        </p>
      </div>
      <div className="panel-body">
        {error ? (
          <p className="empty">{error}</p>
        ) : !skills.length ? (
          <p className="empty">
            No markdown files in <code>agent/</code>.
          </p>
        ) : (
          skills.map((s) => {
            const selectable = s.selectable !== false;
            if (!selectable) {
              return (
                <div key={s.id} className="skill-row skill-row-static" data-skill-id={s.id} data-selectable="0">
                  <span className="skill-static-tag">always</span>
                  <div>
                    <span className="skill-title">{s.title}</span>
                    <span className="skill-excerpt">
                      {(s.filename || "") + " — " + (s.excerpt || "")}
                    </span>
                  </div>
                </div>
              );
            }
            const checked = selectedIds.has(s.id);
            return (
              <div key={s.id} className="skill-row" data-skill-id={s.id} data-selectable="1">
                <input
                  type="checkbox"
                  id={"sk-" + s.id}
                  checked={checked}
                  onChange={() => onToggle(s.id)}
                />
                <label htmlFor={"sk-" + s.id}>
                  <span className="skill-title">{s.title}</span>
                  <span className="skill-excerpt">{s.excerpt || ""}</span>
                </label>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}
