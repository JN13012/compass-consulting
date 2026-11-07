import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../App'

const passage = {
  ref: 'MICA-ART-3-1-33',
  kind: 'point',
  heading: 'Article 3 — Définitions, paragraphe 1, point 33',
  text: '33) «jeton de monnaie électronique»: un type de crypto-actif…',
  source_code: 'MICA',
  source_title: 'Règlement (UE) 2023/1114',
  domain: 'crypto',
  url: 'https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:02023R1114-20240109',
  version: '02023R1114-20240109',
  consolidated: true,
  consulted_on: '2026-11-07',
  original_url: 'https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32023R1114',
  score: 0.9,
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function mockApi(ask: unknown, askStatus = 200) {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    const url = input instanceof Request ? input.url : String(input)
    if (url.endsWith('/kb/sources')) return json([{ code: 'MICA', title: 'MiCA', domain: 'crypto', version: 'x', consolidated: true, consulted_on: '2026-11-07', url: '', original_url: '', passages: 1155 }])
    if (url.endsWith('/kb/ask')) return json(ask, askStatus)
    return json({}, 404)
  })
}

function renderKb() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/connaissances']}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

async function askQuestion() {
  fireEvent.change(screen.getByLabelText('Votre question'), { target: { value: "Qu'est-ce qu'un EMT ?" } })
  fireEvent.click(screen.getByRole('button', { name: 'Poser la question' }))
}

afterEach(() => vi.restoreAllMocks())

describe('Base de connaissances', () => {
  it('shows the answer with the exact cited passage and its official link', async () => {
    mockApi({ status: 'answered', answer: 'Un EMT est un crypto-actif…', refusal_reason: null, refusal_message: null, citations: [passage], retrieved: [passage], mode_used: 'fulltext', model: 'fake', duration_s: 1.2 })
    renderKb()
    expect(await screen.findByText(/1 textes officiels/)).toHaveTextContent(/1\s?155 passages/)
    await askQuestion()
    expect(await screen.findByText('Un EMT est un crypto-actif…')).toBeInTheDocument()
    const cited = screen.getByRole('article', { name: 'Passage MICA-ART-3-1-33' })
    expect(cited).toHaveTextContent('«jeton de monnaie électronique»')
    expect(cited).toHaveTextContent('Version consolidée au 09/01/2024')
    expect(screen.getByRole('link', { name: 'Voir sur EUR-Lex' })).toHaveAttribute('href', passage.url)
  })

  it('shows a refusal instead of an answer', async () => {
    mockApi({ status: 'refused', answer: '', refusal_reason: 'aucun_passage_pertinent', refusal_message: 'Les textes du corpus ne contiennent pas de passage suffisamment pertinent.', citations: [], retrieved: [], mode_used: 'fulltext', model: null, duration_s: 0.1 })
    renderKb()
    await askQuestion()
    expect(await screen.findByRole('status')).toHaveTextContent('Pas de réponse.')
  })

  it('suggests search-only mode when the AI provider is down', async () => {
    mockApi({ detail: 'down' }, 503)
    renderKb()
    await askQuestion()
    expect(await screen.findByRole('alert')).toHaveTextContent('Rechercher les passages')
  })
})
