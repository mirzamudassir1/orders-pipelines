const $ = (id) => document.getElementById(id);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(path, opts) {
  const res = await fetch(path, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || res.statusText);
  return data;
}

function table(rows, cols, render = {}) {
  if (!rows.length) return "<p class='muted'>No data</p>";
  const head = cols.map((c) => `<th>${esc(c)}</th>`).join("");
  const body = rows.map((r) =>
    `<tr>${cols.map((c) => `<td>${render[c] ? render[c](r[c]) : esc(r[c])}</td>`).join("")}</tr>`
  ).join("");
  return `<div class="scroll"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

const badge = (s) => `<span class="badge ${esc(s)}">${esc(s)}</span>`;

async function loadQuality() {
  const rows = await api("/api/quality");
  $("quality").innerHTML = table(rows, ["check", "passed", "violations", "description"], {
    passed: (p) => `<span class="badge ${p ? "pass" : "fail"}">${p ? "PASS" : "FAIL"}</span>`,
  });
}

async function loadSummary() {
  const s = await api("/api/summary");
  $("summary").innerHTML =
    table(s.orders_by_status, ["status", "orders", "revenue_usd"]) +
    "<h3>Rejects by reason</h3>" + table(s.rejects_by_reason, ["reason_code", "rejected"]);
}

async function loadRuns() {
  const runs = await api("/api/runs");
  $("runs").innerHTML = table(runs,
    ["run_id", "source_file", "status", "started_at", "input_rows", "accepted_rows",
     "rejected_rows", "duplicate_rows", "duration_sec", "failure_reason"],
    { status: badge });
  const sel = $("runFilter");
  const current = sel.value;
  sel.innerHTML = `<option value="">All runs</option>` +
    runs.map((r) => `<option value="${esc(r.run_id)}">${esc(r.run_id)}</option>`).join("");
  sel.value = current;
}

async function loadRejects() {
  const id = $("runFilter").value;
  const rows = await api("/api/rejects" + (id ? `?run_id=${encodeURIComponent(id)}` : ""));
  $("rejects").innerHTML = table(rows,
    ["run_id", "source_file", "line_no", "reason_code", "reason_detail", "raw_record"]);
}

async function refresh() {
  await Promise.all([loadQuality(), loadSummary(), loadRuns()]);
  await loadRejects();
}

$("runFilter").addEventListener("change", loadRejects);
$("runBtn").addEventListener("click", async () => {
  const file = $("file").files[0];
  if (!file) { $("runResult").textContent = "Choose a CSV first."; return; }
  const form = new FormData();
  form.append("file", file);
  $("runResult").textContent = "Running...";
  try {
    $("runResult").textContent = JSON.stringify(await api("/api/run", { method: "POST", body: form }), null, 2);
    await refresh();
  } catch (e) {
    $("runResult").textContent = "Error: " + e.message;
  }
});

refresh().catch((e) => ($("runResult").textContent = "Error: " + e.message));