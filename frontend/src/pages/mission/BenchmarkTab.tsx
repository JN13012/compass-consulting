import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { api } from '../../api/client'
import { Badge, type Tone } from '../../components/Badge'

interface Cell {
  value: unknown
  display: string
  source: string
  url: string
  method: string
}
interface BenchmarkData {
  title: string
  description: string
  collected_at: string
  columns: { key: string; label: string }[]
  rows: { key: string; cells: Record<string, Cell> }[]
  sources: { name: string; url: string }[]
}

const MICA: Record<string, Tone> = { inscrit: 'green', absent: 'red', non_rapproche: 'neutral' }

export function BenchmarkTab({ missionId }: { missionId: string }) {
  const qc = useQueryClient()
  const templates = useQuery({
    queryKey: ['bench-templates'],
    queryFn: async () => (await api.GET('/benchmarks/templates')).data ?? [],
  })
  const history = useQuery({
    queryKey: ['benchmarks', missionId],
    queryFn: async () => (await api.GET('/benchmarks', { params: { query: { mission_id: missionId } } })).data ?? [],
  })
  const [template, setTemplate] = useState('stablecoins_eur')
  const run = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST('/benchmarks', { body: { template, mission_id: missionId } })
      if (error || !data) throw new Error('Source de données injoignable.')
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['benchmarks', missionId] }),
  })
  const [selected, setSelected] = useState<string | null>(null)
  const runs = history.data ?? []
  const current = runs.find((b) => b.id === selected) ?? runs[0]
  const data = current?.data as unknown as BenchmarkData | undefined
  const [focus, setFocus] = useState<Cell | null>(null)

  const supplies = data?.rows.map((r) => Number(r.cells.offre?.value ?? 0)) ?? []
  const max = Math.max(1, ...supplies)

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-sm text-ink/70">
          Données publiques collectées en direct (on-chain et registre officiel). Chaque cellule garde sa source.
        </p>
        <select
          aria-label="Gabarit de benchmark"
          value={template}
          onChange={(e) => setTemplate(e.target.value)}
          className="ml-auto rounded border border-ink/30 bg-white px-2 py-2 text-sm"
        >
          {templates.data?.map((t) => (
            <option key={t.key} value={t.key}>
              {t.title}
            </option>
          ))}
        </select>
        <button onClick={() => run.mutate()} disabled={run.isPending} className="rounded bg-ink px-4 py-2 text-sm text-white disabled:opacity-40">
          {run.isPending ? 'Collecte…' : 'Lancer la collecte'}
        </button>
      </div>
      {run.isError && (
        <p role="alert" className="rounded border border-red-200 bg-red-50 p-4 text-sm">
          {run.error.message}
        </p>
      )}

      {data && (
        <div className="rounded border border-line bg-white">
          <header className="flex flex-wrap items-baseline gap-3 border-b border-line px-4 py-3">
            <h2 className="font-medium">{data.title}</h2>
            <span className="text-xs text-ink/60">{data.description}</span>
            {runs.length > 1 && (
              <select
                aria-label="Version"
                value={current?.id}
                onChange={(e) => setSelected(e.target.value)}
                className="ml-auto rounded border border-line px-2 py-1 text-xs"
              >
                {runs.map((b) => (
                  <option key={b.id} value={b.id}>
                    {new Date(b.created_at).toLocaleString('fr-FR')} — {b.template}
                  </option>
                ))}
              </select>
            )}
          </header>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-paper text-xs uppercase tracking-wide text-ink/60">
                <tr>
                  {data.columns.map((c) => (
                    <th key={c.key} className="px-3 py-2 font-semibold">
                      {c.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {data.rows.map((r) => (
                  <tr key={r.key}>
                    {data.columns.map((c) => {
                      const cell = r.cells[c.key]
                      if (!cell) return <td key={c.key} />
                      return (
                        <td key={c.key} className={`px-3 py-2 align-top ${c.key === 'blockchains' || c.key === 'emetteur' ? 'min-w-40' : 'whitespace-nowrap'}`}>
                          <button
                            type="button"
                            onClick={() => setFocus(cell)}
                            title={`Source : ${cell.source} — ${cell.method}`}
                            className="text-left hover:underline"
                          >
                            {c.key === 'statut_mica' ? (
                              <Badge tone={MICA[String(cell.value)] ?? 'neutral'}>{cell.display}</Badge>
                            ) : c.key === 'offre' ? (
                              <span className="flex items-center gap-2">
                                <span className="h-2 rounded-sm bg-ink" style={{ width: `${Math.max(2, (Number(cell.value) / max) * 80)}px` }} />
                                {cell.display}
                              </span>
                            ) : (
                              cell.display
                            )}
                          </button>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <footer className="space-y-1 border-t border-line px-4 py-3 text-xs text-ink/70">
            <p>Collecté le {new Date(data.collected_at).toLocaleString('fr-FR')}. Cliquez une cellule pour voir sa source.</p>
            <p>
              Sources :{' '}
              {data.sources.map((s, i) => (
                <span key={s.url}>
                  {i > 0 && ' · '}
                  <a className="underline" href={s.url} target="_blank" rel="noreferrer">
                    {s.name}
                  </a>
                </span>
              ))}
            </p>
            <p>« Émetteur non rapproché » signifie qu'aucun rapprochement token → émetteur n'est configuré, pas que le token est non autorisé.</p>
          </footer>
        </div>
      )}

      {focus && (
        <aside role="dialog" aria-label="Source de la cellule" className="rounded border border-ink/30 bg-white p-4 text-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-medium">{focus.display}</p>
              <p className="mt-1 text-ink/70">Source : {focus.source}</p>
              <p className="text-ink/70">Méthode : {focus.method}</p>
              {focus.url && (
                <a className="underline" href={focus.url} target="_blank" rel="noreferrer">
                  Ouvrir la source
                </a>
              )}
            </div>
            <button onClick={() => setFocus(null)} className="text-xs underline">
              Fermer
            </button>
          </div>
        </aside>
      )}
    </section>
  )
}
