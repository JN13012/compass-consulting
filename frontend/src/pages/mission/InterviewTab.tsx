import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../../api/client'
import type { components } from '../../api/schema'
import type { MissionOut } from '../../lib/missions'

type Interview = components['schemas']['Interview']

function errorText(error: unknown, status: number): string {
  const detail = (error as { detail?: unknown } | undefined)?.detail
  return typeof detail === 'string' ? detail : `Erreur ${status}`
}

export function InterviewTab({ mission }: { mission: MissionOut }) {
  const id = mission.id
  const qc = useQueryClient()
  const navigate = useNavigate()
  const path = { params: { path: { mission_id: id } } }
  const grid = useQuery({
    queryKey: ['interview', id],
    queryFn: async () => (await api.GET('/missions/{mission_id}/interview', path)).data,
  })
  const [draft, setDraft] = useState<Interview>({ answers: {}, checked: [] })
  const [dirty, setDirty] = useState(false)
  useEffect(() => {
    if (grid.data) setDraft(grid.data.interview)
  }, [grid.data])

  const save = useMutation({
    mutationFn: async (body: Interview) => {
      const { error } = await api.PUT('/missions/{mission_id}/interview', { ...path, body })
      if (error) throw new Error('Enregistrement impossible.')
    },
    onSuccess: () => setDirty(false),
  })
  const persist = (next: Interview) => {
    setDraft(next)
    save.mutate(next)
  }
  const followups = useMutation({
    mutationFn: async () => {
      const { data, error, response } = await api.POST('/missions/{mission_id}/interview/followups', path)
      if (error || !data) throw new Error(errorText(error, response.status))
      return data.questions
    },
  })
  const toNotes = useMutation({
    mutationFn: async () => {
      const { data, error, response } = await api.POST('/missions/{mission_id}/interview/notes', path)
      if (error || !data) throw new Error(errorText(error, response.status))
      return data
    },
    onSuccess: (data) => {
      qc.setQueryData(['mission', id], data)
      void qc.invalidateQueries({ queryKey: ['missions'] })
      navigate(`/missions/${id}/diagnostic`)
    },
  })

  if (grid.isPending) return <p className="text-sm">Chargement…</p>
  if (!grid.data) return <p className="text-sm">Grille indisponible.</p>
  const questions = grid.data.sections.flatMap((s) => s.themes.flatMap((t) => t.questions))
  const answered = questions.filter((q) => draft.answers[q.id]?.trim()).length

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-sm text-ink/70">
          Grille d'entretien adaptée aux domaines de la mission. {answered}/{questions.length} réponses
          {save.isPending ? ' · enregistrement…' : dirty ? ' · non enregistré' : ''}
        </p>
        <a href={`/api/missions/${id}/interview/print`} target="_blank" rel="noreferrer" className="ml-auto text-sm underline">
          Imprimer la grille vierge
        </a>
        <button
          onClick={() => followups.mutate()}
          disabled={followups.isPending}
          className="rounded border border-ink/30 px-3 py-2 text-sm disabled:opacity-40"
        >
          {followups.isPending ? 'Réflexion…' : 'Questions de relance (IA)'}
        </button>
        <button
          onClick={() => {
            if (window.confirm('Remplacer les notes de la mission par les réponses de la grille ? Les analyses déjà faites seront effacées.'))
              toNotes.mutate()
          }}
          disabled={toNotes.isPending || answered === 0}
          className="rounded bg-ink px-4 py-2 text-sm text-white disabled:opacity-40"
        >
          Envoyer vers les notes
        </button>
      </div>

      {[followups, toNotes].map(
        (m, i) =>
          m.isError && (
            <p key={i} role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-sm">
              {m.error.message}
            </p>
          ),
      )}
      {followups.data && (
        <div className="rounded border border-ink/30 bg-white p-4">
          <h2 className="mb-2 text-sm font-medium">Questions de relance suggérées</h2>
          <ol className="list-decimal space-y-2 pl-5 text-sm">
            {followups.data.map((f) => (
              <li key={f.question}>
                {f.question}
                <p className="text-xs text-ink/60">{f.raison}</p>
              </li>
            ))}
          </ol>
        </div>
      )}

      {grid.data.sections.map((s) => (
        <div key={s.key} className="rounded border border-line bg-white">
          <header className="border-b border-line px-4 py-3">
            <h2 className="font-medium">{s.title}</h2>
            <p className="text-xs text-ink/60">{s.intro}</p>
          </header>
          <div className="space-y-5 px-4 py-4">
            {s.themes.map((t) => (
              <div key={t.title}>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink/60">{t.title}</h3>
                <div className="space-y-3">
                  {t.questions.map((q) => (
                    <label key={q.id} className="block">
                      <span className="text-sm font-medium">{q.question}</span>
                      <span className="block text-xs text-ink/60">Ce qu'on cherche : {q.but}</span>
                      <textarea
                        rows={2}
                        value={draft.answers[q.id] ?? ''}
                        onChange={(e) => {
                          setDraft({ ...draft, answers: { ...draft.answers, [q.id]: e.target.value } })
                          setDirty(true)
                        }}
                        onBlur={() => dirty && save.mutate(draft)}
                        placeholder="Réponse du client, avec ses mots"
                        className="mt-1 w-full rounded border border-ink/20 p-2 text-sm"
                      />
                    </label>
                  ))}
                </div>
              </div>
            ))}
            {(s.observer ?? []).length > 0 && (
              <div>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink/60">À observer ou demander</h3>
                <ul className="space-y-1 text-sm">
                  {s.observer?.map((o) => (
                    <li key={o}>
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={draft.checked?.includes(o) ?? false}
                          onChange={() => {
                            const checked = draft.checked ?? []
                            persist({ ...draft, checked: checked.includes(o) ? checked.filter((x) => x !== o) : [...checked, o] })
                          }}
                        />
                        {o}
                      </label>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      ))}
    </section>
  )
}
