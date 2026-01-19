import React, { useState } from 'react';

const PROVINCES = [
    'Eastern Cape',
    'Free State',
    'Gauteng',
    'KwaZulu-Natal',
    'Limpopo',
    'Mpumalanga',
    'Northern Cape',
    'North West',
    'Western Cape'
];

const SmartAddress = ({ onComplete }) => {
    const [street, setStreet] = useState('');
    const [city, setCity] = useState('');
    const [province, setProvince] = useState('Gauteng');
    const [postalCode, setPostalCode] = useState('');
    const [errors, setErrors] = useState({});

    const handleSubmit = () => {
        const newErrors = {};
        if (!street) newErrors.street = 'Street address required';
        if (!city) newErrors.city = 'City required';
        if (!postalCode || postalCode.length !== 4) newErrors.postalCode = 'Valid 4-digit postal code required';

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }

        setErrors({});

        // Structured data object
        const addressData = {
            street,
            city,
            province,
            postalCode
        };

        // Pass structured data AND display string
        const displayString = `${street}, ${city}, ${province}, ${postalCode}`;
        onComplete(displayString, addressData);
    };

    return (
        <div className="smart-form-container" style={styles.container}>
            <h3 style={styles.header}>Address Details</h3>

            <div className="form-group" style={styles.group}>
                <label style={styles.label}>Street Address</label>
                <input
                    type="text"
                    style={styles.input}
                    value={street}
                    onChange={(e) => setStreet(e.target.value)}
                    placeholder="123 Example St"
                />
            </div>

            <div className="form-group" style={styles.group}>
                <label style={styles.label}>City / Town</label>
                <input
                    type="text"
                    style={styles.input}
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    placeholder="City"
                />
            </div>

            <div className="form-group" style={styles.group}>
                <label style={styles.label}>Province</label>
                <select
                    style={styles.input}
                    value={province}
                    onChange={(e) => setProvince(e.target.value)}
                >
                    {PROVINCES.map(p => (
                        <option key={p} value={p}>{p}</option>
                    ))}
                </select>
            </div>

            <div className="form-group" style={styles.group}>
                <label style={styles.label}>Postal Code</label>
                <input
                    type="number"
                    style={styles.input}
                    value={postalCode}
                    onChange={(e) => setPostalCode(e.target.value)}
                    placeholder="0000"
                />
            </div>

            <button
                style={styles.button}
                onClick={handleSubmit}
                disabled={!street || !city || !postalCode}
            >
                Confirm Address
            </button>
        </div>
    );
};

// Reusing style object pattern
const styles = {
    container: {
        background: '#fff',
        padding: '15px',
        borderRadius: '12px',
        border: '1px solid #e9ecef',
        marginTop: '10px',
        width: '100%',
        maxWidth: '350px',
        boxShadow: '0 2px 5px rgba(0,0,0,0.05)'
    },
    header: {
        margin: '0 0 15px 0',
        fontSize: '1.1rem',
        color: 'var(--wc-charcoal, #333)'
    },
    group: {
        marginBottom: '10px'
    },
    label: {
        display: 'block',
        fontSize: '0.85rem',
        color: '#666',
        marginBottom: '4px'
    },
    input: {
        width: '100%',
        padding: '8px',
        borderRadius: '6px',
        border: '1px solid #ccc',
        fontSize: '1rem'
    },
    button: {
        width: '100%',
        padding: '10px',
        background: 'var(--wc-clay, #d4a373)',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        marginTop: '10px',
        cursor: 'pointer',
        fontWeight: 'bold'
    }
};

export default SmartAddress;
