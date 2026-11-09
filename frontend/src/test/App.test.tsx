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
        ? { status: 'ok', database: 'ok', version: '0.1.0', ai_model: 'qwen3.5:9b (local)', ai_status: 'ok', search_model: 'bge-m3 (local)' }
        : []
      return new Response(JSON.stringify(body), { headers: { 'Content-Type': 'application/json' } })
    })
    renderAt('/')
    expect(await screen.findByText('qwen3.5:9b (local)')).toBeInTheDocument()
    expect(screen.getByText('disponibles')).toBeInTheDocument()
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
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(mission), { headers: { 'Content-Type': 'application/json' } }),
    )
    renderAt('/missions/m1/diagnostic')
    expect(await screen.findByText('Pas de MFA')).toBeInTheDocument()
    expect(screen.getByText('✓ citation retrouvée dans les notes')).toBeInTheDocument()
    const tabs = screen.getByRole('navigation', { name: 'Étapes de la mission' })
    expect(tabs.querySelectorAll('a')).toHaveLength(7)
  })
})
