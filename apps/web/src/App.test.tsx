import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import App from './App';

describe('App', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders the header', () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'healthy', version: '0.1.0' }),
      })
    );

    render(<App />);
    expect(screen.getByText('Finance Manager')).toBeInTheDocument();
  });

  it('displays API status when healthy', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'healthy', version: '0.1.0' }),
      })
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('healthy')).toBeInTheDocument();
    });
  });

  it('displays error when API is unavailable', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
      })
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Unable to connect to API')).toBeInTheDocument();
    });
  });
});
