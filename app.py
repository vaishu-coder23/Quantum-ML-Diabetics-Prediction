from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
import os
import json
import numpy as np
import pandas as pd
from datetime import datetime
from werkzeug.utils import secure_filename
from functools import wraps

# Import custom modules
from authlib.integrations.flask_client import OAuth
from backend.data_processor import DataProcessor
from backend.quantum_engine import QuantumEngine
from backend.classical_engine import ClassicalEngine
from backend.ocr_service import OCRService
from backend.pdf_service import PDFService
from backend.chatbot_service import ChatbotService
from backend.db_manager import DatabaseManager, User, Doctor, MedicationReminder, Appointment

# New Integrations
from backend.sms_service import send_sms
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__, template_folder='frontend/templates', static_folder='frontend/static')
# A static secret key is required for OAuth sessions to persist between redirects!
app.secret_key = "temp_key"
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB
app.config['GEMINI_API_KEY'] = ""

# 🔹 OAuth Setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='',
    client_secret = "",
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# Ensure directories exist
for folder in [app.config['UPLOAD_FOLDER'], 'static/reports', 'models', 'data']:
    os.makedirs(folder, exist_ok=True)

# Initialize Services
db = DatabaseManager()
dp = DataProcessor()
qe = QuantumEngine()
ce = ClassicalEngine()
ocr = OCRService(api_key=app.config.get('GEMINI_API_KEY'))
pdf = PDFService()
bot = ChatbotService(api_key=app.config.get('GEMINI_API_KEY'))

# Global state for models
models_initialized = False

# --- Twilio & Scheduling Setup ---
def check_alerts():
    """Poll DB for active medications and appointments, sending SMS via Twilio if the time matches the current time."""
    now_time = datetime.now().strftime("%H:%M")
    now_date = datetime.now().strftime("%Y-%m-%d")
    try:
        session_db = db.Session()
        
        # 1. Check Medications
        medications = session_db.query(MedicationReminder).filter_by(is_active=1, reminder_time=now_time).all()
        for med in medications:
            user = session_db.query(User).filter_by(id=med.user_id).first()
            if user and user.phone_number:
                msg = f"Quantum Health Alert: Hi {user.full_name or user.username}, it's time to take your {med.dosage} of {med.med_name}."
                print(f"[{now_time}] Sending Rx SMS to {user.phone_number}")
                send_sms(user.phone_number, msg)
                
        # 2. Check Appointments
        appointments = session_db.query(Appointment).filter_by(appointment_date=now_date, appointment_time=now_time).all()
        for apt in appointments:
            user = session_db.query(User).filter_by(id=apt.user_id).first()
            doctor = session_db.query(Doctor).filter_by(id=apt.doctor_id).first()
            if user and user.phone_number and doctor:
                msg = f"Quantum Health Alert: Hi {user.full_name or user.username}, your follow-up appointment with {doctor.name} is scheduled for right now!"
                print(f"[{now_time}] Sending Appt SMS to {user.phone_number}")
                send_sms(user.phone_number, msg)
                
        session_db.close()
    except Exception as e:
        print("Scheduler Error:", e)

scheduler = BackgroundScheduler()
scheduler.add_job(check_alerts, 'cron', minute='*') # Run exactly at the top of every minute
scheduler.start()

# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth'))
        return f(*args, **kwargs)
    return decorated_function

def initialize_models():
    global models_initialized
    # Load data first (required by both engines)
    try:
        X_train, X_test, y_train, y_test = dp.load_data()
    except Exception as e:
        print(f"FATAL: Could not load data: {e}")
        return

    # Classical Engine (primary - required)
    try:
        if not ce.load_model():
            ce.train(X_train, y_train, X_test, y_test)
            ce.save_model()
        print("Classical engine ready.")
    except Exception as e:
        print(f"Error initializing classical engine: {e}")
        return  # Cannot proceed without classical engine

    # Quantum Engine (secondary - optional)
    try:
        if not qe.load_model():
            qe.train(X_train[:100], y_train[:100])
            qe.save_model()
        print("Quantum engine ready.")
    except Exception as e:
        print(f"Quantum engine unavailable (using classical fallback): {e}")

    models_initialized = True
    print("Models initialized successfully.")

# --- Routes ---

