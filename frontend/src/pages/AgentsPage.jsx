/**
 * Agents Page
 * Monitoring and management of AI agents
 */

import React, { useState, useEffect } from 'react'
import {
  Bot, Activity, RefreshCw, Server, Cpu,
  CheckCircle, XCircle, Shield
} from 'lucide-react'
import toast from 'react-hot-toast'

import StatCard from '../components/common/StatCard'
import StatusBadge from '../components/common/StatusBadge'
import { PageLoader } from '../components/common/LoadingSpinner'
import ErrorDisplay from '../components/common/ErrorDisplay'

import { agentAPI } from '../services/api'
import { formatNumber } from '../utils/helpers'
import { AGENT_TYPES } from '../utils/constants'

export default function AgentsPage() {
  const [stats, setStats] = useState(null)
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      const [statsRes, healthRes] = await Promise.all([
        agentAPI.getStats(),
        agentAPI.getHealth()
      ])
      
      setStats(statsRes.agents || {})
      setHealth(healthRes || {})
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [])

  if (loading && !stats) return <PageLoader text="Connecting to agent network..." />
  if (error && !stats) return <ErrorDisplay error={error} onRetry={fetchData} />

  const totalActions = Object.values(stats).reduce((sum, a) => sum + (a.metrics?.total_actions || 0), 0)
  const allHealthy = health?.all_healthy

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">AI Agent Network</h1>
          <p className="page-subtitle">Multi-agent orchestration status and metrics</p>
        </div>
        <button onClick={fetchData} className="btn-secondary btn-sm">
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Network Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          title="Network Status"
          value={allHealthy ? "Operational" : "Degraded"}
          icon={Server}
          color={allHealthy ? "success" : "danger"}
        />
        <StatCard
          title="Total Agents"
          value={Object.keys(stats).length}
          icon={Bot}
          color="primary"
        />
        <StatCard
          title="Total Actions"
          value={formatNumber(totalActions)}
          icon={Activity}
          color="info"
        />
      </div>

      {/* Agents Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {Object.entries(stats).map(([key, agent]) => {
          const typeInfo = AGENT_TYPES[key] || { label: key, icon: 'Bot', color: 'neutral' }
          const isHealthy = health?.agents?.[key]?.healthy
          
          return (
            <div key={key} className="card relative overflow-hidden group hover:border-dark-600 transition-colors">
              {/* Status Indicator */}
              <div className={`absolute top-0 right-0 p-4`}>
                {isHealthy ? (
                  <CheckCircle size={20} className="text-success-500" />
                ) : (
                  <XCircle size={20} className="text-danger-500" />
                )}
              </div>

              <div className="flex items-start gap-4 mb-6">
                <div className={`p-3 rounded-xl bg-${typeInfo.color}-500/10`}>
                  <Bot size={24} className={`text-${typeInfo.color}-500`} />
                </div>
                <div>
                  <h3 className="font-bold text-white text-lg">{typeInfo.label}</h3>
                  <p className="text-xs text-dark-400 font-mono">{agent.agent_id}</p>
                </div>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-dark-700/30 p-3 rounded-lg">
                  <p className="text-xs text-dark-400 mb-1">Success Rate</p>
                  <p className="text-xl font-bold text-white">
                    {agent.metrics?.success_rate}%
                  </p>
                </div>
                <div className="bg-dark-700/30 p-3 rounded-lg">
                  <p className="text-xs text-dark-400 mb-1">Avg Latency</p>
                  <p className="text-xl font-bold text-white">
                    {agent.metrics?.average_processing_time_ms}ms
                  </p>
                </div>
              </div>

              {/* Capabilities */}
              <div>
                <p className="text-xs font-medium text-dark-300 mb-2">Capabilities</p>
                <div className="flex flex-wrap gap-2">
                  {agent.capabilities?.slice(0, 4).map((cap, idx) => (
                    <span key={idx} className="badge badge-neutral bg-dark-700/50">
                      {cap.replace(/_/g, ' ')}
                    </span>
                  ))}
                  {(agent.capabilities?.length || 0) > 4 && (
                    <span className="badge badge-neutral">
                      +{agent.capabilities.length - 4} more
                    </span>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}