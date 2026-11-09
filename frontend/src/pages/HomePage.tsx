import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { api } from '../api/client'

const STEPS = [
  ['Entretiens', 'Grille de questions par domaine, relances proposées par l’IA, réponses rangées dans les notes.'],
  ['Diagnostic', 'Notes d’entretien → irritants, maturité ; chaque citation est vérifiée dans les notes.'],
  ['Solutions', 'De la simple digitalisation à l’IA ou la blockchain ; verdict blockchain calculé par une grille.'],
  ['Réglementation', 'MiCA, DORA, NIS2, AI Act… obligations appuyées sur le passage officiel exact.'],
  ['Benchmark', 'Données on-chain et registre MiCA de l’ESMA, collectées en direct, chaque cellule sourcée.'],
  ['POC', 'Cadrage avec critères chiffrés, puis évaluation sur un jeu de test que le développeur ne voit pas.'],
  ['Livrables', 'Note de mission prête à imprimer, export PDF.'],
] as const

const PRINCIPLES = [
  ['Aucune citation générée', 'Le modèle renvoie des identifiants ; le texte affiché est relu depuis la base.'],
  ['Refuser plutôt qu’inventer', 'Hors corpus, l’outil répond « le corpus ne permet pas de conclure ».'],
  ['Confidentialité dans le code', 'Une mission confidentielle ne peut appeler qu’un modèle local.'],
  ['Mesuré, pas affirmé', '48 questions de test gelées avant mesure, intervalles de confiance de Wilson.'],
] as const

function Figure({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded border border-line bg-white p-4">
      <p className="text-2xl font-semibold tracking-tight">{value}</p>
      <p className="mt-1 text-xs text-ink/70">{label}</p>
    </div>
  )
}

export function HomePage() {
  const sources = useQuery({ queryKey: ['kb-sources'], queryFn: async () => (await api.GET('/kb/sources')).data ?? [] })
  const missions = useQuery({ queryKey: ['missions'], queryFn: async () => (await api.GET('/missions')).data ?? [] })
  const passages =sources.data?.reduce((n, s) => n + s.passages, 0) ?? 0

  return (
    <div className="space-y-8">
      <header>
        <p className="text-xs uppercase tracking-widest text-ink/60">Assistant du consultant</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">Compass - IA, Blockchain, Cybersécurité</h1>
        <p className="mt-2 max-w-2xl text-ink/80">
          Conduit une mission de conseil de bout en bout, du premier entretien au livrable, en s’appuyant sur les textes
          officiels européens et des données publiques vérifiables.
        </p>
        <div className="mt-4 flex gap-3">
          <Link to="/missions" className="rounded bg-ink px-4 py-2 text-sm text-white">
            Voir les missions
          </Link>
          <Link to="/textes" className="rounded border border-ink/30 px-4 py-2 text-sm">
            Interroger les textes
          </Link>
        </div>
      </header>

      <section aria-label="Chiffres clés" className="grid grid-cols-3 gap-3">
        <Figure value={String(sources.data?.length ?? '-')} label="textes officiels (versions consolidées)" />
        <Figure value={passages ? passages.toLocaleString('fr-FR') : '-'} label="passages indexés et citables" />
        <Figure value={missions.data ? String(missions.data.length) : '-'} label="missions en cours" />
      </section>

      <section>
        <h2 className="mb-3 font-medium">Une mission en sept étapes</h2>
        <ol className="grid gap-3 md:grid-cols-4">
          {STEPS.map(([title, text], i) => (
            <li key={title} className="rounded border border-line bg-white p-4">
              <p className="text-xs text-ink/60">Étape {i}</p>
              <p className="font-medium">{title}</p>
              <p className="mt-1 text-sm text-ink/75">{text}</p>
            </li>
          ))}
        </ol>
      </section>

      <section>
        <h2 className="mb-3 font-medium">Garde-fous</h2>
        <ul className="grid gap-3 md:grid-cols-2">
          {PRINCIPLES.map(([title, text]) => (
            <li key={title} className="border-l-2 border-ink pl-3">
              <p className="text-sm font-medium">{title}</p>
              <p className="text-sm text-ink/75">{text}</p>
            </li>
          ))}
        </ul>
      </section>

    </div>
  )
}
