import { useEffect, useState } from 'react';
import apiClient from '../services/api';
import type { PublicHome } from '../types/public';

// One shared, short-lived fetch of /public/home: the masthead's LATEST strip
// and the homepage both read it, so navigating between pages does not refetch.
const MAX_AGE_MS = 5 * 60 * 1000;
let inflight: Promise<PublicHome> | null = null;
let fetchedAt = 0;

const loadPublicHome = (): Promise<PublicHome> => {
  if (!inflight || Date.now() - fetchedAt > MAX_AGE_MS) {
    fetchedAt = Date.now();
    inflight = apiClient.getPublicHome().catch((err) => {
      inflight = null; // let the next caller retry
      throw err;
    });
  }
  return inflight;
};

export const usePublicHome = () => {
  const [data, setData] = useState<PublicHome | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    loadPublicHome()
      .then((d) => {
        if (alive) setData(d ?? null);
      })
      .catch(() => {
        if (alive) setError('The latest disclosures could not be loaded.');
      });
    return () => {
      alive = false;
    };
  }, []);

  return { data, error, loading: data == null && error == null };
};
