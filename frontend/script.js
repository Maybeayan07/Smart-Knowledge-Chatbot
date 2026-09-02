// ---------- Background vector-space network ----------
// ---------- Auth ----------
let authToken = null;
let authMode = "login";


const authScreen = document.getElementById("authScreen");
const appShellEl = document.getElementById("appShell");
const authForm = document.getElementById("authForm");
const authEmail = document.getElementById("authEmail");
const authPassword = document.getElementById("authPassword");
const authError = document.getElementById("authError");
const authSubmitBtn = document.getElementById("authSubmitBtn");
const tabLogin = document.getElementById("tabLogin");
const tabSignup = document.getElementById("tabSignup");

function showApp() {
  authScreen.classList.add("hidden");
  appShellEl.classList.remove("hidden");
}

function showAuth() {
  authScreen.classList.remove("hidden");
  appShellEl.classList.add("hidden");
}

tabLogin.addEventListener("click", () => {
  authMode = "login";
  tabLogin.classList.add("active");
  tabSignup.classList.remove("active");
  authSubmitBtn.textContent = "Login";
  authError.classList.add("hidden");
});

tabSignup.addEventListener("click", () => {
  authMode = "signup";
  tabSignup.classList.add("active");
  tabLogin.classList.remove("active");
  authSubmitBtn.textContent = "Sign Up";
  authError.classList.add("hidden");
});

authForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  authError.classList.add("hidden");

  const email = authEmail.value.trim();
  const password = authPassword.value;

  try {
    const res = await fetch(`/${authMode}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (!res.ok) {
      authError.textContent = data.detail || "Something went wrong.";
      authError.classList.remove("hidden");
      return;
    }

    authToken = data.access_token;
    showApp();
    initApp();
  } catch (err) {
    authError.textContent = "Could not reach the server.";
    authError.classList.remove("hidden");
  }
});

// Every fetch to our own backend now needs the Authorization header.
// This wraps the native fetch so we don't have to add headers everywhere manually.
const originalFetch = window.fetch;
window.fetch = function (url, options = {}) {
  const isOwnApi = typeof url === "string" && url.startsWith("/");
  if (isOwnApi && authToken) {
    options.headers = { ...(options.headers || {}), Authorization: `Bearer ${authToken}` };
  }
  return originalFetch(url, options).then((res) => {
    // Token expired/invalid — drop back to the login screen instead of
    // leaving every subsequent call to fail silently while the UI still
    // looks logged in.
    if (isOwnApi && res.status === 401 && authToken) {
      doLogout();
      authError.textContent = "Your session expired — please log in again.";
      authError.classList.remove("hidden");
    }
    return res;
  });
};

(function initNetwork() {
  const canvas = document.getElementById("network");
  const ctx = canvas.getContext("2d");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduceMotion) return;

  let w, h, points;

  function resize() {
    w = canvas.width = window.innerWidth;
    h = canvas.height = window.innerHeight;
    const count = Math.floor((w * h) / 26000);
    points = Array.from({ length: count }, () => ({
      x: Math.random() * w, y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.25, vy: (Math.random() - 0.5) * 0.25
    }));
  }

  function step() {
    ctx.clearRect(0, 0, w, h);
    for (const p of points) {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > w) p.vx *= -1;
      if (p.y < 0 || p.y > h) p.vy *= -1;
    }
    for (let i = 0; i < points.length; i++) {
      for (let j = i + 1; j < points.length; j++) {
        const dx = points[i].x - points[j].x;
        const dy = points[i].y - points[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 130) {
          ctx.strokeStyle = `rgba(124, 111, 255, ${0.12 * (1 - dist / 130)})`;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(points[i].x, points[i].y);
          ctx.lineTo(points[j].x, points[j].y);
          ctx.stroke();
        }
      }
    }
    for (const p of points) {
      ctx.fillStyle = "rgba(67, 217, 200, 0.4)";
      ctx.beginPath();
      ctx.arc(p.x, p.y, 1.4, 0, Math.PI * 2);
      ctx.fill();
    }
    requestAnimationFrame(step);
  }

  window.addEventListener("resize", resize);
  resize();
  step();
})();

// ---------- App logic ----------

const dropOverlay = document.getElementById("dropOverlay");
const chatArea = document.querySelector(".chat-area");
const chatLog = document.getElementById("chatLog");
const composerForm = document.getElementById("composerForm");
const questionInput = document.getElementById("questionInput");
const sendBtn = document.getElementById("sendBtn");
const brandMark = document.getElementById("brandMark");
const scrollDownBtn = document.getElementById("scrollDownBtn");
const docStatusText = document.getElementById("docStatusText");
const statusDot = document.getElementById("statusDot");
const resetBtn = document.getElementById("resetBtn");
const exportBtn = document.getElementById("exportBtn");
const sidebar = document.getElementById("sidebar");
const sidebarToggle = document.getElementById("sidebarToggle");
const sidebarOpenBtn = document.getElementById("sidebarOpenBtn");
const newChatBtn = document.getElementById("newChatBtn");
const sessionList = document.getElementById("sessionList");
const analyticsBtn = document.getElementById("analyticsBtn");
const analyticsModal = document.getElementById("analyticsModal");
const closeAnalytics = document.getElementById("closeAnalytics");
const analyticsContent = document.getElementById("analyticsContent");

const composerUpload = document.getElementById("composerUpload");
const uploadMenu = document.getElementById("uploadMenu");
const fileInputDoc = document.getElementById("fileInputDoc");
const fileInputImage = document.getElementById("fileInputImage");
const composerAttachments = document.getElementById("composerAttachments");

const API_BASE = "";

// Styling for the edit/regenerate controls is injected here directly,
// so it always applies regardless of what's in style.css.
(function injectControlStyles() {
  if (document.getElementById("chatui-controls-style")) return;
  const style = document.createElement("style");
  style.id = "chatui-controls-style";
  style.textContent = `
    .msg-user { position: relative; }

    .msg-controls {
      display: flex;
      align-items: center;
      gap: 4px;
      margin-top: 6px;
    }

    .icon-action-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 26px;
      height: 26px;
      padding: 0;
      background: transparent;
      border: none;
      border-radius: 50%;
      color: rgba(255, 255, 255, 0.55);
      cursor: pointer;
      transition: background 0.15s ease, color 0.15s ease;
    }
    .icon-action-btn:hover {
      background: rgba(255, 255, 255, 0.12);
      color: #fff;
    }
    .icon-action-btn svg { display: block; }

    .msg-user.editing {
      width: 100%;
      max-width: 520px;
      border-radius: 24px;
      padding: 14px 16px 12px;
      box-sizing: border-box;
    }
    .edit-textarea {
      width: 100%;
      min-height: 24px;
      max-height: 320px;
      resize: none;
      overflow-y: auto;
      background: transparent;
      border: none;
      color: #fff;
      font-family: inherit;
      font-size: 15px;
      line-height: 1.5;
      padding: 0;
      outline: none;
      box-sizing: border-box;
    }
    .edit-btn-row {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 14px;
    }
    .edit-cancel-btn,
    .edit-save-btn {
      border: none;
      border-radius: 999px;
      padding: 7px 16px;
      font-size: 13.5px;
      font-weight: 500;
      cursor: pointer;
      transition: opacity 0.15s ease, background 0.15s ease;
    }
    .edit-cancel-btn {
      background: transparent;
      color: rgba(255, 255, 255, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.25);
    }
    .edit-cancel-btn:hover { background: rgba(255, 255, 255, 0.08); }
    .edit-save-btn {
      background: #fff;
      color: #1a1a1a;
    }
    .edit-save-btn:hover { opacity: 0.85; }
  `;
  document.head.appendChild(style);
})();
let dragCounter = 0;

let hasDoc = false;
let hasImages = false;
let isGenerating = false;
let abortController = null;
let currentSessionId = null;
let autoScrollEnabled = true;

const SEND_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none"><path d="M4 12L20 4L14 20L11 13L4 12Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>`;
const STOP_ICON = `<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><rect x="5" y="5" width="14" height="14" rx="2"/></svg>`;

function scrollToBottom(smooth) {
  chatArea.scrollTo({ top: chatArea.scrollHeight, behavior: smooth ? "smooth" : "auto" });
}

// Only follows the bottom while streaming if the user hasn't scrolled up
// to read something earlier — avoids yanking them back down mid-read.
// When it can't auto-scroll, it flags the button so the user knows
// something new landed below.
function followBottomIfEnabled() {
  if (autoScrollEnabled) {
    scrollToBottom();
  } else {
    scrollDownBtn.classList.add("has-new");
  }
}

chatArea.addEventListener("scroll", () => {
  const distanceFromBottom = chatArea.scrollHeight - chatArea.scrollTop - chatArea.clientHeight;
  const nearBottom = distanceFromBottom < 120;
  autoScrollEnabled = nearBottom;
  scrollDownBtn.classList.toggle("hidden", nearBottom);
  if (nearBottom) scrollDownBtn.classList.remove("has-new");
});

scrollDownBtn.addEventListener("click", () => {
  autoScrollEnabled = true;
  scrollDownBtn.classList.remove("has-new");
  scrollToBottom(true);
});

const appShell = document.querySelector(".app-shell");
sidebarToggle.addEventListener("click", () => appShell.classList.toggle("sidebar-collapsed"));
sidebarOpenBtn.addEventListener("click", () => appShell.classList.remove("sidebar-collapsed"));
// On mobile, tapping the dark backdrop (rendered via ::after on .app-shell
// when the sidebar is open) should close the sidebar — same UX as most
// mobile apps' drawer navigation.
appShell.addEventListener("click", (e) => {
  const isMobile = window.innerWidth <= 760;
  if (isMobile && !appShell.classList.contains("sidebar-collapsed") && !sidebar.contains(e.target) && e.target !== sidebarOpenBtn) {
    appShell.classList.add("sidebar-collapsed");
  }
});
// ---------- Sessions ----------

async function loadSessionList() {
  const res = await fetch(`${API_BASE}/sessions`);
  const data = await res.json();

  sessionList.innerHTML = "";
  data.sessions.forEach((s) => {
    const item = document.createElement("div");
    item.className = "session-item" + (s.id === currentSessionId ? " active" : "");

    const title = document.createElement("span");
    title.className = "session-title";
    title.textContent = s.title;

    const del = document.createElement("button");
    del.className = "session-delete";
    del.innerHTML = `<svg viewBox="0 0 24 24" width="13" height="13" fill="none"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>`;
    del.addEventListener("click", async (e) => {
      e.stopPropagation();
      await fetch(`${API_BASE}/sessions/${s.id}`, { method: "DELETE" });
      if (s.id === currentSessionId) {
        await startNewChat();
      } else {
        loadSessionList();
      }
    });

    item.appendChild(title);
    item.appendChild(del);
    item.addEventListener("click", () => switchSession(s.id));
    sessionList.appendChild(item);
  });
}

async function startNewChat() {
  const res = await fetch(`${API_BASE}/sessions`, { method: "POST" });
  const data = await res.json();
  currentSessionId = data.session_id;
  hasDoc = false;
  hasImages = false;
  chatLog.innerHTML = `<div class="msg msg-system"><p>Click the + below to upload a PDF or images — I'll figure out what your question is about.</p></div>`;
  updateStatus();
  await loadSessionList();
}

async function switchSession(sessionId) {
  if (isGenerating || sessionId === currentSessionId) return;
  currentSessionId = sessionId;

  const [statusRes, messagesRes] = await Promise.all([
    fetch(`${API_BASE}/status?session_id=${sessionId}`),
    fetch(`${API_BASE}/sessions/${sessionId}/messages`)
  ]);
  const statusData = await statusRes.json();
  const messagesData = await messagesRes.json();

  hasDoc = statusData.has_doc;
  hasImages = statusData.has_images;
  updateStatus();

  chatLog.innerHTML = "";
  if (messagesData.messages.length === 0) {
    addSystemMessage("Click the + below to upload a PDF or images — I'll figure out what your question is about.");
  } else {
    const msgs = messagesData.messages;
    msgs.forEach((m) => {
      addMessage(m.content, m.role === "user" ? "user" : "bot", m.role === "assistant" ? "retrieved from vector index" : null, m.id);
    });

    // If the conversation's most recent turn is a complete user→assistant
    // exchange, that user bubble should also get the Regenerate icon
    // (edit already gets added by addMessage above via messageId).
    const lastMsg = msgs[msgs.length - 1];
    const secondLastMsg = msgs[msgs.length - 2];
    if (lastMsg && lastMsg.role === "assistant" && secondLastMsg && secondLastMsg.role === "user") {
      const userEl = chatLog.querySelector(`.msg-user[data-message-id="${secondLastMsg.id}"]`);
      if (userEl) attachUserControls(userEl, secondLastMsg.id, secondLastMsg.content, true);
    }
  }

  await loadSessionList();
}

newChatBtn.addEventListener("click", () => !isGenerating && startNewChat());

// ---------- Upload menu ----------

composerUpload.addEventListener("click", (e) => {
  e.stopPropagation();
  if (composerUpload.classList.contains("disabled")) return;
  uploadMenu.classList.toggle("hidden");
  composerUpload.classList.toggle("open");
});

document.addEventListener("click", () => {
  uploadMenu.classList.add("hidden");
  composerUpload.classList.remove("open");
});

uploadMenu.querySelectorAll("button").forEach((btn) => {
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    uploadMenu.classList.add("hidden");
    composerUpload.classList.remove("open");
    if (btn.dataset.type === "doc") fileInputDoc.click();
    else fileInputImage.click();
  });
});

