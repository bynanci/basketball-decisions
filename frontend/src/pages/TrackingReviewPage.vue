<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { apiClient, isApiClientError } from '../api/client'
import type { Detection, DetectionRecognitionScore, PlayerAlias, PlayerTrack, TeamSide, TrackRecognitionScore, TrackReviewPatch, TrackReviewResponse } from '../api/client'
import { useProjectHydration } from '../composables/useProjectHydration'
import { useProjectStore } from '../stores/projectStore'

const props = defineProps<{
  projectId: string
}>()

const projectStore = useProjectStore()
const { ensureProjectHydrated, isHydrating, hydrationError, hydrationErrorCode, hydrationErrorHint } = useProjectHydration()
projectStore.setActiveProject(props.projectId)

const project = computed(() => projectStore.getProject(props.projectId))
const review = ref<TrackReviewResponse | null>(null)
const selectedFrameIndex = ref<number | null>(null)
const excludedDetectionIds = ref<Set<string>>(new Set())
const excludedTrackIds = ref<Set<string>>(new Set())
const notes = ref('')
const isLoadingReview = ref(false)
const isSaving = ref(false)
const isScoring = ref(false)
const isModelScoring = ref(false)
const errorMessage = ref('')
const errorCode = ref('')
const errorHint = ref('')
const saveMessage = ref('')
const recognitionMessage = ref('')
const detectionScores = ref<DetectionRecognitionScore[]>([])
const trackScores = ref<TrackRecognitionScore[]>([])
const modelDetectionScores = ref<DetectionRecognitionScore[]>([])
const modelTrackScores = ref<TrackRecognitionScore[]>([])
const aliases = ref<PlayerAlias[]>([])
const selectedAliasKey = ref('')
const showExcludedAliasTracks = ref(false)
const isSavingAliases = ref(false)
const aliasMessage = ref('')

const rawTracking = computed(() => review.value?.tracking ?? null)
const detections = computed(() => rawTracking.value?.detections ?? project.value?.detections ?? [])
const tracks = computed(() => rawTracking.value?.tracks ?? project.value?.tracks ?? [])
const cleanedTracking = computed(() => review.value?.cleaned_tracking ?? null)
const cleanedProjectedTracks = computed(() => review.value?.cleaned_projected_tracks ?? [])
const hasTracking = computed(() => detections.value.length > 0 || tracks.value.length > 0)
const frameOptions = computed(() => Array.from(new Set(detections.value.map((detection) => detection.frame_index))).sort((a, b) => a - b))
const currentFrameIndex = computed(() => selectedFrameIndex.value ?? frameOptions.value[0] ?? project.value?.frames[0]?.frame_index ?? 0)
const currentFrame = computed(() => project.value?.frames.find((frame) => frame.frame_index === currentFrameIndex.value) ?? project.value?.frames[0] ?? null)
const frameSrc = computed(() => (currentFrame.value ? apiClient.frameImageUrl(props.projectId, currentFrame.value.frame_index) : undefined))
const overlayWidth = computed(() => currentFrame.value?.width ?? project.value?.videoAsset?.width ?? 100)
const overlayHeight = computed(() => currentFrame.value?.height ?? project.value?.videoAsset?.height ?? 100)
const frameDetections = computed(() => detections.value.filter((detection) => detection.frame_index === currentFrameIndex.value))
const rawTrackCount = computed(() => tracks.value.length)
const cleanedTrackCount = computed(() => cleanedTracking.value?.tracks.length ?? 0)
const detectionScoreById = computed(() => new Map(detectionScores.value.map((score) => [score.detection_id, score])))
const trackScoreById = computed(() => new Map(trackScores.value.map((score) => [score.track_id, score])))
const modelDetectionScoreById = computed(() => new Map(modelDetectionScores.value.map((score) => [score.detection_id, score])))
const modelTrackScoreById = computed(() => new Map(modelTrackScores.value.map((score) => [score.track_id, score])))

const assignedTrackIds = computed(() => new Set(aliases.value.flatMap((alias) => alias.track_ids)))
const unaliasedTrackCount = computed(() => tracks.value.filter((track) => !assignedTrackIds.value.has(track.track_id)).length)
const aliasableTrackSummaries = computed(() => trackSummaries.value.filter((summary) => showExcludedAliasTracks.value || !summary.excluded))

