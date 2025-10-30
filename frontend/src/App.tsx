import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Upload from "./pages/Upload";
import Dashboard from "./pages/Dashboard";
import Valuation from "./pages/Valuation";

export default function App(){
  return (
    <BrowserRouter>
      <div className="layout">
        {/* ... 사이드바 동일 ... */}
        <nav className="nav">
          <NavLink to="/" end className={({isActive}:{isActive:boolean})=> isActive? 'active' : ''}>📊 Dashboard</NavLink>
          <NavLink to="/upload" className={({isActive}:{isActive:boolean})=> isActive? 'active' : ''}>📤 Upload</NavLink>
          <NavLink to="/valuation" className={({isActive}:{isActive:boolean})=> isActive? 'active' : ''}>💰 Valuation</NavLink>
        </nav>
        {/* ... */}
        <main className="content">
          <Routes>
            <Route path="/" element={<Dashboard/>} />
            <Route path="/upload" element={<Upload/>} />
            <Route path="/valuation" element={<Valuation/>} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
