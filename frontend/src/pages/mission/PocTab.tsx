import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { api } from '../../api/client'
import type { components } from '../../api/schema'
import { Badge } from '../../components/Badge'
import type { MissionOut } from '../../lib/missions'
import {
  CAUSE_LABELS,
  LOWER_IS_BETTER,
  METRIC_LABELS,
  pct,
  type Criterion,
  type Evaluation,
  type Framing,
  type Metric,
} from '../../lib/poc'

type PocOut = components['schemas']['PocOut']

function errorText(error: unknown, status: number): string {
  const detail = (error as { detail?: unknown } | undefined)?.detail
  return typeof detail === 'string' ? detail : `Erreur ${status}`
}

function usePoc(id: string) {
  return useQuery({
    queryKey: ['poc', id],
    queryFn: async () => {
      const { data, error } = await api.GET('/missions/{mission_id}/poc', { params: { path: { mission_id: id } } })
      if (error || !data) throw new Error('poc')
      return data
    },
    refetchInterval: (q) => ((q.state.data?.evaluation as Evaluation | null)?.status === 'en_cours' ? 2000 : false),
  })
}

function usePocAction<T>(id: string, run: (arg: T) => Promise<{ data?: PocOut; error?: unknown; response: Response }>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (arg: T) => {
      const { data, error, response } = await run(arg)
      if (error || !data) throw new Error(errorText(error, response.status))
      return data
    },
    onSuccess: (data) => {
      qc.setQueryData(['poc', id], data)
      void qc.invalidateQueries({ queryKey: ['mission', id] })
    },
  })
}

export function PocTab({ mission }: { mission: MissionOut }) {
  const id = mission.id
  const path = { params: { path: { mission_id: id } } }
  const poc = usePoc(id)
  const frame = usePocAction(id, () => api.POST('/missions/{mission_id}/poc/framing', path))
  const demo = usePocAction(id, () => api.POST('/missions/{mission_id}/poc/cases/demo', path))
  const upload = usePocAction(id, (jsonl: string) =>
    api.PUT('/missions/{mission_id}/poc/cases', { ...path, body: { jsonl, source: 'fichier importé' } }),
  )
  const criteria = usePocAction(id, (body: Criterion[]) => api.PUT('/missions/{mission_id}/poc/criteria', { ...path, body }))
  const evaluate = usePocAction(id, (endpoint: string) =>
    api.POST('/missions/{mission_id}/poc/evaluate', { ...path, body: { endpoint } }),
  )

  if (poc.isPending) return <p className="text-sm">Chargement…</p>
  if (!poc.data) return <p className="text-sm">POC indisponible.</p>
  const framing = poc.data.framing as Framing | null
  const evaluation = poc.data.evaluation as Evaluation | null
  const cases = poc.data.cases
  const failed = [frame, demo, upload, criteria, evaluate].find((m) => m.isError)

  return (
    <section className="space-y-5">
      <p className="max-w-3xl text-sm text-ink/70">
        Compass ne code pas le POC : il le <strong>cadre</strong>, remet un dossier à celui qui le construit, puis l'
        <strong>évalue</strong> sur un jeu de test qu'il garde pour lui.
      </p>
      {failed && (
        <p role="alert" className="rounded border border-red-200 bg-red-50 p-4 text-sm">
          {failed.error?.message}
        </p>
      )}

      <Block n={1} title="Cadrage" done={!!framing}>
        <div className="flex flex-wrap items-center gap-3">
          <p className="text-sm text-ink/70">
            L'IA choisit la solution la plus vérifiable et propose des critères chiffrés ; les contraintes de la mission sont ajoutées par le code.
          </p>
          <button
            onClick={() => frame.mutate(undefined)}
            disabled={frame.isPending || !mission.solutions}
            className="ml-auto rounded bg-ink px-4 py-2 text-sm text-white disabled:opacity-40"
          >
            {frame.isPending ? 'Cadrage en cours…' : framing ? 'Recadrer' : 'Cadrer le POC'}
          </button>
        </div>
        {!mission.solutions && <p className="mt-2 text-sm text-ink/70">Lancez d'abord les solutions : le POC en découle.</p>}
        {framing && <FramingView framing={framing} onSave={(c) => criteria.mutate(c)} saving={criteria.isPending} />}
      </Block>

      <Block n={2} title="Jeu de cas et dossier" done={!!cases}>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          {cases ? (
            <p>
              <strong>{cases.total} cas</strong> ({cases.a_refuser} à refuser) · {cases.source} ·{' '}
              <span className="text-ink/70">
                {cases.dev} transmis au développeur, <strong>{cases.test} gardés par Compass</strong> pour le test.
              </span>
            </p>
          ) : (
            <p className="text-ink/70">Un cas = une entrée et la sortie attendue (ou un refus attendu).</p>
          )}
          <div className="ml-auto flex gap-2">
            <button onClick={() => demo.mutate(undefined)} disabled={demo.isPending} className="rounded border border-ink/30 px-3 py-1.5">
              Jeu de démo (commandes)
            </button>
            <label className="cursor-pointer rounded border border-ink/30 px-3 py-1.5">
              Importer un .jsonl
              <input
                type="file"
                accept=".jsonl,.json,.txt"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) void file.text().then((t) => upload.mutate(t))
                }}
              />
            </label>
            <a
              href={framing ? `/api/missions/${id}/poc/dossier.zip` : undefined}
              aria-disabled={!framing}
              className={`rounded px-3 py-1.5 text-white ${framing ? 'bg-ink' : 'pointer-events-none bg-ink/40'}`}
            >
              Télécharger le dossier POC
            </a>
          </div>
        </div>
        <p className="mt-2 text-xs text-ink/60">
          Le zip contient CLAUDE.md, SPEC.md, ARCHITECTURE.md, INTERFACE.md et le jeu de développement : de quoi construire le POC avec Claude Code.
        </p>
      </Block>

      <Block n={3} title="Évaluation" done={evaluation?.status === 'terminee'}>
        <EvaluateForm
          defaultEndpoint={evaluation?.endpoint ?? poc.data.default_endpoint ?? ''}
          disabled={!framing || !cases || evaluation?.status === 'en_cours' || evaluate.isPending}
          onRun={(e) => evaluate.mutate(e)}
        />
        {evaluation && <EvaluationView evaluation={evaluation} />}
      </Block>
    </section>
  )
}

