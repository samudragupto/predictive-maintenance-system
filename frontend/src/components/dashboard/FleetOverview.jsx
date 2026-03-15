/**
 * FleetOverview Component
 * Shows fleet-wide statistics cards
 */

import React from 'react'
import { Car, AlertTriangle, Wrench, HeartPulse, TrendingUp, ShieldCheck } from 'lucide-react'
import StatCard from '../common/StatCard'
import { formatNumber, formatPercent } from '../../utils/helpers'

export default function FleetOverview({ data, loading }) {
  if (loading || !data) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="card animate-pulse">
            <div className="h-4 bg-dark-700 rounded w-1/2 mb-3" />
            <div className="h-8 bg-dark-700 rounded w-1/3 mb-2" />
            <div className="h-3 bg-dark-700 rounded w-2/3" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
      <StatCard
        title="Total Vehicles"
        value={formatNumber(data.total_vehicles)}
        subtitle="In fleet"
        icon={Car}
        color="primary"
      />
      <StatCard
        title="Active"
        value={formatNumber(data.active_vehicles)}
        subtitle={`${data.total_vehicles > 0 ? formatPercent((data.active_vehicles / data.total_vehicles) * 100) : '0%'} of fleet`}
        icon={TrendingUp}
        color="success"
      />
      <StatCard
        title="In Service"
        value={formatNumber(data.vehicles_in_service)}
        subtitle="Currently serviced"
        icon={Wrench}
        color="warning"
      />
      <StatCard
        title="Healthy"
        value={formatNumber(data.healthy_vehicles)}
        subtitle="No issues"
        icon={ShieldCheck}
        color="success"
      />
      <StatCard
        title="Warning"
        value={formatNumber(data.warning_vehicles)}
        subtitle="Need attention"
        icon={AlertTriangle}
        color="warning"
      />
      <StatCard
        title="Critical"
        value={formatNumber(data.critical_vehicles)}
        subtitle="Immediate action"
        icon={HeartPulse}
        color="danger"
      />
    </div>
  )
}