/**
 * Feedback Page
 * RCA/CAPA and closed-loop feedback management
 */

import React, { useState, useEffect } from 'react'
import {
  MessageSquare, AlertCircle, CheckSquare, Plus,
  FileText, Search
} from 'lucide-react'
import toast from 'react-hot-toast'

import StatCard from '../components/common/StatCard'
import StatusBadge from '../components/common/StatusBadge'
import EmptyState from '../components/common/EmptyState'
import { PageLoader } from '../components/common/LoadingSpinner'
import ErrorDisplay from '../components/common/ErrorDisplay'

import { feedbackAPI } from '../services/api'
import { formatDate } from '../utils/helpers'

export default function FeedbackPage() {
  const [reports, setReports] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('rca') // rca | feedback

  const fetchData = async () => {
    try {
      setLoading(true)
      const [rcaResult, statsResult] = await Promise.all([
        feedbackAPI.getRCAReports({ limit: 50 }),
        feedbackAPI.getStats()
      ])
      
      setReports(rcaResult.data || [])
      setStats(statsResult.data)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  if (loading) return <PageLoader text="Loading feedback data..." />
  if (error) return <ErrorDisplay error={error} onRetry={fetchData} />

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">Feedback Loop</h1>
          <p className="page-subtitle">RCA, CAPA, and continuous improvement</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          title="Total Feedback"
          value={stats?.total_feedbacks || 0}
          icon={MessageSquare}
          color="primary"
        />
        <StatCard
          title="Avg Rating"
          value={stats?.average_rating?.toFixed(1) || '0.0'}
          subtitle="/ 5.0"
          icon={CheckSquare}
          color={stats?.average_rating >= 4 ? 'success' : 'warning'}
        />
        <StatCard
          title="Open RCAs"
          value={reports.filter(r => r.status === 'OPEN').length}
          icon={AlertCircle}
          color="danger"
        />
        <StatCard
          title="Resolution Rate"
          value={`${stats?.resolution_rate || 0}%`}
          icon={FileText}
          color="success"
        />
      </div>

      {/* Main Content */}
      <div className="card">
        <div className="flex items-center gap-6 mb-6 border-b border-dark-700 pb-1">
          <button
            onClick={() => setActiveTab('rca')}
            className={`pb-3 text-sm font-medium transition-colors border-b-2 ${
              activeTab === 'rca' 
                ? 'text-primary-400 border-primary-500' 
                : 'text-dark-400 border-transparent hover:text-white'
            }`}
          >
            RCA Reports
          </button>
          <button
            onClick={() => setActiveTab('feedback')}
            className={`pb-3 text-sm font-medium transition-colors border-b-2 ${
              activeTab === 'feedback' 
                ? 'text-primary-400 border-primary-500' 
                : 'text-dark-400 border-transparent hover:text-white'
            }`}
          >
            Customer Feedback
          </button>
        </div>

        {activeTab === 'rca' && (
          <div className="space-y-4">
            {reports.length === 0 ? (
              <EmptyState title="No RCA reports" description="All issues resolved." />
            ) : (
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Problem</th>
                      <th>Priority</th>
                      <th>Status</th>
                      <th>Created</th>
                      <th>AI Analysis</th>
                    </tr>
                  </thead>
                  <tbody>
                    {reports.map((rca) => (
                      <tr key={rca.rca_id} className="cursor-pointer hover:bg-dark-700/30">
                        <td className="font-mono text-dark-300">{rca.rca_id}</td>
                        <td className="font-medium text-white max-w-xs truncate" title={rca.problem_title}>
                          {rca.problem_title}
                        </td>
                        <td>
                          <StatusBadge 
                            status={rca.priority} 
                            color={rca.priority === 'HIGH' ? 'danger' : 'warning'} 
                          />
                        </td>
                        <td>
                          <StatusBadge 
                            status={rca.status} 
                            color={rca.status === 'OPEN' ? 'warning' : 'success'} 
                            showDot
                          />
                        </td>
                        <td className="text-dark-400">{formatDate(rca.created_at)}</td>
                        <td>
                          {rca.ai_analysis ? (
                            <span className="text-xs bg-primary-500/10 text-primary-400 px-2 py-1 rounded">
                              Generated
                            </span>
                          ) : (
                            <span className="text-xs text-dark-500">None</span>
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

        {activeTab === 'feedback' && (
          <EmptyState 
            icon={MessageSquare} 
            title="Feedback view coming soon" 
            description="This module is currently under development."
          />
        )}
      </div>
    </div>
  )
}