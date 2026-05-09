<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink to="/" class="brand">Basketball Decisions</RouterLink>
      <nav>
        <RouterLink to="/">Home</RouterLink>
      </nav>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>
