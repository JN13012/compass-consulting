import { useRef } from 'react'

import type { MissionOut } from '../../lib/missions'

const STEPS = [
  ['diagnostic', 'Diagnostic'],
  ['solutions', 'Solutions'],
  ['regulation', 'Réglementation'],
] as const

export function DeliverablesTab({ mission }: { mission: MissionOut }) {
  const frame = useRef<HTMLIFrameElement>(null)
  const url = `/api/missions/${mission.id}/note`

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <p className="text-sm text-ink/70">
          Note de mission assemblée à partir des résultats enregistrés (aucun appel au modèle). Étapes incluses :{' '}
          {STEPS.map(([k, label]) => (mission.steps_done.includes(k) ? '✓ ' : '✗ ') + label).join(' · ')} · Benchmark (dernière collecte).
        </p>
        <a href={url} target="_blank" rel="noreferrer" className="ml-auto text-sm underline">
          Ouvrir dans un onglet
        </a>
        <button
          onClick={() => frame.current?.contentWindow?.print()}
          className="rounded bg-ink px-4 py-2 text-sm text-white"
        >
          Exporter en PDF
        </button>
      </div>
      <iframe ref={frame} title="Note de mission" src={url} className="h-[75vh] w-full rounded border border-line bg-white" />
    </section>
  )
}
