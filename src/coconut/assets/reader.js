(function () {
  "use strict";

  const SHORTCUT_ORDER = [
    "open_file",
    "open_folder",
    "new_file",
    "toggle_edit",
    "save_file",
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
  let extCategoryFilter = "all";
  let extSearchQuery = "";

  const scrollMemory = new Map();
  // Map of filePath (or "__untitled__") -> { text, originalText, dirty, filename, isCode }
  const editBuffers = new Map();

  let uiStrings = {
    toc_label: "Outline",
    files_header: "Open files",
    files_add_title: "Add file…",
    files_new_title: "New file (Ctrl+N)",
    files_close_title: "Close file",
    files_empty: "No open files",
    btn_settings_label: "Settings",
    btn_settings_title: "Settings (Ctrl+,)",
    welcome_sub: "Drop files here, open them from disk, or start a new note.",
    welcome_open: "Open files…",
    welcome_new: "New file",
    recent_title: "Recent",
    hint_open: "Ctrl+O Open",
    hint_edit: "Ctrl+E Edit",
    hint_zoom: "Ctrl+/− Text",
    hint_theme: "Ctrl+T Palette",
    hint_settings: "Ctrl+, Settings",
    btn_toc_title: "Outline & files (Ctrl+B)",
    btn_open_title: "Open files (Ctrl+O)",
    btn_new_title: "New file (Ctrl+N)",
    btn_edit_title: "Edit mode (Ctrl+E)",
    btn_view_title: "Reading mode (Ctrl+E)",
    btn_edit_label: "Edit",
    btn_view_label: "Read",
    btn_save_title: "Save file (Ctrl+S)",
    btn_save_label: "Save",
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
    toast_epub_readonly: "EPUB books are read-only",
    "theme_warm-dark": "Warm Night",
    "theme_sepia": "Paper Sepia",
    "theme_soft-light": "Soft Stone",
    untitled_filename: "Untitled.md",
    editor_unsaved: "Unsaved changes",
    editor_saved: "Saved",
    editor_placeholder: "Write Markdown, notes, or code here… (Ctrl+S to save, Ctrl+E to return to reading mode)",
    editor_stats: "{lines} lines · {words} words",
    settings_title: "Settings",
    tab_reading: "Reading",
    tab_translate: "Translate",
    tab_shortcuts: "Shortcuts",
    tab_about: "About",
    sec_palette: "Color palette",
    sec_accent_color: "Accent color",
    accent_default: "Default",
    accent_amber: "Amber",
    accent_sage: "Sage",
    accent_ocean: "Ocean",
    accent_berry: "Berry",
    accent_lavender: "Lavender",
    sec_text_size: "Text size",
    sec_reading_width: "Reading width",
    width_narrow: "Narrow",
    width_medium: "Medium",
    width_wide: "Wide",
    sec_line_height: "Line spacing",
    lh_compact: "Compact",
    lh_comfortable: "Comfortable",
    lh_spacious: "Spacious",
    sec_code_style: "Code block style",
    cstyle_card: "Card",
    cstyle_minimal: "Minimal",
    cstyle_contrast: "Contrast",
    sec_interface_lang: "Interface language",
    lang_auto: "Automatic (System)",
    lang_en: "English",
    lang_es: "Español",
    sec_behavior: "Reader toggles",
    opt_sidebar: "Show outline & open files sidebar",
    opt_sidebar_desc: "Keep the left navigation panel visible while reading.",
    opt_progress: "Show reading progress hairline",
    opt_progress_desc: "Display a subtle 2 px progress indicator at the top edge.",
    opt_line_numbers: "Show line numbers in code",
    opt_line_numbers_desc: "Display line numbering inside code files and syntax-highlighted blocks.",
    opt_autoreload: "Auto-reload when file changes on disk",
    opt_autoreload_desc: "Refresh silently while preserving your scroll position (paused while editing).",
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
    about_tagline: "Minimalist, local-first, eye-comfort Markdown & code reader for Linux (Wayland & X11).",
    about_credits_title: "Credits & Open Source Licenses",
    about_author: "Created by Maximiliano Cano (Rhazieh) — MIT License.",
    about_font: "Typography: Atkinson Hyperlegible Next (Braille Institute) — SIL OFL 1.1.",
    about_engine: "Rendering: libcmark-gfm / python-markdown + local syntax highlighter & EPUB engine.",
    about_contribute_title: "How to contribute",
    about_contribute_body: "Coconut stays local-first, offline, and distraction-free. You can report bugs, suggest ergonomic improvements, or open pull requests on GitHub.",
    btn_github_repo: "GitHub Repository",
    btn_report_issue: "Report Issue",
    btn_contribute: "Contributing Guide",
    btn_extensions_label: "Extensions",
    btn_extensions_title: "Extensions",
    ext_modal_title: "Extensions",
    ext_tab_languages: "Languages & Formats",
    ext_empty_title: "No matching extensions",
    ext_empty_desc: "Try a different filter or search term.",
    ext_subtitle: "Enable lightweight local modules on demand. Active extensions update file dialogs and drag-and-drop filters.",
    ext_search_placeholder: "Filter formats (.py, .epub, .ts, .sql…)",
    ext_cat_all: "All",
    ext_cat_document: "Documents & Books",
    ext_cat_code: "Code & IT",
    ext_btn_add: "Add",
    ext_btn_remove: "Remove",
    ext_btn_add_all: "Add all",
    ext_btn_remove_all: "Remove all",
    ext_status_active: "Active",
  };

  const state = {
    hasDoc: false,
    currentPath: "",
    currentFilename: "",
    currentLanguage: "",
    rawText: "",
    editable: true,
    isEpub: false,
    isCode: false,
    isEditing: false,
    isDirty: false,
    tocCount: 0,
    sidebarWanted: true,
    tocElements: [],
    tocButtons: new Map(),
    activeId: null,
    openFiles: [],
    openFolders: [],
    folderTrees: [],
    activeFile: "",
    collapsedFolders: new Set(),
    recentFiles: [],
    shortcuts: {},
    extensionsCatalog: [],
  };

  let sidebarDragState = null;

  const progressBar = document.getElementById("progress-bar");
  const sidebar = document.getElementById("toc-sidebar");
  const sidebarResizer = document.getElementById("sidebar-resizer");
  const tocSection = document.getElementById("toc-section");
  const tocDocTitle = document.getElementById("toc-doc-title");
  const tocList = document.getElementById("toc-list");
  const filesTitle = document.getElementById("files-title");
  const btnFilesNew = document.getElementById("btn-files-new");
  const btnFilesFolder = document.getElementById("btn-files-folder");
  const btnFilesAdd = document.getElementById("btn-files-add");
  const btnFilesCollapse = document.getElementById("btn-files-collapse");
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

  const editorView = document.getElementById("editor-view");
  const editorDirtyDot = document.getElementById("editor-dirty-dot");
  const editorFilename = document.getElementById("editor-filename");
  const editorStatusBadge = document.getElementById("editor-status-badge");
  const editorStats = document.getElementById("editor-stats");
  const btnEditorSave = document.getElementById("btn-editor-save");
  const btnEditorDone = document.getElementById("btn-editor-done");
  const editorGutter = document.getElementById("editor-gutter");
  const editorBackdropCode = document.getElementById("editor-backdrop-code");
  const editorTextarea = document.getElementById("editor-textarea");

  const hintOpen = document.getElementById("hint-open");
  const hintEdit = document.getElementById("hint-edit");
  const hintZoom = document.getElementById("hint-zoom");
  const hintTheme = document.getElementById("hint-theme");
  const hintSettings = document.getElementById("hint-settings");

  const btnToc = document.getElementById("btn-toc");
  const btnOpen = document.getElementById("btn-open");
  const btnNewFile = document.getElementById("btn-new-file");
  const btnEditMode = document.getElementById("btn-edit-mode");
  const btnEditLabel = document.getElementById("btn-edit-label");
  const btnSaveFile = document.getElementById("btn-save-file");
  const btnSaveLabel = document.getElementById("btn-save-label");
  const btnWelcomeOpen = document.getElementById("btn-welcome-open");
  const btnWelcomeFolder = document.getElementById("btn-welcome-folder");
  const btnWelcomeNew = document.getElementById("btn-welcome-new");
  const btnFontDec = document.getElementById("btn-font-dec");
  const btnFontReset = document.getElementById("font-size-value");
  const btnFontInc = document.getElementById("btn-font-inc");
  const btnTheme = document.getElementById("btn-theme");
  const btnFullscreen = document.getElementById("btn-fullscreen");
  const iconFsEnter = btnFullscreen.querySelector(".icon-enter");
  const iconFsExit = btnFullscreen.querySelector(".icon-exit");
  const extensionsPill = document.getElementById("extensions-pill");
  const btnExtensionsLabel = document.getElementById("btn-extensions-label");
  const extCountBadge = document.getElementById("ext-count-badge");
  const extensionsModal = document.getElementById("extensions-modal");
  const btnExtClose = document.getElementById("btn-ext-close");
  const extSearchInput = document.getElementById("ext-search-input");
  const extCatBtns = Array.from(document.querySelectorAll("[data-ext-cat]"));
  const btnExtAddAll = document.getElementById("btn-ext-add-all");
  const btnExtRemoveAll = document.getElementById("btn-ext-remove-all");
  const extensionsListEl = document.getElementById("extensions-list");
  const extEmptyState = document.getElementById("ext-empty-state");

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
  const tabBtns = Array.from(document.querySelectorAll("#settings-modal .modal-tab"));
  const tabPanels = {
    reading: document.getElementById("panel-reading"),
    translate: document.getElementById("panel-translate"),
    shortcuts: document.getElementById("panel-shortcuts"),
    about: document.getElementById("panel-about"),
  };

  const themeCards = Array.from(document.querySelectorAll(".theme-card"));
  const accentPills = Array.from(document.querySelectorAll("[data-accent-choice]"));
  const widthBtns = Array.from(document.querySelectorAll("[data-width-choice]"));
  const lhBtns = Array.from(document.querySelectorAll("[data-lh-choice]"));
  const cstyleBtns = Array.from(document.querySelectorAll("[data-cstyle-choice]"));
  const setFontDec = document.getElementById("set-font-dec");
  const setFontValue = document.getElementById("set-font-value");
  const setFontInc = document.getElementById("set-font-inc");
  const setFontReset = document.getElementById("set-font-reset");
  const setLanguage = document.getElementById("set-language");

  const chkSidebar = document.getElementById("chk-sidebar");
  const chkProgress = document.getElementById("chk-progress");
  const chkLineNumbers = document.getElementById("chk-line-numbers");
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
    }, 1350);
  }

  function bufferKey() {
    return state.currentPath || "__untitled__";
  }

  function isPathDirty(path) {
    const entry = editBuffers.get(path);
    return Boolean(entry && entry.dirty);
  }

  function syncEditControlsUI() {
    btnEditMode.classList.toggle("active", state.isEditing);
    btnEditMode.setAttribute("aria-pressed", state.isEditing ? "true" : "false");
    btnEditMode.title = state.isEditing ? uiStrings.btn_view_title : uiStrings.btn_edit_title;
    btnEditLabel.textContent = state.isEditing ? uiStrings.btn_view_label : uiStrings.btn_edit_label;

    const showSave = state.isEditing || state.isDirty;
    btnSaveFile.classList.toggle("hidden", !showSave);
    btnSaveFile.classList.toggle("dirty", state.isDirty);
    btnSaveFile.title = uiStrings.btn_save_title;
    btnSaveLabel.textContent = uiStrings.btn_save_label;

    if (editorDirtyDot) {
      editorDirtyDot.classList.toggle("hidden", !state.isDirty);
    }
    if (editorFilename) {
      editorFilename.textContent = state.currentFilename || uiStrings.untitled_filename;
    }
    if (editorStatusBadge) {
      editorStatusBadge.textContent = state.isDirty ? uiStrings.editor_unsaved : uiStrings.editor_saved;
      editorStatusBadge.classList.toggle("dirty", state.isDirty);
    }
    if (btnEditorSave) {
      btnEditorSave.textContent = uiStrings.btn_save_label;
      btnEditorSave.classList.toggle("dirty", state.isDirty);
    }
    if (btnEditorDone) {
      btnEditorDone.textContent = uiStrings.btn_view_label;
    }

    updateEditorStats();
    renderFilesList();
    if (bridge && typeof bridge.setEditState === "function") {
      bridge.setEditState(state.isEditing, state.isDirty);
    }
  }

  function updateEditorStats() {
    if (!editorStats) return;
    const text = editorTextarea ? editorTextarea.value : state.rawText || "";
    const lines = text ? text.split("\n").length : 1;
    const trimmed = text.trim();
    const words = trimmed ? trimmed.split(/\s+/).length : 0;
    const tpl = uiStrings.editor_stats || "{lines} lines · {words} words";
    editorStats.textContent = tpl.replace("{lines}", String(lines)).replace("{words}", String(words));
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
    if (btnFilesNew) btnFilesNew.title = uiStrings.files_new_title;
    if (btnFilesFolder) btnFilesFolder.title = uiStrings.files_open_folder_title || "Open folder… (Ctrl+Shift+O)";
    if (btnFilesCollapse) btnFilesCollapse.title = uiStrings.files_collapse_all_title || "Collapse all folders";
    btnSettingsLabel.textContent = uiStrings.btn_settings_label;
    btnSettings.title = uiStrings.btn_settings_title;

    welcomeSub.innerHTML = uiStrings.welcome_sub;
    btnWelcomeOpen.textContent = uiStrings.welcome_open;
    if (btnWelcomeFolder) btnWelcomeFolder.textContent = uiStrings.welcome_open_folder || "Open folder…";
    if (btnWelcomeNew) btnWelcomeNew.textContent = uiStrings.welcome_new;
    recentLabel.textContent = uiStrings.recent_title;
    hintOpen.textContent = uiStrings.hint_open;
    if (hintEdit) hintEdit.textContent = uiStrings.hint_edit;
    hintZoom.textContent = uiStrings.hint_zoom;
    hintTheme.textContent = uiStrings.hint_theme;
    hintSettings.textContent = uiStrings.hint_settings;

    btnToc.title = uiStrings.btn_toc_title;
    btnOpen.title = uiStrings.btn_open_title;
    if (btnNewFile) btnNewFile.title = uiStrings.btn_new_title;
    btnFontDec.title = uiStrings.btn_dec_title;
    btnFontReset.title = uiStrings.btn_reset_title;
    btnFontInc.title = uiStrings.btn_inc_title;
    findInput.placeholder = uiStrings.find_placeholder;
    findPrev.title = uiStrings.find_prev_title;
    findNext.title = uiStrings.find_next_title;
    findClose.title = uiStrings.find_close_title;
    dropBox.textContent = uiStrings.drop_prompt;
    if (editorTextarea) editorTextarea.placeholder = uiStrings.editor_placeholder;

    setText("settings-title", uiStrings.settings_title);
    setText("tab-btn-reading", uiStrings.tab_reading);
    setText("tab-btn-translate", uiStrings.tab_translate);
    setText("tab-btn-shortcuts", uiStrings.tab_shortcuts);
    setText("tab-btn-about", uiStrings.tab_about);

    setText("sec-palette", uiStrings.sec_palette);
    setText("lbl-theme-warm-dark", uiStrings["theme_warm-dark"]);
    setText("lbl-theme-sepia", uiStrings.theme_sepia);
    setText("lbl-theme-soft-light", uiStrings["theme_soft-light"]);

    setText("sec-accent-color", uiStrings.sec_accent_color);
    setText("lbl-accent-default", uiStrings.accent_default);
    setText("lbl-accent-amber", uiStrings.accent_amber);
    setText("lbl-accent-sage", uiStrings.accent_sage);
    setText("lbl-accent-ocean", uiStrings.accent_ocean);
    setText("lbl-accent-berry", uiStrings.accent_berry);
    setText("lbl-accent-lavender", uiStrings.accent_lavender);

    setText("sec-text-size", uiStrings.sec_text_size);
    setText("sec-reading-width", uiStrings.sec_reading_width);
    setText("lbl-width-narrow", uiStrings.width_narrow);
    setText("lbl-width-medium", uiStrings.width_medium);
    setText("lbl-width-wide", uiStrings.width_wide);

    setText("sec-line-height", uiStrings.sec_line_height);
    setText("lbl-lh-compact", uiStrings.lh_compact);
    setText("lbl-lh-comfortable", uiStrings.lh_comfortable);
    setText("lbl-lh-spacious", uiStrings.lh_spacious);

    setText("sec-code-style", uiStrings.sec_code_style);
    setText("lbl-cstyle-card", uiStrings.cstyle_card);
    setText("lbl-cstyle-minimal", uiStrings.cstyle_minimal);
    setText("lbl-cstyle-contrast", uiStrings.cstyle_contrast);

    setText("sec-interface-lang", uiStrings.sec_interface_lang);
    setText("opt-lang-auto", uiStrings.lang_auto);
    setText("opt-lang-en", uiStrings.lang_en);
    setText("opt-lang-es", uiStrings.lang_es);

    setText("sec-behavior", uiStrings.sec_behavior);
    setText("opt-sidebar", uiStrings.opt_sidebar);
    setText("opt-sidebar-desc", uiStrings.opt_sidebar_desc);
    setText("opt-progress", uiStrings.opt_progress);
    setText("opt-progress-desc", uiStrings.opt_progress_desc);
    setText("opt-line-numbers", uiStrings.opt_line_numbers);
    setText("opt-line-numbers-desc", uiStrings.opt_line_numbers_desc);
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

    btnExtensionsLabel.textContent = uiStrings.btn_extensions_label;
    extensionsPill.title = uiStrings.btn_extensions_title;
    setText("ext-modal-title", uiStrings.ext_modal_title);
    setText("ext-tab-languages", uiStrings.ext_tab_languages);
    setText("ext-subtitle", uiStrings.ext_subtitle);
    if (extSearchInput) extSearchInput.placeholder = uiStrings.ext_search_placeholder;
    setText("ext-cat-all", uiStrings.ext_cat_all);
    setText("ext-cat-document", uiStrings.ext_cat_document);
    setText("ext-cat-code", uiStrings.ext_cat_code);
    if (btnExtAddAll) btnExtAddAll.textContent = uiStrings.ext_btn_add_all;
    if (btnExtRemoveAll) btnExtRemoveAll.textContent = uiStrings.ext_btn_remove_all;
    setText("ext-empty-title", uiStrings.ext_empty_title);
    setText("ext-empty-desc", uiStrings.ext_empty_desc);

    refreshThemeTooltip();
    refreshFullscreenButton();
    syncEditControlsUI();
    renderShortcutsList();
    renderExtensionsCatalog();
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
    if (cfg.reading_width) {
      document.documentElement.setAttribute("data-reading-width", cfg.reading_width);
      widthBtns.forEach((btn) => {
        btn.classList.toggle("active", btn.getAttribute("data-width-choice") === cfg.reading_width);
      });
    }
    if (cfg.line_height) {
      document.documentElement.setAttribute("data-line-height", cfg.line_height);
      lhBtns.forEach((btn) => {
        btn.classList.toggle("active", btn.getAttribute("data-lh-choice") === cfg.line_height);
      });
    }
    if (cfg.accent_color) {
      document.documentElement.setAttribute("data-accent", cfg.accent_color);
      accentPills.forEach((pill) => {
        pill.classList.toggle("active", pill.getAttribute("data-accent-choice") === cfg.accent_color);
      });
    }
    if (cfg.code_style) {
      document.documentElement.setAttribute("data-code-style", cfg.code_style);
      cstyleBtns.forEach((btn) => {
        btn.classList.toggle("active", btn.getAttribute("data-cstyle-choice") === cfg.code_style);
      });
    }
    if (typeof cfg.show_line_numbers === "boolean") {
      document.documentElement.setAttribute("data-line-numbers", cfg.show_line_numbers ? "true" : "false");
      if (chkLineNumbers) chkLineNumbers.checked = cfg.show_line_numbers;
    }
    if (cfg.language) {
      setLanguage.value = cfg.language;
    }
    if (typeof cfg.sidebar_visible === "boolean") {
      state.sidebarWanted = cfg.sidebar_visible;
      chkSidebar.checked = cfg.sidebar_visible;
      updateSidebarVisibility();
    }
    if (typeof cfg.sidebar_width === "number" && cfg.sidebar_width >= 180) {
      document.documentElement.style.setProperty("--sidebar-width", cfg.sidebar_width + "px");
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
    if (Array.isArray(cfg.extensions_catalog)) {
      state.extensionsCatalog = cfg.extensions_catalog;
      renderExtensionsCatalog();
    }
  }

  function renderExtensionsCatalog() {
    if (!extensionsListEl) return;
    const catalog = Array.isArray(state.extensionsCatalog) ? state.extensionsCatalog : [];
    const activeCount = catalog.filter((item) => item.enabled).length;
    if (extCountBadge) {
      extCountBadge.textContent = String(activeCount);
    }

    const q = extSearchQuery.trim().toLowerCase();
    const filtered = catalog.filter((item) => {
      if (extCategoryFilter !== "all" && item.category !== extCategoryFilter) {
        return false;
      }
      if (!q) return true;
      const hay = (
        (item.id || "") +
        " " +
        (item.name || "") +
        " " +
        (item.badge || "") +
        " " +
        (item.description || "") +
        " " +
        (Array.isArray(item.extensions) ? item.extensions.join(" ") : "")
      ).toLowerCase();
      return hay.indexOf(q) !== -1;
    });

    extensionsListEl.innerHTML = "";
    if (filtered.length === 0) {
      extensionsListEl.classList.add("hidden");
      if (extEmptyState) extEmptyState.classList.remove("hidden");
      return;
    }

    extensionsListEl.classList.remove("hidden");
    if (extEmptyState) extEmptyState.classList.add("hidden");

    const frag = document.createDocumentFragment();
    filtered.forEach((item) => {
      const card = document.createElement("div");
      card.className = "ext-card" + (item.enabled ? " ext-enabled" : "");
      card.setAttribute("data-ext-id", item.id);

      const topRow = document.createElement("div");
      topRow.className = "ext-card-top";

      const titleWrap = document.createElement("div");
      titleWrap.className = "ext-title-wrap";

      const badge = document.createElement("span");
      badge.className = "ext-badge";
      badge.textContent = item.badge || item.id;

      const nameEl = document.createElement("span");
      nameEl.className = "ext-name";
      nameEl.textContent = item.name || item.id;

      titleWrap.appendChild(badge);
      titleWrap.appendChild(nameEl);

      const actionBtn = document.createElement("button");
      actionBtn.type = "button";
      actionBtn.className = "ext-action-btn" + (item.enabled ? " remove-mode" : "");
      actionBtn.textContent = item.enabled ? uiStrings.ext_btn_remove : uiStrings.ext_btn_add;
      actionBtn.setAttribute("data-ext-toggle", item.id);
      actionBtn.addEventListener("click", () => {
        const nextState = !item.enabled;
        item.enabled = nextState;
        renderExtensionsCatalog();
        if (bridge && typeof bridge.toggleExtension === "function") {
          bridge.toggleExtension(item.id, nextState);
        }
      });

      topRow.appendChild(titleWrap);
      topRow.appendChild(actionBtn);

      const desc = document.createElement("p");
      desc.className = "ext-desc";
      desc.textContent = item.description || "";

      card.appendChild(topRow);
      card.appendChild(desc);
      frag.appendChild(card);
    });

    extensionsListEl.appendChild(frag);
  }

  function reorderArray(arr, fromPath, targetPath, insertAfter) {
    const next = arr.slice();
    const fromIdx = next.indexOf(fromPath);
    if (fromIdx === -1 || fromPath === targetPath) return null;
    next.splice(fromIdx, 1);
    let toIdx = next.indexOf(targetPath);
    if (toIdx === -1) {
      next.push(fromPath);
    } else {
      if (insertAfter) toIdx += 1;
      next.splice(toIdx, 0, fromPath);
    }
    return next;
  }

  function clearDragClasses() {
    filesList
      .querySelectorAll(".drag-over-before, .drag-over-after, .dragging")
      .forEach((el) => el.classList.remove("drag-over-before", "drag-over-after", "dragging"));
  }

  function attachReorderHandlers(el, scopeKey, itemPath, onCommitOrder, getSiblings) {
    el.setAttribute("draggable", "true");
    el.addEventListener("dragstart", (e) => {
      e.stopPropagation();
      sidebarDragState = { scopeKey, itemPath };
      el.classList.add("dragging");
      if (e.dataTransfer) {
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", itemPath);
      }
    });
    el.addEventListener("dragend", () => {
      sidebarDragState = null;
      clearDragClasses();
    });
    el.addEventListener("dragover", (e) => {
      if (!sidebarDragState || sidebarDragState.scopeKey !== scopeKey || sidebarDragState.itemPath === itemPath) {
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      const rect = el.getBoundingClientRect();
      const after = e.clientY > rect.top + rect.height / 2;
      el.classList.toggle("drag-over-before", !after);
      el.classList.toggle("drag-over-after", after);
    });
    el.addEventListener("dragleave", () => {
      el.classList.remove("drag-over-before", "drag-over-after");
    });
    el.addEventListener("drop", (e) => {
      if (!sidebarDragState || sidebarDragState.scopeKey !== scopeKey) return;
      e.preventDefault();
      e.stopPropagation();
      const rect = el.getBoundingClientRect();
      const after = e.clientY > rect.top + rect.height / 2;
      const fromPath = sidebarDragState.itemPath;
      sidebarDragState = null;
      clearDragClasses();
      const siblings = getSiblings();
      const reordered = reorderArray(siblings, fromPath, itemPath, after);
      if (reordered) {
        onCommitOrder(reordered);
      }
    });
  }

  function collectTreeFilePaths(node, outSet) {
    if (!node) return;
    if (node.type === "file" && node.path) {
      outSet.add(node.path);
      return;
    }
    if (Array.isArray(node.children)) {
      node.children.forEach((child) => collectTreeFilePaths(child, outSet));
    }
  }

  function collectTreeDirPaths(node, outList) {
    if (!node || node.type !== "dir") return;
    if (node.path) outList.push(node.path);
    if (Array.isArray(node.children)) {
      node.children.forEach((child) => collectTreeDirPaths(child, outList));
    }
  }

  function createFileRowElement(filePath, fileName, showCloseBtn) {
    const item = document.createElement("div");
    item.className = "file-item";
    if (filePath === state.activeFile) {
      item.classList.add("active");
    }

    const openBtn = document.createElement("button");
    openBtn.type = "button";
    openBtn.className = "file-open-btn";
    openBtn.title = filePath;

    if (isPathDirty(filePath)) {
      const dot = document.createElement("span");
      dot.className = "file-dirty-dot";
      dot.textContent = "●";
      openBtn.appendChild(dot);
    }
    openBtn.appendChild(document.createTextNode(fileName));

    openBtn.addEventListener("click", () => {
      if (state.currentPath && state.hasDoc) {
        scrollMemory.set(state.currentPath, scrollEl.scrollTop);
      }
      if (bridge) bridge.activateFile(filePath);
    });
    openBtn.addEventListener("auxclick", (e) => {
      if (e.button === 1 && showCloseBtn) {
        e.preventDefault();
        scrollMemory.delete(filePath);
        editBuffers.delete(filePath);
        if (bridge) bridge.closeFile(filePath);
      }
    });

    item.appendChild(openBtn);

    const dotIdx = fileName.lastIndexOf(".");
    if (dotIdx > 0 && dotIdx < fileName.length - 1) {
      const extPill = document.createElement("span");
      extPill.className = "file-ext-pill";
      extPill.textContent = fileName.slice(dotIdx + 1);
      item.appendChild(extPill);
    }

    if (showCloseBtn) {
      const closeBtn = document.createElement("button");
      closeBtn.type = "button";
      closeBtn.className = "file-close";
      closeBtn.textContent = "✕";
      closeBtn.title = uiStrings.files_close_title;
      closeBtn.setAttribute("aria-label", uiStrings.files_close_title);
      closeBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        scrollMemory.delete(filePath);
        editBuffers.delete(filePath);
        if (bridge) bridge.closeFile(filePath);
      });
      item.appendChild(closeBtn);
    }

    return item;
  }

  function renderWorkspaceTreeNode(node, isRoot, parentDirPath, siblingPaths) {
    if (node.type === "file") {
      const row = createFileRowElement(node.path, node.name, false);
      attachReorderHandlers(
        row,
        "tree:" + parentDirPath,
        node.path,
        (newOrder) => {
          if (bridge && typeof bridge.reorderFolderChildren === "function") {
            bridge.reorderFolderChildren(parentDirPath, JSON.stringify(newOrder));
          }
        },
        () => siblingPaths
      );
      return row;
    }

    const folderGroup = document.createElement("div");
    folderGroup.className = "folder-group";
    if (state.collapsedFolders.has(node.path)) {
      folderGroup.classList.add("collapsed");
    }

    const folderRow = document.createElement("div");
    folderRow.className = "folder-row";

    const headerBtn = document.createElement("button");
    headerBtn.type = "button";
    headerBtn.className = "folder-header" + (isRoot ? "" : " subfolder-header");
    headerBtn.title = node.path;

    const chev = document.createElement("span");
    chev.className = "folder-chevron";
    chev.textContent = "▾";

    const nameSpan = document.createElement("span");
    nameSpan.className = "folder-name";
    nameSpan.textContent = node.name;

    const childCount = Array.isArray(node.children) ? node.children.length : 0;
    const countSpan = document.createElement("span");
    countSpan.className = "folder-count";
    countSpan.textContent = String(childCount);

    headerBtn.appendChild(chev);
    headerBtn.appendChild(nameSpan);
    headerBtn.appendChild(countSpan);
    headerBtn.addEventListener("click", () => {
      const nowCollapsed = folderGroup.classList.toggle("collapsed");
      if (nowCollapsed) {
        state.collapsedFolders.add(node.path);
      } else {
        state.collapsedFolders.delete(node.path);
      }
      if (bridge) bridge.toggleFolderCollapsed(node.path);
    });

    folderRow.appendChild(headerBtn);

    if (isRoot) {
      const closeFolderBtn = document.createElement("button");
      closeFolderBtn.type = "button";
      closeFolderBtn.className = "folder-close";
      closeFolderBtn.textContent = "✕";
      closeFolderBtn.title = uiStrings.files_close_folder_title || "Remove folder";
      closeFolderBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (bridge && typeof bridge.closeFolder === "function") {
          bridge.closeFolder(node.path);
        }
      });
      folderRow.appendChild(closeFolderBtn);
      attachReorderHandlers(
        folderGroup,
        "roots",
        node.path,
        (newOrder) => {
          state.openFolders = newOrder;
          if (bridge && typeof bridge.reorderOpenFolders === "function") {
            bridge.reorderOpenFolders(JSON.stringify(newOrder));
          }
        },
        () => state.openFolders
      );
    } else if (parentDirPath) {
      attachReorderHandlers(
        folderGroup,
        "tree:" + parentDirPath,
        node.path,
        (newOrder) => {
          if (bridge && typeof bridge.reorderFolderChildren === "function") {
            bridge.reorderFolderChildren(parentDirPath, JSON.stringify(newOrder));
          }
        },
        () => siblingPaths
      );
    }

    const listWrap = document.createElement("div");
    listWrap.className = "folder-files" + (isRoot ? "" : " nested-tree");

    const children = Array.isArray(node.children) ? node.children : [];
    const childPaths = children.map((c) => c.path);
    children.forEach((child) => {
      listWrap.appendChild(renderWorkspaceTreeNode(child, false, node.path, childPaths));
    });

    folderGroup.appendChild(folderRow);
    folderGroup.appendChild(listWrap);
    return folderGroup;
  }

  function renderFilesList() {
    filesList.innerHTML = "";
    const trees = Array.isArray(state.folderTrees) ? state.folderTrees : [];
    const openFiles = Array.isArray(state.openFiles) ? state.openFiles : [];

    const treeFileSet = new Set();
    trees.forEach((tree) => collectTreeFilePaths(tree, treeFileSet));
    const looseFiles = openFiles.filter((p) => !treeFileSet.has(p));

    if (trees.length === 0 && looseFiles.length === 0) {
      const empty = document.createElement("div");
      empty.className = "files-empty";
      empty.textContent = uiStrings.files_empty;
      filesList.appendChild(empty);
      return;
    }

    const frag = document.createDocumentFragment();

    // 1. Render opened workspace folders as VS Code-style nested trees
    trees.forEach((tree) => {
      frag.appendChild(renderWorkspaceTreeNode(tree, true, "", state.openFolders));
    });

    // 2. Render loose open files grouped by folder (drag-and-drop reorderable)
    if (looseFiles.length > 0) {
      const groups = new Map();
      looseFiles.forEach((fullPath) => {
        const sep = fullPath.lastIndexOf("/");
        const dirPath = sep > 0 ? fullPath.slice(0, sep) : "/";
        if (!groups.has(dirPath)) {
          groups.set(dirPath, []);
        }
        groups.get(dirPath).push(fullPath);
      });

      const groupKeys = Array.from(groups.keys());
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

        attachReorderHandlers(
          folderGroup,
          "loose-folders",
          dirPath,
          (newGroupOrder) => {
            const reorderedFiles = [];
            newGroupOrder.forEach((gKey) => {
              const gPaths = groups.get(gKey) || [];
              gPaths.forEach((fp) => reorderedFiles.push(fp));
            });
            openFiles.forEach((fp) => {
              if (!reorderedFiles.includes(fp)) reorderedFiles.push(fp);
            });
            state.openFiles = reorderedFiles;
            renderFilesList();
            if (bridge && typeof bridge.reorderOpenFiles === "function") {
              bridge.reorderOpenFiles(JSON.stringify(reorderedFiles));
            }
          },
          () => groupKeys
        );

        const listWrap = document.createElement("div");
        listWrap.className = "folder-files";

        paths.forEach((filePath) => {
          const sep = filePath.lastIndexOf("/");
          const fileName = sep >= 0 ? filePath.slice(sep + 1) : filePath;
          const item = createFileRowElement(filePath, fileName, true);
          attachReorderHandlers(
            item,
            "loose-files:" + dirPath,
            filePath,
            (newGroupFiles) => {
              const nextOpen = [];
              const replacedSet = new Set(paths);
              let inserted = false;
              state.openFiles.forEach((fp) => {
                if (replacedSet.has(fp)) {
                  if (!inserted) {
                    newGroupFiles.forEach((nf) => nextOpen.push(nf));
                    inserted = true;
                  }
                } else {
                  nextOpen.push(fp);
                }
              });
              state.openFiles = nextOpen;
              renderFilesList();
              if (bridge && typeof bridge.reorderOpenFiles === "function") {
                bridge.reorderOpenFiles(JSON.stringify(nextOpen));
              }
            },
            () => paths
          );
          listWrap.appendChild(item);
        });

        folderGroup.appendChild(headerBtn);
        folderGroup.appendChild(listWrap);
        frag.appendChild(folderGroup);
      });
    }

    filesList.appendChild(frag);
  }

  function collapseAllFolders() {
    const allDirs = [];
    (state.folderTrees || []).forEach((tree) => collectTreeDirPaths(tree, allDirs));
    (state.openFiles || []).forEach((fp) => {
      const sep = fp.lastIndexOf("/");
      if (sep > 0) allDirs.push(fp.slice(0, sep));
    });
    allDirs.forEach((dirPath) => {
      if (!state.collapsedFolders.has(dirPath)) {
        state.collapsedFolders.add(dirPath);
        if (bridge) bridge.toggleFolderCollapsed(dirPath);
      }
    });
    renderFilesList();
  }

  function updateSession(session) {
    if (!session) return;
    state.openFiles = Array.isArray(session.open_files) ? session.open_files : [];
    state.openFolders = Array.isArray(session.open_folders) ? session.open_folders : [];
    state.folderTrees = Array.isArray(session.folder_trees) ? session.folder_trees : [];
    state.activeFile = session.active_file || "";
    state.collapsedFolders = new Set(Array.isArray(session.collapsed_folders) ? session.collapsed_folders : []);
    renderFilesList();
  }

  function enhanceCodeBlocks() {
    const pres = contentEl.querySelectorAll("pre");
    pres.forEach((pre) => {
      if (pre.classList.contains("plain-text-pre")) {
        return;
      }
      if (pre.parentElement && pre.parentElement.classList.contains("code-block")) {
        return;
      }
      const wrapper = document.createElement("div");
      wrapper.className = "code-block";

      const codeEl = pre.querySelector("code");
      const lang = (codeEl ? codeEl.getAttribute("data-lang") : pre.getAttribute("data-lang")) || "";

      if (codeEl && window.CocoHighlight) {
        window.CocoHighlight.highlightElement(codeEl, lang);
      }

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
        const rawAttr = codeEl ? codeEl.getAttribute("data-raw-code") : null;
        const text = rawAttr !== null ? rawAttr : (codeEl ? codeEl.textContent : pre.textContent) || "";
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
        if (state.isEditing) {
          exitEditMode();
        }
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
    if (!state.hasDoc || state.isEditing) {
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

  function renderDocument(doc, preserveScroll, isLivePreview) {
    if (state.hasDoc && state.currentPath && state.currentPath !== doc.path) {
      scrollMemory.set(state.currentPath, scrollEl.scrollTop);
    }

    let ratio = 0;
    if (preserveScroll) {
      const maxScroll = scrollEl.scrollHeight - scrollEl.clientHeight;
      if (maxScroll > 0) ratio = scrollEl.scrollTop / maxScroll;
    }

    const incomingPath = doc.path || "";
    const existingBuf = editBuffers.get(incomingPath || "__untitled__");

    state.hasDoc = true;
    state.currentPath = incomingPath;
    state.currentFilename = doc.filename || doc.title || uiStrings.untitled_filename;
    state.currentLanguage = inferEditorLanguage(state.currentFilename, doc.language || doc.format || "");
    state.editable = doc.editable !== false;
    state.isEpub = Boolean(doc.is_epub);
    state.isCode = Boolean(doc.is_code);
    state.tocCount = Array.isArray(doc.toc) ? doc.toc.length : 0;

    if (!isLivePreview) {
      const diskText = typeof doc.raw_text === "string" ? doc.raw_text : "";
      if (existingBuf && existingBuf.dirty && incomingPath) {
        state.rawText = existingBuf.text;
        state.isDirty = true;
      } else {
        state.rawText = diskText;
        state.isDirty = false;
        if (incomingPath) {
          editBuffers.set(incomingPath, {
            text: diskText,
            originalText: diskText,
            dirty: false,
            filename: state.currentFilename,
            isCode: state.isCode,
          });
        }
      }
      state.isEditing = false;
    }

    welcomeEl.classList.add("hidden");
    editorView.classList.add("hidden");
    contentEl.classList.remove("hidden");
    contentEl.classList.toggle("code-prose", state.isCode);
    contentEl.innerHTML = doc.html || "";

    enhanceCodeBlocks();
    wireInternalAnchors();
    buildToc(doc.toc || [], doc.title || doc.filename || "Coconut");
    updateSidebarVisibility();
    syncEditControlsUI();

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

  function inferEditorLanguage(filename, explicitLang) {
    const cleanExplicit = String(explicitLang || "").trim().toLowerCase();
    if (cleanExplicit && cleanExplicit !== "code" && cleanExplicit !== "text") {
      return cleanExplicit;
    }
    const name = String(filename || "");
    const dot = name.lastIndexOf(".");
    if (dot >= 0 && dot < name.length - 1) {
      return name.slice(dot + 1).toLowerCase();
    }
    return "markdown";
  }

  function syncEditorBackdrop() {
    if (!editorTextarea) return;
    const text = editorTextarea.value || "";
    const lang = inferEditorLanguage(state.currentFilename, state.currentLanguage);
    if (editorBackdropCode) {
      if (window.CocoHighlight && typeof window.CocoHighlight.highlightForEditor === "function") {
        editorBackdropCode.innerHTML = window.CocoHighlight.highlightForEditor(text, lang);
      } else {
        editorBackdropCode.textContent = text;
      }
    }
    if (editorGutter) {
      const lineCount = text ? text.split("\n").length : 1;
      const nums = [];
      for (let i = 1; i <= lineCount; i++) {
        nums.push(String(i));
      }
      editorGutter.textContent = nums.join("\n");
    }
  }

  function enterEditMode() {
    if (!state.editable || state.isEpub) {
      showToast(uiStrings.toast_epub_readonly);
      return;
    }
    const key = bufferKey();
    const buf = editBuffers.get(key);
    const currentText = buf ? buf.text : state.rawText || "";

    state.isEditing = true;
    state.isDirty = buf ? Boolean(buf.dirty) : false;

    const currentScroll = scrollEl.scrollTop;
    welcomeEl.classList.add("hidden");
    contentEl.classList.add("hidden");
    editorView.classList.remove("hidden");
    editorView.classList.toggle("code-editor", state.isCode);

    editorTextarea.value = currentText;
    syncEditorBackdrop();
    syncEditControlsUI();
    requestAnimationFrame(() => {
      scrollEl.scrollTop = currentScroll;
      editorTextarea.focus();
    });
  }

  function exitEditMode() {
    if (!state.isEditing) return;
    state.isEditing = false;

    if (!state.currentPath && !editorTextarea.value.trim()) {
      editBuffers.delete("__untitled__");
      state.isDirty = false;
      showWelcome(state.recentFiles);
      return;
    }

    editorView.classList.add("hidden");
    contentEl.classList.remove("hidden");
    syncEditControlsUI();

    if (bridge && typeof bridge.previewRawText === "function") {
      bridge.previewRawText(
        editorTextarea.value,
        state.currentPath || state.currentFilename || uiStrings.untitled_filename
      );
    }
  }

  function toggleEditMode() {
    if (state.isEpub) {
      showToast(uiStrings.toast_epub_readonly);
      return;
    }
    if (!state.hasDoc && !state.isEditing) {
      startNewDocument();
      return;
    }
    if (state.isEditing) {
      exitEditMode();
    } else {
      enterEditMode();
    }
  }

  function startNewDocument() {
    state.hasDoc = true;
    state.currentPath = "";
    state.currentFilename = uiStrings.untitled_filename || "Untitled.md";
    state.currentLanguage = "markdown";
    state.rawText = "";
    state.editable = true;
    state.isEpub = false;
    state.isCode = false;
    state.isDirty = false;
    state.tocCount = 0;

    editBuffers.set("__untitled__", {
      text: "",
      originalText: "",
      dirty: false,
      filename: state.currentFilename,
      isCode: false,
    });

    buildToc([], state.currentFilename);
    updateSidebarVisibility();
    enterEditMode();
  }

  function requestSave() {
    if (state.isEpub) return;
    if (!state.hasDoc && !state.isEditing) return;

    const key = bufferKey();
    const buf = editBuffers.get(key);
    const contentToSave = state.isEditing
      ? editorTextarea.value
      : buf
      ? buf.text
      : state.rawText;

    if (bridge && typeof bridge.saveFile === "function") {
      bridge.saveFile(state.currentPath || "", contentToSave);
    }
  }

  function onFileSaved(doc) {
    if (!doc) return;
    const wasEditing = state.isEditing;
    const selStart = editorTextarea ? editorTextarea.selectionStart : 0;
    const selEnd = editorTextarea ? editorTextarea.selectionEnd : 0;
    const editorScroll = editorTextarea ? editorTextarea.scrollTop : 0;

    editBuffers.delete("__untitled__");
    if (doc.path) {
      const savedText = typeof doc.raw_text === "string" ? doc.raw_text : editorTextarea.value;
      editBuffers.set(doc.path, {
        text: savedText,
        originalText: savedText,
        dirty: false,
        filename: doc.filename || "Untitled.md",
        isCode: Boolean(doc.is_code),
      });
    }

    state.isDirty = false;
    renderDocument(doc, true, false);

    if (wasEditing) {
      enterEditMode();
      requestAnimationFrame(() => {
        editorTextarea.setSelectionRange(selStart, selEnd);
        editorTextarea.scrollTop = editorScroll;
      });
    }
  }

  function showWelcome(recentFiles) {
    state.hasDoc = false;
    state.currentPath = "";
    state.currentFilename = "";
    state.rawText = "";
    state.isEditing = false;
    state.isDirty = false;
    state.isEpub = false;
    state.isCode = false;
    state.tocCount = 0;
    state.tocElements = [];
    state.tocButtons.clear();
    state.activeId = null;
    if (Array.isArray(recentFiles)) {
      state.recentFiles = recentFiles;
    }

    contentEl.innerHTML = "";
    contentEl.classList.add("hidden");
    editorView.classList.add("hidden");
    welcomeEl.classList.remove("hidden");
    progressBar.style.width = "0%";
    updateSidebarVisibility();
    syncEditControlsUI();

    recentList.innerHTML = "";
    if (Array.isArray(state.recentFiles) && state.recentFiles.length > 0) {
      recentBlock.classList.remove("hidden");
      state.recentFiles.forEach((fullPath) => {
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
    if (state.isEditing) {
      editorTextarea.focus();
    } else {
      scrollEl.focus();
    }
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
    if (state.isEditing) {
      editorTextarea.focus();
    } else {
      scrollEl.focus();
    }
  }

  function openExtensions() {
    renderExtensionsCatalog();
    extensionsModal.classList.remove("hidden");
  }

  function closeExtensions() {
    if (extensionsModal.classList.contains("hidden")) return;
    extensionsModal.classList.add("hidden");
    if (state.isEditing) {
      editorTextarea.focus();
    } else {
      scrollEl.focus();
    }
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

  // Editor events
  if (editorTextarea) {
    editorTextarea.addEventListener("input", () => {
      const key = bufferKey();
      const existing = editBuffers.get(key) || {
        text: "",
        originalText: state.rawText || "",
        dirty: false,
        filename: state.currentFilename || uiStrings.untitled_filename,
        isCode: state.isCode,
      };
      existing.text = editorTextarea.value;
      existing.dirty = existing.text !== existing.originalText || !state.currentPath;
      editBuffers.set(key, existing);

      state.rawText = existing.text;
      state.isDirty = existing.dirty;
      syncEditorBackdrop();
      syncEditControlsUI();
    });

    editorTextarea.addEventListener("keydown", (e) => {
      if (e.key === "Tab" && !e.ctrlKey && !e.altKey && !e.metaKey) {
        e.preventDefault();
        const start = editorTextarea.selectionStart;
        const end = editorTextarea.selectionEnd;
        const val = editorTextarea.value;
        editorTextarea.value = val.slice(0, start) + "  " + val.slice(end);
        editorTextarea.selectionStart = editorTextarea.selectionEnd = start + 2;
        editorTextarea.dispatchEvent(new Event("input"));
      }
    });
  }

  if (btnEditorSave) {
    btnEditorSave.addEventListener("click", requestSave);
  }
  if (btnEditorDone) {
    btnEditorDone.addEventListener("click", exitEditMode);
  }

  // Top-right & sidebar buttons
  btnToc.addEventListener("click", () => {
    if (bridge) bridge.toggleSidebar();
  });
  btnOpen.addEventListener("click", () => {
    if (bridge) bridge.openFileDialog();
  });
  if (btnNewFile) {
    btnNewFile.addEventListener("click", startNewDocument);
  }
  if (btnFilesNew) {
    btnFilesNew.addEventListener("click", startNewDocument);
  }
  if (btnFilesFolder) {
    btnFilesFolder.addEventListener("click", () => {
      if (bridge && typeof bridge.openFolderDialog === "function") {
        bridge.openFolderDialog();
      }
    });
  }
  if (btnFilesCollapse) {
    btnFilesCollapse.addEventListener("click", collapseAllFolders);
  }
  btnFilesAdd.addEventListener("click", () => {
    if (bridge) bridge.openFileDialog();
  });
  btnWelcomeOpen.addEventListener("click", () => {
    if (bridge) bridge.openFileDialog();
  });
  if (btnWelcomeFolder) {
    btnWelcomeFolder.addEventListener("click", () => {
      if (bridge && typeof bridge.openFolderDialog === "function") {
        bridge.openFolderDialog();
      }
    });
  }
  if (btnWelcomeNew) {
    btnWelcomeNew.addEventListener("click", startNewDocument);
  }

  // VS Code-style sidebar width resizer
  if (sidebarResizer) {
    let resizing = false;
    let lastWidth = 260;
    sidebarResizer.addEventListener("mousedown", (e) => {
      if (e.button !== 0 || !state.sidebarWanted) return;
      e.preventDefault();
      resizing = true;
      sidebar.classList.add("resizing");
      sidebarResizer.classList.add("active");
    });
    window.addEventListener("mousemove", (e) => {
      if (!resizing) return;
      const clamped = Math.max(180, Math.min(520, Math.round(e.clientX)));
      lastWidth = clamped;
      document.documentElement.style.setProperty("--sidebar-width", clamped + "px");
    });
    window.addEventListener("mouseup", () => {
      if (!resizing) return;
      resizing = false;
      sidebar.classList.remove("resizing");
      sidebarResizer.classList.remove("active");
      if (bridge && typeof bridge.setSidebarWidth === "function") {
        bridge.setSidebarWidth(lastWidth);
      }
    });
  }
  if (btnEditMode) {
    btnEditMode.addEventListener("click", toggleEditMode);
  }
  if (btnSaveFile) {
    btnSaveFile.addEventListener("click", requestSave);
  }
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

  // Extensions modal wiring
  extensionsPill.addEventListener("click", openExtensions);
  btnExtClose.addEventListener("click", closeExtensions);
  extensionsModal.addEventListener("click", (e) => {
    if (e.target === extensionsModal) closeExtensions();
  });
  if (extSearchInput) {
    extSearchInput.addEventListener("input", () => {
      extSearchQuery = extSearchInput.value || "";
      renderExtensionsCatalog();
    });
  }
  extCatBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      extCategoryFilter = btn.getAttribute("data-ext-cat") || "all";
      extCatBtns.forEach((b) => b.classList.toggle("active", b === btn));
      renderExtensionsCatalog();
    });
  });
  if (btnExtAddAll) {
    btnExtAddAll.addEventListener("click", () => {
      if (bridge && typeof bridge.setAllExtensions === "function") {
        bridge.setAllExtensions(true);
      }
    });
  }
  if (btnExtRemoveAll) {
    btnExtRemoveAll.addEventListener("click", () => {
      if (bridge && typeof bridge.setAllExtensions === "function") {
        bridge.setAllExtensions(false);
      }
    });
  }

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

  accentPills.forEach((pill) => {
    pill.addEventListener("click", () => {
      const choice = pill.getAttribute("data-accent-choice");
      if (bridge && choice && typeof bridge.setSettingChoice === "function") {
        bridge.setSettingChoice("accent_color", choice);
      }
    });
  });

  widthBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const choice = btn.getAttribute("data-width-choice");
      if (bridge && choice && typeof bridge.setSettingChoice === "function") {
        bridge.setSettingChoice("reading_width", choice);
      }
    });
  });

  lhBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const choice = btn.getAttribute("data-lh-choice");
      if (bridge && choice && typeof bridge.setSettingChoice === "function") {
        bridge.setSettingChoice("line_height", choice);
      }
    });
  });

  cstyleBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const choice = btn.getAttribute("data-cstyle-choice");
      if (bridge && choice && typeof bridge.setSettingChoice === "function") {
        bridge.setSettingChoice("code_style", choice);
      }
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
  if (chkLineNumbers) {
    chkLineNumbers.addEventListener("change", () => {
      if (bridge) bridge.setSettingBool("show_line_numbers", chkLineNumbers.checked);
    });
  }
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
      if (!extensionsModal.classList.contains("hidden")) {
        e.preventDefault();
        closeExtensions();
        return;
      }
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
    if (!extensionsModal.classList.contains("hidden") || !settingsModal.classList.contains("hidden")) return;
    if (
      document.activeElement === findInput ||
      document.activeElement === editorTextarea ||
      document.activeElement === extSearchInput
    ) {
      return;
    }
    if (e.ctrlKey || e.altKey || e.metaKey) return;

    if (e.key === "j") {
      scrollEl.scrollBy({ top: 96, behavior: "smooth" });
    } else if (e.key === "k") {
      scrollEl.scrollBy({ top: -96, behavior: "smooth" });
    }
  });

  // Drag-over visual indicator only (Qt eventFilter handles actual drop)
  window.addEventListener("dragenter", (e) => {
    if (sidebarDragState) return;
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
    openExtensions,
    closeExtensions,
    renderDocument,
    showWelcome,
    openFindBar,
    closeFindBar,
    showToast,
    toggleEditMode,
    startNewDocument,
    requestSave,
    onFileSaved,
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
