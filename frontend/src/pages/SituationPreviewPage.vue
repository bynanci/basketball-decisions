<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import RoleCourtPreview from '../components/RoleCourtPreview.vue'
import { useRoleStore } from '../stores/roleStore'

const roleStore = useRoleStore()
const roleProfile = computed(() => roleStore.roleProfile)

function formatRole(value: string) {
  return value
    .split('_')
    .map((part) => part.charAt(0) + part.slice(1).toLowerCase())
    .join(' ')
}
</script>

<template>
  <section v-if="!roleProfile" class="card hero-card">
    <p class="eyebrow">Situation preview</p>
    <h1>Choose your court role first</h1>
    <p>Select a role profile so Court IQ can draw the court areas and reads that matter to you.</p>
    <RouterLink class="button" to="/start">Go to role selection</RouterLink>
  </section>

  <template v-else>
    <section class="card situation-hero">
      <div>
        <p class="eyebrow">Situation preview</p>
        <h1>{{ formatRole(roleProfile.courtRole) }} court reads</h1>
        <p>
          This preview turns your selected role into a simple half-court map of spacing, lanes, and help responsibilities.
        </p>
      </div>
      <div class="hero-actions">
        <RouterLink class="button secondary-button" to="/start">Change role</RouterLink>
        <RouterLink class="button" to="/training">Start Training</RouterLink>
      </div>
    </section>

    <section class="card profile-summary">
      <div>
        <strong>Current mode</strong>
        <span>{{ formatRole(roleProfile.userRole) }} / {{ formatRole(roleProfile.courtRole) }}</span>
      </div>
      <div>
        <strong>Selected situations</strong>
        <span v-if="roleProfile.situationTypes.length">{{ roleProfile.situationTypes.map(formatRole).join(', ') }}</span>
        <span v-else>All situations</span>
      </div>
    </section>

    <section class="card">
      <RoleCourtPreview :court-role="roleProfile.courtRole" />
    </section>
  </template>
</template>

<style scoped>
.situation-hero,
.profile-summary {
  align-items: flex-start;
  display: flex;
  gap: 1rem;
  justify-content: space-between;
}

.situation-hero h1 {
  margin: 0.2rem 0;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  justify-content: flex-end;
}

.profile-summary {
  background: #f8fafc;
}

.profile-summary div {
  display: grid;
  gap: 0.35rem;
}

.profile-summary span {
  color: #334155;
}

@media (max-width: 720px) {
  .situation-hero,
  .profile-summary {
    display: grid;
  }

  .hero-actions {
    justify-content: flex-start;
  }
}
</style>
