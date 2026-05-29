import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import DriversPage from './pages/DriversPage';
import GoldenBlocksPage from './pages/GoldenBlocksPage';
import BuildPage from './pages/BuildPage';
import SettingsPage from './pages/SettingsPage';

function App() {
  return (
    <div className="app">
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/drivers" element={<DriversPage />} />
          <Route path="/blocks" element={<GoldenBlocksPage />} />
          <Route path="/build" element={<BuildPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
