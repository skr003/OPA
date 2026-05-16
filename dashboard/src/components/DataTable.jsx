import React, { useMemo, useState } from 'react';
import { Table, Download, Info, Maximize2, Minimize2, ExternalLink } from 'lucide-react';

const DataCell = ({ value, onDrillDown }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const parsedValue = useMemo(() => {
    if (typeof value !== 'string') return null;
    try {
      const parsed = JSON.parse(value);
      if (typeof parsed === 'object' && parsed !== null) return parsed;
    } catch (e) {}
    return null;
  }, [value]);

  const displayValue = String(value ?? '');
  const isLong = displayValue.length > 100;

  return (
    <td>
      <div 
        className={isExpanded ? 'cell-expanded' : 'cell-content'} 
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {parsedValue && <span className="badge-json">JSON</span>}
        {displayValue}
      </div>
      
      {isExpanded && (
        <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
          <button className="drill-down-btn" onClick={() => setIsExpanded(false)}>
            <Minimize2 size={12} /> Collapse
          </button>
          {parsedValue && (
            <button className="drill-down-btn" onClick={() => onDrillDown(parsedValue)}>
              <ExternalLink size={12} /> Drill Down
            </button>
          )}
        </div>
      )}
      
      {!isExpanded && isLong && (
        <div style={{ fontSize: '10px', color: 'var(--primary)', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Maximize2 size={10} /> Click to expand
        </div>
      )}
    </td>
  );
};

const DataTable = ({ data, onDrillDown }) => {
  const flattenObject = (obj, parent = '', res = {}) => {
    if (typeof obj !== 'object' || obj === null) {
      res[parent || 'Value'] = obj;
      return res;
    }
    for (let key in obj) {
      const propName = parent ? `${parent}.${key}` : key;
      if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
        flattenObject(obj[key], propName, res);
      } else {
        res[propName] = typeof obj[key] === 'object' ? JSON.stringify(obj[key]) : obj[key];
      }
    }
    return res;
  };

  const tableData = useMemo(() => {
    if (!data) return [];
    const arrayData = Array.isArray(data) ? data : [data];
    return arrayData.map(item => flattenObject(item));
  }, [data]);

  const columns = useMemo(() => {
    if (tableData.length === 0) return [];
    const keys = new Set();
    tableData.forEach(item => {
      Object.keys(item).forEach(key => keys.add(key));
    });
    return Array.from(keys);
  }, [tableData]);

  const handleExportCSV = () => {
    if (tableData.length === 0 || columns.length === 0) return;
    const header = columns.join(',');
    const rows = tableData.map(row => 
      columns.map(col => `"${String(row[col] || '').replace(/"/g, '""')}"`).join(',')
    );
    const csvContent = [header, ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', 'parsed_json.csv');
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!data) return null;

  return (
    <div className="glass-card animate-fade-in">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Table size={20} color="var(--primary)" />
          <h2 style={{ margin: 0 }}>Data Visualization</h2>
        </div>
        <button className="btn-secondary" onClick={handleExportCSV} disabled={columns.length === 0}>
          <Download size={16} />
          Export CSV
        </button>
      </div>

      <div className="table-container">
        {columns.length > 0 ? (
          <table>
            <thead>
              <tr>
                {columns.map(col => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tableData.map((row, i) => (
                <tr key={i}>
                  {columns.map(col => (
                    <DataCell 
                      key={col} 
                      value={row[col]} 
                      onDrillDown={onDrillDown}
                    />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: '60px 40px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <Info size={32} style={{ marginBottom: '16px', opacity: 0.5 }} />
            <p style={{ fontSize: '16px' }}>No columns found in this data level.</p>
            <p style={{ fontSize: '14px', marginTop: '8px' }}>The data might be empty or in an unsupported format.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default DataTable;
