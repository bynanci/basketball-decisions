<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { apiClient, type PlayerHomeResponse } from '../api/client'

const playerKey = ref('P1')
const home = ref<PlayerHomeResponse | null>(null)
const isLoading = ref(false)
const error = ref<string | null>(null)

const trendLabel = computed(() => {
  const value = home.value?.trend_direction
  if (value === 'up') return 'Improving'
  if (value === 'down') return 'Needs attention'
  if (value === 'flat') return 'Holding steady'
  return 'No trend yet'
})

async function loadPlayerHome() {
  isLoading.value = true
  error.value = null
  try {
    home.value = await apiClient.getPlayerHome(playerKey.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Unable to load player home.'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadPlayerHome)
</script>

<template>
  <section class="page" data-testid="player-home-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Training</p>
        <h1>Player Home</h1>
      </div>
    </header>

    <section class="panel">
      <label>
        Player key
        <input v-model="playerKey" placeholder="P1" />
      </label>
      <button :disabled="isLoading" @click="loadPlayerHome">{{ isLoading ? 'Loading…' : 'Load player' }}</button>
    </section>

    <div v-if="error" class="error-callout">{{ error }}</div>
    <p v-if="!isLoading && !home" class="empty-state">Select a player to see today’s next action.</p>

    <section v-if="home" class="player-home-grid">
      <article class="panel"><h2>Today’s Focus</h2><p>{{ home.today_focus }}</p></article>
      <article class="panel"><h2>Current Strength</h2><p>{{ home.current_strength }}</p></article>
      <article class="panel"><h2>Current Risk</h2><p>{{ home.current_risk }}</p></article>
      <article class="panel"><h2>Recommended Drill</h2><p>{{ home.recommended_drill }}</p><RouterLink to="/drills">View Drill</RouterLink></article>
      <article class="panel"><h2>Latest Practice Feedback</h2><p>{{ home.latest_practice_feedback }}</p><RouterLink to="/practice-executions">Record Practice Feedback</RouterLink></article>
      <article class="panel"><h2>Progress Trend</h2><p>{{ trendLabel }}</p><RouterLink to="/player-value/trends">View Progress Trend</RouterLink></article>
      <article class="panel"><h2>Confidence</h2><p>{{ home.confidence ?? '—' }}</p><ul v-if="home.warnings.length"><li v-for="warning in home.warnings" :key="warning">{{ warning }}</li></ul></article>
    </section>

    <section v-if="home" class="panel">
      <RouterLink class="primary" to="/practice-plans">{{ home.next_action }} — Start Training</RouterLink>
      <div>
        <RouterLink to="/practice-plans">View Practice Plan</RouterLink>
      </div>
    </section>
  </section>
</template>
