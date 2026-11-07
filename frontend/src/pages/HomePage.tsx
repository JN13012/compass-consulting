import { useQuery } from '@tanstack/react-query'

import { api } from '../api/client'
import { PageHeader } from '../components/PageHeader'

export function HomePage() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const { data, error } = await api.GET('/health')
      if (error || !data) throw new Error('API injoignable')
      return data
    },
  })

  return (
    <>
      <PageHeader
        title="Compass"
        subtitle="Assistant du consultant IA & Blockchain : diagnostic, solutions, réglementation, benchmark, POC, livrables."
      />
      <section aria-label="État du système" className="rounded border border-line bg-white p-4 text-sm">
        <h2 className="mb-2 font-medium">État du système</h2>
        {health.isPending && <p>Vérification…</p>}
        {health.isError && <p className="text-red-700">API injoignable.</p>}
        {health.data && (
          <ul className="space-y-1">
            <li>API : {health.data.status === 'ok' ? 'opérationnelle' : 'dégradée'}</li>
            <li>Base de données : {health.data.database === 'ok' ? 'connectée' : 'injoignable'}</li>
            <li>Version : {health.data.version}</li>
          </ul>
        )}
      </section>
    </>
  )
}
