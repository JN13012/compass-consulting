import createClient from 'openapi-fetch'

import type { paths } from './schema'

/** Typed API client. Types come from `npm run gen:api` — never edit schema.d.ts by hand. */
export const api = createClient<paths>({
  baseUrl: `${window.location.origin}/api`,
  // Resolve fetch at call time (lets tests mock it).
  fetch: (request) => globalThis.fetch(request),
})
