<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  apiClient,
  isApiClientError,
  type BreakdownConfidence,
  type CourtRoleTarget,
  type DecisionRuleDraft,
  type QuizPromptDraft,
  type ReferenceBreakdownNote,
  type ReferenceVideo,
  type SituationType
} from '../api/client'

const props = defineProps<{ referenceId: string }>()

const courtRoles: CourtRoleTarget[] = ['BALL_HANDLER', 'OFF_BALL_SHOOTER', 'ROLLER', 'SCREENER', 'ON_BALL_DEFENDER', 'HELP_DEFENDER', 'LOW_MAN', 'TRAILER', 'WEAK_SIDE_WING']
const situationTypes: SituationType[] = ['PICK_AND_ROLL', 'SHORT_ROLL', 'SPOT_UP', 'CLOSEOUT_ATTACK', 'TRANSITION_3_ON_2', 'LATE_CLOCK', 'POST_DOUBLE', 'DRIVE_AND_KICK', 'HELP_ROTATION', 'LOW_MAN_DECISION', 'OFF_BALL_RELOCATION']
const confidenceValues: BreakdownConfidence[] = ['LOW', 'MEDIUM', 'HIGH']

const referenceVideo = ref<ReferenceVideo | null>(null)
const notes = ref<ReferenceBreakdownNote[]>([])
const quizDrafts = ref<QuizPromptDraft[]>([])
const ruleDrafts = ref<DecisionRuleDraft[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const statusMessage = ref('')
const errorMessage = ref('')
const errorCode = ref('')
const form = ref({
  timestamp_sec: '',
  timestamp_label: '',
  court_role: 'BALL_HANDLER' as CourtRoleTarget,
  situation_type: 'PICK_AND_ROLL' as SituationType,
  concept: '',
  good_read: '',
  bad_read: '',
  coaching_cue: '',
  tags: '',
  confidence: 'MEDIUM' as BreakdownConfidence
})

const sortedNotes = computed(() => [...notes.value].sort((a, b) => (a.timestamp_sec ?? 0) - (b.timestamp_sec ?? 0)))

function parseTags(value: string) {
  return value.split(',').map((tag) => tag.trim()).filter(Boolean)
}

function timestampDisplay(note: ReferenceBreakdownNote) {
  if (note.timestamp_label) return note.timestamp_label
  if (note.timestamp_sec === null || note.timestamp_sec === undefined) return '—'
  return `${note.timestamp_sec}s`
}

function showError(error: unknown, fallback: string) {
  if (isApiClientError(error)) {
    errorCode.value = error.code
    errorMessage.value = error.message
  } else {
    errorCode.value = 'FRONTEND_ERROR'
    errorMessage.value = error instanceof Error ? error.message : fallback
  }
}

async function loadDetail() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const [videosResponse, notesResponse, quizResponse, ruleResponse] = await Promise.all([
      apiClient.listReferenceVideos(),
      apiClient.listReferenceNotes(props.referenceId),
      apiClient.listReferenceQuizDrafts(props.referenceId),
      apiClient.listReferenceRuleDrafts(props.referenceId)
    ])
    referenceVideo.value = videosResponse.reference_videos.find((video) => video.reference_id === props.referenceId) ?? null
    notes.value = notesResponse
    quizDrafts.value = quizResponse
    ruleDrafts.value = ruleResponse
  } catch (error) {
    showError(error, 'Could not load reference video detail.')
  } finally {
    isLoading.value = false
  }
}

