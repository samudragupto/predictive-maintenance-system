/**
 * UpcomingAppointments Component
 * List of upcoming service appointments
 */

import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Calendar, ChevronRight, Clock, MapPin } from 'lucide-react'
import StatusBadge from '../common/StatusBadge'
import EmptyState from '../common/EmptyState'
import { formatDateTime } from '../../utils/helpers'
import { APPOINTMENT_STATUS } from '../../utils/constants'

export default function UpcomingAppointments({ data, loading }) {
  const navigate = useNavigate()

  if (loading) {
    return (
      <div className="card">
        <h3 className="section-title">Upcoming Appointments</h3>
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="p-3 bg-dark-700/30 rounded-lg animate-pulse">
              <div className="h-4 bg-dark-700 rounded w-1/3 mb-2" />
              <div className="h-3 bg-dark-700 rounded w-1/2 mb-1" />
              <div className="h-3 bg-dark-700 rounded w-1/4" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  const appointments = data || []

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="section-title mb-0">Upcoming Appointments</h3>
        <button
          onClick={() => navigate('/appointments')}
          className="btn-ghost btn-sm"
        >
          View All <ChevronRight size={14} />
        </button>
      </div>

      {appointments.length === 0 ? (
        <EmptyState
          icon={Calendar}
          title="No upcoming appointments"
          description="Schedule a service appointment to see it here."
        />
      ) : (
        <div className="space-y-3">
          {appointments.slice(0, 6).map((apt) => {
            const statusInfo = APPOINTMENT_STATUS[apt.status] || APPOINTMENT_STATUS.PENDING

            return (
              <div
                key={apt.appointment_id}
                className="p-3 bg-dark-700/30 rounded-lg hover:bg-dark-700/50 transition-colors cursor-pointer"
                onClick={() => navigate('/appointments')}
              >
                <div className="flex items-start justify-between mb-2">
                  <p className="text-sm font-medium text-white">{apt.vehicle_id}</p>
                  <StatusBadge status={statusInfo.label} color={statusInfo.color} />
                </div>
                <div className="flex items-center gap-4 text-xs text-dark-400">
                  <div className="flex items-center gap-1">
                    <Calendar size={12} />
                    <span>{formatDateTime(apt.scheduled_date)}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock size={12} />
                    <span>{apt.estimated_duration_minutes}min</span>
                  </div>
                </div>
                {apt.service_description && (
                  <p className="text-xs text-dark-500 mt-1 truncate">{apt.service_description}</p>
                )}
                {apt.ai_scheduled && (
                  <span className="inline-flex items-center gap-1 mt-1 text-xs text-primary-400">
                    🤖 AI Scheduled
                  </span>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}