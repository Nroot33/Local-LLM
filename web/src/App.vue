<script setup>
import { nextTick, onMounted, onUnmounted, ref } from "vue";
import DOMPurify from "dompurify";
import { marked } from "marked";
import markedKatex from "marked-katex-extension";
import PotatoMark from "./PotatoMark.vue";

marked.use(markedKatex({ throwOnError: false, nonStandard: true }));

const messages = ref([]);
const input = ref("");
const searching = ref(true);
const loading = ref(false);
const online = ref(false);
const model = ref("qwen3:8b");
const scrollArea = ref(null);
const textarea = ref(null);
const imageInput = ref(null);
const cameraInput = ref(null);
const selectedImage = ref(null);
const imageError = ref("");
const draggingImage = ref(false);
let dragDepth = 0;
const gpu = ref(null);
const searchProvider = ref("-");
const visionModel = ref("qwen3-vl:4b");
const isPetMode = new URLSearchParams(window.location.search).has("pet");
const canSpeak = typeof window.Audio === "function";
const voiceEnabled = ref(canSpeak && isPetMode && window.localStorage.getItem("thunder-potato-voice") !== "off");
const speakingIndex = ref(-1);
let statusTimer;
let speechAudio = null;
let speechAbort = null;
let speechUrl = null;

function speechText(text) {
  return text
    .replace(/```[\s\S]*?```/g, "코드 블록")
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/\$+/g, "")
    .replace(/[*_`#>|]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function stopSpeaking() {
  speechAbort?.abort();
  speechAbort = null;
  speechAudio?.pause();
  speechAudio = null;
  if (speechUrl) URL.revokeObjectURL(speechUrl);
  speechUrl = null;
  speakingIndex.value = -1;
}

async function speakAnswer(text, index) {
  if (!canSpeak || !text?.trim()) return;
  stopSpeaking();
  const controller = new AbortController();
  speechAbort = controller;
  speakingIndex.value = index;
  try {
    const response = await fetch("/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: speechText(text).slice(0, 1000) }),
      signal: controller.signal,
    });
    if (!response.ok) throw new Error("음성 생성 실패");
    const blob = await response.blob();
    if (controller.signal.aborted) return;
    speechUrl = URL.createObjectURL(blob);
    speechAudio = new Audio(speechUrl);
    speechAudio.onended = stopSpeaking;
    speechAudio.onerror = stopSpeaking;
    await speechAudio.play();
  } catch (error) {
    if (error.name !== "AbortError") {
      console.error(error);
      stopSpeaking();
    }
  }
}

function toggleVoice() {
  voiceEnabled.value = !voiceEnabled.value;
  window.localStorage.setItem("thunder-potato-voice", voiceEnabled.value ? "on" : "off");
  if (!voiceEnabled.value) stopSpeaking();
}

async function desktopAction(action) {
  const api = window.pywebview?.api;
  if (api && typeof api[action] === "function") await api[action]();
}

async function checkStatus() {
  try {
    const response = await fetch("/status");
    if (!response.ok) throw new Error();
    const data = await response.json();
    online.value = !!data.server_connected;
    model.value = data.model || model.value;
    visionModel.value = data.vision_model || visionModel.value;
    searchProvider.value = data.search_provider || "-";
    gpu.value = data.gpu || null;
  } catch {
    online.value = false;
    gpu.value = null;
  }
}

async function sendMessage(text = input.value) {
  const question = text.trim();
  if ((!question && !selectedImage.value) || loading.value) return;
  stopSpeaking();
  const attachedImage = selectedImage.value;
  const history = messages.value
    .filter((item) => item.role === "user" || item.role === "assistant")
    .slice(-12)
    .map((item) => ({ role: item.role, content: item.text || (item.image ? "[이미지 첨부]" : "") }));
  messages.value.push({
    role: "user",
    text: question,
    image: attachedImage?.url,
  });
  input.value = "";
  selectedImage.value = null;
  if (imageInput.value) imageInput.value.value = "";
  if (cameraInput.value) cameraInput.value.value = "";
  loading.value = true;
  await scrollToBottom();
  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: question,
        image: attachedImage?.dataUrl || null,
        web_search: searching.value && !attachedImage,
        max_results: 5,
        history,
      }),
    });
    const data = await response.json();
    if (!response.ok)
      throw new Error(data.detail || `서버 오류 (${response.status})`);
    messages.value.push({
      role: "assistant",
      text: data.answer,
      searched: data.searched,
      fastMath: data.fast_math,
    });
    if (voiceEnabled.value) speakAnswer(data.answer, messages.value.length - 1);
    online.value = true;
  } catch (error) {
    messages.value.push({
      role: "error",
      text: error.message || "답변을 가져오지 못했습니다.",
    });
    await checkStatus();
  } finally {
    loading.value = false;
    await scrollToBottom();
    textarea.value?.focus();
  }
}

function attachImage(event) {
  const file = event.target.files?.[0];
  if (file) attachImageFile(file);
  event.target.value = "";
}

function attachImageFile(file) {
  imageError.value = "";
  if (!file) return;
  if (loading.value) {
    imageError.value = "답변이 끝난 뒤 이미지를 첨부해 주세요.";
    return;
  }
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
    imageError.value = "JPG, PNG, WEBP 이미지만 첨부할 수 있어요.";
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    imageError.value = "이미지는 10MB 이하여야 해요.";
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    selectedImage.value = {
      name: file.name || "붙여넣은 이미지",
      dataUrl: reader.result,
      url: reader.result,
    };
    textarea.value?.focus();
  };
  reader.onerror = () => {
    imageError.value = "이미지를 읽지 못했어요.";
  };
  reader.readAsDataURL(file);
}

function hasDraggedFiles(event) {
  return Array.from(event.dataTransfer?.types || []).includes("Files");
}

function onDragEnter(event) {
  if (!hasDraggedFiles(event)) return;
  event.preventDefault();
  dragDepth += 1;
  draggingImage.value = true;
}

function onDragOver(event) {
  if (!hasDraggedFiles(event)) return;
  event.preventDefault();
  event.dataTransfer.dropEffect = "copy";
}

function onDragLeave(event) {
  if (!hasDraggedFiles(event)) return;
  dragDepth = Math.max(0, dragDepth - 1);
  if (dragDepth === 0) draggingImage.value = false;
}

function onDrop(event) {
  if (!hasDraggedFiles(event)) return;
  event.preventDefault();
  dragDepth = 0;
  draggingImage.value = false;
  const file = event.dataTransfer?.files?.[0];
  if (file) attachImageFile(file);
}

function onPaste(event) {
  const imageItem = Array.from(event.clipboardData?.items || []).find((item) => item.kind === "file" && item.type.startsWith("image/"));
  if (!imageItem) return;
  event.preventDefault();
  const file = imageItem.getAsFile();
  if (file) attachImageFile(file);
}

function clearImage() {
  selectedImage.value = null;
  if (imageInput.value) imageInput.value.value = "";
  if (cameraInput.value) cameraInput.value.value = "";
}

async function scrollToBottom() {
  await nextTick();
  scrollArea.value?.scrollTo({
    top: scrollArea.value.scrollHeight,
    behavior: "smooth",
  });
}

function onKeydown(event) {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    sendMessage();
  }
}

function renderAnswer(text) {
  const normalized = text
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, math) => `\n$$\n${math}\n$$\n`)
    .replace(/\\\(([\s\S]*?)\\\)/g, (_, math) => `$${math}$`);
  return DOMPurify.sanitize(marked.parse(normalized, { breaks: true }));
}

onMounted(() => {
  checkStatus();
  statusTimer = window.setInterval(checkStatus, 5000);
  document.addEventListener("paste", onPaste);
});
onUnmounted(() => {
  window.clearInterval(statusTimer);
  document.removeEventListener("paste", onPaste);
  stopSpeaking();
});
</script>

<template>
  <div class="shell" @dragenter="onDragEnter" @dragover="onDragOver" @dragleave="onDragLeave" @drop="onDrop">
    <div v-if="draggingImage" class="drop-overlay" aria-hidden="true"><div class="drop-overlay-card"><PotatoMark :size="66" /><strong>이미지를 여기에 놓아줘!</strong><span>JPG · PNG · WEBP</span></div></div>
    <main class="main">
      <section class="chat-area">
      <header v-if="isPetMode" class="pet-header">
        <div class="pet-title-row">
          <div class="pet-drag pywebview-drag-region"><span aria-hidden="true">⚡</span> 천둥감자</div>
          <div class="pet-window-actions">
            <button type="button" aria-label="천둥감자 최소화" @click="desktopAction('minimize')">−</button>
            <button type="button" aria-label="천둥감자 닫기" @click="desktopAction('close')">×</button>
          </div>
        </div>
        <div class="pet-hero">
          <div :class="['pet-character', { thinking: loading }]" aria-hidden="true"><PotatoMark :size="100" /></div>
          <div class="pet-hero-copy">
            <strong>{{ loading ? "생각하는 중..." : "여기 있어요" }}</strong>
            <span>{{ online ? "천둥감자와 이야기해요" : "서버 연결을 확인 중이에요" }}</span>
          </div>
        </div>
        <div class="pet-preferences">
          <label class="pet-search"><span>웹 검색</span><input v-model="searching" type="checkbox" :disabled="loading" /><span>{{ searching ? "켜짐" : "꺼짐" }}</span></label>
          <button v-if="canSpeak" type="button" class="pet-voice" :aria-pressed="voiceEnabled" @click="toggleVoice">{{ voiceEnabled ? "🔊 음성 켜짐" : "🔇 음성 꺼짐" }}</button>
        </div>
      </header>
      <div class="conversation" ref="scrollArea">
        <div v-if="messages.length === 0" class="welcome">
          <template v-if="isPetMode"><p class="pet-welcome">말을 걸어 주세요. 질문도, 사진도 좋아요.</p></template>
          <template v-else><div class="welcome-icon"><PotatoMark :size="118" /></div><div class="eyebrow">THUNDER POTATO · LOCAL AI</div></template>
        </div>
        <div v-else class="message-list">
          <div
            v-for="(message, index) in messages"
            :key="index"
            :class="['message-row', message.role]"
          >
            <div v-if="message.role !== 'user'" class="avatar">
              <span v-if="message.role === 'error'">!</span
              ><PotatoMark v-else :size="29" />
            </div>
            <div class="message-content">
              <div v-if="message.role !== 'user'" class="message-label">
                {{ message.role === "error" ? "오류" : "천둥감자" }}
                <span v-if="message.searched">· 웹 검색 사용</span>
                <span v-if="message.fastMath">· 빠른 답변 · 검증 필요</span>
                <button v-if="isPetMode && canSpeak && message.role === 'assistant'" type="button" class="message-voice" @click="speakingIndex === index ? stopSpeaking() : speakAnswer(message.text, index)">{{ speakingIndex === index ? "■ 멈춤" : "▶ 다시 듣기" }}</button>
              </div>
              <div
                v-if="message.role === 'assistant'"
                class="message-text rendered"
                v-html="renderAnswer(message.text)"
              ></div>
              <div v-else class="message-text">{{ message.text }}</div>
              <img
                v-if="message.image"
                class="message-image"
                :src="message.image"
                alt="첨부한 이미지"
              />
            </div>
          </div>
          <div v-if="loading" class="message-row assistant">
            <div class="avatar"><PotatoMark :size="29" /></div>
            <div class="message-content">
              <div class="message-label">천둥감자</div>
              <div class="thinking">
                <i></i><i></i><i></i><span>감자가 생각하는 중...</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="composer-wrap">
        <div class="composer">
          <div v-if="selectedImage" class="attachment-preview">
            <img :src="selectedImage.url" alt="첨부 이미지 미리보기" />
            <span>{{ selectedImage.name }}</span>
            <button type="button" @click="clearImage" aria-label="이미지 제거">
              ×
            </button>
          </div>
          <div v-if="imageError" class="attachment-error">{{ imageError }}</div>
          <textarea
            ref="textarea"
            v-model="input"
            @keydown="onKeydown"
            rows="2"
            :disabled="loading"
          ></textarea>
          <div class="composer-bottom">
            <div class="composer-actions">
              <input
                ref="imageInput"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                hidden
                @change="attachImage"
              /><input
                ref="cameraInput"
                type="file"
                accept="image/*"
                capture="environment"
                hidden
                @change="attachImage"
              /><button
                type="button"
                class="attach-button"
                @click="imageInput?.click()"
                :disabled="loading"
                aria-label="이미지 첨부"
              >
                ＋ 이미지</button
              ><button
                type="button"
                class="attach-button camera-button"
                @click="cameraInput?.click()"
                :disabled="loading"
                aria-label="카메라로 촬영"
              >📷 촬영</button
              ><span>Enter로 전송 · Shift+Enter로 줄바꿈</span>
            </div>
            <button
              class="send"
              :disabled="(!input.trim() && !selectedImage) || loading"
              @click="sendMessage()"
              aria-label="메시지 전송"
            >
              ↑
            </button>
          </div>
        </div>
      </div>
      </section>
      <aside class="state-panel" aria-label="시스템 상태">
        <div class="state-heading"><PotatoMark :size="27" /><strong>천둥감자 상태</strong><span>LIVE</span></div>
        <div class="state-refresh">5초마다 갱신</div>
        <div class="state-row"><span>로컬 서버</span><strong :class="{ disconnected: !online }"><i :class="['status-dot', { offline: !online }]"></i>{{ online ? "연결됨" : "연결 안 됨" }}</strong></div>
        <div class="state-row"><span>대화 모델</span><strong>{{ model }}</strong></div>
        <div class="state-row"><span>이미지 모델</span><strong>{{ visionModel }}</strong></div>
        <div class="state-divider"></div>
        <div class="state-row"><span>GPU</span><strong>{{ gpu?.name || "정보 없음" }}</strong></div>
        <div v-if="gpu" class="gpu-stats">
          <div class="gpu-numbers"><span>사용률 {{ gpu.utilization_percent }}%</span><span>{{ gpu.memory_used_mb }} / {{ gpu.memory_total_mb }} MB</span></div>
          <div class="gpu-track"><div :style="{ width: gpu.utilization_percent + '%' }"></div></div>
          <div class="gpu-temperature">온도 {{ gpu.temperature_c }}°C</div>
        </div>
        <div class="state-divider"></div>
        <div class="instructions-applied">개인 사용자 지침 적용 중</div>
        <div class="state-divider"></div>
        <label class="web-control"><span><strong>웹 검색 허용</strong><small>{{ searchProvider }} 검색 사용</small></span><input v-model="searching" type="checkbox" role="switch" /><span class="switch-visual"></span></label>
        <p class="state-note">이미지 분석은 웹 검색 없이 로컬에서 처리합니다.</p>
      </aside>
    </main>
  </div>
</template>
