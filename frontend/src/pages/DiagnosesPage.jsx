/**
 * Diagnoses Page
 * AI-powered diagnosis results and management
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  Stethoscope, RefreshCw, Search, Filter, AlertTriangle,
  CheckCircle, Clock, ChevronRight, Brain, Target,
  Zap, Play
} from 'lucide-react'
import toast from 'react-hot-toast'

import StatusBadge from '../components/common/StatusBadge'
import EmptyState from '../components/common/EmptyState'
import { PageLoader } from '../components/common/LoadingSpinner'
import ErrorDisplay from '../components/common/ErrorDisplay'

import { diagnosisAPI, vehicleAPI } from '../services/api'
import {
  formatTimeAgo, formatPercent, formatDateTime,
  getHealthColor, cn
} from '../utils/helpers'
import { RISK_LEVELS } from '../utils/constants'

export default function DiagnosesPage() {
  const [diagnoses, setDiagnoses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [riskFilter, setRiskFilter] = useState('')
  const [selectedDiagnosis, setSelectedDiagnosis] = useState(null)
  const [runningDiagnosis, setRunningDiagnosis] = useState(false)
  const [vehicles, setVehicles] = useState([])
  const [selectedVehicleForDiag, setSelectedVehicleForDiag] = useState('')

  const fetchDiagnoses = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await diagnosisAPI.getRecent({
        limit: 50,
        risk_level: riskFilter || undefined,
      })
      setDiagnoses(result.data || [])
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [riskFilter])

  const fetchVehicles = async () => {
    try {
      const result = await vehicleAPI.list({ page: 1, page_size: 100 })
      setVehicles(result.data || [])
    } catch (err) {
      console.error('Error fetching vehicles:', err)
    }
  }

  useEffect(() => {
    fetchDiagnoses()
    fetchVehicles()
  }, [fetchDiagnoses])

  const handleRunDiagnosis = async () => {
    if (!selectedVehicleForDiag) {
      toast.error('Please select a vehicle')
      return
    }
    try {
      setRunningDiagnosis(true)
      toast.loading('Running AI diagnosis...', { id: 'rundiag' })
      const result = await diagnosisAPI.create(selectedVehicleForDiag, 'MANUAL')
      toast.success('Diagnosis complete!', { id: 'rundiag' })
      await fetchDiagnoses()
    } catch (err) {
      toast.error('Diagnosis failed', { id: 'rundiag' })
    } finally {
      setRunningDiagnosis(false)
    }
  }

  if (loading && diagnoses.length === 0) {
    return <PageLoader text="Loading diagnoses..." />
  }

  if (error && diagnoses.length === 0) {
    return <ErrorDisplay error={error} onRetry={fetchDiagnoses} />
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">AI Diagnoses</h1>
          <p className="page-subtitle">AI-powered vehicle health analysis and failure predictions</p>
        </div>
        <button onClick={fetchDiagnoses} className="btn-secondary btn-sm">
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Run Diagnosis Panel */}
      <div className="card bg-gradient-to-r from-primary-600/10 to-primary-800/5 border-primary-500/20">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-500/20 rounded-lg">
              <Brain size={24} className="text-primary-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Run New Diagnosis</h3>
              <p className="text-xs text-dark-400">Select a vehicle for AI analysis</p>
            </div>
          </div>
          <div className="flex items-center gap-3 flex-1 sm:justify-end">
            <select
              value={selectedVehicleForDiag}
              onChange={(e) => setSelectedVehicleForDiag(e.target.value)}
              className="input w-52"
            >
              <option value="">Select Vehicle...</option>
              {vehicles.map((v) => (
                <option key={v.vehicle_id} value={v.vehicle_id}>
                  {v.vehicle_id} - {v.make} {v.model}
                </option>
              ))}
            </select>
            <button
              onClick={handleRunDiagnosis}
              disabled={runningDiagnosis || !selectedVehicleForDiag}
              className="btn-primary"
            >
              {runningDiagnosis ? (
                <><RefreshCw size={14} className="animate-spin" /> Analyzing...</>
              ) : (
                <><Play size={14} /> Run Diagnosis</>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-dark-400">Filter:</span>
        {['', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((level) => (
          <button
            key={level}
            onClick={() => setRiskFilter(level)}
            className={cn(
              'btn-sm rounded-full',
              riskFilter === level ? 'btn-primary' : 'btn-secondary'
            )}
          >
            {level || 'All'}
          </button>
        ))}
      </div>

      {/* Diagnoses Grid */}
      {diagnoses.length === 0 ? (
        <EmptyState
          icon={Stethoscope}
          title="No diagnoses found"
          description="Run a diagnosis on a vehicle to see results here."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {diagnoses.map((diag) => {
            const riskInfo = RISK_LEVELS[diag.overall_risk_level] || RISK_LEVELS.LOW
            const isSelected = selectedDiagnosis?.diagnosis_id === diag.diagnosis_id

            return (
              <div
                key={diag.diagnosis_id}
                className={cn(
                  'card-hover cursor-pointer',
                  isSelected && 'ring-2 ring-primary-500 border-primary-500',
                )}
                onClick={() => setSelectedDiagnosis(isSelected ? null : diag)}
              >
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className={`p-1.5 rounded-lg ${riskInfo.bgClass}`}>
                      <Stethoscope size={16} className={riskInfo.textClass} />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">{diag.vehicle_id}</p>
                      <p className="text-xs text-dark-500">{diag.diagnosis_id}</p>
                    </div>
                  </div>
                  <StatusBadge
                    status={riskInfo.label}
                    color={riskInfo.color}
                    showDot
                  />
                </div>

                {/* Metrics */}
                <div className="grid grid-cols-2 gap-3 mb-3">
                  <div>
                    <p className="text-xs text-dark-400">Health Score</p>
                    <p className={cn('text-lg font-bold', getHealthColor(diag.health_score))}>
                      {diag.health_score?.toFixed(0) || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-dark-400">Confidence</p>
                    <p className="text-lg font-bold text-white">
                      {diag.confidence_score ? formatPercent(diag.confidence_score * 100) : 'N/A'}
                    </p>
                  </div>
                </div>

                {/* Summary */}
                {diag.summary && (
                  <p className="text-xs text-dark-400 line-clamp-2 mb-3">
                    {diag.summary}
                  </p>
                )}

                {/* Footer */}
                <div className="flex items-center justify-between pt-3 border-t border-dark-700">
                  <div className="flex items-center gap-3 text-xs text-dark-500">
                    {diag.requires_immediate_attention && (
                      <span className="flex items-center gap-1 text-danger-500">
                        <AlertTriangle size={12} /> Urgent
                      </span>
                    )}
                    {diag.service_recommended && (
                      <span className="flex items-center gap-1 text-warning-500">
                        <Target size={12} /> Service Needed
                      </span>
                    )}
                  </div>
                  <span className="text-xs text-dark-500">
                    {formatTimeAgo(diag.created_at)}
                  </span>
                </div>

                {/* Expanded Details */}
                {isSelected && (
                  <div className="mt-4 pt-4 border-t border-dark-700 space-y-3 animate-slide-down">
                    {/* Affected Components */}
                    {diag.affected_components && diag.affected_components.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-dark-300 mb-2">Affected Components</p>
                        <div className="flex flex-wrap gap-1.5">
                          {diag.affected_components.map((comp, idx) => (
                            <span key={idx} className="badge-info">
                              {comp.replace('_', ' ')}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Recommended Actions */}
                    {diag.recommended_actions && diag.recommended_actions.length > 0 && (
                      <div>
                        <p className="text-xs font-medium text-dark-300 mb-2">Recommendations</p>
                        <ul className="space-y-1">
                          {diag.recommended_actions.slice(0, 3).map((action, idx) => (
                            <li key={idx} className="text-xs text-dark-400 flex items-start gap-1.5">
                              <CheckCircle size={12} className="text-primary-400 mt-0.5 flex-shrink-0" />
                              {action}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Failure Info */}
                    {diag.failure_probability > 0 && (
                      <div className="p-2 bg-danger-500/10 rounded-lg">
                        <p className="text-xs text-danger-400">
                          Failure probability: {formatPercent(diag.failure_probability * 100)} •
                          Est. {diag.estimated_days_to_failure || '?'} days to failure
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}