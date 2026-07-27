import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const API_BASE = 'http://localhost:8000';
const CELL_SIZE = 24; // Visual scaling factor

function App() {
  const [env, setEnv] = useState(null);
  const [points, setPoints] = useState([]);
  const [routers, setRouters] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [history, setHistory] = useState([]);
  const [sinrMap, setSinrMap] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('map');
  const [errorMessage, setErrorMessage] = useState(null);
  const [apiConnected, setApiConnected] = useState(false);
  const heatmapRef = useRef(null);

  // Fetch initial environment with auto-retry
  useEffect(() => {
    let isMounted = true;
    let timer = null;

    const fetchEnv = async () => {
      try {
        const res = await fetch(`${API_BASE}/environment`);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        const data = await res.json();
        if (isMounted) {
          setEnv(data);
          setRouters(data.routers || []);
          setApiConnected(true);
          setErrorMessage(null);
        }
      } catch (err) {
        if (isMounted) {
          setApiConnected(false);
          // Retry fetching after 3 seconds if not connected
          timer = setTimeout(fetchEnv, 3000);
        }
      }
    };

    fetchEnv();

    return () => {
      isMounted = false;
      if (timer) clearTimeout(timer);
    };
  }, []);

  // Redraw canvas whenever activeTab becomes 'map', or sinrMap/env changes
  useEffect(() => {
    if (activeTab === 'map' && sinrMap && env) {
      const animationFrame = requestAnimationFrame(() => {
        drawHeatmap(sinrMap);
      });
      return () => cancelAnimationFrame(animationFrame);
    }
  }, [activeTab, sinrMap, env]);

  const handleMapClick = (e) => {
    if (!env) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / CELL_SIZE;
    const y = (e.clientY - rect.top) / CELL_SIZE;
    const newPt = { x: Math.floor(x), y: Math.floor(y) };
    
    // Clamp points within boundaries
    if (newPt.x >= 0 && newPt.x < env.length && newPt.y >= 0 && newPt.y < env.breadth) {
      setPoints(prev => [...prev, newPt]);
    }
  };

  const handleSimulate = async () => {
    if (points.length === 0) return;
    setLoading(true);
    setErrorMessage(null);
    try {
      const response = await fetch(`${API_BASE}/simulate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ points, routers: routers.length > 0 ? routers : undefined })
      });

      if (!response.ok) {
        throw new Error(`Simulation failed with status code ${response.status}`);
      }

      const data = await response.json();
      setRouters(data.routers);
      setSinrMap(data.sinr_map);
      setMetrics({
        initialCov: data.initial_coverage,
        finalCov: data.final_coverage,
        inc: data.reachability_increase,
        time: data.optimization_time,
        move: data.total_movement
      });
      setHistory(prev => [...prev, {
        step: prev.length,
        coverage: data.final_coverage,
        movement: data.total_movement,
        time: data.optimization_time
      }]);
    } catch (err) {
      console.error(err);
      setErrorMessage(`Optimization error: ${err.message}. Make sure API backend is active.`);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setPoints([]);
    setMetrics(null);
    setHistory([]);
    setSinrMap(null);
    setErrorMessage(null);
    if (env) {
      setRouters(env.routers);
    }
    const canvas = heatmapRef.current;
    if (canvas && env) {
      const ctx = canvas.getContext('2d');
      if (ctx) ctx.clearRect(0, 0, env.length * CELL_SIZE, env.breadth * CELL_SIZE);
    }
  };

  const handleDownloadHeatmap = () => {
    if (!env) return;
    
    const compositeCanvas = document.createElement('canvas');
    compositeCanvas.width = env.length * CELL_SIZE;
    compositeCanvas.height = env.breadth * CELL_SIZE;
    const ctx = compositeCanvas.getContext('2d');
    
    // Fill with dark background
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, compositeCanvas.width, compositeCanvas.height);
    
    // Draw heatmap data if available
    if (sinrMap) {
      for (let x = 0; x < env.length; x++) {
        for (let y = 0; y < env.breadth; y++) {
          const val = sinrMap[x][y];
          const normalized = Math.max(0, Math.min(1, (val + 10) / 40));
          const hue = (1.0 - normalized) * 240;
          ctx.fillStyle = `hsla(${hue}, 100%, 50%, 0.8)`;
          ctx.fillRect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
        }
      }
    } else if (heatmapRef.current) {
      ctx.drawImage(heatmapRef.current, 0, 0);
    }

    // Draw walls
    env.walls.forEach(w => {
      const isH = w.o === 'h';
      const left = (isH ? w.s : w.p) * CELL_SIZE;
      const top = (isH ? w.p : w.s) * CELL_SIZE;
      const width = (isH ? w.e - w.s : 0.5) * CELL_SIZE;
      const height = (isH ? 0.5 : w.e - w.s) * CELL_SIZE;
      if (w.m === 'glass') ctx.fillStyle = 'rgba(125, 211, 252, 0.8)';
      else if (w.m === 'wood') ctx.fillStyle = 'rgba(217, 119, 6, 0.8)';
      else ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
      ctx.fillRect(left, top, isH ? width : 4, isH ? 4 : height);
    });

    // Draw human nodes
    ctx.fillStyle = '#f43f5e';
    points.forEach(pt => {
      ctx.beginPath();
      ctx.arc((pt.x + 0.5) * CELL_SIZE, (pt.y + 0.5) * CELL_SIZE, 6, 0, 2 * Math.PI);
      ctx.fill();
    });

    // Draw routers and directional beams
    routers.forEach(r => {
      const cx = r.x * CELL_SIZE;
      const cy = r.y * CELL_SIZE;

      const beamRadius = Math.sqrt(compositeCanvas.width * compositeCanvas.width + compositeCanvas.height * compositeCanvas.height);
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      const startAngle = (r.phi - r.alpha / 2) * Math.PI / 180;
      const endAngle = (r.phi + r.alpha / 2) * Math.PI / 180;
      ctx.arc(cx, cy, beamRadius, startAngle, endAngle);
      ctx.fillStyle = 'rgba(16, 185, 129, 0.15)';
      ctx.fill();

      ctx.beginPath();
      ctx.arc(cx, cy, 8, 0, 2 * Math.PI);
      ctx.fillStyle = '#10b981';
      ctx.fill();

      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(r.phi * Math.PI / 180) * 15, cy + Math.sin(r.phi * Math.PI / 180) * 15);
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.stroke();
    });
    
    const link = document.createElement('a');
    link.download = 'thz_heatmap_analysis.png';
    link.href = compositeCanvas.toDataURL('image/png');
    link.click();
  };

  const drawHeatmap = (mapData) => {
    const canvas = heatmapRef.current;
    if (!canvas || !env || !mapData) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, env.length * CELL_SIZE, env.breadth * CELL_SIZE);
    
    for (let x = 0; x < env.length; x++) {
      for (let y = 0; y < env.breadth; y++) {
        const val = mapData[x][y];
        const normalized = Math.max(0, Math.min(1, (val + 10) / 40));
        const hue = (1.0 - normalized) * 240; // 240 is blue, 0 is red
        ctx.fillStyle = `hsla(${hue}, 100%, 50%, 0.8)`;
        ctx.fillRect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
      }
    }
  };

  if (!env) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        backgroundColor: '#0f172a',
        color: 'white',
        gap: '16px',
        fontFamily: 'Outfit, sans-serif'
      }}>
        <div className="spinner"></div>
        <h2>Connecting to Simulation Backend...</h2>
        <p style={{ color: '#94a3b8', fontSize: '14px' }}>
          Searching for API at <code>http://localhost:8000</code>. Retrying automatically...
        </p>
      </div>
    );
  }

  const mapWidth = env.length * CELL_SIZE;
  const mapHeight = env.breadth * CELL_SIZE;

  return (
    <div className="dashboard-container">
      <div className="sidebar">
        <h2 style={{color: 'white', marginBottom: '10px'}}>Control Panel</h2>
        <p style={{color: 'var(--text-muted)', fontSize: '14px'}}>
          Click on the map to add humans, then run the simulation to optimize THz router placements.
        </p>

        {errorMessage && (
          <div style={{
            background: 'rgba(244, 63, 94, 0.15)',
            border: '1px solid rgba(244, 63, 94, 0.4)',
            borderRadius: '12px',
            padding: '12px',
            color: '#f43f5e',
            fontSize: '13px'
          }}>
            {errorMessage}
          </div>
        )}

        <button className="btn" onClick={handleSimulate} disabled={loading || points.length === 0}>
          {loading ? 'Optimizing...' : 'Run Optimization'}
        </button>
        <button 
          className="btn" 
          style={{background: 'rgba(255,255,255,0.1)', color: 'var(--text-main)', marginTop: '-10px'}} 
          onClick={handleReset}
        >
          Reset Environment
        </button>

        {metrics && (
          <button 
            className="btn" 
            style={{background: 'rgba(16, 185, 129, 0.2)', color: 'var(--accent-success)', marginTop: '-10px'}} 
            onClick={handleDownloadHeatmap}
          >
            Download HD Heatmap
          </button>
        )}

        {metrics && (
          <div style={{display:'flex', flexDirection:'column', gap:'12px', marginTop:'20px'}}>
            <div className="metric-card">
              <div className="metric-label">Initial Coverage</div>
              <div className="metric-value">{metrics.initialCov.toFixed(1)}<span className="metric-unit">%</span></div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Optimized Coverage</div>
              <div className="metric-value" style={{color: 'var(--accent-success)'}}>
                {metrics.finalCov.toFixed(1)}<span className="metric-unit">%</span>
              </div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Process Time</div>
              <div className="metric-value">{metrics.time.toFixed(2)}<span className="metric-unit">s</span></div>
            </div>
            <div className="metric-card">
              <div className="metric-label">Total Movement</div>
              <div className="metric-value">{metrics.move.toFixed(2)}<span className="metric-unit">m</span></div>
            </div>
          </div>
        )}
      </div>

      <div className="main-content">
        <div className="header">
          <div>
            <h1>APSO THz Dashboard</h1>
            <p style={{fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px'}}>
              Adaptive Particle Swarm Optimization for Terahertz Wireless Networks
            </p>
          </div>
          <div style={{display:'flex', gap:'20px', alignItems: 'center'}}>
             <div style={{display:'flex', alignItems:'center', gap:'8px'}}>
               <div style={{width:'12px', height:'12px', borderRadius:'50%', background:'#f43f5e'}}></div>
               <span style={{fontSize:'14px', color:'var(--text-muted)'}}>Human ({points.length})</span>
             </div>
             <div style={{display:'flex', alignItems:'center', gap:'8px'}}>
               <div style={{width:'12px', height:'12px', borderRadius:'50%', background:'#10b981'}}></div>
               <span style={{fontSize:'14px', color:'var(--text-muted)'}}>Router ({routers.length})</span>
             </div>
          </div>
        </div>

        <div style={{display: 'flex', gap: '10px', padding: '0 32px'}}>
          <button 
            className="btn" 
            style={{ width: 'auto', background: activeTab === 'map' ? 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)' : 'rgba(255,255,255,0.1)' }}
            onClick={() => setActiveTab('map')}
          >
            Map View
          </button>
          <button 
            className="btn" 
            style={{ width: 'auto', background: activeTab === 'graphs' ? 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)' : 'rgba(255,255,255,0.1)' }}
            onClick={() => setActiveTab('graphs')}
          >
            Graphs & Analytics
          </button>
        </div>

        {activeTab === 'map' && (
        <div className="map-container">
          <div className="map-wrapper" style={{width: mapWidth, height: mapHeight}} onClick={handleMapClick}>
            <canvas 
              ref={heatmapRef} 
              width={mapWidth} 
              height={mapHeight} 
              className="heatmap-canvas"
            />
            {env.walls.map((w, i) => {
              const isH = w.o === 'h';
              const left = (isH ? w.s : w.p) * CELL_SIZE;
              const top = (isH ? w.p : w.s) * CELL_SIZE;
              const width = (isH ? w.e - w.s : 0.5) * CELL_SIZE;
              const height = (isH ? 0.5 : w.e - w.s) * CELL_SIZE;
              return (
                <div key={i} className={`wall ${w.m}`} style={{
                  left, top, width: isH ? width : 4, height: isH ? 4 : height
                }} />
              )
            })}
            
            {points.map((pt, i) => (
              <div key={i} className="human-node" style={{ left: (pt.x + 0.5) * CELL_SIZE, top: (pt.y + 0.5) * CELL_SIZE }} />
            ))}

            {routers.map((r, i) => {
               const beamRadius = Math.sqrt(mapWidth * mapWidth + mapHeight * mapHeight);
               const beamDiameter = beamRadius * 2;
               return (
               <div key={`router-${i}`} className="router-node" style={{ left: r.x * CELL_SIZE, top: r.y * CELL_SIZE }}>
                 <div className="beam-ray" style={{
                   position: 'absolute',
                   left: `-${beamRadius}px`, top: `-${beamRadius}px`,
                   width: `${beamDiameter}px`, height: `${beamDiameter}px`,
                   borderRadius: '50%',
                   background: `conic-gradient(from ${r.phi - r.alpha/2 + 90}deg at 50% 50%, rgba(16, 185, 129, 0.15) ${r.alpha}deg, transparent ${r.alpha}deg)`,
                   pointerEvents: 'none',
                   zIndex: -1
                 }}></div>
                 <div style={{
                    position: 'absolute', top: '50%', left: '50%', width: '18px', height: '2px',
                    background: '#fff', transformOrigin: '0% 50%', transform: `rotate(${r.phi}deg)`,
                    pointerEvents: 'none'
                 }}></div>
               </div>
               );
            })}
            
            {loading && (
              <div className="loading-overlay">
                <div className="spinner"></div>
                <div style={{ marginTop: '12px', color: 'white', fontWeight: 500 }}>Optimizing THz Beams & Positions...</div>
              </div>
            )}
          </div>
          
          <div className="sinr-legend">
            <div className="legend-title">SINR Signal Map Legend</div>
            <div className="legend-bar"></div>
            <div className="legend-labels">
              <span>-10 dB (Poor)</span>
              <span>0 dB</span>
              <span>10 dB</span>
              <span>20 dB</span>
              <span>30+ dB (Excellent)</span>
            </div>
          </div>
        </div>
        )}

        {activeTab === 'graphs' && (
          <div className="map-container" style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: '24px', overflowY: 'auto' }}>
            <h2 style={{color: 'white', marginBottom: '4px'}}>Graphs & Performance Analytics</h2>
            <p style={{color: 'var(--text-muted)', fontSize: '14px'}}>
              Comprehensive analysis of APSO algorithm convergence, signal distribution, and router performance.
            </p>

            {metrics ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px', width: '100%' }}>
                <div className="metric-card" style={{ background: 'rgba(255,255,255,0.04)', padding: '20px' }}>
                  <h3 style={{ fontSize: '16px', color: '#60a5fa', marginBottom: '16px' }}>Coverage Comparison</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                        <span>Before Optimization</span>
                        <span>{metrics.initialCov.toFixed(1)}%</span>
                      </div>
                      <div style={{ height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{ width: `${Math.min(100, metrics.initialCov)}%`, height: '100%', background: '#f59e0b' }}></div>
                      </div>
                    </div>

                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                        <span>After Optimization</span>
                        <span style={{ color: '#10b981', fontWeight: 600 }}>{metrics.finalCov.toFixed(1)}%</span>
                      </div>
                      <div style={{ height: '8px', background: 'rgba(255,255,255,0.1)', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{ width: `${Math.min(100, metrics.finalCov)}%`, height: '100%', background: '#10b981' }}></div>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="metric-card" style={{ background: 'rgba(255,255,255,0.04)', padding: '20px' }}>
                  <h3 style={{ fontSize: '16px', color: '#c084fc', marginBottom: '16px' }}>Optimization Efficiency</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Computation Time</span>
                      <span style={{ color: 'white', fontWeight: 600 }}>{metrics.time.toFixed(2)} sec</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Total Router Movement</span>
                      <span style={{ color: 'white', fontWeight: 600 }}>{metrics.move.toFixed(2)} meters</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px dashed rgba(255,255,255,0.1)',
                borderRadius: '16px',
                padding: '40px',
                textAlign: 'center',
                color: 'var(--text-muted)'
              }}>
                <p>No simulation run yet. Click on the map tab, add human nodes, and press <strong>"Run Optimization"</strong> to generate performance graphs.</p>
              </div>
            )}

            {history.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginTop: '10px' }}>
                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '20px', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <h3 style={{ fontSize: '15px', color: 'white', marginBottom: '16px' }}>Density Coverage Over Time</h3>
                  <div style={{ height: '250px', width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={history} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                        <XAxis dataKey="step" stroke="rgba(255,255,255,0.5)" tick={{fill: 'rgba(255,255,255,0.5)', fontSize: 12}} />
                        <YAxis stroke="rgba(255,255,255,0.5)" tick={{fill: 'rgba(255,255,255,0.5)', fontSize: 12}} />
                        <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} />
                        <Legend />
                        <Line type="monotone" dataKey="coverage" stroke="#10b981" strokeWidth={2} activeDot={{ r: 8 }} name="Coverage (%)" />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '20px', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <h3 style={{ fontSize: '15px', color: 'white', marginBottom: '16px' }}>Router Movement Per Simulation</h3>
                    <div style={{ height: '200px', width: '100%' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={history} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                          <XAxis dataKey="step" stroke="rgba(255,255,255,0.5)" tick={{fill: 'rgba(255,255,255,0.5)', fontSize: 12}} />
                          <YAxis stroke="rgba(255,255,255,0.5)" tick={{fill: 'rgba(255,255,255,0.5)', fontSize: 12}} />
                          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} />
                          <Legend />
                          <Bar dataKey="movement" fill="#3b82f6" name="Total Movement (m)" />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  <div style={{ background: 'rgba(255,255,255,0.03)', padding: '20px', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <h3 style={{ fontSize: '15px', color: 'white', marginBottom: '16px' }}>Optimization Time Trend</h3>
                    <div style={{ height: '200px', width: '100%' }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={history} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                          <XAxis dataKey="step" stroke="rgba(255,255,255,0.5)" tick={{fill: 'rgba(255,255,255,0.5)', fontSize: 12}} />
                          <YAxis stroke="rgba(255,255,255,0.5)" tick={{fill: 'rgba(255,255,255,0.5)', fontSize: 12}} />
                          <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid rgba(255,255,255,0.1)' }} />
                          <Legend />
                          <Line type="monotone" dataKey="time" stroke="#f59e0b" strokeWidth={2} name="Opt. Time (s)" />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div style={{
              background: 'rgba(255,255,255,0.03)',
              borderRadius: '16px',
              padding: '24px',
              border: '1px solid rgba(255,255,255,0.05)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px'
            }}>
              <h3 style={{ fontSize: '16px', color: 'white' }}>THz Router Status</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '12px' }}>
                {routers.map((r, i) => (
                  <div key={i} style={{
                    background: 'rgba(0,0,0,0.2)',
                    padding: '12px',
                    borderRadius: '8px',
                    border: '1px solid rgba(255,255,255,0.05)',
                    fontSize: '13px'
                  }}>
                    <div style={{ color: '#10b981', fontWeight: 600, marginBottom: '4px' }}>Router #{i+1}</div>
                    <div>Position: ({r.x.toFixed(1)}, {r.y.toFixed(1)}, {r.z ? r.z.toFixed(1) : '2.4'})</div>
                    <div>Angle (&phi;): {r.phi.toFixed(0)}&deg;</div>
                    <div>Beam Angle (&alpha;): {r.alpha.toFixed(0)}&deg;</div>
                    <div>Power: {(r.power !== undefined ? r.power : 1.0).toFixed(1)}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;

