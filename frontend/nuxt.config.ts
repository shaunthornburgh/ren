// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-01',
  devtools: { enabled: true },

  modules: ['@nuxtjs/tailwindcss'],

  tailwindcss: {
    cssPath: '~/assets/css/main.css',
    configPath: 'tailwind.config.js',
  },

  runtimeConfig: {
    public: {
      // Overridable via NUXT_PUBLIC_API_BASE. Defaults to the backend exposed
      // by docker-compose on the host (calls are made from the browser).
      apiBase: 'http://localhost:8000/api/v1',
    },
  },

  app: {
    head: {
      htmlAttrs: { lang: 'en' },
      title: 'Ren — Discover & book event tickets',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        {
          name: 'description',
          content:
            'Ren is the easiest way to discover events and book tickets — ' +
            'concerts, festivals, conferences and more.',
        },
      ],
      link: [
        {
          rel: 'stylesheet',
          href: 'https://unpkg.com/boxicons@2.1.4/css/boxicons.min.css',
        },
      ],
      script: [
        {
          // Apply the persisted colour scheme before paint to avoid a flash.
          innerHTML:
            "(function(){try{var t=localStorage.theme;if(t==='dark'||(!t&&window.matchMedia('(prefers-color-scheme:dark)').matches)){document.documentElement.classList.add('dark')}}catch(e){}})()",
          tagPosition: 'head',
        },
      ],
    },
  },
})
