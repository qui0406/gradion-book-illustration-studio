import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import API from '../api/projects';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const STATUS_ORDER = ['CREATED', 'STYLE_SET', 'CHARACTERS_GENERATED', 'PORTRAITS_GENERATED', 'CHAPTERS_GENERATED', 'DONE'];
const STEPS = 5;

function statusIndex(status) {
  return STATUS_ORDER.indexOf(status);
}

function getStatusLabel(project) {
  if (project.status === 'DONE') return { label: 'Done', cls: 'gd-pill gd-pill-ink' };
  if (project.status === 'CREATED') return { label: 'Draft', cls: 'gd-pill gd-pill-gray' };
  return { label: 'In progress', cls: 'gd-pill gd-pill-orange', dot: true };
}

function getStepCount(project) {
  return Math.max(0, statusIndex(project.status));
}

function getThumbnail(project) {
  // Show first illustration, then first portrait
  if (project.illustrations?.length > 0) {
    return API_BASE + project.illustrations[0].image_path;
  }
  if (project.portraits?.length > 0) {
    return API_BASE + project.portraits[0].image_path;
  }
  return null;
}

function formatDate(isoStr) {
  if (!isoStr) return '';
  const d = new Date(isoStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function ProjectCard({ project, index }) {
  const navigate = useNavigate();
  const { label, cls, dot } = getStatusLabel(project);
  const stepsCompleted = getStepCount(project);
  const thumb = getThumbnail(project);

  return (
    <div
      className="project-card"
      style={{ animationDelay: `${index * 60}ms` }}
      onClick={() => navigate(`/projects/${project.id}`)}
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && navigate(`/projects/${project.id}`)}
      aria-label={`Open project ${project.title}`}
    >
      {/* Thumbnail */}
      <div className="project-card-thumb">
        {thumb ? (
          <img src={thumb} alt={`${project.title} illustration`} />
        ) : (
          <div className="project-card-thumb-placeholder">📖</div>
        )}
        <div className="project-card-badge">
          <span className={cls}>
            {dot && <span className="dot" />}
            {label}
          </span>
        </div>
      </div>

      {/* Body */}
      <div className="project-card-body">
        <div className="project-card-title">{project.title}</div>
        <div className="project-card-meta">
          Created {formatDate(project.created_at)} · Step {stepsCompleted} of {STEPS}
          {project.status === 'DONE' ? ' complete' : ''}
        </div>

        {/* 5 progress bars */}
        <div className="progress-bars">
          {Array.from({ length: STEPS }).map((_, i) => (
            <div
              key={i}
              className={`progress-bar ${i < stepsCompleted ? 'done' : ''}`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function ProjectList() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user?.email) return;
    API.listProjects(user.email)
      .then(res => {
        setProjects(res.data || []);
        setLoading(false);
      })
      .catch(() => {
        setError('Failed to load projects');
        setLoading(false);
      });
  }, [user?.email]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Navbar />

      <main className="app-body" style={{ flex: 1 }}>
        <div className="list-head">
          <div>
            <h2>Your projects</h2>
            <p className="list-head-sub">Manage and track the progress of your book illustrations.</p>
          </div>
          <button
            className="gd-btn gd-btn-primary"
            onClick={() => navigate('/projects/new')}
            id="btn-new-project"
          >
            + New project
          </button>
        </div>

        {loading && (
          <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--sp-9)' }}>
            <span className="gd-spinner gd-spinner-lg" />
          </div>
        )}

        {error && (
          <div className="step-error-box">{error}</div>
        )}

        {!loading && !error && projects.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">📚</div>
            <h3>No projects yet</h3>
            <p>Create your first project to get started with book illustration.</p>
            <button
              className="gd-btn gd-btn-primary"
              onClick={() => navigate('/projects/new')}
            >
              + New project
            </button>
          </div>
        )}

        {!loading && projects.length > 0 && (
          <div className="project-grid">
            {projects.map((p, i) => (
              <ProjectCard key={p.id} project={p} index={i} />
            ))}
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}
