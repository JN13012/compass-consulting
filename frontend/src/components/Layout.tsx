import { useQuery } from '@tanstack/react-query'
import { NavLink, Outlet } from 'react-router-dom'

import { api } from '../api/client'

const NAV = [
  { to: '/', label: 'Tableau de bord', end: true },
  { to: '/missions', label: 'Missions', end: false },
  { to: '/textes', label: 'Textes officiels', end: false },
  { to: '/veille', label: 'Veille', end: false },
]

export function Layout() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: async () => (await api.GET('/health')).data ?? null,
  })

  return (
    <div className="flex min-h-screen">
      <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col bg-ink px-4 py-6 text-white">
        <NavLink to="/" className="mb-10 block px-3">
          <span className="block font-serif text-2xl font-semibold tracking-tight">Compass</span>
          <span className="mt-0.5 block text-[11px] uppercase tracking-[0.18em] text-white/50">IA · Blockchain · Cyber</span>
        </NavLink>
        <nav aria-label="Navigation principale" className="flex flex-col gap-0.5">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `border-l-2 px-3 py-2 text-sm transition-colors ${
                  isActive ? 'border-accent bg-white/10 font-medium text-white' : 'border-transparent text-white/65 hover:bg-white/5 hover:text-white'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto space-y-1 border-t border-white/10 px-3 pt-4 text-[11px] text-white/50">
          <p>
            Modèle : <span className="text-white/80">{health.data?.ai_model ?? '…'}</span>
          </p>
          <p>{health.data?.database === 'ok' ? 'Base de données connectée' : health.isPending ? '…' : 'API injoignable'}</p>
        </div>
      </aside>
      <main className="mx-auto w-full max-w-6xl min-w-0 flex-1 px-10 py-10">
        <Outlet />
      </main>
    </div>
  )
}
