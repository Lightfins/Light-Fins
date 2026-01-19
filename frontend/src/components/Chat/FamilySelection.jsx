import React, { useState } from 'react';
import { FAMILY_TYPES } from '../../data/flowConfig';

const FamilySelection = ({ onComplete }) => {
    const [activeTab, setActiveTab] = useState('immediate');
    const [counts, setCounts] = useState({});

    const updateCount = (id, delta) => {
        setCounts(prev => {
            const current = prev[id] || 0;
            const newVal = Math.max(0, current + delta);
            return { ...prev, [id]: newVal };
        });
    };

    const handleDone = () => {
        const summary = [];
        Object.entries(counts).forEach(([key, count]) => {
            if (count > 0) summary.push(`${count} x ${key}`);
        });
        const text = summary.length > 0 ? summary.join(", ") : "Just me";
        onComplete(text, counts); // Pass text for chat, counts for backend
    };

    return (
        <div className="family-selection-container">
            <div className="family-tabs">
                <button
                    className={`tab-btn ${activeTab === 'immediate' ? 'active' : ''}`}
                    onClick={() => setActiveTab('immediate')}
                >
                    Immediate Family
                </button>
                <button
                    className={`tab-btn ${activeTab === 'extended' ? 'active' : ''}`}
                    onClick={() => setActiveTab('extended')}
                >
                    Extended Family
                </button>
            </div>

            <div className="family-grid">
                {FAMILY_TYPES[activeTab].map(member => {
                    const count = counts[member.id] || 0;
                    return (
                        <div
                            key={member.id}
                            className={`family-card ${count > 0 ? 'selected' : ''}`}
                            onClick={() => updateCount(member.id, 1)}
                        >
                            <div className="family-icon">{member.icon}</div>
                            <div className="family-label">{member.label}</div>
                            <div className="counter-ctrl">
                                <button
                                    className="ctrl-btn"
                                    onClick={(e) => { e.stopPropagation(); updateCount(member.id, -1); }}
                                >
                                    -
                                </button>
                                <span className="count-display">{count}</span>
                                <button
                                    className="ctrl-btn"
                                    onClick={(e) => { e.stopPropagation(); updateCount(member.id, 1); }}
                                >
                                    +
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>

            <button className="done-btn" onClick={handleDone}>
                Done Adding Members
            </button>
        </div>
    );
};

export default FamilySelection;
