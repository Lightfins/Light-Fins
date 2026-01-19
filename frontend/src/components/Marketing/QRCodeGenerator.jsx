import React, { useRef, useEffect } from 'react';
import QRCode from 'qrcode';

const QRCodeGenerator = ({ url, size = 200 }) => {
    const canvasRef = useRef(null);

    useEffect(() => {
        if (canvasRef.current && url) {
            QRCode.toCanvas(canvasRef.current, url, {
                width: size,
                margin: 2,
                color: {
                    dark: '#3A4F7A',  // Sanlam indigo
                    light: '#FFFFFF'
                }
            });
        }
    }, [url, size]);

    return (
        <div style={{ textAlign: 'center', padding: '20px' }}>
            <h3 style={{ color: 'var(--wc-indigo)', marginBottom: '15px' }}>
                Share This App
            </h3>
            <canvas ref={canvasRef} style={{ border: '2px solid var(--wc-skywash)', borderRadius: '10px' }} />
            <p style={{ marginTop: '10px', fontSize: '0.9rem', color: 'var(--wc-charcoal)' }}>
                Scan to open on mobile
            </p>
            <div style={{ marginTop: '15px' }}>
                <input
                    type="text"
                    value={url}
                    readOnly
                    style={{
                        width: '100%',
                        maxWidth: '400px',
                        padding: '10px',
                        border: '1px solid var(--wc-skywash)',
                        borderRadius: '5px',
                        textAlign: 'center',
                        fontSize: '0.85rem'
                    }}
                    onClick={(e) => e.target.select()}
                />
                <button
                    onClick={() => {
                        navigator.clipboard.writeText(url);
                        alert('Link copied to clipboard!');
                    }}
                    style={{
                        marginTop: '10px',
                        padding: '10px 20px',
                        background: 'var(--wc-sage)',
                        color: 'white',
                        border: 'none',
                        borderRadius: '5px',
                        cursor: 'pointer',
                        fontWeight: '600'
                    }}
                >
                    Copy Link
                </button>
            </div>
        </div>
    );
};

export default QRCodeGenerator;
