import React from 'react';

const Sidebar = () => {
    return (
        <aside className="sidebar">
            <div className="logo">
                <img
                    src="https://www.sanlam.co.za/style%20library/Images/Sanlam-Logo.svg"
                    alt="Sanlam Logo"
                    onError={(e) => { e.target.src = 'https://via.placeholder.com/150x50?text=Sanlam' }}
                />
            </div>
            <div className="intro-content">
                <h1>Value Funeral Plan</h1>
                <p>Secure your family's future with our AI-driven conversational assistant. Fast, simple, and transparent cover.</p>
                <div className="feature-tags">
                    <span>Instant Quotes</span>
                    <span>No Medicals</span>
                    <span>Up to R100k</span>
                </div>
            </div>
            <div className="sidebar-footer">
                <p>&copy; 2024 Sanlam. Licensed FSP.</p>
            </div>
        </aside>
    );
};

export default Sidebar;