function Block({ n, title, done, children }: { n: number; title: string; done: boolean; children: React.ReactNode }) {
  return (
    <div className="rounded border border-line bg-white p-5">
      <h2 className="mb-3 flex items-center gap-2 font-medium">
        <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${done ? 'bg-emerald-100 text-emerald-800' : 'bg-ink/5'}`}>
          {done ? '✓' : n}
        </span>
        {title}
      </h2>
      {children}
    </div>
  )
}

function List({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wider text-ink/60">{title}</p>
      <ul className="mt-1 list-disc space-y-0.5 pl-5 text-sm">
        {items.map((i) => (
          <li key={i}>{i}</li>
        ))}
      </ul>
    </div>
  )
}

function FramingView({ framing, onSave, saving }: { framing: Framing; onSave: (c: Criterion[]) => void; saving: boolean }) {
  const [draft, setDraft] = useState<Criterion[]>(framing.criteres)
  const changed = JSON.stringify(draft) !== JSON.stringify(framing.criteres)
  return (
    <div className="mt-4 space-y-4">
      <div>
        <p className="font-serif text-xl font-semibold">{framing.nom}</p>
        <p className="text-sm text-ink/70">Solution retenue : {framing.solution_retenue}</p>
        <p className="mt-2 text-sm leading-relaxed">{framing.objectif}</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <List title="Périmètre" items={framing.perimetre} />
        <List title="Hors périmètre" items={framing.hors_perimetre} />
        <List title="User stories" items={framing.user_stories} />
        <List title="Risques" items={framing.risques} />
      </div>
      <List title="Contraintes de la mission (ajoutées par le code)" items={framing.contraintes} />
      <div>
        <p className="text-xs font-medium uppercase tracking-wider text-ink/60">Critères d'acceptation (modifiables)</p>
        <table className="mt-2 w-full text-sm">
          <tbody>
            {draft.map((c, i) => (
              <tr key={c.metrique} className="border-t border-line">
                <td className="py-2 pr-3">{METRIC_LABELS[c.metrique]}</td>
                <td className="w-32 py-2 pr-3">
                  {LOWER_IS_BETTER.includes(c.metrique) ? '≤ ' : '≥ '}
                  <input
                    aria-label={`Seuil ${METRIC_LABELS[c.metrique]}`}
                    type="number"
                    step={c.metrique === 'latence_p95_s' ? 1 : 0.01}
                    min={0}
                    value={c.seuil}
                    onChange={(e) => setDraft(draft.map((d, j) => (j === i ? { ...d, seuil: Number(e.target.value) } : d)))}
                    className="w-20 rounded border border-line px-1.5 py-0.5"
                  />
                </td>
                <td className="py-2 text-ink/70">{c.justification}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {changed && (
          <button onClick={() => onSave(draft)} disabled={saving} className="mt-2 rounded bg-ink px-3 py-1.5 text-sm text-white">
            Enregistrer les seuils
          </button>
        )}
      </div>
    </div>
  )
}

function EvaluateForm({ defaultEndpoint, disabled, onRun }: { defaultEndpoint: string; disabled: boolean; onRun: (e: string) => void }) {
  const [endpoint, setEndpoint] = useState(defaultEndpoint)
  return (
    <form
      className="flex flex-wrap items-center gap-2 text-sm"
      onSubmit={(e) => {
        e.preventDefault()
        onRun(endpoint)
      }}
    >
      <label htmlFor="poc-endpoint" className="text-ink/70">
        Adresse du POC (POST /run)
      </label>
      <input
        id="poc-endpoint"
        value={endpoint}
        onChange={(e) => setEndpoint(e.target.value)}
        className="min-w-64 flex-1 rounded border border-line px-2 py-1 font-mono text-xs"
      />
      <button type="submit" disabled={disabled} className="rounded bg-ink px-4 py-2 text-white disabled:opacity-40">
        Lancer l'évaluation
      </button>
    </form>
  )
}

function value(metric: Metric, v: number) {
  return metric === 'latence_p95_s' ? `${v.toFixed(1)} s` : pct(v)
}

function EvaluationView({ evaluation: e }: { evaluation: Evaluation }) {
  if (e.status === 'en_cours')
    return (
      <p role="status" className="mt-4 text-sm">
        Évaluation en cours : {e.done}/{e.total} cas…
        <span className="mt-2 block h-1.5 w-full rounded bg-line">
          <span className="block h-1.5 rounded bg-accent" style={{ width: `${(100 * e.done) / Math.max(e.total, 1)}%` }} />
        </span>
      </p>
    )
  if (e.status === 'erreur')
    return (
      <p role="alert" className="mt-4 rounded border border-red-200 bg-red-50 p-3 text-sm">
        Évaluation interrompue : {e.erreur}
      </p>
    )
  const m = e.metrics
  return (
    <div className="mt-5 space-y-5">
      <div className={`rounded p-4 ${e.passage_echelle ? 'bg-emerald-50' : 'bg-amber-50'}`}>
        <p className="font-medium">
          Passage à l'échelle : {e.passage_echelle ? 'oui, tous les critères sont atteints' : 'pas encore, critères non atteints'}
        </p>
        <p className="text-xs text-ink/70">
          {e.total} cas de test jamais transmis au développeur · {e.endpoint} · {m?.erreurs_techniques ?? 0} erreur(s) technique(s) · latence
          moyenne {m?.latence_moyenne_s ?? 0} s
        </p>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wider text-ink/60">
            <th className="py-1">Critère</th>
            <th>Seuil</th>
            <th>Mesuré</th>
            <th>IC 95 %</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {e.verdict?.map((c) => (
            <tr key={c.metrique} className="border-t border-line">
              <td className="py-2">{c.libelle}</td>
              <td>
                {LOWER_IS_BETTER.includes(c.metrique) ? '≤ ' : '≥ '}
                {value(c.metrique, c.seuil)}
              </td>
              <td className="font-semibold">{value(c.metrique, c.valeur)}</td>
              <td className="text-ink/70">{c.ic95 ? `${pct(c.ic95[0])} - ${pct(c.ic95[1])}` : '-'}</td>
              <td>
                {c.atteint ? (
                  <Badge tone={c.robuste ? 'green' : 'amber'}>{c.robuste ? 'atteint' : 'atteint, IC sous le seuil'}</Badge>
                ) : (
                  <Badge tone="red">non atteint</Badge>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!!e.groupes?.length && (
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-ink/60">Échecs par cause</p>
          <ul className="space-y-2 text-sm">
            {e.groupes.map((g) => (
              <li key={g.cause} className="rounded border border-line p-3">
                <p className="font-medium">
                  {g.cause.startsWith('champ:') ? `Champ « ${g.cause.slice(6)} » faux` : (CAUSE_LABELS[g.cause] ?? g.cause)} · {g.nombre} cas
                </p>
                {g.exemples.map((x) => (
                  <p key={x.id} className="mt-1 font-mono text-xs text-ink/70">
                    {x.id} · attendu {x.attendu} · obtenu {x.obtenu}
                  </p>
                ))}
              </li>
            ))}
          </ul>
        </div>
      )}
      {!!e.corrections?.length && (
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-ink/60">Corrections à renvoyer au développeur du POC</p>
          <pre className="whitespace-pre-wrap rounded bg-paper p-3 text-xs">{e.corrections.map((c) => `- ${c}`).join('\n')}</pre>
        </div>
      )}
    </div>
  )
}