fileInputDoc.addEventListener("change", () => {
  if (fileInputDoc.files.length) Array.from(fileInputDoc.files).forEach((f) => queueFileUpload(f, "doc"));
  fileInputDoc.value = "";
});

fileInputImage.addEventListener("change", () => {
  if (fileInputImage.files.length) Array.from(fileInputImage.files).forEach((f) => queueFileUpload(f, "image"));
  fileInputImage.value = "";
});

// ---------- Full-page drag & drop ----------

window.addEventListener("dragenter", (e) => {
  e.preventDefault();
  dragCounter++;
  dropOverlay.classList.add("active");
});
window.addEventListener("dragover", (e) => e.preventDefault());
window.addEventListener("dragleave", () => {
  dragCounter--;
  if (dragCounter <= 0) { dragCounter = 0; dropOverlay.classList.remove("active"); }
});
window.addEventListener("drop", (e) => {
  e.preventDefault();
  dragCounter = 0;
  dropOverlay.classList.remove("active");
  if (isGenerating || !e.dataTransfer.files.length) return;

  Array.from(e.dataTransfer.files).forEach((file) => {
    if (/\.(pdf|docx|txt)$/i.test(file.name)) queueFileUpload(file, "doc");
    else if (file.type.startsWith("image/")) queueFileUpload(file, "image");
  });
});

// ---------- Status text ----------

function updateStatus() {
  const ready = hasDoc || hasImages;

  if (hasDoc && hasImages) docStatusText.innerHTML = `<span class="status-dot ready" id="statusDot"></span><span class="mono">document + images indexed</span>`;
  else if (hasDoc) docStatusText.innerHTML = `<span class="status-dot ready" id="statusDot"></span><span class="mono">document indexed</span>`;
  else if (hasImages) docStatusText.innerHTML = `<span class="status-dot ready" id="statusDot"></span><span class="mono">images indexed</span>`;
  else docStatusText.innerHTML = `<span class="status-dot" id="statusDot"></span><span class="mono">nothing indexed yet</span>`;

  questionInput.disabled = isGenerating || !ready;
  sendBtn.disabled = false;
  questionInput.placeholder = ready ? "Ask anything…" : "Upload a document or image first…";
}

