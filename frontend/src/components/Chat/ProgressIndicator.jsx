import React from 'react';

const FLOW_STEPS = [
    { id: 'consent', label: 'Consent' },
    { id: 'id_scan', label: 'Identity' },
    { id: 'member_selection', label: 'Family' },
    { id: 'plan_selection', label: 'Plan' },
    { id: 'quote', label: 'Quote' },
    { id: 'accept_quote', label: 'Accept' },
    { id: 'address', label: 'Address' },
    { id: 'bank_details', label: 'Banking' },
    { id: 'signature', label: 'Sign' }
];

const ProgressIndicator = ({ currentStepId }) => {
    const currentIndex = FLOW_STEPS.findIndex(step => step.id === currentStepId);
    const progress = currentIndex >= 0 ? ((currentIndex + 1) / FLOW_STEPS.length) * 100 : 0;

    return (
        <div style={styles.container}>
            <div style={styles.progressBar}>
                <div style={{ ...styles.progressFill, width: `${progress}%` }} />
            </div>
            <div style={styles.stepLabels}>
                {FLOW_STEPS.map((step, index) => (
                    <div
                        key={step.id}
                        style={{
                            ...styles.stepDot,
                            backgroundColor: index <= currentIndex ? 'var(--wc-primary)' : '#ddd',
                            transform: index === currentIndex ? 'scale(1.2)' : 'scale(1)'
                        }}
                        title={step.label}
                    />
                ))}
            </div>
        </div>
    );
};

const styles = {
    container: {
        padding: '10px 20px',
        backgroundColor: 'var(--wc-surface)',
        borderBottom: '1px solid var(--wc-border)'
    },
    progressBar: {
        height: '4px',
        backgroundColor: '#e9ecef',
        borderRadius: '2px',
        overflow: 'hidden',
        marginBottom: '8px'
    },
    progressFill: {
        height: '100%',
        background: 'var(--wc-gradient-main)',
        transition: 'width 0.3s ease'
    },
    stepLabels: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
    },
    stepDot: {
        width: '8px',
        height: '8px',
        borderRadius: '50%',
        transition: 'all 0.3s ease',
        cursor: 'pointer'
    }
};

export default ProgressIndicator;
