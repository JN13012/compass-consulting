import { Badge, type Tone } from '../../components/Badge'
import type { Diagnostic, Regulation, Solution, Solutions } from '../../lib/analysis'
import { versionLabel } from '../../lib/labels'
import type { MissionOut } from '../../lib/missions'

const IMPACT: Record<string, Tone> = { élevé: 'red', moyen: 'amber', faible: 'neutral' }

export function DiagnosticTab({ mission }: { mission: MissionOut }) {
  const d = mission.diagnostic as unknown as Diagnostic | null
  return (
    <>
      <details className="rounded border border-line bg-white p-4 text-sm">
        <summary className="cursor-pointer font-medium">Notes d'entretien</summary>
        <p className="mt-3 whitespace-pre-line leading-relaxed">{mission.notes}</p>
      </details>
      {d && (
        <>
          <Card title="Synthèse">
            <p className="text-sm leading-relaxed">{d.synthese}</p>
          </Card>
          <Card title={`Irritants (${d.irritants.length})`}>
            <ul className="divide-y divide-line">
              {d.irritants.map((i) => (
                <li key={i.id} className="py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <code className="text-xs font-semibold">{i.id}</code>
                    <span className="font-medium">{i.titre}</span>
                    <Badge tone={IMPACT[i.impact]}>impact {i.impact}</Badge>
                  </div>
                  <p className="mt-1 text-sm">{i.description}</p>
                  <blockquote className="mt-2 border-l-2 border-line pl-3 text-xs text-ink/70">
                    « {i.source} »{' '}
                    {i.source_verifiee ? (
                      <Badge tone="green">✓ citation retrouvée dans les notes</Badge>
                    ) : (
                      <Badge tone="amber">⚠ citation non retrouvée telle quelle</Badge>
                    )}
                  </blockquote>
                </li>
              ))}
            </ul>
          </Card>
          <Card title="Maturité">
            <ul className="space-y-2">
              {d.maturite.map((m) => (
                <li key={m.axe} className="grid grid-cols-[12rem_6rem_1fr] items-center gap-3 text-sm">
                  <span>{m.axe}</span>
                  <span aria-label={`${m.note} sur 3`} className="flex gap-1">
                    {[1, 2, 3].map((n) => (
                      <span key={n} className={`h-2.5 w-6 rounded-sm ${n <= m.note ? 'bg-ink' : 'bg-line'}`} />
                    ))}
                  </span>
                  <span className="text-ink/70">{m.justification}</span>
                </li>
              ))}
            </ul>
          </Card>
          <Card title="Processus observés">
            <ul className="space-y-2 text-sm">
              {d.processus.map((p) => (
                <li key={p.nom}>
                  <span className="font-medium">{p.nom}</span> - {p.description}
                  {p.volume && <span className="text-ink/60"> · {p.volume}</span>}
                  {p.outils.length > 0 && <span className="text-ink/60"> · {p.outils.join(', ')}</span>}
                </li>
              ))}
            </ul>
          </Card>
        </>
      )}
    </>
  )
}

const LEVEL: Record<Solution['niveau'], { label: string; tone: Tone }> = {
  digitaliser: { label: 'Digitaliser', tone: 'neutral' },
  automatiser: { label: 'Automatiser', tone: 'blue' },
  cyber: { label: 'Cybersécurité', tone: 'red' },
  ia: { label: 'IA', tone: 'amber' },
  blockchain: { label: 'Blockchain', tone: 'dark' },
}
const HORIZONS: { key: Solution['horizon']; label: string }[] = [
  { key: 'quick_win', label: 'Quick wins (< 3 mois)' },
  { key: 'moyen_terme', label: '3 à 6 mois' },
  { key: 'long_terme', label: '6 à 18 mois' },
]

export function SolutionsTab({ mission }: { mission: MissionOut }) {
  const s = mission.solutions as unknown as Solutions | null
  if (!s) return null
  return (
    <>
      <Card title="Synthèse">
        <p className="text-sm leading-relaxed">{s.synthese}</p>
      </Card>
      <h2 className="font-medium">Feuille de route</h2>
      <div className="grid gap-4 lg:grid-cols-3">
        {HORIZONS.map((h) => (
          <div key={h.key} className="space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-ink/60">{h.label}</h3>
            {s.solutions
              .filter((x) => x.horizon === h.key)
              .map((x) => (
                <SolutionCard key={`${x.irritant_id}-${x.titre}`} s={x} />
              ))}
          </div>
        ))}
      </div>
    </>
  )
}

