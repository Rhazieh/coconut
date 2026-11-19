(function () {
  "use strict";

  let bridge = null;
  let toastTimer = null;
  let scrollRaf = false;
  let dragDepth = 0;
  let currentTheme = "warm-dark";

  let uiStrings = {
    toc_label: "Outline",
    welcome_sub: "Drop a <code>.md</code> file here or open one from disk.",
    welcome_open: "Open file…",
    recent_title: "Recent",
    hint_open: "Ctrl+O Open",
    hint_zoom: "Ctrl+/− Text",
    hint_theme: "Ctrl+T Palette",
    hint_toc: "Ctrl+B Outline",
    btn_toc_title: "Outline (Ctrl+B)",
    btn_open_title: "Open file (Ctrl+O)",
    btn_dec_title: "Decrease text size (Ctrl+-)",
    btn_reset_title: "Reset text size (Ctrl+0)",
    btn_inc_title: "Increase text size (Ctrl++)",
    btn_theme_prefix: "Palette",
    find_placeholder: "Find…",
    find_prev_title: "Previous (Shift+Enter)",
    find_next_title: "Next (Enter)",
    find_close_title: "Close (Esc)",
    drop_prompt: "Drop file to read",
    copy_btn: "Copy",
    copied_btn: "Copied",
    toast_copied: "Copied",
    "theme_warm-dark": "Warm Night",
    "theme_sepia": "Paper Sepia",
    "theme_soft-light": "Soft Stone",
  };

  const state = {
    hasDoc: false,
    tocCount: 0,
    sidebarWanted: true,
    tocElements: [],
    tocButtons: new Map(),
    activeId: null,
  };

  const progressBar = document.getElementById("progress-bar");
  const sidebar = document.getElementById("toc-sidebar");
  const tocDocTitle = document.getElementById("toc-doc-title");
  const tocList = document.getElementById("toc-list");
  const scrollEl = document.getElementById("reader-scroll");
  const welcomeEl = document.getElementById("welcome");
  const welcomeSub = document.getElementById("welcome-sub");
  const recentLabel = document.getElementById("recent-label");
  const contentEl = document.getElementById("content");
  const recentBlock = document.getElementById("recent-block");
  const recentList = document.getElementById("recent-list");

  const hintOpen = document.getElementById("hint-open");
  const hintZoom = document.getElementById("hint-zoom");
  const hintTheme = document.getElementById("hint-theme");
  const hintToc = document.getElementById("hint-toc");

  const btnToc = document.getElementById("btn-toc");
  const btnOpen = document.getElementById("btn-open");
  const btnWelcomeOpen = document.getElementById("btn-welcome-open");
  const btnFontDec = document.getElementById("btn-font-dec");
  const btnFontReset = document.getElementById("font-size-value");
  const btnFontInc = document.getElementById("btn-font-inc");
  const btnTheme = document.getElementById("btn-theme");

  const findBar = document.getElementById("find-bar");
  const findInput = document.getElementById("find-input");
  const findPrev = document.getElementById("find-prev");
  const findNext = document.getElementById("find-next");
  const findClose = document.getElementById("find-close");

  const dropOverlay = document.getElementById("drop-overlay");
  const dropBox = document.getElementById("drop-box");
  const toastEl = document.getElementById("toast");

  function showToast(msg) {
    if (!msg) return;
    toastEl.textContent = msg;
    toastEl.classList.remove("hidden");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toastEl.classList.add("hidden");
    }, 1300);
  }

  function refreshThemeTooltip() {
    const label = uiStrings["theme_" + currentTheme] || currentTheme;
    btnTheme.title = uiStrings.btn_theme_prefix + ": " + label + " (Ctrl+T)";
  }

  function applyStrings(strings) {
    if (!strings) return;
    uiStrings = Object.assign({}, uiStrings, strings);
    sidebar.setAttribute("aria-label", uiStrings.toc_label);
    welcomeSub.innerHTML = uiStrings.welcome_sub;
    btnWelcomeOpen.textContent = uiStrings.welcome_open;
    recentLabel.textContent = uiStrings.recent_title;
    hintOpen.textContent = uiStrings.hint_open;
    hintZoom.textContent = uiStrings.hint_zoom;
    hintTheme.textContent = uiStrings.hint_theme;
    hintToc.textContent = uiStrings.hint_toc;
    btnToc.title = uiStrings.btn_toc_title;
    btnOpen.title = uiStrings.btn_open_title;
    btnFontDec.title = uiStrings.btn_dec_title;
    btnFontReset.title = uiStrings.btn_reset_title;
    btnFontInc.title = uiStrings.btn_inc_title;
    findInput.placeholder = uiStrings.find_placeholder;
    findPrev.title = uiStrings.find_prev_title;
    findNext.title = uiStrings.find_next_title;
    findClose.title = uiStrings.find_close_title;
    dropBox.textContent = uiStrings.drop_prompt;
    refreshThemeTooltip();
  }

  function updateSidebarVisibility() {
    const showSidebar = state.hasDoc && state.sidebarWanted && state.tocCount >= 2;
    sidebar.classList.toggle("sidebar-hidden", !showSidebar);
    btnToc.classList.toggle("hidden", !state.hasDoc || state.tocCount < 2);
  }

  function applySettings(cfg) {
    if (!cfg) return;
    if (typeof cfg.font_size === "number") {
      document.documentElement.style.setProperty("--font-size", cfg.font_size + "px");
      btnFontReset.textContent = String(cfg.font_size);
    }
    if (cfg.theme) {
      currentTheme = cfg.theme;
      document.documentElement.setAttribute("data-theme", cfg.theme);
      refreshThemeTooltip();
    }
    if (typeof cfg.sidebar_visible === "boolean") {
      state.sidebarWanted = cfg.sidebar_visible;
      updateSidebarVisibility();
    }
  }

  function enhanceCodeBlocks() {
    const pres = contentEl.querySelectorAll("pre");
    pres.forEach((pre) => {
      if (pre.parentElement && pre.parentElement.classList.contains("code-block")) {
        return;
      }
      const wrapper = document.createElement("div");
      wrapper.className = "code-block";

      const codeEl = pre.querySelector("code");
      const lang = codeEl ? codeEl.getAttribute("data-lang") : "";

      const meta = document.createElement("div");
      meta.className = "code-meta";

      if (lang) {
        const langBadge = document.createElement("span");
        langBadge.className = "code-lang";
        langBadge.textContent = lang;
        meta.appendChild(langBadge);
      }

      const copyBtn = document.createElement("button");
      copyBtn.type = "button";
      copyBtn.className = "copy-btn";
      copyBtn.textContent = uiStrings.copy_btn;
      copyBtn.addEventListener("click", () => {
        const text = (codeEl ? codeEl.textContent : pre.textContent) || "";
        if (bridge) bridge.copyText(text);
        copyBtn.textContent = uiStrings.copied_btn;
        showToast(uiStrings.toast_copied);
        setTimeout(() => {
          copyBtn.textContent = uiStrings.copy_btn;
        }, 1200);
      });
      meta.appendChild(copyBtn);

      pre.parentNode.insertBefore(wrapper, pre);
      wrapper.appendChild(meta);
      wrapper.appendChild(pre);
    });
  }

  function wireInternalAnchors() {
    const anchors = contentEl.querySelectorAll('a[href^="#"]');
    anchors.forEach((anchor) => {
      anchor.addEventListener("click", (e) => {
        const rawHref = anchor.getAttribute("href") || "";
        const targetId = decodeURIComponent(rawHref.slice(1));
        if (!targetId) return;
        const target = document.getElementById(targetId);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
    });
  }

  function buildToc(toc, docTitle) {
    tocList.innerHTML = "";
    state.tocElements = [];
    state.tocButtons.clear();
    state.activeId = null;
    tocDocTitle.textContent = docTitle || "Velum";

    if (!Array.isArray(toc) || toc.length === 0) return;

    const frag = document.createDocumentFragment();
    toc.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "toc-item toc-l" + Math.min(3, Math.max(1, item.level || 1));
      btn.textContent = item.text || "";
      btn.title = item.text || "";
      btn.setAttribute("data-target", item.id || "");
      btn.addEventListener("click", () => {
        const target = document.getElementById(item.id);
        if (target) {
          target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
      frag.appendChild(btn);

      const el = document.getElementById(item.id);
      if (el) {
        state.tocElements.push({ id: item.id, el });
        state.tocButtons.set(item.id, btn);
      }
    });
    tocList.appendChild(frag);
  }

  function updateScrollState() {
    scrollRaf = false;
    if (!state.hasDoc) {
      progressBar.style.width = "0%";
      return;
    }

    const maxScroll = scrollEl.scrollHeight - scrollEl.clientHeight;
    const pct = maxScroll > 0 ? Math.min(100, Math.max(0, (scrollEl.scrollTop / maxScroll) * 100)) : 0;
    progressBar.style.width = pct.toFixed(1) + "%";

    if (state.tocElements.length === 0) return;

    const topBound = scrollEl.getBoundingClientRect().top + 72;
    let currentId = state.tocElements[0].id;
    for (let i = 0; i < state.tocElements.length; i++) {
      const rect = state.tocElements[i].el.getBoundingClientRect();
      if (rect.top <= topBound) {
        currentId = state.tocElements[i].id;
      } else {
        break;
      }
    }

    if (maxScroll > 0 && scrollEl.scrollTop >= maxScroll - 4) {
      currentId = state.tocElements[state.tocElements.length - 1].id;
    }

    if (currentId !== state.activeId) {
      if (state.activeId && state.tocButtons.has(state.activeId)) {
        state.tocButtons.get(state.activeId).classList.remove("active");
      }
      state.activeId = currentId;
      const activeBtn = state.tocButtons.get(currentId);
      if (activeBtn) {
        activeBtn.classList.add("active");
        const listRect = tocList.getBoundingClientRect();
        const btnRect = activeBtn.getBoundingClientRect();
        if (btnRect.top < listRect.top || btnRect.bottom > listRect.bottom) {
          activeBtn.scrollIntoView({ block: "nearest" });
        }
      }
    }
  }

  function renderDocument(doc, preserveScroll) {
    let ratio = 0;
    if (preserveScroll) {
      const maxScroll = scrollEl.scrollHeight - scrollEl.clientHeight;
      if (maxScroll > 0) ratio = scrollEl.scrollTop / maxScroll;
    }

    state.hasDoc = true;
    state.tocCount = Array.isArray(doc.toc) ? doc.toc.length : 0;

    welcomeEl.classList.add("hidden");
    contentEl.classList.remove("hidden");
    contentEl.innerHTML = doc.html || "";

    enhanceCodeBlocks();
    wireInternalAnchors();
    buildToc(doc.toc || [], doc.title || doc.filename || "Velum");
    updateSidebarVisibility();

    requestAnimationFrame(() => {
      if (preserveScroll) {
        const newMax = scrollEl.scrollHeight - scrollEl.clientHeight;
        scrollEl.scrollTop = newMax > 0 ? Math.round(ratio * newMax) : 0;
      } else {
        scrollEl.scrollTop = 0;
      }
      updateScrollState();
    });
  }

  function showWelcome(recentFiles) {
    state.hasDoc = false;
    state.tocCount = 0;
    state.tocElements = [];
    state.tocButtons.clear();
    state.activeId = null;

    contentEl.innerHTML = "";
    contentEl.classList.add("hidden");
    welcomeEl.classList.remove("hidden");
    progressBar.style.width = "0%";
    updateSidebarVisibility();

    recentList.innerHTML = "";
    if (Array.isArray(recentFiles) && recentFiles.length > 0) {
      recentBlock.classList.remove("hidden");
      recentFiles.forEach((fullPath) => {
        const li = document.createElement("li");
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "recent-btn";
        btn.title = fullPath;

        const sep = fullPath.lastIndexOf("/");
        const name = sep >= 0 ? fullPath.slice(sep + 1) : fullPath;
        const dir = sep > 0 ? fullPath.slice(0, sep) : "";

        const nameSpan = document.createElement("span");
        nameSpan.className = "recent-name";
        nameSpan.textContent = name;

        const dirSpan = document.createElement("span");
        dirSpan.className = "recent-dir";
        dirSpan.textContent = dir;

        btn.appendChild(nameSpan);
        btn.appendChild(dirSpan);
        btn.addEventListener("click", () => {
          if (bridge) bridge.openRecentFile(fullPath);
        });
        li.appendChild(btn);
        recentList.appendChild(li);
      });
    } else {
      recentBlock.classList.add("hidden");
    }
  }

  function openFindBar() {
    findBar.classList.remove("hidden");
    findInput.focus();
    findInput.select();
    if (findInput.value && bridge) {
      bridge.findText(findInput.value, false);
    }
  }

  function closeFindBar() {
    if (findBar.classList.contains("hidden")) return;
    findBar.classList.add("hidden");
    if (bridge) bridge.clearFind();
    scrollEl.focus();
  }

  btnToc.addEventListener("click", () => {
    if (bridge) bridge.toggleSidebar();
  });
  btnOpen.addEventListener("click", () => {
    if (bridge) bridge.openFileDialog();
  });
  btnWelcomeOpen.addEventListener("click", () => {
    if (bridge) bridge.openFileDialog();
  });
  btnFontDec.addEventListener("click", () => {
    if (bridge) bridge.adjustFontSize(-1);
  });
  btnFontReset.addEventListener("click", () => {
    if (bridge) bridge.resetFontSize();
  });
  btnFontInc.addEventListener("click", () => {
    if (bridge) bridge.adjustFontSize(1);
  });
  btnTheme.addEventListener("click", () => {
    if (bridge) bridge.cycleTheme();
  });

  findInput.addEventListener("input", () => {
    if (!bridge) return;
    if (findInput.value) {
      bridge.findText(findInput.value, false);
    } else {
      bridge.clearFind();
    }
  });
  findInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (bridge && findInput.value) {
        bridge.findText(findInput.value, e.shiftKey);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      closeFindBar();
    }
  });
  findNext.addEventListener("click", () => {
    if (bridge && findInput.value) bridge.findText(findInput.value, false);
  });
  findPrev.addEventListener("click", () => {
    if (bridge && findInput.value) bridge.findText(findInput.value, true);
  });
  findClose.addEventListener("click", closeFindBar);

  scrollEl.addEventListener("scroll", () => {
    if (!scrollRaf) {
      scrollRaf = true;
      requestAnimationFrame(updateScrollState);
    }
  });

  window.addEventListener(
    "wheel",
    (e) => {
      if (e.ctrlKey) {
        e.preventDefault();
        if (bridge && e.deltaY !== 0) {
          bridge.adjustFontSize(e.deltaY < 0 ? 1 : -1);
        }
      }
    },
    { passive: false }
  );

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !findBar.classList.contains("hidden")) {
      e.preventDefault();
      closeFindBar();
      return;
    }
    if (document.activeElement === findInput) return;
    if (e.ctrlKey || e.altKey || e.metaKey) return;

    if (e.key === "j") {
      scrollEl.scrollBy({ top: 96, behavior: "smooth" });
    } else if (e.key === "k") {
      scrollEl.scrollBy({ top: -96, behavior: "smooth" });
    }
  });

  window.addEventListener("dragenter", (e) => {
    if (e.dataTransfer && Array.from(e.dataTransfer.types || []).includes("Files")) {
      dragDepth += 1;
      dropOverlay.classList.remove("hidden");
    }
  });
  window.addEventListener("dragleave", () => {
    dragDepth = Math.max(0, dragDepth - 1);
    if (dragDepth === 0) {
      dropOverlay.classList.add("hidden");
    }
  });
  window.addEventListener("drop", () => {
    dragDepth = 0;
    dropOverlay.classList.add("hidden");
  });
  window.addEventListener("blur", () => {
    dragDepth = 0;
    dropOverlay.classList.add("hidden");
  });

  window.Velum = {
    applyStrings,
    applySettings,
    renderDocument,
    showWelcome,
    openFindBar,
    closeFindBar,
    showToast,
  };

  function connectBridge() {
    if (typeof QWebChannel === "undefined" || !window.qt || !window.qt.webChannelTransport) {
      return;
    }
    new QWebChannel(window.qt.webChannelTransport, (channel) => {
      bridge = channel.objects.bridge;
      if (bridge && typeof bridge.onReady === "function") {
        bridge.onReady();
      }
    });
  }

  connectBridge();
})();
