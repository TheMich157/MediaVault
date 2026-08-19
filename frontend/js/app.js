/**
 * MediaVault • Instagram & TikTok Downloader Studio
 * Enhanced Frontend Application Controller with Multi-Job & Interactive Terminal Shell
 */

document.addEventListener("DOMContentLoaded", () => {
  // App State
  const state = {
    activeTab: "instagram",
    currentJobId: null,
    activeJobs: new Map(), // Map<job_id, jobData>
    selectedUser: null,
    galleryUsers: [],
    currentGalleryItems: [],
    currentGalleryFilter: "all",
    gallerySearchQuery: "",
    gallerySortOrder: "date-desc",
    userSearchQuery: "",
    batchMode: false,
    selectedFilenames: new Set(),
    currentModalIndex: 0,
    filteredModalItems: [],
    sessionStatus: { has_instagram_session: false },
    drawerCollapsed: false,
    cmdHistory: [],
    cmdHistoryIndex: -1,
  };

  // DOM Elements
  const navBtns = document.querySelectorAll(".nav-btn");
  const tabPanels = document.querySelectorAll(".tab-panel");
  const galleryTotalBadge = document.getElementById("gallery-total-badge");
  const batchActiveBadge = document.getElementById("batch-active-badge");
  const sessionStatusDot = document.getElementById("session-status-dot");
  const btnOpenFinder = document.getElementById("btn-open-finder");
  const btnToggleLogDrawer = document.getElementById("btn-toggle-log-drawer");
  const headerActiveJobDot = document.getElementById("header-active-job-dot");
  const headerStoragePill = document.getElementById("header-storage-pill");
  const headerStorageText = document.getElementById("header-storage-text");
  const toastContainer = document.getElementById("toast-container");

  // Instagram Elements
  const formInstagram = document.getElementById("form-instagram");
  const inputIgUsername = document.getElementById("ig-username");
  const btnInspectIg = document.getElementById("btn-inspect-ig");
  const igProfilePreview = document.getElementById("ig-profile-preview");
  const igPreviewAvatar = document.getElementById("ig-preview-avatar");
  const igPreviewName = document.getElementById("ig-preview-name");
  const igPreviewBio = document.getElementById("ig-preview-bio");
  const igPreviewPosts = document.getElementById("ig-preview-posts");
  const igPreviewFollowers = document.getElementById("ig-preview-followers");
  const igPreviewFollowing = document.getElementById("ig-preview-following");
  const igPreviewVerified = document.getElementById("ig-preview-verified");
  const igPreviewPrivate = document.getElementById("ig-preview-private");
  const igSessionTag = document.getElementById("ig-session-tag");
  const igSessionTagText = document.getElementById("ig-session-tag-text");

  // TikTok Elements
  const formTikTok = document.getElementById("form-tiktok");
  const inputTtUsername = document.getElementById("tt-username");
  const btnInspectTt = document.getElementById("btn-inspect-tt");
  const ttProfilePreview = document.getElementById("tt-profile-preview");
  const ttPreviewAvatar = document.getElementById("tt-preview-avatar");
  const ttPreviewName = document.getElementById("tt-preview-name");
  const ttPreviewBio = document.getElementById("tt-preview-bio");

  // Batch Hub Elements
  const formBatch = document.getElementById("form-batch");
  const batchTargetsInput = document.getElementById("batch-targets-input");
  const btnImportTargetsFile = document.getElementById("btn-import-targets-file");
  const batchFileInput = document.getElementById("batch-file-input");
  const btnSampleBatchIg = document.getElementById("btn-sample-batch-ig");
  const btnSampleBatchTt = document.getElementById("btn-sample-batch-tt");
  const btnSampleBatchMix = document.getElementById("btn-sample-batch-mix");

  // Direct URL Elements
  const formDirect = document.getElementById("form-direct");
  const directUrlsInput = document.getElementById("direct-urls");

  // Session & Cookie Elements
  const sessionBadge = document.getElementById("session-badge");
  const sessionBadgeText = document.getElementById("session-badge-text");
  const sessionDescText = document.getElementById("session-desc-text");
  const btnClearSession = document.getElementById("btn-clear-session");
  const btnVerifySession = document.getElementById("btn-verify-session");
  const rawCookieInput = document.getElementById("raw-cookie-input");
  const btnSaveCookieText = document.getElementById("btn-save-cookie-text");
  const btnCopyJsSnippet = document.getElementById("btn-copy-js-snippet");
  const browserButtons = document.querySelectorAll(".btn-browser");
  const btnScanAllBrowsers = document.getElementById("btn-scan-all-browsers");
  const cookieUploadDropzone = document.getElementById("cookie-upload-dropzone");
  const cookieFileInput = document.getElementById("cookie-file-input");

  // Gallery Elements
  const galleryUserList = document.getElementById("gallery-user-list");
  const galleryUserSearch = document.getElementById("gallery-user-search");
  const btnRefreshGallery = document.getElementById("btn-refresh-gallery");
  const galleryActiveUsername = document.getElementById("gallery-active-username");
  const galleryActiveMeta = document.getElementById("gallery-active-meta");
  const galleryUserAvatar = document.getElementById("gallery-user-avatar");
  const galleryActionsBar = document.getElementById("gallery-actions-bar");
  const galleryToolbar = document.getElementById("gallery-toolbar");
  const galleryMediaSearch = document.getElementById("gallery-media-search");
  const gallerySortSelect = document.getElementById("gallery-sort-select");
  const galleryMediaGrid = document.getElementById("gallery-media-grid");
  const btnGalleryFinder = document.getElementById("btn-gallery-finder");
  const btnGalleryZip = document.getElementById("btn-gallery-zip");
  const btnGalleryDelete = document.getElementById("btn-gallery-delete");
  const btnToggleBatchMode = document.getElementById("btn-toggle-batch-mode");
  const batchActionBar = document.getElementById("batch-action-bar");
  const batchSelectedCount = document.getElementById("batch-selected-count");
  const btnBatchSelectAll = document.getElementById("btn-batch-select-all");
  const btnBatchDeselect = document.getElementById("btn-batch-deselect");
  const btnBatchZip = document.getElementById("btn-batch-zip");
  const btnBatchDelete = document.getElementById("btn-batch-delete");
  const filterBtns = document.querySelectorAll(".btn-filter");

  // Drawer / Console & Interactive Terminal Elements
  const progressDrawer = document.getElementById("progress-drawer");
  const drawerToggleHeader = document.getElementById("drawer-toggle-header");
  const drawerChevronIcon = document.getElementById("drawer-chevron-icon");
  const drawerTitle = document.getElementById("drawer-title");
  const drawerSubtitle = document.getElementById("drawer-subtitle");
  const drawerPulse = document.getElementById("drawer-pulse");
  const btnCancelJob = document.getElementById("btn-cancel-job");
  const btnCancelAllJobs = document.getElementById("btn-cancel-all-jobs");
  const btnClearLogs = document.getElementById("btn-clear-logs");
  const progressCurrentFilename = document.getElementById("progress-current-filename");
  const progressStatsText = document.getElementById("progress-stats-text");
  const progressBarFill = document.getElementById("progress-bar-fill");
  const terminalLogsContainer = document.getElementById("terminal-logs-container");
  const jobsStripContainer = document.getElementById("jobs-strip-container");
  const jobsStripList = document.getElementById("jobs-strip-list");
  const jobsStripCount = document.getElementById("jobs-strip-count");
  const terminalCliForm = document.getElementById("terminal-cli-form");
  const terminalCmdInput = document.getElementById("terminal-cmd-input");

  // Modal / Lightbox Elements
  const mediaModal = document.getElementById("media-modal");
  const btnCloseModal = document.getElementById("btn-close-modal");
  const btnLightboxPrev = document.getElementById("btn-lightbox-prev");
  const btnLightboxNext = document.getElementById("btn-lightbox-next");
  const modalIndexCounter = document.getElementById("modal-index-counter");
  const modalMediaDisplay = document.getElementById("modal-media-display");
  const modalFilename = document.getElementById("modal-filename");
  const modalFilesize = document.getElementById("modal-filesize");
  const modalFiledate = document.getElementById("modal-filedate");
  const modalVideoControlsRow = document.getElementById("modal-video-controls-row");
  const modalPlaybackSpeed = document.getElementById("modal-playback-speed");
  const modalCaptionContainer = document.getElementById("modal-caption-container");
  const modalCaptionText = document.getElementById("modal-caption-text");
  const modalDownloadLink = document.getElementById("modal-download-link");
  const modalCopyPathBtn = document.getElementById("modal-copy-path-btn");
  const modalFinderBtn = document.getElementById("modal-finder-btn");
  const modalDeleteBtn = document.getElementById("modal-delete-btn");

  // -------------------------------------------------------------
  // 0. Toast Notification System
  // -------------------------------------------------------------
  function showToast(type, message, duration = 3500) {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let iconName = "info";
    if (type === "success") iconName = "check-circle-2";
    else if (type === "error") iconName = "alert-circle";
    else if (type === "warning") iconName = "alert-triangle";

    toast.innerHTML = `
      <i data-lucide="${iconName}"></i>
      <span>${escapeHtml(message)}</span>
    `;

    toastContainer.appendChild(toast);
    lucide.createIcons();

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  // -------------------------------------------------------------
  // 1. Navigation & Tabs & Storage
  // -------------------------------------------------------------
  function switchTab(targetTab) {
    state.activeTab = targetTab;
    navBtns.forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.tab === targetTab);
    });
    tabPanels.forEach((panel) => {
      panel.classList.toggle("active", panel.id === `panel-${targetTab}`);
    });

    if (targetTab === "gallery") {
      loadGalleryOverview();
    } else if (targetTab === "session") {
      checkSessionStatus();
    }
    updateStorageStats();
  }

  navBtns.forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  document.querySelectorAll(".tab-link").forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      switchTab(link.dataset.tab);
    });
  });

  async function updateStorageStats() {
    try {
      const res = await fetch("/api/system/storage");
      const data = await res.json();
      if (headerStorageText) {
        headerStorageText.textContent = `${data.total_size_human} (${data.total_files_count} files)`;
      }
      if (headerStoragePill) {
        headerStoragePill.title = `Total Storage: ${data.total_size_human}\nFiles: ${data.total_files_count}\nUsers: ${data.total_users_count}\nFree Disk: ${data.free_disk_space_human}`;
      }
    } catch (e) {
      console.warn("Storage update notice:", e);
    }
  }

  // -------------------------------------------------------------
  // 2. Logging & Interactive Terminal Execution
  // -------------------------------------------------------------
  function appendLog(level, message, time = null) {
    const logTime = time || new Date().toLocaleTimeString();
    const line = document.createElement("div");
    line.className = `log-line log-${level}`;
    line.innerHTML = `
      <span class="log-time">[${logTime}]</span>
      <span class="log-msg">${escapeHtml(message)}</span>
    `;
    terminalLogsContainer.appendChild(line);
    terminalLogsContainer.scrollTop = terminalLogsContainer.scrollHeight;
  }

  function appendTerminalEcho(cmdText) {
    const line = document.createElement("div");
    line.className = "log-line log-info";
    line.innerHTML = `
      <span class="log-time" style="color:var(--color-success)">mediavault &gt;</span>
      <span class="terminal-cmd-echo">${escapeHtml(cmdText)}</span>
    `;
    terminalLogsContainer.appendChild(line);
    terminalLogsContainer.scrollTop = terminalLogsContainer.scrollHeight;
  }

  function appendTerminalResult(output, isError = false) {
    if (!output) return;
    const line = document.createElement("div");
    line.className = `log-line ${isError ? "log-error" : "log-info"}`;
    line.innerHTML = `<span class="terminal-cmd-result">${escapeHtml(output)}</span>`;
    terminalLogsContainer.appendChild(line);
    terminalLogsContainer.scrollTop = terminalLogsContainer.scrollHeight;
  }

  function clearLogs() {
    terminalLogsContainer.innerHTML = "";
  }

  btnClearLogs.addEventListener("click", (e) => {
    e.stopPropagation();
    clearLogs();
    appendLog("info", "Terminal log cleared.");
  });

  function toggleDrawer(forceOpen = null) {
    if (forceOpen === true) {
      progressDrawer.classList.remove("collapsed");
      state.drawerCollapsed = false;
    } else if (forceOpen === false) {
      progressDrawer.classList.add("collapsed");
      state.drawerCollapsed = true;
    } else {
      progressDrawer.classList.toggle("collapsed");
      state.drawerCollapsed = progressDrawer.classList.contains("collapsed");
    }
    drawerChevronIcon.setAttribute(
      "data-lucide",
      state.drawerCollapsed ? "chevron-up" : "chevron-down"
    );
    lucide.createIcons();
    if (!state.drawerCollapsed) {
      setTimeout(() => terminalCmdInput?.focus(), 100);
    }
  }

  drawerToggleHeader.addEventListener("click", () => toggleDrawer());
  btnToggleLogDrawer.addEventListener("click", () => toggleDrawer());

  // Interactive Terminal Form Submission
  if (terminalCliForm) {
    terminalCliForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const rawCmd = terminalCmdInput.value.trim();
      if (!rawCmd) return;

      // Add to command history
      state.cmdHistory.push(rawCmd);
      state.cmdHistoryIndex = state.cmdHistory.length;
      terminalCmdInput.value = "";

      // Echo command into terminal window
      appendTerminalEcho(rawCmd);

      // Execute via backend command engine
      try {
        const res = await fetch("/api/terminal/execute", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command: rawCmd }),
        });
        const data = await res.json();

        if (data.action === "clear_screen") {
          clearLogs();
          return;
        }

        if (data.output) {
          appendTerminalResult(data.output, !data.success);
        }

        if (data.action === "download_zip" && data.data?.zip_url) {
          window.location.href = data.data.zip_url;
        }

        if (data.action === "refresh_jobs") {
          loadJobsStatus();
        }

      } catch (err) {
        appendTerminalResult(`Error executing command: ${err}`, true);
      }
    });

    // History navigation with Up/Down arrow keys
    terminalCmdInput.addEventListener("keydown", (e) => {
      if (e.key === "ArrowUp") {
        if (state.cmdHistory.length > 0 && state.cmdHistoryIndex > 0) {
          state.cmdHistoryIndex--;
          terminalCmdInput.value = state.cmdHistory[state.cmdHistoryIndex];
          e.preventDefault();
        }
      } else if (e.key === "ArrowDown") {
        if (state.cmdHistoryIndex < state.cmdHistory.length - 1) {
          state.cmdHistoryIndex++;
          terminalCmdInput.value = state.cmdHistory[state.cmdHistoryIndex];
          e.preventDefault();
        } else {
          state.cmdHistoryIndex = state.cmdHistory.length;
          terminalCmdInput.value = "";
        }
      }
    });

    // Quick action shortcut buttons
    document.querySelectorAll(".term-quick-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const cmd = btn.getAttribute("data-cmd");
        if (cmd && terminalCmdInput) {
          terminalCmdInput.value = cmd;
          terminalCliForm.dispatchEvent(new Event("submit"));
        }
      });
    });
  }

  // -------------------------------------------------------------
  // 3. Multi-Job Tracking & Real-Time SSE Stream
  // -------------------------------------------------------------
  function updateJobsStrip() {
    const runningJobs = Array.from(state.activeJobs.values()).filter(
      (j) => j.status === "running" || j.status === "queued"
    );

    const count = runningJobs.length;
    if (count > 0) {
      jobsStripContainer.style.display = "block";
      jobsStripCount.textContent = `${count} active`;
      btnCancelAllJobs.style.display = "inline-flex";
      btnCancelJob.style.display = "inline-flex";
      drawerPulse.classList.add("active");
      headerActiveJobDot.classList.remove("hidden");
      if (batchActiveBadge) {
        batchActiveBadge.style.display = "inline-block";
        batchActiveBadge.textContent = count.toString();
      }

      if (count === 1) {
        drawerTitle.textContent = `Downloading ${runningJobs[0].target}`;
        drawerSubtitle.textContent = `Platform: ${runningJobs[0].platform.toUpperCase()}`;
      } else {
        drawerTitle.textContent = `Active Download Batch (${count} jobs)`;
        drawerSubtitle.textContent = `${count} active downloads running in queue`;
      }
    } else {
      jobsStripContainer.style.display = "none";
      btnCancelAllJobs.style.display = "none";
      btnCancelJob.style.display = "none";
      drawerPulse.classList.remove("active");
      headerActiveJobDot.classList.add("hidden");
      if (batchActiveBadge) {
        batchActiveBadge.style.display = "none";
      }

      if (state.currentJobId && state.activeJobs.has(state.currentJobId)) {
        const lastJob = state.activeJobs.get(state.currentJobId);
        if (lastJob.status === "completed") {
          drawerTitle.textContent = `Completed ${lastJob.target}`;
          drawerSubtitle.textContent = `Platform: ${lastJob.platform.toUpperCase()} • ${lastJob.downloaded_items || 0} files saved`;
        } else if (lastJob.status === "failed") {
          drawerTitle.textContent = `Download Failed`;
          drawerSubtitle.textContent = `${lastJob.target} • ${lastJob.error_message || "Error"}`;
        } else if (lastJob.status === "cancelled") {
          drawerTitle.textContent = `Download Cancelled`;
          drawerSubtitle.textContent = `${lastJob.target}`;
        }
      }
    }

    // Render mini cards for running jobs
    jobsStripList.innerHTML = "";
    runningJobs.forEach((job) => {
      const card = document.createElement("div");
      card.className = "jobs-strip-item running";

      let subInfo = "";
      if (job.status === "queued") {
        subInfo = "<span>Queued</span><span>Waiting...</span>";
      } else if (!job.total_items && !job.downloaded_items) {
        subInfo = "<span>Scanning profile...</span><span>0%</span>";
      } else if (!job.total_items && job.downloaded_items > 0) {
        subInfo = `<span>${job.downloaded_items} saved</span><span>${job.progress_percent || 0}%</span>`;
      } else {
        subInfo = `<span>${job.downloaded_items || 0}/${job.total_items}</span><span>${job.progress_percent || 0}%</span>`;
      }

      card.innerHTML = `
        <div class="jobs-strip-item-title">
          <span>${escapeHtml(job.target)}</span>
          <span style="font-size:0.7rem; color:var(--accent-primary); text-transform:uppercase;">${job.platform}</span>
        </div>
        <div class="jobs-strip-item-sub">
          ${subInfo}
        </div>
        <div class="jobs-strip-mini-bar">
          <div class="jobs-strip-mini-bar-fill" style="width: ${Math.min(job.progress_percent || 0, 100)}%"></div>
        </div>
      `;
      jobsStripList.appendChild(card);
    });
  }

  async function loadJobsStatus() {
    try {
      const res = await fetch("/api/jobs");
      const jobs = await res.json();
      state.activeJobs.clear();
      Object.entries(jobs).forEach(([jid, jdata]) => {
        state.activeJobs.set(jid, jdata);
      });
      updateJobsStrip();
    } catch (e) {
      console.warn("Could not fetch jobs:", e);
    }
  }

  function initSSE() {
    const eventSource = new EventSource("/api/events");

    eventSource.addEventListener("ping", () => {
      console.log("SSE connected");
    });

    eventSource.addEventListener("job_created", (e) => {
      const data = JSON.parse(e.data);
      state.currentJobId = data.job_id;
      state.activeJobs.set(data.job_id, data);
      toggleDrawer(true);
      updateJobsStrip();
      showToast("info", `Queued download for ${data.target}`);
    });

    eventSource.addEventListener("job_started", (e) => {
      const data = JSON.parse(e.data);
      state.activeJobs.set(data.job_id, data);
      progressCurrentFilename.textContent = `Scanning ${data.target}...`;
      progressStatsText.textContent = "Initializing...";
      progressBarFill.style.width = "0%";
      updateJobsStrip();
    });

    eventSource.addEventListener("job_progress", (e) => {
      const data = JSON.parse(e.data);
      state.activeJobs.set(data.job_id, data);
      progressCurrentFilename.textContent = data.current_item_name || `Downloading ${data.target}...`;
      
      if (!data.total_items && !data.downloaded_items) {
        progressStatsText.textContent = data.status === "queued" ? "Queued" : "Scanning profile...";
      } else if (!data.total_items && data.downloaded_items > 0) {
        progressStatsText.textContent = `${data.downloaded_items} saved (${data.progress_percent}%)`;
      } else {
        progressStatsText.textContent = `${data.downloaded_items} / ${data.total_items} (${data.progress_percent}%)`;
      }
      progressBarFill.style.width = `${Math.min(data.progress_percent, 100)}%`;
      updateJobsStrip();
    });

    eventSource.addEventListener("job_log", (e) => {
      const data = JSON.parse(e.data);
      appendLog(data.log.level, data.log.message, data.log.timestamp);
    });

    eventSource.addEventListener("job_completed", (e) => {
      const data = JSON.parse(e.data);
      state.activeJobs.set(data.job_id, data);
      progressCurrentFilename.textContent = `Saved ${data.downloaded_items} files for ${data.target}`;
      progressStatsText.textContent = `${data.downloaded_items} / ${data.total_items || data.downloaded_items} (100%)`;
      progressBarFill.style.width = "100%";
      updateJobsStrip();
      appendLog("success", `Job [${data.job_id}] for ${data.target} completed! (${data.downloaded_items} files saved)`);
      showToast("success", `Finished! Saved ${data.downloaded_items} files for ${data.target}`);
      loadGalleryOverview();
      updateStorageStats();
    });

    eventSource.addEventListener("job_failed", (e) => {
      const data = JSON.parse(e.data);
      state.activeJobs.set(data.job_id, data);
      progressCurrentFilename.textContent = `Download failed for ${data.target}`;
      progressStatsText.textContent = "Failed";
      updateJobsStrip();
      appendLog("error", `Job [${data.job_id}] failed: ${data.error_message}`);
      showToast("error", `Download failed for ${data.target}: ${data.error_message}`);
    });

    eventSource.addEventListener("job_cancelled", (e) => {
      const data = JSON.parse(e.data);
      state.activeJobs.set(data.job_id, data);
      progressCurrentFilename.textContent = `Download stopped for ${data.target}`;
      progressStatsText.textContent = "Cancelled";
      updateJobsStrip();
      appendLog("warning", `Job [${data.job_id}] was stopped.`);
    });

    eventSource.onerror = (err) => {
      console.warn("SSE reconnecting in 3s...", err);
      eventSource.close();
      setTimeout(initSSE, 3000);
    };
  }

  btnCancelJob.addEventListener("click", async () => {
    if (!state.currentJobId) return;
    try {
      await fetch(`/api/jobs/${state.currentJobId}/cancel`, { method: "POST" });
      appendLog("warning", "Cancelling download job...");
    } catch (e) {
      appendLog("error", `Cancel request failed: ${e}`);
    }
  });

  btnCancelAllJobs.addEventListener("click", async () => {
    if (!confirm("Cancel all currently running downloads?")) return;
    try {
      const res = await fetch("/api/jobs/cancel-all", { method: "POST" });
      const data = await res.json();
      showToast("info", data.message || "Cancelled all jobs.");
      appendLog("warning", "Cancelled all active jobs.");
      loadJobsStatus();
    } catch (e) {
      showToast("error", `Failed to cancel jobs: ${e}`);
    }
  });

  // -------------------------------------------------------------
  // 4. Quick Presets
  // -------------------------------------------------------------
  document.querySelectorAll(".btn-preset").forEach((btn) => {
    btn.addEventListener("click", () => {
      const p = btn.dataset.preset;
      if (p === "ig-top20") {
        document.getElementById("ig-limit").value = "20";
        document.getElementById("ig-target-posts").checked = true;
        document.getElementById("ig-target-reels").checked = true;
        document.getElementById("ig-target-stories").checked = false;
        document.getElementById("ig-target-highlights").checked = false;
        document.getElementById("ig-target-tagged").checked = false;
        document.getElementById("ig-media-type").value = "all";
        showToast("info", "Preset: Top 20 Posts");
      } else if (p === "ig-reels") {
        document.getElementById("ig-target-posts").checked = false;
        document.getElementById("ig-target-reels").checked = true;
        document.getElementById("ig-target-stories").checked = false;
        document.getElementById("ig-target-highlights").checked = false;
        document.getElementById("ig-media-type").value = "videos";
        showToast("info", "Preset: Reels Only");
      } else if (p === "ig-stories") {
        document.getElementById("ig-target-posts").checked = false;
        document.getElementById("ig-target-reels").checked = false;
        document.getElementById("ig-target-stories").checked = true;
        document.getElementById("ig-target-highlights").checked = true;
        showToast("info", "Preset: Stories & Highlights");
      } else if (p === "ig-full") {
        document.getElementById("ig-limit").value = "all";
        document.getElementById("ig-target-posts").checked = true;
        document.getElementById("ig-target-reels").checked = true;
        document.getElementById("ig-target-stories").checked = true;
        document.getElementById("ig-target-highlights").checked = true;
        document.getElementById("ig-target-tagged").checked = true;
        document.getElementById("ig-media-type").value = "all";
        showToast("info", "Preset: Full Profile Archive");
      } else if (p === "tt-top30") {
        document.getElementById("tt-limit").value = "30";
        document.getElementById("tt-target-videos").checked = true;
        document.getElementById("tt-target-slideshows").checked = true;
        document.getElementById("tt-target-audio").checked = false;
        showToast("info", "Preset: Top 30 Videos");
      } else if (p === "tt-audio") {
        document.getElementById("tt-target-videos").checked = false;
        document.getElementById("tt-target-slideshows").checked = false;
        document.getElementById("tt-target-audio").checked = true;
        showToast("info", "Preset: Audio Soundtracks Only");
      } else if (p === "tt-full") {
        document.getElementById("tt-limit").value = "all";
        document.getElementById("tt-target-videos").checked = true;
        document.getElementById("tt-target-slideshows").checked = true;
        document.getElementById("tt-target-audio").checked = false;
        showToast("info", "Preset: Full Creator Archive");
      }
    });
  });

  // Batch Hub Samples
  btnSampleBatchIg?.addEventListener("click", () => {
    batchTargetsInput.value = "@zuck\n@instagram\n@natgeo";
    showToast("info", "Loaded sample Instagram accounts");
  });

  btnSampleBatchTt?.addEventListener("click", () => {
    batchTargetsInput.value = "@khaby.lame\n@tiktok\n@mrbeast";
    showToast("info", "Loaded sample TikTok creators");
  });

  btnSampleBatchMix?.addEventListener("click", () => {
    batchTargetsInput.value = "ig:zuck\ntt:khaby.lame\nhttps://www.instagram.com/leomessi/\ntiktok.com/@tiktok";
    showToast("info", "Loaded mixed Instagram + TikTok bundle");
  });

  // Batch Targets File Reader
  btnImportTargetsFile?.addEventListener("click", () => batchFileInput.click());
  batchFileInput?.addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      batchTargetsInput.value = ev.target.result;
      showToast("success", `Loaded targets list from ${file.name}`);
    };
    reader.readAsText(file);
  });

  // -------------------------------------------------------------
  // 5. Instagram Tab Submission (Single or Multi)
  // -------------------------------------------------------------
  btnInspectIg.addEventListener("click", async () => {
    const raw = inputIgUsername.value.trim();
    if (!raw) return;
    const firstTarget = raw.split(/[\s,]+/)[0];

    btnInspectIg.disabled = true;
    btnInspectIg.innerHTML = `<span>Inspecting...</span>`;

    try {
      const res = await fetch(`/api/preview/instagram/${encodeURIComponent(firstTarget)}`);
      const data = await res.json();
      if (data.success) {
        igProfilePreview.classList.remove("hidden");
        const defaultIgAvatar = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%236366f1'%3E%3Cpath d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z'/%3E%3C/svg%3E";
        igPreviewAvatar.onerror = function () {
          this.onerror = null;
          this.src = defaultIgAvatar;
        };
        igPreviewAvatar.src = data.profile_pic_url || defaultIgAvatar;
        igPreviewName.textContent = data.full_name ? `${data.full_name} (@${data.username})` : `@${data.username}`;
        igPreviewBio.textContent = data.biography || "(No biography)";
        igPreviewPosts.textContent = data.mediacount?.toLocaleString() || "0";
        igPreviewFollowers.textContent = data.followers?.toLocaleString() || "0";
        igPreviewFollowing.textContent = data.followees?.toLocaleString() || "0";
        igPreviewVerified.classList.toggle("hidden", !data.is_verified);
        igPreviewPrivate.classList.toggle("hidden", !data.is_private);
        showToast("success", `Profile inspected: @${data.username}`);
      } else {
        showToast("warning", data.error || "Could not inspect profile.");
      }
    } catch (e) {
      showToast("error", `Inspect failed: ${e}`);
    } finally {
      btnInspectIg.disabled = false;
      btnInspectIg.innerHTML = `<i data-lucide="search"></i><span>Inspect</span>`;
      lucide.createIcons();
    }
  });

  formInstagram.addEventListener("submit", async (e) => {
    e.preventDefault();
    const raw = inputIgUsername.value.trim();
    if (!raw) return;

    const limitVal = document.getElementById("ig-limit").value;
    const payload = {
      username_or_url: raw,
      download_posts: document.getElementById("ig-target-posts").checked,
      download_reels: document.getElementById("ig-target-reels").checked,
      download_stories: document.getElementById("ig-target-stories").checked,
      download_highlights: document.getElementById("ig-target-highlights").checked,
      download_tagged: document.getElementById("ig-target-tagged").checked,
      download_profile_pic: true,
      media_type: document.getElementById("ig-media-type").value,
      limit: limitVal === "all" ? null : parseInt(limitVal, 10),
      custom_subfolder: document.getElementById("ig-custom-folder").value.trim() || null,
      date_from: document.getElementById("ig-date-from").value || null,
      date_to: document.getElementById("ig-date-to").value || null,
      save_captions: document.getElementById("ig-save-captions").checked,
      save_metadata: document.getElementById("ig-save-meta").checked,
    };

    try {
      const res = await fetch("/api/download/instagram", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        showToast("success", data.message || "Download job(s) queued.");
        loadJobsStatus();
      } else {
        showToast("error", data.detail || "Failed to start download.");
      }
    } catch (err) {
      showToast("error", `Download trigger error: ${err}`);
    }
  });

  // -------------------------------------------------------------
  // 6. TikTok Tab Submission (Single or Multi)
  // -------------------------------------------------------------
  btnInspectTt.addEventListener("click", async () => {
    const raw = inputTtUsername.value.trim();
    if (!raw) return;
    const firstTarget = raw.split(/[\s,]+/)[0];

    btnInspectTt.disabled = true;
    btnInspectTt.innerHTML = `<span>Inspecting...</span>`;

    try {
      const res = await fetch(`/api/preview/tiktok/${encodeURIComponent(firstTarget)}`);
      const data = await res.json();
      if (data.success) {
        ttProfilePreview.classList.remove("hidden");
        const defaultTtAvatar = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%2300f2fe'%3E%3Cpath d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z'/%3E%3C/svg%3E";
        ttPreviewAvatar.onerror = function () {
          this.onerror = null;
          this.src = defaultTtAvatar;
        };
        ttPreviewAvatar.src = data.avatar_url || defaultTtAvatar;
        ttPreviewAvatar.classList.remove("hidden");
        ttPreviewName.textContent = data.display_name ? `${data.display_name} (@${data.username})` : `@${data.username}`;
        ttPreviewBio.textContent = data.description || "TikTok Creator Channel";
        showToast("success", `Profile inspected: @${data.username}`);
      } else {
        showToast("warning", data.error || "Could not inspect TikTok profile.");
      }
    } catch (e) {
      showToast("error", `TikTok inspect failed: ${e}`);
    } finally {
      btnInspectTt.disabled = false;
      btnInspectTt.innerHTML = `<i data-lucide="search"></i><span>Inspect</span>`;
      lucide.createIcons();
    }
  });

  formTikTok.addEventListener("submit", async (e) => {
    e.preventDefault();
    const raw = inputTtUsername.value.trim();
    if (!raw) return;

    const limitVal = document.getElementById("tt-limit").value;
    const payload = {
      username_or_url: raw,
      download_videos: document.getElementById("tt-target-videos").checked,
      download_slideshows: document.getElementById("tt-target-slideshows").checked,
      download_audio: document.getElementById("tt-target-audio").checked,
      download_profile_pic: true,
      limit: limitVal === "all" ? null : parseInt(limitVal, 10),
      custom_subfolder: document.getElementById("tt-custom-folder").value.trim() || null,
      save_metadata: document.getElementById("tt-target-metadata").checked,
    };

    try {
      const res = await fetch("/api/download/tiktok", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        showToast("success", data.message || "TikTok download job(s) queued.");
        loadJobsStatus();
      } else {
        showToast("error", data.detail || "Failed to start TikTok download.");
      }
    } catch (err) {
      showToast("error", `TikTok download trigger error: ${err}`);
    }
  });

  // -------------------------------------------------------------
  // 7. Batch Hub Submission
  // -------------------------------------------------------------
  formBatch?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const raw = batchTargetsInput.value.trim();
    if (!raw) return;

    const targets = raw
      .split(/[\n,]+/)
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    if (targets.length === 0) return;

    const limitVal = document.getElementById("batch-limit").value;
    const defaultPlat = document.getElementById("batch-default-platform").value;
    const concurrency = parseInt(document.getElementById("batch-concurrency").value, 10) || 3;

    const payload = {
      targets: targets,
      default_platform: defaultPlat,
      limit: limitVal === "all" ? null : parseInt(limitVal, 10),
      download_posts: true,
      download_reels: document.getElementById("batch-download-reels").checked,
      download_videos: true,
      download_slideshows: true,
      save_captions: document.getElementById("batch-save-captions").checked,
      save_metadata: document.getElementById("batch-save-meta").checked,
      concurrency: concurrency,
    };

    try {
      showToast("info", `Queuing batch of ${targets.length} profiles...`);
      const res = await fetch("/api/download/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        showToast("success", `Launched ${data.count} concurrent download tasks!`);
        loadJobsStatus();
        toggleDrawer(true);
      } else {
        showToast("error", data.detail || "Failed to start batch.");
      }
    } catch (err) {
      showToast("error", `Batch trigger error: ${err}`);
    }
  });

  // -------------------------------------------------------------
  // 8. Direct URL Batch Downloader
  // -------------------------------------------------------------
  formDirect.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = directUrlsInput.value.trim();
    if (!text) return;

    const urls = text.split(/[\n\s]+/).map((u) => u.trim()).filter((u) => u.length > 0);
    if (!urls.length) return;

    const payload = {
      urls: urls,
      save_metadata: document.getElementById("direct-save-meta").checked,
    };

    try {
      const res = await fetch("/api/download/direct", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (data.success) {
        showToast("success", `Direct download queued for ${urls.length} items.`);
        loadJobsStatus();
      } else {
        showToast("error", data.detail || "Failed to start direct download.");
      }
    } catch (err) {
      showToast("error", `Direct download trigger error: ${err}`);
    }
  });

  // -------------------------------------------------------------
  // 9. Session & Cookie Manager
  // -------------------------------------------------------------
  async function checkSessionStatus() {
    try {
      const res = await fetch("/api/session/status");
      const data = await res.json();
      state.sessionStatus = data;

      if (data.has_instagram_session) {
        sessionStatusDot.className = "status-dot active";
        sessionBadge.className = "status-indicator-badge connected";
        sessionBadgeText.textContent = "Instagram Session Connected";
        sessionDescText.textContent = `Authenticated session active (${data.cookies_count} cookies loaded). Stories & private profile downloads enabled!`;
        btnClearSession.classList.remove("hidden");
        igSessionTag.style.background = "rgba(16, 185, 129, 0.15)";
        igSessionTag.style.color = "var(--color-success)";
        igSessionTagText.textContent = "Authenticated Session Active";
      } else {
        sessionStatusDot.className = "status-dot inactive";
        sessionBadge.className = "status-indicator-badge";
        sessionBadgeText.textContent = "No Active Session";
        sessionDescText.textContent = "No session loaded. You can still download public posts and reels without login.";
        btnClearSession.classList.add("hidden");
        igSessionTag.style.background = "rgba(255, 255, 255, 0.08)";
        igSessionTag.style.color = "var(--text-muted)";
        igSessionTagText.textContent = "Public Mode";
      }
    } catch (e) {
      console.warn("Could not check session status:", e);
    }
  }

  btnVerifySession?.addEventListener("click", async () => {
    btnVerifySession.disabled = true;
    await checkSessionStatus();
    showToast("info", "Session connection status refreshed.");
    btnVerifySession.disabled = false;
  });

  // Cookie File Drag & Drop + Upload
  if (cookieUploadDropzone) {
    cookieUploadDropzone.addEventListener("click", () => cookieFileInput.click());

    cookieUploadDropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      cookieUploadDropzone.classList.add("dragover");
    });

    cookieUploadDropzone.addEventListener("dragleave", () => {
      cookieUploadDropzone.classList.remove("dragover");
    });

    cookieUploadDropzone.addEventListener("drop", async (e) => {
      e.preventDefault();
      cookieUploadDropzone.classList.remove("dragover");
      if (e.dataTransfer.files.length > 0) {
        handleCookieFileUpload(e.dataTransfer.files[0]);
      }
    });

    cookieFileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        handleCookieFileUpload(e.target.files[0]);
      }
    });
  }

  async function handleCookieFileUpload(file) {
    const selectedPlatform = document.querySelector('input[name="cookie-upload-platform"]:checked')?.value || "instagram";
    const formData = new FormData();
    formData.append("file", file);
    formData.append("platform", selectedPlatform);

    try {
      showToast("info", `Uploading and parsing ${file.name}...`);
      const res = await fetch("/api/session/upload-cookies", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.success) {
        showToast("success", data.message || "Cookies successfully imported!");
        checkSessionStatus();
      } else {
        showToast("error", data.detail || "Failed to parse cookie file.");
      }
    } catch (err) {
      showToast("error", `Cookie upload error: ${err}`);
    }
  }

  // Browser auto-extract buttons
  browserButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      const browser = btn.dataset.browser;
      if (!browser) return;

      btn.disabled = true;
      const originalText = btn.innerHTML;
      btn.innerHTML = `<span>Extracting...</span>`;

      try {
        const res = await fetch("/api/session/extract-browser", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ browser: browser }),
        });
        const data = await res.json();
        if (data.success) {
          showToast("success", `Extracted session from ${browser.toUpperCase()}!`);
          checkSessionStatus();
        } else {
          showToast("warning", data.details?.error || `Could not find Instagram session in ${browser}.`);
        }
      } catch (err) {
        showToast("error", `Browser extraction error: ${err}`);
      } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
        lucide.createIcons();
      }
    });
  });

  btnScanAllBrowsers.addEventListener("click", async () => {
    btnScanAllBrowsers.disabled = true;
    btnScanAllBrowsers.innerHTML = `<span>Scanning all browsers...</span>`;

    try {
      const res = await fetch("/api/session/extract-browser", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (data.success) {
        showToast("success", `Found active session in ${data.browser.toUpperCase()}!`);
        checkSessionStatus();
      } else {
        showToast("warning", "No active Instagram session found in standard browser profiles.");
      }
    } catch (err) {
      showToast("error", `Auto-scan error: ${err}`);
    } finally {
      btnScanAllBrowsers.disabled = false;
      btnScanAllBrowsers.innerHTML = `<i data-lucide="search"></i><span>Auto-Scan All Browsers</span>`;
      lucide.createIcons();
    }
  });

  btnCopyJsSnippet.addEventListener("click", () => {
    const code = "copy(document.cookie)";
    navigator.clipboard.writeText(code).then(() => {
      btnCopyJsSnippet.innerHTML = `<i data-lucide="check"></i><span>Copied!</span>`;
      lucide.createIcons();
      showToast("success", "Console command copied to clipboard!");
      setTimeout(() => {
        btnCopyJsSnippet.innerHTML = `<i data-lucide="copy"></i><span>Copy Command</span>`;
        lucide.createIcons();
      }, 2000);
    });
  });

  btnSaveCookieText.addEventListener("click", async () => {
    const raw = rawCookieInput.value.trim();
    if (!raw) {
      showToast("warning", "Please paste your cookies or session ID first.");
      return;
    }

    try {
      const res = await fetch("/api/session/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ raw_cookies: raw }),
      });
      const data = await res.json();
      if (data.success) {
        showToast("success", "Session cookies saved and verified!");
        rawCookieInput.value = "";
        checkSessionStatus();
      } else {
        showToast("error", data.detail || "Invalid cookies format.");
      }
    } catch (e) {
      showToast("error", `Failed to save cookies: ${e}`);
    }
  });

  btnClearSession.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to disconnect your Instagram session?")) return;
    try {
      await fetch("/api/session/clear", { method: "POST" });
      showToast("info", "Instagram session disconnected.");
      checkSessionStatus();
    } catch (e) {
      showToast("error", `Failed to clear session: ${e}`);
    }
  });

  // -------------------------------------------------------------
  // 10. Gallery & Media Explorer
  // -------------------------------------------------------------
  async function loadGalleryOverview() {
    try {
      const res = await fetch("/api/gallery");
      const data = await res.json();
      state.galleryUsers = data.users || [];

      // Update badge
      const totalMedia = state.galleryUsers.reduce((acc, u) => acc + u.item_count, 0);
      galleryTotalBadge.textContent = totalMedia.toString();

      renderUserList();

      // If user was selected or default to first
      if (state.selectedUser) {
        loadUserMedia(state.selectedUser.platform, state.selectedUser.username);
      } else if (state.galleryUsers.length > 0) {
        const first = state.galleryUsers[0];
        loadUserMedia(first.platform, first.username);
      } else {
        renderEmptyGallery();
      }
    } catch (e) {
      console.warn("Error loading gallery:", e);
    }
  }

  galleryUserSearch?.addEventListener("input", (e) => {
    state.userSearchQuery = e.target.value.toLowerCase().trim();
    renderUserList();
  });

  function renderUserList() {
    galleryUserList.innerHTML = "";
    const filteredUsers = state.galleryUsers.filter((u) => {
      if (!state.userSearchQuery) return true;
      return (
        u.username.toLowerCase().includes(state.userSearchQuery) ||
        u.platform.toLowerCase().includes(state.userSearchQuery)
      );
    });

    if (filteredUsers.length === 0) {
      galleryUserList.innerHTML = `<div class="empty-state-mini" style="padding: 20px; color: var(--text-dim); text-align: center;">No profiles match search.</div>`;
      return;
    }

    filteredUsers.forEach((u) => {
      const isSelected =
        state.selectedUser &&
        state.selectedUser.platform === u.platform &&
        state.selectedUser.username === u.username;

      const item = document.createElement("div");
      item.className = `user-item ${isSelected ? "active" : ""}`;
      
      const avatarHtml = u.profile_pic_url
        ? `<img src="${u.profile_pic_url}" class="user-avatar-mini" alt="${u.username}" />`
        : `<div class="user-avatar-mini">${u.username.charAt(0).toUpperCase()}</div>`;

      item.innerHTML = `
        ${avatarHtml}
        <div class="user-item-info">
          <div class="user-item-name">@${escapeHtml(u.username)}</div>
          <div class="user-item-sub">
            <span>${u.platform.toUpperCase()}</span> • 
            <span>${u.item_count} items</span> • 
            <span>${u.total_size_human}</span>
          </div>
        </div>
      `;

      item.addEventListener("click", () => {
        loadUserMedia(u.platform, u.username);
      });

      galleryUserList.appendChild(item);
    });
  }

  async function loadUserMedia(platform, username) {
    state.selectedUser = { platform, username };
    state.selectedFilenames.clear();
    updateBatchCount();
    renderUserList();

    try {
      const res = await fetch(`/api/gallery/${platform}/${username}`);
      const data = await res.json();
      state.currentGalleryItems = data.items || [];

      // Update Header
      galleryActiveUsername.textContent = `@${data.username}`;
      galleryActiveMeta.textContent = `${platform.toUpperCase()} • ${data.item_count} files • ${data.total_size_human}`;
      
      if (data.profile_pic_url) {
        galleryUserAvatar.src = data.profile_pic_url;
        galleryUserAvatar.classList.remove("hidden");
      } else {
        galleryUserAvatar.classList.add("hidden");
      }

      galleryActionsBar.classList.remove("hidden");
      galleryToolbar.classList.remove("hidden");
      renderMediaGrid();
    } catch (e) {
      showToast("error", `Error loading user gallery: ${e}`);
    }
  }

  function getSortedAndFilteredItems() {
    let items = [...state.currentGalleryItems];

    // Filter by type
    if (state.currentGalleryFilter !== "all") {
      items = items.filter((it) => it.media_type === state.currentGalleryFilter);
    }

    // Filter by search query
    if (state.gallerySearchQuery) {
      const q = state.gallerySearchQuery.toLowerCase();
      items = items.filter((it) => {
        const fnMatch = it.filename.toLowerCase().includes(q);
        const capMatch = it.caption ? it.caption.toLowerCase().includes(q) : false;
        return fnMatch || capMatch;
      });
    }

    // Sort items
    const s = state.gallerySortOrder;
    items.sort((a, b) => {
      if (s === "date-desc") {
        return (b.created_time || "").localeCompare(a.created_time || "");
      } else if (s === "date-asc") {
        return (a.created_time || "").localeCompare(b.created_time || "");
      } else if (s === "size-desc") {
        return b.file_size - a.file_size;
      } else if (s === "size-asc") {
        return a.file_size - b.file_size;
      } else if (s === "name-asc") {
        return a.filename.localeCompare(b.filename);
      }
      return 0;
    });

    return items;
  }

  function renderMediaGrid() {
    galleryMediaGrid.innerHTML = "";
    const filtered = getSortedAndFilteredItems();
    state.filteredModalItems = filtered;

    if (filtered.length === 0) {
      galleryMediaGrid.innerHTML = `
        <div class="empty-gallery">
          <i data-lucide="image-off" class="empty-icon"></i>
          <h3>No media matching filter or search</h3>
          <p>Try clearing your search query or selecting another filter category.</p>
        </div>
      `;
      lucide.createIcons();
      return;
    }

    filtered.forEach((item, index) => {
      const isSelected = state.selectedFilenames.has(item.filename);
      const card = document.createElement("div");
      card.className = `media-card ${isSelected ? "selected" : ""}`;

      let mediaContent = "";
      let badgeContent = "";

      if (item.media_type === "image") {
        mediaContent = `<img src="${item.url_path}" class="media-thumbnail" alt="${item.filename}" loading="lazy" />`;
        badgeContent = `<i data-lucide="image"></i> Photo`;
      } else if (item.media_type === "video") {
        mediaContent = `<video src="${item.url_path}#t=0.5" class="media-thumbnail" preload="metadata" muted></video>`;
        badgeContent = `<i data-lucide="play"></i> Video`;
      } else if (item.media_type === "audio") {
        mediaContent = `<div class="media-thumbnail" style="display:flex;align-items:center;justify-content:center;background:#131d2e;"><i data-lucide="music" style="width:40px;height:40px;color:var(--accent-primary)"></i></div>`;
        badgeContent = `<i data-lucide="music"></i> Audio`;
      }

      const checkboxHtml = state.batchMode
        ? `<input type="checkbox" class="media-card-select-checkbox" ${isSelected ? "checked" : ""} />`
        : "";

      card.innerHTML = `
        ${checkboxHtml}
        ${mediaContent}
        <div class="media-card-badge">${badgeContent}</div>
        <div class="media-card-overlay">
          <span>${item.file_size_human}</span>
          <span>${item.created_time.split(" ")[0]}</span>
        </div>
      `;

      if (state.batchMode) {
        const chk = card.querySelector(".media-card-select-checkbox");
        card.addEventListener("click", (e) => {
          if (e.target !== chk) {
            chk.checked = !chk.checked;
          }
          if (chk.checked) {
            state.selectedFilenames.add(item.filename);
            card.classList.add("selected");
          } else {
            state.selectedFilenames.delete(item.filename);
            card.classList.remove("selected");
          }
          updateBatchCount();
        });
      } else {
        card.addEventListener("click", () => openMediaModal(index));
      }

      galleryMediaGrid.appendChild(card);
    });

    lucide.createIcons();
  }

  function updateBatchCount() {
    if (batchSelectedCount) {
      batchSelectedCount.textContent = state.selectedFilenames.size.toString();
    }
  }

  function renderEmptyGallery() {
    galleryActiveUsername.textContent = "Select a downloaded user";
    galleryActiveMeta.textContent = "Choose a profile from the left sidebar to view media";
    galleryUserAvatar.classList.add("hidden");
    galleryActionsBar.classList.add("hidden");
    galleryToolbar.classList.add("hidden");
    batchActionBar.classList.add("hidden");
    galleryMediaGrid.innerHTML = `
      <div class="empty-gallery">
        <i data-lucide="image" class="empty-icon"></i>
        <h3>No media selected</h3>
        <p>Start a download in Instagram or TikTok tabs to populate the gallery.</p>
      </div>
    `;
    lucide.createIcons();
  }

  // Filter Pills
  filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      filterBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.currentGalleryFilter = btn.dataset.filter;
      renderMediaGrid();
    });
  });

  // Search & Sort Handlers
  galleryMediaSearch?.addEventListener("input", (e) => {
    state.gallerySearchQuery = e.target.value.trim();
    renderMediaGrid();
  });

  gallerySortSelect?.addEventListener("change", (e) => {
    state.gallerySortOrder = e.target.value;
    renderMediaGrid();
  });

  btnRefreshGallery.addEventListener("click", () => loadGalleryOverview());

  btnGalleryZip.addEventListener("click", () => {
    if (!state.selectedUser) return;
    const { platform, username } = state.selectedUser;
    showToast("info", "Generating full ZIP archive...");
    window.location.href = `/api/gallery/${platform}/${username}/zip`;
  });

  btnGalleryFinder.addEventListener("click", async () => {
    if (!state.selectedUser) return;
    const { platform, username } = state.selectedUser;
    await fetch("/api/gallery/open-finder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ platform, username }),
    });
    showToast("info", `Opened @${username} folder in Finder.`);
  });

  btnGalleryDelete.addEventListener("click", async () => {
    if (!state.selectedUser) return;
    const { platform, username } = state.selectedUser;
    if (!confirm(`Are you sure you want to delete all downloaded files for @${username}?`)) return;

    try {
      await fetch(`/api/gallery/${platform}/${username}`, { method: "DELETE" });
      showToast("info", `Deleted profile @${username}.`);
      state.selectedUser = null;
      loadGalleryOverview();
      updateStorageStats();
    } catch (e) {
      showToast("error", `Delete failed: ${e}`);
    }
  });

  // -------------------------------------------------------------
  // 11. Batch Selection Mode
  // -------------------------------------------------------------
  btnToggleBatchMode?.addEventListener("click", () => {
    state.batchMode = !state.batchMode;
    btnToggleBatchMode.classList.toggle("active", state.batchMode);
    batchActionBar.classList.toggle("hidden", !state.batchMode);
    if (!state.batchMode) {
      state.selectedFilenames.clear();
    }
    updateBatchCount();
    renderMediaGrid();
  });

  btnBatchSelectAll?.addEventListener("click", () => {
    state.filteredModalItems.forEach((it) => state.selectedFilenames.add(it.filename));
    updateBatchCount();
    renderMediaGrid();
  });

  btnBatchDeselect?.addEventListener("click", () => {
    state.selectedFilenames.clear();
    updateBatchCount();
    renderMediaGrid();
  });

  btnBatchZip?.addEventListener("click", async () => {
    if (state.selectedFilenames.size === 0) {
      showToast("warning", "No files selected to export.");
      return;
    }
    const { platform, username } = state.selectedUser;
    try {
      showToast("info", `Generating ZIP for ${state.selectedFilenames.size} files...`);
      const res = await fetch(`/api/gallery/${platform}/${username}/batch-zip`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filenames: Array.from(state.selectedFilenames) }),
      });
      const data = await res.json();
      if (data.success && data.zip_url) {
        window.location.href = data.zip_url;
        showToast("success", `Export ready! Downloaded ${data.items_count} items.`);
      } else {
        showToast("error", "Could not create batch ZIP archive.");
      }
    } catch (e) {
      showToast("error", `Batch ZIP failed: ${e}`);
    }
  });

  btnBatchDelete?.addEventListener("click", async () => {
    if (state.selectedFilenames.size === 0) {
      showToast("warning", "No files selected to delete.");
      return;
    }
    if (!confirm(`Are you sure you want to delete ${state.selectedFilenames.size} selected files?`)) return;

    const { platform, username } = state.selectedUser;
    try {
      const res = await fetch(`/api/gallery/${platform}/${username}/batch-delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filenames: Array.from(state.selectedFilenames) }),
      });
      const data = await res.json();
      if (data.success) {
        showToast("success", data.message || `Deleted ${data.deleted_count} files.`);
        state.selectedFilenames.clear();
        updateBatchCount();
        loadUserMedia(platform, username);
        updateStorageStats();
      }
    } catch (e) {
      showToast("error", `Batch delete failed: ${e}`);
    }
  });

  // -------------------------------------------------------------
  // 12. Lightbox / Media Modal & Keyboard Navigation
  // -------------------------------------------------------------
  function openMediaModal(index) {
    if (!state.filteredModalItems || state.filteredModalItems.length === 0) return;
    if (index < 0) index = 0;
    if (index >= state.filteredModalItems.length) index = state.filteredModalItems.length - 1;

    state.currentModalIndex = index;
    const item = state.filteredModalItems[index];

    modalIndexCounter.textContent = `${index + 1} of ${state.filteredModalItems.length}`;
    modalFilename.textContent = item.filename;
    modalFilesize.textContent = item.file_size_human;
    modalFiledate.textContent = item.created_time;
    modalDownloadLink.href = item.url_path;
    modalDownloadLink.setAttribute("download", item.filename);

    if (item.caption) {
      modalCaptionContainer.classList.remove("hidden");
      modalCaptionText.textContent = item.caption;
    } else {
      modalCaptionContainer.classList.add("hidden");
    }

    modalMediaDisplay.innerHTML = "";
    if (item.media_type === "image") {
      modalVideoControlsRow.classList.add("hidden");
      const img = document.createElement("img");
      img.src = item.url_path;
      img.alt = item.filename;
      modalMediaDisplay.appendChild(img);
    } else if (item.media_type === "video") {
      modalVideoControlsRow.classList.remove("hidden");
      const vid = document.createElement("video");
      vid.src = item.url_path;
      vid.controls = true;
      vid.autoplay = true;
      vid.style.width = "100%";
      vid.style.maxHeight = "75vh";
      modalPlaybackSpeed.value = "1";
      modalPlaybackSpeed.onchange = (e) => {
        vid.playbackRate = parseFloat(e.target.value);
      };
      modalMediaDisplay.appendChild(vid);
    } else if (item.media_type === "audio") {
      modalVideoControlsRow.classList.add("hidden");
      const audio = document.createElement("audio");
      audio.src = item.url_path;
      audio.controls = true;
      audio.autoplay = true;
      modalMediaDisplay.appendChild(audio);
    }

    modalFinderBtn.onclick = () => {
      fetch("/api/gallery/open-finder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: item.full_path }),
      });
      showToast("info", "Revealed in macOS Finder.");
    };

    modalCopyPathBtn.onclick = () => {
      navigator.clipboard.writeText(item.full_path).then(() => {
        showToast("success", "Copied local file path to clipboard!");
      });
    };

    modalDeleteBtn.onclick = async () => {
      if (!confirm(`Delete '${item.filename}'?`)) return;
      try {
        const { platform, username } = state.selectedUser;
        const res = await fetch(
          `/api/gallery/${platform}/${username}/item?filename=${encodeURIComponent(item.filename)}`,
          { method: "DELETE" }
        );
        const data = await res.json();
        if (data.success) {
          showToast("success", `Deleted ${item.filename}`);
          // Remove from list
          state.currentGalleryItems = state.currentGalleryItems.filter(
            (it) => it.filename !== item.filename
          );
          state.filteredModalItems = getSortedAndFilteredItems();
          renderMediaGrid();
          updateStorageStats();
          if (state.filteredModalItems.length > 0) {
            openMediaModal(Math.min(index, state.filteredModalItems.length - 1));
          } else {
            closeModal();
          }
        }
      } catch (e) {
        showToast("error", `Delete failed: ${e}`);
      }
    };

    mediaModal.classList.remove("hidden");
  }

  function closeModal() {
    mediaModal.classList.add("hidden");
    modalMediaDisplay.innerHTML = ""; // Stop audio/video
  }

  btnLightboxPrev?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (state.currentModalIndex > 0) {
      openMediaModal(state.currentModalIndex - 1);
    } else {
      openMediaModal(state.filteredModalItems.length - 1); // Loop to end
    }
  });

  btnLightboxNext?.addEventListener("click", (e) => {
    e.stopPropagation();
    if (state.currentModalIndex < state.filteredModalItems.length - 1) {
      openMediaModal(state.currentModalIndex + 1);
    } else {
      openMediaModal(0); // Loop to start
    }
  });

  btnCloseModal.addEventListener("click", closeModal);
  mediaModal.addEventListener("click", (e) => {
    if (e.target === mediaModal) closeModal();
  });

  document.addEventListener("keydown", (e) => {
    if (mediaModal.classList.contains("hidden")) return;
    if (e.key === "Escape") {
      closeModal();
    } else if (e.key === "ArrowLeft") {
      if (state.currentModalIndex > 0) openMediaModal(state.currentModalIndex - 1);
    } else if (e.key === "ArrowRight") {
      if (state.currentModalIndex < state.filteredModalItems.length - 1) {
        openMediaModal(state.currentModalIndex + 1);
      }
    }
  });

  // Finder header button
  btnOpenFinder.addEventListener("click", () => {
    fetch("/api/gallery/open-finder", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    showToast("info", "Opened downloads root folder in macOS Finder.");
  });

  // Utility
  function escapeHtml(text) {
    if (!text) return "";
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Initial Boot
  initSSE();
  checkSessionStatus();
  loadGalleryOverview();
  updateStorageStats();
  loadJobsStatus();
});
