document.addEventListener("DOMContentLoaded", () => {
  const askForm = document.getElementById("askForm");
  const questionInput = document.getElementById("questionInput");
  const sendBtn = document.getElementById("sendBtn");
  const sendIcon = document.getElementById("sendIcon");
  const loadingSpinner = document.getElementById("loadingSpinner");
  const chatContainer = document.getElementById("chatContainer");
  const healthPill = document.getElementById("healthPill");
  const healthStatusText = document.getElementById("healthStatusText");

  // Check health on boot
  checkHealth();

  // Setup chip click handlers
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const q = chip.getAttribute("data-question");
      if (q) {
        questionInput.value = q;
        submitQuestion(q);
      }
    });
  });

  // Auto-resize textarea
  questionInput.addEventListener("input", () => {
    questionInput.style.height = "auto";
    questionInput.style.height = Math.min(questionInput.scrollHeight, 120) + "px";
  });

  // Handle Enter to submit (Shift+Enter for newline)
  questionInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      askForm.dispatchEvent(new Event("submit"));
    }
  });

  // Form submission
  askForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const question = questionInput.value.trim();
    if (!question) return;
    submitQuestion(question);
  });

  async function checkHealth() {
    try {
      const res = await fetch("/health");
      if (res.ok) {
        const data = await res.json();
        const dot = healthPill.querySelector(".status-dot");
        dot.classList.add("healthy");
        
        let statusNotes = [];
        if (data.superhero_api_configured) statusNotes.push("Hero API: Ready");
        if (data.llm_configured) statusNotes.push(`LLM: ${data.active_provider}`);
        else statusNotes.push("LLM: Preview Mode");
        
        healthStatusText.textContent = statusNotes.join(" • ");
      } else {
        healthStatusText.textContent = "API Offline";
      }
    } catch (err) {
      healthStatusText.textContent = "Connecting...";
    }
  }

  async function submitQuestion(question) {
    // Append user message
    appendUserMessage(question);
    questionInput.value = "";
    questionInput.style.height = "auto";

    // Set loading state
    setLoading(true);
    const loadingBubbleId = appendLoadingBubble();

    try {
      const startTime = performance.now();
      const res = await fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });

      const clientLatency = Math.round(performance.now() - startTime);
      const data = await res.json();

      removeBubble(loadingBubbleId);

      if (!res.ok) {
        let errorMsg = "Failed to process question.";
        if (data.details) {
          errorMsg = data.details.map((d) => `${d.field}: ${d.message}`).join(", ");
        } else if (data.detail) {
          errorMsg = data.detail;
        }
        appendErrorMessage(errorMsg);
        return;
      }

      appendBotMessage(data, clientLatency);
    } catch (err) {
      removeBubble(loadingBubbleId);
      appendErrorMessage("Network error: Could not reach the FastAPI server.");
    } finally {
      setLoading(false);
      checkHealth();
    }
  }

  function setLoading(isLoading) {
    sendBtn.disabled = isLoading;
    questionInput.disabled = isLoading;
    if (isLoading) {
      sendIcon.classList.add("hidden");
      loadingSpinner.classList.remove("hidden");
    } else {
      sendIcon.classList.remove("hidden");
      loadingSpinner.classList.add("hidden");
      questionInput.focus();
    }
  }

  function appendUserMessage(text) {
    const bubble = document.createElement("div");
    bubble.className = "message-bubble user-message";
    bubble.innerHTML = `<div class="message-body">${escapeHtml(text)}</div>`;
    chatContainer.appendChild(bubble);
    scrollToBottom();
  }

  function appendLoadingBubble() {
    const id = "loading-" + Date.now();
    const bubble = document.createElement("div");
    bubble.id = id;
    bubble.className = "message-bubble bot-message";
    bubble.innerHTML = `
      <div class="message-header">
        <span class="bot-badge">Routing & Retrieving...</span>
      </div>
      <div class="message-body">
        <div class="typing-indicator">
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
          <div class="typing-dot"></div>
        </div>
      </div>
    `;
    chatContainer.appendChild(bubble);
    scrollToBottom();
    return id;
  }

  function removeBubble(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function appendErrorMessage(errorText) {
    const bubble = document.createElement("div");
    bubble.className = "message-bubble bot-message";
    bubble.style.borderColor = "rgba(244, 63, 94, 0.4)";
    bubble.innerHTML = `
      <div class="message-header">
        <span class="bot-badge" style="background: rgba(244,63,94,0.15); color: #fb7185; border-color: rgba(244,63,94,0.3);">Error</span>
      </div>
      <div class="message-body" style="color: #fca5a5;">
        ${escapeHtml(errorText)}
      </div>
    `;
    chatContainer.appendChild(bubble);
    scrollToBottom();
  }

  function appendBotMessage(data, clientLatency) {
    const bubble = document.createElement("div");
    bubble.className = "message-bubble bot-message";

    const formattedAnswer = renderMarkdown(data.answer);
    const route = data.route || "general";
    const latency = data.latency_ms || clientLatency;
    const llm = data.llm_provider || "Hosted LLM";

    // Sources badges
    let sourcesBadgesHtml = "";
    if (data.sources && data.sources.length) {
      sourcesBadgesHtml = data.sources
        .map((src) => {
          let badgeClass = "route";
          if (src.toLowerCase().includes("superhero")) badgeClass = "superhero";
          else if (src.toLowerCase().includes("dataset") || src.toLowerCase().includes(".txt")) badgeClass = "dataset";
          return `<span class="source-badge ${badgeClass}">${escapeHtml(src)}</span>`;
        })
        .join("");
    }

    bubble.innerHTML = `
      <div class="message-header">
        <span class="bot-badge">Route: ${escapeHtml(route.toUpperCase())}</span>
        <span class="timestamp">${new Date().toLocaleTimeString()}</span>
      </div>
      <div class="message-body">
        ${formattedAnswer}
      </div>
      <div class="message-meta">
        <div class="sources-row">
          <span class="sources-label">Sources:</span>
          ${sourcesBadgesHtml}
        </div>
        <div class="meta-stats">
          <span>⚡ ${latency}ms</span>
          <span>•</span>
          <span>🤖 ${escapeHtml(llm)}</span>
        </div>
      </div>
    `;

    chatContainer.appendChild(bubble);
    scrollToBottom();
  }

  function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function renderMarkdown(md) {
    if (!md) return "";
    let html = escapeHtml(md);

    // Headers
    html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");
    html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>");
    html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>");

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Blockquote
    html = html.replace(/^> (.*$)/gim, '<blockquote style="border-left: 3px solid var(--accent-purple); padding-left: 0.75rem; margin: 0.5rem 0; color: #cbd5e1;">$1</blockquote>');

    // Code inline
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

    // Unordered lists
    html = html.replace(/^\s*-\s+(.*$)/gim, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>)/gms, "<ul>$1</ul>");
    // Clean nested ul wraps
    html = html.replace(/<\/ul>\s*<ul>/g, "");

    // Paragraph line breaks
    html = html.replace(/\n\n/g, "</p><p>");
    html = `<p>${html}</p>`;
    // Clean empty tags
    html = html.replace(/<p><\/p>/g, "");
    html = html.replace(/<p><h([1-3])>/g, "<h$1>");
    html = html.replace(/<\/h([1-3])><\/p>/g, "</h$1>");
    html = html.replace(/<p><ul>/g, "<ul>");
    html = html.replace(/<\/ul><\/p>/g, "</ul>");

    return html;
  }
});
