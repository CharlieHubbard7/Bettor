// Generic data-fetching hook: exposes data/loading/error/refetch with optional polling.
import { useCallback, useEffect, useRef, useState } from "react";

export interface UseApiResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Fetch data from an async function.
 *
 * @param fetcher  The async call (typically an `api.*` method).
 * @param deps     Re-run the fetch when any of these change.
 * @param intervalMs  If > 0, auto-refetch on this interval.
 */
export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: ReadonlyArray<unknown> = [],
  intervalMs = 0
): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Keep the latest fetcher without forcing it into the dependency array.
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const run = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcherRef.current();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    void run();
    if (intervalMs > 0) {
      const id = setInterval(() => void run(), intervalMs);
      return () => clearInterval(id);
    }
  }, [run, intervalMs]);

  return { data, loading, error, refetch: run };
}
