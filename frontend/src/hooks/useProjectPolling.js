import { useState, useEffect, useRef } from 'react';
import API from '../api/projects';

const POLL_INTERVAL = 2500; // ms

export default function useProjectPolling(projectId) {
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  const fetchProject = async (showLoading = false) => {
    if (!projectId) return;
    if (showLoading) setLoading(true);
    try {
      const res = await API.getProject(projectId);
      setProject(res.data);
      setError(null);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Failed to load project');
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    if (!projectId) return;
    fetchProject(true);
  }, [projectId]);

  // Manage polling based on step_state
  useEffect(() => {
    if (!project) return;

    if (project.step_state === 'RUNNING') {
      if (!timerRef.current) {
        timerRef.current = setInterval(() => fetchProject(false), POLL_INTERVAL);
      }
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [project?.step_state]);

  const refresh = () => fetchProject(false);

  return { project, setProject, loading, error, refresh };
}
