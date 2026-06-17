<template>
  <div class="page">
    <h1>Research History</h1>
    <p class="subtitle">View and reload previous research runs.</p>

    <!-- View Toggle -->
    <div class="view-toggle">
      <button
        class="toggle-btn"
        :class="{ active: viewMode === 'table' }"
        @click="viewMode = 'table'"
      >
        📋 Table
      </button>
      <button
        class="toggle-btn"
        :class="{ active: viewMode === 'detail' }"
        @click="viewMode = 'detail'"
        :disabled="!selectedRun"
      >
        📊 Details
      </button>
    </div>

    <!-- Table View -->
    <div v-if="viewMode === 'table'" class="table-view">
      <div v-if="loading" class="loading-spinner">Loading history...</div>
      <div v-else-if="loadError" class="empty-state">{{ loadError }}</div>
      <div v-else-if="runs.length === 0" class="empty-state">
        No research runs yet. <a href="/">Start a new one.</a>
      </div>
      <table v-else class="history-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Competitors</th>
            <th>Topics</th>
            <th>URLs</th>
            <th>Trust Score</th>
            <th>Duration</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="run in runs" :key="run.id" :class="{ selected: selectedRun?.id === run.id }">
            <td>{{ formatDate(run.created_at) }}</td>
            <td>
              <span class="tag-list">
                <span v-for="(c, i) in run.competitors.slice(0, 2)" :key="i" class="tag tag-competitor">{{ c }}</span>
                <span v-if="run.competitors.length > 2" class="tag tag-competitor">+{{ run.competitors.length - 2 }}</span>
              </span>
            </td>
            <td>
              <span class="tag-list">
                <span v-for="(topic, i) in run.topics.slice(0, 2)" :key="i" class="tag">{{ topic }}</span>
                <span v-if="run.topics.length > 2" class="tag">+{{ run.topics.length - 2 }}</span>
              </span>
            </td>
            <td>{{ run.urls.length }}</td>
            <td>
              <span v-if="run.hallucination_count === 0" class="badge badge-success">All verified</span>
              <span v-else class="badge badge-warning">{{ run.hallucination_count }} issues</span>
            </td>
            <td>{{ run.run_duration_seconds.toFixed(1) }}s</td>
            <td>
              <button @click="selectRun(run)" class="btn-view">View</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Detail View -->
    <div v-if="viewMode === 'detail' && selectedRun && selectedRun.result" class="detail-view">
      <button @click="viewMode = 'table'" class="btn-back">← Back to Table</button>

      <!-- Executive Summary -->
      <section class="result-section">
        <div class="summary-card">
          <h2>Executive Summary</h2>
          <p>{{ selectedRun.result.summary.executive_summary }}</p>
          <div class="trust-badge">
            <span v-if="selectedRun.result.hallucination_count === 0" class="badge badge-success">
              ✅ All claims verified
            </span>
            <span v-else class="badge badge-warning">
              ⚠️ {{ selectedRun.result.summary.key_themes.length + selectedRun.result.summary.competitor_activities.length - selectedRun.result.hallucination_count }}/{{ selectedRun.result.summary.key_themes.length + selectedRun.result.summary.competitor_activities.length }} claims verified
            </span>
          </div>
        </div>
      </section>

      <!-- Key Themes -->
      <section class="result-section">
        <h2>Key Themes</h2>
        <div v-if="selectedRun.result.summary.key_themes.length === 0" class="empty-state">
          No themes identified.
        </div>
        <div v-for="(theme, idx) in selectedRun.result.summary.key_themes" :key="`theme-${idx}`" class="theme-card">
          <h3>📌 {{ theme.theme }}</h3>
          <p>{{ theme.finding }}</p>
          <div class="sources">
            <a v-for="(source, sidx) in theme.sources" :key="`src-${sidx}`" :href="source.url" target="_blank" class="source-badge">
              🔗 Source
            </a>
          </div>
        </div>
      </section>

      <!-- Competitor Activity -->
      <section class="result-section">
        <h2>Competitor Activity</h2>
        <div v-if="selectedRun.result.summary.competitor_activities.length === 0" class="empty-state">
          No competitor activities identified.
        </div>
        <div class="competitor-grid">
          <div v-for="(activity, idx) in selectedRun.result.summary.competitor_activities" :key="`comp-${idx}`" class="competitor-card">
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

      <!-- Fact Check Results -->
      <section v-if="selectedRun.result.verdicts.length > 0" class="result-section">
        <h2>Fact Check Results</h2>
        <div class="verdicts-list">
          <div v-for="(verdict, idx) in selectedRun.result.verdicts" :key="`verdict-${idx}`" class="verdict-item">
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
          <p><strong>Run date:</strong> {{ formatDate(selectedRun.created_at) }}</p>
          <p><strong>URLs processed:</strong> {{ selectedRun.urls.length }}</p>
          <p><strong>Run duration:</strong> {{ selectedRun.result.run_duration_seconds.toFixed(1) }}s</p>
          <p><strong>Generated at:</strong> {{ new Date(selectedRun.result.summary.generated_at).toLocaleString() }}</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import * as api from "../api";

const runs = ref<api.Run[]>([]);
const selectedRun = ref<api.Run | null>(null);
const loading = ref(false);
const loadError = ref("");
const viewMode = ref<"table" | "detail">("table");

async function loadHistory(): Promise<void> {
  loading.value = true;
  loadError.value = "";
  try {
    runs.value = await api.getHistory();
  } catch (e) {
    loadError.value = "Failed to load history.";
    console.error("Failed to load history:", e);
  } finally {
    loading.value = false;
  }
}

function selectRun(run: api.Run): void {
  selectedRun.value = run;
  viewMode.value = "detail";
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

onMounted(() => {
  loadHistory();
});
</script>

<style scoped>
/* View Toggle */
.view-toggle {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.toggle-btn {
  background: none;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-weight: 500;
  color: var(--color-text-muted);
  transition: all 0.15s;
}

.toggle-btn:hover:not(:disabled) {
  color: var(--color-primary);
  border-color: var(--color-primary);
}

.toggle-btn.active {
  background: var(--color-primary);
  color: white;
  border-color: var(--color-primary);
}

.toggle-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Table View */
.table-view {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  overflow: hidden;
}

.loading-spinner {
  padding: 2rem;
  text-align: center;
  color: var(--color-text-muted);
}

.history-table {
  width: 100%;
  border-collapse: collapse;
}

.history-table thead {
  background: #f8f9fa;
  border-bottom: 1px solid var(--color-border);
}

.history-table th {
  text-align: left;
  padding: 1rem;
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.history-table td {
  padding: 1rem;
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}

.history-table tbody tr {
  cursor: pointer;
  transition: background 0.1s;
}

.history-table tbody tr:hover {
  background: #f8f9fa;
}

.history-table tbody tr.selected {
  background: #eff6ff;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
}

.tag {
  display: inline-block;
  background: #e0e7ff;
  color: var(--color-primary);
  padding: 0.25rem 0.5rem;
  border-radius: 3px;
  font-size: 0.75rem;
  font-weight: 500;
}

.tag-competitor {
  background: #fce7f3;
  color: #9d174d;
}

.btn-view {
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.375rem 0.75rem;
  font-size: 0.8rem;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-view:hover {
  background: var(--color-primary-hover);
}

/* Detail View */
.detail-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.btn-back {
  background: none;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 0.5rem 1rem;
  color: var(--color-text-muted);
  cursor: pointer;
  font-weight: 500;
  transition: all 0.15s;
  align-self: flex-start;
}

.btn-back:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

/* Result Sections */
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
</style>