/**
 * Telemetry Page
 * Real-time vehicle telemetry monitoring
 */

import React, { useState, useEffect } from 'react'
import {
  Activity, Thermometer, Battery, Droplets, Disc, Gauge,
  RefreshCw, Zap, Play, Square, AlertTriangle
} from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area
} from 'recharts'
import toast from 'react-hot-toast'

import StatCard from '../components/common/StatCard'
import StatusBadge from '../components/common/StatusBadge'
import { PageLoader } from '../components/common/LoadingSpinner'
import ErrorDisplay from '../components/common/ErrorDisplay'
import EmptyState from '../components/common/EmptyState'

import { telemetryAPI } from '../services/api'
import { formatNumber, formatPercent, getHealthColor } from '../utils/helpers'
import { RISK_LEVELS } from '../utils/constants'

const chartTooltipStyle = {
  backgroundColor: '#1e293b',
  border: '1px solid #334155',
  borderRadius: '8px',
  color: '#f1f5f9',
  fontSize: '12px',
}

export default function TelemetryPage() {
  const [realTimeData, setRealTimeData] = useState(null)
  const [selectedVehicle, setSelectedVehicle] = useState(null)
  const [vehicleData, setVehicleData] = useState(null)
  const [riskAnalysis, setRiskAnalysis] = useState(null)
  const [telemetryHistory, setTelemetryHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isSimulating, setIsSimulating] = useState(false)

  const fetchRealTimeData = async () => {
    try {
      setError(null)
      const result = await telemetryAPI.getRealTime()
      setRealTimeData(result.data)

      // Auto-select first vehicle if none selected
      if (!selectedVehicle && result.data?.vehicles) {
        const vehicleIds = Object.keys(result.data.vehicles)
        if (vehicleIds.length > 0) {
          setSelectedVehicle(vehicleIds[0])
        }
      }
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }

  const fetchVehicleDetails = async (vehicleId) => {
    if (!vehicleId) return
    try {
      const [latestResult, riskResult] = await Promise.allSettled([
        telemetryAPI.getLatest(vehicleId),
        telemetryAPI.getRiskAnalysis(vehicleId),
      ])

      if (latestResult.status === 'fulfilled') {
        setVehicleData(latestResult.value.data)
      }
      if (riskResult.status === 'fulfilled') {
        setRiskAnalysis(riskResult.value.data)
      }
    } catch (err) {
      console.error('Error fetching vehicle details:', err)
    }
  }

  useEffect(() => {
    fetchRealTimeData()
    const interval = setInterval(fetchRealTimeData, 2000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (selectedVehicle) {
      fetchVehicleDetails(selectedVehicle)
    }
  }, [selectedVehicle])

  const handleSimulate = async () => {
    try {
      setIsSimulating(true)
      toast.loading('Simulating telemetry...', { id: 'sim' })
      await telemetryAPI.simulate(10)
      toast.success('Telemetry simulated!', { id: 'sim' })
      await fetchRealTimeData()
    } catch (err) {
      toast.error('Simulation failed', { id: 'sim' })
    } finally {
      setIsSimulating(false)
    }
  }

  const handleSimulateSingle = async () => {
    if (!selectedVehicle) return
    try {
      toast.loading('Generating reading...', { id: 'single' })
      await telemetryAPI.simulateSingle(selectedVehicle)
      toast.success('Reading generated!', { id: 'single' })
      await fetchVehicleDetails(selectedVehicle)
      await fetchRealTimeData()
    } catch (err) {
      toast.error('Failed to generate reading', { id: 'single' })
    }
  }

  if (loading && !realTimeData) {
    return <PageLoader text="Loading telemetry data..." />
  }

  if (error && !realTimeData) {
    return <ErrorDisplay error={error} onRetry={fetchRealTimeData} />
  }

  const vehicles = realTimeData?.vehicles || {}
  const vehicleIds = Object.keys(vehicles)
  const selectedData = selectedVehicle ? vehicles[selectedVehicle] : null

  // Extract metrics from selected vehicle data
  const engineTemp = selectedData?.engine_temperature?.latest
  const batteryVoltage = selectedData?.battery_voltage?.latest
  const oilLevel = selectedData?.oil_level?.latest
  const fuelLevel = selectedData?.fuel_level?.latest
  const brakeWearFront = selectedData?.brake_wear?.front
  const brakeWearRear = selectedData?.brake_wear?.rear
  const speed = selectedData?.speed?.latest

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">Telemetry Monitoring</h1>
          <p className="page-subtitle">
            Real-time vehicle sensor data • {vehicleIds.length} vehicles tracked
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={handleSimulate} disabled={isSimulating} className="btn-secondary btn-sm">
            <Zap size={14} />
            Simulate Fleet
          </button>
          <button onClick={handleSimulateSingle} disabled={!selectedVehicle} className="btn-primary btn-sm">
            <Play size={14} />
            Generate Reading
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Vehicle Selector Panel */}
        <div className="lg:col-span-1">
          <div className="card max-h-[600px] overflow-y-auto">
            <h3 className="section-title">Vehicles ({vehicleIds.length})</h3>
            {vehicleIds.length === 0 ? (
              <EmptyState
                icon={Activity}
                title="No data"
                description="Simulate telemetry to see data."
                action={handleSimulate}
                actionLabel="Simulate"
              />
            ) : (
              <div className="space-y-2">
                {vehicleIds.map((id) => {
                  const vData = vehicles[id]
                  const healthScore = vData?.engine_temperature?.latest < 100 ? 85 : 55
                  const isSelected = selectedVehicle === id

                  return (
                    <button
                      key={id}
                      onClick={() => setSelectedVehicle(id)}
                      className={`w-full text-left p-3 rounded-lg transition-all ${
                        isSelected
                          ? 'bg-primary-600/10 border border-primary-500/30'
                          : 'hover:bg-dark-700/50 border border-transparent'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-white">{id}</span>
                        <div className={`w-2 h-2 rounded-full ${
                          healthScore >= 80 ? 'bg-success-500' : healthScore >= 50 ? 'bg-warning-500' : 'bg-danger-500'
                        }`} />
                      </div>
                      <p className="text-xs text-dark-400 mt-0.5">
                        {vData?.reading_count || 0} readings
                      </p>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        </div>

        {/* Telemetry Data Panel */}
        <div className="lg:col-span-3 space-y-6">
          {!selectedVehicle ? (
            <div className="card">
              <EmptyState
                icon={Activity}
                title="Select a vehicle"
                description="Choose a vehicle from the list to view telemetry data."
              />
            </div>
          ) : (
            <>
              {/* Risk Analysis Banner */}
              {riskAnalysis && riskAnalysis.overall_risk_level !== 'LOW' && (
                <div className={`p-4 rounded-xl border flex items-center gap-3 ${
                  riskAnalysis.overall_risk_level === 'CRITICAL'
                    ? 'bg-danger-500/10 border-danger-500/30'
                    : riskAnalysis.overall_risk_level === 'HIGH'
                    ? 'bg-orange-500/10 border-orange-500/30'
                    : 'bg-warning-500/10 border-warning-500/30'
                }`}>
                  <AlertTriangle size={20} className={
                    riskAnalysis.overall_risk_level === 'CRITICAL' ? 'text-danger-500' : 'text-warning-500'
                  } />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-white">
                      Risk Level: {riskAnalysis.overall_risk_level}
                    </p>
                    <p className="text-xs text-dark-400">
                      {riskAnalysis.risk_indicators?.length || 0} risk indicators detected
                    </p>
                  </div>
                  <StatusBadge
                    status={riskAnalysis.overall_risk_level}
                    color={RISK_LEVELS[riskAnalysis.overall_risk_level]?.color || 'neutral'}
                    showDot
                    size="lg"
                  />
                </div>
              )}

              {/* Metric Cards */}
              <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
                <StatCard
                  title="Engine Temp"
                  value={engineTemp ? `${engineTemp.toFixed(1)}°C` : 'N/A'}
                  icon={Thermometer}
                  color={engineTemp > 100 ? 'danger' : engineTemp > 90 ? 'warning' : 'success'}
                />
                <StatCard
                  title="Battery"
                  value={batteryVoltage ? `${batteryVoltage.toFixed(1)}V` : 'N/A'}
                  icon={Battery}
                  color={batteryVoltage && batteryVoltage < 12 ? 'danger' : 'success'}
                />
                <StatCard
                  title="Oil Level"
                  value={oilLevel ? formatPercent(oilLevel) : 'N/A'}
                  icon={Droplets}
                  color={oilLevel && oilLevel < 30 ? 'danger' : oilLevel && oilLevel < 50 ? 'warning' : 'success'}
                />
                <StatCard
                  title="Brake Wear (F)"
                  value={brakeWearFront ? formatPercent(brakeWearFront) : 'N/A'}
                  icon={Disc}
                  color={brakeWearFront && brakeWearFront > 80 ? 'danger' : brakeWearFront && brakeWearFront > 60 ? 'warning' : 'success'}
                />
                <StatCard
                  title="Brake Wear (R)"
                  value={brakeWearRear ? formatPercent(brakeWearRear) : 'N/A'}
                  icon={Disc}
                  color={brakeWearRear && brakeWearRear > 80 ? 'danger' : brakeWearRear && brakeWearRear > 60 ? 'warning' : 'success'}
                />
                <StatCard
                  title="Fuel Level"
                  value={fuelLevel ? formatPercent(fuelLevel) : 'N/A'}
                  icon={Gauge}
                  color={fuelLevel && fuelLevel < 15 ? 'danger' : fuelLevel && fuelLevel < 30 ? 'warning' : 'success'}
                />
                <StatCard
                  title="Speed"
                  value={speed !== undefined ? `${speed.toFixed(0)} km/h` : 'N/A'}
                  icon={Gauge}
                  color="primary"
                />
                <StatCard
                  title="Health Score"
                  value={riskAnalysis?.health_score ? riskAnalysis.health_score.toFixed(0) : 'N/A'}
                  icon={Activity}
                  color={riskAnalysis?.health_score >= 80 ? 'success' : riskAnalysis?.health_score >= 50 ? 'warning' : 'danger'}
                />
              </div>

              {/* Risk Indicators */}
              {riskAnalysis?.risk_indicators && riskAnalysis.risk_indicators.length > 0 && (
                <div className="card">
                  <h3 className="section-title">Risk Indicators</h3>
                  <div className="space-y-2">
                    {riskAnalysis.risk_indicators.map((indicator, idx) => {
                      const riskInfo = RISK_LEVELS[indicator.risk_level] || RISK_LEVELS.LOW

                      return (
                        <div key={idx} className="flex items-center gap-3 p-3 bg-dark-700/30 rounded-lg">
                          <div className={`w-2 h-2 rounded-full ${riskInfo.dotClass}`} />
                          <div className="flex-1">
                            <p className="text-sm text-white">{indicator.component}</p>
                            <p className="text-xs text-dark-400">{indicator.message}</p>
                          </div>
                          <StatusBadge status={riskInfo.label} color={riskInfo.color} />
                          <span className="text-sm font-mono text-dark-300">
                            {indicator.value?.toFixed(1)}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {riskAnalysis?.recommended_actions && riskAnalysis.recommended_actions.length > 0 && (
                <div className="card">
                  <h3 className="section-title">Recommended Actions</h3>
                  <ul className="space-y-2">
                    {riskAnalysis.recommended_actions.map((action, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-dark-300">
                        <span className="text-primary-400 mt-0.5">→</span>
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}