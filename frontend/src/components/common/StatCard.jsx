/**
 * StatCard Component
 * Card for displaying a key metric with label and icon
 */

import React from 'react'
import { cn } from '../../utils/helpers'

export default function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  trendValue,
  color = 'primary',
  className,
  onClick,
}) {
  const colorMap = {
    primary: 'from-primary-500/10 to-primary-600/5 border-primary-500/20',
    success: 'from-success-500/10 to-success-600/5 border-success-500/20',
    warning: 'from-warning-500/10 to-warning-600/5 border-warning-500/20',
    danger: 'from-danger-500/10 to-danger-600/5 border-danger-500/20',
    neutral: 'from-dark-700/50 to-dark-800/50 border-dark-600',
  }

  const iconColorMap = {
    primary: 'text-primary-400 bg-primary-500/10',
    success: 'text-success-500 bg-success-500/10',
    warning: 'text-warning-500 bg-warning-500/10',
    danger: 'text-danger-500 bg-danger-500/10',
    neutral: 'text-dark-400 bg-dark-700',
  }

  const trendColorMap = {
    up: 'text-success-500',
    down: 'text-danger-500',
    stable: 'text-dark-400',
  }

  return (
    <div
      className={cn(
        'bg-gradient-to-br rounded-xl border p-5 transition-all duration-200',
        colorMap[color],
        onClick && 'cursor-pointer hover:scale-[1.02] hover:shadow-lg',
        className,
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-dark-400 font-medium">{title}</p>
          <p className="text-3xl font-bold text-white mt-1">{value}</p>
          {subtitle && (
            <p className="text-sm text-dark-400 mt-1">{subtitle}</p>
          )}
          {trend && (
            <div className={cn('flex items-center gap-1 mt-2 text-sm', trendColorMap[trend])}>
              <span>{trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}</span>
              <span>{trendValue}</span>
            </div>
          )}
        </div>
        {Icon && (
          <div className={cn('p-3 rounded-lg', iconColorMap[color])}>
            <Icon size={24} />
          </div>
        )}
      </div>
    </div>
  )
}