/**
 * Sanlam Assistant - Frontend Logic
 * Implements the 14-step flow, pricing logic, and African Theme features
 */

// --- DATA STRUCTURES (Ported from Pricing Engine) ---
const RATES = {
    principal: {
        "18-25": { 5000: 23, 10000: 35, 15000: 45, 20000: 55, 30000: 67, 50000: 93, 70000: 117, 100000: 141 },
        "26-35": { 5000: 28, 10000: 46, 15000: 59, 20000: 71, 30000: 86, 50000: 122, 70000: 159, 100000: 214 },
        "36-45": { 5000: 33, 10000: 62, 15000: 76, 20000: 88, 30000: 101, 50000: 138, 70000: 174, 100000: 239 },
        "46-55": { 5000: 61, 10000: 81, 15000: 100, 20000: 120, 30000: 146, 50000: 221, 70000: 284, 100000: 369 },
        "56-65": { 5000: 76, 10000: 116, 15000: 155, 20000: 195, 30000: 242, 50000: 346, 70000: 442, 100000: 614 },
    }
};

// --- APP STATE ---
let currentStepIndex = 0;
let userData = {};
let selectedPlan = 'value'; // 'value' or 'all_in_one'

const MIN_PREMIUMS = {
    value: 80,
    all_in_one: 250
};

// --- DOM ELEMENTS ---
const messagesContainer = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const actionArea = document.getElementById('action-area');
const inputArea = document.getElementById('input-area');
const pricingCard = document.getElementById('pricing-card');
const priceValue = document.querySelector('.price-value');
const productSelection = document.getElementById('product-selection');
const mainChat = document.getElementById('main-chat');
const chatTitle = document.getElementById('chat-title');
const signatureOverlay = document.getElementById('signature-overlay');
const signatureCanvas = document.getElementById('signature-pad');

// --- SIGNATURE PAD LOGIC ---
let isDrawing = false;
let sigCtx = signatureCanvas.getContext('2d');

function setupSignaturePad() {
    sigCtx.strokeStyle = '#3A4F7A'; // Indigo
    sigCtx.lineWidth = 2;
    sigCtx.lineCap = 'round';

    // Mouse Events
    signatureCanvas.addEventListener('mousedown', startDrawing);
    signatureCanvas.addEventListener('mousemove', draw);
    signatureCanvas.addEventListener('mouseup', stopDrawing);
    signatureCanvas.addEventListener('mouseleave', stopDrawing);

    // Touch Events
    signatureCanvas.addEventListener('touchstart', (e) => {
        e.preventDefault(); // Prevent scrolling
        const touch = e.touches[0];
        const mouseEvent = new MouseEvent('mousedown', {
            clientX: touch.clientX,
            clientY: touch.clientY
        });
        signatureCanvas.dispatchEvent(mouseEvent);
    });

    signatureCanvas.addEventListener('touchmove', (e) => {
        e.preventDefault();
        const touch = e.touches[0];
        const mouseEvent = new MouseEvent('mousemove', {
            clientX: touch.clientX,
            clientY: touch.clientY
        });
        signatureCanvas.dispatchEvent(mouseEvent);
    });

    signatureCanvas.addEventListener('touchend', () => {
        const mouseEvent = new MouseEvent('mouseup', {});
        signatureCanvas.dispatchEvent(mouseEvent);
    });
}

function startDrawing(e) {
    isDrawing = true;
    const rect = signatureCanvas.getBoundingClientRect();
    sigCtx.beginPath();
    sigCtx.moveTo(e.clientX - rect.left, e.clientY - rect.top);
}

function draw(e) {
    if (!isDrawing) return;
    const rect = signatureCanvas.getBoundingClientRect();
    sigCtx.lineTo(e.clientX - rect.left, e.clientY - rect.top);
    sigCtx.stroke();
}

function stopDrawing() {
    isDrawing = false;
    sigCtx.closePath();
}

function clearSignature() {
    sigCtx.clearRect(0, 0, signatureCanvas.width, signatureCanvas.height);
}

function saveSignature() {
    const dataUrl = signatureCanvas.toDataURL();
    handleInput("Signed Layout");
    signatureOverlay.classList.add('hidden');
    triggerConfetti();
}

