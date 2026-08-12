import client from './client';

const API = {
  // ── Auth ──────────────────────────────────────────────────────────────
  signIn: (name, email) =>
    client.post('/api/auth/signin', { name, email }).then(r => r.data),

  // ── Projects ──────────────────────────────────────────────────────────
  listProjects: (email) =>
    client.get('/api/projects', { params: { email } }).then(r => r.data),

  getProject: (id) =>
    client.get(`/api/projects/${id}`).then(r => r.data),

  createProject: (user_email, title, book_text) =>
    client.post('/api/projects', { user_email, title, book_text }).then(r => r.data),

  createProjectFromFile: (user_email, title, file) => {
    const form = new FormData();
    form.append('user_email', user_email);
    form.append('title', title);
    form.append('file', file);
    return client.post('/api/projects/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },

  // ── Steps ─────────────────────────────────────────────────────────────
  runStyle: (project_id, style = '') =>
    client.post('/api/projects/' + project_id + '/steps/style', { style }).then(r => r.data),

  runCharacters: (project_id) =>
    client.post('/api/projects/' + project_id + '/steps/characters').then(r => r.data),

  runPortraits: (project_id) =>
    client.post('/api/projects/' + project_id + '/steps/portraits').then(r => r.data),

  runChapters: (project_id) =>
    client.post('/api/projects/' + project_id + '/steps/chapters').then(r => r.data),

  runIllustrations: (project_id) =>
    client.post('/api/projects/' + project_id + '/steps/illustrations').then(r => r.data),
};

export default API;
