import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import API from '../api/projects';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import useProjectPolling from '../hooks/useProjectPolling';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ─── Constants ────────────────────────────────────────────────────────────────
const STATUS_ORDER = [
  'CREATED',
  'STYLE_SET',
  'CHARACTERS_GENERATED',
  'PORTRAITS_GENERATED',
  'CHAPTERS_GENERATED',
  'DONE',
];

const STEPS = [
  { key: 'STYLE',         label: 'Style',         status: 'STYLE_SET' },
  { key: 'CHARACTERS',    label: 'Characters',     status: 'CHARACTERS_GENERATED' },
  { key: 'PORTRAITS',     label: 'Portraits',      status: 'PORTRAITS_GENERATED' },
  { key: 'CHAPTERS',      label: 'Chapters',       status: 'CHAPTERS_GENERATED' },
  { key: 'ILLUSTRATIONS', label: 'Illustrations',  status: 'DONE' },
];

// Timeout for "stuck" detection (align with backend STEP_TIMEOUT_SECONDS)
const STEP_TIMEOUT_MS = {
  1: 60_000,
  2: 60_000,
  3: 180_000,
  4: 60_000,
  5: 120_000,
};

function statusIndex(status) {
  return STATUS_ORDER.indexOf(status);
}

function formatDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
  });
}