function setGenerating(state) {
  isGenerating = state;
  composerUpload.classList.toggle("disabled", state);
  sendBtn.disabled = false;
  sendBtn.classList.toggle("stopping", state);
  sendBtn.innerHTML = state ? STOP_ICON : SEND_ICON;
  sendBtn.setAttribute("aria-label", state ? "Stop generating" : "Send");
  questionInput.disabled = state || !(hasDoc || hasImages);
}

// ---------- Uploads ----------
// ChatGPT/Claude-style attachment chips: a file appears as a small card
// above the composer the instant it's picked, with a spinner while
// uploading. It stays visible (does NOT auto-disappear) once the upload
// finishes — it's only cleared when the user actually sends their
// question, matching how ChatGPT/Claude keep an attached file visible
// until the message carrying it is sent.

function getFileTypeLabel(file, kind) {
  if (kind === "image") return "IMAGE";
  const parts = file.name.split(".");
  const ext = parts.length > 1 ? parts.pop().toUpperCase() : "";
  return ext || "FILE";
}

function createAttachmentChip(file, kind) {
  const chip = document.createElement("div");
  chip.className = "attachment-chip uploading";

  const iconWrap = document.createElement("div");
  iconWrap.className = "attachment-icon-wrap";
  iconWrap.textContent = getFileTypeLabel(file, kind).slice(0, 3);

  const info = document.createElement("div");
  info.className = "attachment-info";

  const name = document.createElement("span");
  name.className = "attachment-name";
  name.textContent = file.name;
  name.title = file.name;

  const type = document.createElement("span");
  type.className = "attachment-type";
  type.textContent = getFileTypeLabel(file, kind);

  info.appendChild(name);
  info.appendChild(type);

  const removeBtn = document.createElement("button");
  removeBtn.type = "button";
  removeBtn.className = "attachment-remove";
  removeBtn.setAttribute("aria-label", "Remove");
  removeBtn.innerHTML = `<svg viewBox="0 0 24 24" width="12" height="12" fill="none"><path d="M6 6l12 12M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`;

  chip.appendChild(iconWrap);
  chip.appendChild(info);
  chip.appendChild(removeBtn);

  return { chip, removeBtn };
}

function removeAttachmentChip(chip) {
  chip.remove();
  if (!composerAttachments.children.length) composerAttachments.classList.add("hidden");
}

// Clears every attachment chip from the composer — called right when the
// user actually sends their question, not on any timer.
function clearAttachmentChips() {
  composerAttachments.innerHTML = "";
  composerAttachments.classList.add("hidden");
}

async function queueFileUpload(file, kind) {
  if (!currentSessionId) return;

  const isDoc = kind === "doc";
  if (isDoc && !/\.(pdf|docx|txt)$/i.test(file.name)) return;
  if (!isDoc && !file.type.startsWith("image/")) return;

  composerAttachments.classList.remove("hidden");
  const { chip, removeBtn } = createAttachmentChip(file, kind);
  composerAttachments.appendChild(chip);
  followBottomIfEnabled();

  const controller = new AbortController();
  let cancelled = false;

  removeBtn.addEventListener("click", () => {
    if (chip.classList.contains("uploading")) {
      cancelled = true;
      controller.abort();
    }
    removeAttachmentChip(chip);
  });

  const formData = new FormData();
  formData.append("file", file);
  const endpoint = isDoc ? "upload-doc" : "upload-image";

  try {
    const res = await fetch(`${API_BASE}/${endpoint}?session_id=${currentSessionId}`, {
      method: "POST",
      body: formData,
      signal: controller.signal
    });
    if (!res.ok) throw new Error("Upload failed");

    if (isDoc) hasDoc = true;
    else hasImages = true;

    updateStatus();
    questionInput.focus();

    if (isDoc) {
      brandMark.classList.add("stamped");
      setTimeout(() => brandMark.classList.remove("stamped"), 500);
    }

    chip.classList.remove("uploading");
    chip.classList.add("done");
    // Stays visible — only cleared on send (see clearAttachmentChips()).
  } catch (err) {
    if (cancelled) return; // chip already removed by the click handler
    chip.classList.remove("uploading");
    chip.classList.add("error");
    setTimeout(() => removeAttachmentChip(chip), 4000);
  }
}

function addSystemMessage(text, isError) {
  const el = document.createElement("div");
  el.className = `msg msg-${isError ? "error" : "system"}`;
  const p = document.createElement("p");
  p.textContent = text;
  el.appendChild(p);
  chatLog.appendChild(el);
  followBottomIfEnabled();
}

// ---------- Reset ----------

resetBtn.addEventListener("click", async () => {
  if (isGenerating || !currentSessionId) return;
  await fetch(`${API_BASE}/clear-doc?session_id=${currentSessionId}`, { method: "POST" });
  await fetch(`${API_BASE}/clear-images?session_id=${currentSessionId}`, { method: "POST" });
  hasDoc = false;
  hasImages = false;
  updateStatus();
  chatLog.innerHTML = `<div class="msg msg-system"><p>Click the + below to upload a PDF or images — I'll figure out what your question is about.</p></div>`;
});
// ---------- Logout ----------

const logoutBtn = document.getElementById("logoutBtn");

function doLogout() {
  authToken = null;
  currentSessionId = null;
  hasDoc = false;
  hasImages = false;
  chatLog.innerHTML = "";
  sessionList.innerHTML = "";
  authEmail.value = "";
  authPassword.value = "";
  showAuth();
}

