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
  it('shows the legal disclaimer on every page', () => {
    renderAt('/veille')
    expect(screen.getByRole('note')).toHaveTextContent("Ceci n'est pas un conseil juridique")
  })

  it('displays API health from /health', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ status: 'ok', database: 'ok', version: '0.1.0' }), {
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    renderAt('/')
    expect(await screen.findByText('Base de données : connectée')).toBeInTheDocument()
  })

  it('renders the six mission tabs', () => {
    renderAt('/missions/demo/benchmark')
    const tabs = screen.getByRole('navigation', { name: 'Étapes de la mission' })
    expect(tabs.querySelectorAll('a')).toHaveLength(6)
  })
})
