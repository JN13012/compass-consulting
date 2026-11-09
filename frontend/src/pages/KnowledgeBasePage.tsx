import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { api } from '../api/client'
import type { components } from '../api/schema'
import { Citation } from '../components/Citation'
import { PageHeader } from '../components/PageHeader'
import { DOMAIN_LABELS } from '../lib/labels'

type AskResponse = components['schemas']['AskResponse']
type SearchResponse = components['schemas']['SearchResponse']

const MAX = 1000
const EXAMPLES = [
  "Qu'est-ce qu'un jeton de monnaie électronique selon MiCA ?",
  'Dans quel délai faut-il notifier un incident significatif selon NIS 2 ?',
  "Quelles pratiques en matière d'IA sont interdites par l'AI Act ?",
  'Quelles informations un prestataire doit-il transmettre avec un transfert de crypto-actifs ?',
]

type Result = { kind: 'ask'; data: AskResponse } | { kind: 'search'; data: SearchResponse }

export function KnowledgeBasePage() {
  const [question, setQuestion] = useState('')
  const [domains, setDomains] = useState<string[]>([])
  const [result, setResult] = useState<Result | null>(null)

  const sources = useQuery({
    queryKey: ['kb-sources'],
    queryFn: async () => {
      const { data, error } = await api.GET('/kb/sources')
      if (error || !data) throw new Error('sources')
      return data
    },
  })
  const availableDomains = [...new Set((sources.data ?? []).map((s) => s.domain))]
  const passageCount = (sources.data ?? []).reduce((n, s) => n + s.passages, 0)

  const body = () => ({ question: question.trim(), domains: domains.length ? domains : null, mode: 'vector' as const })

  const ask = useMutation({
    mutationFn: async () => {
      const { data, error, response } = await api.POST('/kb/ask', { body: body() })
      if (response.status === 503) throw new Error('provider')
      if (error || !data) throw new Error('ask')
      return data
    },
    onSuccess: (data) => setResult({ kind: 'ask', data }),
  })
  const search = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST('/kb/search', { body: body() })
      if (error || !data) throw new Error('search')
      return data
    },
    onSuccess: (data) => setResult({ kind: 'search', data }),
  })
  const busy = ask.isPending || search.isPending
  const canSubmit = question.trim().length >= 3 && !busy

  const toggle = (d: string) => setDomains((cur) => (cur.includes(d) ? cur.filter((x) => x !== d) : [...cur, d]))

  return (
    <>
      <PageHeader
        eyebrow="Base de connaissances"
        title="Textes officiels"
        subtitle="La réponse cite le passage exact du texte officiel, avec sa source. Si les textes du corpus ne permettent pas de répondre, l'outil le dit et ne répond pas."
      />

      {sources.data && (
        <p className="mb-4 text-sm text-ink/70">
          {sources.data.length} textes officiels · {passageCount.toLocaleString('fr-FR')} passages · dernière version
          consolidée disponible
        </p>
      )}

      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault()
          if (canSubmit) ask.mutate()
        }}
      >
        <label htmlFor="question" className="block font-medium">
          Votre question
        </label>
        <textarea
          id="question"
          value={question}
          maxLength={MAX}
          rows={4}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Par exemple : Qu'est-ce qu'un jeton de monnaie électronique selon MiCA ?"
          className="w-full rounded border border-ink/40 bg-white p-3 text-sm focus:border-ink focus:outline-none"
        />
        {availableDomains.length > 0 && (
          <fieldset className="flex flex-wrap gap-2" aria-label="Filtrer par domaine">
            {availableDomains.map((d) => (
              <button
                type="button"
                key={d}
                aria-pressed={domains.includes(d)}
                onClick={() => toggle(d)}
                className={`rounded-full border px-3 py-1 text-xs ${domains.includes(d) ? 'border-ink bg-ink text-white' : 'border-line bg-white hover:border-ink/40'}`}
              >
                {DOMAIN_LABELS[d] ?? d}
              </button>
            ))}
          </fieldset>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs text-ink/60">
            {question.length} / {MAX} caractères
          </span>
          <button
            type="button"
            disabled={!canSubmit}
            onClick={() => search.mutate()}
            className="ml-auto rounded border border-ink px-4 py-2 text-sm disabled:opacity-40"
          >
            Rechercher les passages
          </button>
          <button type="submit" disabled={!canSubmit} className="rounded bg-ink px-4 py-2 text-sm text-white disabled:opacity-40">
            {ask.isPending ? 'Analyse…' : 'Poser la question'}
          </button>
        </div>
      </form>

      {!result && !busy && (
        <section className="mt-8" aria-label="Exemples de questions">
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink/60">Exemples de questions</h2>
          <ul className="divide-y divide-line border-y border-line">
            {EXAMPLES.map((ex) => (
              <li key={ex}>
                <button type="button" onClick={() => setQuestion(ex)} className="w-full py-2 text-left text-sm underline-offset-2 hover:underline">
                  {ex}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {ask.isError && (
        <p role="alert" className="mt-6 rounded border border-red-200 bg-red-50 p-4 text-sm">
          {ask.error.message === 'provider'
            ? 'Le fournisseur IA est indisponible. Utilisez « Rechercher les passages » pour consulter les textes sans génération.'
            : 'Une erreur est survenue.'}
        </p>
      )}

      {result?.kind === 'ask' && <AskResult data={result.data} />}
      {result?.kind === 'search' && (
        <section className="mt-8 space-y-3" aria-label="Passages trouvés">
          <h2 className="font-medium">Passages les plus pertinents</h2>
          {result.data.passages.length === 0 && <p className="text-sm">Aucun passage trouvé.</p>}
          {result.data.passages.map((p) => (
            <Citation key={p.ref} passage={p} />
          ))}
        </section>
      )}
    </>
  )
}

function AskResult({ data }: { data: AskResponse }) {
  if (data.status === 'refused') {
    return (
      <section className="mt-8 space-y-3" aria-label="Réponse">
        <div role="status" className="rounded border border-line bg-warn-bg p-4 text-sm">
          <strong>Pas de réponse.</strong> {data.refusal_message}
        </div>
        {data.retrieved.length > 0 && (
          <details>
            <summary className="cursor-pointer text-sm">Voir les passages les plus proches ({data.retrieved.length})</summary>
            <div className="mt-3 space-y-3">
              {data.retrieved.slice(0, 5).map((p) => (
                <Citation key={p.ref} passage={p} />
              ))}
            </div>
          </details>
        )}
      </section>
    )
  }
  return (
    <section className="mt-8 space-y-4" aria-label="Réponse">
      <div className="rounded border border-line bg-white p-4">
        <h2 className="mb-2 font-medium">Réponse</h2>
        <p className="text-sm leading-relaxed">{data.answer}</p>
        <p className="mt-3 text-xs text-ink/60">
          {data.model} · recherche {data.mode_used} · {data.duration_s.toFixed(1)} s
        </p>
      </div>
      <h3 className="font-medium">Passages cités ({data.citations.length})</h3>
      {data.citations.map((p) => (
        <Citation key={p.ref} passage={p} />
      ))}
    </section>
  )
}