logoutBtn.addEventListener("click", doLogout);
// ---------- Export ----------

exportBtn.addEventListener("click", async () => {
  if (!currentSessionId) return;

  const choice = window.confirm("OK = Export as PDF, Cancel = Export as Markdown");
  const format = choice ? "pdf" : "markdown";

  try {
    const res = await fetch(`${API_BASE}/export-chat?session_id=${currentSessionId}&format=${format}`);
    if (!res.ok) {
      addSystemMessage("Nothing to export yet — start a conversation first.", true);
      return;
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `chat_${currentSessionId}.${format === "pdf" ? "pdf" : "md"}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    addSystemMessage("Could not export chat.", true);
  }
});

// ---------- Analytics ----------

// top_questions comes from user-submitted questions and gets inserted via
// innerHTML below — escape it so a question containing HTML/script can't
// execute in the analytics modal (stored XSS).
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

analyticsBtn.addEventListener("click", async () => {
  analyticsModal.classList.remove("hidden");
  analyticsContent.innerHTML = "Loading…";

  try {
    const res = await fetch(`${API_BASE}/analytics`);
    const data = await res.json();

    const topQuestionsHtml = data.top_questions.length
      ? data.top_questions.map(q => `<li>${escapeHtml(q.question)} <span class="mono">(${q.count}x)</span></li>`).join("")
      : "<li>No queries yet</li>";

    analyticsContent.innerHTML = `
      <div class="analytics-grid">
        <div class="analytics-stat">
          <div class="analytics-number">${data.total_queries}</div>
          <div class="analytics-label">Total Queries</div>
        </div>
        <div class="analytics-stat">
          <div class="analytics-number">${data.avg_response_time_ms}ms</div>
          <div class="analytics-label">Avg Response Time</div>
        </div>
        <div class="analytics-stat">
          <div class="analytics-number">${data.documents_indexed}</div>
          <div class="analytics-label">Documents Indexed</div>
        </div>
        <div class="analytics-stat">
          <div class="analytics-number">👍 ${data.feedback.up} / 👎 ${data.feedback.down}</div>
          <div class="analytics-label">Feedback</div>
        </div>
      </div>
      <h4>Top Questions</h4>
      <ul class="analytics-list">${topQuestionsHtml}</ul>
    `;
  } catch (err) {
    analyticsContent.innerHTML = "Could not load analytics.";
  }
});

closeAnalytics.addEventListener("click", () => {
  analyticsModal.classList.add("hidden");
});

// ---------- Submit / Stop ----------
async function submitQuestion(question) {
  if (!question || !(hasDoc || hasImages) || !currentSessionId) return;

  // Any attachment chips are cleared right as the question is actually
  // sent, not on a timer — matches ChatGPT/Claude behavior.
  clearAttachmentChips();

  let resolvedContext;
  if (hasDoc && hasImages) {
    const stageEl = addThinking(["Reading your question…"]);
    try {
      const intentRes = await fetch(`${API_BASE}/predict-intent`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: currentSessionId })
      });
      const intentData = await intentRes.json();
      resolvedContext = intentData.intent;
    } catch (err) {
      resolvedContext = "doc";
    }
    stageEl.remove();
  } else if (hasDoc) {
    resolvedContext = "doc";
  } else {
    resolvedContext = "image";
  }

  addMessage(question, "user");
  autoScrollEnabled = true;
  setGenerating(true);

  const thinkingEl = addThinking(
    resolvedContext === "image"
      ? ["Searching indexed images…"]
      : ["Searching documents…", "Retrieving relevant passages…", "Generating answer…"]
  );
  abortController = new AbortController();

  try {
    if (resolvedContext === "doc") {
      const res = await fetch(`${API_BASE}/chat-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: currentSessionId }),
        signal: abortController.signal
      });

      if (!res.ok) {
        thinkingEl.remove();
        const err = await res.json();
        addMessage(err.detail || "Something went wrong.", "error");
      } else {
        await streamIntoMessage(res, thinkingEl, question);
        loadSessionList();
        await attachControlsForLatestExchange(question);
      }
    } else if (resolvedContext === "image") {
      const res = await fetch(`${API_BASE}/search-image`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: currentSessionId }),
        signal: abortController.signal
      });
      thinkingEl.remove();

      if (!res.ok) {
        const err = await res.json();
        addMessage(err.detail || "Something went wrong.", "error");
      } else {
        const data = await res.json();
        addImageResults(data.matches);
        loadSessionList();
      }
    } else {
      const docRes = await fetch(`${API_BASE}/chat-stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: currentSessionId }),
        signal: abortController.signal
      });

      if (!docRes.ok) {
        thinkingEl.remove();
        const err = await docRes.json();
        addMessage(err.detail || "Something went wrong.", "error");
      } else {
        await streamIntoMessage(docRes, thinkingEl, question);
        await attachControlsForLatestExchange(question);

        const imgRes = await fetch(`${API_BASE}/search-image`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question, session_id: currentSessionId }),
          signal: abortController.signal
        });

        if (imgRes.ok) {
          const data = await imgRes.json();
          addImageResults(data.matches);
        }
        loadSessionList();
      }
    }
  } catch (err) {
    thinkingEl.remove();
    if (err.name === "AbortError") addSystemMessage("Generation stopped.");
    else addMessage("Could not reach the server. Is it still running?", "error");
  }

  abortController = null;
  setGenerating(false);
  questionInput.focus();
}

composerForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  if (isGenerating) {
    if (abortController) abortController.abort();
    return;
  }

  const question = questionInput.value.trim();
  questionInput.value = "";
  await submitQuestion(question);
});
// ---------- Message rendering ----------

// Renders bot text with light structure: turns "A) Label: value" / "1. Label: value"
// lines into styled key/value rows so multi-field answers are easy to scan.
function renderStructuredText(container, text) {
  const lines = text.split("\n");
  const kvPattern = /^\s*(?:[A-Za-z0-9]+[).])\s*([^:]{1,40}):\s*(.+)$/;
  let list = null;

  lines.forEach((line) => {
    if (!line.trim()) { list = null; return; }
    const match = line.match(kvPattern);

    if (match) {
      if (!list) {
        list = document.createElement("ul");
        list.className = "kv-list";
        container.appendChild(list);
      }
      const li = document.createElement("li");
      const strong = document.createElement("strong");
      strong.textContent = match[1].trim() + ": ";
      li.appendChild(strong);
      li.appendChild(document.createTextNode(match[2].trim()));
      list.appendChild(li);
    } else {
      list = null;
      const p = document.createElement("p");
      p.textContent = line;
      container.appendChild(p);
    }
  });
}

// Builds (or extends) a single always-visible icon row under the user's
// bubble holding Edit and, for the latest exchange, Regenerate too —
// both live together, matching how the person wants them grouped.
function attachUserControls(msgEl, messageId, text, includeRegenerate) {
  let row = msgEl.querySelector(".msg-controls");

  if (!row) {
    row = document.createElement("div");
    row.className = "msg-controls";
    msgEl.appendChild(row);

    const editBtn = document.createElement("button");
    editBtn.type = "button";
    editBtn.className = "icon-action-btn edit-msg-btn";
    editBtn.title = "Edit message";
    editBtn.setAttribute("aria-label", "Edit message");
    editBtn.innerHTML = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none"><path d="M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4L16.5 3.5z" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    editBtn.addEventListener("click", () => startEditMessage(messageId, text, msgEl));
    row.appendChild(editBtn);
  }

  if (includeRegenerate && !row.querySelector(".regenerate-btn")) {
    msgEl.dataset.hasRegenerate = "true";
    const regenBtn = document.createElement("button");
    regenBtn.type = "button";
    regenBtn.className = "icon-action-btn regenerate-btn";
    regenBtn.title = "Regenerate";
    regenBtn.setAttribute("aria-label", "Regenerate response");
    regenBtn.innerHTML = `<svg viewBox="0 0 24 24" width="15" height="15" fill="none"><path d="M3 12a9 9 0 0115.4-6.4M21 12a9 9 0 01-15.4 6.4M3 4v5h5M21 20v-5h-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
    regenBtn.addEventListener("click", () => regenerateLastAnswer(messageId, text));
    row.appendChild(regenBtn);
  }
}

