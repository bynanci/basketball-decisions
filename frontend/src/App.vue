<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink to="/" class="brand">Basketball Decisions</RouterLink>
      <nav>
        <RouterLink to="/">Home</RouterLink>
        <RouterLink to="/start">Choose training role</RouterLink>
        <RouterLink to="/training">Training</RouterLink>
        <RouterLink to="/situations">Situations</RouterLink>
        <RouterLink to="/local-lab">Local Lab</RouterLink>
        <RouterLink to="/player-value">Player Value</RouterLink>
        <RouterLink to="/reports/coach">Coach Reports</RouterLink>
        <RouterLink to="/review-queue">Review Queue</RouterLink>
        <RouterLink to="/model-registry">Model Registry</RouterLink>
        <RouterLink to="/reference-videos">Reference Videos</RouterLink>
        <RouterLink to="/decision-rules">Decision Rules</RouterLink>
      </nav>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>
