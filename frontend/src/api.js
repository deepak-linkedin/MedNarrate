const API = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api';

function csrfToken(){ return sessionStorage.getItem('mednarrate_csrf') || ''; }
function rememberCsrf(data){ if(data?.csrf_token) sessionStorage.setItem('mednarrate_csrf',data.csrf_token); return data; }

async function request(path, options={}){
  const method=(options.method||'GET').toUpperCase();
  const headers={...(options.headers||{})};
  if(!['GET','HEAD','OPTIONS'].includes(method)){
    const token=csrfToken();
    if(token) headers['X-CSRF-Token']=token;
  }
  const res=await fetch(`${API}${path}`,{...options,headers,credentials:'include'});
  let data=null;
  try{data=await res.json()}catch{data={}}
  if(!res.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

export const authApi={
  register:async(body)=>rememberCsrf(await request('/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})),
  login:async(body)=>rememberCsrf(await request('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})),
  logout:async()=>{const r=await request('/auth/logout',{method:'POST'});sessionStorage.removeItem('mednarrate_csrf');return r},
  me:async()=>rememberCsrf(await request('/auth/me')),
  updateProfile:(body)=>request('/auth/profile',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),
};

export async function analyzeReport(file){
  const form=new FormData();
  form.append('report',file);
  form.append('debug','true');
  return request('/analyze',{method:'POST',body:form});
}

export const reportApi={
  list:()=>request('/reports'),
  get:(id)=>request(`/reports/${id}`),
};
