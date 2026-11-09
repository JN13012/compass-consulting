import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App'

function renderAt(path: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => vi.restoreAllMocks())

describe('App', () => {
  it('renders the main navigation', () => {
    renderAt('/veille')
    expect(screen.getByRole('navigation', { name: 'Navigation principale' })).toBeInTheDocument()
  })

  it('shows AI and data status in the sidebar', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = input instanceof Request ? input.url : String(input)
      const body = url.endsWith('/health')
        ? {
            status: 'ok', database: 'ok', version: '0.1.0', ai_active: 'local',
            ai_options: [{ role: 'local', label: 'IA locale', model: 'qwen3.5:9b', local: true, status: 'ok' }],
            search: { label: 'Recherche sémantique', status: 'ok', detail: 'bge-m3' },
            texts: { label: 'Textes officiels', status: 'ok', detail: '13 textes · à jour au 09/11' },
          }
        : []
      return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } })
    })
    renderAt('/')
    expect(await screen.findByRole('option', { name: 'Local · qwen3.5:9b + bge-m3' })).toBeInTheDocument()
    expect(screen.getByText('13 textes · à jour au 09/11')).toBeInTheDocument()
  })

  it('renders a mission with its seven tabs and diagnostic results', async () => {
    const mission = {
      id: 'm1', client: 'Hexa Industrie', sector: 'Industrie', focus: ['cyber'], confidentiality: 'public',
      created_at: '2026-11-07T10:00:00Z', steps_done: ['diagnostic'], context: 'ETI', notes: 'notes',
      maturity_axes: [], solutions: null, regulation: null,
      diagnostic: {
        synthese: 'SI vieillissant.', processus: [], maturite: [{ axe: 'Cyber - Protéger', note: 1, justification: 'pas de MFA' }],
        irritants: [{ id: 'I1', titre: 'Pas de MFA', description: 'VPN sans MFA', impact: 'élevé', source: 'pas d’authentification multifacteur', source_verifiee: true }],
      },
    }
    // a fresh Response per call: the sidebar also fetches (a body can only be read once)
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () =>
      new Response(JSON.stringify(mission), { headers: { 'Content-Type': 'application/json' } }),
    )
    renderAt('/missions/m1/diagnostic')
    expect(await screen.findByText('Pas de MFA')).toBeInTheDocument()
    expect(screen.getByText('✓ citation retrouvée dans les notes')).toBeInTheDocument()
    const tabs = screen.getByRole('navigation', { name: 'Étapes de la mission' })
    expect(tabs.querySelectorAll('a')).toHaveLength(7)
  })
})
