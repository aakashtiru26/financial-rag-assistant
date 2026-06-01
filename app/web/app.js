// ─── Config ───────────────────────────────────────────────────────────────────
const API_BASE   = "/api/v1";
const API_KEY    = "cc59ef5dc4daebc8cc6cac35b5e2a39b0dbfbc6654d6c31c0dedf24e0a374217";

// ─── State ────────────────────────────────────────────────────────────────────
const state = { selectedFile: null, documents: [] };

// ─── DOM refs (grabbed after DOMContentLoaded) ────────────────────────────────
let el = {};

// ─── Boot ─────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  el = {
    healthText:       document.getElementById("healthText"),
    documentCount:    document.getElementById("documentCount"),
    dropZone:         document.getElementById("dropZone"),
    fileInput:        document.getElementById("fileInput"),
    fileLabel:        document.getElementById("fileLabel"),
    uploadButton:     document.getElementById("uploadButton"),
    reindexButton:    document.getElementById("reindexButton"),
    refreshButton:    document.getElementById("refreshButton"),
    statusText:       document.getElementById("statusText"),
    questionInput:    document.getElementById("questionInput"),
    topKInput:        document.getElementById("topKInput"),
    askButton:        document.getElementById("askButton"),
    clearAnswerButton:document.getElementById("clearAnswerButton"),
    answerBody:       document.getElementById("answerBody"),
    citationCount:    document.getElementById("citationCount"),
    sourceCount:      document.getElementById("sourceCount"),
    sourceList:       document.getElementById("sourceList"),
    documentsTable:   document.getElementById("documentsTable"),
    toastRegion:      document.getElementById("toastRegion"),
  };

  bindEvents();
  if (window.lucide) window.lucide.createIcons();
  checkHealth();
  loadDocuments();
});

// ─── Events ───────────────────────────────────────────────────────────────────
function bindEvents() {
  // File input change — works with both <label for> click and drag-drop
  el.fileInput.addEventListener("change", () => {
    const file = el.fileInput.files[0] || null;
    state.selectedFile = file;
    el.fileLabel.textContent = file ? file.name : "Select PDF, DOCX, TXT, or CSV";
  });

  // Drag and drop onto drop zone
  el.dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    el.dropZone.classList.add("dragging");
  });
  el.dropZone.addEventListener("dragleave", () => {
    el.dropZone.classList.remove("dragging");
  });
  el.dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    el.dropZone.classList.remove("dragging");
    const file = e.dataTransfer.files[0];
    if (file) {
      state.selectedFile = file;
      el.fileLabel.textContent = file.name;
    }
  });

  el.uploadButton.addEventListener("click",    uploadDocument);
  el.reindexButton.addEventListener("click",   reindexDocuments);
  el.refreshButton.addEventListener("click",   loadDocuments);
  el.askButton.addEventListener("click",       askQuestion);
  el.clearAnswerButton.addEventListener("click", clearAnswer);
}

// ─── API helpers ──────────────────────────────────────────────────────────────
function headers(isJson = true) {
  const h = { "X-API-Key": API_KEY };
  if (isJson) h["Content-Type"] = "application/json";
  return h;
}

async function apiFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  const ct  = res.headers.get("content-type") || "";
  const body = ct.includes("application/json") ? await res.json() : await res.text();
  if (!res.ok) {
    const msg = typeof body === "object" && body !== null ? body.detail : body;
    throw new Error(msg || `HTTP ${res.status}`);
  }
  return body;
}

// ─── Health ───────────────────────────────────────────────────────────────────
async function checkHealth() {
  try {
    const data = await apiFetch("/health");
    el.healthText.textContent = `${data.status} · ${data.environment}`;
  } catch {
    el.healthText.textContent = "Service unavailable";
  }
}

// ─── Upload ───────────────────────────────────────────────────────────────────
async function uploadDocument() {
  if (!state.selectedFile) {
    toast("Please select a file first.", "error");
    return;
  }

  const form = new FormData();
  form.append("file", state.selectedFile);

  await withBusy(el.uploadButton, "Uploading…", async () => {
    setStatus(`Uploading ${state.selectedFile.name}…`);
    const data = await apiFetch("/documents", {
      method:  "POST",
      headers: headers(false),   // no Content-Type — let browser set multipart boundary
      body:    form,
    });
    toast(data.message || "Document uploaded and indexed.");
    state.selectedFile      = null;
    el.fileInput.value      = "";
    el.fileLabel.textContent = "Select PDF, DOCX, TXT, or CSV";
    setStatus("Ready");
    await loadDocuments();
  });
}

// ─── Documents ────────────────────────────────────────────────────────────────
async function loadDocuments() {
  await withBusy(el.refreshButton, "Loading…", async () => {
    try {
      const data = await apiFetch("/documents", { headers: headers(false) });
      state.documents = data.documents || [];
      renderDocuments(state.documents);
    } catch (err) {
      renderDocuments([]);
      toast(err.message, "error");
    }
  });
}

async function deleteDocument(id) {
  if (!confirm("Delete this document and rebuild the index?")) return;
  setStatus("Deleting…");
  try {
    const data = await apiFetch(`/documents/${encodeURIComponent(id)}`, {
      method:  "DELETE",
      headers: headers(false),
    });
    toast(data.message || "Deleted.");
    await loadDocuments();
  } catch (err) {
    toast(err.message, "error");
  } finally {
    setStatus("Ready");
  }
}

