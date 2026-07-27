// ManageTypes.jsx — admin-only panel to add / retire component types.
// This IS the place to manage what shows in the New Component dropdown.
// Retiring is a soft ARCHIVE (hidden from the picker, not deleted) so any lot
// that already used the type keeps resolving its name. Rendered on the
// Components dashboard for admins only.
import { useState, useEffect } from "react";
import { API_BASE } from "../App";
import "./ManageTypes.css";

const blankForm = () => ({ display_name: "", uid_prefix: "", is_produced_inhouse: "true", unit_of_measure: "g" });

export default function ManageTypes() {
  const [open, setOpen] = useState(false);
  const [types, setTypes] = useState([]);
  const [form, setForm] = useState(blankForm());
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");

  async function load() {
    try {
      const res = await fetch(`${API_BASE}/components/types`).then(r => r.json());
      setTypes(res.types || []);
    } catch { setErr("Failed to load types."); }
  }
  useEffect(() => { if (open) load(); }, [open]);

  async function setArchived(key, archived) {
    setErr(""); setBusy(key);
    try {
      const res = await fetch(`${API_BASE}/components/types/${encodeURIComponent(key)}`, {
        method: archived ? "DELETE" : "PATCH",
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || "Failed");
      await load();
    } catch (e) { setErr(e.message || "Failed to update type."); }
    finally { setBusy(""); }
  }

  async function add(e) {
    e.preventDefault();
    setErr(""); setBusy("__add__");
    try {
      const res = await fetch(`${API_BASE}/components/types`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          display_name: form.display_name.trim(),
          uid_prefix: form.uid_prefix.trim(),
          is_produced_inhouse: form.is_produced_inhouse === "true",
          unit_of_measure: form.unit_of_measure.trim() || "g",
        }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.detail || "Failed to add type");
      setForm(blankForm());
      await load();
    } catch (e) { setErr(e.message || "Failed to add type."); }
    finally { setBusy(""); }
  }

  return (
    <div className="mt-wrap">
      <button className="mt-toggle" onClick={() => setOpen(o => !o)}>
        ⚙ Manage Component Types {open ? "▲" : "▼"}
      </button>

      {open && (
        <div className="mt-panel">
          {err && <div className="mt-err">{err}</div>}

          <div className="mt-table-wrap">
            <table className="mt-table">
              <thead>
                <tr><th>Type</th><th>Prefix</th><th>Source</th><th>Unit</th><th>Status</th><th></th></tr>
              </thead>
              <tbody>
                {types.map(t => (
                  <tr key={t.key} className={t.archived ? "mt-archived" : ""}>
                    <td className="mt-name">{t.display_name}</td>
                    <td className="mono">{t.uid_prefix}</td>
                    <td>{t.is_produced_inhouse ? "In-house" : "Received"}</td>
                    <td>{t.unit_of_measure}</td>
                    <td>{t.archived ? <span className="mt-pill-off">Archived</span>
                                     : <span className="mt-pill-on">Active</span>}</td>
                    <td className="mt-actions">
                      {t.archived ? (
                        <button className="mt-btn" disabled={busy === t.key}
                                onClick={() => setArchived(t.key, false)}>Restore</button>
                      ) : (
                        <button className="mt-btn mt-btn-danger" disabled={busy === t.key}
                                onClick={() => setArchived(t.key, true)}>Retire</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <form className="mt-add" onSubmit={add}>
            <div className="mt-add-title">Add a type</div>
            <div className="mt-add-row">
              <input className="mt-input" placeholder="Display name (e.g. Rosin Sauce)"
                     value={form.display_name} onChange={e => setForm(f => ({ ...f, display_name: e.target.value }))} />
              <input className="mt-input mt-prefix" placeholder="PREFIX"
                     value={form.uid_prefix} onChange={e => setForm(f => ({ ...f, uid_prefix: e.target.value }))} />
              <select className="mt-input" value={form.is_produced_inhouse}
                      onChange={e => setForm(f => ({ ...f, is_produced_inhouse: e.target.value }))}>
                <option value="true">In-house</option>
                <option value="false">Received (3rd party)</option>
              </select>
              <input className="mt-input mt-unit" placeholder="g"
                     value={form.unit_of_measure} onChange={e => setForm(f => ({ ...f, unit_of_measure: e.target.value }))} />
              <button className="mt-btn mt-btn-add" type="submit"
                      disabled={busy === "__add__" || !form.display_name.trim() || !form.uid_prefix.trim()}>
                {busy === "__add__" ? "…" : "+ Add"}
              </button>
            </div>
            <div className="mt-hint">Retiring hides a type from the New Component picker but keeps existing lots intact.</div>
          </form>
        </div>
      )}
    </div>
  );
}
