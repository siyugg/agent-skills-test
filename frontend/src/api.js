export async function fetchJson(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) {
    let detail = r.statusText;
    try {
      const j = await r.json();
      if (j.detail !== undefined) {
        detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail, null, 2);
      }
    } catch (_) {}
    throw new Error(detail);
  }
  return r.json();
}
