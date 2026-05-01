import React, { useCallback, useEffect, useMemo, useState } from "react";
import { fetchJson } from "./api.js";
import { STORAGE_KEY } from "./constants.js";
import { InboxRequirements } from "./components/InboxRequirements.jsx";
import { ChatPanel } from "./components/ChatPanel.jsx";
import { SkillsPanel } from "./components/SkillsPanel.jsx";
import { OutputPanel } from "./components/OutputPanel.jsx";

function loadSelection() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? new Set(parsed) : null;
  } catch (_) {
    return null;
  }
}

function saveSelection(ids) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify([...ids]));
}

export default function App() {
  const [config, setConfig] = useState(null);
  const [configFailed, setConfigFailed] = useState(false);
  const [skills, setSkills] = useState([]);
  const [skillsError, setSkillsError] = useState("");
  const [inboxDocs, setInboxDocs] = useState([]);
  const [bundleInbox, setBundleInbox] = useState([]);
  const [inboxError, setInboxError] = useState("");
  const [bundleOutbox, setBundleOutbox] = useState([]);
  const [selectedIds, setSelectedIds] = useState(() => new Set());
  const [loadStatus, setLoadStatus] = useState("Loading…");
  const [agentBanner, setAgentBanner] = useState("");
  const [runError, setRunError] = useState("");

  const [runLogs, setRunLogs] = useState("");
  const [showLogs, setShowLogs] = useState(false);
  const [genMeta, setGenMeta] = useState("");
  const [running, setRunning] = useState(false);
  const [runFiles, setRunFiles] = useState([]);

  const applyPatches = useCallback((patches) => {
    if (!patches?.length) return;
    setInboxDocs((prev) => {
      const next = prev.map((d) => ({ ...d }));
      for (const p of patches) {
        const row = next.find((x) => x.name === p.name);
        if (row) row.content = (row.content || "") + (p.append || "");
      }
      return next;
    });
  }, []);

  useEffect(() => {
    const errs = [];
    let cfg = null;
    (async () => {
      try {
        cfg = await fetchJson("/api/config");
        setConfig(cfg);
      } catch (e) {
        errs.push("config: " + (e.message || e));
        setConfigFailed(true);
      }
      try {
        const s = await fetchJson("/api/skills");
        setSkills(s);
      } catch (e) {
        setSkillsError("Could not load skills: " + (e.message || String(e)));
        errs.push("skills: " + (e.message || e));
      }
      try {
        const inbox = await fetchJson("/api/inbox");
        setBundleInbox(inbox);
        setInboxDocs(inbox.map((d) => ({ name: d.name, content: d.content || "" })));
        setInboxError("");
      } catch (e) {
        setInboxError("Could not load inbox: " + (e.message || String(e)));
        errs.push("inbox: " + (e.message || e));
      }
      try {
        const ob = await fetchJson("/api/outbox");
        setBundleOutbox(ob);
      } catch (e) {
        errs.push("outbox: " + (e.message || e));
      }

      if (cfg) {
        let banner = "";
        if (!cfg.generate_backend_ready) {
          banner =
            cfg.exec_mode === "openshift-job"
              ? "Job mode unavailable (check in-cluster API / RBAC)."
              : "Set AGENT_EXEC_MODE=openshift-job on OpenShift.";
        } else if (!cfg.openai_configured) {
          banner =
            "Configure OPENAI_API_KEY or OPENAI_K8S_SECRET_NAME for Run agent (OpenAI) — not used for Qwen chat.";
        }
        setAgentBanner(banner);
        setLoadStatus(
          "Loaded · " +
            cfg.exec_mode +
            " · " +
            cfg.pi_agent_image +
            (cfg.chat_completions_configured ? " · Qwen chat OK" : " · Qwen chat not wired") +
            (cfg.generate_backend_ready && cfg.openai_configured ? " · OpenAI agent ready" : " · set OpenAI for Run agent") +
            (errs.length ? " · errors: " + errs.join("; ") : "")
        );
      } else {
        setLoadStatus(errs.length ? "Partial load · " + errs.join("; ") : "Loaded.");
      }
    })();
  }, []);

  useEffect(() => {
    if (!skills.length) return;
    const selectable = skills.filter((s) => s.selectable !== false);
    let sel = loadSelection();
    if (!sel) sel = new Set(selectable.map((s) => s.id));
    else {
      sel = new Set([...sel].filter((id) => selectable.some((s) => s.id === id)));
      if (sel.size === 0) sel = new Set(selectable.map((s) => s.id));
    }
    setSelectedIds(sel);
  }, [skills]);

  function toggleSkill(id) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      saveSelection(next);
      return next;
    });
  }

  const getInboxPayload = useCallback(
    () => inboxDocs.map((d) => ({ name: d.name, content: d.content })),
    [inboxDocs]
  );

  const getSelectedSkillIds = useCallback(() => [...selectedIds], [selectedIds]);

  async function runGenerate() {
    if (!config?.generate_backend_ready || !config?.openai_configured) return;
    setRunError("");
    setRunLogs("");
    setShowLogs(false);
    setRunning(true);
    try {
      const data = await fetchJson("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          inbox: getInboxPayload(),
          selected_skill_ids: getSelectedSkillIds(),
        }),
      });
      setRunFiles(data.files || []);
      const ec = data.exit_code !== undefined ? data.exit_code : "—";
      const mode = data.exec_mode || config?.exec_mode || "—";
      const jn = data.job_name ? " · job " + data.job_name : "";
      setGenMeta(
        "Last run · " + mode + " · exit " + ec + " · files " + ((data.files && data.files.length) || 0) + jn
      );
      const logs =
        (data.stderr ? "stderr:\n" + data.stderr : "") + (data.stdout ? "\nstdout:\n" + data.stdout : "");
      const t = logs.trim();
      setRunLogs(t);
      setShowLogs(!!t);
    } catch (e) {
      setRunError(e.message || String(e));
      try {
        const parsed = JSON.parse(e.message);
        if (parsed.stderr) {
          const t = parsed.stderr + (parsed.stdout ? "\n" + parsed.stdout : "");
          setRunLogs(t);
          setShowLogs(true);
        }
      } catch (_) {}
    } finally {
      setRunning(false);
    }
  }

  function resetInbox() {
    setInboxDocs(bundleInbox.map((d) => ({ name: d.name, content: d.content || "" })));
  }

  const stableConfig = useMemo(() => config, [config]);
  const outputGenError = runError || agentBanner;

  return (
    <div className="wrap">
      <header className="topbar">
        <h1>Marketing Intern Agent</h1>
        <p>
          <strong>Chat</strong> (Qwen) fills <code>inbox/</code> · <strong>Run agent</strong> uses OpenAI API ·
          Skills · Output
        </p>
      </header>

      <div className="dashboard">
        <div className="col-left">
          <InboxRequirements
            items={inboxDocs}
            inboxError={inboxError}
            onItemsChange={setInboxDocs}
            onRequestGenerate={runGenerate}
          />
          <ChatPanel config={stableConfig} configFailed={configFailed} onPatches={applyPatches} />
        </div>

        <SkillsPanel skills={skills} error={skillsError} selectedIds={selectedIds} onToggle={toggleSkill} />

        <OutputPanel
          config={stableConfig}
          genError={outputGenError}
          runLogs={runLogs}
          showLogs={showLogs}
          genMeta={genMeta}
          running={running}
          runFiles={runFiles}
          bundleOutbox={bundleOutbox}
          onRunAgent={runGenerate}
          onResetInbox={resetInbox}
        />
      </div>

      <p className="status">{loadStatus}</p>
    </div>
  );
}