async function createNote() {
  isSaving.value = true
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    await apiClient.createReferenceNote(props.referenceId, {
      timestamp_sec: form.value.timestamp_sec ? Number(form.value.timestamp_sec) : null,
      timestamp_label: form.value.timestamp_label || null,
      court_role: form.value.court_role,
      situation_type: form.value.situation_type,
      concept: form.value.concept,
      good_read: form.value.good_read,
      bad_read: form.value.bad_read,
      coaching_cue: form.value.coaching_cue,
      tags: parseTags(form.value.tags),
      confidence: form.value.confidence
    })
    form.value = {
      timestamp_sec: '',
      timestamp_label: '',
      court_role: 'BALL_HANDLER',
      situation_type: 'PICK_AND_ROLL',
      concept: '',
      good_read: '',
      bad_read: '',
      coaching_cue: '',
      tags: '',
      confidence: 'MEDIUM'
    }
    statusMessage.value = 'Breakdown note added.'
    await loadDetail()
  } catch (error) {
    showError(error, 'Could not add the breakdown note.')
  } finally {
    isSaving.value = false
  }
}

async function convertToQuizDraft(note: ReferenceBreakdownNote) {
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    await apiClient.convertReferenceNoteToQuizDraft(props.referenceId, note.note_id)
    statusMessage.value = 'Quiz prompt draft created.'
    await loadDetail()
  } catch (error) {
    showError(error, 'Could not convert the note to a quiz draft.')
  }
}

async function convertToRuleDraft(note: ReferenceBreakdownNote) {
  statusMessage.value = ''
  errorMessage.value = ''
  try {
    await apiClient.convertReferenceNoteToRuleDraft(props.referenceId, note.note_id)
    statusMessage.value = 'Decision rule draft created.'
    await loadDetail()
  } catch (error) {
    showError(error, 'Could not convert the note to a rule draft.')
  }
}

onMounted(loadDetail)
</script>

