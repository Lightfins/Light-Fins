import { RATES } from './pricingData';

// Unified Flow: Consent -> ID -> Members -> Plan -> Quote -> Address -> Bank -> Sign -> Submit

export const MAIN_FLOW = [
    {
        id: "consent",
        message: "Welcome to Sanlam. Before we begin, do you consent to your information being used to process a funeral policy application in line with POPIA?",
        type: "options",
        options: ["Yes, I consent", "No"]
    },
    {
        id: "id_scan",
        message: "Thank you. Please enter your 13-digit South African ID number so I can fetch your details.",
        type: "text",
        validate: (v) => v.length === 13 && !isNaN(v) ? "" : "Please enter a valid 13-digit ID number."
    },
    {
        id: "member_selection",
        message: "We've got your details. Now, who else would you like to cover? Add your spouse, children, or extended family.",
        type: "family_selection"
    },
    {
        id: "plan_selection",
        message: "Based on your needs, please choose a plan that suits you.",
        type: "plan_selection"  // New type for the card view
    },
    {
        id: "quote",
        message: "Calculating your best premium...",
        type: "quote_presentation" // New type to show the premium
    },
    {
        id: "accept_quote",
        message: "Would you like to proceed with this premium?",
        type: "options",
        options: ["Yes, Accept Quote", "No, adjust coverage"]
    },
    {
        id: "address",
        message: "Great! Let's get your details. Please provide your residential address.",
        type: "address"
    },
    {
        id: "bank_details",
        message: "Please provide your banking details for the debit order.",
        type: "bank_details"
    },
    {
        id: "signature",
        message: "Almost done. Please sign below to confirm your application.",
        type: "signature",
        noTyping: true
    },
    {
        id: "summary",
        message: "Finalizing your application...",
        type: "final"
    }
];

export const FAMILY_TYPES = {
    immediate: [
        { id: 'spouse', label: 'Spouse', icon: '💑' },
        { id: 'child', label: 'Child', icon: '👶' }
    ],
    extended: [
        { id: 'gogo', label: 'Gogo', icon: '👵' },
        { id: 'grandpa', label: 'Grandpa', icon: '👴' },
        { id: 'aunt', label: 'Aunt', icon: '👩' },
        { id: 'uncle', label: 'Uncle', icon: '👨' },
        { id: 'brother', label: 'Brother', icon: '👱' },
        { id: 'sister', label: 'Sister', icon: '👱‍♀️' }
    ]
};

// Helper to get rates if needed elsewhere
export { RATES };
