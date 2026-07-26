import React, { useState, useEffect, useRef } from 'react';

const API_BASE = 'http://localhost:8000';
const CELL_SIZE = 24; // Visual scaling factor

function App() {
  const [env, setEnv] = useState(null);
  const [points, setPoints] = useState([]);
  const [routers, setRouters] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(false);
  const heatmapRef = useRef(null);

  useEffect(() => {
    fetch(`${API_BASE}/environment`)
      .then(res => res.json())
      .then(data => {
        setEnv(data);
        setRouters(data.routers);
      })
      .catch(err => console.error(err));
  }, []);

  const handleMapClick = (e) => {
    if (!env) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / CELL_SIZE;
    const y = (e.clientY - rect.top) / CELL_SIZE;
    setPoints([...points, { x: Math.floor(x), y: Math.floor(y) }]);
  };

  const handleSimulate = async () => {
    if (points.length === 0) return;
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/simulate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ points })
      });
      const data = await response.json();
      setRouters(data.routers);
      setMetrics({
        initialCov: data.initial_coverage,
        finalCov: data.final_coverage,
        inc: data.reachability_increase,
        time: data.optimization_time,
        move: data.total_movement
      });
      drawHeatmap(data.sinr_map);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  const handleDownloadHeatmap = () => {
    if (!heatmapRef.current) return;
    
    // Create a temporary, unblurred composite canvas to save
    const compositeCanvas = document.createElement('canvas');
    compositeCanvas.width = env.length * CELL_SIZE;
    compositeCanvas.height = env.breadth * CELL_SIZE;
    const ctx = compositeCanvas.getContext('2d');
    
    // Fill with dark background
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, compositeCanvas.width, compositeCanvas.height);
    
    // Draw the raw heatmap directly with no blur
    ctx.drawImage(heatmapRef.current, 0, 0);

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

    // Draw humans
    ctx.fillStyle = '#f43f5e';
    points.forEach(pt => {
      ctx.beginPath();
      ctx.arc((pt.x + 0.5) * CELL_SIZE, (pt.y + 0.5) * CELL_SIZE, 6, 0, 2 * Math.PI);
      ctx.fill();
    });

    // Draw routers and their beams
    routers.forEach(r => {
      const cx = r.x * CELL_SIZE;
      const cy = r.y * CELL_SIZE;

      // Draw beam
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      const startAngle = (r.phi - r.alpha / 2) * Math.PI / 180;
      const endAngle = (r.phi + r.alpha / 2) * Math.PI / 180;
      ctx.arc(cx, cy, 90, startAngle, endAngle);
      ctx.fillStyle = 'rgba(16, 185, 129, 0.7)';
      ctx.fill();

      // Draw router body
      ctx.beginPath();
      ctx.arc(cx, cy, 8, 0, 2 * Math.PI);
      ctx.fillStyle = '#10b981';
      ctx.fill();

      // Draw direction pointer
      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(cx + Math.cos(r.phi * Math.PI / 180) * 15, cy + Math.sin(r.phi * Math.PI / 180) * 15);
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 2;
      ctx.stroke();
    });
    
    // Download
    const link = document.createElement('a');
    link.download = 'heatmap_output.png';
    link.href = compositeCanvas.toDataURL('image/png');
    link.click();
  };

  const drawHeatmap = (mapData) => {
    const canvas = heatmapRef.current;
    if (!canvas || !env || !mapData) return;
    const ctx = canvas.getContext('2d');
    
    // Each cell in the 2D array is mapData[x][y]
    // Note: The numpy array comes back as y, x or x, y? 
    // In compute it's density[x,y]. In python: mapData is LENGTH x BREADTH
    // Length is X, Breadth is Y
    for (let x = 0; x < env.length; x++) {
      for (let y = 0; y < env.breadth; y++) {
        const val = mapData[x][y];
        // simple coloring from blue (low) to red (high)
        // Normalize val (-10 to 40 usually for SINR)
        const normalized = Math.max(0, Math.min(1, (val + 10) / 40));
        const hue = (1.0 - normalized) * 240; // 240 is blue, 0 is red
        ctx.fillStyle = `hsla(${hue}, 100%, 50%, 0.8)`;
        ctx.fillRect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE);
      }
    }
  };

  if (!env) {
    return <div style={{color:'white', padding:'20px'}}>Connecting to simulation backend... Ensure API is running on :8000</div>;
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

        <button className="btn" onClick={handleSimulate} disabled={loading || points.length === 0}>
          {loading ? 'Optimizing...' : 'Run Optimization'}
        </button>
        <button 
          className="btn" 
          style={{background: 'rgba(255,255,255,0.1)', color: 'var(--text-main)', marginTop: '-10px'}} 
          onClick={() => {setPoints([]); setMetrics(null); setRouters(env.routers); const ctx = heatmapRef.current?.getContext('2d'); if(ctx) ctx.clearRect(0,0,mapWidth,mapHeight); }}
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
              <div className="metric-label">Reachability Gain</div>
              <div className="metric-value">+{metrics.inc.toFixed(1)}<span className="metric-unit">%</span></div>
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
          <h1>APSO THz Dashboard</h1>
          <div style={{display:'flex', gap:'20px'}}>
             <div style={{display:'flex', alignItems:'center', gap:'8px'}}>
               <div style={{width:'12px', height:'12px', borderRadius:'50%', background:'#f43f5e'}}></div>
               <span style={{fontSize:'14px', color:'var(--text-muted)'}}>Human</span>
             </div>
             <div style={{display:'flex', alignItems:'center', gap:'8px'}}>
               <div style={{width:'12px', height:'12px', borderRadius:'50%', background:'#10b981'}}></div>
               <span style={{fontSize:'14px', color:'var(--text-muted)'}}>Router</span>
             </div>
          </div>
        </div>

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

            {routers.map((r, i) => (
               <div key={`router-${i}`} className="router-node" style={{ left: r.x * CELL_SIZE, top: r.y * CELL_SIZE }}>
                 {/* Better Beam Indicator visualization using conic-gradient */}
                 <div className="beam-ray" style={{
                   position: 'absolute',
                   left: '-82px', top: '-82px',
                   width: '180px', height: '180px',
                   borderRadius: '50%',
                   background: `conic-gradient(from ${r.phi - r.alpha/2 + 90}deg at 50% 50%, rgba(16, 185, 129, 0.7) ${r.alpha}deg, transparent ${r.alpha}deg)`,
                   pointerEvents: 'none',
                   zIndex: -1
                 }}></div>
                 {/* Directional pointer line within the router dot */}
                 <div style={{
                    position: 'absolute', top: '50%', left: '50%', width: '10px', height: '2px',
                    background: '#fff', transformOrigin: '0% 50%', transform: `rotate(${r.phi}deg)`,
                    pointerEvents: 'none'
                 }}></div>
               </div>
            ))}
            
            {loading && (
              <div className="loading-overlay">
                <div className="spinner"></div>
              </div>
            )}
          </div>
          
          <div className="sinr-legend">
            <div className="legend-title">SINR Color Legend</div>
            <div className="legend-bar"></div>
            <div className="legend-labels">
              <span>-10 dB</span>
              <span>0 dB</span>
              <span>10 dB</span>
              <span>20 dB</span>
              <span>30+ dB</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
