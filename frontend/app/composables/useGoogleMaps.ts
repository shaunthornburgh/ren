/**
 * Lazily loads the Google Maps JavaScript API in the browser.
 *
 * The script is injected once per page load and shared by every caller, so a
 * page with several place fields still only fetches it a single time. The key
 * comes from `runtimeConfig.public.googleMapsApiKey`; when it is blank the
 * loader reports "not configured" instead of injecting a script that would
 * fail, letting callers fall back to a plain input.
 */

// Module-scoped so the promise survives component remounts (client-only).
let loadPromise: Promise<any> | null = null

const CALLBACK = '__renInitGoogleMaps'

export function useGoogleMaps() {
  const apiKey = useRuntimeConfig().public.googleMapsApiKey as string
  const isConfigured = computed(() => !!apiKey)

  function loadApi(): Promise<any> {
    if (loadPromise) return loadPromise

    loadPromise = new Promise((resolve, reject) => {
      if (import.meta.server) {
        reject(new Error('Google Maps can only load in the browser.'))
        return
      }
      const existing = (window as any).google?.maps
      if (existing) {
        resolve(existing)
        return
      }
      if (!apiKey) {
        reject(new Error('Google Maps API key is not configured.'))
        return
      }

      ;(window as any)[CALLBACK] = () => {
        delete (window as any)[CALLBACK]
        resolve((window as any).google.maps)
      }

      const script = document.createElement('script')
      const params = new URLSearchParams({
        key: apiKey,
        libraries: 'places',
        v: 'weekly',
        loading: 'async',
        callback: CALLBACK,
      })
      script.src = `https://maps.googleapis.com/maps/api/js?${params}`
      script.async = true
      script.onerror = () => {
        // Let a later attempt retry rather than caching the failure forever.
        loadPromise = null
        reject(new Error('Could not load Google Maps.'))
      }
      document.head.appendChild(script)
    })

    return loadPromise
  }

  /** Load a Maps library (e.g. `places`) and return its exports. */
  async function loadLibrary(name: string): Promise<any> {
    const maps = await loadApi()
    return maps.importLibrary(name)
  }

  return { apiKey, isConfigured, loadApi, loadLibrary }
}
