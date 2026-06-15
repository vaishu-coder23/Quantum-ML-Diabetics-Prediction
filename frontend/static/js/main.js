console.log("QuantumHealth: Main JS Loaded");
window.onerror = function (msg, url, line) {
    console.error(`GLOBAL ERROR: ${msg} at ${url}:${line}`);
};

// --- Translations & Config ---
const translations = {
    en: {
        predict: "Risk Prediction", analysis: "Lab Analysis", reminders: "Medical Log", chat: "AI Advisor", consult: "Consultations", analytics: "Analytics", profile: "My Profile",
        trajectory: "Health Trajectory", predictionHistory: "Prediction History"
    },
    hi: {
        predict: "जोखिम पूर्वानुमान", analysis: "लैब विश्लेषण", reminders: "मेडिकल लॉग", chat: "एआई सलाहकार", consult: "परामर्श", analytics: "विश्लेषण", profile: "मेरी प्रोफाइल",
        trajectory: "स्वास्थ्य प्रक्षेपवक्र", predictionHistory: "भविष्यवाणी इतिहास"
    },
    te: {
        predict: "రిస్క్ ప్రిడిక్షన్", analysis: "ల్యాబ్ అనాలిసిస్", reminders: "మెడికల్ లాగ్", chat: "AI సలహాదారు", consult: "సంప్రదింపులు", analytics: "ఎనలిటిక్స్", profile: "నా ప్రొఫైల్",
        trajectory: "ఆరోగ్య పథం", predictionHistory: "అంచనా చరిత్ర"
    },
    ta: {
        predict: "ஆபத்து கணிப்பு", analysis: "ஆய்வக பகுப்பாய்வு", reminders: "மருத்துவ பதிவு", chat: "AI ஆலோசகர்", consult: "ஆலோசனைகள்", analytics: "பகுப்பாய்வு", profile: "என் சுயவிவரம்",
        trajectory: "சுகாதாரப் பாதை", predictionHistory: "கணிப்பு வரலாறு"
    }
};

let currentLang = 'en';
let riskChart, xaiChart, trendChart;

// --- Module Switching ---
function showModule(mid) {
    document.querySelectorAll('.module').forEach(m => m.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    const target = document.getElementById(mid + '-module');
    if (target) target.classList.add('active');

    // Highlight Nav (Simple index-based or text-based matching)
    const navItems = document.querySelectorAll('.nav-item');
    const modules = ['predict', 'analysis', 'reminders', 'chat', 'consult', 'analytics', 'profile'];
    const idx = modules.indexOf(mid);
    if (idx !== -1 && navItems[idx]) navItems[idx].classList.add('active');

    // Update Header Text using i18n
    const headerTitle = document.getElementById('module-title');
    if (headerTitle && translations[currentLang][mid]) {
        headerTitle.innerText = translations[currentLang][mid];
        headerTitle.setAttribute('data-i18n', mid);
    }

    // Auto-search doctors on initial module show if it's the consult module
    if (mid === 'consult') {
        searchDoctors();
    }
}

// --- Multi-Language Logic ---
function setLanguage(lang) {
    currentLang = lang;
    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (translations[lang] && translations[lang][key]) {
            el.innerText = translations[lang][key];
        }
    });
}

// --- Progressive Form Logic ---
function nextFormStep() {
    const age = document.getElementById('inputAge').value;
    if (!age) {
        alert("Please enter your age first.");
        return;
    }
    document.getElementById('formStep1').style.display = 'none';
    document.getElementById('formStep2').style.display = 'block';
    handleGenderChange(); // Ensure pregnancies field is updated
}

function prevFormStep() {
    document.getElementById('formStep2').style.display = 'none';
    document.getElementById('formStep1').style.display = 'block';
}

function handleGenderChange() {
    const gender = document.getElementById('inputGender').value;
    const pregGroup = document.getElementById('groupPregnancies');
    const pregInput = document.getElementById('inputPregnancies');
    if (gender === 'male') {
        if (pregGroup) pregGroup.style.display = 'none';
        if (pregInput) pregInput.value = 0;
    } else {
        if (pregGroup) pregGroup.style.display = 'block';
    }
}



