<template>
  <div class="page">
    <h1>New Research</h1>
    <p class="subtitle">Collect and analyze market intelligence from public sources.</p>

    <!-- Tabs -->
    <div class="tabs">
      <button v-for="tab in tabs" :key="tab" class="tab-button"
        :class="{ active: activeTab === tab }"
        :disabled="(tab === 'progress' && !isRunning && progressLog.length === 0) || (tab === 'results' && !result)"
        @click="activeTab = tab">
        {{ tab === 'input' ? '1. Input' : tab === 'progress' ? '2. Progress' : '3. Results' }}
      </button>
    </div>

    <!-- TAB 1: Input Form -->
    <div v-if="activeTab === 'input'" class="tab-content">
      <form @submit.prevent="submitResearch" class="research-form">

        <div class="form-row">
          <!-- Left column -->
          <div class="form-col">
            <div class="form-group">
              <label class="form-label">Competitors <span class="required">*</span></label>
              <p class="form-hint">Enter the names of companies or products you want to track — one per line.</p>
              <textarea v-model="input.competitors"
                class="form-input tall"
                :class="{ 'input-error': fieldErrors.competitors }"
                placeholder="One competitor or product name per line"></textarea>
              <span v-if="fieldErrors.competitors" class="field-error">{{ fieldErrors.competitors }}</span>
            </div>
            <div class="form-group">
              <label class="form-label">Topics <span class="optional">(optional)</span></label>
              <p class="form-hint">Specific themes or questions to focus on — one per line. If left blank, the analysis uses your competitor names as topics.</p>
              <textarea v-model="input.topics"
                class="form-input"
                placeholder="One topic or research question per line"></textarea>
            </div>
          </div>

          <!-- Right column -->
          <div class="form-col">
            <div class="form-group">
              <label class="form-label">Source URLs <span class="required">*</span></label>
              <p class="form-hint">
                Paste the public pages you want analyzed — blog posts, news pages, release notes, or announcements.
                Enter one URL per line, between 1 and 5 URLs.
                Each URL must start with <code>https://</code> or <code>http://</code>.
              </p>
              <textarea v-model="input.urls"
                class="form-input tall"
                :class="{ 'input-error': fieldErrors.urls }"
                placeholder="One URL per line — must start with https:// or http://"></textarea>
              <span v-if="fieldErrors.urls" class="field-error">{{ fieldErrors.urls }}</span>
            </div>
            <div class="url-preview" v-if="parsedUrls.length > 0">
              <div v-for="(url, i) in parsedUrls" :key="i" class="url-chip"
                :class="{ 'url-chip-invalid': !isValidUrl(url) }">
                <span class="url-index">{{ i + 1 }}</span>
                <span class="url-text">{{ url }}</span>
                <span v-if="!isValidUrl(url)" class="url-invalid-tag">invalid URL</span>
              </div>
            </div>
          </div>
        </div>

        <div class="form-footer">
          <button type="submit" class="btn-primary btn-run" :disabled="isRunning">
            {{ isRunning ? 'Analyzing...' : 'Run Analysis' }}
          </button>
          <span class="form-meta" v-if="parsedUrls.length > 0">
            {{ parsedCompetitors.length }} competitor{{ parsedCompetitors.length !== 1 ? 's' : '' }} ·
            {{ parsedTopics.length > 0 ? parsedTopics.length + ' topic' + (parsedTopics.length !== 1 ? 's' : '') : 'topics from competitors' }} ·
            {{ parsedUrls.length }} URL{{ parsedUrls.length !== 1 ? 's' : '' }}
          </span>
        </div>

      </form>
    </div>

    <!-- TAB 2: Live Progress -->
    <div v-if="activeTab === 'progress'" class="tab-content">
      <div class="progress-card">
        <div class="progress-header">
          <h2>{{ isRunning ? 'Analysis in progress...' : 'Analysis complete' }}</h2>
          <div v-if="isRunning" class="spinner"></div>
        </div>

        <!-- URL status grid -->
        <div v-if="urlStatuses.length > 0" class="url-status-grid">
          <div v-for="(s, i) in urlStatuses" :key="i" class="url-status-item"
            :class="s.ok === true ? 'ok' : s.ok === false ? 'fail' : 'pending'">
            <span class="url-status-icon">{{ s.ok === true ? '✅' : s.ok === false ? '❌' : '⏳' }}</span>
            <span class="url-status-text">{{ s.url }}</span>
            <span v-if="s.ok === false" class="url-status-error">{{ s.error }}</span>
          </div>
        </div>

        <!-- Pipeline log -->
        <div class="progress-log">
          <div v-for="(msg, idx) in progressLog" :key="idx" class="progress-item"
            :class="msg.type">
            <span class="progress-icon">{{ msg.icon }}</span>
            <span class="progress-text">{{ msg.text }}</span>
          </div>
        </div>

        <button v-if="!isRunning && result" @click="activeTab = 'results'" class="btn-primary" style="margin-top:1rem">
          View Results
        </button>
      </div>
    </div>

    <!-- TAB 3: Results -->
    <div v-if="activeTab === 'results'" class="tab-content">
      <div v-if="result" class="results-container">

        <!-- Executive Summary -->
        <section class="result-section">
          <div class="summary-card">
            <div class="summary-header">
              <h2>Executive Summary</h2>
              <span v-if="result.hallucination_count === 0" class="badge badge-success">✅ All claims verified</span>
              <span v-else class="badge badge-warning">⚠️ {{ verifiedCount }}/{{ totalClaims }} claims verified</span>
            </div>
            <p>{{ result.summary.executive_summary }}</p>
            <div class="run-meta">
              <span>{{ parsedUrls.length }} URLs</span>
              <span>{{ result.run_duration_seconds.toFixed(1) }}s</span>
              <span>{{ new Date(result.summary.generated_at).toLocaleString() }}</span>
            </div>
          </div>
        </section>

        <!-- Key Themes -->
        <section class="result-section">
          <h2>Key Themes</h2>
          <div v-if="result.summary.key_themes.length === 0" class="empty-state">No themes identified.</div>
          <div v-for="(theme, idx) in result.summary.key_themes" :key="`theme-${idx}`" class="theme-card">
            <div class="theme-header">
              <h3>📌 {{ theme.theme }}</h3>
              <div v-if="isHallucination(theme.finding)" class="inline-warning">⚠️ Unverified</div>
            </div>
            <p>{{ theme.finding }}</p>
            <div class="sources">
              <a v-for="(s, si) in theme.sources" :key="si" :href="s.url" target="_blank" class="source-badge" :title="s.excerpt">
                🔗 {{ sourceDomain(s.url) }}
              </a>
            </div>
          </div>
        </section>

        <!-- Competitor Activity -->
        <section class="result-section">
          <h2>Competitor Activity</h2>
          <div v-if="result.summary.competitor_activities.length === 0" class="empty-state">No activities identified.</div>
          <div class="competitor-grid">
            <div v-for="(a, idx) in result.summary.competitor_activities" :key="`comp-${idx}`" class="competitor-card">
              <h3>{{ a.competitor }}</h3>
              <p>{{ a.activity }}</p>
              <div class="sources">
                <a v-for="(s, si) in a.sources" :key="si" :href="s.url" target="_blank" class="source-badge" :title="s.excerpt">
                  🔗 {{ sourceDomain(s.url) }}
                </a>
              </div>
            </div>
          </div>
        </section>

        <!-- Fact Check -->
        <section v-if="result.verdicts.length > 0" class="result-section">
          <h2>Fact Check</h2>
          <div class="verdicts-list">
            <div v-for="(v, idx) in result.verdicts" :key="`v-${idx}`" class="verdict-item"
              :class="v.supported ? 'supported' : 'unsupported'">
              <div class="verdict-row">
                <span>{{ v.supported ? '✅' : '❌' }}</span>
                <span class="verdict-claim">{{ v.claim }}</span>
                <span class="verdict-conf">{{ (v.confidence * 100).toFixed(0) }}%</span>
              </div>
              <p v-if="!v.supported" class="verdict-explanation">{{ v.explanation }}</p>
              <a v-if="v.source_url" :href="v.source_url" target="_blank" class="source-badge verdict-source">
                🔗 {{ sourceDomain(v.source_url) }}
              </a>
            </div>
          </div>
        </section>

        <button @click="resetForm" class="btn-secondary">New Research</button>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import * as api from "../api";

