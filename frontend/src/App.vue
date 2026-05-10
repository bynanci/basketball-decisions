<template>
  <div class="app-shell">
    <header class="topbar">
      <RouterLink to="/" class="brand">Basketball Decisions</RouterLink>
      <nav>
        <RouterLink to="/">Home</RouterLink>
        <RouterLink to="/start">Choose training role</RouterLink>
      </nav>
    </header>
    <main>
      <RouterView />
    </main>
  </div>
</template>
