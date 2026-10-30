"use strict";

const incremental = document.getElementById("incremental");
const full = document.getElementById("full");
const error = document.getElementById("error");
let submitting = false;
let running = false;
let connected = false;

function setButtons() {
  incremental.disabled = full.disabled = submitting || running || !connected;
}

function showError(message) {
  error.textContent = message;
  error.hidden = !message;
}

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, cache: "no-store", credentials: "same-origin" });
  if (response.status === 401) {
    window.location.assign("/login");
    throw new Error("Please sign in again.");
  }
  if (response.status === 403) throw new Error("Access denied or session expired. Reload the page to continue.");
  if (!response.headers.get("content-type")?.includes("application/json")) {
    throw new Error("Admin is unavailable. Check the server and reload this page.");
  }
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "Request failed. Please try again.");
  return result;
}

function render(state) {
  running = state.status === "running";
  connected = true;
  const badge = document.getElementById("badge");
  badge.textContent = { idle: "Ready", running: "Running", succeeded: "Complete", warning: "Completed with warnings", failed: "Failed" }[state.status] || state.status;
  badge.dataset.state = state.status;
  document.getElementById("message").textContent = state.message;
  const timing = [];
  if (state.started_by) timing.push(`By ${state.started_by}`);
  if (state.mode) timing.push(state.mode === "full" ? "Full refetch" : "Incremental update");
  if (state.started_at) timing.push(`Started ${new Date(state.started_at).toLocaleString()}`);
  if (state.finished_at) timing.push(`Finished ${new Date(state.finished_at).toLocaleString()}`);
  document.getElementById("timing").textContent = timing.join(" · ");
  const logs = document.getElementById("logs");
  const atBottom = logs.scrollHeight - logs.scrollTop - logs.clientHeight < 40;
  logs.textContent = state.logs.join("\n") || "No log output yet.";
  if (atBottom) logs.scrollTop = logs.scrollHeight;
  const history = document.getElementById("history");
  history.replaceChildren();
  for (const update of state.history) {
    const row = document.createElement("tr");
    for (const value of [new Date(update.started_at).toLocaleString(), update.started_by, update.mode, update.status]) {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.appendChild(cell);
    }
    row.title = update.message;
    history.appendChild(row);
  }
  setButtons();
}

async function refresh() {
  try {
    const state = await api("/admin/api/status");
    if (!submitting) {
      render(state);
      showError("");
    }
  } catch (exc) {
    connected = false;
    setButtons();
    showError(exc.message);
  } finally {
    window.setTimeout(refresh, 2000);
  }
}

async function start(mode) {
  if (submitting || running || !connected) return;
  if (mode === "full" && !window.confirm("Rebuild all records from the current input files? This includes edits and removes records for deleted or renamed files. Existing records will be backed up. Input files are not changed.")) return;
  submitting = true;
  setButtons();
  showError("");
  try {
    render(await api("/admin/api/update", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]').content },
      body: JSON.stringify({ mode, confirm: mode === "full" }),
    }));
  } catch (exc) {
    showError(exc.message);
  } finally {
    submitting = false;
    setButtons();
  }
}

incremental.addEventListener("click", () => start("incremental"));
full.addEventListener("click", () => start("full"));
refresh();
