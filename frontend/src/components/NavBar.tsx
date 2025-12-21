import React from 'react';
import { NavLink } from 'react-router-dom';

const NavBar: React.FC = () => {
  return (
    <nav className="navbar navbar-expand-lg navbar-light bg-light border-bottom">
      <div className="container">
        <NavLink className="navbar-brand fw-semibold" to="/">
          SatyaSethu
        </NavLink>

        <button
          className="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#mainNavbar"
          aria-controls="mainNavbar"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span className="navbar-toggler-icon" />
        </button>

        <div className="collapse navbar-collapse" id="mainNavbar">
          <ul className="navbar-nav me-auto mb-2 mb-lg-0">
            <li className="nav-item">
              <NavLink
                to="/"
                end
                className={({ isActive }) =>
                  `nav-link${isActive ? ' active fw-semibold' : ''}`
                }
              >
                Home
              </NavLink>
            </li>

            <li className="nav-item">
              <NavLink
                to="/protect"
                className={({ isActive }) =>
                  `nav-link${isActive ? ' active fw-semibold' : ''}`
                }
              >
                Protect
              </NavLink>
            </li>

            <li className="nav-item">
              <NavLink
                to="/policies"
                className={({ isActive }) =>
                  `nav-link${isActive ? ' active fw-semibold' : ''}`
                }
              >
                Policies
              </NavLink>
            </li>

            <li className="nav-item">
              <NavLink
                to="/evidence"
                className={({ isActive }) =>
                  `nav-link${isActive ? ' active fw-semibold' : ''}`
                }
              >
                Evidence
              </NavLink>
            </li>

            <li className="nav-item">
              <NavLink
                to="/audit"
                className={({ isActive }) =>
                  `nav-link${isActive ? ' active fw-semibold' : ''}`
                }
              >
                Audit
              </NavLink>
            </li>
          </ul>

          <span className="navbar-text text-muted small">
            Policy Management UI
          </span>
        </div>
      </div>
    </nav>
  );
};

export default NavBar;