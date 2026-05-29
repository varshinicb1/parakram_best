import { NavLink } from 'react-router-dom';

function Sidebar() {
  return (
    <nav className="sidebar">
      <div className="sidebar-header">
        <h1>Parakram Studio</h1>
        <p>Zero-Code IoT IDE</p>
      </div>
      <div className="sidebar-nav">
        <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          ◈ Dashboard
        </NavLink>
        <NavLink to="/drivers" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          ⚙ Drivers
        </NavLink>
        <NavLink to="/blocks" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          ▦ Golden Blocks
        </NavLink>
        <NavLink to="/build" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          ▸ Build & Flash
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          ☰ Settings
        </NavLink>
      </div>
    </nav>
  );
}

export default Sidebar;