function SolutionCard({ s }: { s: Solution }) {
  const bc = s.verification_blockchain
  return (
    <article className="rounded border border-line bg-white p-3 text-sm">
      <div className="mb-1 flex flex-wrap items-center gap-1.5">
        <Badge tone={LEVEL[s.niveau].tone}>{LEVEL[s.niveau].label}</Badge>
        <code className="text-xs text-ink/60">{s.irritant_id}</code>
      </div>
      <h4 className="font-medium">{s.titre}</h4>
      <p className="mt-1 text-ink/80">{s.description}</p>
      <dl className="mt-2 grid grid-cols-[4.5rem_1fr] gap-x-2 gap-y-0.5 text-xs">
        <dt className="text-ink/60">Gain</dt>
        <dd>{s.gain}</dd>
        <dt className="text-ink/60">Coût</dt>
        <dd>{s.cout}</dd>
        <dt className="text-ink/60">Délai</dt>
        <dd>{s.delai}</dd>
        <dt className="text-ink/60">Risques</dt>
        <dd>{s.risques}</dd>
      </dl>
      {bc && (
        <div className={`mt-2 rounded border p-2 text-xs ${bc.verdict === 'pertinente' ? 'border-emerald-300 bg-emerald-50' : 'border-amber-300 bg-amber-50'}`}>
          <strong>Grille « Faut-il une blockchain ? » : {bc.verdict === 'pertinente' ? 'pertinente' : 'déconseillée'}</strong>
          <p className="mt-1">{bc.explication}</p>
        </div>
      )}
    </article>
  )
}

const APPLICABLE: Record<string, { label: string; tone: Tone }> = {
  oui: { label: 'S’applique', tone: 'red' },
  a_verifier: { label: 'À vérifier', tone: 'amber' },
  non: { label: 'Ne s’applique pas', tone: 'neutral' },
}
const STATUS: Record<string, { label: string; tone: Tone }> = {
  couvert: { label: 'Couvert', tone: 'green' },
  manquant: { label: 'Manquant', tone: 'red' },
  a_verifier: { label: 'À vérifier', tone: 'amber' },
}

export function RegulationTab({ mission }: { mission: MissionOut }) {
  const r = mission.regulation as unknown as Regulation | null
  if (!r) return null
  return (
    <>
      {r.textes.map((t) => (
        <Card
          key={t.code}
          title={
            <span className="flex flex-wrap items-center gap-2">
              {t.titre} <Badge tone={APPLICABLE[t.applicable].tone}>{APPLICABLE[t.applicable].label}</Badge>
            </span>
          }
        >
          <p className="text-sm text-ink/80">{t.raisonnement}</p>
          {t.obligations.length === 0 && (
            <p className="mt-2 text-sm text-ink/60">Aucune obligation appuyée par un passage trouvé : à approfondir.</p>
          )}
          <ul className="mt-3 space-y-3">
            {t.obligations.map((o) => (
              <li key={o.obligation} className="rounded border border-line p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={STATUS[o.statut].tone}>{STATUS[o.statut].label}</Badge>
                  <span className="font-medium">{o.obligation}</span>
                </div>
                <p className="mt-1 text-ink/80">{o.justification}</p>
                {o.citations.map((c) => (
                  <details key={c.ref} className="mt-2 text-xs">
                    <summary className="cursor-pointer">
                      <code className="font-semibold">{c.ref}</code> - {c.heading}
                    </summary>
                    <p className="mt-1 whitespace-pre-line rounded bg-paper p-2 leading-relaxed">{c.text}</p>
                    <p className="mt-1 text-ink/60">
                      {versionLabel(c.version, c.consolidated)} ·{' '}
                      <a className="underline" href={c.url} target="_blank" rel="noreferrer">
                        Voir sur EUR-Lex
                      </a>
                    </p>
                  </details>
                ))}
              </li>
            ))}
          </ul>
          {t.obligations_rejetees > 0 && (
            <p className="mt-2 text-xs text-ink/60">
              {t.obligations_rejetees} obligation(s) proposée(s) par le modèle écartée(s) : aucun passage officiel valide cité.
            </p>
          )}
        </Card>
      ))}
      {r.ecartes.length > 0 && (
        <Card title="Textes écartés">
          <ul className="space-y-1 text-sm">
            {r.ecartes.map((e) => (
              <li key={e.code}>
                <span className="font-medium">{e.code}</span> - <span className="text-ink/70">{e.raisonnement}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </>
  )
}

function Card({ title, children }: { title: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded border border-line bg-white p-4">
      <h2 className="mb-2 font-medium">{title}</h2>
      {children}
    </section>
  )
}
