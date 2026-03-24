import React, { useState, useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import axios from 'axios';
import { Send, Layers, Activity, X } from 'lucide-react';

const App = () => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [chat, setChat] = useState([{ role: 'ai', text: 'SAP Control Tower Online. Ready to trace your Order-to-Cash flow.' }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [highlights, setHighlights] = useState([]);
  const fgRef = useRef();
  const API_BASE = "https://sap-o2c-backend.onrender.com";

  useEffect(() => {
    axios.get(`${API_BASE}/graph-data`).then(res => {
      const nodes = [], links = [], seen = new Set();
      res.data.forEach(row => {
        if (!seen.has(row.source_id)) {
          nodes.push({ id: row.source_id, label: row.source_label, ...row.source_props });
          seen.add(row.source_id);
        }
        if (!seen.has(row.target_id)) {
          nodes.push({ id: row.target_id, label: row.target_label, ...row.target_props });
          seen.add(row.target_id);
        }
        links.push({ source: row.source_id, target: row.target_id, type: row.rel_type });
      });
      setGraphData({ nodes, links });
      setTimeout(() => fgRef.current?.zoomToFit(400, 100), 500);
    }).catch(e => console.error(e));
  }, []);

  const handleAsk = async () => {
    if (!input || loading) return;
    const q = input;
    setChat(p => [...p, { role: 'user', text: q }]);
    setInput('');
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/ask`, { question: q });
      setChat(p => [...p, { role: 'ai', text: res.data.answer }]);
      setHighlights(res.data.affected_node_ids || []);
    } catch {
      setChat(p => [...p, { role: 'ai', text: 'Connection lost.' }]);
    }
    setLoading(false);
  };

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh', background: '#030712', color: 'white', overflow: 'hidden' }}>
      
      {/* 1. GRAPH SECTION */}
      <div style={{ position: 'relative', flex: 1, borderRight: '1px solid #1f2937' }}>
        <div style={{ position: 'absolute', top: '20px', left: '20px', zIndex: 10, background: 'rgba(17,24,39,0.8)', padding: '10px', borderRadius: '4px', border: '1px solid #374151', fontSize: '10px' }}>
           <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}><div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#3b82f6' }}/> ORDER</div>
           <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}><div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f97316' }}/> DELIVERY</div>
           <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#22c55e' }}/> INVOICE</div>
        </div>

        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          width={window.innerWidth * 0.75}
          height={window.innerHeight}
          nodeColor={n => highlights.includes(n.id) ? '#ef4444' : (n.label === 'Order' ? '#3b82f6' : n.label === 'Delivery' ? '#f97316' : '#22c55e')}
          onNodeClick={n => setSelectedNode(n)}
          nodeRelSize={7}
          linkDirectionalParticles={2}
          linkColor={() => '#1f2937'}
        />

        {selectedNode && (
          <div
            style={{
              position: 'absolute',
              bottom: '30px',
              left: '30px',
              width: '350px',
              background: '#111827',
              padding: '17px',
              borderRadius: '10px',
              border: '1px solid #3b82f6',
              zIndex: 20,
              boxShadow: '0 8px 24px rgba(0,0,0,0.35)'
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '10px',
                borderBottom: '1px solid #1f2937',
                paddingBottom: '7px'
              }}
            >
              <b style={{ color: '#60a5fa', fontSize: '14px' }}>
                {selectedNode.label} Details
              </b>
              <X
                size={16}
                style={{ cursor: 'pointer', color: '#cbd5e1' }}
                onClick={() => setSelectedNode(null)}
              />
            </div>

            <div
              style={{
                fontSize: '12px',
                maxHeight: '180px',
                overflowY: 'auto',
                paddingRight: '8px'
              }}
            >
              {Object.entries(selectedNode).map(
                ([k, v]) =>
                  !['id', 'label', 'x', 'y', 'vx', 'vy', 'index', 'fx', 'fy', '__indexColor'].includes(k) && (
                    <div
                      key={k}
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr',
                        gap: '10px',
                        marginBottom: '8px',
                        alignItems: 'start'
                      }}
                    >
                      <span style={{ color: '#94a3b8', wordBreak: 'break-word' }}>
                        {k}:
                      </span>
                      <span style={{ color: '#f8fafc', textAlign: 'right', wordBreak: 'break-word' }}>
                        {String(v)}
                      </span>
                    </div>
                  )
              )}
            </div>
          </div>
        )}
      </div>

      {/* 2. CHATBAR SECTION (FIXED WIDTH) */}
      <div style={{ width: '350px', background: '#0b0e14', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '20px', borderBottom: '1px solid #1f2937', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Layers size={20} color="#3b82f6"/>
          <b style={{ letterSpacing: '1px' }}>DODGE AI</b>
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
          {chat.map((m, i) => (
            <div key={i} style={{ marginBottom: '15px', textAlign: m.role === 'user' ? 'right' : 'left' }}>
               <div style={{ display: 'inline-block', padding: '10px', borderRadius: '8px', fontSize: '12px', background: m.role === 'user' ? '#2563eb' : '#1f2937', maxWidth: '85%' }}>
                 {m.text}
               </div>
            </div>
          ))}
          {loading && <div style={{ fontSize: '10px', color: '#3b82f6' }}>Analysing Graph...</div>}
        </div>
        <div style={{ padding: '20px', borderTop: '1px solid #1f2937' }}>
          <div style={{ display: 'flex', background: '#111827', padding: '5px', borderRadius: '4px', border: '1px solid #374151' }}>
            <input 
              value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleAsk()}
              style={{ flex: 1, background: 'transparent', border: 'none', color: 'white', fontSize: '12px', outline: 'none', paddingLeft: '5px' }}
              placeholder="Query orders..." 
            />
            <button onClick={handleAsk} style={{ background: 'none', border: 'none', cursor: 'pointer' }}><Send size={16} color="#3b82f6"/></button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;