const tabs = ["input", "progress", "results"] as const;
const activeTab = ref<"input" | "progress" | "results">("input");
const isRunning = ref(false);
const progressLog = ref<Array<{ icon: string; text: string; type: string }>>([]);
const result = ref<api.PipelineResult | null>(null);
const urlStatuses = ref<Array<{ url: string; ok: boolean | null; error?: string }>>([]);
let activeEventSource: EventSource | null = null;

const input = ref({ competitors: "", topics: "", urls: "" });
const fieldErrors = ref({ competitors: "", urls: "" });

const parsedCompetitors = computed(() =>
  input.value.competitors.split("\n").map(s => s.trim()).filter(Boolean)
);
const parsedTopics = computed(() =>
  input.value.topics.split("\n").map(s => s.trim()).filter(Boolean)
);
const parsedUrls = computed(() =>
  input.value.urls.split("\n").map(s => s.trim()).filter(Boolean)
);
const totalClaims = computed(() =>
  result.value ? result.value.summary.key_themes.length + result.value.summary.competitor_activities.length : 0
);
const verifiedCount = computed(() =>
  result.value ? totalClaims.value - result.value.hallucination_count : 0
);

function isValidUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:";
  } catch {
    return false;
  }
}

function validateInput(): boolean {
  fieldErrors.value = { competitors: "", urls: "" };
  let valid = true;

  if (parsedCompetitors.value.length === 0) {
    fieldErrors.value.competitors = "Enter at least one competitor or product name.";
    valid = false;
  }

  if (parsedUrls.value.length === 0) {
    fieldErrors.value.urls = "Enter at least one source URL.";
    valid = false;
  } else if (parsedUrls.value.length > 5) {
    fieldErrors.value.urls = `You entered ${parsedUrls.value.length} URLs — maximum is 5. Remove ${parsedUrls.value.length - 5} to continue.`;
    valid = false;
  } else {
    const invalidUrls = parsedUrls.value.filter(u => !isValidUrl(u));
    if (invalidUrls.length > 0) {
      fieldErrors.value.urls = `${invalidUrls.length} URL${invalidUrls.length > 1 ? "s are" : " is"} invalid — each must start with https:// or http://`;
      valid = false;
    }
  }

  return valid;
}

