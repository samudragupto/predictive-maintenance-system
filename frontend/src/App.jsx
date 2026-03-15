/**
 * Main Application Component
 * Sets up routing, global providers, and Authentication
 */

import React, { Suspense, lazy } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { SignedIn, SignedOut, SignIn, ClerkLoaded, ClerkLoading } from "@clerk/clerk-react"

import Layout from './components/layout/Layout'
import { PageLoader } from './components/common/LoadingSpinner'

// Lazy load pages for code splitting
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const VehiclesPage = lazy(() => import('./pages/VehiclesPage'))
const TelemetryPage = lazy(() => import('./pages/TelemetryPage'))
const DiagnosesPage = lazy(() => import('./pages/DiagnosesPage'))
const AppointmentsPage = lazy(() => import('./pages/AppointmentsPage'))
const CostsPage = lazy(() => import('./pages/CostsPage'))
const BehaviorPage = lazy(() => import('./pages/BehaviorPage'))
const FeedbackPage = lazy(() => import('./pages/FeedbackPage'))
const AgentsPage = lazy(() => import('./pages/AgentsPage'))
const SecurityPage = lazy(() => import('./pages/SecurityPage'))

export default function App() {
  return (
    <Router>
      {/* Toast Notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#1e293b',
            color: '#f1f5f9',
            border: '1px solid #334155',
            fontSize: '14px',
          },
          success: {
            iconTheme: { primary: '#22c55e', secondary: '#fff' },
          },
          error: {
            iconTheme: { primary: '#ef4444', secondary: '#fff' },
          },
        }}
      />

      {/* Show loader while Clerk initializes */}
      <ClerkLoading>
        <div className="min-h-screen bg-dark-900 flex items-center justify-center">
          <PageLoader text="Initializing Security..." />
        </div>
      </ClerkLoading>

      {/* Render App only after Clerk is loaded */}
      <ClerkLoaded>
        {/* --- AUTHENTICATION ROUTING --- */}
        
        {/* 1. PUBLIC ROUTES (Login) */}
        <SignedOut>
          <Routes>
            <Route path="/sign-in/*" element={
              <div className="min-h-screen w-full bg-dark-900 flex flex-col items-center justify-center p-4">
                <div className="mb-8 text-center">
                  <h1 className="text-3xl font-bold text-white mb-2">Predictive Maintenance AI</h1>
                  <p className="text-dark-400">Enterprise Fleet Management System</p>
                </div>
                {/* Clerk's Pre-built Login Component */}
                <SignIn 
                  routing="path" 
                  path="/sign-in" 
                  appearance={{
                    elements: {
                      rootBox: "mx-auto w-full max-w-md",
                      card: "bg-dark-800 border border-dark-700 shadow-xl",
                      headerTitle: "text-white",
                      headerSubtitle: "text-dark-400",
                      formFieldLabel: "text-dark-300",
                      formFieldInput: "bg-dark-900 border-dark-600 text-white",
                      footerActionLink: "text-primary-400 hover:text-primary-300",
                      identityPreviewText: "text-white",
                      formButtonPrimary: "bg-primary-600 hover:bg-primary-700 text-white",
                    }
                  }}
                />
              </div>
            } />
            {/* Redirect any other public route to sign-in */}
            <Route path="*" element={<Navigate to="/sign-in" replace />} />
          </Routes>
        </SignedOut>

        {/* 2. PROTECTED ROUTES (Dashboard) */}
        <SignedIn>
          <Layout>
            <Suspense fallback={<PageLoader text="Loading modules..." />}>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/vehicles" element={<VehiclesPage />} />
                <Route path="/telemetry" element={<TelemetryPage />} />
                <Route path="/diagnoses" element={<DiagnosesPage />} />
                <Route path="/appointments" element={<AppointmentsPage />} />
                <Route path="/costs" element={<CostsPage />} />
                <Route path="/behavior" element={<BehaviorPage />} />
                <Route path="/feedback" element={<FeedbackPage />} />
                <Route path="/agents" element={<AgentsPage />} />
                <Route path="/security" element={<SecurityPage />} />
                {/* Redirect root sign-in to dashboard if already logged in */}
                <Route path="/sign-in" element={<Navigate to="/" replace />} />
              </Routes>
            </Suspense>
          </Layout>
        </SignedIn>
      </ClerkLoaded>

    </Router>
  )
}