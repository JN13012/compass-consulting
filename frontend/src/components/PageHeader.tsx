export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header className="mb-6">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      {subtitle && <p className="mt-1 text-sm text-ink/70">{subtitle}</p>}
    </header>
  )
}

export function Placeholder({ phase }: { phase: string }) {
  return (
    <p className="rounded border border-dashed border-line bg-white p-6 text-sm text-ink/60">
      À construire en {phase}.
    </p>
  )
}