function submitResearch(): void {
  if (!validateInput()) return;

  if (activeEventSource) {
    activeEventSource.close();
    activeEventSource = null;
  }

  isRunning.value = true;
  result.value = null;
  progressLog.value = [];
  // Pre-populate URL statuses as pending
  urlStatuses.value = parsedUrls.value.map(url => ({ url, ok: null }));
  activeTab.value = "progress";

  const topics = parsedTopics.value.length > 0 ? parsedTopics.value : parsedCompetitors.value;
  const eventSource = api.streamResearch({
    competitors: parsedCompetitors.value,
    topics,
    urls: parsedUrls.value,
  });
  activeEventSource = eventSource;

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      // Update URL status if this event carries one
      if (data.url_status) {
        const idx = urlStatuses.value.findIndex(s => s.url === data.url_status.url);
        if (idx !== -1) {
          urlStatuses.value[idx] = {
            url: data.url_status.url,
            ok: data.url_status.ok,
            error: data.url_status.error,
          };
        }
      }

      if (data.stage === "done") {
        isRunning.value = false;
        result.value = data.result;
        progressLog.value.push({ icon: "✅", text: "Analysis complete!", type: "success" });
        eventSource.close();
        activeEventSource = null;
      } else if (data.stage === "error") {
        isRunning.value = false;
        progressLog.value.push({ icon: "❌", text: data.message, type: "error" });
        eventSource.close();
        activeEventSource = null;
      } else if (!data.url_status) {
        // Only push non-URL-status progress messages to the log
        progressLog.value.push({ icon: getIcon(data.stage), text: data.message, type: "info" });
      }
    } catch (e) {
      console.error("Failed to parse SSE message:", event.data, e);
    }
  };

  eventSource.onerror = () => {
    eventSource.close();
    activeEventSource = null;
    if (!result.value && isRunning.value) {
      isRunning.value = false;
      progressLog.value.push({ icon: "❌", text: "Connection closed unexpectedly.", type: "error" });
    }
  };
}