function addMessage(text, type, tagText, messageId) {
  const el = document.createElement("div");
  el.className = `msg msg-${type}`;
  if (messageId) el.dataset.messageId = messageId;

  if (type === "bot") {
    renderStructuredText(el, text);
  } else {
    const p = document.createElement("p");
    p.textContent = text;
    el.appendChild(p);
  }

  if (tagText) {
    const tag = document.createElement("span");
    tag.className = "source-tag";
    tag.textContent = tagText;
    el.appendChild(tag);
  }

  if (type === "user" && messageId) {
    attachUserControls(el, messageId, text, false);
  }

  chatLog.appendChild(el);
  followBottomIfEnabled();
  return el;
}

function addImageResults(paths) {
  const el = document.createElement("div");
  el.className = "msg msg-bot";

  const p = document.createElement("p");
  p.textContent = paths.length ? "Closest matches:" : "No matching images found.";
  el.appendChild(p);

  if (paths.length) {
    const grid = document.createElement("div");
    grid.className = "image-results";
    paths.forEach((path) => {
      const filename = path.split(/[\\/]/).pop();
      const img = document.createElement("img");
      img.src = `${API_BASE}/images/${filename}`;
      img.alt = filename;
      grid.appendChild(img);
    });
    el.appendChild(grid);
  }

  chatLog.appendChild(el);
  followBottomIfEnabled();
  return el;
}

// Staged "thinking" indicator — cycles through a list of short status labels
// (e.g. "Searching documents…" → "Generating answer…") so the user sees
// what the RAG pipeline is doing instead of a blank spinner.
function addThinking(stages) {
  const labels = stages && stages.length ? stages : ["Thinking…"];
  const el = document.createElement("div");
  el.className = "msg msg-bot";

  const row = document.createElement("div");
  row.className = "thinking-row";

  const spinner = document.createElement("div");
  spinner.className = "thinking-spinner";

  const label = document.createElement("span");
  label.className = "thinking-label";
  label.textContent = labels[0];

  row.appendChild(spinner);
  row.appendChild(label);
  el.appendChild(row);
  chatLog.appendChild(el);
  followBottomIfEnabled();

  let i = 0;
  const interval = labels.length > 1 ? setInterval(() => {
    i = (i + 1) % labels.length;
    label.style.animation = "none";
    void label.offsetWidth;
    label.style.animation = "";
    label.textContent = labels[i];
  }, 1400) : null;

  const originalRemove = el.remove.bind(el);
  el.remove = () => {
    if (interval) clearInterval(interval);
    originalRemove();
  };

  return el;
}
// ---------- Edit & Regenerate ----------

