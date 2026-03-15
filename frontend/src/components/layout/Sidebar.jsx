/**
 * Sidebar Navigation Component
 */

import React from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Car, Activity, Stethoscope,
  Calendar, DollarSign, UserCheck, MessageSquare,
  Bot, Shield, Settings, ChevronLeft, ChevronRight,
  Wrench
} from 'lucide-react'
import { cn } from '../../utils/helpers'
import { APP_NAME } from '../../utils/constants'

const iconMap = {
  LayoutDashboard, Car, Activity, Stethoscope,
  Calendar, DollarSign, UserCheck, MessageSquare,
  Bot, Shield, Settings,
}

const navItems = [
  { path: '/', label: 'Dashboard', icon: 'LayoutDashboard' },
  { path: '/vehicles', label: 'Vehicles', icon: 'Car' },
  { path: '/telemetry', label: 'Telemetry', icon: 'Activity' },
  { path: '/diagnoses', label: 'Diagnoses', icon: 'Stethoscope' },
  { path: '/appointments', label: 'Appointments', icon: 'Calendar' },
  { path: '/costs', label: 'Cost Estimates', icon: 'DollarSign' },
  { path: '/behavior', label: 'Driver Behavior', icon: 'UserCheck' },
  { path: '/feedback', label: 'Feedback & RCA', icon: 'MessageSquare' },
  { path: '/agents', label: 'AI Agents', icon: 'Bot' },
  { path: '/security', label: 'Security', icon: 'Shield' },
]

export default function Sidebar({ collapsed, onToggle }) {
  const location = useLocation()

  return (
    <aside className={cn(
      'fixed left-0 top-0 h-screen bg-dark-800 border-r border-dark-700 z-40 transition-all duration-300 flex flex-col',
      collapsed ? 'w-16' : 'w-64',
    )}>
      {/* Logo */}
      <div className={cn(
        'flex items-center h-16 px-4 border-b border-dark-700',
        collapsed ? 'justify-center' : 'gap-3',
      )}>
        <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center flex-shrink-0">
          <Wrench size={18} className="text-white" />
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <h1 className="text-sm font-bold text-white truncate">Predictive</h1>
            <p className="text-xs text-dark-400 truncate">Maintenance AI</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4 px-2">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const Icon = iconMap[item.icon] || LayoutDashboard
            const isActive = location.pathname === item.path ||
              (item.path !== '/' && location.pathname.startsWith(item.path))

            return (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200',
                    isActive
                      ? 'bg-primary-600/10 text-primary-400 border-l-2 border-primary-500'
                      : 'text-dark-400 hover:text-white hover:bg-dark-700/50',
                    collapsed && 'justify-center px-2',
                  )}
                  title={collapsed ? item.label : undefined}
                >
                  <Icon size={20} className="flex-shrink-0" />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </NavLink>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Collapse Button */}
      <div className="p-2 border-t border-dark-700">
        <button
          onClick={onToggle}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-dark-400 hover:text-white hover:bg-dark-700 transition-colors text-sm"
        >
          {collapsed ? <ChevronRight size={18} /> : (
            <>
              <ChevronLeft size={18} />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  )
}