const trackSummaries = computed(() =>
  tracks.value
    .map((track) => ({
      track,
      detectionCount: detections.value.filter((detection) => detection.track_id === track.track_id).length,
      pointCount: track.points.length,
      score: trackScoreById.value.get(track.track_id) ?? null,
      modelScore: modelTrackScoreById.value.get(track.track_id) ?? null,
      playerKey: playerKeyForTrack(track.track_id),
      excluded: excludedTrackIds.value.has(track.track_id)
    }))
    .sort((a, b) => b.pointCount - a.pointCount || a.track.track_id.localeCompare(b.track.track_id))
)

watch(frameOptions, (options) => {
  if (selectedFrameIndex.value === null && options.length > 0) selectedFrameIndex.value = options[0]
})

onMounted(async () => {
  await ensureProjectHydrated(props.projectId, { force: true }).catch(() => undefined)
  await loadReview()
  await loadAliases()
})

function showError(error: unknown, fallbackMessage: string) {
  if (isApiClientError(error)) {
    errorCode.value = error.code
    errorMessage.value = error.message
    errorHint.value = error.debug_hint ?? ''
  } else {
    errorCode.value = 'TRACKING_REVIEW_ERROR'
    errorMessage.value = fallbackMessage
    errorHint.value = error instanceof Error ? error.message : ''
  }
}

function hydratePatch(patch: TrackReviewPatch) {
  excludedDetectionIds.value = new Set(patch.excluded_detection_ids ?? [])
  excludedTrackIds.value = new Set(patch.excluded_track_ids ?? [])
  notes.value = patch.notes ?? ''
}

async function loadReview() {
  isLoadingReview.value = true
  errorMessage.value = ''
  errorCode.value = ''
  errorHint.value = ''
  try {
    const response = await apiClient.getTrackingReview(props.projectId)
    review.value = response
    hydratePatch(response.review_patch)
    if (selectedFrameIndex.value === null && frameOptions.value.length > 0) selectedFrameIndex.value = frameOptions.value[0]
  } catch (error) {
    showError(error, 'Could not load tracking review data.')
  } finally {
    isLoadingReview.value = false
  }
}

function hydrateAliases(payload?: { aliases?: PlayerAlias[] } | null) {
  aliases.value = (payload?.aliases ?? []).map((alias) => ({ ...alias, track_ids: [...alias.track_ids] }))
  if (!selectedAliasKey.value && aliases.value.length > 0) selectedAliasKey.value = aliases.value[0].player_key
}

async function loadAliases() {
  aliasMessage.value = ''
  try {
    if (project.value?.playerAliases) {
      hydrateAliases(project.value.playerAliases)
      return
    }
    const response = await apiClient.getPlayerAliases(props.projectId)
    projectStore.setPlayerAliases(props.projectId, response)
    hydrateAliases(response)
  } catch (error) {
    showError(error, 'Could not load player aliases.')
  }
}

function nextPlayerKey() {
  const used = new Set(aliases.value.map((alias) => alias.player_key))
  let index = 1
  while (used.has(`P${index}`)) index += 1
  return `P${index}`
}

function createAlias() {
  const playerKey = nextPlayerKey()
  aliases.value = [
    ...aliases.value,
    {
      player_key: playerKey,
      project_id: props.projectId,
      track_ids: [],
      display_name: null,
      team_side: 'UNKNOWN',
      role_hint: null,
      confidence: 1,
      source: 'MANUAL',
      notes: null
    }
  ]
  selectedAliasKey.value = playerKey
}

function playerKeyForTrack(trackId: string) {
  return aliases.value.find((alias) => alias.track_ids.includes(trackId))?.player_key ?? ''
}

function setAliasTeam(alias: PlayerAlias, teamSide: string) {
  alias.team_side = teamSide as TeamSide
}

function toggleTrackAlias(trackId: string, playerKey: string, checked: boolean) {
  if (!playerKey) return
  aliases.value = aliases.value.map((alias) => {
    const trackIds = alias.track_ids.filter((id) => id !== trackId)
    if (checked && alias.player_key === playerKey) trackIds.push(trackId)
    return { ...alias, track_ids: Array.from(new Set(trackIds)).sort() }
  })
}

