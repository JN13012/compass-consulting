const TONES = {
  neutral: 'border-line bg-paper text-ink/80',
  dark: 'border-ink bg-ink text-white',
  green: 'border-emerald-300 bg-emerald-50 text-emerald-900',
  amber: 'border-amber-300 bg-amber-50 text-amber-900',
  red: 'border-red-300 bg-red-50 text-red-900',
  blue: 'border-sky-300 bg-sky-50 text-sky-900',
} as const

export type Tone = keyof typeof TONES

export function Badge({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: Tone }) {
  return <span className={`inline-block rounded border px-1.5 py-0.5 text-xs font-medium ${TONES[tone]}`}>{children}</span>
}

