import { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { MdDashboard, MdCloudDownload, MdSearch, MdChecklist, MdLogout, MdChevronLeft, MdChevronRight } from 'react-icons/md';
import { useUser } from '../context/UserContext';
import Logo from './Logo';
import './Sidebar.css';

function Sidebar({ onToggle }) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);
  const { logout } = useUser();

  const handleLogout = () => {
    setShowLogoutConfirm(true);
  };

  const confirmLogout = () => {
    logout(); // Use context logout for centralized state management
  };

  const cancelLogout = () => {
    setShowLogoutConfirm(false);
  };

  const toggleSidebar = () => {
    const newState = !isCollapsed;
    setIsCollapsed(newState);
    if (onToggle) onToggle(newState);
  };

  useEffect(() => {
    if (onToggle) onToggle(isCollapsed);
  }, [isCollapsed, onToggle]);

  const navItems = [
    { path: '/dashboard', icon: MdDashboard, label: 'Dashboard' },
    { path: '/ingest', icon: MdCloudDownload, label: 'Ingest' },
    { path: '/search', icon: MdSearch, label: 'Search' },
    { path: '/track', icon: MdChecklist, label: 'Track' },
  ];

  return (
    <>
      <div className={`sidebar ${isCollapsed ? 'collapsed' : ''}`}>
        {/* Header Section */}
        <div className="sidebar-header">
          <div className="sidebar-title">
            <Logo size={36} />
            <span className="title-text">Job Track</span>
          </div>
        </div>

        {/* Toggle button - floats on right edge */}
        <button
          className="toggle-button-edge"
          onClick={toggleSidebar}
          aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? <MdChevronRight size={20} /> : <MdChevronLeft size={20} />}
        </button>

        {/* Navigation Items */}
        <nav className="sidebar-nav">
          {navItems.map((item) => {
            const IconComponent = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `nav-item ${isActive ? 'active' : ''}`
                }
                title={isCollapsed ? item.label : ''}
              >
                <span className="nav-icon">
                  <IconComponent size={22} />
                </span>
                <span className="nav-label">{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Logout Button */}
        <div className="sidebar-footer">
          <button
            className="logout-button"
            onClick={handleLogout}
            title={isCollapsed ? 'Logout' : ''}
          >
            <span className="nav-icon">
              <MdLogout size={22} />
            </span>
            <span className="nav-label">Logout</span>
          </button>
        </div>
      </div>

      {/* Logout Confirmation Modal */}
      {showLogoutConfirm && (
        <div className="modal-overlay" onClick={cancelLogout}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Confirm Logout</h2>
            <p>Are you sure you want to log out?</p>
            <div className="modal-actions">
              <button className="btn-cancel" onClick={cancelLogout}>
                Cancel
              </button>
              <button className="btn-confirm" onClick={confirmLogout}>
                Logout
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default Sidebar;
