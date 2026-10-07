import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { FileText, LogOut, ShieldCheck, Sparkles, UserRound } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
export default function Layout(){
  const {user,logout}=useAuth(); const navigate=useNavigate();
  async function signOut(){await logout();navigate('/')}
  return <div className="app-shell">
    <header className="nav">
      <Link to={user?'/dashboard':'/'} className="brand"><div className="brand-mark"><Sparkles size={18}/></div><div><strong>MedNarrate</strong><span>Understand your report, in your language</span></div></Link>
      <div className="nav-actions">{user?<><NavLink to="/dashboard"><FileText size={16}/>Reports</NavLink><NavLink to="/profile"><UserRound size={16}/>Profile</NavLink><button className="nav-button" onClick={signOut}><LogOut size={16}/>Logout</button></>:<><div className="safety-pill"><ShieldCheck size={16}/>Educational, not diagnostic</div><Link className="nav-link" to="/login">Sign in</Link><Link className="nav-cta" to="/register">Get started</Link></>}</div>
    </header>
    <Outlet/>
    <footer>MedNarrate explains medical reports for educational purposes. It does not diagnose conditions or replace qualified medical care.</footer>
  </div>
}
