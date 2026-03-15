/**
 * Frontend Helper Functions
 */

import { format, formatDistanceToNow, parseISO } from 'date-fns'

// ============ Date Formatting ============

export function formatDate(dateStr) {
  if (!dateStr) return 'N/A'
  try {
    const date = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr
    return format(date, 'MMM dd, yyyy')
  } catch {
    return 'N/A'
  }
}

export function formatDateTime(dateStr) {
  if (!dateStr) return 'N/A'
  try {
    const date = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr
    return format(date, 'MMM dd, yyyy HH:mm')
  } catch {
    return 'N/A'
  }
}

export function formatTimeAgo(dateStr) {
  if (!dateStr) return 'N/A'
  try {
    const date = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr
    return formatDistanceToNow(date, { addSuffix: true })
  } catch {
    return 'N/A'
  }
}

// ============ Number Formatting ============

export function formatCurrency(amount, currency = 'INR') {
  if (amount === null || amount === undefined) return 'N/A'
  return new Intl.NumberFormat('en-IN', {  // Changed locale to 'en-IN' for Indian formatting
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2,
  }).format(amount)
}

export function formatNumber(num, decimals = 0) {
  if (num === null || num === undefined) return 'N/A'
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(num)
}

export function formatPercent(value, decimals = 1) {
  if (value === null || value === undefined) return 'N/A'
  return `${value.toFixed(decimals)}%`
}

// ============ Health & Risk ============

export function getHealthColor(score) {
  if (score >= 80) return 'text-success-500'
  if (score >= 60) return 'text-warning-500'
  if (score >= 40) return 'text-orange-500'
  return 'text-danger-500'
}

export function getHealthBg(score) {
  if (score >= 80) return 'bg-success-500'
  if (score >= 60) return 'bg-warning-500'
  if (score >= 40) return 'bg-orange-500'
  return 'bg-danger-500'
}

export function getRiskBadge(level) {
  const map = {
    LOW: 'badge-success',
    MEDIUM: 'badge-warning',
    HIGH: 'badge-danger',
    CRITICAL: 'badge-danger',
  }
  return map[level] || 'badge-neutral'
}

export function getStatusBadge(status) {
  const map = {
    ACTIVE: 'badge-success',
    HEALTHY: 'badge-success',
    COMPLETED: 'badge-success',
    SCHEDULED: 'badge-info',
    CONFIRMED: 'badge-info',
    IN_PROGRESS: 'badge-warning',
    PENDING: 'badge-neutral',
    WARNING: 'badge-warning',
    CRITICAL: 'badge-danger',
    CANCELLED: 'badge-danger',
    INACTIVE: 'badge-neutral',
    IN_SERVICE: 'badge-warning',
  }
  return map[status] || 'badge-neutral'
}

// ============ Truncation ============

export function truncate(str, maxLen = 50) {
  if (!str) return ''
  if (str.length <= maxLen) return str
  return str.substring(0, maxLen) + '...'
}

// ============ Class Names ============

export function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}