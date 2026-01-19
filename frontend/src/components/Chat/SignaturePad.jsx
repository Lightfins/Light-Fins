import React, { useRef, useState, useEffect } from 'react';

const SignaturePad = ({ onSave }) => {
    const canvasRef = useRef(null);
    const [isDrawing, setIsDrawing] = useState(false);
    const [isEmpty, setIsEmpty] = useState(true);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (canvas) {
            const ctx = canvas.getContext('2d');
            ctx.strokeStyle = '#000000';
            ctx.lineWidth = 2;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
        }
    }, []);

    const startDrawing = (e) => {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left || e.touches[0].clientX - rect.left;
        const y = e.clientY - rect.top || e.touches[0].clientY - rect.top;

        ctx.beginPath();
        ctx.moveTo(x, y);
        setIsDrawing(true);
        setIsEmpty(false);
    };

    const draw = (e) => {
        if (!isDrawing) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        const rect = canvas.getBoundingClientRect();
        const x = e.clientX - rect.left || e.touches[0].clientX - rect.left;
        const y = e.clientY - rect.top || e.touches[0].clientY - rect.top;

        ctx.lineTo(x, y);
        ctx.stroke();
    };

    const stopDrawing = () => {
        setIsDrawing(false);
    };

    const clearCanvas = () => {
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        setIsEmpty(true);
    };

    const handleSave = () => {
        if (isEmpty) {
            alert('Please provide your signature before proceeding.');
            return;
        }
        const canvas = canvasRef.current;
        const dataUrl = canvas.toDataURL();
        onSave(dataUrl);
    };

    return (
        <div style={styles.container}>
            <h3 style={styles.title}>Sign Below</h3>
            <canvas
                ref={canvasRef}
                width={350}
                height={150}
                style={styles.canvas}
                onMouseDown={startDrawing}
                onMouseMove={draw}
                onMouseUp={stopDrawing}
                onMouseLeave={stopDrawing}
                onTouchStart={startDrawing}
                onTouchMove={draw}
                onTouchEnd={stopDrawing}
            />
            <div style={styles.buttons}>
                <button onClick={clearCanvas} style={styles.clearBtn}>
                    Clear
                </button>
                <button onClick={handleSave} style={styles.saveBtn}>
                    Confirm Signature
                </button>
            </div>
        </div>
    );
};

const styles = {
    container: {
        background: '#fff',
        padding: '20px',
        borderRadius: '12px',
        border: '1px solid var(--wc-border)',
        marginTop: '10px',
        width: '100%',
        maxWidth: '380px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
    },
    title: {
        margin: '0 0 15px 0',
        fontSize: '1rem',
        color: 'var(--wc-text-main)',
        fontWeight: 600
    },
    canvas: {
        border: '2px dashed var(--wc-border)',
        borderRadius: '8px',
        cursor: 'crosshair',
        backgroundColor: '#fafafa',
        display: 'block',
        width: '100%',
        touchAction: 'none'
    },
    buttons: {
        display: 'flex',
        gap: '10px',
        marginTop: '15px'
    },
    clearBtn: {
        flex: 1,
        padding: '10px',
        background: 'white',
        color: 'var(--wc-text-sec)',
        border: '1px solid var(--wc-border)',
        borderRadius: '8px',
        cursor: 'pointer',
        fontWeight: 500,
        transition: 'all 0.2s'
    },
    saveBtn: {
        flex: 2,
        padding: '10px',
        background: 'var(--wc-primary)',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        cursor: 'pointer',
        fontWeight: 600,
        transition: 'all 0.2s'
    }
};

export default SignaturePad;
