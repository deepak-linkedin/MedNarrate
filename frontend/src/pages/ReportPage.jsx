import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, BookOpen, CircleHelp, FileSearch, ShieldCheck, Sparkles } from 'lucide-react';
import { reportApi } from '../api';
export default function ReportPage(){
    const {id}=useParams();
    
    const [result,setResult]=useState(()=>{
        try{
            return JSON.parse(sessionStorage.getItem(`report:${id}`))
        }catch{
            return null
        }
    }),[error,setError]=useState('');
    
    useEffect(()=>{if(!result)reportApi.get(id).then(setResult).catch(e=>setError(e.message))},[id,result]);
    
    if(error)return <main><div className="empty-card">{error}</div></main>;
    
    if(!result)return <main><div className="center-card">Loading report explanation…</div></main>;
    
    const n=result.narrative;
    
    const all=result.findings||result.important_findings;
    
    return <main className="results-wrap">
        <div className="result-top">
            <div><Link className="back-link" to="/dashboard"><ArrowLeft size={15}/>Back to reports</Link>
    
            <div className="eyebrow">YOUR REPORT EXPLANATION</div>
            
                <h1>{n.title}</h1>
            </div>
        </div>
        
        <section className="summary-grid">
            <Summary value={result.summary.total_findings} label="measured values"/>
            <Summary value={result.summary.abnormal_findings} label="outside range" accent/>
            <Summary value={result.summary.normal_findings} label="within range"/>
            <Summary value={result.summary.unknown_findings} label="range unknown"/>
        </section>
        
        <section className="card result-section">
            <Header icon={<FileSearch/>} title="Your report at a glance"/>
            
            <p className="lead-copy">{n.explanation}</p>
        </section>
        
        <section className="card result-section">
            <Header icon={<BookOpen/>} title="Important findings"/>
            <div className="finding-table">
                {/* <div className="finding-head">
                    <span>Test</span>
                    {/* <span>Your value</span> */}
                    {/* <span>Result / finding</span>
                    <span>Reference</span>
                    <span>Status</span>
                </div> */}
                <div className="finding-head">
                    <span>Test / finding</span>
                    <span>Result / finding</span>
                    <span>Reference</span>
                    <span>Status</span>
                </div>
                
                {/* {all.map((f,i)=><div className="finding-row" key={i}>
                    <strong>{f.test_name}</strong>
                    
                    <span>
                        {f.value
                            ? `${f.value} ${f.unit || ''}`.trim()
                            : f.description || 'Not applicable'}
                    </span>
                    
                    <span>{f.reference_range||'Not provided'}</span>
                    
                    <b className={`status ${f.status}`}>{f.status}</b>

                    </div>)
                } */}

                {all.map((f, i) => (
                        <div className="finding-row" key={i}>
                            <strong>{f.test_name}</strong>

                            <span>
                                {f.value
                                    ? `${f.value} ${f.unit || ''}`.trim()
                                    : f.description || 'Not applicable'}
                            </span>

                            <span>
                                {f.reference_range || 'Not applicable'}
                            </span>

                            <b className={`status ${f.status}`}>
                                {pretty(f.status)}
                            </b>
                        </div>
                    ))
                }
                </div>
                </section>
                
                <section className="two-results"><section className="card result-section"><Header icon={<Sparkles/>} title="How these findings connect"/>{result.relationships.length?result.relationships.map((x,i)=><p key={i}>{x}</p>):<p>No specific relationship was identified from the available findings.</p>}{result.possible_patterns?.length>0&&<><h3>Possible patterns</h3>{result.possible_patterns.map((x,i)=><p key={i}>{x}</p>)}</>}</section><section className="card result-section"><Header icon={<ShieldCheck/>} title="What this report cannot determine"/><ul>{result.limitations.map((x,i)=><li key={i}>{x}</li>)}</ul></section></section><section className="card result-section"><Header icon={<FileSearch/>} title="What you might notice"/>{result.possible_associations?.length?<><p className="muted">These are possible associations, not predictions about what you personally will experience.</p><ul>{result.possible_associations.map((x,i)=><li key={i}>{x}</li>)}</ul></>:<p>No symptom associations were included in the supported interpretation for this report.</p>}</section><section className="card result-section"><Header icon={<CircleHelp/>} title="Questions to discuss with your clinician"/><ul className="question-list">{result.questions_for_clinician.map((x,i)=><li key={i}>{x}</li>)}</ul></section><section className="two-results"><section className="card result-section"><Header icon={<Sparkles/>} title="Why am I seeing this explanation?"/><p className="muted">The underlying findings stay the same. Your profile changes communication style only.</p><div className="specs"><span>Age <b>{result.profile.age}</b></span><span>Education <b>{result.profile.education}</b></span><span>Medical knowledge <b>{result.profile.medical_knowledge}</b></span><span>Language <b>{result.profile.preferred_language}</b></span>{result.narrative_specification&&<><span>Vocabulary <b>{pretty(result.narrative_specification.vocabulary_level)}</b></span><span>Detail <b>{pretty(result.narrative_specification.detail_level)}</b></span><span>Analogies <b>{pretty(result.narrative_specification.analogy_usage)}</b></span></>}</div></section><section className="card result-section"><Header icon={<ShieldCheck/>} title="Important note"/><p>{n.important_note}</p></section></section>
                    
                    {/* {result.sources?.length>0&&<section className="card result-section sources"><Header icon={<BookOpen/>} title="Medical information sources"/><p className="muted">Evidence used to ground the interpretation. MedNarrate first searches its curated local index and can fall back to allow-listed medical websites when local coverage is insufficient.</p>{result.sources.slice(0,6).map((s,i)=><details key={i}><summary>{s.title||s.topic||s.source} · {s.organization||'source'}</summary><p>{s.text}</p><span className="source-meta">{s.origin?.replaceAll('_',' ')} · {s.source_reference?.startsWith('http')?<a href={s.source_reference} target="_blank" rel="noreferrer">Open source</a>:s.source_reference}</span></details>)}</section>} */}

                    {result.sources?.length > 0 && (
                        <section className="card result-section sources">
                            <Header
                                icon={<BookOpen />}
                                title="Medical information sources"
                            />

                            <p className="muted">
                                Medical reference material used to provide general context
                                for your report. MedNarrate first searches its curated
                                medical knowledge base and may use trusted online medical
                                sources when additional context is needed.
                            </p>

                            <div className="source-list">
                                {result.sources.slice(0, 5).map((source, index) => (
                                    <div
                                        className="source-card"
                                        key={`${source.url || source.title}-${index}`}
                                    >
                                        <div className="source-info">
                                            <h3>
                                                {source.title || "Medical reference"}
                                            </h3>

                                            <p className="source-organization">
                                                {source.organization || "Trusted medical source"}
                                            </p>

                                            {source.topic && (
                                                <p className="source-topic">
                                                    Relevant to: <strong>{source.topic}</strong>
                                                </p>
                                            )}

                                            <span className="source-meta">
                                                {source.origin === "online"
                                                    ? "Trusted online medical source"
                                                    : "Curated medical knowledge"}
                                            </span>
                                        </div>

                                        {source.url && (
                                            <a
                                                href={source.url}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="source-link"
                                            >
                                                Open source ↗
                                            </a>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}
                    
                    </main>}


function Summary({value,label,accent}) {

    return (
        <div className={`summary-card ${accent?'accent':''}`}>
            <b>{value}</b>
            <span>{label}</span>
        </div>
    );
}
function Header({icon,title}){
    return (
        <div className="result-section-title">
            <div>{icon}</div>
            <h2>{title}</h2>
        </div>
    );
}
function pretty(x=''){return String(x).replaceAll('_',' ')}
