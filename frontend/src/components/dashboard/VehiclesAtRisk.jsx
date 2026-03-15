/**
 * VehiclesAtRisk Component
 * Shows vehicles that need immediate attention
 */

import React from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, ChevronRight, ArrowRight } from 'lucide-react'
import StatusBadge from '../common/StatusBadge'
import EmptyState from '../common/EmptyState'
import { getHealthColor, formatNumber } from '../../utils/helpers'
import { HEALTH_STATUS } from '../../utils/constants'

export default function VehiclesAtRisk({ data, loading }) {
  const navigate = useNavigate()

  if (loading) {
    return (
      <div className="card animate-pulse">
        <div className="h-5 bg-dark-700 rounded w-1/3 mb-4" />
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-14 bg-dark-700 rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  const vehicles = data || []

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-title mb-0">Vehicles Needing Service</h3>
        <button
          onClick={() => navigate('/vehicles')}
          className="btn-ghost btn-sm"
        >
          View All <ChevronRight size={14} />
        </button>
      </div>

      {vehicles.length === 0 ? (
        <EmptyState
          icon={AlertTriangle}
          title="All vehicles healthy"
          description="No vehicles currently require service."
        />
      ) : (
        <div className="space-y-2">
          {vehicles.slice(0, 6).map((vehicle) => {
            const healthInfo = HEALTH_STATUS[vehicle.health_status] || HEALTH_STATUS.UNKNOWN

            return (
              <div
                key={vehicle.vehicle_id}
                className="flex items-center gap-3 p-3 rounded-lg hover:bg-dark-700/50 transition-colors cursor-pointer group"
                onClick={() => navigate('/vehicles')}
              >
                <div className="flex-shrink-0">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    vehicle.health_status === 'CRITICAL' ? 'bg-danger-500/20' : 'bg-warning-500/20'
                  }`}>
                    <span className="text-lg">{healthInfo.icon}</span>
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-white">{vehicle.vehicle_id}</p>
                    <StatusBadge
                      status={healthInfo.label}
                      color={healthInfo.color}
                    />
                  </div>
                  <p className="text-xs text-dark-400">
                    {vehicle.make} {vehicle.model} {vehicle.year} • Score: {' '}
                    <span className={getHealthColor(vehicle.health_score)}>
                      {vehicle.health_score?.toFixed(0)}
                    </span>
                  </p>
                </div>
                <ArrowRight size={16} className="text-dark-500 group-hover:text-primary-400 transition-colors" />
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}