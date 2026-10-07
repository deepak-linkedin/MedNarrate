import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertCircle, FileText, Image, ShieldCheck, Sparkles, Upload } from 'lucide-react';
import { analyzeReport } from '../api';
import { useAuth } from '../context/AuthContext';

export default function AnalyzePage(){
  const {user}=useAuth(); const nav=useNavigate();
  const [file,setFile]=useState(null),[loading,setLoading]=useState(false),[error,setError]=useState('');
  async function submit(e){
    e.preventDefault();
    if(!file){setError('Choose a PDF, TXT, PNG, JPG, or JPEG medical report first.');return}
    setLoading(true);setError('');
    try{
      const result=await analyzeReport(file);
      sessionStorage.setItem(`report:${result.session_id}`,JSON.stringify(result));
      nav(`/reports/${result.session_id}`)
    }catch(e){setError(e.message)}finally{setLoading(false)}
  }
  return <main className="analyze-page">
    <section className="page-title"><div className="eyebrow">NEW ANALYSIS</div><h1>Upload your medical report</h1><p>Upload a digital report or a clear photo. MedNarrate extracts the findings, grounds them with medical evidence, and explains them using your saved profile.</p></section>
    <form className="card form-card" onSubmit={submit}>
      <div className="section-heading"><div className="icon-box"><FileText/></div><div><h2>Report file</h2><p>PDF, TXT, PNG, JPG or JPEG · maximum 15 MB</p></div></div>
      <label className="dropzone"><input type="file" accept=".pdf,.txt,.png,.jpg,.jpeg,application/pdf,text/plain,image/png,image/jpeg" onChange={e=>setFile(e.target.files?.[0]||null)}/><Upload/><strong>{file?file.name:'Choose your medical report'}</strong><span>{file?'Ready to analyze':'Click to browse a report or clear report image'}</span></label>
      <div className="using-profile"><div><Sparkles/><strong>Using your profile</strong></div><div className="mini-tags"><span>{user.profile.age} years</span><span>{user.profile.education}</span><span>{user.profile.medical_knowledge}</span><span>{user.profile.preferred_language}</span></div></div>
      <div className="upload-privacy"><Image size={16}/>Images and scanned PDFs are read with OCR. Clear, straight, well-lit photos produce better extraction.</div>
      {error&&<div className="error"><AlertCircle size={18}/>{error}</div>}
      <button className="primary" disabled={loading}>{loading?<><span className="spinner"/>Analyzing report…</>:<><Sparkles size={18}/>Analyze with MedNarrate</>}</button>
      <div className="upload-privacy"><ShieldCheck size={16}/>Raw uploaded files are processed in memory and are not intentionally persisted. Extracted findings and generated explanations are stored in your report history.</div>
    </form>
  </main>
}
