<template>
  <nav aria-label="Admin sections" class="flex gap-2 mt-6">
    <NuxtLink
      to="/admin"
      exact-active-class="bg-purple-600 text-white hover:bg-purple-700 dark:hover:bg-purple-700"
      class="px-5 py-2 font-semibold transition duration-200 border rounded-full hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800"
    >Users</NuxtLink>
    <NuxtLink
      to="/admin/events"
      exact-active-class="bg-purple-600 text-white hover:bg-purple-700 dark:hover:bg-purple-700"
      class="px-5 py-2 font-semibold transition duration-200 border rounded-full hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800"
    >Events</NuxtLink>
  </nav>
</template>
