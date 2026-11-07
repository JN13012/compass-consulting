import { PageHeader, Placeholder } from '../components/PageHeader'

export function SettingsPage() {
  return (
    <>
      <PageHeader title="Paramètres" subtitle="Fournisseurs IA, clés API, sources surveillées." />
      <Placeholder phase="une phase ultérieure (configuration actuelle : config/llm.yaml)" />
    </>
  )
}