<template>
  <section class="card detail-hero">
    <p class="eyebrow">Reference Video</p>
    <h1>{{ referenceVideo?.title ?? 'Reference video' }}</h1>
    <a v-if="referenceVideo" :href="referenceVideo.url" target="_blank" rel="noreferrer">{{ referenceVideo.url }}</a>
    <div v-if="referenceVideo" class="badge-row">
      <span class="warning-badge">{{ referenceVideo.usage_scope }}</span>
      <span class="danger-badge">NOT TRAINING ELIGIBLE</span>
      <span>{{ referenceVideo.license_type }}</span>
    </div>
    <p v-if="referenceVideo?.notes" class="muted">{{ referenceVideo.notes }}</p>
    <p v-if="statusMessage" class="success-message">{{ statusMessage }}</p>
    <div v-if="errorMessage" class="error-card" role="alert">
      <strong>{{ errorCode }}</strong>
      <p>{{ errorMessage }}</p>
    </div>
  </section>

  <section class="card">
    <p class="eyebrow">Manual extraction</p>
    <h2>Add breakdown note</h2>
    <form class="note-form" @submit.prevent="createNote">
      <label>Timestamp seconds<input v-model="form.timestamp_sec" type="number" step="0.1" min="0" placeholder="42.5" /></label>
      <label>Timestamp label<input v-model="form.timestamp_label" placeholder="0:42" /></label>
      <label>Court role<select v-model="form.court_role"><option v-for="role in courtRoles" :key="role" :value="role">{{ role }}</option></select></label>
      <label>Situation<select v-model="form.situation_type"><option v-for="situation in situationTypes" :key="situation" :value="situation">{{ situation }}</option></select></label>
      <label>Concept<textarea v-model="form.concept" required rows="2" /></label>
      <label>Good read<textarea v-model="form.good_read" required rows="2" /></label>
      <label>Bad read<textarea v-model="form.bad_read" required rows="2" /></label>
      <label>Coaching cue<textarea v-model="form.coaching_cue" required rows="2" /></label>
      <label>Tags<input v-model="form.tags" placeholder="tag defender, skip pass" /></label>
      <label>Confidence<select v-model="form.confidence"><option v-for="value in confidenceValues" :key="value" :value="value">{{ value }}</option></select></label>
      <button type="submit" :disabled="isSaving">{{ isSaving ? 'Saving…' : 'Add Note' }}</button>
    </form>
  </section>

  <section class="card">
    <div class="table-header"><h2>Breakdown notes</h2><span>{{ notes.length }} notes</span></div>
    <p v-if="isLoading">Loading…</p>
    <div v-else class="table-scroll">
      <table>
        <thead><tr><th>Time</th><th>Role</th><th>Situation</th><th>Concept</th><th>Good read</th><th>Bad read</th><th>Cue</th><th>Actions</th></tr></thead>
        <tbody>
          <tr v-for="note in sortedNotes" :key="note.note_id">
            <td>{{ timestampDisplay(note) }}</td>
            <td>{{ note.court_role }}</td>
            <td>{{ note.situation_type }}</td>
            <td>{{ note.concept }}</td>
            <td>{{ note.good_read }}</td>
            <td>{{ note.bad_read }}</td>
            <td>{{ note.coaching_cue }}</td>
            <td class="action-cell">
              <button type="button" @click="convertToQuizDraft(note)">Convert to Quiz Draft</button>
              <button type="button" @click="convertToRuleDraft(note)">Convert to Rule Draft</button>
            </td>
          </tr>
          <tr v-if="notes.length === 0"><td colspan="8">No breakdown notes yet.</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section class="draft-grid">
    <article class="card">
      <div class="table-header"><h2>Quiz Drafts</h2><span>{{ quizDrafts.length }} drafts</span></div>
      <div v-for="draft in quizDrafts" :key="draft.draft_id" class="draft-card">
        <strong>{{ draft.status }}</strong>
        <h3>{{ draft.question }}</h3>
        <p>{{ draft.role_instruction }}</p>
        <ol type="A"><li v-for="option in draft.options" :key="option.option_id">{{ option.label }} <strong v-if="option.is_correct">(correct)</strong></li></ol>
        <p><strong>Explanation:</strong> {{ draft.explanation }}</p>
      </div>
      <p v-if="quizDrafts.length === 0">No quiz drafts yet.</p>
    </article>

    <article class="card">
      <div class="table-header"><h2>Rule Drafts</h2><span>{{ ruleDrafts.length }} drafts</span></div>
      <div v-for="draft in ruleDrafts" :key="draft.draft_id" class="draft-card">
        <strong>{{ draft.status }}</strong>
        <p><strong>Condition:</strong> {{ draft.condition_text }}</p>
        <p><strong>Positive cue:</strong> {{ draft.positive_cue }}</p>
        <p><strong>Negative cue:</strong> {{ draft.negative_cue }}</p>
        <p><strong>Suggested weight:</strong> {{ draft.suggested_weight }}</p>
      </div>
      <p v-if="ruleDrafts.length === 0">No rule drafts yet.</p>
    </article>
  </section>
</template>

<style scoped>
.detail-hero,
.note-form,
.draft-card {
  display: grid;
  gap: 0.75rem;
}

.note-form {
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.note-form label {
  display: grid;
  gap: 0.35rem;
  font-weight: 700;
}

.note-form button {
  align-self: end;
}

.badge-row,
.action-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.badge-row span,
.warning-badge,
.danger-badge {
  border-radius: 999px;
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 800;
  padding: 0.2rem 0.55rem;
}

.warning-badge {
  background: #fef3c7;
  border: 1px solid #f59e0b;
  color: #92400e;
}

.danger-badge {
  background: #fee2e2;
  border: 1px solid #ef4444;
  color: #991b1b;
}

.success-message {
  color: #166534;
  font-weight: 800;
}

.table-header {
  align-items: center;
  display: flex;
  justify-content: space-between;
}

.table-scroll {
  overflow-x: auto;
}

table {
  border-collapse: collapse;
  min-width: 1100px;
  width: 100%;
}

th,
td {
  border-bottom: 1px solid #e2e8f0;
  padding: 0.7rem;
  text-align: left;
  vertical-align: top;
}

.draft-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
}

.draft-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  margin-top: 1rem;
  padding: 1rem;
}
</style>
