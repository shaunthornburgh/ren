<template>
  <div class="flex flex-col min-h-screen antialiased text-gray-900 dark:bg-gray-900 dark:text-gray-50">
    <AppHeader />
    <main class="flex-1">
      <slot />
    </main>
    <AppFooter />
  </div>
</template>
