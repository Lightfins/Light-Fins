import React, { useState } from 'react';

const ReviewSubmit = ({ onPrev, data }) => {
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmit = async () => {
        setSubmitting(true);
        setError(null);
        try {
            const apiUrl = import.meta.env.VITE_API_URL || '/api';
            console.log('Attempting to generate PDF via:', apiUrl); // Debug log
            const response = await fetch(`${apiUrl}/generate-pdf`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            console.log('Response status:', response.status); // Debug log

            if (!response.ok) throw new Error('Failed to generate PDF');

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Sanlam_Application_${data.policyholder?.surname}.pdf`;
            document.body.appendChild(a);
            a.click();
            a.remove();
        } catch (err) {
            setError(err.message);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="wizard-step review-step">
            <h2>6. Review & Submit</h2>
            <div className="review-summary">
                <p>Please review your details before submitting. Once submitted, a 16-page application PDF will be generated for you to download and sign.</p>

                <div className="summary-section">
                    <h4>Policyholder</h4>
                    <p>{data.policyholder?.firstNames} {data.policyholder?.surname}</p>
                    <p>ID: {data.policyholder?.idNumber}</p>
                </div>

                <div className="summary-section">
                    <h4>Lives Covered</h4>
                    <ul>
                        <li>Principal: R{data.livesCovered?.principal?.premium || '0'}</li>
                        {data.livesCovered?.spouse?.enabled && <li>Spouse: {data.livesCovered.spouse.firstNames}</li>}
                        <li>Children: {data.livesCovered?.children?.length || 0}</li>
                        <li>Parents: {data.livesCovered?.parents?.length || 0}</li>
                        <li>Wider Family: {data.livesCovered?.widerFamily?.length || 0}</li>
                    </ul>
                </div>
            </div>

            {error && <p className="error-text">{error}</p>}

            <div className="btn-group">
                <button className="btn-secondary" onClick={onPrev} disabled={submitting}>Back</button>
                <button
                    className="btn-primary"
                    onClick={handleSubmit}
                    disabled={submitting}
                >
                    {submitting ? 'Generating PDF (may take 60s to wake up backend)...' : 'Submit & Download PDF'}
                </button>
            </div>
        </div>
    );
};

export default ReviewSubmit;