// --- CONFETTI ANIMATION ---
function triggerConfetti() {
    const colors = ['#C36A2D', '#E09F3E', '#6B8E6B', '#3A4F7A', '#9E2A2B'];
    for (let i = 0; i < 40; i++) {
        const confetti = document.createElement('div');
        confetti.className = 'confetti';
        confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        confetti.style.left = Math.random() * 100 + 'vw';
        confetti.style.animationDuration = (Math.random() * 2 + 2) + 's';
        confetti.style.animationDelay = (Math.random() * 2) + 's';
        document.body.appendChild(confetti);

        // Remove after animation
        setTimeout(() => confetti.remove(), 5000);
    }
}


// --- FLOW DEFINITIONS ---

const COMMON_STEPS = [
    {
        id: "consent",
        message: "Before we begin, do you consent to your information being used to process a funeral policy application in line with POPIA?",
        type: "options",
        options: ["Yes, I consent", "No"]
    },
    {
        id: "name",
        message: "Great! Let's start with your full name. What should I call you?",
        type: "text"
    },
    {
        id: "age",
        message: "Thanks! And how old are you?",
        type: "number",
        validate: (v) => v >= 18 && v <= 74 ? "" : "Please enter an age between 18 and 74."
    }
];

const VALUE_STEPS = [
    ...COMMON_STEPS,
    {
        id: "cover",
        message: "How much funeral cover do you want for yourself?",
        type: "options",
        get options() { return Object.keys(RATES.principal["26-35"]).map(k => `R${parseInt(k).toLocaleString()}`); }
    },
    {
        id: "id",
        message: "What is your 13-digit SA ID number?",
        type: "text"
    },
    {
        id: "signature",
        message: "Please sign below to confirm your application.",
        type: "signature"
    },
    {
        id: "summary",
        message: "Calculating your quote...",
        type: "final"
    }
];

const AIO_STEPS = [
    ...COMMON_STEPS,
    {
        id: "cover",
        message: "For the All-in-One Plan, the minimum cover is R10,000. How much cover do you need?",
        type: "options",
        get options() { return ["R10,000", "R20,000", "R30,000", "R50,000", "R100,000"]; }
    },
    {
        id: "family_visual",
        message: "Who else would you like to cover? Use the tabs to find more family members.",
        type: "family_selection"
    },
    {
        id: "id",
        message: "Please enter your 13-digit SA ID number to finalize.",
        type: "text",
        noTyping: true
    },
    {
        id: "signature",
        message: "Please sign below to confirm your application.",
        type: "signature",
        noTyping: true
    },
    {
        id: "summary",
        message: "Finalizing your All-in-One quote...",
        type: "final"
    }
];

let currentFlow = VALUE_STEPS;

// --- FUNCTIONS ---

function selectPlan(plan) {
    selectedPlan = plan;
    currentFlow = plan === 'all_in_one' ? AIO_STEPS : VALUE_STEPS;

    // Update UI
    productSelection.classList.add('hidden');
    mainChat.classList.remove('hidden');
    chatTitle.innerText = plan === 'all_in_one' ? "Sanlam All-in-One Assistant" : "Sanlam Value Assistant";

    setupSignaturePad(); // Init canvas events

    // Start Chat
    setTimeout(renderStep, 500);
}

