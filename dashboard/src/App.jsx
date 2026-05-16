import React, { useState, useMemo } from 'react';
import DataTable from './components/DataTable';
import Dashboard from './components/Dashboard';
import GraphView from './components/GraphView';
import { OUTPUT_DATA } from './generatedData.js';
import {
  ShieldCheck, FileJson, ChevronRight, History as HistoryIcon, AlertCircle,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const FILE_META = [
  { key: 'security_report',                       label: 'Security Report',               group: 'Static Analysis'  },
  { key: 'opa_cis_result',                        label: 'OPA – CIS Azure Benchmark',     group: 'Static Analysis'  },
  { key: 'opa_vm_result',                         label: 'OPA – VM Size Policy',          group: 'Static Analysis'  },
  { key: 'opa_tags_result',                       label: 'OPA – Mandatory Tags',          group: 'Static Analysis'  },
  { key: 'compliance_dashboard_latest',           label: 'Compliance Dashboard (Latest)', group: 'Compliance'       },
  { key: 'compliance_dashboard_pre_remediation',  label: 'Pre-Remediation Dashboard',     group: 'Compliance'       },
  { key: 'compliance_dashboard_post_remediation', label: 'Post-Remediation Dashboard',    group: 'Compliance'       },
  { key: 'nsg_drift',                             label: 'NSG Drift',                     group: 'Drift Detection'  },
  { key: 'storage_drift',                         label: 'Storage Drift',                 group: 'Drift Detection'  },
  { key: 'scaling_drift',                         label: 'Scaling Drift',                 group: 'Drift Detection'  },
  { key: 'iam_drift',                             label: 'IAM Drift',                     group: 'Drift Detection'  },
  { key: 'nsg_raw',                               label: 'NSG Raw',                       group: 'Raw Azure Data'   },
  { key: 'storage_raw',                           label: 'Storage Raw',                   group: 'Raw Azure Data'   },
  { key: 'scaling_raw',                           label: 'Scaling Raw',                   group: 'Raw Azure Data'   },
  { key: 'iam_raw',                               label: 'IAM Raw',                       group: 'Raw Azure Data'   },
];

const GROUP_ORDER = ['Static Analysis', 'Compliance', 'Drift Detection', 'Raw Azure Data'];

const AUTO_DRILL_KEYS = ['results', 'data', 'items', 'value', 'records', 'resources', 'scenarios'];

function autoExtract(raw) {
  if (!raw) return raw;
  if (Array.isArray(raw)) return raw;
  for (const k of AUTO_DRILL_KEYS) {
    const v = raw[k];
    if (Array.isArray(v) && v.length > 0) return v;
  }
  return raw;
}

const loadedCount = FILE_META.filter(f => OUTPUT_DATA[f.key] !== null).length;
const grouped     = GROUP_ORDER.map(g => ({ group: g, files: FILE_META.filter(f => f.group === g) }));

export default function App() {
  const [selectedKey,  setSelectedKey]  = useState(null);
  const [dataHistory,  setDataHistory]  = useState([]);
  const [parsedData,   setParsedData]   = useState(null);
  const [sidebarOpen,  setSidebarOpen]  = useState(true);

  function selectFile(key) {
    const raw  = OUTPUT_DATA[key];
    const data = autoExtract(raw);
    setSelectedKey(key);
    setParsedData(data);
    setDataHistory([data]);
  }

  function handleDrillDown(child) {
    setDataHistory(h => [...h, child]);
    setParsedData(child);
  }

  function handleGoBack() {
    if (dataHistory.length > 1) {
      const next = dataHistory.slice(0, -1);
      setDataHistory(next);
      setParsedData(next[next.length - 1]);
    }
  }

  const selectedFile = FILE_META.find(f => f.key === selectedKey);

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg-main)' }}>

      {/* ── Sidebar ── */}
      <aside style={{
        width: sidebarOpen ? '260px' : '0',
        minWidth: sidebarOpen ? '260px' : '0',
        overflow: 'hidden',
        background: '#0d1117',
        borderRight: '1px solid var(--border)',
        display: 'flex', flexDirection: 'column',
        transition: 'min-width .25s, width .25s',
        flexShrink: 0,
      }}>
        {/* Brand */}
        <div style={{ padding: '18px 16px 12px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <ShieldCheck size={20} color="var(--primary)" />
            <span style={{ fontWeight: 700, fontSize: '15px', color: 'var(--text-main)' }}>CSPM Visualizer</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            {loadedCount}/{FILE_META.length} files available
          </div>
          <div style={{ marginTop: '8px', height: '4px', borderRadius: '4px', background: '#1e293b', overflow: 'hidden' }}>
            <div style={{
              height: '100%', borderRadius: '4px', background: 'var(--primary)',
              width: `${(loadedCount / FILE_META.length) * 100}%`,
            }} />
          </div>
        </div>

        {/* File list */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
          {grouped.map(({ group, files }) => (
            <div key={group}>
              <div style={{
                padding: '10px 16px 4px', fontSize: '10px', fontWeight: 700,
                letterSpacing: '1px', textTransform: 'uppercase', color: '#475569',
              }}>{group}</div>

              {files.map(f => {
                const available  = OUTPUT_DATA[f.key] !== null;
                const isSelected = selectedKey === f.key;
                return (
                  <button
                    key={f.key}
                    onClick={() => available && selectFile(f.key)}
                    disabled={!available}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '10px',
                      width: '100%', padding: '8px 16px',
                      background: isSelected ? '#1d4ed820' : 'transparent',
                      borderLeft: isSelected ? '3px solid var(--primary)' : '3px solid transparent',
                      border: 'none',
                      cursor: available ? 'pointer' : 'not-allowed',
                      color: available ? 'var(--text-main)' : '#334155',
                      textAlign: 'left', fontSize: '13px',
                    }}
                  >
                    <FileJson size={14} style={{ flexShrink: 0, color: available ? '#22c55e' : '#ef4444' }} />
                    <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {f.label}
                    </span>
                    {!available && <AlertCircle size={12} color="#ef4444" />}
                    {isSelected && <ChevronRight size={14} color="var(--primary)" />}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </aside>

      {/* ── Main ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* Top bar */}
        <header style={{
          height: '52px', background: '#0d1117', borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', padding: '0 20px', gap: '14px', flexShrink: 0,
        }}>
          <button onClick={() => setSidebarOpen(o => !o)} className="btn-secondary"
            style={{ padding: '6px 10px' }} title="Toggle sidebar">
            ☰
          </button>

          {selectedFile
            ? <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                <span style={{ color: '#475569' }}>{selectedFile.group}</span>
                &nbsp;/&nbsp;
                <span style={{ color: 'var(--text-main)', fontWeight: 600 }}>{selectedFile.label}</span>
                {dataHistory.length > 1 &&
                  <span style={{ color: 'var(--primary)' }}> · Depth {dataHistory.length - 1}</span>}
              </span>
            : <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                Select a file from the sidebar to visualise it
              </span>
          }

          {dataHistory.length > 1 && (
            <button className="btn-secondary" onClick={handleGoBack}
              style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px' }}>
              <HistoryIcon size={14} /> Back
            </button>
          )}
        </header>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 28px' }}>
          <AnimatePresence mode="wait">
            {!selectedKey ? (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center',
                  justifyContent: 'center', height: '60vh', gap: '16px', color: 'var(--text-muted)',
                }}
              >
                <ShieldCheck size={64} color="var(--primary)" style={{ opacity: 0.4 }} />
                <h2 style={{ fontWeight: 700, fontSize: '22px', color: 'var(--text-main)' }}>
                  CSPM Visualizer
                </h2>
                <p style={{ fontSize: '14px', textAlign: 'center', maxWidth: '380px' }}>
                  {loadedCount === 0
                    ? 'No output files found. Run the Jenkins pipelines first, then rebuild this dashboard.'
                    : `${loadedCount} of ${FILE_META.length} files loaded. Click any green file in the sidebar to explore it.`
                  }
                </p>
              </motion.div>
            ) : (
              <motion.div
                key={selectedKey + '-' + dataHistory.length}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <Dashboard data={parsedData} />

                <div style={{
                  display: 'grid', gridTemplateColumns: '1fr 1fr',
                  gap: '24px', alignItems: 'start', marginTop: '24px',
                }}>
                  <div style={{ minWidth: 0 }}>
                    <DataTable data={parsedData} onDrillDown={handleDrillDown} />
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <GraphView data={parsedData} />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
