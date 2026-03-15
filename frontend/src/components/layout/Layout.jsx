/**
 * Main Layout Component
 * Wraps all pages with sidebar and header
 */

import React, { useState } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'
import { cn } from '../../utils/helpers'

export default function Layout({ children }) {
  const [collapsed, setCollapsed] = useState(false)

  const handleToggle = () => {
    setCollapsed(!collapsed)
  }

  return (
    <div className="min-h-screen bg-dark-900">
      {/* Sidebar */}
      <Sidebar collapsed={collapsed} onToggle={handleToggle} />

      {/* Header */}
      <Header collapsed={collapsed} onMenuToggle={handleToggle} />

      {/* Main Content */}
      <main className={cn(
        'pt-16 min-h-screen transition-all duration-300',
        collapsed ? 'ml-16' : 'ml-64',
      )}>
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  )
}