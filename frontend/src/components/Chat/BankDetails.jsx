import React, { useState, useEffect } from 'react';

const BANKS = [
    { name: 'Capitec', code: '470010' },
    { name: 'FNB', code: '250655' },
    { name: 'Standard Bank', code: '051001' },
    { name: 'Absa', code: '632005' },
    { name: 'Nedbank', code: '198765' },
    { name: 'Tymebank', code: '678910' },
    { name: 'African Bank', code: '430000' },
    { name: 'Other', code: '' }
];

const ACCOUNT_TYPES = [
    'Savings',
    'Cheque',
    'Transmission'
];

const BankDetails = ({ onComplete }) => {
    const [bank, setBank] = useState('');
    const [branchCode, setBranchCode] = useState('');
    const [accountNumber, setAccountNumber] = useState('');
    const [accountType, setAccountType] = useState('Savings');
    const [errors, setErrors] = useState({});

    // Auto-fill branch code when bank changes
    useEffect(() => {
        const selectedBank = BANKS.find(b => b.name === bank);
        if (selectedBank) {
            setBranchCode(selectedBank.code);
        }
    }, [bank]);

    const handleSubmit = () => {
        const newErrors = {};
        if (!bank) newErrors.bank = 'Please select a bank';
        if (!branchCode) newErrors.branchCode = 'Branch code required';
        if (!accountNumber || accountNumber.length < 8) newErrors.accountNumber = 'Valid account number required (min 8 digits)';

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }

        setErrors({});

        // Structured data object
        const bankData = {
            bank,
            branchCode,
            accountNumber,
            accountType
        };

        // Pass structured data AND a display string for the chat
        const displayString = `Bank: ${bank}, Acc: ${accountNumber} (${accountType})`;
        onComplete(displayString, bankData);
    };

    return (
        <div className="smart-form-container" style={styles.container}>
            <h3 style={styles.header}>Banking Details</h3>

            <div className="form-group" style={styles.group}>
                <label style={styles.label}>Bank Name</label>
                <select
                    style={styles.input}
                    value={bank}
                    onChange={(e) => setBank(e.target.value)}
                >
                    <option value="">Select a Bank...</option>
                    {BANKS.map(b => (
                        <option key={b.name} value={b.name}>{b.name}</option>
                    ))}
                </select>
            </div>

            <div className="form-group" style={styles.group}>
                <label style={styles.label}>Branch Code</label>
                <input
                    type="text"
                    style={styles.input}
                    value={branchCode}
                    onChange={(e) => setBranchCode(e.target.value)}
                    placeholder="Branch Code"
                />
            </div>

            <div className="form-group" style={styles.group}>
                <label style={styles.label}>Account Number</label>
                <input
                    type="number"
                    style={styles.input}
                    value={accountNumber}
                    onChange={(e) => setAccountNumber(e.target.value)}
                    placeholder="Enter Account Number"
                />
            </div>

            <div className="form-group" style={styles.group}>
                <label style={styles.label}>Account Type</label>
                <select
                    style={styles.input}
                    value={accountType}
                    onChange={(e) => setAccountType(e.target.value)}
                >
                    {ACCOUNT_TYPES.map(type => (
                        <option key={type} value={type}>{type}</option>
                    ))}
                </select>
            </div>

            <button
                style={styles.button}
                onClick={handleSubmit}
                disabled={!bank || !accountNumber}
            >
                Confirm Banking Details
            </button>
        </div>
    );
};

// Inline styles for speed, should ideally move to CSS file
const styles = {
    container: {
        background: '#f8f9fa',
        padding: '15px',
        borderRadius: '12px',
        border: '1px solid #e9ecef',
        marginTop: '10px',
        width: '100%',
        maxWidth: '350px'
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
        background: 'var(--wc-primary)',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        marginTop: '10px',
        cursor: 'pointer',
        fontWeight: 'bold'
    },
    error: {
        color: '#dc3545',
        fontSize: '0.75rem',
        marginTop: '4px',
        display: 'block'
    }
};

export default BankDetails;
