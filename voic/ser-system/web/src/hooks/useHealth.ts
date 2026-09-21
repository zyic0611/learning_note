import { useCallback, useEffect, useState } from 'react';
import { getHealth } from '../api/client';
import type { HealthResponse } from '../types/api';

export type HealthState = 'checking' | 'online' | 'offline';

export function useHealth() {
  const [state, setState] = useState<HealthState>('checking');
  const [detail, setDetail] = useState<HealthResponse | null>(null);

  const check = useCallback(async (signal?: AbortSignal) => {
    setState((current) => current === 'offline' ? 'checking' : current);
    try {
      const response = await getHealth(signal);
      setDetail(response);
      setState(response.model_ready && response.asr_ready ? 'online' : 'offline');
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      setState('offline');
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void check(controller.signal);
    const timer = window.setInterval(() => void check(), 30_000);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [check]);

  return { state, detail, refresh: check };
}
