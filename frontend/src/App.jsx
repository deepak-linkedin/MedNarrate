import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import LandingPage from './pages/LandingPage';
import { LoginPage, RegisterPage } from './pages/AuthPages';
import DashboardPage from './pages/DashboardPage';
import ProfilePage from './pages/ProfilePage';
import AnalyzePage from './pages/AnalyzePage';
import ReportPage from './pages/ReportPage';
export default function App(){return <BrowserRouter><AuthProvider><Routes><Route element={<Layout/>}><Route index element={<LandingPage/>}/><Route path="login" element={<LoginPage/>}/><Route path="register" element={<RegisterPage/>}/><Route path="dashboard" element={<ProtectedRoute><DashboardPage/></ProtectedRoute>}/><Route path="profile" element={<ProtectedRoute><ProfilePage/></ProtectedRoute>}/><Route path="analyze" element={<ProtectedRoute><AnalyzePage/></ProtectedRoute>}/><Route path="reports/:id" element={<ProtectedRoute><ReportPage/></ProtectedRoute>}/><Route path="*" element={<Navigate to="/" replace/>}/></Route></Routes></AuthProvider></BrowserRouter>}
