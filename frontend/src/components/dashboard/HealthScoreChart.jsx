/**
 * HealthScoreChart Component
 * Doughnut-style health distribution chart
 */

import React from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

const COLORS = {
  Healthy: '#22c55e',
  Warning: '#f59e0b',
  Critical: '#ef4444',
  Unknown: '#64748b',
}

export default function HealthScoreChart({ data }) {
  if (!data) return null

  const chartData = [
    { name: 'Healthy', value: data.healthy_vehicles || 0 },
    { name: 'Warning', value: data.warning_vehicles || 0 },
    { name: 'Critical', value: data.critical_vehicles || 0 },
  ].filter(d => d.value > 0)

  const total = chartData.reduce((sum, d) => sum + d.value, 0)

  if (total === 0) {
    chartData.push({ name: 'Unknown', value: 1 })
  }

  return (
    <div className="card">
      <h3 className="section-title">Fleet Health Distribution</h3>
      <div className="flex items-center gap-6">
        {/* Chart */}
        <div className="w-40 h-40">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={70}
                paddingAngle={3}
                dataKey="value"
                stroke="none"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[entry.name] || '#64748b'} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                  color: '#f1f5f9',
                  fontSize: '13px',
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Legend */}
        <div className="flex-1 space-y-3">
          {chartData.map((entry) => (
            <div key={entry.name} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: COLORS[entry.name] }}
                />
                <span className="text-sm text-dark-300">{entry.name}</span>
              </div>
              <div className="text-right">
                <span className="text-sm font-semibold text-white">{entry.value}</span>
                <span className="text-xs text-dark-400 ml-1">
                  ({total > 0 ? Math.round((entry.value / total) * 100) : 0}%)
                </span>
              </div>
            </div>
          ))}

          {/* Average Score */}
          <div className="pt-3 border-t border-dark-700">
            <div className="flex items-center justify-between">
              <span className="text-sm text-dark-400">Avg Health Score</span>
              <span className="text-lg font-bold text-white">
                {data.average_health_score?.toFixed(1) || 'N/A'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}