import { createContext, useContext, useEffect, useState } from 'react';
import { authApi } from '../api';

const AuthContext=createContext(null);
export function AuthProvider({children}){
  const [user,setUser]=useState(null),[loading,setLoading]=useState(true);
  useEffect(()=>{authApi.me().then(r=>setUser(r.user)).catch(()=>setUser(null)).finally(()=>setLoading(false))},[]);
  const value={user,loading,
    async login(payload){const r=await authApi.login(payload);setUser(r.user);return r.user},
    async register(payload){const r=await authApi.register(payload);setUser(r.user);return r.user},
    async logout(){await authApi.logout();setUser(null)},
    async updateProfile(payload){const r=await authApi.updateProfile(payload);setUser(r);return r},
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export const useAuth=()=>useContext(AuthContext);
