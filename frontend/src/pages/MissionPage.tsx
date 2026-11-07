import { NavLink, Navigate, useParams } from 'react-router-dom'

import { PageHeader, Placeholder } from '../components/PageHeader'

export const MISSION_TABS = [
  { slug: 'diagnostic', label: '1. Diagnostic', phase: 'phase 2a' },
  { slug: 'solutions', label: '2. Solutions', phase: 'phase 2b' },
  { slug: 'reglementation', label: '3. Réglementation', phase: 'phase 2b' },
  { slug: 'benchmark', label: '4. Benchmark', phase: 'phase 3' },
  { slug: 'poc', label: '5. POC & évaluation', phase: 'phase 4' },
  { slug: 'livrables', label: '6. Livrables', phase: 'phase 5' },
] as const

export function MissionPage() {
  const { missionId, tab } = useParams()
  const current = MISSION_TABS.find((t) => t.slug === tab)
  if (!current) return <Navigate to={`/missions/${missionId}/${MISSION_TABS[0].slug}`} replace />

  return (
    <>
      <PageHeader title={`Mission ${missionId}`} />
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
      <Placeholder phase={current.phase} />
    </>
  )
}
