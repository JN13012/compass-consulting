/** Shapes of the analysis results stored on a mission (mirror of backend app/missions/analysis.py). */

export interface Diagnostic {
  synthese: string
  processus: { nom: string; description: string; outils: string[]; volume: string }[]
  irritants: { id: string; titre: string; description: string; impact: 'élevé' | 'moyen' | 'faible'; source: string; source_verifiee: boolean }[]
  maturite: { axe: string; note: number; justification: string }[]
}

export interface BlockchainCheck {
  plusieurs_parties: boolean
  sans_confiance_mutuelle: boolean
  registre_partage: boolean
  actif_programmable: boolean
  intermediaire_suffit: boolean
  explication: string
  verdict: 'pertinente' | 'deconseillee' | null
}

export interface Solution {
  irritant_id: string
  niveau: 'digitaliser' | 'automatiser' | 'cyber' | 'ia' | 'blockchain'
  titre: string
  description: string
  gain: string
  cout: string
  delai: string
  risques: string
  horizon: 'quick_win' | 'moyen_terme' | 'long_terme'
  verification_blockchain: BlockchainCheck | null
}

export interface Solutions {
  synthese: string
  solutions: Solution[]
}

export interface RegCitation {
  ref: string
  heading: string
  text: string
  url: string
  version: string
  consolidated: boolean
}

export interface TextAnalysis {
  code: string
  titre: string
  applicable: 'oui' | 'a_verifier' | 'non'
  raisonnement: string
  obligations: { obligation: string; statut: 'couvert' | 'manquant' | 'a_verifier'; justification: string; citations: RegCitation[] }[]
  obligations_rejetees: number
}

export interface Regulation {
  textes: TextAnalysis[]
  ecartes: { code: string; applicable: string; raisonnement: string }[]
}
