import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard,
  Briefcase,
  Users,
  CheckSquare,
  FileCheck2,
  Settings,
  LogOut,
  Mail,
} from 'lucide-react'
import { useAuth } from './auth-context'

export function AppLayout() {
  const { auth, logout } = useAuth()

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Opportunities', path: '/opportunities', icon: Briefcase },
    { name: 'Review Queue', path: '/review', icon: FileCheck2 },
    { name: 'Follow-ups', path: '/follow-ups', icon: CheckSquare },
    { name: 'Contacts', path: '/contacts', icon: Users },
    { name: 'Settings', path: '/settings', icon: Settings },
  ]

  return (
    <div className="h-screen bg-slate-950 text-slate-100 flex flex-col md:flex-row overflow-hidden">
      {/* Sticky / Fixed Sidebar */}
      <aside className="w-full md:w-64 bg-slate-900 border-b md:border-b-0 md:border-r border-slate-800 flex flex-col shrink-0 md:h-screen md:sticky md:top-0">
        {/* Brand */}
        <div className="h-16 flex items-center px-6 border-b border-slate-800/80">
          <div className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 font-bold flex items-center justify-center border border-indigo-500/30 mr-3">
            R
          </div>
          <span className="font-bold text-lg text-white tracking-tight">Relayn</span>
          {auth?.is_demo_mode && (
            <span className="ml-auto text-[10px] bg-amber-500/10 text-amber-400 font-semibold px-2 py-0.5 rounded border border-amber-500/20 uppercase tracking-wider">
              Demo
            </span>
          )}
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1.5 flex-1">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                    isActive
                      ? 'bg-indigo-600/10 text-indigo-400 border border-indigo-500/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`
                }
              >
                <Icon className="w-4 h-4 mr-3 shrink-0" />
                {item.name}
              </NavLink>
            )
          })}
        </nav>

        {/* Bottom User / Sync Status & Logout */}
        <div className="p-4 border-t border-slate-800/80 space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <div className="flex items-center space-x-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse"></span>
              <span>Sync Idle</span>
            </div>
            <span className="text-slate-500">{auth?.timezone || 'UTC'}</span>
          </div>

          <button
            onClick={() => logout()}
            className="w-full flex items-center px-3 py-2 text-sm text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition cursor-pointer"
          >
            <LogOut className="w-4 h-4 mr-3 shrink-0" />
            Lock Application
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <header className="h-16 border-b border-slate-800 px-6 flex items-center justify-between bg-slate-900/40 backdrop-blur-sm">
          <h1 className="text-base font-semibold text-white">Career Management Pipeline</h1>
          <div className="text-xs text-slate-400 flex items-center space-x-4">
            <span className="flex items-center">
              <Mail className="w-3.5 h-3.5 mr-1 text-slate-500" />
              Single Mailbox
            </span>
          </div>
        </header>

        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
