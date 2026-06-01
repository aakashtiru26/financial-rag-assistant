const API_BASE = "/api/v1";

// API key is hardcoded — users never need to enter it
const HARDCODED_API_KEY = "cc59ef5dc4daebc8cc6cac35b5e2a39b0dbfbc6654d6c31c0dedf24e0a374217";

const state = {
  apiKey: HARDCODED_API_KEY,
  selectedFile: null,
  documents: [],
};

const el = {
  healthText: document.getElementById("healthText"),
  documentCount: document.getElementById("documentCount"),
  dropZone: document.getElementById("dropZone"),
  browseButton: document.getElementById("browseButton"),
  fileInput: document.getElementById("fileInput"),
  fileLabel: document.getElementById("fileLabel"),
  uploadButton: document.getElementById("uploadButton"),
  reindexButton: document.getElementById("reindexButton"),
  refreshButton: document.getElementById("refreshButton"),
  statusText: document.getElementById("statusText"),
  runDot: document.getElementById("runDot"),
  questionInput: document.getElementById("questionInput"),
  topKInput: document.getElementById("topKInput"),
  askButton: document.getElementById("askButton"),
  clearAnswerButton: document.getElementById("clearAnswerButton"),
  answerBody: document.getElementById("answerBody"),
  citationCount: document.getElementById("citationCount"),
  sourceCount: document.getElementById("sourceCount"),
  sourceList: document.getElementById("sourceList"),
  documentsTable: document.getElementById("documentsTable"),
  toastRegion: document.getElementById("toastRegion"),
};

function init() {
  bindEvents();
  hydrateIcons();
  checkHealth();
  loadDocuments();
}

function hydrateIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function bindEvents() {
  el.browseButton.addEventListener("click", () => {
    if (typeof el.fileInput.showPicker === "function") {
      el.fileInput.showPicker();
      return;
    }
    el.fileInput.click();
  });

  el.dropZone.addEventListener("click", (event) => {
    if (event.target.closest("button") || event.target.closest("input")) return;
    el.fileInput.click();
  });

  el.fileInput.addEventListener("change", handleFileSelection);
  el.uploadButton.addEventListener("click", uploadDocument);
  el.reindexButton.addEventListener("click", reindexDocuments);
  el.refreshButton.addEventListener("click", loadDocuments);
  el.askButton.addEventListener("click", askQuestion);
  el.clearAnswerButton.addEventListener("click", clearAnswer);

  el.dropZone.addEventListener("dragover", (event) => {
    event.preventDefault();
    el.dropZone.classList.add("dragging");
  });
  el.dropZone.addEventListener("dragleave", () => el.dropZone.classList.remove("dragging"));
  el.dropZone.addEventListener("drop", (event) => {
    event.preventDefault();
    el.dropZone.classList.remove("dragging");
    const [file] = event.dataTransfer.files;
    if (file) {
      state.selectedFile = file;
      el.fileLabel.textContent = file.name;
    }
  });
}

function apiHeaders(json = true) {
  const headers = { "X-API-Key": state.apiKey };
  if (json) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof payload === "object" && payload !== null ? payload.detail : payload;
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return payload;
}

