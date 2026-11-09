import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { NavLink, Navigate, useNavigate, useParams } from 'react-router-dom'

import { api } from '../api/client'
import { Badge } from '../components/Badge'
import { MissionForm } from '../components/MissionForm'
import { FOCUS_LABELS } from '../lib/labels'
import { useAnalyze, useMission, type MissionOut, type Step } from '../lib/missions'
import { BenchmarkTab } from './mission/BenchmarkTab'
import { DeliverablesTab } from './mission/DeliverablesTab'
import { InterviewTab } from './mission/InterviewTab'
import { PocTab } from './mission/PocTab'
import { DiagnosticTab, RegulationTab, SolutionsTab } from './mission/tabs'

export const MISSION_TABS = [
  { slug: 'entretiens', label: 'Entretiens' },
  { slug: 'diagnostic', label: 'Diagnostic' },
  { slug: 'solutions', label: 'Solutions' },
  { slug: 'reglementation', label: 'Réglementation' },
  { slug: 'benchmark', label: 'Benchmark' },
  { slug: 'poc', label: 'POC' },
  { slug: 'livrables', label: 'Livrables' },
] as const

function stepDone(m: MissionOut, slug: string): boolean {
  if (slug === 'entretiens') return m.notes.trim().length > 0
  if (slug === 'poc') return m.steps_done.includes('poc')
  const step = STEP_OF[slug]
  return step !== undefined && m.steps_done.includes(step)
}

const STEP_OF: Record<string, Step> = { diagnostic: 'diagnostic', solutions: 'solutions', reglementation: 'regulation' }

export function MissionPage() {
  const { missionId = '', tab } = useParams()
  const current = MISSION_TABS.find((t) => t.slug === tab)
  const mission = useMission(missionId)
  const [editing, setEditing] = useState(false)
  const navigate = useNavigate()
  const qc = useQueryClient()
  const remove = useMutation({
    mutationFn: async () => {
      const { error } = await api.DELETE('/missions/{mission_id}', { params: { path: { mission_id: missionId } } })
      if (error) throw new Error('Suppression impossible.')
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['missions'] })
      navigate('/missions')
    },
  })
  if (!current) return <Navigate to={`/missions/${missionId}/${MISSION_TABS[0].slug}`} replace />
  if (mission.isPending) return <p className="text-sm">Chargement…</p>
  if (mission.isError || !mission.data) return <p className="text-sm">Mission introuvable.</p>
  const m = mission.data

  return (
    <>
      <div className="mb-6 flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="mb-1 text-[11px] font-medium uppercase tracking-[0.18em] text-accent">Mission · {m.sector}</p>
          <h1 className="text-3xl font-semibold">{m.client}</h1>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink/70">{m.context}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {m.focus.map((f) => (
              <Badge key={f} tone="blue">
                {FOCUS_LABELS[f] ?? f}
              </Badge>
            ))}
            {m.confidentiality === 'confidentiel' && <Badge tone="dark">Confidentiel · modèle local uniquement</Badge>}
          </div>
        </div>
        <button onClick={() => setEditing((v) => !v)} className="rounded-md border border-ink/20 bg-white px-3 py-1.5 text-sm hover:border-ink/40">
          Modifier
        </button>
        <button
          onClick={() => {
            if (window.confirm(`Supprimer la mission « ${m.client} » et ses benchmarks ? Cette action est définitive.`)) remove.mutate()
          }}
          disabled={remove.isPending}
          className="rounded-md border border-red-200 bg-white px-3 py-1.5 text-sm text-red-700 hover:border-red-400"
        >
          Supprimer
        </button>
      </div>
      {editing && <MissionForm mission={m} onSaved={() => setEditing(false)} onCancel={() => setEditing(false)} />}
      <nav aria-label="Étapes de la mission" className="mb-8 flex flex-wrap items-center gap-y-2 rounded-md border border-line bg-white px-2 py-2">
        {MISSION_TABS.map((t, i) => {
          const done = stepDone(m, t.slug)
          return (
            <NavLink
              key={t.slug}
              to={`/missions/${missionId}/${t.slug}`}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded px-3 py-1.5 text-sm transition-colors ${isActive ? 'bg-ink text-white' : 'text-ink/70 hover:bg-paper hover:text-ink'}`
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    className={`flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-semibold ${
                      isActive ? 'bg-accent text-white' : done ? 'bg-emerald-100 text-emerald-800' : 'bg-ink/5 text-ink/60'
                    }`}
                  >
                    {done && !isActive ? '✓' : i}
                  </span>
                  {t.label}
                </>
              )}
            </NavLink>
          )
        })}
      </nav>
      {STEP_OF[current.slug] ? (
        <StepPanel mission={m} step={STEP_OF[current.slug]} />
      ) : current.slug === 'benchmark' ? (
        <BenchmarkTab missionId={m.id} />
      ) : current.slug === 'entretiens' ? (
        <InterviewTab mission={m} />
      ) : current.slug === 'livrables' ? (
        <DeliverablesTab mission={m} />
      ) : (
        <PocTab mission={m} />
      )}
    </>
  )
}

const STEP_TEXT: Record<Step, { action: string; empty: string; needs?: Step }> = {
  diagnostic: { action: 'Lancer le diagnostic', empty: 'Analyse des notes d’entretien : processus, irritants, maturité.' },
  solutions: { action: 'Proposer des solutions', empty: 'Solutions classées de la plus simple à la plus complexe, avec feuille de route.', needs: 'diagnostic' },
  regulation: { action: 'Analyser la réglementation', empty: 'Textes applicables et obligations, chacune appuyée par le passage officiel.' },
}

function StepPanel({ mission, step }: { mission: MissionOut; step: Step }) {
  const analyze = useAnalyze(mission.id)
  const text = STEP_TEXT[step]
  const result = mission[step]
  const blocked = text.needs !== undefined && !mission[text.needs]

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-sm text-ink/70">{text.empty}</p>
        <button
          onClick={() => analyze.mutate(step)}
          disabled={analyze.isPending || blocked}
          className="ml-auto rounded bg-ink px-4 py-2 text-sm text-white disabled:opacity-40"
        >
          {analyze.isPending ? 'Analyse en cours…' : result ? 'Relancer' : text.action}
        </button>
      </div>
      {blocked && <p className="text-sm text-ink/70">Lancez d'abord le diagnostic.</p>}
      {analyze.isPending && (
        <p role="status" className="rounded border border-line bg-white p-4 text-sm">
          Le modèle analyse la mission (de 30 secondes à 2 minutes)…
        </p>
      )}
      {analyze.isError && (
        <p role="alert" className="rounded border border-red-200 bg-red-50 p-4 text-sm">
          {analyze.error.message}
        </p>
      )}
      {step === 'diagnostic' && <DiagnosticTab mission={mission} />}
      {step === 'solutions' && <SolutionsTab mission={mission} />}
      {step === 'regulation' && <RegulationTab mission={mission} />}
    </section>
  )
}
