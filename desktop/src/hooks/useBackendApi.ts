import { useState, useCallback } from 'react';

export interface DriverInfo {
  name: string;
  display_name: string;
  version: string;
  driver_type: string;
  bus_types: string[];
  capabilities: string[];
  max_latency_us: number;
  min_interval_ms: number;
  i2c_addresses: number[];
}

interface DriversResponse {
  drivers: DriverInfo[];
  total: number;
}

const DEFAULT_BACKEND_URL = 'http://localhost:8400';

function getBackendUrl(): string {
  return DEFAULT_BACKEND_URL;
}

export function useBackendApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDrivers = useCallback(async (): Promise<DriverInfo[]> => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${getBackendUrl()}/api/drivers`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: DriversResponse = await res.json();
      return data.drivers;
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Unknown error';
      setError(msg);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchDriverCount = useCallback(async (): Promise<number> => {
    try {
      const res = await fetch(`${getBackendUrl()}/api/drivers`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: DriversResponse = await res.json();
      return data.total;
    } catch {
      return 0;
    }
  }, []);

  const fetchHealth = useCallback(async (): Promise<boolean> => {
    try {
      const res = await fetch(`${getBackendUrl()}/api/system/health`);
      return res.ok;
    } catch {
      return false;
    }
  }, []);

  const compileIntent = useCallback(async (intentText: string): Promise<string> => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${getBackendUrl()}/api/llm/intent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: intentText }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.text();
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Unknown error';
      setError(msg);
      return '';
    } finally {
      setLoading(false);
    }
  }, []);

  return { fetchDrivers, fetchDriverCount, fetchHealth, compileIntent, loading, error };
}
