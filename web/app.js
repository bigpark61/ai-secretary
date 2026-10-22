const state = { apiBase: window.location.origin, conversationId: null, busy: false };
const metricKeys = [
  "production_volume",
  "defect_rate",
  "energy_consumption",
  "energy_efficiency",
  "downtime_percentage",
  "maintenance_hours",
  "energy_per_unit",
];

const $ = (selector) => document.querySelector(selector);
const number = (value, digits = 2) =>
  Number(value).toLocaleString("ko-KR", { maximumFractionDigits: digits });

async function configureApi() {
  const response = await fetch("/api/config");
  if (response.status === 404) return;
  if (!response.ok) throw new Error("프론트엔드 API 설정을 불러오지 못했습니다.");
  const config = await response.json();
  if (config.apiBaseUrl) state.apiBase = config.apiBaseUrl;
}

async function api(path, options = {}) {
  const response = await fetch(`${state.apiBase}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `요청에 실패했습니다 (${response.status}).`);
  }
  return response.status === 204 ? null : response.json();
}

function showNotice(message, isError = false) {
  const notice = $("#notice");
  notice.textContent = message;
  notice.classList.toggle("error", isError);
  notice.hidden = false;
  window.clearTimeout(showNotice.timer);
  showNotice.timer = window.setTimeout(() => { notice.hidden = true; }, 6000);
}

async function refreshAll() {
  await Promise.all([loadHealth(), loadSummary(), loadData()]);
}

async function loadHealth() {
  const indicator = $(".connection-indicator");
  try {
    await api("/api/health");
    indicator.classList.remove("failed");
    indicator.classList.add("ready");
    $("#connection-status").textContent = "API 연결됨";
  } catch {
    indicator.classList.remove("ready");
    indicator.classList.add("failed");
    $("#connection-status").textContent = "API 연결 확인 필요";
  }
}

async function loadSummary() {
  try {
    const summary = await api("/api/data/summary");
    const cards = [
      ["전체 레코드", `${number(summary.count, 0)}개`, "Firestore 저장 데이터"],
      ["평균 생산량", summary.metrics.production_volume ? number(summary.metrics.production_volume.average) : "-", "전체 표본 평균"],
      ["평균 불량률", summary.metrics.defect_rate ? `${number(summary.metrics.defect_rate.average)}%` : "-", "전체 표본 평균"],
      ["평균 에너지 소비", summary.metrics.energy_consumption ? number(summary.metrics.energy_consumption.average) : "-", "전체 표본 평균"],
    ];
    $("#summary-strip").replaceChildren(...cards.map(([label, value, caption]) => {
      const card = document.createElement("article");
      card.className = "summary-card";
      card.innerHTML = `<span>${label}</span><strong>${value}</strong><small>${caption}</small>`;
      return card;
    }));
    if (summary.trend) {
      const trendText = `표본 순서 비교 · 생산량 ${summary.trend.production_volume.direction} ${formatChange(summary.trend.production_volume.change_percent)} · 불량률 ${summary.trend.defect_rate.direction} ${formatChange(summary.trend.defect_rate.change_percent)}`;
      const trend = document.createElement("small");
      trend.className = "trend-note";
      trend.textContent = trendText;
      $("#summary-strip").append(trend);
    }
  } catch (error) {
    showNotice(error.message, true);
  }
}

function formatChange(value) {
  return value === null ? "(기준 평균 0)" : `${Math.abs(value)}%`;
}

async function loadData() {
  try {
    const result = await api("/api/data");
    $("#data-count").textContent = `${number(result.count, 0)} records`;
    $("#empty-data").hidden = result.items.length > 0;
    $("#data-rows").replaceChildren(...result.items.map((record) => {
      const row = document.createElement("tr");
      const cells = [
        record.source_record_id ? `#${record.source_record_id}` : record.id.slice(0, 8),
        number(record.production_volume),
        `${number(record.defect_rate)}%`,
        number(record.energy_consumption),
        number(record.energy_efficiency, 3),
        `${number(record.downtime_percentage)}%`,
        number(record.maintenance_hours),
      ];
      row.append(...cells.map((value) => {
        const cell = document.createElement("td");
        cell.textContent = value;
        return cell;
      }));
      const action = document.createElement("td");
      const remove = document.createElement("button");
      remove.className = "delete-button";
      remove.type = "button";
      remove.textContent = "삭제";
      remove.addEventListener("click", () => deleteRecord(record.id));
      action.append(remove);
      row.append(action);
      return row;
    }));
  } catch (error) {
    showNotice(error.message, true);
  }
}

async function deleteRecord(id) {
  if (!window.confirm("이 레코드를 삭제할까요?")) return;
  try {
    await api(`/api/data/${encodeURIComponent(id)}`, { method: "DELETE" });
    showNotice("레코드를 삭제했습니다.");
    await refreshAll();
  } catch (error) {
    showNotice(error.message, true);
  }
}

