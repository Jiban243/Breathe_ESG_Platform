import React, { useState, useEffect } from "react";
import axios from "axios";

// Fallback logic: Detects if running on Render or locally, keeping paths intact
const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
const API = isLocal ? "http://127.0.0.1:8080/api" : "https://breathe-esg-backend-nu5m.onrender.com/api";
const CLIENT = "acme-manufacturing";

const SCOPE_COLORS = {
  SCOPE_1: "#ef4444",
  SCOPE_2: "#3b82f6",
  SCOPE_3: "#8b5cf6",
};

const SOURCE_LABELS = {
  SAPFUEL: "SAP Fuel",
  UTILITYELECTRICITY: "Utility",
  TRAVELCONCUR: "Travel",
};

const STATUS_COLORS = {
  PENDING_REVIEW: "#f59e0b",
  APPROVED: "#10b981",
  REJECTED: "#ef4444",
};

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [summary, setSummary] = useState(null);
  const [records, setRecords] = useState([]);
  const [batches, setBatches] = useState([]);
  const [filters, setFilters] = useState({ status: "", scope: "", source_type: "" });
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ client_slug: CLIENT });
      if (filters.status) params.append("status", filters.status);
      if (filters.scope) params.append("scope", filters.scope);
      if (filters.source_type) params.append("source_type", filters.source_type);
      
      const res = await axios.get(API + "/dashboard/?" + params.toString());
      setSummary(res.data?.summary ?? null);
      setRecords(res.data?.records ?? []);
    } catch (err) {
      console.error("Dashboard fetch failed", err);
    }
    setLoading(false);
  };

  const fetchBatches = async () => {
    try {
      const res = await axios.get(API + "/batches/?client_slug=" + CLIENT);
      setBatches(res.data ?? []);
    } catch (err) {
      console.error("Batches fetch failed", err);
    }
  };

  useEffect(() => { 
    fetchDashboard(); 
  }, [filters]);

  useEffect(() => { 
    if (tab === "batches") fetchBatches(); 
  }, [tab]);

  const handleApprove = async (id) => {
    try {
      await axios.post(API + "/review/" + id + "/", { action: "approve", actor: "analyst" });
      fetchDashboard();
    } catch (err) {
      console.error("Approval failed", err);
    }
  };

  const handleReject = async (id) => {
    try {
      await axios.post(API + "/review/" + id + "/", { action: "reject", actor: "analyst" });
      fetchDashboard();
    } catch (err) {
      console.error("Rejection failed", err);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    const form = e.target;
    const data = new FormData();
    // Aligned to exact backend requirements keys
    data.append("source_type", form.source_type.value);
    data.append("client_slug", CLIENT);
    data.append("file", form.file.files[0]);
    
    setUploading(true);
    setUploadResult(null);
    try {
      // Clean trailing slash to prevent local Django redirect loops
      const res = await axios.post(API + "/upload/", data);
      setUploadResult({ ok: true, ...res.data });
      fetchDashboard();
    } catch (err) {
      setUploadResult({ ok: false, error: err.response?.data?.error || "Upload connection rejected" });
    }
    setUploading(false);
    form.reset();
  };

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", minHeight: "100vh", background: "#f8fafc" }}>
      {/* Header */}
      <div style={{ background: "#0f172a", color: "#fff", padding: "16px 32px", display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#10b981" }} />
        <span style={{ fontWeight: 600, fontSize: 18 }}>Breathe ESG</span>
        <span style={{ color: "#64748b", fontSize: 14, marginLeft: 8 }}>Acme Manufacturing Pvt Ltd</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
          {["dashboard", "upload", "batches"].map(t => (
            <button key={t} onClick={() => setTab(t)} style={{
              background: tab === t ? "#1e40af" : "transparent",
              color: tab === t ? "#fff" : "#94a3b8",
              border: "none", borderRadius: 6, padding: "6px 16px",
              cursor: "pointer", fontSize: 13, fontWeight: 500, textTransform: "capitalize"
            }}>{t}</button>
          ))}
        </div>
      </div>

      <div style={{ padding: "24px 32px" }}>
        {/* DASHBOARD TAB */}
        {tab === "dashboard" && (
          <>
            {/* Summary Cards */}
            {summary && (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 12, marginBottom: 24 }}>
                {[
                  { label: "Total records", value: summary?.total ?? 0, color: "#0f172a" },
                  { label: "Pending review", value: summary?.pending ?? 0, color: "#f59e0b" },
                  { label: "Approved", value: summary?.approved ?? 0, color: "#10b981" },
                  { label: "Rejected", value: summary?.rejected ?? 0, color: "#ef4444" },
                  { label: "Flagged", value: summary?.flagged ?? 0, color: "#f97316" },
                  { 
                    label: "Total CO₂e (kg)", 
                    value: summary?.totalco2ekg ? summary.totalco2ekg.toLocaleString("en-IN", { maximumFractionDigits: 0 }) : 0, 
                    color: "#6366f1" 
                  },
                ].map(card => (
                  <div key={card.label} style={{ background: "#fff", borderRadius: 10, padding: "16px", boxShadow: "0 1px 3px rgba(0,0,0,0.07)" }}>
                    <div style={{ fontSize: 22, fontWeight: 700, color: card.color }}>{card.value}</div>
                    <div style={{ fontSize: 12, color: "#64748b", marginTop: 4 }}>{card.label}</div>
                  </div>
                ))}
              </div>
            )}

            {/* Filters */}
            <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
              <select value={filters.status} onChange={e => setFilters(prev => ({ ...prev, status: e.target.value }))} style={{ padding: "7px 12px", borderRadius: 6, border: "1px solid #e2e8f0", fontSize: 13, background: "#fff" }}>
                <option value="">All statuses</option>
                <option value="PENDING_REVIEW">Pending</option>
                <option value="APPROVED">Approved</option>
                <option value="REJECTED">Rejected</option>
              </select>

              <select value={filters.scope} onChange={e => setFilters(prev => ({ ...prev, scope: e.target.value }))} style={{ padding: "7px 12px", borderRadius: 6, border: "1px solid #e2e8f0", fontSize: 13, background: "#fff" }}>
                <option value="">All scopes</option>
                <option value="SCOPE_1">Scope 1</option>
                <option value="SCOPE_2">Scope 2</option>
                <option value="SCOPE_3">Scope 3</option>
              </select>

              <select value={filters.source_type} onChange={e => setFilters(prev => ({ ...prev, source_type: e.target.value }))} style={{ padding: "7px 12px", borderRadius: 6, border: "1px solid #e2e8f0", fontSize: 13, background: "#fff" }}>
                <option value="">All sources</option>
                <option value="SAPFUEL">SAP Fuel</option>
                <option value="UTILITYELECTRICITY">Utility</option>
                <option value="TRAVELCONCUR">Travel</option>
              </select>

              <span style={{ marginLeft: "auto", fontSize: 13, color: "#64748b", alignSelf: "center" }}>
                {loading ? "Loading..." : (records?.length ?? 0) + " records"}
              </span>
            </div>

            {/* Records Table */}
            <div style={{ background: "#fff", borderRadius: 10, boxShadow: "0 1px 3px rgba(0,0,0,0.07)", overflow: "hidden" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#f1f5f9", borderBottom: "1px solid #e2e8f0" }}>
                    {["Scope", "Source", "Category", "Period", "Quantity", "CO₂e (kg)", "Status", "Flag", "Actions"].map(h => (
                      <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontWeight: 600, color: "#475569", fontSize: 12 }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {records && records.map((r, i) => (
                    <tr key={r.id} style={{ borderBottom: "1px solid #f1f5f9", background: i % 2 === 0 ? "#fff" : "#fafafa" }}>
                      <td style={{ padding: "10px 14px" }}>
                        <span style={{ background: (SCOPE_COLORS[r.scope] || "#64748b") + "20", color: SCOPE_COLORS[r.scope] || "#64748b", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
                          {r.scope ? r.scope.replace("SCOPE_", "S") : ""}
                        </span>
                      </td>
                      <td style={{ padding: "10px 14px", color: "#64748b" }}>{SOURCE_LABELS[r.source_type] || r.source_type}</td>
                      <td style={{ padding: "10px 14px", fontWeight: 500 }}>{r.category}</td>
                      <td style={{ padding: "10px 14px", color: "#64748b", fontSize: 12 }}>
                        {r.period_start === r.period_end ? r.period_start : r.period_start + " → " + r.period_end}
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        {(r.quantity_norm ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 1 })} {r.unit_norm}
                      </td>
                      <td style={{ padding: "10px 14px", fontWeight: 600 }}>
                        {(r.co2e_kg ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 1 })}
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        <span style={{ background: (STATUS_COLORS[r.status] || "#64748b") + "20", color: STATUS_COLORS[r.status] || "#64748b", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
                          {r.status === "PENDING_REVIEW" ? "Pending" : r.status === "APPROVED" ? "Approved" : "Rejected"}
                        </span>
                      </td>
                      <td style={{ padding: "10px 14px", maxWidth: 200 }}>
                        {r.flagged_reason && (
                          <span style={{ color: "#f97316", fontSize: 11 }} title={r.flagged_reason}>
                            ⚠ {r.flagged_reason.length > 40 ? r.flagged_reason.slice(0, 40) + "…" : r.flagged_reason}
                          </span>
                        )}
                      </td>
                      <td style={{ padding: "10px 14px" }}>
                        {r.status === "PENDING_REVIEW" && (
                          <div style={{ display: "flex", gap: 6 }}>
                            <button onClick={() => handleApprove(r.id)} style={{ background: "#10b981", color: "#fff", border: "none", borderRadius: 5, padding: "4px 10px", fontSize: 12, cursor: "pointer" }}>✓</button>
                            <button onClick={() => handleReject(r.id)} style={{ background: "#ef4444", color: "#fff", border: "none", borderRadius: 5, padding: "4px 10px", fontSize: 12, cursor: "pointer" }}>✗</button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(!records || records.length === 0) && !loading && (
                <div style={{ padding: 40, textAlign: "center", color: "#94a3b8" }}>No records found</div>
              )}
            </div>
          </>
        )}

        {/* UPLOAD TAB */}
        {tab === "upload" && (
          <div style={{ maxWidth: 480, margin: "0 auto" }}>
            <div style={{ background: "#fff", borderRadius: 12, padding: 32, boxShadow: "0 1px 3px rgba(0,0,0,0.07)" }}>
              <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 6, color: "#0f172a" }}>Upload data file</h2>
              <p style={{ fontSize: 13, color: "#64748b", marginBottom: 24 }}>Upload a CSV export from SAP, your utility portal, or Concur.</p>
              <form onSubmit={handleUpload}>
                <div style={{ marginBottom: 16 }}>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 500, marginBottom: 6, color: "#374151" }}>Data source</label>
                  <select name="source_type" required style={{ width: "100%", padding: "9px 12px", borderRadius: 7, border: "1px solid #e2e8f0", fontSize: 14 }}>
                    <option value="">Select source…</option>
                    <option value="SAPFUEL">SAP — Fuel & Procurement (MB51)</option>
                    <option value="UTILITYELECTRICITY">Utility — Electricity portal CSV</option>
                    <option value="TRAVELCONCUR">Travel — Concur expense export</option>
                  </select>
                </div>
                <div style={{ marginBottom: 24 }}>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 500, marginBottom: 6, color: "#374151" }}>CSV file</label>
                  <input name="file" type="file" accept=".csv" required style={{ width: "100%", padding: "9px 12px", borderRadius: 7, border: "1px solid #e2e8f0", fontSize: 13 }} />
                </div>
                <button type="submit" disabled={uploading} style={{ width: "100%", background: uploading ? "#94a3b8" : "#1e40af", color: "#fff", border: "none", borderRadius: 7, padding: "11px", fontSize: 14, fontWeight: 600, cursor: uploading ? "not-allowed" : "pointer" }}>
                  {uploading ? "Uploading…" : "Upload and ingest"}
                </button>
              </form>
              {uploadResult && (
                <div style={{ marginTop: 20, padding: 16, borderRadius: 8, background: uploadResult.ok ? "#f0fdf4" : "#fef2f2", border: "1px solid " + (uploadResult.ok ? "#bbf7d0" : "#fecaca") }}>
                  {uploadResult.ok ? (
                    <>
                      <div style={{ color: "#15803d", fontWeight: 600, marginBottom: 4 }}>✓ Ingestion complete</div>
                      <div style={{ fontSize: 13, color: "#166534" }}>{(uploadResult.row_count ?? 0)} rows processed · {(uploadResult.error_count ?? 0)} errors</div>
                    </>
                  ) : (
                    <div style={{ color: "#dc2626", fontSize: 13 }}>✗ {uploadResult.error}</div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* BATCHES TAB */}
        {tab === "batches" && (
          <div style={{ background: "#fff", borderRadius: 10, boxShadow: "0 1px 3px rgba(0,0,0,0.07)", overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f1f5f9", borderBottom: "1px solid #e2e8f0" }}>
                  {["Source", "File", "Status", "Rows", "Errors", "Uploaded by", "Uploaded at"].map(h => (
                    <th key={h} style={{ padding: "10px 14px", textAlign: "left", fontWeight: 600, color: "#475569", fontSize: 12 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {batches && batches.map((b, i) => (
                  <tr key={b.id} style={{ borderBottom: "1px solid #f1f5f9", background: i % 2 === 0 ? "#fff" : "#fafafa" }}>
                    <td style={{ padding: "10px 14px" }}>{SOURCE_LABELS[b.source_type] || b.source_type}</td>
                    <td style={{ padding: "10px 14px", fontFamily: "monospace", fontSize: 12 }}>{b.filename}</td>
                    <td style={{ padding: "10px 14px" }}>
                      <span style={{ background: b.status === "DONE" ? "#f0fdf4" : "#fef9c3", color: b.status === "DONE" ? "#15803d" : "#92400e", padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600 }}>
                        {b.status}
                      </span>
                    </td>
                    <td style={{ padding: "10px 14px" }}>{b.row_count}</td>
                    <td style={{ padding: "10px 14px", color: b.error_count > 0 ? "#ef4444" : "#64748b" }}>{b.error_count}</td>
                    <td style={{ padding: "10px 14px", color: "#64748b" }}>{b.ingested_by}</td>
                    <td style={{ padding: "10px 14px", color: "#64748b", fontSize: 12 }}>{b.ingested_at ? new Date(b.ingested_at).toLocaleString("en-IN") : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}