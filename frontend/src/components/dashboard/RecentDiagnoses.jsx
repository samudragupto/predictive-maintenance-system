/**
 * RecentDiagnoses Component
 * Table of recent AI diagnoses
 */

import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Stethoscope, ChevronRight } from 'lucide-react'
import StatusBadge from '../common/StatusBadge'
import EmptyState from '../common/EmptyState'
import { formatTimeAgo, formatPercent } from '../../utils/helpers'
import { RISK_LEVELS } from '../../utils/constants'

export default function RecentDiagnoses({ data, loading }) {
  const navigate = useNavigate()

  if (loading) {
    return (
      <div className="card">
        <h3 className="section-title">Recent Diagnoses</h3>
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center gap-4 animate-pulse">
              <div className="w-10 h-10 bg-dark-700 rounded-lg" />
              <div className="flex-1">
                <div className="h-4 bg-dark-700 rounded w-1/3 mb-2" />
                <div className="h-3 bg-dark-700 rounded w-1/2" />
              </div>
              <div className="h-6 w-16 bg-dark-700 rounded-full" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  const diagnoses = data || []

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-title mb-0">Recent Diagnoses</h3>
        <button
          onClick={() => navigate('/diagnoses')}
          className="btn-ghost btn-sm"
        >
          View All <ChevronRight size={14} />
        </button>
      </div>

      {diagnoses.length === 0 ? (
        <EmptyState
          icon={Stethoscope}
          title="No diagnoses yet"
          description="Run a diagnosis on a vehicle to see results here."
        />
      ) : (
        <div className="space-y-3">
          {diagnoses.slice(0, 8).map((diag) => {
            const riskInfo = RISK_LEVELS[diag.overall_risk_level] || RISK_LEVELS.LOW

            return (
              <div
                key={diag.diagnosis_id}
                className="flex items-center gap-4 p-3 rounded-lg hover:bg-dark-700/50 transition-colors cursor-pointer"
                onClick={() => navigate(`/diagnoses`)}
              >
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${riskInfo.bgClass}`}>
                  <Stethoscope size={18} className={riskInfo.textClass} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">
                    {diag.vehicle_id}
                  </p>
                  <p className="text-xs text-dark-400 truncate">
                    {diag.summary ? diag.summary.substring(0, 60) + '...' : 'Diagnosis completed'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge
                    status={riskInfo.label}
                    color={riskInfo.color}
                    showDot
                  />
                  <span className="text-xs text-dark-500">
                    {formatTimeAgo(diag.created_at)}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}