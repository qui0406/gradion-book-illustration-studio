import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import ProjectDetail from '../pages/ProjectDetail';
import { AuthProvider } from '../context/AuthContext';
import API from '../api/projects';

// Mock API
vi.mock('../api/projects', () => ({
  default: {
    getProject: vi.fn(),
    runStyle: vi.fn(),
    runCharacters: vi.fn(),
    runPortraits: vi.fn(),
    runChapters: vi.fn(),
    runIllustrations: vi.fn(),
  },
}));

const renderProjectDetail = (projectId = 'proj_test_1') => {
  localStorage.setItem('gradion_user', JSON.stringify({ name: 'Anh Qui', email: 'qui@example.com' }));
  return render(
    <MemoryRouter initialEntries={[`/projects/${projectId}`]}>
      <AuthProvider>
        <Routes>
          <Route path="/projects/:id" element={<ProjectDetail />} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>
  );
};

describe('ProjectDetail Step Orchestration & Polling Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders Step 1 panel and triggers Style step execution', async () => {
    const mockProject = {
      id: 'proj_test_1',
      title: 'Story Book',
      status: 'CREATED',
      step_state: 'IDLE',
      book_text: 'Once upon a time...',
      created_at: '2026-08-12T12:00:00Z',
      characters: [],
      portraits: [],
      chapters: [],
      illustrations: [],
    };

    API.getProject.mockResolvedValue({ data: mockProject });
    API.runStyle.mockResolvedValue({ data: { ...mockProject, status: 'STYLE_SET', style: 'Watercolor' } });

    renderProjectDetail();

    await waitFor(() => {
      expect(screen.getByText('Ready for the next step: Style')).toBeInTheDocument();
    });

    const runBtn = screen.getByRole('button', { name: /Generate Style/i });
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(API.runStyle).toHaveBeenCalledWith('proj_test_1', '');
    });
  });

  it('detects stuck RUNNING step and renders Retry button', async () => {
    const staleTime = new Date(Date.now() - 300_000).toISOString(); // 5 mins ago
    const mockStuckProject = {
      id: 'proj_test_1',
      title: 'Stuck Story',
      status: 'CREATED',
      step_state: 'RUNNING',
      step_started_at: staleTime,
      book_text: 'Sample content',
      created_at: '2026-08-12T12:00:00Z',
      characters: [],
      portraits: [],
      chapters: [],
      illustrations: [],
    };

    API.getProject.mockResolvedValue({ data: mockStuckProject });
    API.runStyle.mockResolvedValue({ data: { ...mockStuckProject, step_state: 'RUNNING' } });

    renderProjectDetail();

    await waitFor(() => {
      expect(screen.getByText(/Step 1 appears to be stuck/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Retry Style/i })).toBeInTheDocument();
    });

    const retryBtn = screen.getByRole('button', { name: /Retry Style/i });
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(API.runStyle).toHaveBeenCalledWith('proj_test_1', '');
    });
  });

  it('renders Step 3 Portraits ready panel and triggers portrait generation', async () => {
    const mockStep3Project = {
      id: 'proj_test_1',
      title: 'Portraits Story',
      status: 'CHARACTERS_GENERATED',
      step_state: 'IDLE',
      style: 'Watercolor',
      book_text: 'Sample content',
      created_at: '2026-08-12T12:00:00Z',
      characters: [
        { id: 'c1', name: 'Tấm', image_prompt: 'Tấm prompt' }
      ],
      portraits: [],
      chapters: [],
      illustrations: [],
    };

    API.getProject.mockResolvedValue({ data: mockStep3Project });
    API.runPortraits.mockResolvedValue({
      data: {
        ...mockStep3Project,
        status: 'PORTRAITS_GENERATED',
        portraits: [{ character_id: 'c1', character_name: 'Tấm', image_path: '/api/images/p1/portraits/c1.png' }]
      }
    });

    renderProjectDetail();

    await waitFor(() => {
      expect(screen.getByText('Ready for the next step: Portraits')).toBeInTheDocument();
    });

    const runBtn = screen.getByRole('button', { name: /Generate Portraits/i });
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(API.runPortraits).toHaveBeenCalledWith('proj_test_1');
    });
  });
});
