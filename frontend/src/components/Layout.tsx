import { NavLink, Outlet } from 'react-router-dom'

import { Disclaimer } from './Disclaimer'

const NAV = [
  { to: '/missions', label: 'Missions' },
  { to: '/veille', label: 'Veille' },
  { to: '/connaissances', label: 'Base de connaissances' },
]

export function Layout() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-60 shrink-0 border-r border-line bg-white px-4 py-6">
        <NavLink to="/" className="mb-8 block text-lg font-semibold tracking-tight">
          Compass
        </NavLink>
        <nav aria-label="Navigation principale" className="flex flex-col gap-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `rounded px-3 py-2 text-sm ${isActive ? 'bg-ink text-white' : 'hover:bg-paper'}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <Disclaimer />
        <main className="mx-auto w-full max-w-5xl flex-1 px-8 py-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
