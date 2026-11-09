import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { api } from '../api/client'
import { Badge } from '../components/Badge'
import { FOCUS_LABELS } from '../lib/labels'
import { PageHeader } from '../components/PageHeader'
import { MissionForm } from '../components/MissionForm'
import { useMissions } from '../lib/missions'

const STEP_LABELS: Record<string, string> = { diagnostic: 'Diagnostic', solutions: 'Solutions', regulation: 'Réglementation' }

export function MissionsPage() {
  const missions = useMissions()
  const qc = useQueryClient()
  const navigate = useNavigate()
  const [showForm, setShowForm] = useState(false)

  const seed = useMutation({
    mutationFn: async () => {
      const { error } = await api.POST('/missions/demo')
      if (error) throw new Error('seed')
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['missions'] }),
  })

  return (
    <>
      <PageHeader title="Missions" subtitle="Un espace par client : diagnostic, solutions, réglementation." />
      <div className="mb-6 flex flex-wrap gap-3">
        <button onClick={() => setShowForm((v) => !v)} className="rounded bg-ink px-4 py-2 text-sm text-white">
          Nouvelle mission
        </button>
        <button onClick={() => seed.mutate()} disabled={seed.isPending} className="rounded border border-ink px-4 py-2 text-sm">
          Charger les 3 missions de démonstration
        </button>
      </div>

      {showForm && <MissionForm onSaved={(id) => navigate(`/missions/${id}/entretiens`)} />}

      {missions.isPending && <p className="text-sm">Chargement…</p>}
      {missions.data?.length === 0 && (
        <p className="rounded border border-dashed border-line bg-white p-6 text-sm text-ink/70">
          Aucune mission. Chargez les missions de démonstration pour découvrir l'outil.
        </p>
      )}
      <ul className="grid gap-3 md:grid-cols-2">
        {missions.data?.map((m) => (
          <li key={m.id}>
            <Link to={`/missions/${m.id}/diagnostic`} className="block rounded border border-line bg-white p-4 hover:border-ink/40">
              <div className="flex items-start justify-between gap-2">
                <h2 className="font-semibold">{m.client}</h2>
                {m.confidentiality === 'confidentiel' && <Badge tone="dark">Confidentiel · modèle local</Badge>}
              </div>
              <p className="mt-1 text-sm text-ink/70">{m.sector}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {m.focus.map((f) => (
                  <Badge key={f} tone="blue">
                    {FOCUS_LABELS[f] ?? f}
                  </Badge>
                ))}
                {(['diagnostic', 'solutions', 'regulation'] as const).map((s) => (
                  <Badge key={s} tone={m.steps_done.includes(s) ? 'green' : 'neutral'}>
                    {m.steps_done.includes(s) ? '✓ ' : ''}
                    {STEP_LABELS[s]}
                  </Badge>
                ))}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </>
  )
}
