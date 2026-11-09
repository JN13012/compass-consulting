import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { NavLink, Outlet } from 'react-router-dom'

import { api } from '../api/client'

const NAV = [
  { to: '/', label: 'Tableau de bord', end: true },
  { to: '/missions', label: 'Missions', end: false },
  { to: '/textes', label: 'Textes officiels', end: false },
  { to: '/veille', label: 'Veille', end: false },
]

export function Layout() {
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
        <SystemPanel />
      </aside>
      <main className="mx-auto w-full max-w-6xl min-w-0 flex-1 px-10 py-10">
        <Outlet />
      </main>
    </div>
  )
}

const DOWN: Record<string, string> = {
  unreachable: 'hors ligne',
  no_key: 'clé API absente',
  not_configured: 'non configurée',
}

function SystemPanel() {
  const qc = useQueryClient()
  const health = useQuery({
    queryKey: ['health'],
    queryFn: async () => (await api.GET('/health')).data ?? null,
    refetchInterval: 30_000,
  })
  const choose = useMutation({
    mutationFn: async (role: string) => (await api.PUT('/settings/ai', { body: { role } })).data,
    onSuccess: (data) => qc.setQueryData(['health'], data),
  })
  const h = health.data
  const active = h?.ai_options?.find((o) => o.role === h.ai_active)
  // Meaning-based search always runs on the local embedding model, whatever generative model is chosen.
  const search = h?.search
  const status = active?.status !== 'ok' ? active?.status : search && search.status !== 'ok' ? search.status : 'ok'

  return (
    <div className="mt-auto space-y-3 border-t border-white/10 px-3 pt-4 text-[11px] text-white/55">
      <div>
        <label htmlFor="ai-choice" className="mb-1 flex items-center gap-2 text-white/80">
          <Dot status={health.isPending ? undefined : status} />
          Modèles d’IA
        </label>
        <select
          id="ai-choice"
          value={h?.ai_active ?? ''}
          onChange={(e) => choose.mutate(e.target.value)}
          disabled={!h || choose.isPending}
          className="w-full rounded border border-white/15 bg-white/5 px-2 py-1 text-[11px] text-white"
        >
          {h?.ai_options?.map((o) => (
            <option key={o.role} value={o.role} disabled={o.status === 'no_key'} className="text-ink">
              {o.local ? 'Local' : 'Clé API'} · {o.model}
              {search ? ` + ${search.detail}` : ''}
              {o.status === 'no_key' ? ' (clé absente)' : ''}
            </option>
          ))}
        </select>
        {!health.isPending && status && status !== 'ok' && <p className="mt-1 leading-snug">{DOWN[status]}</p>}
      </div>
      {h?.texts && <Line status={h.texts.status} label={h.texts.label} detail={h.texts.detail} />}
    </div>
  )
}

function Line({ status, label, detail }: { status: string; label: string; detail: string }) {
  return (
    <div>
      <p className="flex items-center gap-2 text-white/80">
        <Dot status={status} />
        {label}
      </p>
      <p className="ml-4">{detail}</p>
    </div>
  )
}

function Dot({ status }: { status?: string }) {
  const ok = status === 'ok'
  const color = status === undefined ? 'bg-white/30' : ok ? 'bg-emerald-400' : status === 'no_key' ? 'bg-amber-400' : 'bg-red-400'
  return (
    <span className="relative flex h-2 w-2 shrink-0">
      {ok && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />}
      <span className={`relative inline-flex h-2 w-2 rounded-full ${color}`} />
    </span>
  )
}
