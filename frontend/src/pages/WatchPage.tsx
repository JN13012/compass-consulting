import { PageHeader, Placeholder } from '../components/PageHeader'

export function WatchPage() {
  return (
    <>
      <PageHeader eyebrow="Veille" title="Veille réglementaire" subtitle="Mises à jour des textes officiels, articles modifiés et missions concernées." />
      <Placeholder
        title="Bientôt disponible"
        text="Vérification des nouvelles versions consolidées sur EUR-Lex, comparaison article par article et alerte sur les missions qui citent un passage modifié."
      />
    </>
  )
}
