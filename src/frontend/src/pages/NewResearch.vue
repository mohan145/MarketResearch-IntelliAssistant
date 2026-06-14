<template>
  <div class="page">
    <h1>Market Research</h1>
    <p class="subtitle">Analyze competitors and market trends from public sources.</p>

    <!-- Tabs -->
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab"
        class="tab-button"
        :class="{ active: activeTab === tab }"
        @click="activeTab = tab"
        :disabled="tab === 'progress' && !isRunning"
      >
        {{ tab === 'input' ? '📝 Input' : tab === 'progress' ? '⏳ Progress' : '📊 Results' }}
      </button>
    </div>

    <!-- TAB 1: Input Form -->
    <div v-if="activeTab === 'input'" class="tab-content">
      <form @submit.prevent="submitResearch" class="form-card">
        <div class="form-section">
          <label for="competitors" class="form-label">Competitors / Topics</label>
          <textarea
            id="competitors"
            v-model="input.competitors"
            placeholder="e.g., OpenAI, Mistral AI, Cohere (comma-separated)"
            class="form-input"
          ></textarea>
        </div>

        <div class="form-section">
          <label for="urls" class="form-label">Source URLs</label>
          <textarea
            id="urls"
            v-model="input.urls"
            placeholder="e.g., https://openai.com/blog&#10;https://mistral.ai/news&#10;(one per line)"
            class="form-input"
          ></textarea>
        </div>

        <p v-if="error" class="error-text">⚠️ {{ error }}</p>

        <button type="submit" class="btn-primary" :disabled="isRunning">
          {{ isRunning ? 'Running...' : 'Run Analysis' }}
        </button>

        <div class="hints">
          <p><strong>Sample URLs to try:</strong></p>
          <ul>
            <li>https://openai.com/index/gpt-4o-mini-advancing-cost-efficient-intelligence/</li>
            <li>https://mistral.ai/news/mistral-large-2407/</li>
            <li>https://www.anthropic.com/news/claude-3-5-sonnet</li>
          </ul>
        </div>
      </form>
    </div>

    <!-- TAB 2: Live Progress -->
    <div v-if="activeTab === 'progress'" class="tab-content">
      <div class="progress-card">
        <h2>Research in Progress</h2>
        <div class="progress-log">
          <div v-for="(msg, idx) in progressLog" :key="idx" class="progress-item">
            <span class="progress-icon">{{ msg.icon }}</span>
            <span class="progress-text">{{ msg.text }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: Results -->
    <div v-if="activeTab === 'results'" class="tab-content">
      <div v-if="result" class="results-container">
        <!-- Executive Summary -->
        <section class="result-section">
          <div class="summary-card">
            <h2>Executive Summary</h2>
            <p>{{ result.summary.executive_summary }}</p>
            <div class="trust-badge">
              <span v-if="result.hallucination_count === 0" class="badge badge-success">
                ✅ All claims verified
              </span>
              <span v-else class="badge badge-warning">
                ⚠️ {{ result.summary.key_themes.length + result.summary.competitor_activities.length - result.hallucination_count }}/{{ result.summary.key_themes.length + result.summary.competitor_activities.length }} claims verified
              </span>
            </div>
          </div>
        </section>

        <!-- Key Themes -->
        <section class="result-section">
          <h2>Key Themes</h2>
          <div v-if="result.summary.key_themes.length === 0" class="empty-state">
            No themes identified.
          </div>
          <div v-for="(theme, idx) in result.summary.key_themes" :key="`theme-${idx}`" class="theme-card">
            <h3>📌 {{ theme.theme }}</h3>
            <p>{{ theme.finding }}</p>
            <div class="sources">
              <a v-for="(source, sidx) in theme.sources" :key="`src-${sidx}`" :href="source.url" target="_blank" class="source-badge">
                🔗 Source
              </a>
            </div>
            <!-- Check if this finding is flagged as hallucination -->
            <div v-if="isHallucination(theme.finding)" class="warning-block">
              ⚠️ Judge flagged this as unverified. See hallucinations below.
            </div>
          </div>
        </section>

        <!-- Competitor Activity -->
        <section class="result-section">
          <h2>Competitor Activity</h2>
          <div v-if="result.summary.competitor_activities.length === 0" class="empty-state">
            No competitor activities identified.
          </div>
          <div class="competitor-grid">
            <div v-for="(activity, idx) in result.summary.competitor_activities" :key="`comp-${idx}`" class="competitor-card">
              <h3>{{ activity.competitor }}</h3>
              <p>{{ activity.activity }}</p>
              <div class="sources">
                <a v-for="(source, sidx) in activity.sources" :key="`csrc-${sidx}`" :href="source.url" target="_blank" class="source-badge">
                  🔗 Source
                </a>
              </div>
            </div>
          </div>
        </section>

        <!-- Hallucinations (if any) -->
        <section v-if="result.verdicts.length > 0" class="result-section">
          <h2>Fact Check Results</h2>
          <div class="verdicts-list">
            <div v-for="(verdict, idx) in result.verdicts" :key="`verdict-${idx}`" class="verdict-item">
              <div v-if="!verdict.supported" class="verdict-unsupported">
                <h4>❌ Unverified Claim</h4>
                <p><strong>Claim:</strong> {{ verdict.claim }}</p>
                <p><strong>Judge's reasoning:</strong> {{ verdict.explanation }}</p>
                <p><strong>Source:</strong> <a :href="verdict.source_url" target="_blank">{{ verdict.source_url }}</a></p>
                <p><strong>Confidence:</strong> {{ (verdict.confidence * 100).toFixed(0) }}%</p>
              </div>
              <div v-else class="verdict-supported">
                <p>✅ <strong>{{ verdict.claim }}</strong> — verified with {{ (verdict.confidence * 100).toFixed(0) }}% confidence</p>
              </div>
            </div>
          </div>
        </section>

        <!-- Run Details -->
        <section class="result-section">
          <div class="run-details">
            <p><strong>URLs processed:</strong> {{ input.urls.split('\n').filter(u => u.trim()).length }}</p>
            <p><strong>Run duration:</strong> {{ result.run_duration_seconds.toFixed(1) }}s</p>
            <p><strong>Generated at:</strong> {{ new Date(result.summary.generated_at).toLocaleString() }}</p>
          </div>
        </section>

        <button @click="resetForm" class="btn-primary">Start New Research</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import * as api from "../api";

const activeTab = ref<"input" | "progress" | "results">("input");
const isRunning = ref(false);
const error = ref("");
const progressLog = ref<Array<{ icon: string; text: string }>>([]);
const result = ref<api.PipelineResult | null>(null);

const input = ref({
  competitors: "",
  urls: "",
});

function validateInput(): boolean {
  const competitors = input.value.competitors
    .split(",")
    .map((c) => c.trim())
    .filter((c) => c);
  const urls = input.value.urls
    .split("\n")
    .map((u) => u.trim())
    .filter((u) => u);

  if (competitors.length === 0) {
    error.value = "Please enter at least one competitor or topic.";
    return false;
  }
  if (urls.length === 0) {
    error.value = "Please enter at least one URL.";
    return false;
  }
  if (urls.length > 5) {
    error.value = "Maximum 5 URLs allowed.";
    return false;
  }

  error.value = "";
  return true;
}

function submitResearch(): void {
  if (!validateInput()) return;

  const competitors = input.value.competitors
    .split(",")
    .map((c) => c.trim())
    .filter((c) => c);
  const urls = input.value.urls
    .split("\n")
    .map((u) => u.trim())
    .filter((u) => u);
  const topics = competitors; // For now, use competitors as topics

  isRunning.value = true;
  progressLog.value = [];
  activeTab.value = "progress";

  const eventSource = api.streamResearch({ competitors, topics, urls });

  // Listen for progress messages (default SSE event)
  eventSource.onmessage = (event) => {
    console.log("Received message event:", event.data);
    try {
      const data = JSON.parse(event.data);
      progressLog.value.push({
        icon: getIcon(data.stage),
        text: data.message,
      });
    } catch (e) {
      console.error("Failed to parse message:", e);
    }
  };

  // Listen for specific "result" event type
  eventSource.addEventListener("result", (event: Event) => {
    console.log("Received result event:", (event as MessageEvent).data);
    isRunning.value = false;
    try {
      result.value = JSON.parse((event as MessageEvent).data);
      activeTab.value = "results";
      progressLog.value.push({
        icon: "✅",
        text: "Analysis complete!",
      });
    } catch (e) {
      console.error("Failed to parse result:", e);
      error.value = "Failed to parse results.";
    }
    eventSource.close();
  });

  // Listen for errors
  eventSource.addEventListener("error", (event: Event) => {
    console.log("Received error event:", (event as MessageEvent).data);
    isRunning.value = false;
    progressLog.value.push({
      icon: "❌",
      text: "Error: " + ((event as MessageEvent).data || "Connection failed"),
    });
    eventSource.close();
  });

  // Fallback error handler
  eventSource.onerror = () => {
    console.error("EventSource error (onerror handler)");
    if (eventSource.readyState === EventSource.CLOSED) {
      isRunning.value = false;
      progressLog.value.push({
        icon: "❌",
        text: "Connection closed unexpectedly",
      });
    }
  };
}

function getIcon(stage: string): string {
  const icons: Record<string, string> = {
    scraping: "🔍",
    researching: "🤖",
    summarizing: "📝",
    judging: "⚖️",
    done: "✅",
  };
  return icons[stage] || "⏳";
}

function isHallucination(claim: string): boolean {
  if (!result.value) return false;
  return result.value.verdicts.some(
    (v) => v.claim.includes(claim.substring(0, 50)) && !v.supported && v.confidence > 0.7
  );
}

function resetForm(): void {
  input.value = { competitors: "", urls: "" };
  result.value = null;
  progressLog.value = [];
  activeTab.value = "input";
}
</script>

<style scoped>
/* Tabs */
.tabs {
  display: flex;
  gap: 0.5rem;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 1.5rem;
}

.tab-button {
  background: none;
  border: none;
  border-bottom: 3px solid transparent;
  padding: 0.75rem 1.25rem;
  cursor: pointer;
  font-weight: 600;
  color: var(--color-text-muted);
  transition: all 0.15s;
}

.tab-button:hover:not(:disabled) {
  color: var(--color-primary);
}

.tab-button.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

.tab-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.tab-content {
  animation: fadeIn 0.2s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* Form */
.form-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  font-weight: 600;
  font-size: 0.9rem;
}

.form-input {
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 0.75rem;
  font-family: var(--font);
  font-size: 0.9rem;
  min-height: 100px;
  resize: vertical;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.hints {
  background: #f0f4f8;
  border-radius: var(--radius);
  padding: 1rem;
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.hints ul {
  margin-top: 0.5rem;
  list-style: none;
  padding-left: 1rem;
}

.hints li {
  margin: 0.25rem 0;
  word-break: break-all;
}

/* Progress */
.progress-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1.5rem;
}

.progress-log {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1rem;
  font-family: monospace;
  font-size: 0.9rem;
}

.progress-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.progress-icon {
  font-size: 1.25rem;
}

.progress-text {
  color: var(--color-text-muted);
}

/* Results */
.results-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.result-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.summary-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1.5rem;
}

.summary-card h2 {
  margin-bottom: 1rem;
}

.summary-card p {
  line-height: 1.8;
  margin-bottom: 1rem;
}

.trust-badge {
  display: flex;
  gap: 0.5rem;
}

.badge {
  display: inline-block;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-size: 0.85rem;
  font-weight: 600;
}

.badge-success {
  background: #dcfce7;
  color: var(--color-success);
}

.badge-warning {
  background: #fef9c3;
  color: var(--color-warning);
}

/* Theme Cards */
.theme-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1.25rem;
}

