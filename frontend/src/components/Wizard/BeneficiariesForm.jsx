import React from 'react';

const BeneficiariesForm = ({ onNext, onPrev, data, updateData }) => {
    const addBeneficiary = () => {
        const newList = [...(data || [])];
        if (newList.length >= 2) return;
        newList.push({ firstNames: '', surname: '', idNumber: '', relationship: '', share: '' });
        updateData(newList);
    };

    const removeBeneficiary = (index) => {
        const newList = [...data];
        newList.splice(index, 1);
        updateData(newList);
    };

    const totalShare = (data || []).reduce((sum, b) => sum + (parseFloat(b.share) || 0), 0);

    return (
        <div className="wizard-step beneficiaries-step">
            <h2>5. Beneficiaries (Max 2)</h2>
            <p className="instruction-text">Nominate up to 2 beneficiaries. Total share must equal 100%.</p>

            {(data || []).map((beneficiary, idx) => (
                <div key={idx} className="life-card">
                    <div className="form-grid">
                        <input placeholder="First Names" value={beneficiary.firstNames} onChange={(e) => {
                            const newList = [...data];
                            newList[idx].firstNames = e.target.value;
                            updateData(newList);
                        }} />
                        <input placeholder="Surname" value={beneficiary.surname} onChange={(e) => {
                            const newList = [...data];
                            newList[idx].surname = e.target.value;
                            updateData(newList);
                        }} />
                        <input placeholder="ID Number" value={beneficiary.idNumber} onChange={(e) => {
                            const newList = [...data];
                            newList[idx].idNumber = e.target.value;
                            updateData(newList);
                        }} />
                        <input placeholder="Relationship" value={beneficiary.relationship} onChange={(e) => {
                            const newList = [...data];
                            newList[idx].relationship = e.target.value;
                            updateData(newList);
                        }} />
                        <div className="share-input">
                            <input type="number" placeholder="Share %" value={beneficiary.share} onChange={(e) => {
                                const newList = [...data];
                                newList[idx].share = e.target.value;
                                updateData(newList);
                            }} />
                            <span>%</span>
                        </div>
                    </div>
                    <button className="btn-remove" onClick={() => removeBeneficiary(idx)}>Remove</button>
                </div>
            ))}

            {(!data || data.length < 2) && (
                <button className="btn-add" onClick={addBeneficiary}>+ Add Beneficiary</button>
            )}

            {totalShare !== 100 && (data || []).length > 0 && (
                <p className="error-text">Current total share: {totalShare}%. Must be 100%.</p>
            )}

            <div className="btn-group">
                <button className="btn-secondary" onClick={onPrev}>Back</button>
                <button
                    className="btn-primary"
                    onClick={onNext}
                    disabled={totalShare !== 100 && (data || []).length > 0}
                >
                    Next: Review & Submit
                </button>
            </div>
        </div>
    );
};

export default BeneficiariesForm;