async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/health`);
    const payload = await response.json();
    el.healthText.textContent = `${payload.status} · ${payload.environment}`;
  } catch {
    el.healthText.textContent = "Service unavailable";
  }
}

function handleFileSelection() {
  const [file] = el.fileInput.files;
  state.selectedFile = file || null;
  el.fileLabel.textContent = file ? file.name : "Select PDF, DOCX, TXT, or CSV";
}

async function uploadDocument() {
  if (!state.selectedFile) {
    toast("Select a document first.", "error");
    return;
  }
  const form = new FormData();
  form.append("file", state.selectedFile);
  await withBusy(el.uploadButton, "Indexing", async () => {
    setStatus(`Indexing ${state.selectedFile.name}`);
    const payload = await apiFetch("/documents", {
      method: "POST",
      headers: apiHeaders(false),
      body: form,
    });
    toast(payload.message || "Document indexed.");
    state.selectedFile = null;
    el.fileInput.value = "";
    el.fileLabel.textContent = "Select PDF, DOCX, TXT, or CSV";
    await loadDocuments();
    setStatus("Ready");
  });
}

async function loadDocuments() {
  await withBusy(el.refreshButton, "Refreshing", async () => {
    try {
      const payload = await apiFetch("/documents", { headers: apiHeaders(false) });
      state.documents = payload.documents || [];
      renderDocuments(state.documents);
    } catch (error) {
      renderDocuments([]);
      toast(error.message, "error");
    }
  });
}

async function deleteDocument(documentId) {
  const confirmed = window.confirm("Delete this document and rebuild the index?");
  if (!confirmed) return;
  setStatus("Deleting document and rebuilding index");
  try {
    const payload = await apiFetch(`/documents/${encodeURIComponent(documentId)}`, {
      method: "DELETE",
      headers: apiHeaders(false),
    });
    toast(payload.message || "Document deleted.");
    await loadDocuments();
    setStatus("Ready");
  } catch (error) {
    toast(error.message, "error");
    setStatus("Ready");
  }
}

async function reindexDocuments() {
  await withBusy(el.reindexButton, "Re-indexing", async () => {
    setStatus("Re-indexing stored documents");
    const payload = await apiFetch("/documents/reindex", {
      method: "POST",
      headers: apiHeaders(false),
    });
    toast(`${payload.indexed_documents} documents, ${payload.indexed_chunks} chunks indexed.`);
    await loadDocuments();
    setStatus("Ready");
  });
}

async function askQuestion() {
  const question = el.questionInput.value.trim();
  if (!question) {
    toast("Enter a question.", "error");
    return;
  }
  const topK = Number.parseInt(el.topKInput.value, 10) || 5;
  await withBusy(el.askButton, "Asking", async () => {
    setStatus("Retrieving evidence and generating answer...");
    renderLoadingAnswer();
    const payload = await apiFetch("/query", {
      method: "POST",
      headers: apiHeaders(true),
      body: JSON.stringify({ question, top_k: topK }),
    });
    renderAnswer(payload);
    setStatus("Ready");
  });
}

function renderLoadingAnswer() {
  el.answerBody.textContent = "Retrieving evidence and generating a grounded answer...";
  el.sourceList.innerHTML = '<p class="empty-state">Waiting for retrieved passages.</p>';
  el.citationCount.textContent = "0 citations";
  el.sourceCount.textContent = "0 chunks";
}

function renderError(message) {
  el.answerBody.textContent = message;
  el.sourceList.innerHTML = '<p class="empty-state">No source passages returned.</p>';
  el.citationCount.textContent = "0 citations";
  el.sourceCount.textContent = "0 chunks";
}

function renderDocuments(documents) {
  el.documentCount.textContent = `${documents.length} ${documents.length === 1 ? "doc" : "docs"}`;
  if (!documents.length) {
    el.documentsTable.innerHTML = '<tr><td colspan="5" class="empty-cell">No documents loaded.</td></tr>';
    return;
  }
  el.documentsTable.innerHTML = documents
    .map((doc) => {
      const uploaded = doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleString() : "Unknown";
      return `
        <tr>
          <td>${escapeHtml(doc.filename)}</td>
          <td>${doc.chunk_count ?? 0}</td>
          <td>${escapeHtml(uploaded)}</td>
          <td><div class="doc-id" title="${escapeHtml(doc.document_id)}">${escapeHtml(doc.document_id)}</div></td>
          <td>
            <button class="btn danger" type="button" data-delete="${escapeHtml(doc.document_id)}">
              <i data-lucide="trash-2"></i>
              Delete
            </button>
          </td>
        </tr>
      `;
    })
    .join("");
  el.documentsTable.querySelectorAll("[data-delete]").forEach((button) => {
    button.addEventListener("click", () => deleteDocument(button.dataset.delete));
  });
  hydrateIcons();
}

function renderAnswer(payload) {
  el.answerBody.textContent = payload.answer || "I do not know based on the indexed documents.";
  el.citationCount.textContent = `${(payload.citations || []).length} citations`;
  const sources = payload.sources || [];
  el.sourceCount.textContent = `${sources.length} ${sources.length === 1 ? "chunk" : "chunks"}`;
  if (!sources.length) {
    el.sourceList.innerHTML = '<p class="empty-state">No retrieved passages.</p>';
    return;
  }
  el.sourceList.innerHTML = sources
    .map((source, index) => {
      const score = typeof source.score === "number" ? source.score.toFixed(3) : "n/a";
      const page = source.page !== null && source.page !== undefined ? `<span class="chip">Page ${source.page}</span>` : "";
      const row = source.row !== null && source.row !== undefined ? `<span class="chip">Row ${source.row}</span>` : "";
      return `
        <article class="source-item">
          <div class="source-meta">
            <span class="chip">#${index + 1}</span>
            <span class="chip">${escapeHtml(source.filename || "Unknown")}</span>
            <span class="chip">${escapeHtml(source.chunk_id || "chunk")}</span>
            <span class="chip">Score ${score}</span>
            ${page}
            ${row}
          </div>
          <div class="source-text">${escapeHtml(source.text || "")}</div>
        </article>
      `;
    })
    .join("");
}

function clearAnswer() {
  el.answerBody.innerHTML = '<p class="empty-state">No answer yet.</p>';
  el.sourceList.innerHTML = '<p class="empty-state">Retrieved passages will appear here.</p>';
  el.citationCount.textContent = "0 citations";
  el.sourceCount.textContent = "0 chunks";
}

async function withBusy(button, label, task) {
  const original = button.innerHTML;
  button.disabled = true;
  button.textContent = label;
  try {
    await task();
  } catch (error) {
    toast(error.message, "error");
    if (button === el.askButton) {
      renderError(error.message);
    }
    setStatus("Ready");
  } finally {
    button.disabled = false;
    button.innerHTML = original;
    hydrateIcons();
  }
}

function setStatus(message) {
  el.statusText.textContent = message;
}

function toast(message, type = "info") {
  const node = document.createElement("div");
  node.className = `toast ${type === "error" ? "error" : ""}`;
  node.textContent = message;
  el.toastRegion.appendChild(node);
  window.setTimeout(() => node.remove(), 4200);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

init();