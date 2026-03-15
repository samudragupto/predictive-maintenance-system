/**
 * Behavior Page
 * Driver behavior analysis and scoring
 */

import React, { useState, useEffect } from 'react'
import {
  UserCheck, RefreshCw, TrendingUp, AlertOctagon,
  Award, Gauge, ChevronRight
} from 'lucide-react'
import {
  Radar, RadarChart, PolarGrid, PolarAngleAxis, 
  PolarRadiusAxis, ResponsiveContainer, Tooltip
} from 'recharts'
import toast from 'react-hot-toast'

import StatCard from '../components/common/StatCard'
import EmptyState from '../components/common/EmptyState'
import { PageLoader } from '../components/common/LoadingSpinner'
import ErrorDisplay from '../components/common/ErrorDisplay'

import { behaviorAPI, vehicleAPI } from '../services/api'

export default function BehaviorPage() {
  const [vehicles, setVehicles] = useState([])
  const [selectedVehicle, setSelectedVehicle] = useState(null)
  const [behaviorData, setBehaviorData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    const init = async () => {
      try {
        const vResult = await vehicleAPI.list({ page: 1, page_size: 50 })
        setVehicles(vResult.data || [])
        
        if (vResult.data?.length > 0) {
          const firstId = vResult.data[0].vehicle_id
          setSelectedVehicle(firstId)
          await fetchBehavior(firstId)
        }
      } catch (err) {
        setError(err)
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  const fetchBehavior = async (vehicleId) => {
    try {
      setAnalyzing(true)
      // Try to get existing data first
      let result = await behaviorAPI.get(vehicleId)
      
      // If no data, run analysis
      if (!result.data) {
        result = await behaviorAPI.analyze(vehicleId)
      }
      
      setBehaviorData(result.data)
    } catch (err) {
      console.error('Behavior fetch error:', err)
      setBehaviorData(null)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleAnalyze = async () => {
    if (!selectedVehicle) return
    try {
      setAnalyzing(true)
      toast.loading('Analyzing driving patterns...', { id: 'behavior' })
      const result = await behaviorAPI.analyze(selectedVehicle)
      setBehaviorData(result.data)
      toast.success('Analysis complete!', { id: 'behavior' })
    } catch (err) {
      toast.error('Analysis failed', { id: 'behavior' })
    } finally {
      setAnalyzing(false)
    }
  }

  if (loading) return <PageLoader text="Loading driver insights..." />
  if (error) return <ErrorDisplay error={error} />

  const chartData = behaviorData ? [
    { subject: 'Speed', A: behaviorData.category_scores?.speed || 0, fullMark: 100 },
    { subject: 'Braking', A: behaviorData.category_scores?.braking || 0, fullMark: 100 },
    { subject: 'Accel', A: behaviorData.category_scores?.acceleration || 0, fullMark: 100 },
    { subject: 'Cornering', A: behaviorData.category_scores?.cornering || 0, fullMark: 100 },
    { subject: 'Safety', A: behaviorData.category_scores?.safety || 0, fullMark: 100 },
    { subject: 'Eco', A: behaviorData.category_scores?.fuel_efficiency || 0, fullMark: 100 },
  ] : []

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">Driver Behavior</h1>
          <p className="page-subtitle">Driving pattern analysis and safety scoring</p>
        </div>
        <div className="flex items-center gap-3">
          <select 
            value={selectedVehicle || ''} 
            onChange={(e) => {
              setSelectedVehicle(e.target.value)
              fetchBehavior(e.target.value)
            }}
            className="input w-48"
          >
            {vehicles.map(v => (
              <option key={v.vehicle_id} value={v.vehicle_id}>{v.vehicle_id}</option>
            ))}
          </select>
          <button 
            onClick={handleAnalyze} 
            disabled={analyzing || !selectedVehicle}
            className="btn-primary btn-sm"
          >
            <RefreshCw size={14} className={analyzing ? 'animate-spin' : ''} />
            Analyze
          </button>
        </div>
      </div>

      {!behaviorData ? (
        <div className="card">
          <EmptyState
            icon={UserCheck}
            title="No behavior data"
            description="Run analysis to see driver insights."
            action={handleAnalyze}
            actionLabel="Run Analysis"
          />
        </div>
      ) : (
        <>
          {/* Score Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              title="Overall Score"
              value={behaviorData.overall_score}
              subtitle={`Rating: ${behaviorData.rating}`}
              icon={Award}
              color={behaviorData.overall_score >= 80 ? 'success' : 'warning'}
            />
            <StatCard
              title="Risk Score"
              value={behaviorData.risk_score}
              subtitle="Accident probability factor"
              icon={AlertOctagon}
              color={behaviorData.risk_score < 20 ? 'success' : 'danger'}
            />
            <StatCard
              title="Distance"
              value={`${behaviorData.statistics?.distance_km} km`}
              subtitle="Analyzed distance"
              icon={TrendingUp}
              color="primary"
            />
            <StatCard
              title="Events"
              value={behaviorData.events?.total || 0}
              subtitle="Harsh driving events"
              icon={Gauge}
              color="warning"
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Radar Chart */}
            <div className="card flex flex-col items-center justify-center min-h-[400px]">
              <h3 className="section-title w-full text-left">Behavior Profile</h3>
              <div className="w-full h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartData}>
                    <PolarGrid stroke="#334155" />
                    <PolarAngleAxis dataKey="subject" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                    <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                    <Radar
                      name="Score"
                      dataKey="A"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      fill="#3b82f6"
                      fillOpacity={0.3}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f1f5f9' }}
                      itemStyle={{ color: '#60a5fa' }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Recommendations */}
            <div className="lg:col-span-2 space-y-6">
              {/* Event Breakdown */}
              <div className="card">
                <h3 className="section-title">Event Breakdown</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-3 bg-dark-700/30 rounded-lg text-center">
                    <p className="text-2xl font-bold text-white">{behaviorData.events?.harsh_acceleration || 0}</p>
                    <p className="text-xs text-dark-400">Harsh Accel</p>
                  </div>
                  <div className="p-3 bg-dark-700/30 rounded-lg text-center">
                    <p className="text-2xl font-bold text-white">{behaviorData.events?.harsh_braking || 0}</p>
                    <p className="text-xs text-dark-400">Harsh Braking</p>
                  </div>
                  <div className="p-3 bg-dark-700/30 rounded-lg text-center">
                    <p className="text-2xl font-bold text-white">{behaviorData.events?.speeding || 0}</p>
                    <p className="text-xs text-dark-400">Speeding</p>
                  </div>
                  <div className="p-3 bg-dark-700/30 rounded-lg text-center">
                    <p className="text-2xl font-bold text-white">{behaviorData.statistics?.max_speed || 0}</p>
                    <p className="text-xs text-dark-400">Max Speed (km/h)</p>
                  </div>
                </div>
              </div>

              {/* Insights List */}
              <div className="card">
                <h3 className="section-title">Coaching Recommendations</h3>
                {behaviorData.recommendations?.length === 0 ? (
                  <p className="text-dark-400 text-sm">No specific recommendations at this time.</p>
                ) : (
                  <ul className="space-y-3">
                    {behaviorData.recommendations.map((rec, idx) => (
                      <li key={idx} className="flex gap-3 items-start p-3 bg-primary-500/5 border border-primary-500/10 rounded-lg">
                        <div className="bg-primary-500/20 p-1.5 rounded-full mt-0.5">
                          <ChevronRight size={14} className="text-primary-400" />
                        </div>
                        <p className="text-sm text-dark-200">{rec}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}