import { useState, useEffect } from 'react';
import './App.css';

interface HealthStatus {
  status: string;
  version: string;
}

function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/health')
      .then((res) => {
        if (!res.ok) throw new Error('API unavailable');
        return res.json();
      })
      .then(setHealth)
      .catch(() => setError('Unable to connect to API'));
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Finance Manager</h1>
        <p>Personal finance management application</p>
      </header>

      <main className="app-main">
        <section className="status-card">
          <h2>API Status</h2>
          {error && <p className="error">{error}</p>}
          {health && (
            <div className="status-info">
              <p>
                Status: <span className="status-healthy">{health.status}</span>
              </p>
              <p>Version: {health.version}</p>
            </div>
          )}
          {!health && !error && <p>Checking API status...</p>}
        </section>
      </main>
    </div>
  );
}

export default App;