@app.route('/auth')
def auth():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('auth.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    success, user_id = db.verify_user(data.get('username'), data.get('password'))
    if success:
        session['user_id'] = user_id
        session['username'] = data.get('username')
        return jsonify({"success": True, "message": "Login successful"}), 200
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    success, res = db.create_user(
        data.get('username'), 
        data.get('password'), 
        data.get('email'),
        data.get('fullname')
    )
    if success:
        session['user_id'] = res
        session['username'] = data.get('username')
        return jsonify({"success": True})
    return jsonify({"success": False, "message": res}), 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth'))

@app.route("/google_login")
def google_login():
    redirect_uri = url_for('auth_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/auth/callback")
def auth_callback():
    token = google.authorize_access_token()
    
    # In newer Authlib versions with OIDC, user_info is automatically decoded into the token!
    user_info = token.get('userinfo')
    
    # Fallback to an absolute URL if the token didn't contain userinfo
    if not user_info:
        user_info = google.get('https://www.googleapis.com/oauth2/v3/userinfo').json()
        
    email = user_info.get('email')
    name = user_info.get('name')
    
    session_db = db.Session()
    user = session_db.query(User).filter_by(email=email).first()
    
    if not user:
        # Create user
        import binascii
        random_pass = binascii.hexlify(os.urandom(16)).decode()
        username = email.split('@')[0] if email else name.replace(" ", "")
        
        # Check if username exists, append random if it does
        if session_db.query(User).filter_by(username=username).first():
            username = username + str(os.urandom(4).hex())
            
        success, user_id_or_msg = db.create_user(username=username, password=random_pass, email=email, full_name=name)
        if success:
            user_id = user_id_or_msg
        else:
            session_db.close()
            return f"Error creating user: {user_id_or_msg}", 400
    else:
        user_id = user.id
        username = user.username
        
    session_db.close()
    
    session['user_id'] = user_id
    session['username'] = username
    
    return redirect(url_for('dashboard'))

# --- Patient History Routes ---
@app.route('/api/user/appointments', methods=['GET'])
@login_required
def user_appointments():
    session_db = db.Session()
    apts = session_db.query(Appointment).filter_by(user_id=session['user_id']).all()
    res = []
    for a in apts:
        doc = session_db.query(Doctor).filter_by(id=a.doctor_id).first()
        res.append({
            "doctor_name": doc.name if doc else "Unknown",
            "date": a.appointment_date,
            "time": a.appointment_time
        })
    session_db.close()
    return jsonify(res)

@app.route('/api/user/medications', methods=['GET'])
@login_required
def user_medications():
    session_db = db.Session()
    meds = session_db.query(MedicationReminder).filter_by(user_id=session['user_id']).all()
    res = [{
        "name": m.med_name,
        "dosage": m.dosage,
        "frequency": m.frequency,
        "time": m.reminder_time,
        "active": m.is_active
    } for m in meds]
    session_db.close()
    return jsonify(res)

@app.route('/api/user/add_medication', methods=['POST'])
@login_required
def add_user_medication():
    data = request.get_json()
    try:
        db.add_medication(
            name=data.get('name'),
            dosage=data.get('dosage'),
            frequency=data.get('frequency'),
            time=data.get('time'),
            user_id=session['user_id']
        )
        return jsonify({"success": True, "message": "Medication reminder scheduled successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# --- Doctor Portal Routes ---
@app.route('/doctor_login', methods=['POST'])
def doctor_login():
    data = request.get_json()
    success, doc_id, msg = db.verify_doctor(data.get('username'), data.get('password'))
    if success:
        session['doc_id'] = doc_id
        session['username'] = data.get('username')
        return jsonify({"success": True}), 200
    return jsonify({"success": False, "message": msg}), 401

@app.route('/doctor_signup', methods=['POST'])
def doctor_signup():
    data = request.get_json()
    success, msg = db.create_doctor_request(
        data.get('username'), data.get('password'), data.get('name'), 
        data.get('specialty'), data.get('area'), data.get('pincode')
    )
    if success:
        return jsonify({"success": True, "message": msg}), 200
    return jsonify({"success": False, "message": msg}), 400

# --- Admin Routes ---
@app.route('/admin_login', methods=['POST'])
def admin_login():
    data = request.get_json()
    if data.get('username') == 'admin' and data.get('password') == 'admin123':
        session['admin_logged_in'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Invalid admin credentials"}), 401

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('auth'))
    
    pending_doctors = db.get_pending_doctors()
    all_doctors = db.get_all_doctors()
    all_users = db.get_all_users()
    all_patients = db.get_all_patient_history()
    return render_template('admin.html', pending=pending_doctors, doctors=all_doctors, users=all_users, patients=all_patients)

@app.route('/api/admin/approve_doctor', methods=['POST'])
def admin_approve_doctor():
    if not session.get('admin_logged_in'):
        return jsonify({"success": False}), 401
    data = request.get_json()
    success = db.approve_doctor(data.get('doctor_id'))
    return jsonify({"success": success})

@app.route('/api/admin/delete_doctor', methods=['POST'])
def admin_delete_doctor():
    if not session.get('admin_logged_in'):
        return jsonify({"success": False}), 401
    data = request.get_json()
    success = db.delete_doctor(data.get('doctor_id'))
    if success and session.get('doc_id') == data.get('doctor_id'):
        session.pop('doc_id', None)
    return jsonify({"success": success})

@app.route('/api/admin/delete_user', methods=['POST'])
def admin_delete_user():
    if not session.get('admin_logged_in'):
        return jsonify({"success": False}), 401
    data = request.get_json()
    success = db.delete_user(data.get('user_id'))
    if success and session.get('user_id') == data.get('user_id'):
        session.pop('user_id', None)
    return jsonify({"success": success})


@app.route('/doctor_dashboard')
def doctor_dashboard():
    if 'doc_id' not in session:
        return redirect(url_for('auth'))
    return render_template('doctor.html')

@app.route('/api/doctor/appointments', methods=['GET'])
def doctor_appointments():
    if 'doc_id' not in session:
        return jsonify([]), 401
    session_db = db.Session()
    apts = session_db.query(Appointment).filter_by(doctor_id=session['doc_id']).all()
    res = [{"user_id": a.user_id, "user_name": a.user_name, "appointment_date": a.appointment_date, "appointment_time": a.appointment_time} for a in apts]
    # If no appointments exist for demo purposes, list all users implicitly so doctor can prescribe
    if not res:
        users = session_db.query(User).all()
        res = [{"user_id": u.id, "user_name": u.full_name or u.username, "appointment_date": "Demo", "appointment_time": "Demo"} for u in users]
    session_db.close()
    return jsonify(res)

@app.route('/api/doctor/prescribe', methods=['POST'])
def doctor_prescribe():
    if 'doc_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.get_json()
    try:
        user_id = data.get('user_id')
        db.add_medication(
            name=data.get('name'),
            dosage=data.get('dosage'),
            frequency=data.get('frequency'),
            time=data.get('time'),
            user_id=user_id
        )
        # Send Immediate SMS Confirmation
        session_db = db.Session()
        user = session_db.query(User).filter_by(id=user_id).first()
        doc = session_db.query(Doctor).filter_by(id=session['doc_id']).first()
        if user and user.phone_number:
            from backend.sms_service import send_sms
            doc_name = doc.name if doc else "Specialist"
            msg = f"Quantum Health Alert: {doc_name} has prescribed a new medication for you: {data.get('name')} ({data.get('dosage')}). It is now available in your Patient Portal."
            send_sms(user.phone_number, msg)
        session_db.close()
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/api/doctor/patient_history/<int:user_id>', methods=['GET'])
def doctor_patient_history(user_id):
    if 'doc_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    history = db.get_history(limit=50, user_id=user_id)
    return jsonify([{
        "date": h.timestamp.strftime("%Y-%m-%d"),
        "risk": h.risk_percentage,
        "category": h.result_category
    } for h in history])

@app.route('/api/doctor/schedule_appointment', methods=['POST'])
def doctor_schedule_appointment():
    if 'doc_id' not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401
    data = request.get_json()
    try:
        session_db = db.Session()
        user = session_db.query(User).filter_by(id=data.get('user_id')).first()
        doc = session_db.query(Doctor).filter_by(id=session['doc_id']).first()
        user_name = user.full_name or user.username if user else "Unknown"
        doc_name = doc.name if doc else "Specialist"
        
        db.add_appointment(
            doctor_id=session['doc_id'],
            user_name=user_name,
            date=data.get('date'),
            time=data.get('time'),
            user_id=data.get('user_id')
        )
        
        if user and user.phone_number:
            from backend.sms_service import send_sms
            msg = f"Quantum Health Alert: {doc_name} has scheduled a follow-up appointment with you on {data.get('date')} at {data.get('time')}. Please check your Patient Portal."
            send_sms(user.phone_number, msg)
            
        session_db.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# --- End Doctor Routes ---

@app.route('/')
def landing():
    # If user is already logged in, they can still view landing, or we could redirect
    # Let's just render the beautiful landing page.
    return render_template('landing.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if not models_initialized:
        initialize_models()
    return render_template('index.html')

@app.route("/predict", methods=["POST"])
@login_required
def predict():
    try:
        # Get data from form (Pima features)
        user_input = {col: float(request.form.get(col, 0)) for col in dp.feature_columns}
        
        # Prepare for prediction
        X_input = dp.prepare_input(user_input)
        
        # Classical Prediction (used for risk percentage)
        c_label, c_risk = ce.predict(X_input)
        
        # Explainable AI (LIME)
        explanation = ce.explain(X_input)
        
        # Advanced Intelligence: Condition Analysis (Type 1/2, Alternatives)
        analysis = ce.analyze_condition(user_input, c_risk)
        
        # New Feature: AI Body Impact Summary in Multi-Language
        lang = request.form.get('language', 'English')
        prompt = f"The user just took a diabetes risk test and the result indicates: {analysis['type']}. In exactly 2-3 short sentences, explain in {lang} language what type of sugar/diabetes this represents, and clearly list what specific parts of the body this is going to affect if left unmanaged."
        body_impact = bot.get_response(prompt, patient_context="The user is viewing their immediate risk results.")
        
        # Quantum Prediction (with graceful fallback)
        try:
            q_label = qe.predict(X_input)
        except Exception:
            q_label = c_label
        
        # Determine category
        risk_score = c_risk * 100
        category = "Low"
        if risk_score > 70: category = "High"
        elif risk_score > 30: category = "Moderate"
        
        # Store in DB
        db.add_history("Quantum-Classical", risk_score, category, user_input, user_id=session.get('user_id'), summary=body_impact)
        
        # Generate PDF Report (now includes detailed analysis)
        report_filename, _ = pdf.generate_report(user_input, risk_score, "Quantum-Clinical Hybrid", explanation=explanation)
        
        return jsonify({
            "status": "success",
            "quantum_result": "Diabetic (VQC)" if q_label == 1 else "Not Diabetic (VQC)",
            "classical_risk": f"{risk_score:.1f}%",
            "category": category,
            "explanation": explanation,
            "analysis": analysis,
            "body_impact_summary": body_impact,
            "report_url": f"/static/reports/{report_filename}"
        })
    except Exception as e:
        print(f"PREDICT ERROR: {e}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/upload_report', methods=['POST'])
@login_required
def upload_report():
    try:
        if 'report' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400
        
        file = request.files['report']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process with OCR
        features, full_text = ocr.extract_features(filepath)
        
        # Analyze with Gemini (passes filepath for vision fallback if OCR fails)
        lang = request.form.get('language', 'English')
        summary, primary_disease, medicines, risk_level = ocr.generate_summary(full_text, filepath, language=lang)
        
        # Store in History for Analytics Tracking
        risk_mapping = {"High": 85.0, "Moderate": 50.0, "Low": 15.0}
        num_risk = risk_mapping.get(risk_level, 30.0) # Default to 30% if unknown
        db.add_history(f"Lab Analysis: {primary_disease}", num_risk, risk_level, features, user_id=session.get('user_id'), summary=summary)
        
        return jsonify({
            "success": True,
            "features": features,
            "full_text": full_text,
            "summary": summary,
            "primary_disease": primary_disease,
            "suggested_medicines": medicines,
            "risk_level": risk_level
        })
    except Exception as e:
        print(f"UPLOAD ERROR: {e}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    print("CHAT REQUEST RECEIVED")
    payload = request.json
    user_message = payload.get('message')
    language = payload.get('language', 'English')
    
    # Fetch user history for context
    user_id = session.get('user_id')
    history = db.get_history(limit=3, user_id=user_id)
    history_str = ""
    for entry in history:
        history_str += f"- {entry.timestamp.strftime('%Y-%m-%d')}: {entry.result_category} Risk ({entry.risk_percentage}%)\n"
    
    # Inject language instruction
    lang_instruction = f"IMPORTANT: Please respond entirely in {language}."
    contextualized_message = f"{lang_instruction}\n\n{user_message}"
    
    response = bot.get_response(contextualized_message, patient_context=history_str)
    return jsonify({"response": response})

@app.route("/history")
@login_required
def history():
    user_id = session.get('user_id')
    history_data = db.get_history(limit=10, user_id=user_id)
    return jsonify([{
        "date": h.timestamp.strftime("%Y-%m-%d"),
        "risk": h.risk_percentage,
        "category": h.result_category
    } for h in history_data])

@app.route("/profile/info")
@login_required
def profile_info():
    user_id = session.get('user_id')
    # Logic to fetch user details would go here
    # For now, return session name
    return jsonify({
        "username": session.get('username'),
        "id": user_id,
        "is_active": True
    })

# --- Phase 2: Health Management Routes ---

@app.route("/doctors", methods=["GET"])
@login_required
def get_doctors():
    area = request.args.get("area", "").strip()
    # Provide a default 'Nearby' search if no area is specified
    is_default_search = False
    if not area:
        area = "Main City"
        is_default_search = True
    
    doctors = db.get_doctors_by_area(area)
    
    # Generate dynamic mock hospitals/doctors if the search doesn't match the hardcoded seeds
    if not doctors and area:
        import random
        specialties = ["Endocrinologist", "Diabetes Specialist", "Nutritionist", "General Physician", "Cardiologist"]
        hospitals = ["Apollo Clinics", "Care Hospitals", "KIMS", "Max Super Speciality", "Fortis Hospital", "City Care Clinic"]
        names = ["Dr. Rao", "Dr. Gupta", "Dr. Patel", "Dr. Lee", "Dr. Sharma", "Dr. Singh"]
        
        mock_doctors = []
        # Generate 3-5 random doctors for the requested area/pincode
        for i in range(random.randint(3, 5)):
            doctor_name = random.choice(names)
            specialty = random.choice(specialties)
            hospital = random.choice(hospitals)
            
            mock_doctors.append({
                "id": random.randint(1000, 9999),
                "name": doctor_name,
                "specialty": f"{specialty} at {hospital}",
                "area": area,
                "slots": "10:00 AM, 12:30 PM, 04:00 PM"
            })
        return jsonify(mock_doctors)

    return jsonify([{
        "id": d.id, 
        "name": d.name, 
        "specialty": d.specialty, 
        "area": d.area, 
        "slots": d.available_slots
    } for d in doctors])

@app.route("/update_profile", methods=["POST"])
@login_required
def update_profile():
    user_id = session.get('user_id')
    age = request.form.get('age')
    email = request.form.get('email')
    phone = request.form.get('phone')
    
    # Save the photo if uploaded
    photo_url = None
    if 'photo' in request.files:
        photo = request.files['photo']
        if photo.filename != '':
            filename = secure_filename(photo.filename)
            # Create a unique filename with user_id
            filename = f"user_{user_id}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(filepath)
            photo_url = f"/static/uploads/{filename}"
            session['profile_photo'] = photo_url
            
    # Typically we'd save age/email to Database here. We'll store it in session for now
    if age: session['user_age'] = age
    if email: session['user_email'] = email
    
    # Actually save phone to the Database to ensure Twilio works
    if phone or email:
        session_db = db.Session()
        user = session_db.query(User).filter_by(id=user_id).first()
        if user:
            if phone:
                user.phone_number = phone
                session['user_phone'] = phone
            if email:
                user.email = email
            session_db.commit()
        session_db.close()
    
    return jsonify({
        "success": True, 
        "message": "Profile updated successfully!",
        "photo_url": photo_url,
        "age": age,
        "email": email,
        "phone": phone
    })

@app.route("/book_appointment", methods=["POST"])
def book_appointment():
    data = request.json
    db.add_appointment(data['doctor_id'], "Guest User", data['date'], data['time'])
    return jsonify({"status": "success", "message": "Appointment booked successfully!"})

@app.route("/medicine", methods=["GET", "POST"])
def manage_medicine():
    if request.method == "POST":
        data = request.json
        if not data: return jsonify({"error": "No data received"})
        db.add_medication(data['name'], data['dosage'], data['frequency'], data['time'])
        return jsonify({"status": "success"})
    return jsonify({"status": "success", "medications": []})

@app.route("/set_reminder", methods=["POST"])
def set_reminder():
    return jsonify({"status": "success", "message": "Monthly reminder set!"})

if __name__ == "__main__":
    initialize_models()
    app.run(debug=True)