function appendMessage(role, content) {
  const welcome = $(".welcome-card");
  if (welcome) welcome.remove();
  const message = document.createElement("div");
  message.className = `message ${role}`;
  const label = document.createElement("span");
  label.className = "message-label";
  label.textContent = role === "user" ? "나" : "제조 분석 어시스턴트";
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.textContent = content;
  message.append(label, bubble);
  $("#chat-messages").append(message);
  $("#chat-messages").scrollTop = $("#chat-messages").scrollHeight;
}

function renderConversation(messages) {
  $("#chat-messages").replaceChildren();
  messages.forEach((message) => appendMessage(message.role, message.content));
}

async function sendMessage(text) {
  if (state.busy) return;
  state.busy = true;
  $("#send-button").disabled = true;
  appendMessage("user", text);
  const pending = document.createElement("div");
  pending.className = "message assistant";
  pending.innerHTML = '<span class="message-label">제조 분석 어시스턴트</span><div class="message-bubble">데이터를 확인하고 있습니다...</div>';
  $("#chat-messages").append(pending);
  try {
    const response = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message: text, conversation_id: state.conversationId }),
    });
    pending.remove();
    state.conversationId = response.conversation_id;
    appendMessage("assistant", response.answer);
    await loadSummary();
  } catch (error) {
    pending.remove();
    showNotice(error.message, true);
    appendMessage("assistant", `응답을 가져오지 못했습니다: ${error.message}`);
  } finally {
    state.busy = false;
    $("#send-button").disabled = false;
  }
}

async function loadHistory() {
  try {
    const { items } = await api("/api/conversations");
    $("#empty-history").hidden = items.length > 0;
    $("#conversation-list").replaceChildren(...items.map((item) => {
      const card = document.createElement("article");
      card.className = "conversation-card";
      const main = document.createElement("div");
      main.className = "conversation-main";
      const title = document.createElement("strong");
      title.textContent = item.title || "새 대화";
      const date = document.createElement("small");
      date.textContent = item.updated_at ? new Date(item.updated_at).toLocaleString("ko-KR") : "";
      main.append(title, date);
      const actions = document.createElement("div");
      actions.className = "conversation-actions";
      const load = document.createElement("button");
      load.className = "load-button";
      load.textContent = "불러오기";
      load.addEventListener("click", () => openConversation(item.id));
      const remove = document.createElement("button");
      remove.className = "delete-button";
      remove.textContent = "삭제";
      remove.addEventListener("click", () => removeConversation(item.id));
      actions.append(load, remove);
      card.append(main, actions);
      return card;
    }));
  } catch (error) {
    showNotice(error.message, true);
  }
}

async function openConversation(id) {
  try {
    const conversation = await api(`/api/conversations/${encodeURIComponent(id)}`);
    state.conversationId = conversation.id;
    renderConversation(conversation.messages || []);
    activateView("chat");
  } catch (error) {
    showNotice(error.message, true);
  }
}

async function removeConversation(id) {
  if (!window.confirm("이 대화 기록을 삭제할까요?")) return;
  try {
    await api(`/api/conversations/${encodeURIComponent(id)}`, { method: "DELETE" });
    await loadHistory();
    showNotice("대화 기록을 삭제했습니다.");
  } catch (error) {
    showNotice(error.message, true);
  }
}

function activateView(name) {
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.view === name);
  });
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active", view.id === `${name}-view`);
  });
  $("#page-title").textContent = {
    chat: "AI 데이터 비서",
    data: "데이터 관리",
    history: "대화 기록",
  }[name];
  if (name === "history") loadHistory();
  if (name === "data") loadData();
}

document.querySelectorAll(".nav-item").forEach((item) => {
  item.addEventListener("click", () => activateView(item.dataset.view));
});
document.querySelectorAll(".suggestion").forEach((button) => {
  button.addEventListener("click", () => sendMessage(button.textContent));
});
$("#chat-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const input = $("#chat-input");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  sendMessage(message);
});
$("#new-chat-button").addEventListener("click", () => {
  state.conversationId = null;
  $("#chat-messages").innerHTML = `
    <div class="welcome-card">
      <span class="welcome-icon">✳</span><h2>무엇을 분석해 볼까요?</h2>
      <p>생산량, 불량률, 에너지 사용량 등 제조 데이터를 질문해 보세요.</p>
    </div>`;
});
$("#refresh-button").addEventListener("click", () => refreshAll());
$("#data-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const record = Object.fromEntries(metricKeys.map((key) => [key, Number(form.get(key))]));
  try {
    await api("/api/data", { method: "POST", body: JSON.stringify(record) });
    event.currentTarget.reset();
    showNotice("새 레코드를 Firestore에 저장했습니다.");
    await refreshAll();
  } catch (error) {
    showNotice(error.message, true);
  }
});

configureApi()
  .then(refreshAll)
  .catch((error) => showNotice(error.message, true));
