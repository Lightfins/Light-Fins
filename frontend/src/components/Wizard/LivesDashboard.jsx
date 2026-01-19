import React from 'react';

const LivesDashboard = ({ onNext, onPrev, data, updateData }) => {
    const addLife = (category) => {
        const newList = [...(data[category] || [])];
        if (category === 'children' && newList.length >= 8) return;
        if (category === 'parents' && newList.length >= 4) return;
        if (category === 'widerFamily' && newList.length >= 8) return;

        newList.push({
            firstNames: '',
            surname: '',
            idNumber: '',
            age: '',
            gender: '',
            plan: 'Value Funeral',
            premium: '0'
        });
        updateData({ [category]: newList });
    };

    const removeLife = (category, index) => {
        const newList = [...data[category]];
        newList.splice(index, 1);
        updateData({ [category]: newList });
    };

    const totalLives = 1 + (data.spouse?.enabled ? 1 : 0) +
        (data.children?.length || 0) +
        (data.parents?.length || 0) +
        (data.widerFamily?.length || 0);

    return (
        <div className="wizard-step lives-step">
            <h2>4. Lives Covered ({totalLives}/22)</h2>
            {totalLives > 22 && <p className="error-text">Warning: Total lives exceed the maximum of 22.</p>}

            <div className="lives-section">
                <h3>Principal Member</h3>
                <p>Premium: R{data.principal?.premium || '0.00'}</p>
            </div>

            <div className="lives-section">
                <h3>Spouse</h3>
                {!data.spouse?.enabled ? (
                    <button className="btn-secondary" onClick={() => updateData({ spouse: { ...data.spouse, enabled: true } })}>Add Spouse</button>
                ) : (
                    <div className="life-card">
                        <div className="form-grid">
                            <input placeholder="First Names" value={data.spouse.firstNames} onChange={(e) => updateData({ spouse: { ...data.spouse, firstNames: e.target.value } })} />
                            <input placeholder="Surname" value={data.spouse.surname} onChange={(e) => updateData({ spouse: { ...data.spouse, surname: e.target.value } })} />
                            <input placeholder="ID Number" value={data.spouse.idNumber} onChange={(e) => updateData({ spouse: { ...data.spouse, idNumber: e.target.value } })} />
                        </div>
                        <button className="btn-remove" onClick={() => updateData({ spouse: { ...data.spouse, enabled: false } })}>Remove</button>
                    </div>
                )}
            </div>

            {['children', 'parents', 'widerFamily'].map(cat => (
                <div key={cat} className="lives-section">
                    <h3>{cat.charAt(0).toUpperCase() + cat.slice(1)}</h3>
                    {(data[cat] || []).map((life, idx) => (
                        <div key={idx} className="life-card">
                            <input placeholder="First Names" value={life.firstNames} onChange={(e) => {
                                const newList = [...data[cat]];
                                newList[idx].firstNames = e.target.value;
                                updateData({ [cat]: newList });
                            }} />
                            <button className="btn-remove" onClick={() => removeLife(cat, idx)}>×</button>
                        </div>
                    ))}
                    <button className="btn-add" onClick={() => addLife(cat)}>+ Add {cat.slice(0, -1)}</button>
                </div>
            ))}

            <div className="btn-group">
                <button className="btn-secondary" onClick={onPrev}>Back</button>
                <button
                    className="btn-primary"
                    onClick={onNext}
                    disabled={totalLives > 22}
                >
                    Next: Beneficiaries
                </button>
            </div>
        </div>
    );
};

export default LivesDashboard;