async function saveAliases() {
  if (isSavingAliases.value) return
  isSavingAliases.value = true
  aliasMessage.value = ''
  errorMessage.value = ''
  errorCode.value = ''
  errorHint.value = ''
  try {
    const response = await apiClient.savePlayerAliases(props.projectId, {
      project_id: props.projectId,
      aliases: aliases.value.map((alias) => ({
        ...alias,
        project_id: props.projectId,
        display_name: alias.display_name?.trim() || null,
        role_hint: alias.role_hint?.trim() || null,
        notes: alias.notes?.trim() || null,
        source: 'MANUAL' as const,
        confidence: alias.confidence ?? 1
      })).filter((alias) => alias.player_key.trim() && alias.track_ids.length > 0)
    })
    projectStore.setPlayerAliases(props.projectId, response)
    hydrateAliases(response)
    aliasMessage.value = `Saved ${response.aliases.length} aliases covering ${response.aliases.flatMap((alias) => alias.track_ids).length} tracks.`
  } catch (error) {
    showError(error, 'Could not save player aliases.')
  } finally {
    isSavingAliases.value = false
  }
}

function isDetectionExcluded(detection: Detection) {
  return excludedDetectionIds.value.has(detection.detection_id) || (detection.track_id ? excludedTrackIds.value.has(detection.track_id) : false)
}

function checkedFromEvent(event: Event) {
  return (event.target as HTMLInputElement).checked
}

function valueFromEvent(event: Event) {
  return (event.target as HTMLSelectElement).value
}

function toggleDetection(detectionId: string, checked: boolean) {
  const next = new Set(excludedDetectionIds.value)
  if (checked) next.add(detectionId)
  else next.delete(detectionId)
  excludedDetectionIds.value = next
}

function toggleTrack(trackId: string, checked: boolean) {
  const next = new Set(excludedTrackIds.value)
  if (checked) next.add(trackId)
  else next.delete(trackId)
  excludedTrackIds.value = next
}

function trackOpacity(track: PlayerTrack) {
  return excludedTrackIds.value.has(track.track_id) ? 0.2 : 0.9
}

function pathForTrack(track: PlayerTrack) {
  return track.points.map((point) => `${point.image_point_x},${point.image_point_y}`).join(' ')
}

function riskClass(label?: string | null) {
  return `risk-${(label ?? 'unknown').toLowerCase()}`
}

function scoreForDetection(detection: Detection) {
  return detectionScoreById.value.get(detection.detection_id) ?? null
}

function modelScoreForDetection(detection: Detection) {
  return modelDetectionScoreById.value.get(detection.detection_id) ?? null
}

function formatRisk(score?: DetectionRecognitionScore | TrackRecognitionScore | null) {
  if (!score) return ''
  return `${Math.round(score.false_positive_risk * 100)}% false-positive risk`
}

async function scoreRecognitionQuality() {
  if (isScoring.value) return
  isScoring.value = true
  recognitionMessage.value = ''
  errorMessage.value = ''
  errorCode.value = ''
  errorHint.value = ''
  try {
    const response = await apiClient.scoreRecognitionQuality(props.projectId)
    detectionScores.value = response.detection_scores
    trackScores.value = response.track_scores
    recognitionMessage.value = `Scored ${response.detection_scores.length} detections and ${response.track_scores.length} tracks. High risk: ${response.summary.high_risk_detection_count} detections, ${response.summary.high_risk_track_count} tracks.`
  } catch (error) {
    showError(error, 'Could not score recognition quality.')
  } finally {
    isScoring.value = false
  }
}

async function scoreWithRecognitionModel() {
  if (isModelScoring.value) return
  isModelScoring.value = true
  recognitionMessage.value = ''
  errorMessage.value = ''
  errorCode.value = ''
  errorHint.value = ''
  try {
    const response = await apiClient.scoreRecognitionModel(props.projectId)
    modelDetectionScores.value = response.detection_scores
    modelTrackScores.value = response.track_scores
    recognitionMessage.value = `Model ${response.model_version ?? response.summary.model_version ?? 'active'} scored ${response.detection_scores.length} detections and ${response.track_scores.length} tracks. High risk: ${response.summary.high_risk_detection_count} detections, ${response.summary.high_risk_track_count} tracks.`
  } catch (error) {
    showError(error, 'Could not score with the trained recognition model.')
  } finally {
    isModelScoring.value = false
  }
}

