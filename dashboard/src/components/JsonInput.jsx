import React, { useState } from 'react';
import { Terminal, Trash2, Clipboard, Play } from 'lucide-react';
import { motion } from 'framer-motion';

const JsonInput = ({ onParse }) => {
  const [jsonString, setJsonString] = useState('');
  const [error, setError] = useState(null);

  const handleParse = () => {
    try {
      const parsed = JSON.parse(jsonString);
      setError(null);
      onParse(parsed);
    } catch (err) {
      setError('Invalid JSON: ' + err.message);
    }
  };

  const handleClear = () => {
    setJsonString('');
    setError(null);
  };

  const handlePasteSample = () => {
    const sample = [
      { "id": 1, "name": "System Audit", "status": "Active", "severity": "High", "last_run": "2024-05-10" },
      { "id": 2, "name": "Network Scan", "status": "Pending", "severity": "Medium", "last_run": "2024-05-11" },
      { "id": 3, "name": "User Access Review", "status": "Completed", "severity": "Low", "last_run": "2024-05-09" }
    ];
    setJsonString(JSON.stringify(sample, null, 2));
    setError(null);
  };

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="glass-card"
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Terminal size={20} color="var(--primary)" />
          <h2 style={{ margin: 0 }}>JSON Input</h2>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn-secondary" onClick={handlePasteSample}>Sample</button>
          <button className="btn-secondary" onClick={handleClear} title="Clear">
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      <textarea
        className="input-area"
        placeholder="Paste your JSON here..."
        value={jsonString}
        onChange={(e) => setJsonString(e.target.value)}
        spellCheck="false"
      />

      {error && (
        <div style={{ color: 'var(--error)', marginTop: '12px', fontSize: '14px', background: 'rgba(239, 68, 68, 0.1)', padding: '10px', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
          {error}
        </div>
      )}

      <div style={{ marginTop: '16px', display: 'flex', justifyContent: 'flex-end' }}>
        <motion.button 
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          className="btn-primary" 
          onClick={handleParse} 
          disabled={!jsonString}
        >
          <Play size={16} />
          Parse to Table
        </motion.button>
      </div>
    </motion.div>
  );
};

export default JsonInput;
