import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { NavLink, Navigate, useNavigate, useParams } from 'react-router-dom'

import { api } from '../api/client'
import { Badge } from '../components/Badge'
import { MissionForm } from '../components/MissionForm'
import { FOCUS_LABELS } from '../lib/labels'
import { PageHeader, Placeholder } from '../components/PageHeader'
import { useAnalyze, useMission, type MissionOut, type Step } from '../lib/missions'
import { BenchmarkTab } from './mission/BenchmarkTab'
import { DeliverablesTab } from './mission/DeliverablesTab'
import { InterviewTab } from './mission/InterviewTab'
import { DiagnosticTab, RegulationTab, SolutionsTab } from './mission/tabs'

export const MISSION_TABS = [
  { slug: 'entretiens', label: '0. Entretiens', phase: '' },
  { slug: 'diagnostic', label: '1. Diagnostic', phase: '' },
  { slug: 'solutions', label: '2. Solutions', phase: '' },
  { slug: 'reglementation', label: '3. Réglementation', phase: '' },
  { slug: 'benchmark', label: '4. Benchmark', phase: '' },
  { slug: 'poc', label: '5. POC & évaluation', phase: 'phase 4' },
  { slug: 'livrables', label: '6. Livrables', phase: '' },
] as const

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
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <PageHeader title={m.client} subtitle={`${m.sector} - ${m.context}`} />
        </div>
        <button onClick={() => setEditing((v) => !v)} className="rounded border border-ink/30 px-3 py-1.5 text-sm">
          Modifier
        </button>
        <button
          onClick={() => {
            if (window.confirm(`Supprimer la mission « ${m.client} » et ses benchmarks ? Cette action est définitive.`)) remove.mutate()
          }}
          disabled={remove.isPending}
          className="rounded border border-red-300 px-3 py-1.5 text-sm text-red-700"
        >
          Supprimer
        </button>
      </div>
      {editing && <MissionForm mission={m} onSaved={() => setEditing(false)} onCancel={() => setEditing(false)} />}
      <div className="-mt-3 mb-5 flex flex-wrap gap-1.5">
        {m.focus.map((f) => (
          <Badge key={f} tone="blue">
            {FOCUS_LABELS[f] ?? f}
          </Badge>
        ))}
        {m.confidentiality === 'confidentiel' && <Badge tone="dark">Confidentiel · modèle local uniquement</Badge>}
      </div>
      <nav aria-label="Étapes de la mission" className="mb-6 flex flex-wrap gap-1 border-b border-line">
        {MISSION_TABS.map((t) => (
          <NavLink
            key={t.slug}
            to={`/missions/${missionId}/${t.slug}`}
            className={({ isActive }) =>
              `-mb-px border-b-2 px-3 py-2 text-sm ${isActive ? 'border-ink font-medium' : 'border-transparent text-ink/60 hover:text-ink'}`
            }
          >
            {t.label}
          </NavLink>
        ))}
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
        <Placeholder phase={current.phase} />
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
