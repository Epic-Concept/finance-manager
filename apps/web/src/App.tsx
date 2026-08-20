import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { CohortCard } from './components/CohortCard';
import { OverviewPage } from './pages/OverviewPage';

function Shell() {
  return (
    <div className="shell">
      <nav className="rail" aria-label="Quiet Ledger">
        <strong className="display" style={{ fontSize: '1.1rem' }}>
          Quiet Ledger
        </strong>
        <NavLink to="/review" className={({ isActive }) => (isActive ? 'active' : '')}>
          Review
        </NavLink>
        <NavLink
          to="/bootstrap"
          className={({ isActive }) => (isActive ? 'active' : '')}
        >
          Bootstrap
        </NavLink>
        <NavLink to="/overview" className={({ isActive }) => (isActive ? 'active' : '')}>
          Overview
        </NavLink>
      </nav>
      <main className="stage">
        <Routes>
          <Route path="/" element={<Navigate to="/review" replace />} />
          <Route path="/review" element={<CohortCard title="Review" />} />
          <Route
            path="/bootstrap"
            element={<CohortCard title="Bootstrap" coverage={0.74} />}
          />
          <Route path="/overview" element={<OverviewPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return <Shell />;
}
