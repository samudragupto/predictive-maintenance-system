/**
 * Vehicles Page
 * Fleet vehicle management and monitoring
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  Car, Plus, Search, Filter, RefreshCw, ChevronLeft,
  ChevronRight, Stethoscope, Calendar, DollarSign,
  Activity, MoreVertical
} from 'lucide-react'
import toast from 'react-hot-toast'

import StatusBadge from '../components/common/StatusBadge'
import EmptyState from '../components/common/EmptyState'
import { PageLoader } from '../components/common/LoadingSpinner'
import ErrorDisplay from '../components/common/ErrorDisplay'

import { vehicleAPI, diagnosisAPI, telemetryAPI } from '../services/api'
import {
  formatDate, formatNumber, getHealthColor,
  getHealthBg, getStatusBadge, formatPercent
} from '../utils/helpers'
import { HEALTH_STATUS, VEHICLE_STATUS } from '../utils/constants'

export default function VehiclesPage() {
  const [vehicles, setVehicles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [healthFilter, setHealthFilter] = useState('')

  const fetchVehicles = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await vehicleAPI.list({
        page,
        page_size: 15,
        search: search || undefined,
        status: statusFilter || undefined,
        health_status: healthFilter || undefined,
        sort_by: 'health_score',
        sort_order: 'asc',
      })
      setVehicles(result.data || [])
      setTotalPages(result.total_pages || 1)
      setTotal(result.total || 0)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [page, search, statusFilter, healthFilter])

  useEffect(() => {
    fetchVehicles()
  }, [fetchVehicles])

  const handleSearch = (e) => {
    setSearch(e.target.value)
    setPage(1)
  }

  const handleDiagnose = async (vehicleId) => {
    try {
      toast.loading('Running diagnosis...', { id: 'diagnose' })
      await diagnosisAPI.create(vehicleId, 'MANUAL')
      toast.success('Diagnosis complete!', { id: 'diagnose' })
      fetchVehicles()
    } catch (err) {
      toast.error('Diagnosis failed', { id: 'diagnose' })
    }
  }

  const handleSimulateTelemetry = async (vehicleId) => {
    try {
      toast.loading('Generating telemetry...', { id: 'telemetry' })
      await telemetryAPI.simulateSingle(vehicleId)
      toast.success('Telemetry generated!', { id: 'telemetry' })
      fetchVehicles()
    } catch (err) {
      toast.error('Telemetry simulation failed', { id: 'telemetry' })
    }
  }

  if (loading && vehicles.length === 0) {
    return <PageLoader text="Loading vehicles..." />
  }

  if (error && vehicles.length === 0) {
    return <ErrorDisplay error={error} onRetry={fetchVehicles} />
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">Vehicle Fleet</h1>
          <p className="page-subtitle">{total} vehicles in fleet</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={fetchVehicles} className="btn-secondary btn-sm">
            <RefreshCw size={14} />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col md:flex-row gap-4">
          {/* Search */}
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
            <input
              type="text"
              placeholder="Search by ID, VIN, make, model..."
              value={search}
              onChange={handleSearch}
              className="input pl-10"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
            className="input w-full md:w-44"
          >
            <option value="">All Status</option>
            {Object.entries(VEHICLE_STATUS).map(([key, val]) => (
              <option key={key} value={key}>{val.label}</option>
            ))}
          </select>

          {/* Health Filter */}
          <select
            value={healthFilter}
            onChange={(e) => { setHealthFilter(e.target.value); setPage(1) }}
            className="input w-full md:w-44"
          >
            <option value="">All Health</option>
            {Object.entries(HEALTH_STATUS).map(([key, val]) => (
              <option key={key} value={key}>{val.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Vehicles Table */}
      {vehicles.length === 0 ? (
        <EmptyState
          icon={Car}
          title="No vehicles found"
          description="Try adjusting your search or filters."
        />
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Vehicle</th>
                <th>Make / Model</th>
                <th>Status</th>
                <th>Health</th>
                <th>Health Score</th>
                <th>Mileage</th>
                <th>Last Service</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {vehicles.map((vehicle) => {
                const healthInfo = HEALTH_STATUS[vehicle.health_status] || HEALTH_STATUS.UNKNOWN
                const statusInfo = VEHICLE_STATUS[vehicle.status] || VEHICLE_STATUS.ACTIVE

                return (
                  <tr key={vehicle.vehicle_id}>
                    <td>
                      <div>
                        <p className="font-medium text-white">{vehicle.vehicle_id}</p>
                        <p className="text-xs text-dark-500">{vehicle.vin}</p>
                      </div>
                    </td>
                    <td>
                      <p className="text-dark-200">{vehicle.make} {vehicle.model}</p>
                      <p className="text-xs text-dark-500">{vehicle.year}</p>
                    </td>
                    <td>
                      <StatusBadge status={statusInfo.label} color={statusInfo.color} />
                    </td>
                    <td>
                      <StatusBadge
                        status={healthInfo.label}
                        color={healthInfo.color}
                        showDot
                      />
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 bg-dark-700 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${getHealthBg(vehicle.health_score)}`}
                            style={{ width: `${vehicle.health_score}%` }}
                          />
                        </div>
                        <span className={`text-sm font-medium ${getHealthColor(vehicle.health_score)}`}>
                          {vehicle.health_score?.toFixed(0)}
                        </span>
                      </div>
                    </td>
                    <td className="text-dark-300">
                      {formatNumber(vehicle.current_mileage_km)} km
                    </td>
                    <td className="text-dark-400 text-xs">
                      {formatDate(vehicle.last_service_date)}
                    </td>
                    <td>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleDiagnose(vehicle.vehicle_id)}
                          className="p-1.5 rounded-lg text-dark-400 hover:text-primary-400 hover:bg-primary-500/10 transition-colors"
                          title="Run Diagnosis"
                        >
                          <Stethoscope size={16} />
                        </button>
                        <button
                          onClick={() => handleSimulateTelemetry(vehicle.vehicle_id)}
                          className="p-1.5 rounded-lg text-dark-400 hover:text-success-500 hover:bg-success-500/10 transition-colors"
                          title="Simulate Telemetry"
                        >
                          <Activity size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-dark-400">
            Showing {(page - 1) * 15 + 1}-{Math.min(page * 15, total)} of {total}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn-secondary btn-sm"
            >
              <ChevronLeft size={14} />
              Previous
            </button>
            <span className="text-sm text-dark-400">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="btn-secondary btn-sm"
            >
              Next
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}