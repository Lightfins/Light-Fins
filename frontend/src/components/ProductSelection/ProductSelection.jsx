import React from 'react';

const ProductSelection = ({ onSelectPlan }) => {
    return (
        <div id="product-selection" className="product-selection">
            <div className="selection-card">
                <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginBottom: '20px' }}>
                    <span style={{ color: 'var(--wc-ochre)', fontSize: '24px' }}>✨</span>
                    <span style={{ color: 'var(--wc-clay)', fontSize: '24px' }}>⭐</span>
                    <span style={{ color: 'var(--wc-sage)', fontSize: '24px' }}>✨</span>
                </div>
                <h2>Protect Your Tribe</h2>
                <p>Calm. Grounded. Built for family continuity.</p>

                <div className="plan-options">
                    <div className="plan-option" onClick={() => onSelectPlan('value')}>
                        <div className="plan-icon">💎</div>
                        <h3>Value Funeral Plan</h3>
                        <ul>
                            <li>Covers up to 10 family members</li>
                            <li>Premiums from R80pm</li>
                            <li>Simple, fast cover</li>
                        </ul>
                        <button className="select-btn">Select Value Plan</button>
                    </div>

                    <div className="plan-option" onClick={() => onSelectPlan('all_in_one')}>
                        <div className="plan-icon">🌟</div>
                        <h3>All-in-One Plan</h3>
                        <ul>
                            <li>Covers up to 30 family members</li>
                            <li>Includes Life & Grocery cover</li>
                            <li>Premiums from R250pm</li>
                        </ul>
                        <button className="select-btn">Select All-in-One</button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProductSelection;
