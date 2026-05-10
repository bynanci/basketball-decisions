<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useRoleStore } from '../stores/roleStore'
import { COURT_ROLES, SITUATION_TYPES, USER_ROLES } from '../types/roles'
import type { CourtRole, RoleProfile, SituationType, UserRole } from '../types/roles'

const router = useRouter()
const roleStore = useRoleStore()

const selectedUserRole = ref<UserRole | null>(roleStore.roleProfile?.userRole ?? null)
const selectedCourtRole = ref<CourtRole | null>(roleStore.roleProfile?.courtRole ?? null)
const selectedSituations = ref<SituationType[]>(roleStore.roleProfile?.situationTypes ? [...roleStore.roleProfile.situationTypes] : [])

const canContinue = computed(() => selectedUserRole.value !== null && selectedCourtRole.value !== null)

const userRoleDescriptions: Record<UserRole, string> = {
  COACH: 'Create teaching points, review team choices, and prepare focused decision clips.',
  PLAYER: 'Train reads from your on-court perspective and rehearse the next best decision.',
  ANALYST: 'Study patterns, tags, and tactical context across possessions.',
  FAN: 'Explore basketball decisions with guided situations and plain-language framing.'
}

const courtRoleDescriptions: Record<CourtRole, string> = {
  BALL_HANDLER: 'Reads with the ball: coverage, help, passing windows, and shot choices.',
  OFF_BALL_SHOOTER: 'Spacing, relocation, catch decisions, and closeout attacks.',
  ROLLER: 'Short-roll playmaking, finishing angles, and pocket-pass decisions.',
  SCREENER: 'Screen angle, rescreen, slip, and separation timing decisions.',
  ON_BALL_DEFENDER: 'Contain, screen navigation, pressure, and contest decisions.',
  HELP_DEFENDER: 'Tag, stunt, rotate, and recovery decisions away from the ball.',
  LOW_MAN: 'Back-line rim protection, corner coverage, and x-out choices.',
  TRAILER: 'Transition spacing, early drag screens, and secondary-break reads.',
  WEAK_SIDE_WING: 'Weak-side spacing, lift, cut, and extra-pass decisions.'
}

const situationDescriptions: Record<SituationType, string> = {
  PICK_AND_ROLL: 'Ball-screen coverages, passing windows, and advantage creation.',
  SHORT_ROLL: 'Catch in space, finish, spray out, or make the next pass.',
  SPOT_UP: 'Catch-and-shoot, drive, swing, or relocate decisions.',
  CLOSEOUT_ATTACK: 'Attack long closeouts and choose the right finish or pass.',
  TRANSITION_3_ON_2: 'Numbers advantage spacing, rim pressure, and kick-ahead choices.',
  LATE_CLOCK: 'Urgent clock management and shot-quality tradeoffs.',
  POST_DOUBLE: 'Recognize doubles, punish rotations, and find release valves.',
  DRIVE_AND_KICK: 'Help reactions, corner reads, and extra-pass timing.',
  HELP_ROTATION: 'Defensive rotation chains, stunts, and recovery paths.',
  LOW_MAN_DECISION: 'Protect the rim, cover the corner, or trigger x-outs.',
  OFF_BALL_RELOCATION: 'Move after the pass, improve angles, and punish help.'
}

function formatRole(value: string) {
  return value
    .split('_')
    .map((part) => part.charAt(0) + part.slice(1).toLowerCase())
    .join(' ')
}

function toggleSituation(situation: SituationType) {
  if (selectedSituations.value.includes(situation)) {
    selectedSituations.value = selectedSituations.value.filter((item) => item !== situation)
  } else {
    selectedSituations.value = [...selectedSituations.value, situation]
  }
}

function saveRoleProfile(destination: '/training' | '/situations') {
  if (!selectedUserRole.value || !selectedCourtRole.value) return

  const profile: RoleProfile = {
    userRole: selectedUserRole.value,
    courtRole: selectedCourtRole.value,
    situationTypes: selectedSituations.value
  }

  roleStore.setRoleProfile(profile)
  router.push(destination)
}

function saveAndContinue() {
  saveRoleProfile('/training')
}

function saveAndPreview() {
  saveRoleProfile('/situations')
}

function clearProfile() {
  roleStore.clearRoleProfile()
  selectedUserRole.value = null
  selectedCourtRole.value = null
  selectedSituations.value = []
}
</script>

<template>
  <section class="card hero-card">
    <p class="eyebrow">Role-based entry</p>
    <h1>Choose how you want Court IQ to frame decisions.</h1>
    <p>
      Pick a product perspective, an on-court role, and any training situations you want to focus on. This is optional and will not block the existing project workflow.
    </p>
  </section>

  <section v-if="roleStore.roleProfile" class="card current-profile-card">
    <div>
      <p class="eyebrow">Current profile</p>
      <h2>{{ formatRole(roleStore.roleProfile.userRole) }} / {{ formatRole(roleStore.roleProfile.courtRole) }}</h2>
      <p v-if="roleStore.roleProfile.situationTypes.length">
        Situations: {{ roleStore.roleProfile.situationTypes.map(formatRole).join(', ') }}
      </p>
      <p v-else>No situations selected yet.</p>
    </div>
    <button type="button" class="secondary-button" @click="clearProfile">Change from scratch</button>
  </section>

  <section class="entry-step card">
    <p class="eyebrow">Step 1</p>
    <h2>User role</h2>
    <p>Choose the lens for language, workflows, and recommendations.</p>
    <div class="choice-grid">
      <button
        v-for="role in USER_ROLES"
        :key="role"
        type="button"
        class="choice-card"
        :class="{ selected: selectedUserRole === role }"
        @click="selectedUserRole = role"
      >
        <strong>{{ formatRole(role) }}</strong>
        <span>{{ userRoleDescriptions[role] }}</span>
      </button>
    </div>
  </section>

  <section class="entry-step card">
    <p class="eyebrow">Step 2</p>
    <h2>Court role</h2>
    <p>Choose the role whose decisions you want to train or analyze.</p>
    <div class="choice-grid compact">
      <button
        v-for="role in COURT_ROLES"
        :key="role"
        type="button"
        class="choice-card"
        :class="{ selected: selectedCourtRole === role }"
        @click="selectedCourtRole = role"
      >
        <strong>{{ formatRole(role) }}</strong>
        <span>{{ courtRoleDescriptions[role] }}</span>
      </button>
    </div>
  </section>

  <section class="entry-step card">
    <p class="eyebrow">Step 3 · optional</p>
    <h2>Situation types</h2>
    <p>Select any contexts you want surfaced first. You can leave this empty.</p>
    <div class="choice-grid compact">
      <button
        v-for="situation in SITUATION_TYPES"
        :key="situation"
        type="button"
        class="choice-card"
        :class="{ selected: selectedSituations.includes(situation) }"
        @click="toggleSituation(situation)"
      >
        <strong>{{ formatRole(situation) }}</strong>
        <span>{{ situationDescriptions[situation] }}</span>
      </button>
    </div>
  </section>

  <section class="sticky-action card">
    <div>
      <strong>Ready to continue?</strong>
      <p>Saving stores your profile in this browser for your next visit.</p>
    </div>
    <div class="action-buttons">
      <button type="button" :disabled="!canContinue" @click="saveAndContinue">Start Training</button>
      <button type="button" class="secondary-button" :disabled="!canContinue" @click="saveAndPreview">View Role Situation Preview</button>
    </div>
  </section>
</template>
