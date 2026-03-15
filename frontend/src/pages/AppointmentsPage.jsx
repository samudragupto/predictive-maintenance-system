/**
 * Appointments Page
 * Service appointment scheduling and management
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  Calendar, RefreshCw, Plus, Clock, MapPin,
  CheckCircle, XCircle, Search, Filter
} from 'lucide-react'
import toast from 'react-hot-toast'

import StatusBadge from '../components/common/StatusBadge'
import EmptyState from '../components/common/EmptyState'
import { PageLoader } from '../components/common/LoadingSpinner'
import ErrorDisplay from '../components/common/ErrorDisplay'

import { appointmentAPI, vehicleAPI } from '../services/api'
import { formatDateTime } from '../utils/helpers'
import { APPOINTMENT_STATUS } from '../utils/constants'

export default function AppointmentsPage() {
  const [appointments, setAppointments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [vehicles, setVehicles] = useState([])
  const [selectedVehicle, setSelectedVehicle] = useState('')
  const [scheduling, setScheduling] = useState(false)

  const fetchAppointments = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await appointmentAPI.list({
        page: 1,
        page_size: 50,
        status: statusFilter || undefined,
        vehicle_id: selectedVehicle || undefined,
      })
      setAppointments(result.data || [])
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [statusFilter, selectedVehicle])

  const fetchVehicles = async () => {
    try {
      const result = await vehicleAPI.list({ page: 1, page_size: 100 })
      setVehicles(result.data || [])
    } catch (err) {
      console.error('Error fetching vehicles:', err)
    }
  }

  useEffect(() => {
    fetchAppointments()
    fetchVehicles()
  }, [fetchAppointments])

  const handleAutoSchedule = async () => {
    if (!selectedVehicle) {
      toast.error('Please select a vehicle to schedule')
      return
    }
    try {
      setScheduling(true)
      toast.loading('Finding optimal slot...', { id: 'schedule' })
      await appointmentAPI.autoSchedule(selectedVehicle, 'MEDIUM')
      toast.success('Appointment scheduled!', { id: 'schedule' })
      await fetchAppointments()
    } catch (err) {
      toast.error('Scheduling failed', { id: 'schedule' })
    } finally {
      setScheduling(false)
    }
  }

  const handleStatusUpdate = async (id, status) => {
    try {
      await appointmentAPI.updateStatus(id, status)
      toast.success(`Status updated to ${status}`)
      fetchAppointments()
    } catch (err) {
      toast.error('Update failed')
    }
  }

  if (loading && appointments.length === 0) {
    return <PageLoader text="Loading appointments..." />
  }

  if (error && appointments.length === 0) {
    return <ErrorDisplay error={error} onRetry={fetchAppointments} />
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">Service Appointments</h1>
          <p className="page-subtitle">Manage service schedule and technician assignments</p>
        </div>
        <button onClick={fetchAppointments} className="btn-secondary btn-sm">
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Scheduler Panel */}
      <div className="card bg-gradient-to-r from-primary-600/10 to-primary-800/5 border-primary-500/20">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-500/20 rounded-lg">
              <Calendar size={24} className="text-primary-400" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Smart Scheduler</h3>
              <p className="text-xs text-dark-400">AI-optimized appointment booking</p>
            </div>
          </div>
          <div className="flex items-center gap-3 flex-1 sm:justify-end">
            <select
              value={selectedVehicle}
              onChange={(e) => setSelectedVehicle(e.target.value)}
              className="input w-52"
            >
              <option value="">Select Vehicle...</option>
              {vehicles.map((v) => (
                <option key={v.vehicle_id} value={v.vehicle_id}>
                  {v.vehicle_id} - {v.make}
                </option>
              ))}
            </select>
            <button
              onClick={handleAutoSchedule}
              disabled={scheduling || !selectedVehicle}
              className="btn-primary"
            >
              {scheduling ? (
                <><RefreshCw size={14} className="animate-spin" /> Scheduling...</>
              ) : (
                <><Plus size={14} /> Auto-Schedule</>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 overflow-x-auto pb-2">
        <span className="text-sm text-dark-400 whitespace-nowrap">Filter:</span>
        <button
          onClick={() => setStatusFilter('')}
          className={`btn-sm rounded-full whitespace-nowrap ${!statusFilter ? 'btn-primary' : 'btn-secondary'}`}
        >
          All
        </button>
        {Object.keys(APPOINTMENT_STATUS).map((status) => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            className={`btn-sm rounded-full whitespace-nowrap ${statusFilter === status ? 'btn-primary' : 'btn-secondary'}`}
          >
            {APPOINTMENT_STATUS[status].label}
          </button>
        ))}
      </div>

      {/* Appointments Grid */}
      {appointments.length === 0 ? (
        <EmptyState
          icon={Calendar}
          title="No appointments found"
          description="Try adjusting your filters or schedule a new appointment."
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {appointments.map((apt) => {
            const statusInfo = APPOINTMENT_STATUS[apt.status] || APPOINTMENT_STATUS.PENDING

            return (
              <div key={apt.appointment_id} className="card hover:border-dark-600 transition-colors">
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <p className="text-sm font-bold text-white">{apt.vehicle_id}</p>
                    <p className="text-xs text-dark-400 mt-0.5">{apt.appointment_id}</p>
                  </div>
                  <StatusBadge status={statusInfo.label} color={statusInfo.color} />
                </div>

                {/* Details */}
                <div className="space-y-3 mb-4">
                  <div className="flex items-center gap-2 text-sm text-dark-300">
                    <Calendar size={14} className="text-primary-400" />
                    {formatDateTime(apt.scheduled_date)}
                  </div>
                  <div className="flex items-center gap-2 text-sm text-dark-300">
                    <Clock size={14} className="text-primary-400" />
                    {apt.estimated_duration_minutes} minutes
                  </div>
                  {apt.service_center_id && (
                    <div className="flex items-center gap-2 text-sm text-dark-300">
                      <MapPin size={14} className="text-primary-400" />
                      Center #{apt.service_center_id}
                    </div>
                  )}
                </div>

                {/* Description */}
                {apt.service_description && (
                  <p className="text-xs text-dark-400 mb-4 line-clamp-2 bg-dark-700/30 p-2 rounded">
                    {apt.service_description}
                  </p>
                )}

                {/* Actions */}
                <div className="flex items-center justify-between pt-3 border-t border-dark-700">
                  {apt.ai_scheduled && (
                    <span className="text-xs text-primary-400 font-medium">🤖 AI Scheduled</span>
                  )}
                  
                  {apt.status !== 'COMPLETED' && apt.status !== 'CANCELLED' && (
                    <div className="flex gap-2 ml-auto">
                      <button
                        onClick={() => handleStatusUpdate(apt.appointment_id, 'COMPLETED')}
                        className="p-1.5 rounded bg-success-500/10 text-success-500 hover:bg-success-500/20"
                        title="Mark Complete"
                      >
                        <CheckCircle size={16} />
                      </button>
                      <button
                        onClick={() => handleStatusUpdate(apt.appointment_id, 'CANCELLED')}
                        className="p-1.5 rounded bg-danger-500/10 text-danger-500 hover:bg-danger-500/20"
                        title="Cancel"
                      >
                        <XCircle size={16} />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}