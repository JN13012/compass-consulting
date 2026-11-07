import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { api } from '../api/client'
import { Badge } from '../components/Badge'
import { FOCUS_LABELS } from '../lib/labels'
import { PageHeader } from '../components/PageHeader'
import { useMissions } from '../lib/missions'

const STEP_LABELS: Record<string, string> = { diagnostic: 'Diagnostic', solutions: 'Solutions', regulation: 'Réglementation' }
const FOCUS = ['ia', 'blockchain', 'cyber'] as const

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

      {showForm && <NewMissionForm onCreated={(id) => navigate(`/missions/${id}/diagnostic`)} />}

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

function NewMissionForm({ onCreated }: { onCreated: (id: string) => void }) {
  const [form, setForm] = useState({ client: '', sector: '', context: '', notes: '', focus: [] as string[], confidential: false })
  const create = useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST('/missions', {
        body: {
          client: form.client,
          sector: form.sector,
          context: form.context,
          notes: form.notes,
          focus: form.focus as ('ia' | 'blockchain' | 'cyber')[],
          confidentiality: form.confidential ? 'confidentiel' : 'public',
        },
      })
      if (error || !data) throw new Error('create')
      return data
    },
    onSuccess: (data) => onCreated(data.id),
  })
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: e.target.value })
  const input = 'w-full rounded border border-ink/30 bg-white p-2 text-sm'

  return (
    <form
      className="mb-8 space-y-3 rounded border border-line bg-white p-4"
      onSubmit={(e) => {
        e.preventDefault()
        create.mutate()
      }}
    >
      <div className="grid gap-3 md:grid-cols-2">
        <label className="text-sm">
          Client
          <input required className={input} value={form.client} onChange={set('client')} />
        </label>
        <label className="text-sm">
          Secteur
          <input required className={input} value={form.sector} onChange={set('sector')} />
        </label>
      </div>
      <label className="block text-sm">
        Contexte (2-3 phrases)
        <input className={input} value={form.context} onChange={set('context')} />
      </label>
      <label className="block text-sm">
        Notes d'entretien
        <textarea rows={6} className={input} value={form.notes} onChange={set('notes')} />
      </label>
      <div className="flex flex-wrap items-center gap-4 text-sm">
        {FOCUS.map((f) => (
          <label key={f} className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={form.focus.includes(f)}
              onChange={() =>
                setForm({ ...form, focus: form.focus.includes(f) ? form.focus.filter((x) => x !== f) : [...form.focus, f] })
              }
            />
            {FOCUS_LABELS[f]}
          </label>
        ))}
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={form.confidential} onChange={(e) => setForm({ ...form, confidential: e.target.checked })} />
          Confidentiel (modèle local uniquement)
        </label>
        <button type="submit" disabled={create.isPending} className="ml-auto rounded bg-ink px-4 py-2 text-white">
          Créer
        </button>
      </div>
    </form>
  )
}
