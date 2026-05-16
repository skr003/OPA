import React, { useMemo, useRef, useCallback, useState, useEffect } from 'react';
import { ReactFlow, Background, Controls, MiniMap, useNodesState, useEdgesState, useReactFlow, ReactFlowProvider } from '@xyflow/react';
import { Maximize, Minimize, AlertCircle } from 'lucide-react';
import dagre from 'dagre';
import '@xyflow/react/dist/style.css';

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 220;
const nodeHeight = 100;

const getLayoutedElements = (nodes, edges, direction = 'LR') => {
  if (nodes.length === 0) return { nodes, edges };
  
  const isHorizontal = direction === 'LR';
  dagreGraph.setGraph({ rankdir: direction });

  nodes.forEach((node) => {
    // Estimate width based on longest line
    const lines = node.data.label.split('\n');
    const longestLineLength = Math.max(...lines.map(l => l.length));
    const estimatedWidth = Math.min(600, Math.max(220, longestLineLength * 7 + 40));
    
    // Estimate height
    const lineCount = lines.length;
    const estimatedHeight = Math.max(nodeHeight, lineCount * 18 + 24);
    
    dagreGraph.setNode(node.id, { width: estimatedWidth, height: estimatedHeight });
    node.estimatedWidth = estimatedWidth;
    node.estimatedHeight = estimatedHeight;
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const newNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: isHorizontal ? 'left' : 'top',
      sourcePosition: isHorizontal ? 'right' : 'bottom',
      position: {
        x: nodeWithPosition.x - node.estimatedWidth / 2,
        y: nodeWithPosition.y - node.estimatedHeight / 2,
      },
      style: {
        ...node.style,
        width: node.estimatedWidth,
        height: node.estimatedHeight
      }
    };
  });

  return { nodes: newNodes, edges };
};

const GraphViewContent = ({ data }) => {
  const containerRef = useRef(null);
  const [error, setError] = useState(null);
  const { fitView } = useReactFlow();
  
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().catch(err => {
        alert(`Error attempting to enable full-screen mode: ${err.message}`);
      });
    } else {
      document.exitFullscreen();
    }
  };

  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    try {
      const nodes = [];
      const edges = [];
      let idCounter = 0;

      const process = (obj, parentId = null, label = 'Root', depth = 0) => {
        if (depth > 5) return; 

        const id = `node-${idCounter++}`;
        let nodeContent = [];
        let children = [];

        if (typeof obj === 'object' && obj !== null && !Array.isArray(obj)) {
          // Object: Collect all primitive properties for this node
          Object.keys(obj).forEach(key => {
            const val = obj[key];
            if (typeof val !== 'object' || val === null) {
              nodeContent.push(`${key}: ${val}`);
            } else {
              children.push({ key, val });
            }
          });
        } else if (Array.isArray(obj)) {
          // Array: Just label it and process children
          nodeContent.push(label);
          obj.slice(0, 10).forEach((item, index) => {
            children.push({ key: `[${index}]`, val: item });
          });
        } else {
          // Primitive
          nodeContent.push(`${label}: ${obj}`);
        }

        const labelText = nodeContent.length > 0 ? nodeContent.join('\n') : label;

        nodes.push({
          id,
          data: { label: labelText },
          position: { x: 0, y: 0 },
          style: {
            background: 'var(--bg-card)',
            color: 'var(--text-main)',
            border: '1px solid var(--primary)',
            borderRadius: '8px',
            padding: '12px',
            fontSize: '11px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
            backdropFilter: 'blur(10px)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
            textAlign: 'left'
          }
        });

        if (parentId) {
          edges.push({
            id: `edge-${parentId}-${id}`,
            source: parentId,
            target: id,
            animated: true,
            style: { stroke: 'var(--primary)', strokeWidth: 1.5, opacity: 0.6 }
          });
        }

        // Process actual nested objects/arrays as new nodes
        children.forEach(child => {
          process(child.val, id, child.key, depth + 1);
        });
      };

      process(data);
      setError(null);
      const layout = getLayoutedElements(nodes, edges);
      return { nodes: layout.nodes, edges: layout.edges };
    } catch (err) {
      setError(err.message);
      return { nodes: [], edges: [] };
    }
  }, [data]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes || []);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges || []);

  useEffect(() => {
    if (initialNodes && initialNodes.length > 0) {
      setNodes(initialNodes);
      setEdges(initialEdges);
      // Small timeout to allow nodes to be rendered before fitting
      setTimeout(() => {
        fitView({ padding: 0.2, duration: 800 });
      }, 100);
    }
  }, [initialNodes, initialEdges, setNodes, setEdges, fitView]);

  if (error) {
    return (
      <div className="glass-card" style={{ height: '700px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px' }}>
        <AlertCircle size={48} color="var(--error)" />
        <h3 style={{ color: 'var(--error)' }}>Visualization Error</h3>
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', maxWidth: '400px' }}>{error}</p>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className="glass-card animate-fade-in"
      style={{ height: '700px', width: '100%', overflow: 'hidden', position: 'relative', padding: 0 }}
    >
      <div style={{ position: 'absolute', top: '20px', right: '20px', zIndex: 10 }}>
        <button 
          onClick={toggleFullscreen}
          className="btn-secondary"
          style={{ background: 'rgba(0,0,0,0.6)', padding: '8px' }}
          title="Toggle Fullscreen"
        >
          <Maximize size={18} />
        </button>
      </div>

      <ReactFlow 
        nodes={nodes} 
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
      >
        <Background color="var(--border)" gap={20} variant="dots" style={{ opacity: 0.2 }} />
        <Controls />
        <MiniMap 
          nodeStrokeWidth={3} 
          zoomable 
          pannable 
          style={{ background: 'rgba(15, 23, 42, 0.9)', border: '1px solid var(--border)' }}
        />
      </ReactFlow>
    </div>
  );
};

const GraphView = (props) => (
  <ReactFlowProvider>
    <GraphViewContent {...props} />
  </ReactFlowProvider>
);

export default GraphView;
