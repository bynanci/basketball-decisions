<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiClient, type PlayerValueCompareResponse, type PlayerValueTrendSeries, type PlayerValueTrendsResponse } from '../api/client'

const trends = ref<PlayerValueTrendsResponse | null>(null)
const comparison = ref<PlayerValueCompareResponse | null>(null)
const isLoading = ref(false)
const isComparing = ref(false)
const error = ref<string | null>(null)
const compareInput = ref('')

const allWarnings = computed(() => {
  const values = new Set<string>()
  trends.value?.warnings.forEach((warning) => values.add(warning))
  trends.value?.trends.forEach((series) => series.warnings.forEach((warning) => values.add(warning)))
  comparison.value?.warnings.forEach((warning) => values.add(warning))
  comparison.value?.trends.forEach((series) => series.warnings.forEach((warning) => values.add(warning)))
  return Array.from(values)
})

function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toFixed(2)
}

function latestPoint(series: PlayerValueTrendSeries) {
  return series.points[series.points.length - 1]
}

function parseCompareKeys() {
  return compareInput.value
    .split(/[\n,]/)
    .map((key) => key.trim())
    .filter(Boolean)
}

async function loadTrends() {
  isLoading.value = true
  error.value = null
  try {
    trends.value = await apiClient.getPlayerValueTrends()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to load Player Value trends.'
  } finally {
    isLoading.value = false
  }
}

async function comparePlayers() {
  const playerKeys = parseCompareKeys()
  if (playerKeys.length < 2 || playerKeys.length > 4) {
    error.value = 'Enter 2–4 player_keys separated by commas or new lines.'
    return
  }
  isComparing.value = true
  error.value = null
  try {
    comparison.value = await apiClient.comparePlayerValue(playerKeys)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to compare Player Value trends.'
  } finally {
    isComparing.value = false
  }
}

onMounted(loadTrends)
</script>

<template>
  <section class="page player-value-trends-page" data-testid="player-value-trends-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Local Lab</p>
        <h1>Player Value Trends</h1>
        <p class="lede">Track immutable Player Value build snapshots over time without changing the v1 formula or claiming real player identity.</p>
      </div>
      <RouterLink class="button-link" to="/player-value">Back to Player Value</RouterLink>
    </header>

    <div v-if="error" class="error-callout">{{ error }}</div>

    <section v-if="allWarnings.length" class="warning-panel">
      <h2>Baseline and identity warnings</h2>
      <ul>
        <li v-for="warning in allWarnings" :key="warning">{{ warning }}</li>
      </ul>
    </section>

    <section class="panel comparison-panel">
      <h2>Compare 2–4 player_keys</h2>
      <p>Comparison keeps project-scoped series separate. It does not merge aliases across projects.</p>
      <textarea v-model="compareInput" rows="3" placeholder="P1, P2"></textarea>
      <button class="primary" :disabled="isComparing" @click="comparePlayers">{{ isComparing ? 'Comparing…' : 'Compare players' }}</button>
    </section>

    <section v-if="comparison" class="panel">
      <h2>Comparison results</h2>
      <div class="trend-grid">
        <article v-for="series in comparison.trends" :key="`${series.project_id}:${series.player_key}`" class="trend-card">
          <h3>{{ series.player_key }} <small>{{ series.project_id }}</small></h3>
          <p>Latest score: <strong>{{ formatNumber(latestPoint(series)?.player_value_score) }}</strong></p>
          <p>Confidence: {{ formatNumber(latestPoint(series)?.confidence) }}</p>
          <ol>
            <li v-for="point in series.points" :key="point.build_id">
              {{ new Date(point.generated_at).toLocaleString() }} — {{ formatNumber(point.player_value_score) }}
            </li>
          </ol>
        </article>
      </div>
    </section>

    <section class="panel">
      <div class="section-heading">
        <h2>All trends</h2>
        <button :disabled="isLoading" @click="loadTrends">{{ isLoading ? 'Loading…' : 'Refresh' }}</button>
      </div>
      <div v-if="trends && trends.trends.length" class="trend-grid">
        <article v-for="series in trends.trends" :key="`${series.project_id}:${series.player_key}`" class="trend-card">
          <h3>{{ series.display_name || series.player_key }} <small>{{ series.project_id }}</small></h3>
          <p>player_key: <code>{{ series.player_key }}</code></p>
          <p>Latest score: <strong>{{ formatNumber(latestPoint(series)?.player_value_score) }}</strong></p>
          <p>Points: {{ series.points.length }}</p>
          <ul v-if="series.warnings.length" class="inline-warnings">
            <li v-for="warning in series.warnings" :key="warning">{{ warning }}</li>
          </ul>
        </article>
      </div>
      <p v-else-if="!isLoading" class="empty-state">No trend snapshots yet. Run a Player Value build to create the first snapshot.</p>
    </section>
  </section>
</template>
