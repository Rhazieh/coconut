(function () {
  "use strict";

  const SHORTCUT_ORDER = [
    "open_file",
    "font_increase",
    "font_decrease",
    "font_reset",
    "cycle_theme",
    "toggle_sidebar",
    "find",
    "fullscreen",
    "reload",
    "go_back",
    "go_forward",
    "next_file",
    "prev_file",
    "close_file",
    "open_settings",
    "quit",
  ];

  let bridge = null;
  let toastTimer = null;
  let scrollRaf = false;
  let dragDepth = 0;
  let currentTheme = "warm-dark";
  let isFullscreen = false;
  let recordingAction = null;

  const scrollMemory = new Map();

  let uiStrings = {
    toc_label: "Outline",
    files_header: "Open files",
    files_add_title: "Add Markdown file…",
    files_close_title: "Close file",
    files_empty: "No open files",
    btn_settings_label: "Settings",
    btn_settings_title: "Settings (Ctrl+,)",
    welcome_sub: "Drop <code>.md</code> files here or open them from disk.",
    welcome_open: "Open files…",
    recent_title: "Recent",
    hint_open: "Ctrl+O Open",
    hint_zoom: "Ctrl+/− Text",
    hint_theme: "Ctrl+T Palette",
    hint_settings: "Ctrl+, Settings",
    btn_toc_title: "Outline & files (Ctrl+B)",
    btn_open_title: "Open files (Ctrl+O)",
    btn_dec_title: "Decrease text size (Ctrl+-)",
    btn_reset_title: "Reset text size (Ctrl+0)",
    btn_inc_title: "Increase text size (Ctrl++)",
    btn_theme_prefix: "Palette",
    btn_fullscreen_enter: "Fullscreen (F11)",
    btn_fullscreen_exit: "Exit fullscreen (F11)",
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
    settings_title: "Settings",
    tab_reading: "Reading",
    tab_translate: "Translate",
    tab_shortcuts: "Shortcuts",
    tab_about: "About",
    sec_palette: "Color palette",
    sec_text_size: "Text size",
    sec_interface_lang: "Interface language",
    lang_auto: "Automatic (System)",
    lang_en: "English",
    lang_es: "Español",
    sec_behavior: "Reader toggles",
    opt_sidebar: "Show outline & open files sidebar",
    opt_sidebar_desc: "Keep the left navigation panel visible while reading.",
    opt_progress: "Show reading progress hairline",
    opt_progress_desc: "Display a subtle 2 px progress indicator at the top edge.",
    opt_autoreload: "Auto-reload when file changes on disk",
    opt_autoreload_desc: "Refresh silently while preserving your scroll position.",
    opt_restore_session: "Remember open files across restarts",
    opt_restore_session_desc: "Keep opened documents across sessions until closed manually.",
    sec_quick_actions: "Quick actions",
    act_open_file: "Open files…",
    act_find: "Find in document",
    act_fullscreen: "Fullscreen mode",
    act_reload: "Reload document",
    sec_translate_toggle: "Context menu translation",
    opt_translate_enabled: "Show Google Translate on right-click",
    opt_translate_desc: "Adds an option when text is selected to open it directly in Google Translate.",
    sec_translate_presets: "Quick language pairs",
    sec_translate_pair: "Language pair",
    lbl_translate_source: "From",
    lbl_translate_target: "To",
    btn_swap_langs: "Swap languages",
    translate_privacy_note: "Offline by default: text is only sent to Google Translate in your browser when you click the context menu action.",
    sec_shortcuts_desc: "Click any shortcut pill and press a new key combination. Press Esc to cancel.",
    btn_reset_shortcuts: "Reset defaults",
    btn_clear_shortcut: "Clear",
    shortcut_press: "Press keys…",
    shortcut_empty: "None",
    about_tagline: "Minimalist, local-first, eye-comfort Markdown viewer for Linux (Wayland & X11).",
    about_credits_title: "Credits & Open Source Licenses",
    about_author: "Created by Maximiliano Cano (Rhazieh) — MIT License.",
    about_font: "Typography: Atkinson Hyperlegible Next (Braille Institute) — SIL OFL 1.1.",
    about_engine: "Rendering: libcmark-gfm / python-markdown + PyQt6 QtWebEngine.",
    about_contribute_title: "How to contribute",
    about_contribute_body: "Coconut stays viewer-only, offline, and distraction-free. You can report bugs, suggest ergonomic improvements, or open pull requests on GitHub.",
    btn_github_repo: "GitHub Repository",
    btn_report_issue: "Report Issue",
    btn_contribute: "Contributing Guide",
  };

  const state = {
    hasDoc: false,
    currentPath: "",
    tocCount: 0,
    sidebarWanted: true,
    tocElements: [],
    tocButtons: new Map(),
    activeId: null,
    openFiles: [],
    activeFile: "",
    collapsedFolders: new Set(),
    shortcuts: {},
  };

  const progressBar = document.getElementById("progress-bar");
  const sidebar = document.getElementById("toc-sidebar");
  const tocSection = document.getElementById("toc-section");
  const tocDocTitle = document.getElementById("toc-doc-title");
  const tocList = document.getElementById("toc-list");
  const filesTitle = document.getElementById("files-title");
  const btnFilesAdd = document.getElementById("btn-files-add");
  const filesList = document.getElementById("files-list");
  const btnSettings = document.getElementById("btn-settings");
  const btnSettingsLabel = document.getElementById("btn-settings-label");

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
  const hintSettings = document.getElementById("hint-settings");

  const btnToc = document.getElementById("btn-toc");
  const btnOpen = document.getElementById("btn-open");
  const btnWelcomeOpen = document.getElementById("btn-welcome-open");
  const btnFontDec = document.getElementById("btn-font-dec");
  const btnFontReset = document.getElementById("font-size-value");
  const btnFontInc = document.getElementById("btn-font-inc");
  const btnTheme = document.getElementById("btn-theme");
  const btnFullscreen = document.getElementById("btn-fullscreen");
  const iconFsEnter = btnFullscreen.querySelector(".icon-enter");
  const iconFsExit = btnFullscreen.querySelector(".icon-exit");

  const findBar = document.getElementById("find-bar");
  const findInput = document.getElementById("find-input");
  const findPrev = document.getElementById("find-prev");
  const findNext = document.getElementById("find-next");
  const findClose = document.getElementById("find-close");

  const dropOverlay = document.getElementById("drop-overlay");
  const dropBox = document.getElementById("drop-box");
  const toastEl = document.getElementById("toast");

  // Settings modal elements
  const settingsModal = document.getElementById("settings-modal");
  const btnSettingsClose = document.getElementById("btn-settings-close");
  const tabBtns = Array.from(document.querySelectorAll(".modal-tab"));
  const tabPanels = {
    reading: document.getElementById("panel-reading"),
    translate: document.getElementById("panel-translate"),
    shortcuts: document.getElementById("panel-shortcuts"),
    about: document.getElementById("panel-about"),
  };

  const themeCards = Array.from(document.querySelectorAll(".theme-card"));
  const setFontDec = document.getElementById("set-font-dec");
  const setFontValue = document.getElementById("set-font-value");
  const setFontInc = document.getElementById("set-font-inc");
  const setFontReset = document.getElementById("set-font-reset");
  const setLanguage = document.getElementById("set-language");

  const chkSidebar = document.getElementById("chk-sidebar");
  const chkProgress = document.getElementById("chk-progress");
  const chkAutoreload = document.getElementById("chk-autoreload");
  const chkRestore = document.getElementById("chk-restore");
  const chkTranslate = document.getElementById("chk-translate");

  const qaOpen = document.getElementById("qa-open");
  const qaFind = document.getElementById("qa-find");
  const qaFullscreen = document.getElementById("qa-fullscreen");
  const qaReload = document.getElementById("qa-reload");

  const setTrSource = document.getElementById("set-tr-source");
  const setTrTarget = document.getElementById("set-tr-target");
  const btnTrSwap = document.getElementById("btn-tr-swap");
  const trPresets = Array.from(document.querySelectorAll("[data-tr-preset]"));

  const btnResetShortcuts = document.getElementById("btn-reset-shortcuts");
  const shortcutsListEl = document.getElementById("shortcuts-list");

  const lnkRepo = document.getElementById("lnk-repo");
  const lnkIssues = document.getElementById("lnk-issues");
  const lnkContribute = document.getElementById("lnk-contribute");

  function setText(id, text) {
    const el = document.getElementById(id);
    if (el && typeof text === "string") el.textContent = text;
  }

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

  function refreshFullscreenButton() {
    iconFsEnter.classList.toggle("hidden", isFullscreen);
    iconFsExit.classList.toggle("hidden", !isFullscreen);
    btnFullscreen.title = isFullscreen ? uiStrings.btn_fullscreen_exit : uiStrings.btn_fullscreen_enter;
  }

  function setFullscreenState(flag) {
    isFullscreen = Boolean(flag);
    refreshFullscreenButton();
  }

  function populateTranslateSelects(langs) {
    if (!Array.isArray(langs) || langs.length === 0) return;
    const prevSrc = setTrSource.value;
    const prevTgt = setTrTarget.value;
    setTrSource.innerHTML = "";
    setTrTarget.innerHTML = "";
    langs.forEach((item) => {
      const optSrc = document.createElement("option");
      optSrc.value = item.code;
      optSrc.textContent = item.label;
      setTrSource.appendChild(optSrc);

      if (item.code !== "auto") {
        const optTgt = document.createElement("option");
        optTgt.value = item.code;
        optTgt.textContent = item.label;
        setTrTarget.appendChild(optTgt);
      }
    });
    if (prevSrc) setTrSource.value = prevSrc;
    if (prevTgt) setTrTarget.value = prevTgt;
  }

  function applyStrings(strings, translateLangs) {
    if (strings) {
      uiStrings = Object.assign({}, uiStrings, strings);
    }
    populateTranslateSelects(translateLangs);

    sidebar.setAttribute("aria-label", uiStrings.toc_label);
    filesTitle.textContent = uiStrings.files_header;
    btnFilesAdd.title = uiStrings.files_add_title;
    btnSettingsLabel.textContent = uiStrings.btn_settings_label;
    btnSettings.title = uiStrings.btn_settings_title;

    welcomeSub.innerHTML = uiStrings.welcome_sub;
    btnWelcomeOpen.textContent = uiStrings.welcome_open;
    recentLabel.textContent = uiStrings.recent_title;
    hintOpen.textContent = uiStrings.hint_open;
    hintZoom.textContent = uiStrings.hint_zoom;
    hintTheme.textContent = uiStrings.hint_theme;
    hintSettings.textContent = uiStrings.hint_settings;

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

    setText("settings-title", uiStrings.settings_title);
    setText("tab-btn-reading", uiStrings.tab_reading);
    setText("tab-btn-translate", uiStrings.tab_translate);
    setText("tab-btn-shortcuts", uiStrings.tab_shortcuts);
    setText("tab-btn-about", uiStrings.tab_about);

    setText("sec-palette", uiStrings.sec_palette);
    setText("lbl-theme-warm-dark", uiStrings["theme_warm-dark"]);
    setText("lbl-theme-sepia", uiStrings.theme_sepia);
    setText("lbl-theme-soft-light", uiStrings["theme_soft-light"]);
    setText("sec-text-size", uiStrings.sec_text_size);
    setText("sec-interface-lang", uiStrings.sec_interface_lang);
    setText("opt-lang-auto", uiStrings.lang_auto);
    setText("opt-lang-en", uiStrings.lang_en);
    setText("opt-lang-es", uiStrings.lang_es);

    setText("sec-behavior", uiStrings.sec_behavior);
    setText("opt-sidebar", uiStrings.opt_sidebar);
    setText("opt-sidebar-desc", uiStrings.opt_sidebar_desc);
    setText("opt-progress", uiStrings.opt_progress);
    setText("opt-progress-desc", uiStrings.opt_progress_desc);
    setText("opt-autoreload", uiStrings.opt_autoreload);
    setText("opt-autoreload-desc", uiStrings.opt_autoreload_desc);
    setText("opt-restore-session", uiStrings.opt_restore_session);
    setText("opt-restore-session-desc", uiStrings.opt_restore_session_desc);

    setText("sec-quick-actions", uiStrings.sec_quick_actions);
    setText("qa-open-lbl", uiStrings.act_open_file);
    setText("qa-find-lbl", uiStrings.act_find);
    setText("qa-fullscreen-lbl", uiStrings.act_fullscreen);
    setText("qa-reload-lbl", uiStrings.act_reload);

    setText("sec-translate-toggle", uiStrings.sec_translate_toggle);
    setText("opt-translate-enabled", uiStrings.opt_translate_enabled);
    setText("opt-translate-desc", uiStrings.opt_translate_desc);
    setText("sec-translate-presets", uiStrings.sec_translate_presets);
    setText("sec-translate-pair", uiStrings.sec_translate_pair);
    setText("lbl-translate-source", uiStrings.lbl_translate_source);
    setText("lbl-translate-target", uiStrings.lbl_translate_target);
    btnTrSwap.title = uiStrings.btn_swap_langs;
    setText("translate-privacy-note", uiStrings.translate_privacy_note);

    setText("sec-shortcuts-desc", uiStrings.sec_shortcuts_desc);
    btnResetShortcuts.textContent = uiStrings.btn_reset_shortcuts;

    setText("about-tagline", uiStrings.about_tagline);
    setText("about-credits-title", uiStrings.about_credits_title);
    setText("about-author", uiStrings.about_author);
    setText("about-font", uiStrings.about_font);
    setText("about-engine", uiStrings.about_engine);
    setText("about-contribute-title", uiStrings.about_contribute_title);
    setText("about-contribute-body", uiStrings.about_contribute_body);
    lnkRepo.textContent = uiStrings.btn_github_repo;
    lnkIssues.textContent = uiStrings.btn_report_issue;
    lnkContribute.textContent = uiStrings.btn_contribute;

    refreshThemeTooltip();
    refreshFullscreenButton();
    renderFilesList();
    renderShortcutsList();
  }

  function updateSidebarVisibility() {
    sidebar.classList.toggle("sidebar-hidden", !state.sidebarWanted);
    tocSection.classList.toggle("hidden", !state.hasDoc || state.tocCount < 2);
  }

  function updateQuickActionBadges() {
    const sc = state.shortcuts || {};
    setText("qa-open-kbd", sc.open_file || "—");
    setText("qa-find-kbd", sc.find || "—");
    setText("qa-fullscreen-kbd", sc.fullscreen || "—");
    setText("qa-reload-kbd", sc.reload || "—");
  }

  function applySettings(cfg) {
    if (!cfg) return;
    if (typeof cfg.font_size === "number") {
      document.documentElement.style.setProperty("--font-size", cfg.font_size + "px");
      btnFontReset.textContent = String(cfg.font_size);
      setFontValue.textContent = cfg.font_size + " px";
    }
    if (cfg.theme) {
      currentTheme = cfg.theme;
      document.documentElement.setAttribute("data-theme", cfg.theme);
      themeCards.forEach((card) => {
        card.classList.toggle("active", card.getAttribute("data-theme-choice") === cfg.theme);
      });
      refreshThemeTooltip();
    }
    if (cfg.language) {
      setLanguage.value = cfg.language;
    }
    if (typeof cfg.sidebar_visible === "boolean") {
      state.sidebarWanted = cfg.sidebar_visible;
      chkSidebar.checked = cfg.sidebar_visible;
      updateSidebarVisibility();
    }
    if (typeof cfg.show_progress_bar === "boolean") {
      chkProgress.checked = cfg.show_progress_bar;
      progressBar.classList.toggle("progress-hidden", !cfg.show_progress_bar);
    }
    if (typeof cfg.auto_reload === "boolean") {
      chkAutoreload.checked = cfg.auto_reload;
    }
    if (typeof cfg.restore_session === "boolean") {
      chkRestore.checked = cfg.restore_session;
    }
    if (typeof cfg.translate_enabled === "boolean") {
      chkTranslate.checked = cfg.translate_enabled;
    }
    if (cfg.translate_source) {
      setTrSource.value = cfg.translate_source;
    }
    if (cfg.translate_target) {
      setTrTarget.value = cfg.translate_target;
    }
    if (cfg.shortcuts && typeof cfg.shortcuts === "object") {
      state.shortcuts = cfg.shortcuts;
      updateQuickActionBadges();
      renderShortcutsList();
    }
  }

  function renderFilesList() {
    filesList.innerHTML = "";
    if (!Array.isArray(state.openFiles) || state.openFiles.length === 0) {
      const empty = document.createElement("div");
      empty.className = "files-empty";
      empty.textContent = uiStrings.files_empty;
      filesList.appendChild(empty);
      return;
    }

    const groups = new Map();
    state.openFiles.forEach((fullPath) => {
      const sep = fullPath.lastIndexOf("/");
      const dirPath = sep > 0 ? fullPath.slice(0, sep) : "/";
      if (!groups.has(dirPath)) {
        groups.set(dirPath, []);
      }
      groups.get(dirPath).push(fullPath);
    });

    const frag = document.createDocumentFragment();
    groups.forEach((paths, dirPath) => {
      const folderGroup = document.createElement("div");
      folderGroup.className = "folder-group";
      if (state.collapsedFolders.has(dirPath)) {
        folderGroup.classList.add("collapsed");
      }

      const folderParts = dirPath.split("/").filter(Boolean);
      const folderLabel = folderParts.length > 0 ? folderParts[folderParts.length - 1] : "/";

      const headerBtn = document.createElement("button");
      headerBtn.type = "button";
      headerBtn.className = "folder-header";
      headerBtn.title = dirPath;

      const chev = document.createElement("span");
      chev.className = "folder-chevron";
      chev.textContent = "▾";

      const nameSpan = document.createElement("span");
      nameSpan.className = "folder-name";
      nameSpan.textContent = folderLabel;

      const countSpan = document.createElement("span");
      countSpan.className = "folder-count";
      countSpan.textContent = String(paths.length);

      headerBtn.appendChild(chev);
      headerBtn.appendChild(nameSpan);
      headerBtn.appendChild(countSpan);
      headerBtn.addEventListener("click", () => {
        const nowCollapsed = folderGroup.classList.toggle("collapsed");
        if (nowCollapsed) {
          state.collapsedFolders.add(dirPath);
        } else {
          state.collapsedFolders.delete(dirPath);
        }
        if (bridge) bridge.toggleFolderCollapsed(dirPath);
      });

      const listWrap = document.createElement("div");
      listWrap.className = "folder-files";

      paths.forEach((filePath) => {
        const item = document.createElement("div");
        item.className = "file-item";
        if (filePath === state.activeFile) {
          item.classList.add("active");
        }

        const sep = filePath.lastIndexOf("/");
        const fileName = sep >= 0 ? filePath.slice(sep + 1) : filePath;

        const openBtn = document.createElement("button");
        openBtn.type = "button";
        openBtn.className = "file-open-btn";
        openBtn.textContent = fileName;
        openBtn.title = filePath;
        openBtn.addEventListener("click", () => {
          if (state.currentPath && state.hasDoc) {
            scrollMemory.set(state.currentPath, scrollEl.scrollTop);
          }
          if (bridge) bridge.activateFile(filePath);
        });
        openBtn.addEventListener("auxclick", (e) => {
          if (e.button === 1) {
            e.preventDefault();
            scrollMemory.delete(filePath);
            if (bridge) bridge.closeFile(filePath);
          }
        });

        const closeBtn = document.createElement("button");
        closeBtn.type = "button";
        closeBtn.className = "file-close";
        closeBtn.textContent = "✕";
        closeBtn.title = uiStrings.files_close_title;
        closeBtn.setAttribute("aria-label", uiStrings.files_close_title);
        closeBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          scrollMemory.delete(filePath);
          if (bridge) bridge.closeFile(filePath);
        });

        item.appendChild(openBtn);
        item.appendChild(closeBtn);
        listWrap.appendChild(item);
      });

      folderGroup.appendChild(headerBtn);
      folderGroup.appendChild(listWrap);
      frag.appendChild(folderGroup);
    });

    filesList.appendChild(frag);
  }

  function updateSession(session) {
    if (!session) return;
    state.openFiles = Array.isArray(session.open_files) ? session.open_files : [];
    state.activeFile = session.active_file || "";
    state.collapsedFolders = new Set(Array.isArray(session.collapsed_folders) ? session.collapsed_folders : []);
    renderFilesList();
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
    tocDocTitle.textContent = docTitle || "Coconut";

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

    if (state.currentPath) {
      scrollMemory.set(state.currentPath, scrollEl.scrollTop);
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
    if (state.hasDoc && state.currentPath && state.currentPath !== doc.path) {
      scrollMemory.set(state.currentPath, scrollEl.scrollTop);
    }

    let ratio = 0;
    if (preserveScroll) {
      const maxScroll = scrollEl.scrollHeight - scrollEl.clientHeight;
      if (maxScroll > 0) ratio = scrollEl.scrollTop / maxScroll;
    }

    state.hasDoc = true;
    state.currentPath = doc.path || "";
    state.tocCount = Array.isArray(doc.toc) ? doc.toc.length : 0;

    welcomeEl.classList.add("hidden");
    contentEl.classList.remove("hidden");
    contentEl.innerHTML = doc.html || "";

    enhanceCodeBlocks();
    wireInternalAnchors();
    buildToc(doc.toc || [], doc.title || doc.filename || "Coconut");
    updateSidebarVisibility();

    requestAnimationFrame(() => {
      if (preserveScroll) {
        const newMax = scrollEl.scrollHeight - scrollEl.clientHeight;
        scrollEl.scrollTop = newMax > 0 ? Math.round(ratio * newMax) : 0;
      } else if (state.currentPath && scrollMemory.has(state.currentPath)) {
        scrollEl.scrollTop = scrollMemory.get(state.currentPath) || 0;
      } else {
        scrollEl.scrollTop = 0;
      }
      updateScrollState();
    });
  }

  function showWelcome(recentFiles) {
    state.hasDoc = false;
    state.currentPath = "";
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

  // Settings modal & shortcut recorder
  function switchTab(tabName) {
    tabBtns.forEach((btn) => {
      btn.classList.toggle("active", btn.getAttribute("data-tab") === tabName);
    });
    Object.keys(tabPanels).forEach((name) => {
      tabPanels[name].classList.toggle("hidden", name !== tabName);
    });
  }

  function stopShortcutRecording() {
    if (!recordingAction) return;
    recordingAction = null;
    if (bridge) bridge.setShortcutsEnabled(true);
    renderShortcutsList();
  }

  function openSettings(tabName) {
    if (tabName && tabPanels[tabName]) {
      switchTab(tabName);
    }
    settingsModal.classList.remove("hidden");
  }

  function closeSettings() {
    if (settingsModal.classList.contains("hidden")) return;
    stopShortcutRecording();
    settingsModal.classList.add("hidden");
    scrollEl.focus();
  }

  function normalizeKeyEvent(e) {
    const modifiers = new Set(["Control", "Shift", "Alt", "Meta", "AltGraph"]);
    if (modifiers.has(e.key)) return null;

    const parts = [];
    if (e.ctrlKey) parts.push("Ctrl");
    if (e.altKey) parts.push("Alt");
    if (e.shiftKey && e.key !== "+") parts.push("Shift");
    if (e.metaKey) parts.push("Meta");

    let key = e.key;
    const map = {
      ArrowLeft: "Left",
      ArrowRight: "Right",
      ArrowUp: "Up",
      ArrowDown: "Down",
      " ": "Space",
      Escape: "Esc",
      Enter: "Return",
    };
    if (map[key]) {
      key = map[key];
    } else if (key.length === 1) {
      key = key.toUpperCase();
    }

    if (parts.length === 0 && !/^F\d{1,2}$/.test(key)) {
      return null;
    }

    parts.push(key);
    return parts.join("+");
  }

  function renderShortcutsList() {
    if (!shortcutsListEl) return;
    shortcutsListEl.innerHTML = "";
    const frag = document.createDocumentFragment();

    SHORTCUT_ORDER.forEach((action) => {
      const row = document.createElement("div");
      row.className = "shortcut-row";

      const label = document.createElement("span");
      label.className = "shortcut-name";
      label.textContent = uiStrings["sc_" + action] || action;

      const controlsWrap = document.createElement("div");
      controlsWrap.className = "shortcut-controls";

      const keyBtn = document.createElement("button");
      keyBtn.type = "button";
      keyBtn.className = "shortcut-btn";
      const isRec = recordingAction === action;
      if (isRec) {
        keyBtn.classList.add("recording");
        keyBtn.textContent = uiStrings.shortcut_press;
      } else {
        const val = state.shortcuts[action] || "";
        keyBtn.textContent = val || uiStrings.shortcut_empty;
      }
      keyBtn.addEventListener("click", () => {
        if (recordingAction === action) {
          stopShortcutRecording();
          return;
        }
        recordingAction = action;
        if (bridge) bridge.setShortcutsEnabled(false);
        renderShortcutsList();
      });

      const clearBtn = document.createElement("button");
      clearBtn.type = "button";
      clearBtn.className = "shortcut-clear";
      clearBtn.textContent = uiStrings.btn_clear_shortcut;
      clearBtn.addEventListener("click", () => {
        stopShortcutRecording();
        if (bridge) bridge.setShortcut(action, "");
      });

      controlsWrap.appendChild(keyBtn);
      controlsWrap.appendChild(clearBtn);
      row.appendChild(label);
      row.appendChild(controlsWrap);
      frag.appendChild(row);
    });

    shortcutsListEl.appendChild(frag);
  }

  window.addEventListener(
    "keydown",
    (e) => {
      if (!recordingAction) return;
      e.preventDefault();
      e.stopPropagation();

      if (e.key === "Escape" && !e.ctrlKey && !e.altKey && !e.shiftKey && !e.metaKey) {
        stopShortcutRecording();
        return;
      }

      const combo = normalizeKeyEvent(e);
      if (!combo) return;

      const targetAction = recordingAction;
      recordingAction = null;
      if (bridge) {
        bridge.setShortcutsEnabled(true);
        bridge.setShortcut(targetAction, combo);
      }
    },
    true
  );

  // Top-right & sidebar buttons
  btnToc.addEventListener("click", () => {
    if (bridge) bridge.toggleSidebar();
  });
  btnOpen.addEventListener("click", () => {
    if (bridge) bridge.openFileDialog();
  });
  btnFilesAdd.addEventListener("click", () => {
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
  btnFullscreen.addEventListener("click", () => {
    if (bridge) bridge.toggleFullscreen();
  });
  btnSettings.addEventListener("click", () => {
    openSettings("reading");
  });

  // Settings modal wiring
  btnSettingsClose.addEventListener("click", closeSettings);
  settingsModal.addEventListener("click", (e) => {
    if (e.target === settingsModal) closeSettings();
  });
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      stopShortcutRecording();
      switchTab(btn.getAttribute("data-tab"));
    });
  });

  themeCards.forEach((card) => {
    card.addEventListener("click", () => {
      const choice = card.getAttribute("data-theme-choice");
      if (bridge && choice) bridge.setTheme(choice);
    });
  });

  setFontDec.addEventListener("click", () => {
    if (bridge) bridge.adjustFontSize(-1);
  });
  setFontInc.addEventListener("click", () => {
    if (bridge) bridge.adjustFontSize(1);
  });
  setFontReset.addEventListener("click", () => {
    if (bridge) bridge.resetFontSize();
  });
  setLanguage.addEventListener("change", () => {
    if (bridge) bridge.setLanguage(setLanguage.value);
  });

  chkSidebar.addEventListener("change", () => {
    if (bridge) bridge.setSettingBool("sidebar_visible", chkSidebar.checked);
  });
  chkProgress.addEventListener("change", () => {
    if (bridge) bridge.setSettingBool("show_progress_bar", chkProgress.checked);
  });
  chkAutoreload.addEventListener("change", () => {
    if (bridge) bridge.setSettingBool("auto_reload", chkAutoreload.checked);
  });
  chkRestore.addEventListener("change", () => {
    if (bridge) bridge.setSettingBool("restore_session", chkRestore.checked);
  });
  chkTranslate.addEventListener("change", () => {
    if (bridge) bridge.setSettingBool("translate_enabled", chkTranslate.checked);
  });

  qaOpen.addEventListener("click", () => {
    closeSettings();
    if (bridge) bridge.openFileDialog();
  });
  qaFind.addEventListener("click", () => {
    closeSettings();
    openFindBar();
  });
  qaFullscreen.addEventListener("click", () => {
    closeSettings();
    if (bridge) bridge.toggleFullscreen();
  });
  qaReload.addEventListener("click", () => {
    closeSettings();
    if (bridge) bridge.reloadCurrent();
  });

  setTrSource.addEventListener("change", () => {
    if (bridge) bridge.setTranslatePair(setTrSource.value, setTrTarget.value);
  });
  setTrTarget.addEventListener("change", () => {
    if (bridge) bridge.setTranslatePair(setTrSource.value, setTrTarget.value);
  });
  btnTrSwap.addEventListener("click", () => {
    const src = setTrSource.value;
    const tgt = setTrTarget.value;
    if (src === "auto") {
      showToast(uiStrings.lbl_translate_source + ": Auto");
      return;
    }
    if (bridge) bridge.setTranslatePair(tgt, src);
  });
  trPresets.forEach((btn) => {
    btn.addEventListener("click", () => {
      const pair = (btn.getAttribute("data-tr-preset") || "").split(":");
      if (pair.length === 2 && bridge) {
        bridge.setTranslatePair(pair[0], pair[1]);
      }
    });
  });

  btnResetShortcuts.addEventListener("click", () => {
    stopShortcutRecording();
    if (bridge) bridge.resetShortcuts();
  });

  lnkRepo.addEventListener("click", () => {
    if (bridge) bridge.openExternalUrl("https://github.com/Rhazieh/coconut");
  });
  lnkIssues.addEventListener("click", () => {
    if (bridge) bridge.openExternalUrl("https://github.com/Rhazieh/coconut/issues");
  });
  lnkContribute.addEventListener("click", () => {
    if (bridge) bridge.openExternalUrl("https://github.com/Rhazieh/coconut/blob/main/CONTRIBUTING.md");
  });

  // Find bar wiring
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

  // Scrollspy & progress bar
  scrollEl.addEventListener("scroll", () => {
    if (!scrollRaf) {
      scrollRaf = true;
      requestAnimationFrame(updateScrollState);
    }
  });

  // Ctrl+Wheel font zoom
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

  // Gentle reading keyboard shortcuts
  window.addEventListener("keydown", (e) => {
    if (recordingAction) return;
    if (e.key === "Escape") {
      if (!settingsModal.classList.contains("hidden")) {
        e.preventDefault();
        closeSettings();
        return;
      }
      if (!findBar.classList.contains("hidden")) {
        e.preventDefault();
        closeFindBar();
        return;
      }
    }
    if (!settingsModal.classList.contains("hidden")) return;
    if (document.activeElement === findInput) return;
    if (e.ctrlKey || e.altKey || e.metaKey) return;

    if (e.key === "j") {
      scrollEl.scrollBy({ top: 96, behavior: "smooth" });
    } else if (e.key === "k") {
      scrollEl.scrollBy({ top: -96, behavior: "smooth" });
    }
  });

  // Drag-over visual indicator only (Qt eventFilter handles actual drop)
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

  window.Coconut = {
    applyStrings,
    applySettings,
    updateSession,
    setFullscreenState,
    openSettings,
    closeSettings,
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
