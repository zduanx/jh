import React, { useState } from 'react';
import Sidebar from './Sidebar';
import './Layout.css';

function Layout({ children }) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className="app-layout">
      <Sidebar onToggle={setIsCollapsed} />
      <main className={`main-content ${isCollapsed ? 'sidebar-collapsed' : ''}`}>
        {children}
      </main>
    </div>
  );
}

export default Layout;