function getIcon(stage: string): string {
  const icons: Record<string, string> = {
    scraping: "🔍",
    summarizing: "📝",
    judging: "⚖️",
    done: "✅",
  };
  return icons[stage] || "⏳";
}

function isHallucination(finding: string): boolean {
  if (!result.value) return false;
  return result.value.verdicts.some(v => !v.supported && v.confidence > 0.95 &&
    v.claim.includes(finding.substring(0, 40)));
}

function sourceDomain(url: string): string {
  try {
    return new URL(url).hostname.replace("www.", "");
  } catch {
    return url;
  }
}

function resetForm(): void {
  input.value = { competitors: "", topics: "", urls: "" };
  result.value = null;
  progressLog.value = [];
  urlStatuses.value = [];
  fieldErrors.value = { competitors: "", urls: "" };
  activeTab.value = "input";
}
</script>

<style scoped>
/* Form layout */
.research-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}

@media (max-width: 700px) {
  .form-row { grid-template-columns: 1fr; }
}

.form-col {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.form-label {
  font-weight: 600;
  font-size: 0.9rem;
}

.form-hint {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  margin: 0;
}

.form-input {
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 0.75rem;
  font-family: var(--font);
  font-size: 0.9rem;
  resize: vertical;
  min-height: 80px;
}

.form-input.tall { min-height: 130px; }

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.url-preview {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  margin-top: 0.25rem;
}

.url-chip {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #f0f4ff;
  border-radius: 4px;
  padding: 0.3rem 0.6rem;
  font-size: 0.8rem;
}

.url-chip-invalid {
  background: #fee2e2;
}

.url-invalid-tag {
  font-size: 0.72rem;
  color: var(--color-danger);
  font-weight: 600;
  margin-left: auto;
  white-space: nowrap;
}

.url-index {
  background: var(--color-primary);
  color: white;
  border-radius: 50%;
  width: 1.2rem;
  height: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  flex-shrink: 0;
}

.url-text {
  word-break: break-all;
  color: var(--color-text-muted);
}

.form-footer {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.btn-run {
  padding: 0.75rem 2rem;
  font-size: 1rem;
}

.form-meta {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

/* Tabs */
.tabs {
  display: flex;
  gap: 0.25rem;
  border-bottom: 2px solid var(--color-border);
  margin-bottom: 1.5rem;
}

.tab-button {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  padding: 0.6rem 1.25rem;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
  color: var(--color-text-muted);
  transition: all 0.15s;
}

.tab-button:hover:not(:disabled) { color: var(--color-primary); }
.tab-button.active { color: var(--color-primary); border-bottom-color: var(--color-primary); }
.tab-button:disabled { opacity: 0.4; cursor: not-allowed; }

.tab-content { animation: fadeIn 0.15s; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

/* Progress */
.progress-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.progress-header {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.progress-header h2 { margin: 0; }

.spinner {
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.url-status-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  background: #f8fafc;
  border-radius: var(--radius);
  padding: 1rem;
}

.url-status-item {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  font-size: 0.85rem;
}

.url-status-item.pending { opacity: 0.5; }
.url-status-text { word-break: break-all; flex: 1; }
.url-status-error { color: var(--color-danger); font-size: 0.8rem; }

.progress-log {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  font-family: monospace;
  font-size: 0.88rem;
}

.progress-item {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
}

.progress-item.error { color: var(--color-danger); }
.progress-item.success { color: var(--color-success); }
.progress-item.info { color: var(--color-text-muted); }
.progress-icon { flex-shrink: 0; }

/* Results */
.results-container { display: flex; flex-direction: column; gap: 2rem; }

.result-section { display: flex; flex-direction: column; gap: 1rem; }

.summary-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1.5rem;
}

.summary-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.summary-header h2 { margin: 0; }

.summary-card p { line-height: 1.8; }

.run-meta {
  display: flex;
  gap: 1.5rem;
  margin-top: 1rem;
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.badge {
  display: inline-block;
  padding: 0.35rem 0.85rem;
  border-radius: 4px;
  font-size: 0.82rem;
  font-weight: 600;
  white-space: nowrap;
}

.badge-success { background: #dcfce7; color: var(--color-success); }
.badge-warning { background: #fef9c3; color: var(--color-warning); }

.theme-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1.25rem;
}

.theme-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.6rem;
}

.theme-header h3 { margin: 0; }

.inline-warning {
  font-size: 0.8rem;
  background: #fef9c3;
  color: var(--color-warning);
  padding: 0.2rem 0.6rem;
  border-radius: 4px;
  font-weight: 600;
}

.sources { display: flex; gap: 0.5rem; margin-top: 0.75rem; flex-wrap: wrap; }

.source-badge {
  display: inline-block;
  padding: 0.3rem 0.65rem;
  background: #dbeafe;
  color: var(--color-primary);
  border-radius: 4px;
  text-decoration: none;
  font-size: 0.8rem;
  font-weight: 500;
  transition: background 0.15s;
}

.source-badge:hover { background: #bfdbfe; }

.competitor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
}

.competitor-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1rem;
}

.competitor-card h3 { margin-bottom: 0.5rem; font-size: 1rem; }
.competitor-card p { font-size: 0.9rem; color: var(--color-text-muted); margin-bottom: 0.75rem; }

.verdicts-list { display: flex; flex-direction: column; gap: 0.75rem; }

.verdict-item {
  background: var(--color-surface);
  border-left: 4px solid var(--color-border);
  border-radius: var(--radius);
  padding: 0.85rem 1rem;
}

.verdict-item.supported { border-left-color: var(--color-success); }
.verdict-item.unsupported { border-left-color: var(--color-danger); }

.verdict-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.9rem;
}

.verdict-claim { flex: 1; }
.verdict-conf { font-size: 0.8rem; color: var(--color-text-muted); white-space: nowrap; }
.verdict-explanation { font-size: 0.85rem; color: var(--color-danger); margin: 0.4rem 0 0; }
.verdict-source { display: inline-block; margin-top: 0.5rem; }

.btn-secondary {
  background: none;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 0.65rem 1.5rem;
  font-weight: 600;
  cursor: pointer;
  color: var(--color-text-muted);
  transition: all 0.15s;
}

.btn-secondary:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.required {
  color: var(--color-danger);
  font-size: 0.85rem;
}

.optional {
  color: var(--color-text-muted);
  font-size: 0.8rem;
  font-weight: 400;
}

.field-error {
  color: var(--color-danger);
  font-size: 0.82rem;
  margin-top: 0.2rem;
}

.input-error {
  border-color: var(--color-danger) !important;
}

.input-error:focus {
  outline-color: var(--color-danger);
}

.form-hint code {
  font-size: 0.82rem;
  background: #f1f5f9;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  color: var(--color-text);
}

.empty-state {
  background: var(--color-surface);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius);
  padding: 2rem;
  text-align: center;
  color: var(--color-text-muted);
}
</style>