async function reindexDocuments() {
  await withBusy(el.reindexButton, "Re-indexing…", async () => {
    setStatus("Re-indexing all stored documents…");
    const data = await apiFetch("/documents/reindex", {
      method:  "POST",
      headers: headers(false),
    });
    toast(`${data.indexed_documents} docs, ${data.indexed_chunks} chunks indexed.`);
    setStatus("Ready");
    await loadDocuments();
  });
}

// ─── Query ────────────────────────────────────────────────────────────────────
async function askQuestion() {
  const question = el.questionInput.value.trim();
  if (!question) { toast("Enter a question first.", "error"); return; }
  const topK = parseInt(el.topKInput.value, 10) || 5;

  await withBusy(el.askButton, "Thinking…", async () => {
    setStatus("Searching documents and generating answer…");
    renderLoadingAnswer();
    const data = await apiFetch("/query", {
      method:  "POST",
      headers: headers(true),
      body:    JSON.stringify({ question, top_k: topK }),
    });
    renderAnswer(data);
    setStatus("Ready");
  });
}

// ─── Render helpers ───────────────────────────────────────────────────────────
function renderDocuments(docs) {
  el.documentCount.textContent = `${docs.length} ${docs.length === 1 ? "doc" : "docs"}`;
  if (!docs.length) {
    el.documentsTable.innerHTML = '<tr><td colspan="5" class="empty-cell">No documents loaded.</td></tr>';
    return;
  }
  el.documentsTable.innerHTML = docs.map((doc) => {
    const uploaded = doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleString() : "Unknown";
    return `<tr>
      <td>${esc(doc.filename)}</td>
      <td>${doc.chunk_count ?? 0}</td>
      <td>${esc(uploaded)}</td>
      <td><div class="doc-id" title="${esc(doc.document_id)}">${esc(doc.document_id)}</div></td>
      <td>
        <button class="btn danger" type="button" data-id="${esc(doc.document_id)}">
          <i data-lucide="trash-2"></i> Delete
        </button>
      </td>
    </tr>`;
  }).join("");

  el.documentsTable.querySelectorAll("[data-id]").forEach((btn) => {
    btn.addEventListener("click", () => deleteDocument(btn.dataset.id));
  });
  if (window.lucide) window.lucide.createIcons();
}

function renderLoadingAnswer() {
  el.answerBody.textContent    = "Generating grounded answer…";
  el.sourceList.innerHTML      = '<p class="empty-state">Fetching evidence…</p>';
  el.citationCount.textContent = "0 citations";
  el.sourceCount.textContent   = "0 chunks";
}

function renderAnswer(data) {
  el.answerBody.textContent    = data.answer || "No answer found.";
  el.citationCount.textContent = `${(data.citations || []).length} citations`;
  const sources                = data.sources || [];
  el.sourceCount.textContent   = `${sources.length} ${sources.length === 1 ? "chunk" : "chunks"}`;

  if (!sources.length) {
    el.sourceList.innerHTML = '<p class="empty-state">No passages retrieved.</p>';
    return;
  }
  el.sourceList.innerHTML = sources.map((s, i) => {
    const score = typeof s.score === "number" ? s.score.toFixed(3) : "n/a";
    const page  = s.page != null ? `<span class="chip">Page ${s.page}</span>` : "";
    const row   = s.row  != null ? `<span class="chip">Row ${s.row}</span>`  : "";
    return `<article class="source-item">
      <div class="source-meta">
        <span class="chip">#${i + 1}</span>
        <span class="chip">${esc(s.filename || "Unknown")}</span>
        <span class="chip">${esc(s.chunk_id || "chunk")}</span>
        <span class="chip">Score ${score}</span>
        ${page}${row}
      </div>
      <div class="source-text">${esc(s.text || "")}</div>
    </article>`;
  }).join("");
}

function clearAnswer() {
  el.answerBody.innerHTML      = '<p class="empty-state">No answer yet.</p>';
  el.sourceList.innerHTML      = '<p class="empty-state">Retrieved passages will appear here.</p>';
  el.citationCount.textContent = "0 citations";
  el.sourceCount.textContent   = "0 chunks";
}

// ─── UI utilities ─────────────────────────────────────────────────────────────
async function withBusy(btn, label, task) {
  const orig   = btn.innerHTML;
  btn.disabled = true;
  btn.textContent = label;
  try {
    await task();
  } catch (err) {
    toast(err.message, "error");
    setStatus("Ready");
  } finally {
    btn.disabled  = false;
    btn.innerHTML = orig;
    if (window.lucide) window.lucide.createIcons();
  }
}

function setStatus(msg) {
  if (el.statusText) el.statusText.textContent = msg;
}

function toast(msg, type = "info") {
  const node       = document.createElement("div");
  node.className   = `toast ${type === "error" ? "error" : ""}`;
  node.textContent = msg;
  el.toastRegion.appendChild(node);
  setTimeout(() => node.remove(), 4500);
}

function esc(v) {
  return String(v)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}