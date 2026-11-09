export function PageHeader({ title, subtitle, eyebrow }: { title: string; subtitle?: string; eyebrow?: string }) {
  return (
    <header className="mb-8">
      {eyebrow && <p className="mb-1 text-[11px] font-medium uppercase tracking-[0.18em] text-accent">{eyebrow}</p>}
      <h1 className="text-3xl font-semibold">{title}</h1>
      {subtitle && <p className="mt-2 max-w-3xl text-sm leading-relaxed text-ink/70">{subtitle}</p>}
    </header>
  )
}

export function Placeholder({ title, text }: { title: string; text: string }) {
  return (
    <div className="rounded-md border border-dashed border-line bg-white/60 p-8 text-center">
      <p className="font-serif text-lg">{title}</p>
      <p className="mx-auto mt-1 max-w-lg text-sm text-ink/60">{text}</p>
    </div>
  )
}
