/**
 * Security Page
 * UEBA monitoring and security logs
 */

import React, { useState, useEffect } from 'react'
import {
  Shield, AlertTriangle, Lock, Unlock, Search,
  Activity, List
} from 'lucide-react'

import StatCard from '../components/common/StatCard'
import StatusBadge from '../components/common/StatusBadge'
import EmptyState from '../components/common/EmptyState'
import { PageLoader } from '../components/common/LoadingSpinner'
import ErrorDisplay from '../components/common/ErrorDisplay'

import { securityAPI } from '../services/api'
import { formatDateTime } from '../utils/helpers'

export default function SecurityPage() {
  const [logs, setLogs] = useState([])
  const [alerts, setAlerts] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('alerts')

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const [logsRes, alertsRes, summaryRes] = await Promise.all([
          securityAPI.getLogs({ page: 1, page_size: 50 }),
          securityAPI.getAlerts({ limit: 50 }),
          securityAPI.getAlertSummary()
        ])
        
        setLogs(logsRes.data || [])
        setAlerts(alertsRes.data || [])
        setSummary(summaryRes.data)
      } catch (err) {
        setError(err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [])

  if (loading) return <PageLoader text="Loading security data..." />
  if (error) return <ErrorDisplay error={error} />

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">Security Center</h1>
          <p className="page-subtitle">UEBA Monitoring and Audit Logs</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Alerts"
          value={summary?.total_alerts || 0}
          icon={Shield}
          color="primary"
        />
        <StatCard
          title="Critical"
          value={summary?.critical_alerts || 0}
          icon={AlertTriangle}
          color="danger"
        />
        <StatCard
          title="Blocked Actions"
          value={0} // Placeholder until backend adds this metric
          icon={Lock}
          color="warning"
        />
        <StatCard
          title="Open Issues"
          value={summary?.unacknowledged || 0}
          icon={Activity}
          color="info"
        />
      </div>

      {/* Main Content */}
      <div className="card">
        <div className="flex items-center gap-6 mb-6 border-b border-dark-700 pb-1">
          <button
            onClick={() => setActiveTab('alerts')}
            className={`pb-3 text-sm font-medium transition-colors border-b-2 flex items-center gap-2 ${
              activeTab === 'alerts' 
                ? 'text-danger-400 border-danger-500' 
                : 'text-dark-400 border-transparent hover:text-white'
            }`}
          >
            <AlertTriangle size={16} /> UEBA Alerts
          </button>
          <button
            onClick={() => setActiveTab('logs')}
            className={`pb-3 text-sm font-medium transition-colors border-b-2 flex items-center gap-2 ${
              activeTab === 'logs' 
                ? 'text-primary-400 border-primary-500' 
                : 'text-dark-400 border-transparent hover:text-white'
            }`}
          >
            <List size={16} /> Audit Logs
          </button>
        </div>

        {activeTab === 'alerts' && (
          <div className="space-y-4">
            {alerts.length === 0 ? (
              <EmptyState title="No security alerts" description="System is secure." icon={Shield} />
            ) : (
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Severity</th>
                      <th>Timestamp</th>
                      <th>Type</th>
                      <th>Entity</th>
                      <th>Anomaly Score</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {alerts.map((alert) => (
                      <tr key={alert.alert_id} className="hover:bg-dark-700/30">
                        <td>
                          <StatusBadge 
                            status={alert.severity} 
                            color={alert.severity === 'CRITICAL' ? 'danger' : alert.severity === 'HIGH' ? 'orange' : 'warning'} 
                          />
                        </td>
                        <td className="text-dark-300 text-xs">
                          {formatDateTime(alert.detected_at)}
                        </td>
                        <td className="font-medium text-white">{alert.title}</td>
                        <td className="text-dark-300">
                          {alert.entity?.name} ({alert.entity?.type})
                        </td>
                        <td>
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-1.5 bg-dark-700 rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-danger-500" 
                                style={{ width: `${(alert.anomaly_score || 0) * 100}%` }} 
                              />
                            </div>
                            <span className="text-xs text-dark-400">
                              {(alert.anomaly_score || 0).toFixed(2)}
                            </span>
                          </div>
                        </td>
                        <td>
                          <StatusBadge status={alert.status} color="neutral" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'logs' && (
          <div className="space-y-4">
            {logs.length === 0 ? (
              <EmptyState title="No logs found" description="Audit log is empty." icon={List} />
            ) : (
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Level</th>
                      <th>Actor</th>
                      <th>Action</th>
                      <th>Resource</th>
                      <th>Result</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log) => (
                      <tr key={log.log_id} className="hover:bg-dark-700/30">
                        <td className="text-dark-400 text-xs font-mono">
                          {formatDateTime(log.timestamp)}
                        </td>
                        <td>
                          <StatusBadge 
                            status={log.level} 
                            color={log.level === 'ERROR' ? 'danger' : log.level === 'WARNING' ? 'warning' : 'info'} 
                            size="sm"
                          />
                        </td>
                        <td className="text-white text-xs">
                          {log.actor?.name || 'System'}
                        </td>
                        <td className="text-dark-200">
                          {log.action?.name}
                        </td>
                        <td className="text-dark-400 text-xs">
                          {log.resource?.type} {log.resource?.id ? `#${log.resource.id}` : ''}
                        </td>
                        <td>
                          {log.success ? (
                            <span className="text-success-500 text-xs flex items-center gap-1">
                              <CheckCircle size={12} /> Success
                            </span>
                          ) : (
                            <span className="text-danger-500 text-xs flex items-center gap-1">
                              <XCircle size={12} /> Failed
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}