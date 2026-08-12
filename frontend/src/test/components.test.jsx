import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { AuthProvider } from '../context/AuthContext';

// Mock useNavigate and useLocation
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ pathname: '/' }),
  };
});

describe('Navbar Component', () => {
  it('renders brand and navigation links correctly', () => {
    // Seed localStorage user session
    localStorage.setItem('gradion_user', JSON.stringify({ name: 'Mira Hassan', email: 'mira@example.com' }));

    render(
      <BrowserRouter>
        <AuthProvider>
          <Navbar />
        </AuthProvider>
      </BrowserRouter>
    );

    // Verify logo and brand name exist
    expect(screen.getByText('Gradion')).toBeInTheDocument();
    
    // Verify user avatar displays initials
    expect(screen.getByText('MH')).toBeInTheDocument();
    
    // Verify user name is shown
    expect(screen.getByText('Mira Hassan')).toBeInTheDocument();
    
    // Verify Sign Out button exists
    expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument();

    localStorage.removeItem('gradion_user');
  });

  it('triggers logout and redirects to auth page', () => {
    localStorage.setItem('gradion_user', JSON.stringify({ name: 'Mira Hassan', email: 'mira@example.com' }));

    render(
      <BrowserRouter>
        <AuthProvider>
          <Navbar />
        </AuthProvider>
      </BrowserRouter>
    );

    const signOutBtn = screen.getByRole('button', { name: /sign out/i });
    fireEvent.click(signOutBtn);

    // Verify navigation to /auth is triggered on logout
    expect(mockNavigate).toHaveBeenCalledWith('/auth');
    expect(localStorage.getItem('gradion_user')).toBeNull();
  });
});

describe('Footer Component', () => {
  it('renders Gradion branding and terms links', () => {
    render(<Footer />);
    
    expect(screen.getByText('GRADION | Scaling Business')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /privacy policy/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /terms of service/i })).toBeInTheDocument();
  });
});