function buildPatch(): TrackReviewPatch {
  return {
    excluded_detection_ids: Array.from(excludedDetectionIds.value).sort(),
    excluded_track_ids: Array.from(excludedTrackIds.value).sort(),
    track_id_aliases: review.value?.review_patch.track_id_aliases ?? {},
    notes: notes.value.trim() || null
  }
}

async function saveReview() {
  if (isSaving.value) return
  isSaving.value = true
  saveMessage.value = ''
  errorMessage.value = ''
  errorCode.value = ''
  errorHint.value = ''
  try {
    const response = await apiClient.saveTrackingReview(props.projectId, buildPatch())
    review.value = response
    hydratePatch(response.review_patch)
    projectStore.setTracks(props.projectId, {
      detections: response.tracking.detections,
      tracks: response.tracking.tracks,
      projectedTracks: project.value?.projectedTracks ?? [],
      pipelineOutput: response.tracking.pipeline_output ?? null,
      debugMetadata: response.tracking.debug_metadata ?? null
    })
    saveMessage.value = `Saved ${response.cleaned_tracking?.tracks.length ?? 0} cleaned tracks and ${response.cleaned_projected_tracks.length} cleaned projected tracks.`
  } catch (error) {
    showError(error, 'Could not save tracking review edits.')
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <section class="card review-hero">
    <div>
      <p class="eyebrow">Manual tracking QC</p>
      <h1>Tracking Quality Review</h1>
      <p>Inspect raw person detections, exclude false-positive detections or full tracks, and save cleaned artifacts without overwriting raw tracking.</p>
    </div>
    <div class="hero-actions">
      <button type="button" :disabled="isScoring || !hasTracking" @click="scoreRecognitionQuality">{{ isScoring ? 'Scoring…' : 'Score Recognition Quality' }}</button>
      <button type="button" :disabled="isModelScoring || !hasTracking" @click="scoreWithRecognitionModel">{{ isModelScoring ? 'Scoring…' : 'Score with trained model' }}</button>
      <RouterLink class="button secondary" :to="`/projects/${projectId}/tracking`">Raw tracking</RouterLink>
      <RouterLink class="button secondary" :to="`/projects/${projectId}`">Project</RouterLink>
    </div>
  </section>

  <section v-if="isHydrating || isLoadingReview" class="card" aria-live="polite">
    <strong>Loading review…</strong>
    <p>Hydrating project frames, raw tracking, and any existing tracking review patch.</p>
  </section>

  <section v-if="hydrationError" class="error-card" role="alert">
    <strong>{{ hydrationErrorCode }}</strong>
    <p>{{ hydrationError }}</p>
    <small v-if="hydrationErrorHint">{{ hydrationErrorHint }}</small>
  </section>

  <section v-if="errorMessage" class="error-card" role="alert">
    <strong>{{ errorCode }}</strong>
    <p>{{ errorMessage }}</p>
    <small v-if="errorHint">{{ errorHint }}</small>
  </section>

  <section v-if="!hasTracking && !isLoadingReview" class="card">
    <h2>No tracking to review</h2>
    <p class="muted">Run tracking before using the quality review workflow.</p>
    <RouterLink class="button" :to="`/projects/${projectId}/tracking`">Run tracking</RouterLink>
  </section>

  <template v-else>
    <section class="card status-card">
      <div class="stats-grid">
        <span><strong>{{ rawTrackCount }}</strong> raw tracks</span>
        <span><strong>{{ excludedTrackIds.size }}</strong> excluded tracks</span>
        <span><strong>{{ excludedDetectionIds.size }}</strong> excluded detections</span>
        <span><strong>{{ cleanedTrackCount }}</strong> cleaned tracks saved</span>
        <span><strong>{{ cleanedProjectedTracks.length }}</strong> cleaned projected tracks</span>
      </div>
      <p v-if="recognitionMessage" class="success">{{ recognitionMessage }}</p>
      <p v-if="saveMessage" class="success">{{ saveMessage }}</p>
      <p class="muted">Raw tracking remains available; saved review output is stored separately as cleaned tracking and cleaned projected tracks.</p>
    </section>

    <section class="card alias-card">
      <div class="alias-header">
        <div>
          <p class="eyebrow">Player Identity</p>
          <h2>Player Alias Assignment</h2>
          <p class="muted">Manually group track IDs under stable local player_key values. No jersey recognition or automatic identity is used.</p>
        </div>
        <button type="button" @click="createAlias">Create alias {{ nextPlayerKey() }}</button>
      </div>

      <p v-if="unaliasedTrackCount > 0" class="warning"><strong>{{ unaliasedTrackCount }}</strong> tracks remain unaliased.</p>
      <p v-if="aliasMessage" class="success">{{ aliasMessage }}</p>

      <div class="alias-layout">
        <div class="alias-list">
          <label v-for="alias in aliases" :key="alias.player_key" class="alias-editor" :class="{ active: selectedAliasKey === alias.player_key }">
            <input v-model="selectedAliasKey" type="radio" :value="alias.player_key" />
            <strong>{{ alias.player_key }}</strong>
            <small>{{ alias.track_ids.length }} tracks</small>
            <input v-model="alias.display_name" type="text" placeholder="Display name (optional)" />
            <select :value="alias.team_side" @change="setAliasTeam(alias, valueFromEvent($event))">
              <option value="UNKNOWN">Unknown team</option>
              <option value="HOME">Home</option>
              <option value="AWAY">Away</option>
            </select>
            <input v-model="alias.role_hint" type="text" placeholder="Role hint (optional)" />
            <textarea v-model="alias.notes" rows="2" placeholder="Alias notes" />
          </label>
          <p v-if="aliases.length === 0" class="muted">Create P1/P2/P3 aliases, then assign tracks below.</p>
        </div>

        <div class="alias-track-list">
          <label class="inline-toggle">
            <input v-model="showExcludedAliasTracks" type="checkbox" />
            Show excluded tracks for aliasing
          </label>
          <label v-for="summary in aliasableTrackSummaries" :key="summary.track.track_id" class="track-row" :class="{ excluded: summary.excluded }">
            <input
              type="checkbox"
              :disabled="!selectedAliasKey || (!!summary.playerKey && summary.playerKey !== selectedAliasKey)"
              :checked="summary.playerKey === selectedAliasKey"
              @change="toggleTrackAlias(summary.track.track_id, selectedAliasKey, checkedFromEvent($event))"
            />
            <span>
              <strong>{{ summary.track.track_id }}</strong>
              <small>{{ summary.pointCount }} points · {{ summary.detectionCount }} detections</small>
              <small v-if="summary.excluded">Excluded by review</small>
              <small v-if="summary.playerKey">Assigned to {{ summary.playerKey }}</small>
              <span v-if="summary.score" class="risk-detail">
                <span class="risk-badge" :class="riskClass(summary.score.recommended_label)">{{ summary.score.recommended_label }}</span>
                <small>{{ formatRisk(summary.score) }}</small>
              </span>
              <span v-if="summary.modelScore" class="risk-detail model-risk-detail">
                <span class="risk-badge" :class="riskClass(summary.modelScore.recommended_label)">Model {{ summary.modelScore.recommended_label }}</span>
                <small>{{ formatRisk(summary.modelScore) }}</small>
              </span>
            </span>
          </label>
        </div>
      </div>

      <button type="button" :disabled="isSavingAliases" @click="saveAliases">{{ isSavingAliases ? 'Saving aliases…' : 'Save player aliases' }}</button>
    </section>


    <section class="grid review-grid">
      <div class="card stage-card">
        <div class="timeline-row">
          <label>
            Frame
            <select v-model.number="selectedFrameIndex">
              <option v-for="frameIndex in frameOptions" :key="frameIndex" :value="frameIndex">Frame {{ frameIndex }}</option>
            </select>
          </label>
          <input v-model.number="selectedFrameIndex" type="range" :min="frameOptions[0] ?? 0" :max="frameOptions[frameOptions.length - 1] ?? 0" :disabled="frameOptions.length === 0" />
        </div>

        <div v-if="frameSrc" class="frame-shell">
          <img :src="frameSrc" :alt="`Tracking review frame ${currentFrameIndex}`" />
          <svg class="review-overlay" :viewBox="`0 0 ${overlayWidth} ${overlayHeight}`" preserveAspectRatio="none" aria-label="Raw tracking quality overlay">
            <g v-for="track in tracks" :key="track.track_id" class="raw-path" :style="{ opacity: trackOpacity(track) }">
              <polyline v-if="track.points.length" :points="pathForTrack(track)" />
            </g>
            <g v-for="detection in frameDetections" :key="detection.detection_id" class="bbox" :class="{ excluded: isDetectionExcluded(detection) }">
              <rect :x="detection.box.x" :y="detection.box.y" :width="detection.box.width" :height="detection.box.height" rx="2" />
              <text :x="detection.box.x" :y="Math.max(6, detection.box.y - 3)">
                {{ detection.track_id ?? detection.detection_id }} · {{ Math.round(detection.confidence * 100) }}%
              </text>
            </g>
          </svg>
        </div>
        <p v-else class="muted">No extracted frame image is available, but you can still exclude tracks in the list.</p>

        <div class="detection-list">
          <h2>Frame {{ currentFrameIndex }} detections</h2>
          <label v-for="detection in frameDetections" :key="detection.detection_id" class="qc-row" :class="{ excluded: isDetectionExcluded(detection) }">
            <input type="checkbox" :checked="excludedDetectionIds.has(detection.detection_id)" @change="toggleDetection(detection.detection_id, checkedFromEvent($event))" />
            <span>Exclude detection</span>
            <strong>{{ detection.track_id ?? 'untracked' }}</strong>
            <span v-if="scoreForDetection(detection)" class="risk-detail">
              <span class="risk-badge" :class="riskClass(scoreForDetection(detection)?.recommended_label)">{{ scoreForDetection(detection)?.recommended_label }}</span>
              <small>Rule: {{ formatRisk(scoreForDetection(detection)) }}</small>
              <small v-for="reason in scoreForDetection(detection)?.reasons" :key="reason">{{ reason }}</small>
            </span>
            <span v-if="modelScoreForDetection(detection)" class="risk-detail model-risk-detail">
              <span class="risk-badge" :class="riskClass(modelScoreForDetection(detection)?.recommended_label)">Model {{ modelScoreForDetection(detection)?.recommended_label }}</span>
              <small>{{ formatRisk(modelScoreForDetection(detection)) }}</small>
            </span>
            <code>{{ detection.detection_id }}</code>
          </label>
        </div>
      </div>

      <aside class="card side-panel">
        <h2>Tracks</h2>
        <p class="muted">Exclude an entire track when it is a referee, coach, bench player, or spectator.</p>
        <div class="track-list">
          <label v-for="summary in trackSummaries" :key="summary.track.track_id" class="track-row" :class="{ excluded: excludedTrackIds.has(summary.track.track_id) }">
            <input type="checkbox" :checked="excludedTrackIds.has(summary.track.track_id)" @change="toggleTrack(summary.track.track_id, checkedFromEvent($event))" />
            <span>
              <strong>{{ summary.track.track_id }}</strong>
              <small>{{ summary.pointCount }} points · {{ summary.detectionCount }} detections</small>
              <span v-if="summary.score" class="risk-detail">
                <span class="risk-badge" :class="riskClass(summary.score.recommended_label)">{{ summary.score.recommended_label }}</span>
                <small>Rule: {{ formatRisk(summary.score) }}</small>
                <small v-for="reason in summary.score.reasons" :key="reason">{{ reason }}</small>
              </span>
              <span v-if="summary.modelScore" class="risk-detail model-risk-detail">
                <span class="risk-badge" :class="riskClass(summary.modelScore.recommended_label)">Model {{ summary.modelScore.recommended_label }}</span>
                <small>{{ formatRisk(summary.modelScore) }}</small>
              </span>
            </span>
          </label>
        </div>

        <label class="notes-field">
          Review notes
          <textarea v-model="notes" rows="5" placeholder="Optional notes about excluded tracks or uncertain detections." />
        </label>

        <button type="button" :disabled="isSaving" @click="saveReview">{{ isSaving ? 'Saving…' : 'Save review' }}</button>
      </aside>
    </section>
  </template>
</template>

<style scoped>
.review-hero,
.timeline-row,
.hero-actions {
  align-items: flex-start;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
}

.eyebrow {
  color: #1f6feb;
  font-size: 0.8rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  margin: 0 0 0.25rem;
  text-transform: uppercase;
}

.secondary {
  background: #475569;
}

.stats-grid {
  display: grid;
  gap: 0.75rem;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
}

.stats-grid span {
  background: #f1f5f9;
  border-radius: 10px;
  padding: 0.75rem;
}

.success {
  color: #166534;
  font-weight: 800;
}

.muted {
  color: #64748b;
}

.review-grid {
  grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
}

.timeline-row {
  align-items: center;
  margin-bottom: 1rem;
}

.timeline-row label {
  display: grid;
  font-weight: 800;
  gap: 0.35rem;
}

.timeline-row input[type='range'] {
  flex: 1;
}

.frame-shell {
  background: #111827;
  border-radius: 16px;
  overflow: hidden;
  position: relative;
}

.frame-shell img {
  display: block;
  width: 100%;
}

.review-overlay {
  inset: 0;
  pointer-events: none;
  position: absolute;
}

.raw-path polyline {
  fill: none;
  stroke: #facc15;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 0.7;
}

.bbox rect {
  fill: rgb(34 197 94 / 0.18);
  stroke: #22c55e;
  stroke-width: 0.7;
}

.bbox.excluded rect {
  fill: rgb(239 68 68 / 0.22);
  stroke: #ef4444;
  stroke-dasharray: 3 2;
}

.bbox text {
  fill: white;
  font-size: 5px;
  font-weight: 800;
  paint-order: stroke;
  stroke: #0f172a;
  stroke-width: 0.6px;
}

.detection-list,
.track-list,
.side-panel,
.alias-list,
.alias-track-list {
  display: grid;
  gap: 0.75rem;
}

.qc-row,
.track-row {
  align-items: center;
  border: 1px solid #dde3ee;
  border-radius: 10px;
  display: flex;
  gap: 0.6rem;
  padding: 0.65rem;
}

.qc-row code {
  color: #475569;
  margin-left: auto;
}

.alias-header,
.alias-layout {
  display: grid;
  gap: 1rem;
}

.alias-header {
  align-items: start;
  grid-template-columns: minmax(0, 1fr) auto;
}

.alias-layout {
  grid-template-columns: minmax(260px, 1fr) minmax(280px, 1.2fr);
}

.alias-editor {
  border: 1px solid #dde3ee;
  border-radius: 12px;
  display: grid;
  gap: 0.5rem;
  padding: 0.75rem;
}

.alias-editor.active {
  border-color: #1f6feb;
  box-shadow: 0 0 0 2px rgb(31 111 235 / 0.12);
}

.inline-toggle {
  align-items: center;
  display: flex;
  font-weight: 800;
  gap: 0.5rem;
}

.warning {
  color: #b45309;
  font-weight: 800;
}

.model-risk-detail {
  border-left: 3px solid #6366f1;
  padding-left: 0.5rem;
}

.risk-detail {
  display: grid;
  gap: 0.2rem;
}

.risk-badge {
  border-radius: 999px;
  color: white;
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 900;
  padding: 0.15rem 0.45rem;
  width: fit-content;
}

.risk-low {
  background: #16a34a;
}

.risk-medium {
  background: #d97706;
}

.risk-high {
  background: #dc2626;
}

.risk-unknown {
  background: #64748b;
}

.track-row span {
  display: grid;
}

.track-row small {
  color: #64748b;
}

.qc-row.excluded,
.track-row.excluded {
  background: #fef2f2;
  border-color: #fecaca;
}

.notes-field {
  display: grid;
  font-weight: 800;
  gap: 0.35rem;
}

input[type='text'],
textarea,
select {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0.55rem;
}

@media (max-width: 840px) {
  .review-hero,
  .timeline-row,
  .hero-actions {
    display: grid;
  }

  .review-grid,
  .alias-layout,
  .alias-header {
    grid-template-columns: 1fr;
  }
}
</style>
