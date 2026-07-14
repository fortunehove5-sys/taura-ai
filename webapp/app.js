const API_BASE = ""; // same-origin
let sessionId = crypto.randomUUID();
let channel = "voice_call";

const CHANNEL_LABELS = {
  voice_call: "Voice / IVR session",
  ussd: "USSD session (*888#)",
  whatsapp: "WhatsApp session",
};

const QUICK_REPLIES = {
  fresh: [
    { label: "Mhoro (SN)", text: "Mhoro" },
    { label: "Sawubona (ND)", text: "Sawubona" },
    { label: "YES / Hongu", text: "hongu" },
  ],
  after_consent: [
    { label: "Maize price · Mutare", text: "mutengo wechibage muMutare" },
    { label: "Rain in Gokwe?", text: "kuzonaya here muGokwe" },
    { label: "Flood alert · Chipinge", text: "isikhukhula eChipinge" },
    { label: "Savings info", text: "ndinoda kuchengetedza mari" },
    { label: "Loan info", text: "ngicela isikwelede" },
    { label: "Speak to a person", text: "ndinoda kutaura nemunhu" },
  ],
};

const EXAMPLES = [
  { lang: "SN", text: "mutengo wechibage muMutare", label: "Ask maize price in Mutare (Shona)" },
  { lang: "ND", text: "inani lomumbila eBulawayo", label: "Ask maize price in Bulawayo (Ndebele)" },
  { lang: "SN", text: "kuzonaya here muGokwe", label: "Ask about rain in Gokwe (Shona)" },
  { lang: "ND", text: "isikhukhula eChipinge", label: "Ask about flood alert in Chipinge (Ndebele)" },
  { lang: "EN", text: "I want a loan", label: "Ask about a loan (English, triggers handoff)" },
];

const chatWindow = document.getElementById("chatWindow");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const quickRepliesEl = document.getElementById("quickReplies");
const exampleListEl = document.getElementById("exampleList");
const channelLabelEl = document.getElementById("channelLabel");

let consentResolved = false;

function renderQuickReplies() {
  const set = consentResolved ? QUICK_REPLIES.after_consent : QUICK_REPLIES.fresh;
  quickRepliesEl.innerHTML = "";
  set.forEach((qr) => {
    const btn = document.createElement("button");
    btn.textContent = qr.label;
    btn.addEventListener("click", () => sendMessage(qr.text));
    quickRepliesEl.appendChild(btn);
  });
}

function renderExamples() {
  exampleListEl.innerHTML = "";
  EXAMPLES.forEach((ex) => {
    const btn = document.createElement("button");
    btn.innerHTML = `<span class="lang-tag">${ex.lang}</span>${ex.label}`;
    btn.addEventListener("click", () => sendMessage(ex.text));
    exampleListEl.appendChild(btn);
  });
}

function addBubble(text, sender, groundingLabel, escalated) {
  const bubble = document.createElement("div");
  bubble.className = `bubble ${sender}` + (escalated ? " escalated" : "");
  const textNode = document.createElement("span");
  textNode.textContent = text;
  bubble.appendChild(textNode);

  if (sender === "bot") {
    const grounding = document.createElement("span");
    if (groundingLabel) {
      grounding.className = "grounding";
      grounding.textContent = `grounded in: ${groundingLabel}`;
    } else {
      grounding.className = "grounding none";
      grounding.textContent = "no source record retrieved";
    }
    bubble.appendChild(grounding);
  }
  chatWindow.appendChild(bubble);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function sendMessage(text) {
  if (!text || !text.trim()) return;
  addBubble(text, "user");
  chatInput.value = "";

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: text, channel }),
    });
    const data = await res.json();

    if (data.intent === "consent_prompt") {
      consentResolved = false;
    } else {
      consentResolved = true;
    }

    addBubble(data.response, "bot", data.retrieved_source_id, data.escalated);
    document.getElementById("fLanguage").textContent = data.language;
    document.getElementById("fIntent").textContent = data.intent;
    document.getElementById("fEscalated").textContent = data.escalated ? "yes" : "no";
    renderQuickReplies();
  } catch (err) {
    addBubble("Connection error — is the backend running? (uvicorn backend.app:app)", "bot", null, false);
    console.error(err);
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage(chatInput.value);
});

document.querySelectorAll(".channel-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".channel-btn").forEach((b) => {
      b.classList.remove("active");
      b.setAttribute("aria-selected", "false");
    });
    btn.classList.add("active");
    btn.setAttribute("aria-selected", "true");
    channel = btn.dataset.channel;
    channelLabelEl.textContent = CHANNEL_LABELS[channel];
    document.getElementById("fChannel").textContent = CHANNEL_LABELS[channel];
  });
});

document.getElementById("resetBtn").addEventListener("click", () => {
  sessionId = crypto.randomUUID();
  consentResolved = false;
  chatWindow.innerHTML = "";
  const note = document.createElement("div");
  note.className = "system-note";
  note.textContent = "New session started. Consent will be requested before any advice is given.";
  chatWindow.appendChild(note);
  document.getElementById("fLanguage").textContent = "—";
  document.getElementById("fIntent").textContent = "—";
  document.getElementById("fEscalated").textContent = "—";
  renderQuickReplies();
});

renderQuickReplies();
renderExamples();
