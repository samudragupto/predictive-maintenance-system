/**
 * EmptyState Component
 * Displayed when there is no data to show
 */

import React from 'react'
import { cn } from '../../utils/helpers'

export default function EmptyState({
  icon: Icon,
  title = 'No data found',
  description = 'There is nothing to display at the moment.',
  action,
  actionLabel = 'Take Action',
  className,
}) {
  return (
    <div className={cn(
      'flex flex-col items-center justify-center py-12 px-4 text-center',
      className,
    )}>
      {Icon && (
        <div className="p-4 bg-dark-800 rounded-full mb-4">
          <Icon size={32} className="text-dark-400" />
        </div>
      )}
      <h3 className="text-lg font-semibold text-dark-200 mb-1">{title}</h3>
      <p className="text-sm text-dark-400 max-w-md">{description}</p>
      {action && (
        <button onClick={action} className="btn-primary mt-4">
          {actionLabel}
        </button>
      )}
    </div>
  )
}