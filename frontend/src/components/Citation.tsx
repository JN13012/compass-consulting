import type { components } from '../api/schema'
import { frDate, versionLabel } from '../lib/labels'

export type PassageOut = components['schemas']['PassageOut']

/** An official passage, always shown with its exact text, reference and official link. */
export function Citation({ passage }: { passage: PassageOut }) {
  return (
    <article className="rounded border border-line bg-white" aria-label={`Passage ${passage.ref}`}>
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-line px-4 py-2">
        <code className="rounded bg-paper px-1.5 py-0.5 text-xs font-semibold">{passage.ref}</code>
        <span className="text-sm font-medium">{passage.heading}</span>
      </header>
      <p className="whitespace-pre-line px-4 py-3 text-sm leading-relaxed">{passage.text}</p>
      <footer className="flex flex-wrap items-center gap-x-3 gap-y-1 border-t border-line px-4 py-2 text-xs text-ink/70">
        <span>{passage.source_title}</span>
        <span aria-hidden>·</span>
        <span>{versionLabel(passage.version, passage.consolidated)}</span>
        <span aria-hidden>·</span>
        <span>Consulté le {frDate(passage.consulted_on)}</span>
        <a className="ml-auto font-medium underline" href={passage.url} target="_blank" rel="noreferrer">
          Voir sur EUR-Lex
        </a>
      </footer>
    </article>
  )
}
