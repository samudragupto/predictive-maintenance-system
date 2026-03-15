/**
 * StatusBadge Component
 * Reusable badge for displaying status with appropriate colors
 */

import React from 'react'
import { cn } from '../../utils/helpers'

const colorMap = {
  success: 'bg-success-500/20 text-success-500',
  warning: 'bg-warning-500/20 text-warning-500',
  danger: 'bg-danger-500/20 text-danger-500',
  info: 'bg-primary-500/20 text-primary-400',
  neutral: 'bg-dark-600 text-dark-300',
  orange: 'bg-orange-500/20 text-orange-400',
}

const dotColorMap = {
  success: 'bg-success-500',
  warning: 'bg-warning-500',
  danger: 'bg-danger-500',
  info: 'bg-primary-500',
  neutral: 'bg-dark-400',
  orange: 'bg-orange-500',
}

export default function StatusBadge({ status, color = 'neutral', showDot = false, size = 'sm', className }) {
  const sizeClass = size === 'lg' ? 'px-3 py-1 text-sm' : 'px-2.5 py-0.5 text-xs'

  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 rounded-full font-medium',
      sizeClass,
      colorMap[color] || colorMap.neutral,
      className,
    )}>
      {showDot && (
        <span className={cn(
          'w-1.5 h-1.5 rounded-full',
          dotColorMap[color] || dotColorMap.neutral,
        )} />
      )}
      {status}
    </span>
  )
}