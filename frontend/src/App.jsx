import { Routes, Route, NavLink } from "react-router-dom";
import Upload from "./pages/Upload.jsx";
import ThreadView from "./pages/ThreadView.jsx";
import GeoMap from "./pages/GeoMap.jsx";
import Report from "./pages/Report.jsx";

export default function App() {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">◆</span>
          Email Forensic Intelligence
        </div>
        <nav className="nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Upload
          </NavLink>
          <NavLink to="/threads" className={({ isActive }) => (isActive ? "active" : "")}>
            Threads
          </NavLink>
        </nav>
      </header>

      <main className="content">
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/threads" element={<ThreadView />} />
          <Route path="/threads/:threadId" element={<ThreadView />} />
          <Route path="/emails/:emailId/map" element={<GeoMap />} />
          <Route path="/emails/:emailId/report" element={<Report />} />
        </Routes>
      </main>
    </div>
  );
}
