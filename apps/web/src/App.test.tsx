import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from './App';
import { TierMark } from './components/ui';

describe('Quiet Ledger shell', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ items: [], singletons: [] }),
      })
    );
  });

  it('renders Quiet Ledger navigation', () => {
    render(
      <MemoryRouter initialEntries={['/review']}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByText('Quiet Ledger')).toBeInTheDocument();
    expect(screen.getByText('Review')).toBeInTheDocument();
    expect(screen.getByText('Bootstrap')).toBeInTheDocument();
  });

  it('shows empty queue state', async () => {
    render(
      <MemoryRouter initialEntries={['/review']}>
        <App />
      </MemoryRouter>
    );
    expect(await screen.findByText(/Queue is clear/)).toBeInTheDocument();
  });

  it('shows singleton residual when nothing clustered', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ items: [], singletons: [11, 12] }),
      })
    );
    render(
      <MemoryRouter initialEntries={['/review']}>
        <App />
      </MemoryRouter>
    );
    expect(await screen.findByText(/singleton residual/i)).toBeInTheDocument();
  });
});

describe('TierMark', () => {
  it('renders proof as four dots', () => {
    render(<TierMark strength={3} />);
    expect(screen.getByTestId('tier-mark').textContent).toMatch(/PROOF/);
  });
});
