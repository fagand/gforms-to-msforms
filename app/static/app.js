(() => {
  "use strict";

  const MAX_FILES = 20;

  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file-input");
  const fileListWrap = document.getElementById("file-list-wrap");
  const fileListEl = document.getElementById("file-list");
  const convertBtn = document.getElementById("convert-btn");
  const clearBtn = document.getElementById("clear-btn");

  const resultsSection = document.getElementById("results-section");
  const resultsListEl = document.getElementById("results-list");
  const resultsSummaryEl = document.getElementById("results-summary");
  const downloadBtn = document.getElementById("download-btn");
  const startOverBtn = document.getElementById("start-over-btn");
  const uploadSection = document.getElementById("upload-section");

  /** @type {File[]} */
  let selectedFiles = [];
  let currentJobId = null;
  let currentEventSource = null;

  function formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function renderFileList() {
    fileListEl.innerHTML = "";
    fileListWrap.hidden = selectedFiles.length === 0;
    convertBtn.disabled = selectedFiles.length === 0;

    selectedFiles.forEach((file, index) => {
      const li = document.createElement("li");
      li.className = "file-row pending";
      li.innerHTML = `
        <span class="status-icon">✓</span>
        <span class="file-info">
          <span class="file-name">${escapeHtml(file.name)}</span>
          <span class="file-meta">${formatSize(file.size)}</span>
        </span>
        <button class="remove-btn" title="Remove" aria-label="Remove ${escapeHtml(file.name)}">✕</button>
      `;
      li.querySelector(".remove-btn").addEventListener("click", () => {
        selectedFiles.splice(index, 1);
        renderFileList();
      });
      fileListEl.appendChild(li);
    });
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function addFiles(fileList) {
    const incoming = Array.from(fileList);
    for (const file of incoming) {
      if (selectedFiles.length >= MAX_FILES) break;
      const isDuplicate = selectedFiles.some((f) => f.name === file.name && f.size === file.size);
      if (!isDuplicate) selectedFiles.push(file);
    }
    renderFileList();
  }

  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      fileInput.click();
    }
  });
  fileInput.addEventListener("change", () => {
    addFiles(fileInput.files);
    fileInput.value = "";
  });

  ["dragenter", "dragover"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    dropzone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
    })
  );
  dropzone.addEventListener("drop", (e) => {
    if (e.dataTransfer && e.dataTransfer.files) addFiles(e.dataTransfer.files);
  });

  clearBtn.addEventListener("click", () => {
    selectedFiles = [];
    renderFileList();
  });

  function makeResultRow(filename) {
    const li = document.createElement("li");
    li.className = "file-row pending";
    li.dataset.filename = filename;
    li.innerHTML = `
      <span class="status-icon">&hellip;</span>
      <span class="file-info">
        <span class="file-name">${escapeHtml(filename)}</span>
        <span class="file-meta">Waiting&hellip;</span>
      </span>
    `;
    return li;
  }

  function findPendingRow(filename) {
    const rows = resultsListEl.querySelectorAll(`.file-row[data-filename="${CSS.escape(filename)}"]`);
    for (const row of rows) {
      if (row.dataset.done !== "true") return row;
    }
    return null;
  }

  function setRowState(row, state, { meta, warnings } = {}) {
    row.className = `file-row ${state}`;
    const icon = row.querySelector(".status-icon");
    const metaEl = row.querySelector(".file-meta");
    if (state === "processing") {
      icon.innerHTML = "";
      icon.appendChild(Object.assign(document.createElement("span"), { className: "spinner" }));
      metaEl.textContent = meta || "Converting…";
    } else if (state === "success") {
      icon.textContent = "✅";
      metaEl.textContent = meta || "Converted";
      row.dataset.done = "true";
      if (warnings && warnings.length) {
        const ul = document.createElement("ul");
        ul.className = "warning-list";
        warnings.forEach((w) => {
          const li = document.createElement("li");
          li.textContent = w;
          ul.appendChild(li);
        });
        row.appendChild(ul);
      }
    } else if (state === "error") {
      icon.textContent = "❌";
      metaEl.textContent = meta || "Failed";
      row.dataset.done = "true";
    }
  }

  async function startConversion() {
    if (selectedFiles.length === 0) return;

    convertBtn.disabled = true;
    const formData = new FormData();
    selectedFiles.forEach((f) => formData.append("files", f, f.name));

    uploadSection.hidden = true;
    resultsSection.hidden = false;
    resultsListEl.innerHTML = "";
    resultsSummaryEl.textContent = "";
    downloadBtn.hidden = true;

    selectedFiles.forEach((f) => resultsListEl.appendChild(makeResultRow(f.name)));

    let response;
    try {
      response = await fetch("/api/jobs", { method: "POST", body: formData });
    } catch (err) {
      resultsSummaryEl.textContent = "Upload failed — check your connection and try again.";
      return;
    }

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      resultsSummaryEl.textContent = body.detail || "Upload failed.";
      return;
    }

    const body = await response.json();
    currentJobId = body.job_id;

    for (const rejected of body.rejected || []) {
      const row = findPendingRow(rejected.name);
      if (row) setRowState(row, "error", { meta: rejected.reason });
    }

    listenToJob(currentJobId);
  }

  function listenToJob(jobId) {
    if (currentEventSource) currentEventSource.close();
    const es = new EventSource(`/api/jobs/${jobId}/stream`);
    currentEventSource = es;

    es.addEventListener("start", (e) => {
      const data = JSON.parse(e.data);
      const row = findPendingRow(data.filename);
      if (row) setRowState(row, "processing");
    });

    es.addEventListener("result", (e) => {
      const data = JSON.parse(e.data);
      const row = findPendingRow(data.filename);
      if (!row) return;
      if (data.success) {
        setRowState(row, "success", { meta: data.docx_name, warnings: data.warnings });
      } else {
        setRowState(row, "error", { meta: data.error });
      }
    });

    es.addEventListener("done", (e) => {
      const data = JSON.parse(e.data);
      const parts = [];
      if (data.success_count) parts.push(`${data.success_count} converted successfully`);
      if (data.failure_count) parts.push(`${data.failure_count} failed`);
      resultsSummaryEl.textContent = parts.join(" — ") || "No files were processed.";
      if (data.download_url) {
        downloadBtn.hidden = false;
        downloadBtn.onclick = () => {
          window.location.href = data.download_url;
          setTimeout(() => {
            fetch(`/api/jobs/${jobId}`, { method: "DELETE" }).catch(() => {});
          }, 3000);
        };
      }
      es.close();
      currentEventSource = null;
    });

    es.onerror = () => {
      resultsSummaryEl.textContent = "Connection to the server was lost. Please try again.";
      es.close();
      currentEventSource = null;
    };
  }

  convertBtn.addEventListener("click", startConversion);

  startOverBtn.addEventListener("click", () => {
    if (currentEventSource) currentEventSource.close();
    if (currentJobId) fetch(`/api/jobs/${currentJobId}`, { method: "DELETE" }).catch(() => {});
    currentJobId = null;
    selectedFiles = [];
    renderFileList();
    uploadSection.hidden = false;
    resultsSection.hidden = true;
  });
})();