function addMessage(text, isUser = false) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${isUser ? 'user-message' : 'assistant-message'}`;
    const bubbleStyle = isUser ? 'background: var(--wc-ochre); color: white;' : 'background: white; color: var(--wc-charcoal); border: 1px solid var(--wc-skywash);';
    msgDiv.innerHTML = `<div class="bubble" style="${bubbleStyle}">${text}</div>`;
    messagesContainer.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showTypingIndicator() {
    const existing = document.getElementById('typing-indicator');
    if (existing) return;

    const msgDiv = document.createElement('div');
    msgDiv.id = 'typing-indicator';
    msgDiv.className = 'message assistant-message';
    msgDiv.innerHTML = `<div class="bubble" style="background: white; border: 1px solid var(--wc-skywash); color: var(--wc-charcoal);">
        <div class="typing-dots">
            <span>.</span><span>.</span><span>.</span>
        </div>
    </div>`;
    messagesContainer.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function hideTypingIndicator() {
    const existing = document.getElementById('typing-indicator');
    if (existing) existing.remove();
}

// --- FAMILY CONFIG ---
const FAMILY_TYPES = {
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

let familySelections = {}; // Stores counts: { gogo: 1, aunt: 2 }

function renderStep() {
    const step = currentFlow[currentStepIndex];

    // Reset inputs
    actionArea.innerHTML = '';
    actionArea.classList.add('hidden');
    inputArea.classList.add('hidden');
    signatureOverlay.classList.add('hidden');
    userInput.value = '';

    // Simulate Typing Delay for "Natural" feel
    if (!step.noTyping) showTypingIndicator();

    const delay = step.noTyping ? 0 : Math.random() * 700 + 800;

    setTimeout(() => {
        hideTypingIndicator();
        addMessage(step.message);

        // Show inputs after message appears
        if (step.type === "options") {
            actionArea.classList.remove('hidden');
            step.options.forEach(opt => {
                const btn = document.createElement('button');
                btn.className = 'option-btn';
                btn.innerText = opt;
                btn.style.borderColor = 'var(--wc-indigo)';
                btn.style.color = 'var(--wc-indigo)';
                btn.onclick = () => handleInput(opt);
                actionArea.appendChild(btn);
            });
        } else if (step.type === "family_selection") {
            renderFamilySelectionUI();
        } else if (step.type === "signature") {
            signatureOverlay.classList.remove('hidden');
            clearSignature();
        } else if (step.type !== "final") {
            inputArea.classList.remove('hidden');
            userInput.focus();
        }
    }, delay);
}

function renderFamilySelectionUI() {
    actionArea.classList.remove('hidden');

    const container = document.createElement('div');
    container.className = 'family-selection-container';

    // TABS
    const tabs = document.createElement('div');
    tabs.className = 'family-tabs';

    const tab1 = document.createElement('button');
    tab1.className = 'tab-btn active';
    tab1.innerText = "Immediate Family";
    tab1.onclick = () => switchTab('immediate');

    const tab2 = document.createElement('button');
    tab2.className = 'tab-btn';
    tab2.innerText = "Extended Family";
    tab2.onclick = () => switchTab('extended');

    tabs.appendChild(tab1);
    tabs.appendChild(tab2);
    container.appendChild(tabs);

    // GRIDS
    container.appendChild(createGrid('immediate'));
    container.appendChild(createGrid('extended'));

    // DONE BUTTON
    const doneBtn = document.createElement('button');
    doneBtn.className = 'done-btn';
    doneBtn.innerText = "Done Adding Members";
    doneBtn.onclick = () => submitFamilySelection();
    container.appendChild(doneBtn);

    actionArea.appendChild(container);

    // Default visibility
    document.getElementById('grid-extended').classList.add('hidden-tab');
}

function createGrid(type) {
    const grid = document.createElement('div');
    grid.className = 'family-grid';
    grid.id = `grid-${type}`;

    FAMILY_TYPES[type].forEach(member => {
        const card = document.createElement('div');
        card.className = 'family-card';
        card.id = `card-${member.id}`;

        card.innerHTML = `
            <div class="family-icon">${member.icon}</div>
            <div class="family-label">${member.label}</div>
            <div class="counter-ctrl">
                <button class="ctrl-btn" onclick="updateCount('${member.id}', -1)">-</button>
                <span class="count-display" id="count-${member.id}">0</span>
                <button class="ctrl-btn" onclick="updateCount('${member.id}', 1)">+</button>
            </div>
        `;
        grid.appendChild(card);
    });

    return grid;
}

window.switchTab = function (type) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');

    document.getElementById('grid-immediate').classList.add('hidden-tab');
    document.getElementById('grid-extended').classList.add('hidden-tab');
    document.getElementById(`grid-${type}`).classList.remove('hidden-tab');
}

window.updateCount = function (id, change) {
    event.stopPropagation(); // prevent card click
    const current = familySelections[id] || 0;
    const newCount = Math.max(0, current + change);
    familySelections[id] = newCount;

    document.getElementById(`count-${id}`).innerText = newCount;
    const card = document.getElementById(`card-${id}`);
    if (newCount > 0) card.classList.add('selected');
    else card.classList.remove('selected');
}

function submitFamilySelection() {
    // Summarize
    const summary = [];
    for (const [key, count] of Object.entries(familySelections)) {
        if (count > 0) summary.push(`${count} x ${key}`);
    }
    const text = summary.length > 0 ? summary.join(", ") : "Just me";
    handleInput(text);
}

function handleInput(input) {
    if (!input) return;

    const step = currentFlow[currentStepIndex];

    // Validation
    if (step.validate) {
        const error = step.validate(input);
        if (error) {
            addMessage(error);
            return;
        }
    }

    if (step.type !== "signature") {
        addMessage(input, true);
    } else {
        addMessage("(Signature Captured)", true);
    }

    userData[step.id] = input;

    // Logic for next steps
    currentStepIndex++;
    if (currentStepIndex < currentFlow.length) {
        setTimeout(renderStep, 600);
    } else {
        showFinalSummary();
    }

    updatePriceDisplay();
}

function updatePriceDisplay() {
    if (userData.age && userData.cover) {
        const coverVal = parseInt(userData.cover.replace(/[R,]/g, ''));
        const age = parseInt(userData.age);

        // Find age band (Mock Logic)
        let band = "26-35";
        if (age < 26) band = "18-25";
        else if (age > 35 && age <= 45) band = "36-45";
        else if (age > 45 && age <= 55) band = "46-55";
        else if (age > 55) band = "56-65";

        let price = RATES.principal[band]?.[coverVal] || 0;

        // Enforce Minimum Premium Logic
        const minPremium = MIN_PREMIUMS[selectedPlan];

        if (selectedPlan === 'all_in_one') {
            price = Math.max(price + 50, minPremium); // Base + mock loading
        } else {
            price = Math.max(price, minPremium);
        }

        if (price) {
            priceValue.innerText = `R${price}.00`;
            pricingCard.classList.remove('hidden');
        }
    }
}

function showFinalSummary() {
    setTimeout(() => {
        addMessage(`Summary for ${userData.name} (${selectedPlan === 'all_in_one' ? 'All-in-One' : 'Value Plan'}):<br>
        - Age: ${userData.age}<br>
        - Cover: ${userData.cover}<br>
        - Monthly Premium: ${priceValue.innerText}<br><br>
        Shall I submit this application for <b>${selectedPlan === 'all_in_one' ? 'All-in-One' : 'Value Plan'}</b>?`);

        // Add a "Submit" button dynamically to the action area
        actionArea.innerHTML = '';
        const submitBtn = document.createElement('button');
        submitBtn.className = 'option-btn';
        submitBtn.innerText = "Yes, Submit Application";
        submitBtn.style.background = 'var(--wc-sage)';
        submitBtn.style.color = 'white';
        submitBtn.onclick = submitApplication;
        actionArea.appendChild(submitBtn);
        actionArea.classList.remove('hidden');
        inputArea.classList.add('hidden');

    }, 1000);
}

async function submitApplication() {
    addMessage("Submitting application...", true);
    actionArea.classList.add('hidden');

    showTypingIndicator();

    // Prepare Data
    // Prepare Data
    const payload = {
        name: userData.name,
        age: userData.age,
        id: userData.id,
        cover: userData.cover,
        plan: selectedPlan,
        family: familySelections // Send the raw object: {aunt: 2, gogo: 1}
    };

    try {
        const response = await fetch('/api/submit-application', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        hideTypingIndicator();

        if (result.status === 'success') {
            addMessage(`✅ <b>Success!</b><br>Application has been generated.<br><br>Reference: ${result.path}`);
            triggerConfetti();
        } else {
            addMessage(`❌ <b>Error</b><br>${result.message}`);
        }

    } catch (error) {
        hideTypingIndicator();
        addMessage(`❌ <b>Connection Error</b><br>Could not connect to server. Is it running?`);
        console.error(error);
    }
}

// --- INITIALIZE ---
sendBtn.onclick = () => handleInput(userInput.value);
userInput.onkeypress = (e) => { if (e.key === 'Enter') handleInput(userInput.value); };

// Start logic when plan is selected via selectPlan() in global scope