.theme-card h3 {
  margin-bottom: 0.75rem;
}

.sources {
  display: flex;
  gap: 0.5rem;
  margin-top: 1rem;
  flex-wrap: wrap;
}

.source-badge {
  display: inline-block;
  padding: 0.375rem 0.75rem;
  background: #dbeafe;
  color: var(--color-primary);
  border-radius: 4px;
  text-decoration: none;
  font-size: 0.8rem;
  font-weight: 500;
  transition: background 0.15s;
}

.source-badge:hover {
  background: #bfdbfe;
}

/* Competitor Grid */
.competitor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.competitor-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 1rem;
}

.competitor-card h3 {
  margin-bottom: 0.5rem;
  font-size: 1rem;
}

.competitor-card p {
  font-size: 0.9rem;
  color: var(--color-text-muted);
  margin-bottom: 0.75rem;
}

/* Verdicts */
.verdicts-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.verdict-item {
  background: var(--color-surface);
  border-radius: var(--radius);
  padding: 1rem;
  border-left: 4px solid var(--color-border);
}

.verdict-unsupported {
  border-left-color: var(--color-danger);
}

.verdict-unsupported h4 {
  color: var(--color-danger);
  margin-bottom: 0.5rem;
}

.verdict-supported {
  border-left-color: var(--color-success);
  color: var(--color-success);
}

.verdict-item p {
  font-size: 0.9rem;
  margin: 0.5rem 0;
}

.verdict-item a {
  color: var(--color-primary);
  text-decoration: none;
  word-break: break-all;
}

.verdict-item a:hover {
  text-decoration: underline;
}

/* Run Details */
.run-details {
  background: #f8fafc;
  border-radius: var(--radius);
  padding: 1rem;
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

.run-details p {
  margin: 0.5rem 0;
}

.empty-state {
  background: var(--color-surface);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius);
  padding: 2rem;
  text-align: center;
  color: var(--color-text-muted);
}

.error-text {
  color: var(--color-danger);
  font-size: 0.9rem;
  padding: 0.75rem;
  background: #fee2e2;
  border-radius: 4px;
}

.warning-block {
  background: var(--color-warning-bg);
  border: 1px solid var(--color-warning-border);
  border-radius: 4px;
  padding: 0.75rem;
  margin-top: 0.75rem;
  font-size: 0.85rem;
  color: var(--color-warning);
}
</style>