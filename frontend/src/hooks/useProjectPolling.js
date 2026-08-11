import { useState, useEffect } from 'react';

/**
 * Skeleton custom hook for project status polling.
 * To be implemented with the user in future steps.
 */
export default function useProjectPolling(projectId) {
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Polling logic skeleton
  }, [projectId]);

  return { project, loading, error };
}
