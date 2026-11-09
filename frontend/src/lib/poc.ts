// Shapes of the JSON stored by the POC module (backend/app/poc). The API types them as free dicts.

export type Metric = 'justesse_document' | 'justesse_champs' | 'refus_corrects' | 'faux_refus' | 'latence_p95_s'

export interface Criterion {
  metrique: Metric
  seuil: number
  justification: string
}

export interface Framing {
  nom: string
  solution_retenue: string
  objectif: string
  perimetre: string[]
  hors_perimetre: string[]
  user_stories: string[]
  donnees: string
  architecture: string[]
  criteres: Criterion[]
  risques: string[]
  contraintes: string[]
}

export interface Rate {
  k: number
  n: number
  rate: number
  ic95: [number, number]
}

export interface CriterionResult {
  metrique: Metric
  libelle: string
  seuil: number
  valeur: number
  ic95: [number, number] | null
  atteint: boolean
  robuste: boolean
}

export interface FailureGroup {
  cause: string
  nombre: number
  cas: string[]
  exemples: { id: string; attendu: string; obtenu: string }[]
}

export interface Evaluation {
  status: 'en_cours' | 'terminee' | 'erreur'
  endpoint: string
  done: number
  total: number
  started_at: string
  finished_at?: string
  erreur?: string
  metrics?: Record<Metric, Rate | number> & { erreurs_techniques: number; latence_moyenne_s: number }
  verdict?: CriterionResult[]
  passage_echelle?: boolean
  groupes?: FailureGroup[]
  corrections?: string[]
}

export const METRIC_LABELS: Record<Metric, string> = {
  justesse_document: 'Commandes entièrement justes',
  justesse_champs: 'Champs justes',
  refus_corrects: 'Cas ambigus correctement refusés',
  faux_refus: 'Refus à tort',
  latence_p95_s: 'Latence (95e centile, s)',
}

export const LOWER_IS_BETTER: Metric[] = ['faux_refus', 'latence_p95_s']

export const CAUSE_LABELS: Record<string, string> = {
  faux_refus: 'Refus à tort',
  reponse_au_lieu_de_refus: 'A répondu au lieu de demander à un humain',
  erreur_technique: 'Erreur technique',
}

export const pct = (x: number) => `${Math.round(x * 100)} %`
