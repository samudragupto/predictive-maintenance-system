/**
 * AlertsSummary Component
 * Security alerts overview for the dashboard
 */

import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, AlertTriangle, Bell, ChevronRight } from 'lucide-react'
import StatusBadge from '../common/StatusBadge'

export default function AlertsSummary({ summary, recentAlerts, loading }) {
  const navigate = useNavigate()

  if (loading) {
    return (
      <div className="card animate-pulse">
        <div className="h-5 bg-dark-700 rounded w-1/3 mb-4" />
        <div className="grid grid-cols-3 gap-4 mb-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 bg-dark-700 rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  const alertData = summary || {
    total_alerts: 0,
    critical_alerts: 0,
    high_alerts: 0,
    unacknowledged: 0,
  }

  const alerts = recentAlerts || []

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-title mb-0">Security Alerts</h3>
        <button
          onClick={() => navigate('/security')}
          className="btn-ghost btn-sm"
        >
          View All <ChevronRight size={14} />
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="p-3 bg-dark-700/50 rounded-lg text-center">
          <p className="text-2xl font-bold text-white">{alertData.total_alerts}</p>
          <p className="text-xs text-dark-400">Total</p>
        </div>
        <div className="p-3 bg-danger-500/10 rounded-lg text-center">
          <p className="text-2xl font-bold text-danger-500">{alertData.critical_alerts}</p>
          <p className="text-xs text-dark-400">Critical</p>
        </div>
        <div className="p-3 bg-warning-500/10 rounded-lg text-center">
          <p className="text-2xl font-bold text-warning-500">{alertData.unacknowledged}</p>
          <p className="text-xs text-dark-400">Open</p>
        </div>
      </div>

      {/* Recent Alerts */}
      {alerts.length > 0 ? (
        <div className="space-y-2">
          {alerts.slice(0, 4).map((alert, index) => (
            <div key={alert.alert_id || index} className="flex items-center gap-3 p-2 rounded-lg hover:bg-dark-700/30">
              <AlertTriangle
                size={16}
                className={alert.severity === 'CRITICAL' ? 'text-danger-500' : 'text-warning-500'}
              />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-dark-200 truncate">
                  {alert.title || 'Security Alert'}
                </p>
              </div>
              <StatusBadge
                status={alert.severity || 'LOW'}
                color={alert.severity === 'CRITICAL' ? 'danger' : alert.severity === 'HIGH' ? 'orange' : 'warning'}
              />
            </div>
          ))}
        </div>
      ) : (
        <div className="flex items-center gap-2 p-3 bg-success-500/10 rounded-lg">
          <Shield size={16} className="text-success-500" />
          <span className="text-sm text-success-500">No active alerts</span>
        </div>
      )}
    </div>
  )
}