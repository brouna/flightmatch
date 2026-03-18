import { Routes, Route, NavLink } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import MissionList from './pages/MissionList'
import MissionDetail from './pages/MissionDetail'
import PilotList from './pages/PilotList'
import PilotDetail from './pages/PilotDetail'
import HistoricalImport from './pages/HistoricalImport'
import MLRetrain from './pages/MLRetrain'

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/missions', label: 'Missions' },
  { to: '/pilots', label: 'Pilots' },
  { to: '/import', label: 'Import' },
  { to: '/retrain', label: 'ML Retrain' },
]

export default function App() {
  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <nav className="w-56 bg-blue-900 text-white flex flex-col">
        <div className="p-4 border-b border-blue-800">
          <div className="flex items-center gap-2">
            <span className="text-2xl">✈</span>
            <span className="font-bold text-lg">FlightMatch</span>
          </div>
          <p className="text-xs text-blue-300 mt-1">Admin Dashboard</p>
        </div>
        <div className="flex-1 py-4">
          {navItems.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `block px-4 py-2.5 text-sm transition-colors ${
                  isActive
                    ? 'bg-blue-700 text-white font-medium'
                    : 'text-blue-200 hover:bg-blue-800 hover:text-white'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/missions" element={<MissionList />} />
          <Route path="/missions/:id" element={<MissionDetail />} />
          <Route path="/pilots" element={<PilotList />} />
          <Route path="/pilots/:id" element={<PilotDetail />} />
          <Route path="/import" element={<HistoricalImport />} />
          <Route path="/retrain" element={<MLRetrain />} />
        </Routes>
      </main>
    </div>
  )
}
