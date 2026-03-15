/**
 * Custom Hooks for API calls
 */

import { useState, useEffect, useCallback, useRef } from 'react'

/**
 * Hook for making API calls with loading and error states
 */
export function useApi(apiFunction, immediate = false, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(immediate)
  const [error, setError] = useState(null)
  const mountedRef = useRef(true)

  const execute = useCallback(async (...args) => {
    setLoading(true)
    setError(null)

    try {
      const result = await apiFunction(...args)
      if (mountedRef.current) {
        setData(result)
        setLoading(false)
      }
      return result
    } catch (err) {
      if (mountedRef.current) {
        setError(err)
        setLoading(false)
      }
      throw err
    }
  }, [apiFunction])

  useEffect(() => {
    mountedRef.current = true
    if (immediate) {
      execute()
    }
    return () => {
      mountedRef.current = false
    }
  }, deps)

  const reset = useCallback(() => {
    setData(null)
    setError(null)
    setLoading(false)
  }, [])

  return { data, loading, error, execute, reset }
}

/**
 * Hook for polling an API at regular intervals
 */
export function usePolling(apiFunction, intervalMs = 30000, immediate = true) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(immediate)
  const [error, setError] = useState(null)
  const intervalRef = useRef(null)
  const mountedRef = useRef(true)

  const fetchData = useCallback(async () => {
    try {
      const result = await apiFunction()
      if (mountedRef.current) {
        setData(result)
        setError(null)
        setLoading(false)
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err)
        setLoading(false)
      }
    }
  }, [apiFunction])

  const start = useCallback(() => {
    fetchData()
    intervalRef.current = setInterval(fetchData, intervalMs)
  }, [fetchData, intervalMs])

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    if (immediate) {
      start()
    }
    return () => {
      mountedRef.current = false
      stop()
    }
  }, [])

  return { data, loading, error, refresh: fetchData, start, stop }
}

/**
 * Hook for toggling states
 */
export function useToggle(initialValue = false) {
  const [value, setValue] = useState(initialValue)
  const toggle = useCallback(() => setValue(v => !v), [])
  const setTrue = useCallback(() => setValue(true), [])
  const setFalse = useCallback(() => setValue(false), [])
  return { value, toggle, setTrue, setFalse, setValue }
}