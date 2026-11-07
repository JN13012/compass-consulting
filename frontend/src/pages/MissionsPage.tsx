import { Link } from 'react-router-dom'

import { PageHeader, Placeholder } from '../components/PageHeader'

export function MissionsPage() {
  return (
    <>
      <PageHeader title="Missions" subtitle="Un espace par client." />
      <Placeholder phase="phase 2a" />
      <p className="mt-4 text-sm">
        Aperçu des onglets :{' '}
        <Link className="underline" to="/missions/demo/diagnostic">
          mission de démonstration
        </Link>
      </p>
    </>
  )
}
