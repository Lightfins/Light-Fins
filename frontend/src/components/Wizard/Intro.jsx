import React from 'react';

const Intro = ({ onNext }) => {
    return (
        <div className="wizard-step intro-step">
            <div className="sanlam-logo-large">
                {/* Placeholder for Sanlam Logo */}
                <img src="/logo.png" alt="Sanlam" style={{ maxWidth: '200px' }} />
            </div>

            <h1>Individual Value Funeral Plan</h1>
            <p className="subtitle">Official Application Wizard</p>

            <div className="intro-card shadow-lg">
                <h3>Welcome</h3>
                <p>This process will guide you through the 16-page official Sanlam application. Your data is protected and will be used to generate a legally binding document.</p>

                <ul className="wizard-highlights">
                    <li>✓ 100% Secure & Compliant</li>
                    <li>✓ Real-time Validation</li>
                    <li>✓ Electronic PDF Generation</li>
                </ul>

                <button className="btn-primary" onClick={onNext}>
                    Begin Application
                </button>
            </div>

            <div className="footer-links">
                <span>Product Version: July 2020</span>
                <span>TR4407 MP40</span>
            </div>
        </div>
    );
};

export default Intro;
