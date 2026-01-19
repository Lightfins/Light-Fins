import React from 'react';

const ComplianceChecklist = ({ onNext, onPrev, data, updateData }) => {
    const updateAdvice = (key, val) => {
        updateData({ advice: { ...data.advice, [key]: val } });
    };

    const questions = [
        { id: 'q2a_policyNameAndType', label: 'Policy Name and Type explained?' },
        { id: 'q2b_premium', label: 'Premium amount and frequency explained?' },
        { id: 'q2c_benefitsLimitations', label: 'Benefits and limitations explained?' },
        { id: 'q2d_qualifyingPeriod', label: 'Waiting periods (qualifying periods) explained?' },
        { id: 'q2e_whoCanBeCovered', label: 'Who can be covered explained?' },
        { id: 'q2f_commissionDisclosure', label: 'Commission disclosure provided?' },
        { id: 'q2g_coolingPeriod60Days', label: '60-day cooling-off period explained?' },
        { id: 'q2h_claimProcedure', label: 'Claim procedure explained?' },
        { id: 'q2i_insurerRegisteredNameAddress', label: 'Insurer registered name and address provided?' },
    ];

    const allAnswered = questions.every(q => data?.advice?.[q.id] === 'YES');

    return (
        <div className="wizard-step compliance-step">
            <h2>2. Compliance Checklist (Advice)</h2>
            <p className="instruction-text">The intermediary must ensure all these items were explained to the policyholder.</p>

            <div className="checklist-container">
                {questions.map(q => (
                    <div key={q.id} className="checklist-row">
                        <span className="question-label">{q.label}</span>
                        <div className="radio-group">
                            <label>
                                <input
                                    type="radio"
                                    name={q.id}
                                    value="YES"
                                    checked={data?.advice?.[q.id] === 'YES'}
                                    onChange={() => updateAdvice(q.id, 'YES')}
                                /> Yes
                            </label>
                            <label>
                                <input
                                    type="radio"
                                    name={q.id}
                                    value="NO"
                                    checked={data?.advice?.[q.id] === 'NO'}
                                    onChange={() => updateAdvice(q.id, 'NO')}
                                /> No
                            </label>
                        </div>
                    </div>
                ))}
            </div>

            <div className="btn-group">
                <button className="btn-secondary" onClick={onPrev}>Back</button>
                <button
                    className="btn-primary"
                    disabled={!allAnswered}
                    onClick={onNext}
                >
                    Next: Policyholder Details
                </button>
            </div>
        </div>
    );
};

export default ComplianceChecklist;
