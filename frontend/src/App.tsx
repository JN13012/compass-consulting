import { Navigate, Route, Routes } from 'react-router-dom'

import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { KnowledgeBasePage } from './pages/KnowledgeBasePage'
import { MissionPage, MISSION_TABS } from './pages/MissionPage'
import { MissionsPage } from './pages/MissionsPage'
import { SettingsPage } from './pages/SettingsPage'
import { WatchPage } from './pages/WatchPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="missions" element={<MissionsPage />} />
        <Route path="missions/:missionId" element={<Navigate to={MISSION_TABS[0].slug} replace />} />
        <Route path="missions/:missionId/:tab" element={<MissionPage />} />
        <Route path="veille" element={<WatchPage />} />
        <Route path="connaissances" element={<KnowledgeBasePage />} />
        <Route path="parametres" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
