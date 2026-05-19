<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { primaryNavigationItems } from './navigation'
import { APP_RELEASE_CHANNEL, APP_VERSION } from './version'

const commandCenterLink = primaryNavigationItems.find((item) => item.routeName === 'development-dashboard')
const groupedNavigationItems = computed(() =>
  primaryNavigationItems
    .filter((item) => item.routeName !== 'development-dashboard')
    .reduce<Record<string, typeof primaryNavigationItems>>((groups, item) => {
      groups[item.section] = groups[item.section] ?? []
      groups[item.section].push(item)
      return groups
    }, {})
)
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink to="/development-dashboard" class="brand">Basketball Decisions</RouterLink>
      <nav aria-label="Product navigation">
        <RouterLink v-if="commandCenterLink" :to="commandCenterLink.path" class="command-center-link" data-testid="nav-development-dashboard">
          Command Center
        </RouterLink>
        <div class="nav-sections">
          <div v-for="(items, sectionName) in groupedNavigationItems" :key="sectionName" class="nav-section">
            <span class="nav-section-label">{{ sectionName }}</span>
            <RouterLink v-for="item in items" :key="item.routeName" :to="item.path" :title="item.description" :data-testid="`nav-${item.routeName}`">
              {{ item.label }}
            </RouterLink>
          </div>
        </div>
        <p class="version-pill" data-testid="app-version">{{ APP_VERSION }} · {{ APP_RELEASE_CHANNEL }}</p>
      </nav>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>


<style scoped>
.version-pill {
  margin: 0.5rem 0 0;
  font-size: 0.8rem;
  color: #6b7280;
}
</style>
