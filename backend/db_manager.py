from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    email = Column(String(100), unique=True)
    phone_number = Column(String(20))
    full_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class PredictionHistory(Base):
    __tablename__ = 'prediction_history'
    
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    model_type = Column(String(50)) # 'Quantum' or 'Classical'
    risk_percentage = Column(Float)
    result_category = Column(String(50)) # 'Low', 'Moderate', 'High'
    user_id = Column(Integer, ForeignKey('users.id'))
    features_json = Column(String(1000))
    summary = Column(String(500)) # Store AI insights / Body impact summary
    
class Doctor(Base):
    __tablename__ = 'doctors'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True)
    password_hash = Column(String(128))
    name = Column(String(100))
    specialty = Column(String(100))
    area = Column(String(100))
    pincode = Column(String(10))
    available_slots = Column(String(200)) # e.g., "10:00 AM, 02:00 PM"
    is_approved = Column(Integer, default=0)

class Appointment(Base):
    __tablename__ = 'appointments'
    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey('doctors.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    user_name = Column(String(100))
    appointment_date = Column(String(50))
    appointment_time = Column(String(20))

class MedicationReminder(Base):
    __tablename__ = 'medications'
    id = Column(Integer, primary_key=True)
    med_name = Column(String(100))
    dosage = Column(String(50))
    frequency = Column(String(50)) # e.g., "Daily", "Twice a day"
    reminder_time = Column(String(20))
    user_id = Column(Integer, ForeignKey('users.id'))
    is_active = Column(Integer, default=1)

class MonthlyReminder(Base):
    __tablename__ = 'reminders'
    id = Column(Integer, primary_key=True)
    rem_type = Column(String(50)) # "Checkup", "Activity"
    message = Column(String(200))
    next_due_date = Column(DateTime)
    status = Column(String(20)) # "Pending", "Completed"

class DatabaseManager:
    def __init__(self, db_url='sqlite:///diabetes_platform.db'):
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self._seed_doctors()

    def _seed_doctors(self):
        """Seed initial doctor data for the demo."""
        session = self.Session()
        if session.query(Doctor).count() == 0:
            pw_hash = generate_password_hash("doctor123")
            doctors = [
                Doctor(username="drsmith", password_hash=pw_hash, name="Dr. Smith", specialty="Endocrinologist", area="Downtown", pincode="500001", available_slots="10:00 AM, 11:30 AM, 03:00 PM"),
                Doctor(username="drreddy", password_hash=pw_hash, name="Dr. Reddy", specialty="Diabetes Specialist", area="Banjara Hills", pincode="500034", available_slots="09:00 AM, 12:00 PM, 04:30 PM"),
                Doctor(username="drsharma", password_hash=pw_hash, name="Dr. Sharma", specialty="Nutritionist", area="Hitech City", pincode="500081", available_slots="11:00 AM, 01:00 PM, 02:00 PM")
            ]
            session.add_all(doctors)
            session.commit()
        session.close()

    def add_history(self, model_type, risk_perc, category, features, user_id=None, summary=None):
        session = self.Session()
        new_entry = PredictionHistory(
            model_type=model_type,
            risk_percentage=risk_perc,
            result_category=category,
            features_json=str(features),
            user_id=user_id,
            summary=summary
        )
        session.add(new_entry)
        session.commit()
        session.close()

    def create_user(self, username, password, email=None, full_name=None, phone_number=None):
        session = self.Session()
        if not username or not password:
            session.close()
            return False, "Username and password are required"
            
        if session.query(User).filter_by(username=username).first():
            session.close()
            return False, "Username already exists"
            
        if email and session.query(User).filter_by(email=email).first():
            session.close()
            return False, "Email already registered"
        
        try:
            hashed_pw = generate_password_hash(password)
            new_user = User(username=username, password_hash=hashed_pw, email=email, full_name=full_name, phone_number=phone_number)
            session.add(new_user)
            session.commit()
            user_id = new_user.id
            session.close()
            return True, user_id
        except Exception as e:
            session.rollback()
            session.close()
            return False, f"Database error: {str(e)}"

    def verify_user(self, username, password):
        session = self.Session()
        user = session.query(User).filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            res = (True, user.id)
        else:
            res = (False, None)
        session.close()
        return res

    def verify_doctor(self, username, password):
        session = self.Session()
        doctor = session.query(Doctor).filter_by(username=username).first()
        if doctor and check_password_hash(doctor.password_hash, password):
            if doctor.is_approved == 1:
                res = (True, doctor.id, "Success")
            else:
                res = (False, None, "Your account is pending admin approval.")
        else:
            res = (False, None, "Invalid credentials")
        session.close()
        return res

    def create_doctor_request(self, username, password, name, specialty, area, pincode, slots="10:00 AM, 04:00 PM"):
        session = self.Session()
        if session.query(Doctor).filter_by(username=username).first():
            session.close()
            return False, "Username already exists"
        try:
            hashed_pw = generate_password_hash(password)
            new_doc = Doctor(
                username=username, password_hash=hashed_pw, name=name, 
                specialty=specialty, area=area, pincode=pincode, 
                available_slots=slots, is_approved=0
            )
            session.add(new_doc)
            session.commit()
            session.close()
            return True, "Request submitted successfully. Waiting for Admin approval."
        except Exception as e:
            session.rollback()
            session.close()
            return False, f"Database error: {str(e)}"

    def get_pending_doctors(self):
        session = self.Session()
        doctors = session.query(Doctor).filter_by(is_approved=0).all()
        session.close()
        return doctors

    def approve_doctor(self, doctor_id):
        session = self.Session()
        doctor = session.query(Doctor).filter_by(id=doctor_id).first()
        if doctor:
            doctor.is_approved = 1
            session.commit()
            res = True
        else:
            res = False
        session.close()
        return res

    def get_all_doctors(self):
        session = self.Session()
        doctors = session.query(Doctor).all()
        session.close()
        return doctors

    def delete_doctor(self, doctor_id):
        session = self.Session()
        try:
            # Delete associated appointments
            session.query(Appointment).filter_by(doctor_id=doctor_id).delete()
            # Delete doctor
            session.query(Doctor).filter_by(id=doctor_id).delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            return False
        finally:
            session.close()

    def get_all_users(self):
        session = self.Session()
        users = session.query(User).all()
        session.close()
        return users

    def delete_user(self, user_id):
        session = self.Session()
        try:
            # Delete associated data
            session.query(PredictionHistory).filter_by(user_id=user_id).delete()
            session.query(Appointment).filter_by(user_id=user_id).delete()
            session.query(MedicationReminder).filter_by(user_id=user_id).delete()
            # Delete user
            session.query(User).filter_by(id=user_id).delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            return False
        finally:
            session.close()

    def get_all_patient_history(self):
        session = self.Session()
        history = session.query(PredictionHistory).order_by(PredictionHistory.timestamp.desc()).all()
        # attach usernames 
        results = []
        for h in history:
            user = session.query(User).filter_by(id=h.user_id).first()
            results.append({
                "patient_name": user.full_name if (user and user.full_name) else (user.username if user else "Unknown"),
                "date": h.timestamp.strftime("%Y-%m-%d"),
                "risk": h.risk_percentage,
                "category": h.result_category
            })
        session.close()
        return results

    def get_doctors_by_area(self, area_or_pincode):
        session = self.Session()
        doctors = session.query(Doctor).filter(
            (Doctor.area.ilike(f'%{area_or_pincode}%')) | 
            (Doctor.pincode == area_or_pincode)
        ).all()
        session.close()
        return doctors

    def add_appointment(self, doctor_id, user_name, date, time, user_id=None):
        session = self.Session()
        apt = Appointment(doctor_id=doctor_id, user_name=user_name, appointment_date=date, appointment_time=time, user_id=user_id)
        session.add(apt)
        session.commit()
        session.close()

    def add_medication(self, name, dosage, frequency, time, user_id=None):
        session = self.Session()
        med = MedicationReminder(med_name=name, dosage=dosage, frequency=frequency, reminder_time=time, user_id=user_id)
        session.add(med)
        session.commit()
        session.close()

    def get_history(self, limit=10, user_id=None):
        session = self.Session()
        query = session.query(PredictionHistory)
        if user_id:
            query = query.filter_by(user_id=user_id)
        history = query.order_by(PredictionHistory.timestamp.desc()).limit(limit).all()
        session.close()
        return history

if __name__ == "__main__":
    db = DatabaseManager()
    print("Database and tables created.")