// ─── Stepper ──────────────────────────────────────────────────────────────────
function Stepper({ project }) {
  const doneIdx = statusIndex(project.status); // e.g. 2 means first 2 steps done

  return (
    <div className="stepper">
      {STEPS.map((step, i) => {
        const done    = i < doneIdx;
        const current = i === doneIdx && project.status !== 'DONE';
        const cls     = done ? 'done' : current ? 'current' : 'pending';

        return (
          <React.Fragment key={step.key}>
            <div className={`stepper-step ${cls}`}>
              <span className={`gd-num-circle ${done ? 'gd-num-circle-done' : current ? 'gd-num-circle-active' : 'gd-num-circle-pending'}`}>
                {done ? '✓' : i + 1}
              </span>
              <span className="stepper-label">{step.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`stepper-connector ${i < doneIdx ? 'done' : ''}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ─── Entity Card ──────────────────────────────────────────────────────────────
function EntityCard({ name, prompt, imagePath, isGenerating, isChapter, index }) {
  const hasImage = Boolean(imagePath);
  const artCls   = `entity-card-art${isChapter ? ' chapter' : ''}${!hasImage ? ' pending' : ''}`;

  return (
    <div className="entity-card" style={{ animationDelay: `${index * 80}ms` }}>
      <div className={artCls}>
        {hasImage ? (
          <img src={API_BASE + imagePath} alt={name} />
        ) : isGenerating ? (
          <div className="entity-card-generating">
            <span className="gd-spinner gd-spinner-md" />
            <span className="entity-card-gen-caption">
              Generating {isChapter ? 'illustration' : `portrait for ${name}`}…
            </span>
          </div>
        ) : (
          <span className="entity-card-art-placeholder muted">Not generated yet</span>
        )}
      </div>
      <div className="entity-card-body">
        <h5>{name}</h5>
        <p>{prompt}</p>
      </div>
    </div>
  );
}

// ─── Step Panel ───────────────────────────────────────────────────────────────
function StepPanel({ project, onRunStep }) {
  const [styleInput, setStyleInput] = useState('');
  const [characterGuidance, setCharacterGuidance] = useState('');
  const [actionError, setActionError] = useState('');

  const doneIdx    = statusIndex(project.status);
  const isAllDone  = project.status === 'DONE';
  const isRunning  = project.step_state === 'RUNNING';
  const isFailed   = project.step_state === 'FAILED';
  const currentStep = isAllDone ? null : STEPS[doneIdx];

  // Detect stuck step
  const isStuck = isRunning && project.step_started_at && (() => {
    const elapsed = Date.now() - new Date(project.step_started_at).getTime();
    const timeout = STEP_TIMEOUT_MS[doneIdx + 1] || 60_000;
    return elapsed > timeout;
  })();

  const handleRun = async () => {
    setActionError('');
    try {
      if (currentStep?.key === 'STYLE') {
        await onRunStep('STYLE', styleInput);
      } else {
        await onRunStep(currentStep?.key);
      }
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Something went wrong';
      setActionError(detail);
    }
  };

  if (isAllDone) {
    return (
      <div className="step-panel">
        <div className="step-panel-status">
          <span className="gd-num-circle gd-num-circle-done" style={{ width: 20, height: 20, fontSize: 11 }}>✓</span>
          All 5 steps complete — your book is fully illustrated!
        </div>
        <p className="step-panel-help">
          This project is done. Results are saved and visible below.
        </p>
      </div>
    );
  }

  if (isStuck) {
    return (
      <div className="step-panel">
        <div className="step-panel-status" style={{ color: 'var(--grad-orange-deep)' }}>
          ⚠️ Step {doneIdx + 1} appears to be stuck
        </div>
        <p className="step-panel-help">
          The server may have restarted mid-call. Everything completed before this step is safe.
          You can retry — it won't re-run previous steps.
        </p>
        <button
          className="gd-btn gd-btn-secondary"
          onClick={() => onRunStep(currentStep?.key, styleInput)}
          id="btn-retry-stuck"
        >
          Retry {currentStep?.label}
        </button>
      </div>
    );
  }

  if (isRunning) {
    const stepName = currentStep?.label || 'step';
    const runningCaption = {
      STYLE: 'Reading your book text and defining an art style…',
      CHARACTERS: 'Generating the character list from your book’s text…',
      PORTRAITS: 'Generating character portraits sequentially…',
      CHAPTERS: 'Generating a chapter illustration prompt…',
      ILLUSTRATIONS: 'Generating the chapter illustration scene…',
    }[currentStep?.key] || `Running ${stepName}…`;

    return (
      <div className="step-panel">
        <div className="step-panel-status">
          <span className="gd-spinner gd-spinner-sm" />
          {runningCaption}
        </div>
        <p className="step-panel-help">
          {doneIdx >= 2 && doneIdx <= 4
            ? 'Image generation takes 20–60 seconds. Images appear one by one below as they finish.'
            : 'This usually takes 5–15 seconds.'}
        </p>
      </div>
    );
  }

  // Render Step 1
  if (currentStep?.key === 'STYLE') {
    return (
      <div className="step-panel">
        {isFailed && project.step_error && <div className="step-error-box">⚠️ {project.step_error}</div>}
        <h3 style={{ fontSize: 16, margin: '0 0 8px' }}>Ready for the next step: Style</h3>
        <p className="step-panel-help" style={{ marginBottom: 16 }}>
          Define the artistic style of your book. You can specify a custom style or let Gemini choose one based on the text.
        </p>
        <div className="style-input-row">
          <label htmlFor="style-input">Optional Art Style Guidance</label>
          <input
            id="style-input"
            type="text"
            placeholder="e.g., Watercolor, soft lighting, 19th-century clothing..."
            value={styleInput}
            onChange={e => setStyleInput(e.target.value)}
          />
        </div>
        {actionError && <div className="step-error-box">{actionError}</div>}
        <button className="gd-btn gd-btn-primary" onClick={handleRun} id="btn-run-step-1">
          {isFailed ? 'Retry Style' : 'Generate Style'} →
        </button>
      </div>
    );
  }

  // Render Step 2
  if (currentStep?.key === 'CHARACTERS') {
    return (
      <div className="step-panel">
        {isFailed && project.step_error && <div className="step-error-box">⚠️ {project.step_error}</div>}
        <h3 style={{ fontSize: 16, margin: '0 0 8px' }}>Ready for the next step: Characters</h3>
        <p className="step-panel-help" style={{ marginBottom: 16 }}>
          Define the visual style of your characters based on the manuscript. You can provide optional guidance to refine the generated concepts.
        </p>
        <div className="style-input-row">
          <label htmlFor="char-input">Optional Art Style Guidance</label>
          <input
            id="char-input"
            type="text"
            placeholder="e.g., Watercolor, soft lighting, 19th-century clothing..."
            value={characterGuidance}
            onChange={e => setCharacterGuidance(e.target.value)}
          />
        </div>
        {actionError && <div className="step-error-box">{actionError}</div>}
        <button className="gd-btn gd-btn-primary" onClick={handleRun} id="btn-run-step-2">
          {isFailed ? 'Retry Characters' : 'Generate Characters'} →
        </button>
      </div>
    );
  }

  // Render Step 3
  if (currentStep?.key === 'PORTRAITS') {
    return (
      <div className="step-panel">
        {isFailed && project.step_error && <div className="step-error-box">⚠️ {project.step_error}</div>}
        <h3 style={{ fontSize: 16, margin: '0 0 8px' }}>Ready for the next step: Portraits</h3>
        <p className="step-panel-help" style={{ marginBottom: 16 }}>
          Generate character portraits sequentially. This step will produce a unique headshot illustration for each character extracted in the previous step.
        </p>
        {actionError && <div className="step-error-box">{actionError}</div>}
        <button className="gd-btn gd-btn-primary" onClick={handleRun} id="btn-run-step-3">
          {isFailed ? 'Retry Portraits' : 'Generate Portraits'} →
        </button>
      </div>
    );
  }

  // Render Step 4
  if (currentStep?.key === 'CHAPTERS') {
    return (
      <div className="step-panel">
        {isFailed && project.step_error && <div className="step-error-box">⚠️ {project.step_error}</div>}
        <h3 style={{ fontSize: 16, margin: '0 0 8px' }}>Ready for the next step: Chapters</h3>
        <p className="step-panel-help" style={{ marginBottom: 16 }}>
          Extract the most visually interesting chapter from the book. Gemini will analyze the narrative and write a detailed illustration prompt.
        </p>
        {actionError && <div className="step-error-box">{actionError}</div>}
        <button className="gd-btn gd-btn-primary" onClick={handleRun} id="btn-run-step-4">
          {isFailed ? 'Retry Chapters' : 'Extract Chapters'} →
        </button>
      </div>
    );
  }

  // Render Step 5
  if (currentStep?.key === 'ILLUSTRATIONS') {
    return (
      <div className="step-panel">
        {isFailed && project.step_error && <div className="step-error-box">⚠️ {project.step_error}</div>}
        <h3 style={{ fontSize: 16, margin: '0 0 8px' }}>Ready for the next step: Illustrations</h3>
        <p className="step-panel-help" style={{ marginBottom: 16 }}>
          Create a full scene illustration for the chapter. Gemini will combine the chapter details, character portraits, and the selected art style.
        </p>
        {actionError && <div className="step-error-box">{actionError}</div>}
        <button className="gd-btn gd-btn-primary" onClick={handleRun} id="btn-run-step-5">
          {isFailed ? 'Retry Illustrations' : 'Generate Illustrations'} →
        </button>
      </div>
    );
  }

  return null;
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function ProjectDetail() {
  const { id }     = useParams();
  const navigate   = useNavigate();
  const { user }   = useAuth();
  const [bookOpen, setBookOpen] = useState(false);

  const { project, setProject, loading, error, refresh } = useProjectPolling(id);

  const handleRunStep = async (stepKey, styleInput = '') => {
    const stepFns = {
      STYLE:         () => API.runStyle(id, styleInput),
      CHARACTERS:    () => API.runCharacters(id),
      PORTRAITS:     () => API.runPortraits(id),
      CHAPTERS:      () => API.runChapters(id),
      ILLUSTRATIONS: () => API.runIllustrations(id),
    };

    const fn = stepFns[stepKey];
    if (!fn) return;

    // Optimistic UI: show running immediately
    setProject(p => p ? { ...p, step_state: 'RUNNING', step_started_at: new Date().toISOString() } : p);

    try {
      const res = await fn();
      setProject(res.data);
      refresh();
    } catch (err) {
      await refresh(); // Load the FAILED/IDLE state from disk to clear the optimistic RUNNING state
      throw err; // Propagate to StepPanel so it shows the error message
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Navbar />
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span className="gd-spinner gd-spinner-lg" />
        </div>
        <Footer />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Navbar />
        <div className="app-body" style={{ flex: 1 }}>
          <div className="step-error-box">{error || 'Project not found'}</div>
          <button className="gd-btn gd-btn-secondary" onClick={() => navigate('/')}>← Back to projects</button>
        </div>
        <Footer />
      </div>
    );
  }

  const doneIdx    = statusIndex(project.status);
  const characters = project.characters || [];
  const portraits  = project.portraits  || [];
  const chapters   = project.chapters   || [];
  const illustrations = project.illustrations || [];

  // Per-item generating state
  const portraitsRunning  = project.step_state === 'RUNNING' && project.status === 'CHARACTERS_GENERATED';
  const illustRunning     = project.step_state === 'RUNNING' && project.status === 'CHAPTERS_GENERATED';

  const getPortraitPath = (char) => {
    const p = portraits.find(p => p.character_id === char.id || p.character_name === char.name);
    return p?.image_path || null;
  };
  const getIllustPath = (chap) => {
    const il = illustrations.find(i => i.chapter_id === chap.id || i.chapter_title === chap.title);
    return il?.image_path || null;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Navbar />

      <main className="app-body" style={{ flex: 1 }}>
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

        {/* Header */}
        <div className="detail-header">
          <h2 style={{ marginBottom: 6 }}>{project.title}</h2>
          <div className="detail-header-meta">
            <span>Created {formatDate(project.created_at)}</span>
            <span>·</span>
            <button onClick={() => setBookOpen(true)} id="btn-view-book">
              View book text
            </button>
          </div>
        </div>

        {/* Stepper */}
        <Stepper project={project} />

        {/* Main grid */}
        <div className="detail-grid">
          <div>
            {/* Step action panel */}
            <StepPanel project={project} onRunStep={handleRunStep} />

            {/* Style */}
            {project.style && (
              <>
                <div className="section-title">Art Style</div>
                <div className="side-panel">
                  <h5>Style</h5>
                  <p>{project.style}</p>
                </div>
              </>
            )}

            {/* Characters */}
            {characters.length > 0 && (
              <>
                <div className="section-title">Characters</div>
                <div className="entity-grid">
                  {characters.map((char, i) => (
                    <EntityCard
                      key={char.id}
                      name={char.name}
                      prompt={char.image_prompt}
                      imagePath={getPortraitPath(char)}
                      isGenerating={portraitsRunning && !getPortraitPath(char)}
                      isChapter={false}
                      index={i}
                    />
                  ))}
                </div>
              </>
            )}

            {/* Chapters */}
            {chapters.length > 0 && (
              <>
                <div className="section-title">Chapters</div>
                <div className="entity-grid entity-grid-full">
                  {chapters.map((chap, i) => (
                    <EntityCard
                      key={chap.id}
                      name={chap.title}
                      prompt={chap.illustration_prompt}
                      imagePath={getIllustPath(chap)}
                      isGenerating={illustRunning && !getIllustPath(chap)}
                      isChapter
                      index={i}
                    />
                  ))}
                </div>
              </>
            )}
          </div>

          {/* Right side panel — style info */}
          <div>
            <div className="side-panel">
              <h5>Status</h5>
              <p style={{ marginBottom: 8 }}>
                {project.status === 'DONE'
                  ? '✅ All steps complete'
                  : project.step_state === 'RUNNING'
                  ? `⏳ Step ${doneIdx + 1} running…`
                  : project.step_state === 'FAILED'
                  ? `❌ Step ${doneIdx + 1} failed`
                  : `Step ${doneIdx} / 5 complete`}
              </p>
              {project.style && (
                <>
                  <h5 style={{ marginTop: 16 }}>Art Style</h5>
                  <p>{project.style}</p>
                </>
              )}
              {project.style_source && (
                <p style={{ fontSize: 11, color: 'var(--grad-ink-3)', marginTop: 6 }}>
                  Source: {project.style_source === 'user_provided' ? 'User-provided' : 'AI-generated'}
                </p>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Book text modal */}
      {bookOpen && (
        <div
          className="modal-overlay"
          onClick={e => e.target === e.currentTarget && setBookOpen(false)}
          role="dialog"
          aria-modal
          aria-labelledby="book-modal-title"
        >
          <div className="modal-box">
            <div className="modal-head">
              <h4 id="book-modal-title">Full book text</h4>
              <button
                className="modal-close"
                onClick={() => setBookOpen(false)}
                aria-label="Close"
                id="btn-close-modal"
              >
                ✕
              </button>
            </div>
            <div className="modal-body">{project.book_text}</div>
          </div>
        </div>
      )}

      <Footer />
    </div>
  );
}
