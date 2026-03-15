/**
 * Costs Page
 * Repair cost estimates and financial forecasting
 */

import React, { useState, useEffect, useCallback } from 'react'
import {
  DollarSign, RefreshCw, FileText, CheckCircle,
  Clock, AlertTriangle, TrendingUp, PieChart
} from 'lucide-react'
import toast from 'react-hot-toast'

import StatCard from '../components/common/StatCard'
import StatusBadge from '../components/common/StatusBadge'
import EmptyState from '../components/common/EmptyState'
import { PageLoader } from '../components/common/LoadingSpinner'
import ErrorDisplay from '../components/common/ErrorDisplay'

import { costAPI, diagnosisAPI } from '../services/api'
import { formatCurrency, formatDate } from '../utils/helpers'

export default function CostsPage() {
  const [estimates, setEstimates] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [diagnoses, setDiagnoses] = useState([])
  const [generating, setGenerating] = useState(false)

  // Stats
  const totalEstimated = estimates.reduce((sum, e) => sum + (e.total_estimate || 0), 0)
  const pendingApproval = estimates.filter(e => e.status === 'PENDING').length
  const avgCost = estimates.length > 0 ? totalEstimated / estimates.length : 0

  const fetchEstimates = useCallback(async () => {
    try {
      setLoading(true)
      // Fetch recent diagnoses first to allow creating estimates
      const diagResult = await diagnosisAPI.getRecent({ limit: 20 })
      setDiagnoses(diagResult.data || [])

      // Fetch estimates (mocking list endpoint as it's by vehicle usually)
      // In a real app, you'd have a list endpoint for estimates
      // For now we'll just use empty array until estimates are created
      setEstimates([]) 
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchEstimates()
  }, [fetchEstimates])

  const handleCreateEstimate = async (diagnosis) => {
    try {
      setGenerating(true)
      toast.loading('Generating AI estimate...', { id: 'cost' })
      
      const result = await costAPI.create(
        diagnosis.vehicle_id,
        diagnosis.diagnosis_id,
        diagnosis.affected_components
      )
      
      setEstimates(prev => [result.data, ...prev])
      toast.success('Estimate generated!', { id: 'cost' })
    } catch (err) {
      toast.error('Estimation failed', { id: 'cost' })
    } finally {
      setGenerating(false)
    }
  }

  const handleApprove = async (id) => {
    try {
      await costAPI.approve(id)
      setEstimates(prev => prev.map(e => 
        e.estimate_id === id ? { ...e, status: 'APPROVED' } : e
      ))
      toast.success('Estimate approved')
    } catch (err) {
      toast.error('Approval failed')
    }
  }

  if (loading && estimates.length === 0 && diagnoses.length === 0) {
    return <PageLoader text="Loading financial data..." />
  }

  if (error) {
    return <ErrorDisplay error={error} onRetry={fetchEstimates} />
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="page-title">Cost Estimates</h1>
          <p className="page-subtitle">AI-driven repair forecasting and approvals</p>
        </div>
        <button onClick={fetchEstimates} className="btn-secondary btn-sm">
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard
          title="Total Forecast"
          value={formatCurrency(totalEstimated)}
          subtitle="All active estimates"
          icon={DollarSign}
          color="primary"
        />
        <StatCard
          title="Pending Approval"
          value={pendingApproval}
          subtitle="Estimates waiting"
          icon={Clock}
          color="warning"
        />
        <StatCard
          title="Average Cost"
          value={formatCurrency(avgCost)}
          subtitle="Per service"
          icon={TrendingUp}
          color="success"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pending Diagnoses List */}
        <div className="lg:col-span-1 space-y-4">
          <h3 className="section-title">Recent Diagnoses</h3>
          {diagnoses.length === 0 ? (
            <div className="card">
              <EmptyState title="No diagnoses" description="Run diagnosis to generate costs." />
            </div>
          ) : (
            <div className="space-y-3">
              {diagnoses.map(diag => (
                <div key={diag.diagnosis_id} className="card p-4 flex flex-col gap-3">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-bold text-white">{diag.vehicle_id}</p>
                      <p className="text-xs text-dark-400">{formatDate(diag.created_at)}</p>
                    </div>
                    <StatusBadge 
                      status={diag.overall_risk_level} 
                      color={diag.overall_risk_level === 'CRITICAL' ? 'danger' : 'warning'} 
                    />
                  </div>
                  <p className="text-xs text-dark-300 line-clamp-2">{diag.summary}</p>
                  <button
                    onClick={() => handleCreateEstimate(diag)}
                    disabled={generating}
                    className="btn-primary btn-sm w-full mt-2"
                  >
                    <DollarSign size={14} />
                    Generate Estimate
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Estimates List */}
        <div className="lg:col-span-2 space-y-4">
          <h3 className="section-title">Active Estimates</h3>
          {estimates.length === 0 ? (
            <div className="card">
              <EmptyState 
                icon={FileText} 
                title="No estimates generated" 
                description="Select a diagnosis from the left to generate a cost estimate." 
              />
            </div>
          ) : (
            <div className="space-y-4">
              {estimates.map(est => (
                <div key={est.estimate_id} className="card">
                  <div className="flex flex-col md:flex-row justify-between gap-4 mb-4 border-b border-dark-700 pb-4">
                    <div>
                      <div className="flex items-center gap-3 mb-1">
                        <h4 className="text-lg font-bold text-white">{est.vehicle_id}</h4>
                        <span className="text-xs text-dark-400">#{est.estimate_id}</span>
                      </div>
                      <StatusBadge 
                        status={est.status} 
                        color={est.status === 'APPROVED' ? 'success' : 'warning'} 
                        showDot 
                      />
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-primary-400">
                        {formatCurrency(est.total_estimate)}
                      </p>
                      <p className="text-xs text-dark-400">
                        Range: {formatCurrency(est.estimate_low)} - {formatCurrency(est.estimate_high)}
                      </p>
                    </div>
                  </div>

                  {/* Line Items */}
                  <div className="space-y-2 mb-4">
                    {est.items?.map((item, idx) => (
                      <div key={idx} className="flex justify-between text-sm p-2 bg-dark-700/30 rounded">
                        <div>
                          <span className="text-white">{item.name}</span>
                          <span className="text-xs text-dark-400 ml-2">x{item.quantity}</span>
                        </div>
                        <span className="font-mono text-dark-300">
                          {formatCurrency(item.total_price)}
                        </span>
                      </div>
                    ))}
                  </div>

                  <div className="flex justify-between items-center pt-2">
                    <div className="flex gap-4 text-xs text-dark-400">
                      <span>Parts: {formatCurrency(est.subtotal_parts)}</span>
                      <span>Labor: {formatCurrency(est.subtotal_labor)}</span>
                      <span>Tax: {formatCurrency(est.tax_amount)}</span>
                    </div>
                    
                    {est.status === 'DRAFT' || est.status === 'PENDING' ? (
                      <button
                        onClick={() => handleApprove(est.estimate_id)}
                        className="btn-success btn-sm"
                      >
                        <CheckCircle size={14} />
                        Approve
                      </button>
                    ) : (
                      <span className="text-success-500 text-sm flex items-center gap-1">
                        <CheckCircle size={14} /> Approved
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}