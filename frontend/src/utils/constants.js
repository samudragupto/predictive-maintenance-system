/**
 * Application Constants
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
export const APP_NAME = import.meta.env.VITE_APP_NAME || 'Predictive Maintenance System'
export const REFRESH_INTERVAL = parseInt(import.meta.env.VITE_REFRESH_INTERVAL || '30000')

// Risk Level Colors & Labels
export const RISK_LEVELS = {
  LOW: { label: 'Low', color: 'success', bgClass: 'bg-success-500/20', textClass: 'text-success-500', dotClass: 'bg-success-500' },
  MEDIUM: { label: 'Medium', color: 'warning', bgClass: 'bg-warning-500/20', textClass: 'text-warning-500', dotClass: 'bg-warning-500' },
  HIGH: { label: 'High', color: 'danger', bgClass: 'bg-orange-500/20', textClass: 'text-orange-500', dotClass: 'bg-orange-500' },
  CRITICAL: { label: 'Critical', color: 'danger', bgClass: 'bg-danger-500/20', textClass: 'text-danger-500', dotClass: 'bg-danger-500' },
}

// Health Status
export const HEALTH_STATUS = {
  HEALTHY: { label: 'Healthy', color: 'success', icon: '✅' },
  WARNING: { label: 'Warning', color: 'warning', icon: '⚠️' },
  CRITICAL: { label: 'Critical', color: 'danger', icon: '🔴' },
  UNKNOWN: { label: 'Unknown', color: 'neutral', icon: '❓' },
}

// Vehicle Status
export const VEHICLE_STATUS = {
  ACTIVE: { label: 'Active', color: 'success' },
  INACTIVE: { label: 'Inactive', color: 'neutral' },
  IN_SERVICE: { label: 'In Service', color: 'warning' },
  DECOMMISSIONED: { label: 'Decommissioned', color: 'danger' },
  PENDING_INSPECTION: { label: 'Pending Inspection', color: 'info' },
}

// Appointment Status
export const APPOINTMENT_STATUS = {
  PENDING: { label: 'Pending', color: 'neutral' },
  CONFIRMED: { label: 'Confirmed', color: 'info' },
  SCHEDULED: { label: 'Scheduled', color: 'info' },
  CHECKED_IN: { label: 'Checked In', color: 'warning' },
  IN_PROGRESS: { label: 'In Progress', color: 'warning' },
  COMPLETED: { label: 'Completed', color: 'success' },
  CANCELLED: { label: 'Cancelled', color: 'danger' },
  NO_SHOW: { label: 'No Show', color: 'danger' },
}

// Agent Types
export const AGENT_TYPES = {
  master: { label: 'Master Orchestrator', icon: '🧠', color: 'primary' },
  diagnosis: { label: 'Diagnosis Agent', icon: '🔍', color: 'info' },
  cost: { label: 'Cost Agent', icon: '💰', color: 'success' },
  scheduling: { label: 'Scheduling Agent', icon: '📅', color: 'warning' },
  behavior: { label: 'Behavior Agent', icon: '🚗', color: 'info' },
  feedback: { label: 'Feedback Agent', icon: '📝', color: 'neutral' },
  ueba: { label: 'UEBA Security', icon: '🛡️', color: 'danger' },
}

// Navigation items
export const NAV_ITEMS = [
  { path: '/', label: 'Dashboard', icon: 'LayoutDashboard' },
  { path: '/vehicles', label: 'Vehicles', icon: 'Car' },
  { path: '/telemetry', label: 'Telemetry', icon: 'Activity' },
  { path: '/diagnoses', label: 'Diagnoses', icon: 'Stethoscope' },
  { path: '/appointments', label: 'Appointments', icon: 'Calendar' },
  { path: '/costs', label: 'Cost Estimates', icon: 'DollarSign' },
  { path: '/behavior', label: 'Driver Behavior', icon: 'UserCheck' },
  { path: '/feedback', label: 'Feedback & RCA', icon: 'MessageSquare' },
  { path: '/agents', label: 'AI Agents', icon: 'Bot' },
  { path: '/security', label: 'Security', icon: 'Shield' },
]