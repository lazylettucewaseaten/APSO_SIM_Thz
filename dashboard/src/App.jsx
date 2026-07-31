import React, { useState } from 'react';
import './index.css';

const API_URL = 'http://localhost:8000';

function App() {
  const [steps, setSteps] = useState(3);
  const [loading, setLoading] = useState(false);
  const [modeRun, setModeRun] = useState(null); // 'random' or 'manual'
  const [cacheBuster, setCacheBuster] = useState(Date.now());
  const [error, setError] = useState(null);

  const runSimulation = async (mode) => {
    setLoading(true);
    setModeRun(null);
    setError(null);
    
    try {
      const response = await fetch(`${API_URL}/run/${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ steps })
      });
      
      if (!response.ok) {
        throw new Error('Simulation failed to run.');
      }
      
      const data = await response.json();
      setModeRun(data.mode);
      setCacheBuster(Date.now()); // force image reload
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const basePath = modeRun === 'random' ? `${API_URL}/static_root` : `${API_URL}/static_interactive`;

  // Generate arrays for step-based images
  const stepIndices = Array.from({ length: steps }, (_, i) => i);

  return (
    <div className="app-container">
      <div className="glass-panel main-dashboard">
        <header className="dashboard-header">
          <h1>APSO THz Simulation Dashboard</h1>
          <p className="subtitle">Configure and run spatial repositioning simulations</p>
        </header>

        <div className="control-panel">
          <div className="input-group">
            <label htmlFor="steps">Time Steps:</label>
            <input 
              type="number" 
              id="steps" 
              min="1" 
              max="20"
              value={steps}
              onChange={(e) => setSteps(parseInt(e.target.value) || 1)}
            />
          </div>
          
          <div className="button-group">
            <button 
              className="btn btn-primary" 
              onClick={() => runSimulation('random')}
              disabled={loading}
            >
              Run Random (Automated)
            </button>
            <button 
              className="btn btn-secondary" 
              onClick={() => runSimulation('manual')}
              disabled={loading}
            >
              Run Manual (GUI Placements)
            </button>
          </div>
        </div>
        
        {loading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <p>Running Simulation... Check local GUI if running manual mode!</p>
          </div>
        )}

        {error && (
          <div className="error-banner">
            Error: {error}
          </div>
        )}

        {modeRun && !loading && (
          <div className="results-container">
            <h2>Simulation Results ({modeRun.toUpperCase()} MODE)</h2>
            
            <div className="summary-graphs">
              <div className="graph-card">
                <h3>Coverage Over Time</h3>
                <img src={`${basePath}/coverage_over_time.png?t=${cacheBuster}`} alt="Coverage" />
              </div>
              <div className="graph-card">
                <h3>Reachability vs Movement</h3>
                <img src={`${basePath}/reachability_vs_movement.png?t=${cacheBuster}`} alt="Reachability" />
              </div>
              <div className="graph-card">
                <h3>Optimization Time</h3>
                <img src={`${basePath}/optimization_time.png?t=${cacheBuster}`} alt="Optimization Time" />
              </div>
            </div>

            <h3 className="timeline-title">Timestep Breakdown</h3>
            <div className="timeline-graphs">
              {stepIndices.map(t => (
                <div key={t} className="step-card">
                  <h4>Time Step {t}</h4>
                  <div className="step-images">
                    <div className="img-wrapper">
                      <span>Density Map</span>
                      <img src={`${basePath}/density_t${t}.png?t=${cacheBuster}`} alt={`Density ${t}`} />
                    </div>
                    <div className="img-wrapper">
                      <span>AP Placement (After)</span>
                      <img src={`${basePath}/ap_placement_t${t}_after.png?t=${cacheBuster}`} alt={`Placement ${t}`} />
                    </div>
                    <div className="img-wrapper">
                      <span>SINR (After)</span>
                      <img src={`${basePath}/sinr_t${t}_after.png?t=${cacheBuster}`} alt={`SINR ${t}`} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
