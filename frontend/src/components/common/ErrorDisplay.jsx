/**
 * ErrorDisplay Component
 * Shows error messages with retry option
 */

import React from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export default function ErrorDisplay({
  error,
  title = 'Something went wrong',
  onRetry,
}) {
  const message = error?.response?.data?.detail
    || error?.message
    || 'An unexpected error occurred'

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="p-4 bg-danger-500/10 rounded-full mb-4">
        <AlertTriangle size={32} className="text-danger-500" />
      </div>
      <h3 className="text-lg font-semibold text-white mb-1">{title}</h3>
      <p className="text-sm text-dark-400 max-w-md mb-4">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary">
          <RefreshCw size={16} />
          Retry
        </button>
      )}
    </div>
  )
}