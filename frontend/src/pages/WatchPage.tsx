import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { api } from '../api/client'
import type { components } from '../api/schema'
import { Badge, type Tone } from '../components/Badge'
import { PageHeader } from '../components/PageHeader'
import { frDate } from '../lib/labels'

type Change = components['schemas']['Change']

const STATUS: Record<string, { label: string; tone: Tone }> = {
  a_jour: { label: 'À jour', tone: 'green' },
  nouvelle_version: { label: 'Nouvelle version publiée', tone: 'amber' },
  non_consolide: { label: 'Pas de version consolidée', tone: 'neutral' },
  erreur: { label: 'Source injoignable', tone: 'red' },
}
const KIND: Record<string, { label: string; tone: Tone }> = {
  modifie: { label: 'Modifié', tone: 'amber' },
  ajoute: { label: 'Ajouté', tone: 'green' },
  supprime: { label: 'Supprimé', tone: 'red' },
}

/** "02014L0065-20260606" -> "06/06/2026"; an original act -> "texte d'origine". */
function versionDate(celex: string | null | undefined): string {
  const m = celex ? /-(\d{4})(\d{2})(\d{2})/.exec(celex) : null
  return m ? `${m[3]}/${m[2]}/${m[1]}` : 'texte d’origine'
}

export function WatchPage() {
  const qc = useQueryClient()
  const status = useQuery({ queryKey: ['watch'], queryFn: async () => (await api.GET('/watch/status')).data })
  const check = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST('/watch/check')
      if (error || !data) throw new Error('Vérification impossible : service de l’Office des publications injoignable.')
      return data
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watch'] }),
  })
  const [selected, setSelected] = useState<string | null>(null)
  const last = status.data?.last_check
  const history = status.data?.with_history ?? []
  const open = selected ?? history[0] ?? null

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="Veille"
        title="Veille réglementaire"
        subtitle="Nouvelles versions des textes officiels, articles modifiés et missions concernées. Les versions viennent de l'Office des publications de l'UE ; les comparaisons sont calculées, sans IA."
      />

      <section>
        <div className="mb-3 flex flex-wrap items-end gap-3">
          <div>
            <h2 className="text-xl font-semibold">Versions des textes</h2>
            <p className="text-xs text-ink/60">
              {last ? `Dernière vérification : ${new Date(last.checked_at).toLocaleString('fr-FR')}` : 'Jamais vérifié'} · Vérification
              automatique hebdomadaire prévue (désactivée en démonstration)
            </p>
          </div>
          <button
            onClick={() => check.mutate()}
            disabled={check.isPending}
            className="ml-auto rounded-md bg-ink px-4 py-2 text-sm text-white disabled:opacity-40"
          >
            {check.isPending ? 'Vérification sur EUR-Lex…' : 'Vérifier les mises à jour'}
          </button>
        </div>
        {check.isError && (
          <p role="alert" className="mb-3 rounded border border-red-200 bg-red-50 p-3 text-sm">
            {check.error.message}
          </p>
        )}
        <div className="overflow-x-auto rounded-md border border-line bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-paper text-[11px] uppercase tracking-wide text-ink/60">
              <tr>
                <th className="px-4 py-2 font-semibold">Texte</th>
                <th className="px-4 py-2 font-semibold">En base</th>
                <th className="px-4 py-2 font-semibold">Dernière publiée</th>
                <th className="px-4 py-2 font-semibold">Statut</th>
                <th className="px-4 py-2 font-semibold">Cité dans</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {(last?.texts ?? []).map((t) => (
                <tr key={t.code}>
                  <td className="px-4 py-2.5">
                    <span className="font-medium">{t.code}</span>
                    <span className="block max-w-xs truncate text-xs text-ink/60" title={t.title}>
                      {t.title}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-2.5 tabular-nums">{versionDate(t.current)}</td>
                  <td className="whitespace-nowrap px-4 py-2.5 tabular-nums">{t.latest ? versionDate(t.latest) : '-'}</td>
                  <td className="px-4 py-2.5">
                    <Badge tone={STATUS[t.status]?.tone}>{STATUS[t.status]?.label ?? t.status}</Badge>
                    {t.status === 'nouvelle_version' && t.current === t.current.replace(/-\d{8}$/, '') && (
                      <span className="mt-0.5 block text-[11px] text-ink/50">base : acte d’origine</span>
                    )}
                  </td>
                  <td className="px-4 py-2.5 text-xs text-ink/70">{(status.data?.cited_by[t.code] ?? []).join(', ') || '-'}</td>
                  <td className="px-4 py-2.5 text-right">
                    {history.includes(t.code) && (
                      <button onClick={() => setSelected(t.code)} className="text-xs font-medium text-accent underline">
                        Voir les changements
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {!last && (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-sm text-ink/60">
                    Lancez une vérification pour comparer les versions en base aux dernières publications.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {open && <DiffSection code={open} />}

      <Deadlines />
    </div>
  )
}

function DiffSection({ code }: { code: string }) {
  const diff = useQuery({
    queryKey: ['watch-diff', code],
    queryFn: async () => (await api.GET('/watch/diff/{code}', { params: { path: { code } } })).data,
  })
  const [kind, setKind] = useState<string>('modifie')
  const [limit, setLimit] = useState(8)
  if (!diff.data) return <p className="text-sm">Chargement des changements…</p>
  const { diff: d, impacts } = diff.data
  const counts = Object.fromEntries(Object.keys(KIND).map((k) => [k, d.changes.filter((c) => c.kind === k).length]))
  const shown = d.changes.filter((c) => c.kind === kind)

  return (
    <section>
      <h2 className="text-xl font-semibold">Ce qui a changé - {d.code}</h2>
      <p className="mb-4 text-sm text-ink/70">
        {d.title} · version du {versionDate(d.old_version)} → version du {versionDate(d.new_version)} · {d.changes.length} passages
        changés, {d.unchanged} inchangés
      </p>

      <div className="mb-5 rounded-md border border-line bg-white p-4">
        <h3 className="mb-2 text-sm font-semibold">Missions qui citent ce texte</h3>
        {impacts.length === 0 && <p className="text-sm text-ink/60">Aucune analyse de mission ne cite ce texte.</p>}
        <ul className="space-y-2 text-sm">
          {impacts.map((i) => (
            <li key={i.mission_id} className="flex flex-wrap items-center gap-2">
              <Link to={`/missions/${i.mission_id}/reglementation`} className="font-medium underline">
                {i.client}
              </Link>
              {i.changed.length > 0 ? (
                <Badge tone="red">{i.changed.length} passage(s) cité(s) modifié(s) : analyse à relancer</Badge>
              ) : (
                <Badge tone="green">Passages cités inchangés : analyse à jour</Badge>
              )}
              <span className="text-xs text-ink/50">{i.cited.join(', ')}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="mb-3 flex gap-1">
        {Object.entries(KIND).map(([k, v]) => (
          <button
            key={k}
            onClick={() => {
              setKind(k)
              setLimit(8)
            }}
            className={`rounded-md px-3 py-1.5 text-sm ${kind === k ? 'bg-ink text-white' : 'border border-line bg-white text-ink/70'}`}
          >
            {v.label} ({counts[k]})
          </button>
        ))}
      </div>
      <div className="space-y-3">
        {shown.slice(0, limit).map((c) => (
          <ChangeCard key={c.ref} change={c} />
        ))}
      </div>
      {shown.length > limit && (
        <button onClick={() => setLimit(limit + 20)} className="mt-3 text-sm underline">
          Afficher plus ({shown.length - limit} restants)
        </button>
      )}
    </section>
  )
}

function ChangeCard({ change }: { change: Change }) {
  return (
    <article className="rounded-md border border-line bg-white p-4">
      <header className="mb-2 flex flex-wrap items-center gap-2">
        <Badge tone={KIND[change.kind]?.tone}>{KIND[change.kind]?.label}</Badge>
        <span className="text-sm font-medium">{change.heading}</span>
        <span className="font-mono text-[11px] text-ink/50">{change.ref}</span>
      </header>
      <p className="whitespace-pre-line font-serif text-[15px] leading-relaxed">
        {change.segments.map((s, i) =>
          s.op === 'insert' ? (
            <ins key={i} className="bg-emerald-100 text-emerald-900 no-underline">
              {s.text}
            </ins>
          ) : s.op === 'delete' ? (
            <del key={i} className="bg-red-50 text-red-800/80">
              {s.text}
            </del>
          ) : (
            <span key={i}>{s.text}</span>
          ),
        )}
      </p>
    </article>
  )
}

function Deadlines() {
  const deadlines = useQuery({ queryKey: ['deadlines'], queryFn: async () => (await api.GET('/watch/deadlines')).data ?? [] })
  const today = new Date().toISOString().slice(0, 10)
  const days = (iso: string) => Math.round((new Date(iso).getTime() - new Date(today).getTime()) / 86_400_000)
  const nextIndex = (deadlines.data ?? []).findIndex((d) => d.date >= today)

  return (
    <section>
      <h2 className="text-xl font-semibold">Calendrier des échéances</h2>
      <p className="mb-4 text-sm text-ink/70">Dates tirées des textes eux-mêmes ; chaque date renvoie au passage qui la fixe.</p>
      <ol className="relative ml-2 border-l border-line">
        {deadlines.data?.map((d, i) => {
          const past = d.date < today
          const n = days(d.date)
          return (
            <li key={`${d.date}-${d.ref}-${d.title}`} className={`mb-4 ml-5 ${past ? 'opacity-55' : ''}`}>
              <span
                className={`absolute -left-[5px] mt-1.5 h-2.5 w-2.5 rounded-full ${i === nextIndex ? 'bg-accent ring-4 ring-accent-soft' : past ? 'bg-ink/30' : 'bg-ink'}`}
              />
              <div className="flex flex-wrap items-baseline gap-2">
                <span className="w-24 shrink-0 font-medium tabular-nums">{frDate(d.date)}</span>
                <span className="font-medium">{d.title}</span>
                {!past && <Badge tone={n < 365 ? 'amber' : 'neutral'}>dans {n} jours</Badge>}
                {i === nextIndex && <Badge tone="blue">Prochaine échéance</Badge>}
              </div>
              <p className="pl-26 text-sm text-ink/70">
                {d.detail} <span className="font-mono text-[11px] text-ink/45">{d.ref}</span>
              </p>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
