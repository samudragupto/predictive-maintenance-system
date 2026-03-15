/**
 * Header Component
 * Top navigation bar with search and user actions
 */

import React, { useState } from 'react'
import { Search, Bell, RefreshCw, Settings, Menu, Zap } from 'lucide-react'
import { cn } from '../../utils/helpers'

export default function Header({ collapsed, onMenuToggle }) {
  const [searchQuery, setSearchQuery] = useState('')

  return (
    <header className={cn(
      'fixed top-0 right-0 h-16 bg-dark-800/80 backdrop-blur-xl border-b border-dark-700 z-30 flex items-center justify-between px-6 transition-all duration-300',
      collapsed ? 'left-16' : 'left-64',
    )}>
      {/* Left Side */}
      <div className="flex items-center gap-4">
        <button
          onClick={onMenuToggle}
          className="lg:hidden p-2 rounded-lg text-dark-400 hover:text-white hover:bg-dark-700"
        >
          <Menu size={20} />
        </button>

        {/* Search */}
        <div className="relative hidden md:block">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
          <input
            type="text"
            placeholder="Search vehicles, diagnoses..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-80 pl-10 pr-4 py-2 bg-dark-700 border border-dark-600 rounded-lg text-sm text-white placeholder-dark-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
          />
        </div>
      </div>

      {/* Right Side */}
      <div className="flex items-center gap-3">
        {/* System Status */}
        <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 bg-success-500/10 rounded-full">
          <Zap size={14} className="text-success-500" />
          <span className="text-xs font-medium text-success-500">System Online</span>
        </div>

        {/* Notifications */}
        <button 
          onClick={() => toast('No new notifications', { icon: '🔔' })}
          className="relative p-2 rounded-lg text-dark-400 hover:text-white hover:bg-dark-700 transition-colors"
        >
          <Bell size={20} />
          <span className="absolute top-1 right-1 w-2 h-2 bg-danger-500 rounded-full" />
        </button>

        {/* Settings */}
        <button 
          onClick={() => toast('Settings panel coming soon!', { icon: '⚙️' })}
          className="p-2 rounded-lg text-dark-400 hover:text-white hover:bg-dark-700 transition-colors"
        >
          <Settings size={20} />
        </button>

        {/* User Avatar */}
        <div className="flex items-center gap-3 ml-2 pl-3 border-l border-dark-700">
          <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
            <span className="text-sm font-bold text-white">A</span>
          </div>
          <div className="hidden lg:block">
            <p className="text-sm font-medium text-white">Admin</p>
            <p className="text-xs text-dark-400">OEM Operator</p>
          </div>
        </div>
      </div>
    </header>
  )
}