// --- Prediction Logic ---
async function handlePrediction(event) {
    event.preventDefault();
    console.log("Prediction form submitted...");

    // Hackathon Wow-Factor: Show Quantum Loader
    const loader = document.getElementById('quantumLoader');
    if (loader) loader.style.display = 'flex';

    // Artificial minimum delay to ensure the cool animation plays (1.5 seconds)
    await new Promise(r => setTimeout(r, 1500));

    const formData = new FormData(event.target);
    const langSelect = document.getElementById('langSelect');
    if (langSelect) {
        formData.append('language', langSelect.options[langSelect.selectedIndex].text);
    }
    
    try {
        const response = await fetch('/predict', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();
        console.log("Prediction Result:", result);

        // Hide Loader
        if (loader) loader.style.display = 'none';

        if (result.status === 'success') {
            updatePredictionUI(result);
            loadHistory();
        } else {
            console.error("Prediction Error:", result.message);
            alert("Prediction failed: " + result.message);
        }
    } catch (err) {
        if (loader) loader.style.display = 'none';
        console.error("Fetch Exception:", err);
        alert("Server connection failed.");
    }
}

function updatePredictionUI(data) {
    const riskVal = parseFloat(data.classical_risk);

    // Update Gauge
    if (riskChart) {
        riskChart.data.datasets[0].data = [riskVal, 100 - riskVal];
        riskChart.update();
    }

    document.getElementById('riskPercent').innerText = data.classical_risk;
    document.getElementById('riskCategory').innerText = data.category;
    document.getElementById('quantumStatus').innerText = "Hybrid Result: " + (data.quantum_result || "Diabetic (VQC)");

    // Body effect / sugar type summary
    const impactBox = document.getElementById('bodyImpactSummaryBox');
    if (impactBox && data.body_impact_summary) {
        impactBox.style.display = 'block';
        impactBox.innerHTML = '<strong><span style="font-size:1.2em;">🔍</span> AI Insights:</strong><br>' + data.body_impact_summary;
    }

    // Suggestions from Intelligent Engine
    if (data.analysis) {
        document.getElementById('foodSuggestion').innerText = data.analysis.suggestion;
        document.getElementById('exerciseSuggestion').innerText = data.analysis.exercise || "Moderate 30-min exercise daily.";
        console.log("Suggestions updated from analysis data.");
    } else {
        console.log("No analysis data for suggestions.");
    }

    // Explainable AI (LIME)
    const explainBtn = document.getElementById('btnExplainRisk');
    const limeList = document.getElementById('limeFactorsList');
    if (explainBtn && limeList && data.explanation && Object.keys(data.explanation).length > 0) {
        limeList.innerHTML = '';
        explainBtn.style.display = 'block';

        // Sort explanations by absolute weight magnitude to show most impactful first
        const sortedFactors = Object.entries(data.explanation)
            .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));

        sortedFactors.forEach(([feature, weight]) => {
            // weight > 0 increases risk (red), weight < 0 decreases risk (green)
            const isPositiveRisk = weight > 0;
            const color = isPositiveRisk ? '#ef4444' : '#10b981';
            const icon = isPositiveRisk ? '↑' : '↓';
            const impact = isPositiveRisk ? 'Increases Risk' : 'Lowers Risk';

            limeList.innerHTML += `
                <li style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; background: white; padding: 8px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <span>${feature}</span>
                    <span style="color: ${color}; font-weight: 600; font-size: 0.9em;">
                        ${icon} ${impact}
                    </span>
                </li>`;
        });
    } else if (explainBtn) {
        explainBtn.style.display = 'none';
    }
}

function toggleRiskExplanation() {
    const box = document.getElementById('riskExplanationBox');
    if (box) {
        box.style.display = box.style.display === 'none' ? 'block' : 'none';
    }
}

