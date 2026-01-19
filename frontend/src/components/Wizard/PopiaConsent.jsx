import React from 'react';

const PopiaConsent = ({ onNext, data, updateData }) => {
    const isAccepted = data?.popiaAccepted || false;

    return (
        <div className="wizard-step popia-step">
            <h2>1. POPIA Consent</h2>
            <div className="legal-scroll-box">
                <p><strong>Protection of Personal Information Act (POPIA)</strong></p>
                <p>In terms of POPIA, we are required to obtain your consent to process your personal information. Sanlam takes your privacy seriously. We will only use your personal information in accordance with our Privacy Policy and for the purposes of managing this funeral policy application.</p>
                <p>By checking the box below, you agree to the processing of your data for the purpose of underwriting, policy administration, and claims management.</p>
            </div>

            <div className="consent-checkbox">
                <label className="checkbox-container">
                    <input
                        type="checkbox"
                        checked={isAccepted}
                        onChange={(e) => updateData({ popiaAccepted: e.target.checked, popiaAcceptedAt: new Date().toISOString() })}
                    />
                    <span className="checkmark"></span>
                    I hereby give my clear and unambiguous consent.
                </label>
            </div>

            <div className="btn-group">
                <button
                    className="btn-primary"
                    disabled={!isAccepted}
                    onClick={onNext}
                >
                    Next: Compliance Checklist
                </button>
            </div>
        </div>
    );
};

export default PopiaConsent;
