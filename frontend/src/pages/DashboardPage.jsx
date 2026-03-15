/**
 * Dashboard Page
 * Main OEM Operations Dashboard
 */

import React, { useState, useEffect } from 'react'
import { RefreshCw, Zap, Clock } from 'lucide-react'
import toast from 'react-hot-toast'

import FleetOverview from '../components/dashboard/FleetOverview'
import HealthScoreChart from '../components/dashboard/HealthScoreChart'
import RecentDiagnoses from '../components/dashboard/RecentDiagnoses'
import UpcomingAppointments from '../components/dashboard/UpcomingAppointments'
import AlertsSummary from '../components/dashboard/AlertsSummary'
import VehiclesAtRisk from '../components/dashboard/VehiclesAtRisk'
import { PageLoader } from '../components/common/LoadingSpinner'
import ErrorDisplay from '../components/common/ErrorDisplay'

import { dashboardAPI, telemetryAPI } from '../services/api'
import { formatDateTime } from '../utils/helpers'

export default function DashboardPage() {
  const [dashboardData, setDashboardData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetchDashboard = async () => {
    try {
      setError(null)
      const result = await dashboardAPI.getMain()
      setDashboardData(result.data)
      setLastRefresh(new Date())
    } catch (err) {
      setError(err)
      console.error('Dashboard fetch error:', err)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchDashboard()

    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchDashboard, 5000)
    return () => clearInterval(interval)
  }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    await fetchDashboard()
    toast.success('Dashboard refreshed')
  }

  const handleSimulate = async () => {
    try {
      toast.loading('Generating telemetry data...', { id: 'simulate' })
      await telemetryAPI.simulate(10)
      toast.success('Telemetry simulation complete!', { id: 'simulate' })
      await fetchDashboard()
    } catch (err) {
      toast.error('Simulation failed', { id: 'simulate' })
    }
  }

  if (loading && !dashboardData) {
    return <PageLoader text="Loading dashboard..." />
  }

  if (error && !dashboardData) {
    return <ErrorDisplay error={error} onRetry={fetchDashboard} />
  }

  const data = dashboardData || {}

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">Operations Dashboard</h1>
          <p className="page-subtitle">
            Real-time fleet monitoring and predictive maintenance overview
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastRefresh && (
            <span className="text-xs text-dark-500 flex items-center gap-1">
              <Clock size={12} />
              Updated {formatDateTime(lastRefresh)}
            </span>
          )}
          <button
            onClick={handleSimulate}
            className="btn-secondary btn-sm"
          >
            <Zap size={14} />
            Simulate Data
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="btn-primary btn-sm"
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Fleet Overview Stats */}
      <FleetOverview data={data.fleet_overview} loading={loading} />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - 2/3 width */}
        <div className="lg:col-span-2 space-y-6">
          <RecentDiagnoses data={data.recent_diagnoses} loading={loading} />
          <UpcomingAppointments data={data.upcoming_appointments} loading={loading} />
        </div>

        {/* Right Column - 1/3 width */}
        <div className="space-y-6">
          <HealthScoreChart data={data.fleet_overview} />
          <AlertsSummary
            summary={data.alert_summary}
            recentAlerts={data.recent_alerts}
            loading={loading}
          />
          <VehiclesAtRisk data={data.vehicles_needing_service} loading={loading} />
        </div>
      </div>

      {/* Real-Time Indicator */}
      <div className="flex items-center justify-center gap-2 py-4">
        <div className="w-2 h-2 bg-success-500 rounded-full animate-pulse" />
        <span className="text-xs text-dark-500">
          Live monitoring • {data.real_time_vehicles || 0} vehicles tracked
        </span>
      </div>
    </div>
  )
}