import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.request.use((config) => {
  try {
    const raw = localStorage.getItem('gradion_user');
    if (raw) {
      const user = JSON.parse(raw);
      if (user && user.email) {
        config.headers['X-User-Email'] = user.email;
      }
    }
  } catch {
    // Ignore JSON parse errors
  }
  return config;
});

export default client;

