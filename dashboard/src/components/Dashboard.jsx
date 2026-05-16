import React from 'react';
import { Layers, Hash, Type, Activity } from 'lucide-react';

const Dashboard = ({ data }) => {
  const getStats = () => {
    if (!data) return null;
    const arrayData = Array.isArray(data) ? data : [data];
    const totalRows = arrayData.length;
    const uniqueKeys = new Set();
    let totalFields = 0;

    arrayData.forEach(item => {
      const keys = Object.keys(item);
      keys.forEach(k => uniqueKeys.add(k));
      totalFields += keys.length;
    });

    return [
      { label: 'Total Records', value: totalRows, icon: <Layers size={20} /> },
      { label: 'Unique Columns', value: uniqueKeys.size, icon: <Hash size={20} /> },
      { label: 'Total Fields', value: totalFields, icon: <Type size={20} /> },
      { label: 'Avg Density', value: (totalFields / (totalRows * uniqueKeys.size || 1) * 100).toFixed(0) + '%', icon: <Activity size={20} /> }
    ];
  };

  const stats = getStats();

  if (!stats) return null;

  return (
    <div className="summary-grid animate-fade-in">
      {stats.map((stat, i) => (
        <div key={i} className="glass-card stat-card">
          <div style={{ color: 'var(--primary)', marginBottom: '4px' }}>
            {stat.icon}
          </div>
          <div className="stat-value">{stat.value}</div>
          <div className="stat-label">{stat.label}</div>
        </div>
      ))}
    </div>
  );
};

export default Dashboard;
