import React, { useState, useEffect } from 'react';
import Intro from './Intro';
import PopiaConsent from './PopiaConsent';
import PolicyholderForm from './PolicyholderForm';
import ComplianceChecklist from './ComplianceChecklist';
import LivesDashboard from './LivesDashboard';
import BeneficiariesForm from './BeneficiariesForm';
import ReviewSubmit from './ReviewSubmit';

const WizardContainer = () => {
    const [step, setStep] = useState(1);
    const [formData, setFormData] = useState(() => {
        const saved = localStorage.getItem('sanlam_formData');
        return saved ? JSON.parse(saved) : null;
    });

    useEffect(() => {
        if (!formData) {
            // Initialize with empty structure matching backend/pdf_fill/default_formData.json
            setFormData({
                flow: { popiaAccepted: false },
                complianceChecklist: { advice: {} },
                policyholder: { telephoneNumbers: {} },
                livesCovered: { principal: { premium: '0' }, spouse: { enabled: false }, children: [], parents: [], widerFamily: [] },
                beneficiaries: []
            });
        }
    }, []);

    useEffect(() => {
        if (formData) {
            localStorage.setItem('sanlam_formData', JSON.stringify(formData));
        }
    }, [formData]);

    const nextStep = () => setStep(prev => prev + 1);
    const prevStep = () => setStep(prev => prev - 1);

    const updateData = (section, data) => {
        setFormData(prev => {
            const newData = { ...prev };
            if (Array.isArray(data)) {
                newData[section] = data;
            } else {
                newData[section] = {
                    ...prev[section],
                    ...data
                };
            }
            return newData;
        });
    };

    if (!formData) return <div>Loading...</div>;

    return (
        <div className="wizard-outer">
            <div className="wizard-progress">
                <div className="progress-bar" style={{ width: `${(step / 7) * 100}%` }}></div>
            </div>

            <div className="wizard-content">
                {step === 1 && <Intro onNext={nextStep} />}
                {step === 2 && <PopiaConsent onNext={nextStep} onPrev={prevStep} data={formData.flow} updateData={(d) => updateData('flow', d)} />}
                {step === 3 && <ComplianceChecklist onNext={nextStep} onPrev={prevStep} data={formData.complianceChecklist} updateData={(d) => updateData('complianceChecklist', d)} />}
                {step === 4 && <PolicyholderForm onNext={nextStep} onPrev={prevStep} data={formData.policyholder} updateData={(d) => updateData('policyholder', d)} />}
                {step === 5 && <LivesDashboard onNext={nextStep} onPrev={prevStep} data={formData.livesCovered} updateData={(d) => updateData('livesCovered', d)} />}
                {step === 6 && <BeneficiariesForm onNext={nextStep} onPrev={prevStep} data={formData.beneficiaries} updateData={(d) => updateData('beneficiaries', d)} />}
                {step === 7 && <ReviewSubmit onPrev={prevStep} data={formData} />}
            </div>
        </div>
    );
};

export default WizardContainer;
