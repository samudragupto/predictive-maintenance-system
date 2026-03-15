/**
 * LoadingSpinner Component
 */

import React from 'react'
import { cn } from '../../utils/helpers'

export default function LoadingSpinner({ size = 'md', className, text }) {
  const sizeMap = {
    sm: 'w-4 h-4 border-2',
    md: 'w-8 h-8 border-3',
    lg: 'w-12 h-12 border-4',
    xl: 'w-16 h-16 border-4',
  }

  return (
    <div className={cn('flex flex-col items-center justify-center gap-3', className)}>
      <div className={cn(
        'rounded-full border-primary-500 border-t-transparent animate-spin',
        sizeMap[size] || sizeMap.md,
      )} />
      {text && <p className="text-sm text-dark-400">{text}</p>}
    </div>
  )
}

export function PageLoader({ text = 'Loading...' }) {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <LoadingSpinner size="lg" text={text} />
    </div>
  )
}

export function CardLoader() {
  return (
    <div className="card animate-pulse">
      <div className="h-4 bg-dark-700 rounded w-1/3 mb-4" />
      <div className="h-8 bg-dark-700 rounded w-1/2 mb-2" />
      <div className="h-3 bg-dark-700 rounded w-2/3" />
    </div>
  )
}