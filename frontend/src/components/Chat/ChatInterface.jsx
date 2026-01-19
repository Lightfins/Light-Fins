import React, { useState, useEffect, useRef } from 'react';
import { useChatFlow } from '../../hooks/useChatFlow';
import PricingCard from '../Pricing/PricingCard';
import FamilySelection from './FamilySelection';
import SignaturePad from './SignaturePad';
import BankDetails from './BankDetails';
import SmartAddress from './SmartAddress';
import ProductSelection from '../ProductSelection/ProductSelection'; // Import the selection component
import { parseSAID } from '../../utils/idParser';
import ProgressIndicator from './ProgressIndicator';

// We now pass MAIN_FLOW from the parent or default to it
import { MAIN_FLOW } from '../../data/flowConfig';

const ChatInterface = () => {
    // We default to 'value' initially but it will be overridden by plan selection
    const [selectedPlan, setSelectedPlan] = useState('value');

    // Custom logic to handle the flow which isn't just a static list anymore
    // But for now, we pass the Unified MAIN_FLOW to the hook
    const {
        messages,
        currentStep,
        isTyping,
        handleInput,
        submitApplication,
        isComplete,
        currentPrice,
        userData,
        setUserData, // We might need to expose this from hook or handle side-effects here
        addMessage // Need to manually add messages sometimes
    } = useChatFlow(MAIN_FLOW, selectedPlan);

    const [inputText, setInputText] = useState('');
    const messagesEndRef = useRef(null);

    // Auto-scroll
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isTyping]);

    // Handle ID Scan Side Effects
    // We observe userData.id_scan and update age/gender automatically
    useEffect(() => {
        if (userData?.id_scan && !userData.age_auto_set) {
            const parsed = parseSAID(userData.id_scan);
            if (parsed && parsed.valid) {
                // Update user data silently or via a system message?
                // For now, let's just make sure the backend gets it.
                // But the hook might calculate price based on 'age'.
                // So we need to feed 'age' into userData.

                // We can't easily reach into the hook's state from outside without a setter.
                // NOTE: I need to modify useChatFlow to return setUserData or handle this.
                // For now, let's assume handleInput(parsed.age) was called? No, ID step calls handleInput with ID.

                // Let's rely on the Quote Step to recalculate. 
                // However, the pricing logic needs 'age'.
                // I will update useChatFlow to parse ID if present.
            }
        }
    }, [userData]);

    const onSend = () => {
        if (currentStep.type === 'text' || currentStep.type === 'number') {
            // Special handling for ID input to validate/parse immediately
            if (currentStep.id === 'id_scan') {
                const parsed = parseSAID(inputText);
                if (!parsed || !parsed.valid) {
                    alert("Invalid ID Number. Please check and try again."); // Simple alert for now, better to use chat bubble
                    return;
                }
                // Determine Age/Gender
                // formatting the display text
                handleInput(inputText, { ...parsed, id: inputText }); // Pass object as actualValue
            } else {
                handleInput(inputText);
            }
            setInputText('');
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') onSend();
    };

    const handleReset = () => {
        if (confirm('Are you sure you want to start over?')) {
            window.location.reload();
        }
    };

    // Render specific UI based on step type
    const renderActionArea = () => {
        if (!currentStep) return null;
        if (isTyping) return null;

        if (isComplete) {
            return (
                <div className="action-area">
                    <button
                        className="option-btn"
                        style={{ background: 'var(--wc-primary)', color: 'white' }}
                        onClick={submitApplication}
                    >
                        Yes, Submit Application
                    </button>
                </div>
            );
        }

        switch (currentStep.type) {
            case 'options':
                return (
                    <div className="action-area">
                        {currentStep.options.map(opt => (
                            <button
                                key={opt}
                                className="option-btn"
                                onClick={() => handleInput(opt)}
                            >
                                {opt}
                            </button>
                        ))}
                    </div>
                );
            case 'family_selection':
                return <FamilySelection onComplete={(text, counts) => handleInput(text, counts)} />;

            case 'plan_selection':
                // We render the product selection cards here
                return (
                    <div className="overlay-container">
                        <ProductSelection onSelectPlan={(plan) => {
                            setSelectedPlan(plan);
                            handleInput(`I chose the ${plan === 'value' ? 'Value' : 'All-in-One'} Plan`, plan);
                        }} />
                    </div>
                );

            case 'quote_presentation':
                // Show the calculated premium and a Proceed button
                // The hook calculates price based on userData.
                // We trigger the next step (Accept Quote) automatically or show a button here?
                // The flow config has 'accept_quote' as the next step. 
                // So this step just shows the price.
                return (
                    <div className="quote-display">
                        <h3>Estimated Premium</h3>
                        <div className="price-tag">R{currentPrice}<span>/pm</span></div>
                        <button className="option-btn" onClick={() => handleInput("Show me options")}>
                            View Options
                        </button>
                    </div>
                );

            case 'bank_details':
                return <BankDetails onComplete={(text, data) => handleInput(text, data)} />;
            case 'address':
                return <SmartAddress onComplete={(text, data) => handleInput(text, data)} />;
            case 'signature':
                return <SignaturePad onSave={(dataUrl) => handleInput(dataUrl)} />;
            default:
                return null;
        }
    };

    return (
        <main className="chat-area" id="main-chat">
            <header className="chat-header">
                <div className="status-indicator">
                    <span className="dot"></span>
                    <span className="status-text">Sanlam Assistant</span>
                </div>
                <h2>New Application</h2>
                <button
                    onClick={handleReset}
                    style={styles.resetBtn}
                    title="Start Over"
                >
                    ↻
                </button>
            </header>

            {currentStep && <ProgressIndicator currentStepId={currentStep.id} />}

            <div className="chat-messages">
                {messages.map(msg => (
                    <div key={msg.id} className={`message ${msg.isUser ? 'user-message' : 'assistant-message'}`}>
                        <div
                            className="bubble"
                            dangerouslySetInnerHTML={{ __html: msg.text }}
                        />
                    </div>
                ))}

                {isTyping && (
                    <div className="message assistant-message">
                        <div className="bubble">
                            <div className="typing-dots">
                                <span>.</span><span>.</span><span>.</span>
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className="chat-input-container">
                {/* Input Field */}
                {currentStep && (currentStep.type === 'text' || currentStep.type === 'number') && !isComplete && (
                    <div className="input-area">
                        <input
                            type={currentStep.type === 'number' ? 'number' : 'text'}
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder={currentStep.id === 'id_scan' ? "Enter 13-digit ID" : "Type here..."}
                            autoFocus
                        />
                        <button className="send-btn" onClick={onSend}>
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: 20, height: 20 }}>
                                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
                            </svg>
                        </button>
                    </div>
                )}

                {/* Actions */}
                {renderActionArea()}
            </div>
        </main>
    );
};

const styles = {
    resetBtn: {
        background: 'transparent',
        border: '1px solid var(--wc-border)',
        borderRadius: '8px',
        padding: '6px 12px',
        cursor: 'pointer',
        fontSize: '1.2rem',
        color: 'var(--wc-text-sec)',
        transition: 'all 0.2s',
        marginLeft: 'auto'
    }
};

export default ChatInterface;
