const TONES = {
  neutral: 'bg-ink/5 text-ink/70 ring-ink/10',
  dark: 'bg-ink text-white ring-ink',
  green: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  amber: 'bg-amber-50 text-amber-800 ring-amber-200',
  red: 'bg-red-50 text-red-800 ring-red-200',
  blue: 'bg-accent-soft text-ink ring-accent/30',
} as const

export type Tone = keyof typeof TONES

export function Badge({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: Tone }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset ${TONES[tone]}`}>
      {children}
    </span>
  )
}
