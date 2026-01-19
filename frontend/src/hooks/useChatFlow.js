import { useState, useEffect, useRef } from 'react';
import { RATES, MIN_PREMIUMS } from '../data/pricingData';

export const useChatFlow = (initialFlow, selectedPlan) => {
    const [messages, setMessages] = useState([]);
    const [currentStepIndex, setCurrentStepIndex] = useState(0);
    const [userData, setUserData] = useState({});
    const [isTyping, setIsTyping] = useState(false);
    const [currentPrice, setCurrentPrice] = useState(0);
    const [isComplete, setIsComplete] = useState(false);
    const [isCalculating, setIsCalculating] = useState(false);

    // Safety check
    const flow = initialFlow || [];
    const currentStep = flow[currentStepIndex];

    const addMessage = (text, isUser = false) => {
        setMessages(prev => [...prev, { text, isUser, id: Date.now() + Math.random() }]);
    };

    // Initialize chat
    useEffect(() => {
        if (flow.length > 0 && messages.length === 0) {
            processStep(flow[0]);
        }
    }, [flow]);

    const calculatePrice = (data) => {
        if (data.age && data.cover) {
            const coverVal = parseInt(data.cover.replace(/[R,]/g, ''));
            const age = parseInt(data.age);

            // Find age band
            let band = "26-35";
            if (age < 26) band = "18-25";
            else if (age > 35 && age <= 45) band = "36-45";
            else if (age > 45 && age <= 55) band = "46-55";
            else if (age > 55) band = "56-65";

            // Default to max band price if age > 65 or fallback
            // RATES data might not cover everyone, but let's assume it does for this demo

            let price = RATES.principal[band]?.[coverVal] || 0;
            const minPremium = MIN_PREMIUMS[selectedPlan] || 0;

            if (selectedPlan === 'all_in_one') {
                price = Math.max(price + 50, minPremium);
            } else {
                price = Math.max(price, minPremium);
            }
            return price;
        }
        return 0;
    };

    const processStep = (step) => {
        setIsTyping(true);
        const delay = step.noTyping ? 0 : Math.random() * 700 + 800;

        setTimeout(() => {
            setIsTyping(false);
            addMessage(step.message);
        }, delay);
    };

    const handleInput = async (input, actualValue = null) => {
        if (!input) return;

        // Validation
        if (currentStep.validate) {
            const error = currentStep.validate(input);
            if (error) {
                addMessage(error);
                return;
            }
        }

        // Add User Message
        const displayInput = currentStep.type === "signature" ? "(Signature Captured)" : input;
        addMessage(displayInput, true);

        // Update Data
        // If actualValue is provided (e.g. object for family, or parsed ID), use that.
        // If it's the ID step, actualValue is { id, age, gender, valid, birthDate }. We need to flatten or store nicely.

        let newData = { ...userData };

        if (currentStep.id === 'id_scan' && typeof actualValue === 'object') {
            newData = {
                ...newData,
                [currentStep.id]: input, // Store ID string
                age: actualValue.age,
                gender: actualValue.gender,
                dob: actualValue.birthDate,
                id: actualValue.id
            };
        } else {
            const valueToStore = actualValue !== null ? actualValue : input;
            newData = { ...newData, [currentStep.id]: valueToStore };
        }

        setUserData(newData);

        // Update Price with loading state
        if (currentStep.id === 'plan_selection' && actualValue) {
            setIsCalculating(true);
            setTimeout(() => {
                const price = calculatePrice(newData);
                if (price > 0) setCurrentPrice(price);
                setIsCalculating(false);
            }, 800);
        } else {
            const price = calculatePrice(newData);
            if (price > 0) setCurrentPrice(price);
        }

        // Next Step
        const nextIndex = currentStepIndex + 1;
        if (nextIndex < flow.length) {
            setCurrentStepIndex(nextIndex);
            processStep(flow[nextIndex]);
        } else {
            // End of flow
            showFinalSummary(newData, price);
        }
    };

    const showFinalSummary = (finalData, finalPrice) => {
        setIsTyping(true);
        setTimeout(() => {
            setIsTyping(false);
            const planName = selectedPlan === 'all_in_one' ? 'All-in-One' : 'Value Plan';
            const text = `Summary for ${finalData.name} (${planName}):<br>
            - Age: ${finalData.age}<br>
            - Cover: ${finalData.cover}<br>
            - Monthly Premium: R${finalPrice}.00<br><br>
            Shall I submit this application?`;

            addMessage(text);
            setIsComplete(true); // Helper to show Submit button
        }, 1000);
    };

    const submitApplication = async () => {
        addMessage("Submitting application...", true);
        setIsTyping(true);

        const payload = {
            name: userData.name,
            age: userData.age,
            id: userData.id,
            cover: userData.cover,
            plan: selectedPlan,
            family: userData.family_visual // The family selection component returns text, but we might want the object. 
            // In app.js it stored text in userData[step.id] but the raw object in familySelections global.
            // We need to fix this.
        };

        // For now, let's assume family data is in userData (we will handle object passing in ChatInterface)
        // If userData.family_visual is just text, we might lose the counts.
        // We will fix this by handling object input in handleInput.

        try {
            const response = await fetch('/api/submit-application', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            setIsTyping(false);

            if (result.status === 'success') {
                addMessage(`✅ <b>Success!</b><br>Application generated.<br>Reference: ${result.path}`);
            } else {
                addMessage(`❌ <b>Error</b><br>${result.message}`);
            }
        } catch (error) {
            setIsTyping(false);
            addMessage(`❌ <b>Connection Error</b><br>Could not connect to server. Is it running?`);
        }
    };

    return {
        messages,
        currentStep,
        isTyping,
        handleInput,
        submitApplication,
        isComplete,
        currentPrice,
        userData,
        isCalculating,
        addMessage,
        setUserData
    };
};
