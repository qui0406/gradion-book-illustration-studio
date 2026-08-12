import React, { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import API from '../api/projects';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';

export default function NewProject() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [title, setTitle] = useState('');
  const [bookText, setBookText] = useState('');
  const [fileName, setFileName] = useState('');
  const [dragging, setDragging] = useState(false);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [serverError, setServerError] = useState('');
  const fileRef = useRef(null);
  const uploadedFileRef = useRef(null);

  const readFile = (file) => {
    if (!file?.name.endsWith('.txt')) {
      setErrors(e => ({ ...e, file: 'Only .txt files are supported' }));
      return;
    }
    const reader = new FileReader();
    reader.onload = (ev) => {
      setBookText(ev.target.result);
      setFileName(file.name);
      uploadedFileRef.current = file;
      setErrors(e => ({ ...e, file: undefined }));
    };
    reader.readAsText(file, 'utf-8');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) readFile(file);
  };

  const handleFileInput = (e) => {
    const file = e.target.files[0];
    if (file) readFile(file);
  };

  const validate = () => {
    const e = {};
    if (!title.trim()) e.title = 'Project title is required';
    if (!bookText.trim()) e.bookText = 'Book text is required — upload a .txt file or paste text';
    return e;
  };

  const handleCreate = async () => {
    const e = validate();
    setErrors(e);
    if (Object.keys(e).length) return;

    setLoading(true);
    setServerError('');
    try {
      let res;
      if (uploadedFileRef.current) {
        res = await API.createProjectFromFile(user.email, title.trim(), uploadedFileRef.current);
      } else {
        res = await API.createProject(user.email, title.trim(), bookText.trim());
      }
      navigate(`/projects/${res.data.id}`);
    } catch (err) {
      setServerError(err?.response?.data?.detail || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Navbar />

      <main className="app-body" style={{ flex: 1 }}>
        <div style={{ maxWidth: 600, margin: '0 auto' }}>
          <div className="new-project-card">
            {/* Back */}
            <span
              className="back-link"
              onClick={() => navigate('/')}
              role="link"
              tabIndex={0}
              onKeyDown={e => e.key === 'Enter' && navigate('/')}
            >
              ← Back to Projects
            </span>

            <h3 style={{ margin: '0 0 6px' }}>New Project</h3>
            <p style={{ fontSize: 14, color: 'var(--grad-ink-2)', marginBottom: 'var(--sp-5)' }}>
              Set up a new illustration workspace. Start by defining the manuscript context.
            </p>

            {/* Title */}
            <div className="gd-field">
              <label htmlFor="proj-title">
                Project Title <span className="req">*</span>
              </label>
              <input
                id="proj-title"
                type="text"
                placeholder="e.g., The Midnight Garden"
                value={title}
                onChange={e => setTitle(e.target.value)}
                autoFocus
              />
              {errors.title && <div className="field-err">{errors.title}</div>}
            </div>

            {/* Book text */}
            <div className="gd-field" style={{ marginTop: 'var(--sp-5)' }}>
              <label>
                Book Text Context <span className="req">*</span>
              </label>
              <p style={{ fontSize: 12, color: 'var(--grad-ink-3)', margin: '0 0 10px' }}>
                Provide the text to help generate contextual illustration briefs.
                Upload a file or paste directly.
              </p>

              {/* Drop zone */}
              <div
                className={`dropzone ${dragging ? 'dragging' : ''} ${fileName ? 'has-file' : ''}`}
                onClick={() => fileRef.current?.click()}
                onDragOver={e => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                role="button"
                tabIndex={0}
                aria-label="Upload .txt file"
                onKeyDown={e => e.key === 'Enter' && fileRef.current?.click()}
                id="dropzone"
              >
                <div className="dropzone-icon">
                  {fileName ? '✅' : '📄'}
                </div>
                <div className="dropzone-label">
                  {fileName ? `${fileName} loaded` : 'Drop .txt file here'}
                </div>
                <div className="dropzone-hint">
                  {fileName ? 'Click to replace' : 'or click to browse'}
                </div>
              </div>
              <input
                ref={fileRef}
                type="file"
                accept=".txt"
                style={{ display: 'none' }}
                onChange={handleFileInput}
                id="file-input"
              />
              {errors.file && <div className="field-err">{errors.file}</div>}

              {/* Divider */}
              <div className="divider-or">or paste text</div>

              {/* Textarea */}
              <textarea
                id="book-textarea"
                rows={6}
                placeholder="Paste manuscript excerpt here…"
                value={bookText}
                onChange={e => {
                  setBookText(e.target.value);
                  // If user pastes, clear uploaded file ref
                  if (e.target.value && uploadedFileRef.current) {
                    uploadedFileRef.current = null;
                    setFileName('');
                  }
                }}
                style={{ font: 'inherit', fontSize: 14, width: '100%', padding: '11px 14px', borderRadius: 'var(--r-2)', border: '1px solid var(--border-1)', outline: 'none', resize: 'vertical' }}
              />
              {errors.bookText && <div className="field-err">{errors.bookText}</div>}
            </div>

            {serverError && (
              <div className="step-error-box" style={{ marginTop: 'var(--sp-4)' }}>{serverError}</div>
            )}

            {/* Actions */}
            <div className="new-project-actions">
              <button
                className="gd-btn gd-btn-secondary"
                onClick={() => navigate('/')}
                id="btn-cancel"
              >
                Cancel
              </button>
              <button
                className="gd-btn gd-btn-primary"
                onClick={handleCreate}
                disabled={loading}
                id="btn-create-project"
              >
                {loading ? (
                  <>
                    <span className="gd-spinner gd-spinner-sm" />
                    Creating…
                  </>
                ) : (
                  'Create Project'
                )}
              </button>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
