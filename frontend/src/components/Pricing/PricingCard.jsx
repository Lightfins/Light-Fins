import React from 'react';

const PricingCard = ({ price }) => {
    // If price is null/undefined or we want to hide it, handle via parent prompt or local check
    // But for now, simple render
    return (
        <div id="pricing-card" className="pricing-card">
            <div className="card-header">Your Quote</div>
            <div className="card-body">
                <div className="price-value">R{price.toFixed(2)}</div>
                <div className="price-label">Per Month</div>
            </div>
        </div>
    );
};

export default PricingCard;
