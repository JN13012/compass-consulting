import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { api } from '../api/client'
import { FOCUS_LABELS } from '../lib/labels'
import type { MissionOut } from '../lib/missions'

const FOCUS = ['ia', 'blockchain', 'cyber'] as const
type Focus = (typeof FOCUS)[number]

/** Creates a mission, or edits `mission` when given. */
export function MissionForm({ mission, onSaved, onCancel }: { mission?: MissionOut; onSaved: (id: string) => void; onCancel?: () => void }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({
    client: mission?.client ?? '',
    sector: mission?.sector ?? '',
    context: mission?.context ?? '',
    notes: mission?.notes ?? '',
    focus: (mission?.focus ?? []) as string[],
    confidential: mission?.confidentiality === 'confidentiel',
  })
  const save = useMutation({
    mutationFn: async () => {
      const body = {
        client: form.client,
        sector: form.sector,
        context: form.context,
        notes: form.notes,
        focus: form.focus as Focus[],
        confidentiality: form.confidential ? ('confidentiel' as const) : ('public' as const),
      }
      const { data, error } = mission
        ? await api.PUT('/missions/{mission_id}', { params: { path: { mission_id: mission.id } }, body })
        : await api.POST('/missions', { body })
      if (error || !data) throw new Error('Enregistrement impossible.')
      return data
    },
    onSuccess: (data) => {
      qc.setQueryData(['mission', data.id], data)
      void qc.invalidateQueries({ queryKey: ['missions'] })
      onSaved(data.id)
    },
  })
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [k]: e.target.value })
  const input = 'w-full rounded border border-ink/30 bg-white p-2 text-sm'

  return (
    <form
      className="mb-8 space-y-3 rounded border border-line bg-white p-4"
      onSubmit={(e) => {
        e.preventDefault()
        save.mutate()
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
        <textarea rows={8} className={input} value={form.notes} onChange={set('notes')} />
      </label>
      {mission && (
        <p className="text-xs text-ink/60">
          Modifier le secteur, le contexte, les notes, les domaines ou la confidentialité efface les analyses déjà faites (elles ne seraient plus à jour).
        </p>
      )}
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
        <div className="ml-auto flex gap-2">
          {onCancel && (
            <button type="button" onClick={onCancel} className="rounded border border-ink/30 px-4 py-2">
              Annuler
            </button>
          )}
          <button type="submit" disabled={save.isPending} className="rounded bg-ink px-4 py-2 text-white">
            {mission ? 'Enregistrer' : 'Créer'}
          </button>
        </div>
      </div>
      {save.isError && <p role="alert" className="text-sm text-red-700">{save.error.message}</p>}
    </form>
  )
}
