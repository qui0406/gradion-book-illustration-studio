import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import ProjectList from '../pages/ProjectList';
import Navbar from '../components/Navbar';
import { EntityCard } from '../pages/ProjectDetail';
import { AuthProvider } from '../context/AuthContext';
import API from '../api/projects';

// Mock useNavigate and useLocation
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock API calls
vi.mock('../api/projects', () => ({
  default: {
    listProjects: vi.fn(),
  },
}));

const renderProjectList = () => {
  localStorage.setItem('gradion_user', JSON.stringify({ name: 'Mira Hassan', email: 'mira@example.com' }));
  return render(
    <BrowserRouter>
      <AuthProvider>
        <ProjectList />
      </AuthProvider>
    </BrowserRouter>
  );
};

describe('ProjectList UI States', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('renders loading state initially while fetching projects', () => {
    // Return a promise that doesn't resolve immediately to keep it in loading state
    API.listProjects.mockReturnValue(new Promise(() => {}));

    const { container } = renderProjectList();

    // Verify loading spinner is displayed
    const spinner = container.querySelector('.gd-spinner');
    expect(spinner).toBeInTheDocument();
  });

  it('renders empty state when user has no projects', async () => {
    API.listProjects.mockResolvedValue({ data: [] });

    renderProjectList();

    // Wait for the API call to resolve and loading to finish
    await waitFor(() => {
      expect(screen.queryByRole('status')).not.toBeInTheDocument();
    });

    // Check empty state texts
    expect(screen.getByText('No projects yet')).toBeInTheDocument();
    expect(screen.getByText('Create your first project to get started with book illustration.')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: /\+ New project/i }).length).toBeGreaterThan(0);
  });

  it('renders project list when projects are loaded successfully', async () => {
    const mockProjects = [
      {
        id: 'proj_1',
        title: 'The Wind in the Willows',
        status: 'DONE',
        created_at: '2026-08-12T12:00:00Z',
        characters: [],
        portraits: [],
        chapters: [],
        illustrations: [],
      },
      {
        id: 'proj_2',
        title: "Alice's Adventures",
        status: 'STYLE_SET',
        created_at: '2026-08-12T12:30:00Z',
        characters: [],
        portraits: [],
        chapters: [],
        illustrations: [],
      },
    ];

    API.listProjects.mockResolvedValue({ data: mockProjects });

    renderProjectList();

    // Verify project cards are rendered
    await waitFor(() => {
      expect(screen.getByText('The Wind in the Willows')).toBeInTheDocument();
      expect(screen.getByText("Alice's Adventures")).toBeInTheDocument();
    });

    // Verify progress bars are displayed
    expect(screen.getByText(/Step 5 of 5/i)).toBeInTheDocument();
    expect(screen.getByText(/Step 1 of 5/i)).toBeInTheDocument();
  });

  it('renders error state when the API call fails', async () => {
    API.listProjects.mockRejectedValue(new Error('Network Error'));

    renderProjectList();

    // Verify error box is rendered
    await waitFor(() => {
      expect(screen.getByText('Failed to load projects')).toBeInTheDocument();
    });
  });
});

describe('Navbar Component', () => {
  const mockSignOut = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  const renderNavbar = () => {
    localStorage.setItem('gradion_user', JSON.stringify({ name: 'Mira Hassan', email: 'mira@example.com' }));
    return render(
      <BrowserRouter>
        <AuthProvider>
          <Navbar />
        </AuthProvider>
      </BrowserRouter>
    );
  };

  it('renders user name and initials correctly', () => {
    renderNavbar();

    // Verify avatar initials (M and H) are rendered
    expect(screen.getByText('MH')).toBeInTheDocument();

    // Verify full name is rendered
    expect(screen.getByText('Mira Hassan')).toBeInTheDocument();

    // Verify Sign Out button is rendered
    expect(screen.getByRole('button', { name: /Sign Out/i })).toBeInTheDocument();
  });

  it('clears session and redirects to /auth on Sign Out', async () => {
    const { container } = renderNavbar();

    const signOutBtn = screen.getByRole('button', { name: /Sign Out/i });
    fireEvent.click(signOutBtn);

    // Verify local storage is cleared
    expect(localStorage.getItem('gradion_user')).toBeNull();

    // Verify navigation was triggered to /auth
    expect(mockNavigate).toHaveBeenCalledWith('/auth');
  });
});

describe('EntityCard Component', () => {
  it('renders "Not generated yet" state when image is missing and not generating', () => {
    render(
      <EntityCard
        name="Tấm"
        prompt="A beautiful woman in traditional dress"
        imagePath={null}
        isGenerating={false}
        isChapter={false}
        index={0}
      />
    );

    expect(screen.getByText('Tấm')).toBeInTheDocument();
    expect(screen.getByText('A beautiful woman in traditional dress')).toBeInTheDocument();
    expect(screen.getByText('Not generated yet')).toBeInTheDocument();
  });

  it('renders generating/loading state for characters', () => {
    const { container } = render(
      <EntityCard
        name="Tấm"
        prompt="A beautiful woman"
        imagePath={null}
        isGenerating={true}
        isChapter={false}
        index={0}
      />
    );

    // Verify spinner is rendered
    expect(container.querySelector('.gd-spinner')).toBeInTheDocument();
    expect(screen.getByText('Generating portrait for Tấm…')).toBeInTheDocument();
  });

  it('renders generating/loading state for chapters', () => {
    const { container } = render(
      <EntityCard
        name="Chapter 1"
        prompt="Chapter illustration"
        imagePath={null}
        isGenerating={true}
        isChapter={true}
        index={0}
      />
    );

    expect(container.querySelector('.gd-spinner')).toBeInTheDocument();
    expect(screen.getByText('Generating illustration…')).toBeInTheDocument();
  });

  it('renders image successfully when imagePath is provided', () => {
    render(
      <EntityCard
        name="Tấm"
        prompt="A beautiful woman"
        imagePath="/images/p1/portraits/Tấm.png"
        isGenerating={false}
        isChapter={false}
        index={0}
      />
    );

    const img = screen.getByRole('img', { name: 'Tấm' });
    expect(img).toBeInTheDocument();
    expect(img.getAttribute('src')).toContain('/images/p1/portraits/Tấm.png');
  });
});

