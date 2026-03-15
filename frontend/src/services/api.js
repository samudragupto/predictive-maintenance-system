/**
 * API Service
 * Centralized HTTP client for backend communication
 */

import axios from 'axios'
import toast from 'react-hot-toast'
import { API_BASE_URL } from '../utils/constants'

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use(
  async (config) => {
    // Add Clerk auth token if available
    try {
      if (window.Clerk && window.Clerk.session) {
        const token = await window.Clerk.session.getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
    } catch (err) {
      console.warn("Failed to get auth token", err);
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const message = error.response?.data?.detail?.message
      || error.response?.data?.detail
      || error.response?.data?.message
      || error.message
      || 'An unexpected error occurred'

    // Don't toast for specific error codes or if handled elsewhere
    if (error.response?.status !== 404 && error.code !== 'ERR_CANCELED') {
      toast.error(message)
    }

    // Handle 401 Unauthorized (Session expired)
    if (error.response?.status === 401) {
      // Clerk handles redirect usually, but we can force it if needed
      console.warn("Session expired or invalid token");
    }

    console.error('API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      message: message,
    })

    return Promise.reject(error)
  }
)

// ============ Vehicle API ============
export const vehicleAPI = {
  list: (params) => api.get('/vehicles', { params }),
  get: (id) => api.get(`/vehicles/${id}`),
  create: (data) => api.post('/vehicles', data),
  update: (id, data) => api.put(`/vehicles/${id}`, data),
  delete: (id) => api.delete(`/vehicles/${id}`),
  getFleetOverview: (fleetId) => api.get('/vehicles/fleet-overview', { params: { fleet_id: fleetId } }),
  getNeedingService: (limit = 20) => api.get('/vehicles/needing-service', { params: { limit } }),
  updateHealthScore: (id, score) => api.patch(`/vehicles/${id}/health-score`, null, { params: { health_score: score } }),
}

// ============ Telemetry API ============
export const telemetryAPI = {
  ingest: (data) => api.post('/telemetry/ingest', data),
  ingestBatch: (readings) => api.post('/telemetry/ingest/batch', readings),
  getLatest: (vehicleId) => api.get(`/telemetry/latest/${vehicleId}`),
  getHistory: (vehicleId, params) => api.get(`/telemetry/history/${vehicleId}`, { params }),
  getRiskAnalysis: (vehicleId) => api.get(`/telemetry/risk-analysis/${vehicleId}`),
  getSnapshots: (vehicleId, params) => api.get(`/telemetry/snapshots/${vehicleId}`, { params }),
  getRealTime: () => api.get('/telemetry/real-time'),
  simulate: (count = 10) => api.post('/telemetry/simulate', null, { params: { vehicle_count: count } }),
  simulateSingle: (vehicleId) => api.post(`/telemetry/simulate/${vehicleId}`),
}

// ============ Diagnosis API ============
export const diagnosisAPI = {
  create: (vehicleId, triggeredBy = 'MANUAL', data = null) =>
    api.post('/diagnoses', data, { params: { vehicle_id: vehicleId, triggered_by: triggeredBy } }),
  get: (id) => api.get(`/diagnoses/${id}`),
  getRecent: (params) => api.get('/diagnoses/recent', { params }),
  getByVehicle: (vehicleId, params) => api.get(`/diagnoses/vehicle/${vehicleId}`, { params }),
}

// ============ Cost Estimate API ============
export const costAPI = {
  create: (vehicleId, diagnosisId, services) =>
    api.post('/cost-estimates', services, { params: { vehicle_id: vehicleId, diagnosis_id: diagnosisId } }),
  get: (id) => api.get(`/cost-estimates/${id}`),
  getByVehicle: (vehicleId, params) => api.get(`/cost-estimates/vehicle/${vehicleId}`, { params }),
  approve: (id, approvedBy = 'admin') =>
    api.patch(`/cost-estimates/${id}/approve`, null, { params: { approved_by: approvedBy } }),
}

// ============ Appointment API ============
export const appointmentAPI = {
  create: (data) => api.post('/appointments', data),
  autoSchedule: (vehicleId, urgency = 'MEDIUM', diagnosisId = null) =>
    api.post('/appointments/auto-schedule', null, { params: { vehicle_id: vehicleId, urgency, diagnosis_id: diagnosisId } }),
  list: (params) => api.get('/appointments', { params }),
  getUpcoming: (limit = 10) => api.get('/appointments/upcoming', { params: { limit } }),
  get: (id) => api.get(`/appointments/${id}`),
  updateStatus: (id, status, notes = null) =>
    api.patch(`/appointments/${id}/status`, null, { params: { status, notes } }),
}

// ============ Service Center API ============
export const serviceCenterAPI = {
  list: (params) => api.get('/service-centers', { params }),
  get: (id) => api.get(`/service-centers/${id}`),
  create: (data) => api.post('/service-centers', data),
  findNearest: (lat, lon, radius = 50) =>
    api.get('/service-centers/nearest', { params: { latitude: lat, longitude: lon, radius_km: radius } }),
  seed: () => api.post('/service-centers/seed'),
}

// ============ Driver Behavior API ============
export const behaviorAPI = {
  analyze: (vehicleId, periodType = 'DAILY') =>
    api.post(`/driver-behavior/analyze/${vehicleId}`, null, { params: { period_type: periodType } }),
  get: (vehicleId, periodType = 'DAILY') =>
    api.get(`/driver-behavior/${vehicleId}`, { params: { period_type: periodType } }),
  getHistory: (vehicleId, limit = 30) =>
    api.get(`/driver-behavior/${vehicleId}/history`, { params: { limit } }),
}

// ============ Feedback API ============
export const feedbackAPI = {
  create: (data) => api.post('/feedback', data),
  get: (id) => api.get(`/feedback/${id}`),
  getByVehicle: (vehicleId, params) => api.get(`/feedback/vehicle/${vehicleId}`, { params }),
  getStats: () => api.get('/feedback/stats'),
  createRCA: (data) => api.post('/feedback/rca', data),
  getRCAReports: (params) => api.get('/feedback/rca/reports', { params }),
  createCAPA: (rcaId, data) => api.post(`/feedback/rca/${rcaId}/capa`, data),
}

// ============ Security API ============
export const securityAPI = {
  getLogs: (params) => api.get('/security/logs', { params }),
  getAlerts: (params) => api.get('/security/ueba/alerts', { params }),
  getAlertSummary: () => api.get('/security/ueba/alerts/summary'),
  updateAlert: (id, data) => api.patch(`/security/ueba/alerts/${id}`, data),
}

// ============ Agent API ============
export const agentAPI = {
  orchestrate: (vehicleId, telemetryData = null) =>
    api.post('/agents/orchestrate', telemetryData, { params: { vehicle_id: vehicleId } }),
  execute: (agentType, action, inputData = {}) =>
    api.post('/agents/execute', inputData, { params: { agent_type: agentType, action } }),
  getHealth: () => api.get('/agents/health'),
  getStats: () => api.get('/agents/stats'),
  getAgentStats: (agentType) => api.get(`/agents/stats/${agentType}`),
  getHistory: (agentType, limit = 10) =>
    api.get(`/agents/history/${agentType}`, { params: { limit } }),
  getActiveWorkflows: () => api.get('/agents/workflows/active'),
  getCompletedWorkflows: (limit = 20) =>
    api.get('/agents/workflows/completed', { params: { limit } }),
}

// ============ Dashboard API ============
export const dashboardAPI = {
  getMain: () => api.get('/dashboard'),
  getFleet: (fleetId) => api.get('/dashboard/fleet', { params: { fleet_id: fleetId } }),
  getVehicle: (vehicleId) => api.get(`/dashboard/vehicle/${vehicleId}`),
  getCosts: () => api.get('/dashboard/costs'),
  getSecurity: () => api.get('/dashboard/security'),
}

export default api