// --- AI Chat Logic ---
async function handleChat() {
    console.log("handleChat triggered");
    const input = document.getElementById('chatInput');
    if (!input) { console.error("chatInput not found"); return; }
    const msg = input.value.trim();
    if (!msg) return;

    const container = document.getElementById('chatMessages');
    if (!container) { console.error("chatMessages container not found"); return; }

    // Get selected language
    const langSelect = document.getElementById('chatLang');
    const selectedLang = langSelect ? langSelect.value : 'English';

    // Add User Bubble
    container.innerHTML += `
        <div style="text-align: right; margin-bottom: 12px;">
            <span style="background: var(--primary-gradient); padding: 10px 15px; border-radius: 15px 15px 0 15px; display: inline-block; font-size: 0.9rem; color: white; max-width: 75%; word-wrap: break-word;">
                ${msg}
            </span>
        </div>`;

    input.value = '';
    container.scrollTop = container.scrollHeight;

    // Typing Indicator
    const typingId = 'typing-' + Date.now();
    container.innerHTML += `
        <div id="${typingId}" style="background: white; padding: 12px 16px; border-radius: 15px 15px 15px 0; margin-bottom: 12px; font-size: 0.9rem; border: 1px solid rgba(0,0,0,0.05); color: var(--text-muted); width: fit-content; display: flex; align-items: center; gap: 8px;">
            <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#2dd4bf; animation: pulse 1s infinite;"></span> Advisor is thinking...
        </div>`;
    container.scrollTop = container.scrollHeight;

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: msg, language: selectedLang })
        });

        if (!response.ok) throw new Error(`Server error: ${response.status}`);
        const data = await response.json();

        // Remove typing indicator
        const typingEl = document.getElementById(typingId);
        if (typingEl) typingEl.remove();

        // AI Response bubble with speaker button
        const msgId = 'ai-msg-' + Date.now();
        container.innerHTML += `
            <div style="display: flex; align-items: flex-start; gap: 8px; margin-bottom: 14px; max-width: 80%;">
                <div style="width:32px; height:32px; border-radius:50%; background: var(--primary-gradient); flex-shrink:0; display:flex; align-items:center; justify-content:center; font-size:0.9rem;">&#129302;</div>
                <div style="background: white; padding: 14px 18px; border-radius: 0 15px 15px 15px; font-size: 0.92rem; line-height: 1.65; color: var(--text-main); border: 1px solid rgba(0,0,0,0.06); box-shadow: 0 2px 10px rgba(0,0,0,0.04); flex:1;">
                    <span id="${msgId}">${data.response.replace(/\n/g, '<br>')}</span>
                    <button onclick="speakText(document.getElementById('${msgId}').innerText)" title="Listen to response"
                        style="background: rgba(45,212,191,0.1); border: none; cursor: pointer; margin-left: 10px; border-radius: 6px; padding: 3px 8px; font-size: 0.85rem; color: #0d9488; vertical-align: middle;"
                    >&#128266; Listen</button>
                </div>
            </div>`;
    } catch (err) {
        console.error("Chat Error:", err);
        const typingEl = document.getElementById(typingId);
        if (typingEl) typingEl.remove();
        container.innerHTML += `<div style="color: #f87171; font-size: 0.8rem; padding: 10px;">Error: ${err.message}. Please try again.</div>`;
    }

    container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
}

// --- Voice Input (Speech-to-Text) ---
function startVoiceInput() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert('Voice input is not supported in your browser. Please use Chrome.');
        return;
    }

    const langMap = { 'English': 'en-IN', 'Hindi': 'hi-IN', 'Telugu': 'te-IN', 'Tamil': 'ta-IN' };
    const langSelect = document.getElementById('chatLang');
    const selectedLang = langSelect ? langSelect.value : 'English';

    const recognition = new SpeechRecognition();
    recognition.lang = langMap[selectedLang] || 'en-IN';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    const micBtn = document.getElementById('micBtn');
    if (micBtn) { micBtn.style.background = 'rgba(248,113,113,0.2)'; micBtn.innerHTML = '&#9899;'; }

    recognition.start();

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        const chatInput = document.getElementById('chatInput');
        if (chatInput) chatInput.value = transcript;
        if (micBtn) { micBtn.style.background = 'rgba(45,212,191,0.1)'; micBtn.innerHTML = '&#127908;'; }
    };

    recognition.onerror = (event) => {
        console.error('Voice error:', event.error);
        if (micBtn) { micBtn.style.background = 'rgba(45,212,191,0.1)'; micBtn.innerHTML = '&#127908;'; }
    };

    recognition.onend = () => {
        if (micBtn) { micBtn.style.background = 'rgba(45,212,191,0.1)'; micBtn.innerHTML = '&#127908;'; }
    };
}