// Deletes this message and everything after it from the DB. Returns
// false (without throwing) on failure so callers can show their own
// error message and bail out.
async function deleteMessagesFrom(messageId) {
  try {
    await fetch(`${API_BASE}/sessions/${currentSessionId}/messages/from/${messageId}`, {
      method: "DELETE"
    });
    return true;
  } catch (err) {
    return false;
  }
}

// Removes a message and every message after it from the visible chat log
// (mirrors what deleteMessagesFrom just did in the DB).
function truncateChatDomFrom(messageId) {
  const msgEl = chatLog.querySelector(`[data-message-id="${messageId}"]`);
  if (!msgEl) return;
  let node = msgEl;
  while (node) {
    const next = node.nextElementSibling;
    node.remove();
    node = next;
  }
}

// Inline edit, ChatGPT/Claude-style: the bubble itself turns into a textarea
// with Save/Cancel, instead of a browser prompt() popup.
function startEditMessage(messageId, oldText, msgEl) {
  if (isGenerating || !msgEl || msgEl.classList.contains("editing")) return;
  enterEditMode(msgEl, messageId, oldText);
}

function enterEditMode(msgEl, messageId, oldText) {
  msgEl.classList.add("editing");
  msgEl.innerHTML = "";

  const textarea = document.createElement("textarea");
  textarea.className = "edit-textarea";
  textarea.value = oldText;
  textarea.rows = 1;
  textarea.spellcheck = false;
  textarea.setAttribute("autocomplete", "off");
  textarea.setAttribute("autocorrect", "off");

  const btnRow = document.createElement("div");
  btnRow.className = "edit-btn-row";

  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "edit-cancel-btn";
  cancelBtn.textContent = "Cancel";

  const sendBtn = document.createElement("button");
  sendBtn.type = "button";
  sendBtn.className = "edit-save-btn";
  sendBtn.textContent = "Send";

  btnRow.appendChild(cancelBtn);
  btnRow.appendChild(sendBtn);
  msgEl.appendChild(textarea);
  msgEl.appendChild(btnRow);

  autoGrow(textarea);
  textarea.addEventListener("input", () => autoGrow(textarea));
  textarea.focus();
  textarea.setSelectionRange(textarea.value.length, textarea.value.length);

  textarea.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendBtn.click();
    } else if (e.key === "Escape") {
      cancelBtn.click();
    }
  });

  cancelBtn.addEventListener("click", () => renderUserBubble(msgEl, messageId, oldText));

  sendBtn.addEventListener("click", async () => {
    const newText = textarea.value.trim();
    if (!newText) return;
    if (newText === oldText) {
      renderUserBubble(msgEl, messageId, oldText);
      return;
    }
    await submitEditedMessage(messageId, newText, msgEl);
  });
}

function autoGrow(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = textarea.scrollHeight + "px";
}

// Rebuilds a user bubble back into its normal (non-editing) state.
function renderUserBubble(msgEl, messageId, text) {
  msgEl.classList.remove("editing");
  msgEl.innerHTML = "";

  const p = document.createElement("p");
  p.textContent = text;
  msgEl.appendChild(p);
  attachUserControls(msgEl, messageId, text, msgEl.dataset.hasRegenerate === "true");
}

async function submitEditedMessage(messageId, newText, msgEl) {
  const deleted = await deleteMessagesFrom(messageId);
  if (!deleted) {
    addSystemMessage("Could not edit message — try again.", true);
    renderUserBubble(msgEl, messageId, msgEl.dataset.originalText || newText);
    return;
  }

  // Remove this message and everything visually after it, then re-submit
  // the edited text as a fresh turn.
  let node = msgEl;
  while (node) {
    const next = node.nextElementSibling;
    node.remove();
    node = next;
  }

  await submitQuestion(newText);
}

async function regenerateLastAnswer(userMessageId, questionText) {
  if (isGenerating) return;

  const deleted = await deleteMessagesFrom(userMessageId);
  if (!deleted) {
    addSystemMessage("Could not regenerate — try again.", true);
    return;
  }

  truncateChatDomFrom(userMessageId);
  await submitQuestion(questionText);
}

// Called right after a bot answer finishes streaming. The freshly-created
// user/bot messages don't have their DB ids wired into the DOM yet (the id
// only exists once the turn is persisted), so this re-fetches the latest
// pair from the session and attaches the edit (✏️) and regenerate (🔄)
// controls to the correct DOM nodes, without touching messages that already
// have their controls attached.
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchLatestExchange() {
  const res = await fetch(`${API_BASE}/sessions/${currentSessionId}/messages`);
  const data = await res.json();
  return data.messages || [];
}

