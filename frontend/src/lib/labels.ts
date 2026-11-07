export const DOMAIN_LABELS: Record<string, string> = {
  crypto: 'Crypto-actifs',
  fiscal: 'Fiscalité',
  tokenisation: 'Tokenisation',
  resilience: 'Résilience',
  cyber: 'Cybersécurité',
  lcbft: 'LCB-FT',
  ia: 'IA',
  donnees: 'Données',
  produits: 'Produits',
}

/** "02023R1114-20240109" -> "Version consolidée au 09/01/2024"; original acts -> "Journal officiel". */
export function versionLabel(version: string, consolidated: boolean): string {
  const m = /-(\d{4})(\d{2})(\d{2})/.exec(version)
  if (consolidated && m) return `Version consolidée au ${m[3]}/${m[2]}/${m[1]}`
  return 'Journal officiel (texte d’origine)'
}

export function frDate(iso: string): string {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}