// --- Voice Output (Text-to-Speech) ---
function speakText(text, language = null) {
    if (!window.speechSynthesis) { alert('Text-to-speech is not supported in your browser.'); return; }
    window.speechSynthesis.cancel(); // Stop any ongoing speech

    const langMap = { 'English': 'en-IN', 'Hindi': 'hi-IN', 'Telugu': 'te-IN', 'Tamil': 'ta-IN' };

    // If language is not provided, try to get it from chatLang
    if (!language) {
        const langSelect = document.getElementById('chatLang');
        language = langSelect ? langSelect.value : 'English';
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = langMap[language] || 'en-IN';
    utterance.rate = 0.95;
    window.speechSynthesis.speak(utterance);
}

// --- Lab Report Analysis ---
async function handleUpload(file) {
    if (!file) return;

    // Get selected language for report analysis
    const langSelect = document.getElementById('reportLang');
    const selectedLang = langSelect ? langSelect.value : 'English';

    const formData = new FormData();
    formData.append('report', file);
    formData.append('language', selectedLang);

    // Show loading state
    const analysisSummary = document.getElementById('analysisSummary');
    if (analysisSummary) analysisSummary.innerText = "Analyzing report and translating to " + selectedLang + "... Please wait.";
    const resultsEl = document.getElementById('analysisResults');
    if (resultsEl) resultsEl.style.display = 'block';

    try {
        const res = await fetch('/upload_report', { method: 'POST', body: formData });
        const data = await res.json();

        if (data.success) {
            document.getElementById('analysisSummary').innerHTML = data.summary.replace(/\n/g, '<br>');
            document.getElementById('detectedDisease').innerText = data.primary_disease;
            
            const riskLevelEl = document.getElementById('patientRiskLevel');
            if (riskLevelEl) {
                riskLevelEl.innerText = data.risk_level;
                const riskColor = data.risk_level === 'High' ? '#ef4444' : (data.risk_level === 'Moderate' ? '#f59e0b' : '#10b981');
                riskLevelEl.style.color = riskColor;
            }

            const medList = document.getElementById('suggestedMeds');
            if (medList) {
                medList.innerHTML = '';
                data.suggested_medicines.forEach(m => {
                    medList.innerHTML += `<li>${m}</li>`;
                });
            }

            // Auto-fill Risk Form
            if (data.features.Glucose) {
                const glucoseFields = document.getElementsByName('Glucose');
                if (glucoseFields.length > 0) glucoseFields[0].value = data.features.Glucose;
            }
            if (data.features.BloodPressure) {
                const bpFields = document.getElementsByName('BloodPressure');
                if (bpFields.length > 0) bpFields[0].value = data.features.BloodPressure;
            }
            if (data.features.BMI) {
                const bmiFields = document.getElementsByName('BMI');
                if (bmiFields.length > 0) bmiFields[0].value = data.features.BMI;
            }
            if (data.features.Age) {
                const ageFields = document.getElementsByName('Age');
                if (ageFields.length > 0) ageFields[0].value = data.features.Age;
            }

            alert("Report Analyzed successfully in " + selectedLang + "!");
        } else {
            alert("Error analyzing report: " + (data.error || "Unknown error"));
        }
    } catch (err) {
        console.error("Upload Error:", err);
        alert("Failed to connect to server for analysis.");
    }
}

function speakReportSummary() {
    const text = document.getElementById('analysisSummary').innerText;
    const langSelect = document.getElementById('reportLang');
    const selectedLang = langSelect ? langSelect.value : 'English';
    speakText(text, selectedLang);
}

// --- Health Management (Doctors & Meds) ---
async function searchDoctors() {
    const area = document.getElementById('doctorArea').value;
    const response = await fetch(`/doctors?area=${area}`);
    const doctors = await response.json();

    const list = document.getElementById('doctorList');
    list.innerHTML = doctors.length ? '' : '<p style="opacity:0.5; grid-column: 1/-1;">No specialists found. Try another area.</p>';

    doctors.forEach(doc => {
        list.innerHTML += `
            <div class="glass-card" style="margin-bottom:0; border-left: 4px solid #6366f1;">
                <h4 style="margin:0;">${doc.name}</h4>
                <p style="font-size:0.8rem; margin:5px 0; opacity:0.7;">${doc.specialty}</p>
                <div style="font-size:0.75rem; background:rgba(0,0,0,0.2); padding:5px; border-radius:5px; margin:10px 0;">Next: ${doc.slots.split(',')[0]}</div>
                <button onclick="bookAppointment(${doc.id}, '${doc.name}')" class="btn btn-primary" style="padding:5px 10px; font-size:0.8rem;">Book Slot</button>
            </div>
        `;
    });
}

async function bookAppointment(docId, docName) {
    await fetch('/book_appointment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doctor_id: docId, date: new Date().toLocaleDateString(), time: "09:00 AM" })
    });
    alert(`Success! Confirmed booking with ${docName}`);
}

