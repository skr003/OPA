import React, { useState } from 'react';
import JsonInput from './components/JsonInput';
import DataTable from './components/DataTable';
import Dashboard from './components/Dashboard';
import GraphView from './components/GraphView';
import { Database, ShieldCheck, Table, Network, History as HistoryIcon } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

function App() {
  const [dataHistory, setDataHistory] = useState([]);
  const [parsedData, setParsedData] = useState(null);

  const handleParse = (newData) => {
    // Automatic Drill Down detection
    const dataKeys = ['data', 'DATA', 'items', 'value', 'results', 'records'];
    let targetData = newData;

    for (const key of dataKeys) {
      const val = newData[key];
      if (val) {
        if (Array.isArray(val)) {
          targetData = val;
          break;
        } else if (typeof val === 'string') {
          try {
            const parsed = JSON.parse(val);
            if (Array.isArray(parsed)) {
              targetData = parsed;
              break;
            }
          } catch (e) {}
        }
      }
    }

    setParsedData(targetData);
    // If we auto-drilled, include the original root in history so they can go back
    if (targetData !== newData) {
      setDataHistory([newData, targetData]);
    } else {
      setDataHistory([newData]);
    }
  };

  const handleDrillDown = (childData) => {
    setDataHistory([...dataHistory, childData]);
    setParsedData(childData);
  };

  const handleGoBack = () => {
    if (dataHistory.length > 1) {
      const newHistory = dataHistory.slice(0, -1);
      setDataHistory(newHistory);
      setParsedData(newHistory[newHistory.length - 1]);
    }
  };

  return (
    <div style={{ padding: '20px 40px', width: '100%', maxWidth: '100%', margin: '0' }}>
      <header style={{ marginBottom: '30px', textAlign: 'center' }}>
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '12px', marginBottom: '8px' }}
        >
          <ShieldCheck size={40} color="var(--primary)" />
          <h1 style={{ fontSize: '36px', fontWeight: '800', letterSpacing: '-0.02em', margin: 0 }}>
            CSPM <span style={{ color: 'var(--primary)' }}>Visualizer</span>
          </h1>
        </motion.div>
      </header>

      <main>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '24px' }}>
          {dataHistory.length <= 1 && (
            <div style={{ maxWidth: '800px', margin: '0 auto', width: '100%' }}>
              <JsonInput onParse={handleParse} />
            </div>
          )}
          
          {parsedData && (
            <div className="animate-fade-in">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  {dataHistory.length > 1 && (
                    <button className="btn-secondary" onClick={handleGoBack} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <HistoryIcon size={16} /> Back
                    </button>
                  )}
                  <h2 style={{ fontSize: '18px', color: 'var(--text-muted)' }}>Dashboard Analysis</h2>
                </div>
                <span style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
                  Depth Level: {dataHistory.length - 1}
                </span>
              </div>

              <Dashboard data={parsedData} />
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px', alignItems: 'start' }}>
                <div style={{ minWidth: 0 }}>
                  <DataTable data={parsedData} onDrillDown={handleDrillDown} />
                </div>
                <div style={{ minWidth: 0 }}>
                  <GraphView data={parsedData} />
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      <footer style={{ marginTop: '60px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '14px' }}>
        <p>© 2024 CSPM Visualizer • Secure Local Processing</p>
      </footer>
    </div>
  );
}

export default App;