async function attachControlsForLatestExchange(questionText) {
  try {
    let msgs = [];
    let lastUser = null;
    let lastBot = null;

    // Poll for up to ~6s — the assistant turn is sometimes persisted to the
    // DB a beat after the stream finishes. Match the user message by its
    // actual text rather than assuming it's always exactly two from the end,
    // since other messages (system notices, etc.) can shift that offset.
    for (let attempt = 0; attempt < 15; attempt++) {
      msgs = await fetchLatestExchange();
      const userMsgs = msgs.filter((m) => m.role === "user");
      const botMsgs = msgs.filter((m) => m.role === "assistant");
      lastUser = questionText
        ? [...userMsgs].reverse().find((m) => m.content === questionText) || userMsgs[userMsgs.length - 1]
        : userMsgs[userMsgs.length - 1];
      lastBot = botMsgs[botMsgs.length - 1];

      if (lastUser && lastBot) break;
      await sleep(400);
    }

    if (!lastUser || !lastBot) {
      console.warn("attachControlsForLatestExchange: could not resolve latest exchange from", msgs);
      return;
    }

    const userEls = chatLog.querySelectorAll(".msg-user");
    const userEl = userEls[userEls.length - 1];
    if (userEl) {
      if (!userEl.dataset.messageId) userEl.dataset.messageId = lastUser.id;
      attachUserControls(userEl, lastUser.id, lastUser.content, true);
    }
  } catch (err) {
    console.warn("attachControlsForLatestExchange failed:", err);
  }
}

async function streamIntoMessage(res, thinkingEl, questionText) {
  const el = document.createElement("div");
  el.className = "msg msg-bot streaming";
  const p = document.createElement("p");
  const cursor = document.createElement("span");
  cursor.className = "stream-cursor";
  el.appendChild(p);
  el.appendChild(cursor);
  el.style.display = "none";
  chatLog.appendChild(el);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let fullText = "";
  let firstChunk = true;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const piece = decoder.decode(value, { stream: true });
      if (!piece) continue;

      if (firstChunk) {
        thinkingEl.remove();
        el.style.display = "";
        firstChunk = false;
      }

      fullText += piece;

      const markerIndex = fullText.indexOf("[[SOURCES]]");
      p.textContent = markerIndex === -1 ? fullText : fullText.slice(0, markerIndex);
      followBottomIfEnabled();
    }
  } finally {
    if (firstChunk) thinkingEl.remove();
    cursor.remove();
    el.classList.remove("streaming");

    let answerText = fullText;
    let sources = [];
    let confidence = null;
    const markerIndex = fullText.indexOf("[[SOURCES]]");
    if (markerIndex !== -1) {
      answerText = fullText.slice(0, markerIndex).trim();
      const rawJson = fullText.slice(markerIndex + "[[SOURCES]]".length).trim();
      try {
        const parsed = JSON.parse(rawJson);
        sources = parsed.sources || [];
        confidence = parsed.confidence || null;
      } catch (err) {
        sources = [];
      }
    }

    el.innerHTML = "";
    renderStructuredText(el, answerText);

    if (confidence) {
      const confBadge = document.createElement("span");
      confBadge.className = `confidence-badge confidence-${confidence}`;
      const labels = {
        high: "✅ Grounded in document",
        medium: "🟡 Partially grounded",
        low: "⚠️ Low confidence",
        no_context: "⚠️ No matching content found"
      };
      confBadge.textContent = labels[confidence] || "";
      el.appendChild(confBadge);
    }

    if (sources.length) {
      const sourceWrap = document.createElement("div");
      sourceWrap.className = "source-list";
      sources.forEach((s) => {
        const badge = document.createElement("span");
        badge.className = "source-tag";
        badge.textContent = s.page ? `📄 ${s.file} — Page ${s.page}` : `📄 ${s.file}`;
        sourceWrap.appendChild(badge);
      });
      el.appendChild(sourceWrap);
    } else {
      const tag = document.createElement("span");
      tag.className = "source-tag";
      tag.textContent = "retrieved from vector index";
      el.appendChild(tag);
    }

    // Feedback buttons — always shown, regardless of whether sources exist
    const feedbackRow = document.createElement("div");
    feedbackRow.className = "feedback-row";

    const upBtn = document.createElement("button");
    upBtn.className = "feedback-btn";
    upBtn.innerHTML = "👍";
    upBtn.setAttribute("aria-label", "Good answer");

    const downBtn = document.createElement("button");
    downBtn.className = "feedback-btn";
    downBtn.innerHTML = "👎";
    downBtn.setAttribute("aria-label", "Bad answer");

    async function sendFeedback(rating, clickedBtn) {
      upBtn.disabled = true;
      downBtn.disabled = true;
      clickedBtn.classList.add("feedback-selected");

      try {
        await fetch(`${API_BASE}/feedback`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: currentSessionId,
            question: questionText,
            answer: answerText,
            rating
          })
        });
      } catch (err) {
        // silent fail — feedback is non-critical
      }
    }

    upBtn.addEventListener("click", () => sendFeedback("up", upBtn));
    downBtn.addEventListener("click", () => sendFeedback("down", downBtn));

    feedbackRow.appendChild(upBtn);
    feedbackRow.appendChild(downBtn);
    el.appendChild(feedbackRow);
  }
}

// ---------- Init ----------

async function initApp() {
  try {
    const res = await fetch(`${API_BASE}/sessions`);
    const data = await res.json();
    if (data.sessions.length > 0) {
      await switchSession(data.sessions[0].id);
    } else {
      await startNewChat();
    }
  } catch (err) {
    console.error("Failed to load sessions:", err);
  }
}

// On page load: if we already have a token (from a previous login),
// skip the auth screen and go straight into the app. Otherwise show login/signup.
// Always require login on page load — no persisted auto-login.
showAuth();