async function addMedication() {
    const name = document.getElementById('medName').value;
    const dosage = document.getElementById('medDosage').value;
    const time = document.getElementById('medTime').value;
    if (!name || !time) return;

    await fetch('/medicine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, dosage, frequency: "Daily", time })
    });

    loadMedications();
}

async function loadMedications() {
    // Note: Backend might need to return JSON for this user
    // For now we populate from local state or simple refresh
    const list = document.getElementById('medicineList');
    list.innerHTML = `
        <div style="background:rgba(255,255,255,0.05); padding:12px; border-radius:12px; display:flex; justify-content:space-between; align-items:center;">
            <div>
                <p style="margin:0; font-weight:bold;">Active Monitoring</p>
                <p style="margin:0; font-size:0.8rem; opacity:0.6;">Check dashboard for alerts</p>
            </div>
            <span style="color:#10b981;">●</span>
        </div>
    `;
}

// --- Charts Initialization ---
function initCharts() {
    // Risk Gauge
    const riskCtx = document.getElementById('riskChart').getContext('2d');
    riskChart = new Chart(riskCtx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [0, 100],
                backgroundColor: ['#6366f1', 'rgba(255,255,255,0.05)'],
                borderWidth: 0
            }]
        },
        options: {
            circumference: 180,
            rotation: 270,
            cutout: '85%',
            plugins: { legend: { display: false } }
        }
    });

    // Trend Analysis (Profile)
    const trendCtx = document.getElementById('trendChart').getContext('2d');
    trendChart = new Chart(trendCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Metabolic Risk %',
                data: [],
                borderColor: '#a855f7',
                backgroundColor: 'rgba(168, 85, 247, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.05)' } },
                x: { grid: { display: false } }
            },
            plugins: { legend: { display: false } }
        }
    });

    loadHistory();
}

async function loadHistory() {
    try {
        const response = await fetch('/history');
        const history = await response.json();
        const tbody = document.getElementById('historyTableBody');

        if (history.length > 0) {
            // Update Trend Chart
            trendChart.data.labels = history.map(h => h.date).reverse();
            trendChart.data.datasets[0].data = history.map(h => h.risk).reverse();
            trendChart.update();

            // Populate Table
            if (tbody) {
                tbody.innerHTML = history.map(h => `
                    <tr style="border-bottom: 1px solid rgba(0,0,0,0.05);">
                        <td style="padding: 10px;">${h.date}</td>
                        <td style="padding: 10px;">
                            <span style="background: rgba(168, 85, 247, 0.1); color: #a855f7; padding: 4px 8px; border-radius: 6px; font-size: 0.85em; font-weight: bold;"><|...|>