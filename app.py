import uuid  # Add this import
from datetime import datetime
import json
import pickle
import pandas as pd
import numpy as np
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.feature_extraction.text import TfidfVectorizer
import mysql.connector
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
# Download NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
except:
    pass

app = Flask(__name__)
app.config.from_object(Config)

# Use mysqlconnector directly for MySQL 5.5
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://pregbot:pregbot123@localhost/pregbot_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 280,
    'pool_pre_ping': True
}

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models for MySQL 5.5 
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    user_type = db.Column(db.Enum('patient', 'doctor'), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    profile = db.relationship('PatientProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    symptoms = db.relationship('SymptomLog', backref='patient', lazy=True, cascade='all, delete-orphan')
    risks = db.relationship('RiskPrediction', backref='patient', lazy=True, cascade='all, delete-orphan')
    chats = db.relationship('ChatHistory', backref='user', lazy=True, cascade='all, delete-orphan')
    mental_health_logs = db.relationship('MentalHealthLog', backref='patient', lazy=True, cascade='all, delete-orphan')
    doctor_alerts = db.relationship('DoctorAlert', foreign_keys='DoctorAlert.patient_id', backref='alert_patient', lazy=True)
    reviewed_alerts = db.relationship('DoctorAlert', foreign_keys='DoctorAlert.reviewed_by', backref='reviewer', lazy=True)

class PatientProfile(db.Model):
    __tablename__ = 'patient_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    age = db.Column(db.Integer)
    trimester = db.Column(db.Integer)
    blood_pressure_category = db.Column(db.String(20))
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    medical_history = db.Column(db.Text)
    allergies = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SymptomLog(db.Model):
    __tablename__ = 'symptoms_log'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    symptom_name = db.Column(db.String(100))
    severity = db.Column(db.String(20))
    duration_days = db.Column(db.Integer)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RiskPrediction(db.Model):
    __tablename__ = 'risk_predictions'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    prediction = db.Column(db.String(20))
    confidence = db.Column(db.Float)
    
    # Factor columns (for MySQL 5.5 compatibility)
    factors_age = db.Column(db.Integer)
    factors_trimester = db.Column(db.Integer)
    factors_bp_category = db.Column(db.String(20))
    factors_symptom_severity = db.Column(db.String(20))
    factors_symptom_name = db.Column(db.String(100))
    
    explanation = db.Column(db.Text)
    is_emergency = db.Column(db.Boolean, default=False)
    doctor_reviewed = db.Column(db.Boolean, default=False)
    doctor_feedback = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    alerts = db.relationship('DoctorAlert', backref='risk_prediction', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<RiskPrediction {self.id}: {self.prediction} risk for patient {self.patient_id}>'

class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    intent = db.Column(db.String(50), default='general')
    entities = db.Column(db.Text)  # Store as JSON string
    confidence = db.Column(db.Float, default=0.0)
    session_id = db.Column(db.String(100))
    chat_metadata = db.Column(db.Text)  # FIXED: Changed from 'metadata' to 'chat_metadata'
    sentiment = db.Column(db.String(20), default='neutral')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MentalHealthLog(db.Model):
    __tablename__ = 'mental_health_log'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    mood = db.Column(db.String(50), default='Not specified')
    stress_level = db.Column(db.Integer, default=0)
    anxiety_level = db.Column(db.Integer, default=0)
    sleep_hours = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, default='')
    sentiment = db.Column(db.String(20), default='neutral')
    recommendation = db.Column(db.Text, default='No recommendation available')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DoctorAlert(db.Model):
    __tablename__ = 'doctor_alerts'
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    prediction_id = db.Column(db.Integer, db.ForeignKey('risk_predictions.id', ondelete='CASCADE'))
    alert_type = db.Column(db.String(50))
    priority = db.Column(db.String(20))
    status = db.Column(db.Enum('pending', 'reviewed', 'resolved'), default='pending')
    doctor_notes = db.Column(db.Text)
    alert_metadata = db.Column(db.Text)  # FIXED: Changed from 'metadata' to 'alert_metadata'
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    reviewed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Recommendation(db.Model):
    __tablename__ = 'recommendations'
    id = db.Column(db.Integer, primary_key=True)
    trimester = db.Column(db.Integer)
    category = db.Column(db.String(50))
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    for_condition = db.Column(db.String(100))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# NLP Chatbot Engine
class PregBotChatbot:
    def __init__(self):
        self.intents = {
            'diet': ['food', 'eat', 'nutrition', 'diet', 'meal', 'vitamin'],
            'symptoms': ['pain', 'hurt', 'symptom', 'feel', 'ache', 'discomfort'],
            'exercise': ['exercise', 'workout', 'yoga', 'walk', 'activity'],
            'mental_health': ['stress', 'anxiety', 'depress', 'sad', 'worry', 'mental'],
            'medication': ['medicine', 'pill', 'drug', 'prescription', 'medication'],
            'general': ['hello', 'hi', 'help', 'thanks', 'thank you']
        }
        
        self.responses = {
            'diet': "Based on your trimester, I recommend increasing your intake of leafy greens, lean proteins, and whole grains. Remember to stay hydrated and take prenatal vitamins.",
            'symptoms': "I can help you assess your symptoms. Please describe what you're experiencing in detail, including severity and duration.",
            'exercise': "For your stage of pregnancy, I recommend light exercises like walking, prenatal yoga, or swimming for 30 minutes daily.",
            'mental_health': "Pregnancy can be emotionally challenging. Try deep breathing exercises, talk to loved ones, and consider keeping a journal.",
            'medication': "Always consult your doctor before taking any medication during pregnancy. Some medications may not be safe for the baby.",
            'general': "Hello! I'm PregBot, your pregnancy assistant. How can I help you today?"
        }
        
    def classify_intent(self, message):
        message = message.lower()
        for intent, keywords in self.intents.items():
            for keyword in keywords:
                if keyword in message:
                    return intent
        return 'general'
    
    def get_response(self, intent):
        return self.responses.get(intent, "I'm here to help with your pregnancy questions. Could you please rephrase your question?")

chatbot = PregBotChatbot()

# ML Models for Risk Prediction
# Add to imports
import uuid
from sklearn.ensemble import RandomForestClassifier
import pandas as pd

# Initialize risk predictor globally (outside functions)
class RiskPredictor:
    def __init__(self):
        # Initialize with minimal data first
        self.initialize_model()
    
    def initialize_model(self):
        try:
            # Enhanced training data with more high-risk cases
            self.data = pd.DataFrame({
                'age': [25, 30, 28, 32, 35, 27, 29, 31, 26, 33, 22, 36, 24, 38, 21, 34, 37, 23, 39, 40],
                'trimester': [1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2],
                'bp_category': ['normal', 'high', 'normal', 'low', 'high', 'normal', 'low', 'normal', 'high', 'normal', 
                               'high', 'high', 'normal', 'high', 'low', 'high', 'high', 'normal', 'high', 'high'],
                'symptom_severity': ['mild', 'severe', 'moderate', 'mild', 'severe', 'moderate', 'mild', 'severe', 'moderate', 'mild',
                                    'severe', 'severe', 'moderate', 'severe', 'mild', 'severe', 'severe', 'moderate', 'severe', 'severe'],
                'risk_level': ['low', 'high', 'medium', 'low', 'high', 'medium', 'low', 'high', 'medium', 'low',
                              'high', 'high', 'medium', 'high', 'low', 'high', 'high', 'medium', 'high', 'high']
            })
            
            # Encode categorical variables
            self.bp_mapping = {'low': 0, 'normal': 1, 'high': 2}
            self.severity_mapping = {'mild': 0, 'moderate': 1, 'severe': 2}
            self.risk_mapping = {'low': 0, 'medium': 1, 'high': 2}
            
            # Prepare features
            X = self.prepare_features(self.data)
            y = self.data['risk_level'].map(self.risk_mapping)
            
            # Train model with better parameters
            self.model = RandomForestClassifier(
                n_estimators=100,  # Reduced for faster training
                max_depth=8,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                class_weight='balanced'
            )
            self.model.fit(X, y)
            
            print("✅ Risk prediction model trained successfully")
            
        except Exception as e:
            print(f"❌ Error training risk model: {e}")
            self.model = None
    
    def prepare_features(self, data):
        X = data.copy()
        X['bp_category'] = X['bp_category'].map(self.bp_mapping)
        X['symptom_severity'] = X['symptom_severity'].map(self.severity_mapping)
        return X[['age', 'trimester', 'bp_category', 'symptom_severity']]
    
    def predict_risk(self, age, trimester, bp_category, symptom_severity, symptom_name=None):
        # Check for emergency symptoms first (rule-based)
        emergency_risk = self.check_emergency_risk(symptom_name, symptom_severity, bp_category, trimester)
        if emergency_risk:
            # Ensure emergency risk result has factors
            if 'factors' not in emergency_risk:
                emergency_risk['factors'] = {
                    'age': age,
                    'trimester': trimester,
                    'blood_pressure': bp_category,
                    'symptom_severity': symptom_severity,
                    'symptom_name': symptom_name
                }
            return emergency_risk
        
        # Create feature vector
        features = pd.DataFrame([{
            'age': age,
            'trimester': trimester,
            'bp_category': self.bp_mapping.get(bp_category.lower(), 1),
            'symptom_severity': self.severity_mapping.get(symptom_severity.lower(), 0)
        }])
        
        # Make prediction with both models
        try:
            prediction1 = self.model.predict(features)[0]
            prediction2 = self.high_risk_model.predict(features)[0]
            
            # Take the higher risk prediction (more conservative)
            prediction = max(prediction1, prediction2)
            
            # Get probabilities
            probability = self.high_risk_model.predict_proba(features)[0]
            
        except Exception as e:
            # Fallback to rule-based if ML fails
            app.logger.error(f"ML prediction error: {e}")
            return self.rule_based_risk(age, trimester, bp_category, symptom_severity, symptom_name)
        
        # Map back to string labels
        risk_levels = ['low', 'medium', 'high']
        risk_label = risk_levels[prediction]
        
        # Adjust based on specific conditions
        risk_label = self.adjust_risk_based_on_conditions(
            risk_label, symptom_name, symptom_severity, bp_category, trimester, age
        )
        
        # Generate explanation
        explanation = self.generate_explanation(
            age, trimester, bp_category, symptom_severity, symptom_name, risk_label
        )
        
        return {
            'risk_level': risk_label,
            'confidence': float(max(probability)),
            'probabilities': {
                'low': float(probability[0]),
                'medium': float(probability[1]),
                'high': float(probability[2])
            },
            'explanation': explanation,
            'factors': {
                'age': age,
                'trimester': trimester,
                'blood_pressure': bp_category,
                'symptom_severity': symptom_severity,
                'symptom_name': symptom_name
            },
            'is_emergency': risk_label == 'high' and self.is_emergency_case(symptom_name, symptom_severity)
        }

    def check_emergency_risk(self, symptom_name, severity, bp_category, trimester):
        """Check for emergency conditions that always indicate high risk"""
        if not symptom_name:
            return None
            
        symptom_lower = symptom_name.lower()
        severity_lower = severity.lower()
        bp_lower = bp_category.lower()
        
        # Emergency conditions as a list of dictionaries
        emergency_conditions = [
            {
                'symptoms': ['bleeding'],
                'severity': 'severe',
                'risk': 'high',
                'message': 'Severe bleeding requires immediate medical attention.'
            },
            {
                'symptoms': ['abdominal pain', 'stomach pain'],
                'severity': 'severe',
                'risk': 'high',
                'message': 'Severe abdominal pain could indicate serious complications.'
            },
            {
                'symptoms': ['no fetal movement', 'decreased movement'],
                'severity': 'any',
                'risk': 'high',
                'message': 'Decreased fetal movement requires immediate evaluation.'
            },
            {
                'symptoms': ['contractions'],
                'severity': 'severe',
                'risk': 'high' if trimester < 3 else 'medium',
                'message': 'Severe contractions before term could indicate preterm labor.'
            },
            {
                'symptoms': ['ruptured membranes', 'water breaking'],
                'severity': 'any',
                'risk': 'high',
                'message': 'Ruptured membranes require immediate hospital evaluation.'
            },
            {
                'symptoms': ['seizures', 'convulsions'],
                'severity': 'any',
                'risk': 'high',
                'message': 'Seizures during pregnancy are a medical emergency.'
            },
            {
                'symptoms': ['chest pain'],
                'severity': 'severe',
                'risk': 'high',
                'message': 'Severe chest pain requires emergency evaluation.'
            },
            {
                'symptoms': ['difficulty breathing', 'shortness of breath'],
                'severity': 'severe',
                'risk': 'high',
                'message': 'Severe breathing difficulty is a medical emergency.'
            }
        ]
        
        # Check each emergency condition
        for condition in emergency_conditions:
            for symptom_keyword in condition['symptoms']:
                if symptom_keyword in symptom_lower:
                    if condition['severity'] == 'any' or condition['severity'] in severity_lower:
                        return {
                            'risk_level': condition['risk'],
                            'confidence': 0.95,
                            'explanation': condition['message'],
                            'is_emergency': True,
                            'factors': {
                                'age': 0,  # Will be filled by caller
                                'trimester': trimester,
                                'blood_pressure': bp_category,
                                'symptom_severity': severity,
                                'symptom_name': symptom_name
                            }
                        }
        
        # Special case: High BP with headache/vision changes
        if bp_lower == 'high' and severity_lower == 'severe':
            if any(symptom in symptom_lower for symptom in ['headache', 'vision', 'blurred', 'seeing spots']):
                return {
                    'risk_level': 'high',
                    'confidence': 0.90,
                    'explanation': 'High blood pressure with severe neurological symptoms suggests preeclampsia - a medical emergency.',
                    'is_emergency': True,
                    'factors': {
                        'age': 0,  # Will be filled by caller
                        'trimester': trimester,
                        'blood_pressure': bp_category,
                        'symptom_severity': severity,
                        'symptom_name': symptom_name
                    }
                }
            
            if 'swelling' in symptom_lower and severity_lower == 'severe':
                return {
                    'risk_level': 'high',
                    'confidence': 0.85,
                    'explanation': 'Severe swelling with high blood pressure requires immediate evaluation for preeclampsia.',
                    'is_emergency': True,
                    'factors': {
                        'age': 0,  # Will be filled by caller
                        'trimester': trimester,
                        'blood_pressure': bp_category,
                        'symptom_severity': severity,
                        'symptom_name': symptom_name
                    }
                }
        
        return None

    def rule_based_risk(self, age, trimester, bp_category, symptom_severity, symptom_name):
        """Fallback rule-based risk assessment"""
        symptom_lower = symptom_name.lower() if symptom_name else ""
        severity_lower = symptom_severity.lower()
        bp_lower = bp_category.lower()
        
        # Default to medium risk
        risk_label = 'medium'
        confidence = 0.7
        
        # High risk conditions
        high_risk_conditions = [
            severity_lower == 'severe' and bp_lower == 'high',
            severity_lower == 'severe' and trimester == 3,
            'bleeding' in symptom_lower and severity_lower in ['moderate', 'severe'],
            'abdominal' in symptom_lower and 'pain' in symptom_lower and severity_lower == 'severe',
            'no movement' in symptom_lower or 'decreased movement' in symptom_lower,
            age > 35 and severity_lower == 'severe'
        ]
        
        # Low risk conditions
        low_risk_conditions = [
            severity_lower == 'mild' and bp_lower == 'normal',
            'nausea' in symptom_lower and severity_lower == 'mild',
            'back pain' in symptom_lower and severity_lower == 'mild',
            trimester == 2 and severity_lower == 'mild'
        ]
        
        if any(high_risk_conditions):
            risk_label = 'high'
            confidence = 0.85
        elif any(low_risk_conditions):
            risk_label = 'low'
            confidence = 0.8
        
        explanation = self.generate_explanation(
            age, trimester, bp_category, symptom_severity, symptom_name, risk_label
        )
        
        return {
            'risk_level': risk_label,
            'confidence': confidence,
            'explanation': explanation,
            'factors': {
                'age': age,
                'trimester': trimester,
                'blood_pressure': bp_category,
                'symptom_severity': symptom_severity,
                'symptom_name': symptom_name
            },
            'is_emergency': risk_label == 'high' and self.is_emergency_case(symptom_name, symptom_severity)
        }    
    def adjust_risk(self, current_risk, symptom_name, severity, bp_category, trimester, age):
        """Adjust risk based on medical knowledge"""
        if not symptom_name:
            return current_risk
            
        symptom_lower = symptom_name.lower()
        severity_lower = severity.lower()
        bp_lower = bp_category.lower()
        
        # Auto-upgrade to high risk
        high_risk_conditions = [
            trimester == 3 and severity_lower == 'severe' and any(s in symptom_lower for s in ['pain', 'bleeding', 'headache']),
            bp_lower == 'high' and severity_lower in ['moderate', 'severe'],
            age > 35 and severity_lower == 'severe',
            'bleeding' in symptom_lower and severity_lower in ['moderate', 'severe'],
            'abdominal' in symptom_lower and 'pain' in symptom_lower and severity_lower == 'severe',
            'vision' in symptom_lower and 'change' in symptom_lower,
            'decreased' in symptom_lower and 'movement' in symptom_lower
        ]
        
        if any(high_risk_conditions):
            return 'high'
        
        # Upgrade to medium risk
        medium_risk_conditions = [
            trimester == 2 and severity_lower == 'moderate',
            trimester == 1 and severity_lower == 'severe' and 'nausea' not in symptom_lower,
            bp_lower == 'high' and severity_lower == 'mild',
            age > 35 and severity_lower == 'moderate',
            'fever' in symptom_lower and severity_lower == 'moderate'
        ]
        
        if any(medium_risk_conditions) and current_risk == 'low':
            return 'medium'
        
        return current_risk
    
    def rule_based_risk(self, age, trimester, bp_category, symptom_severity, symptom_name):
        """Fallback rule-based risk assessment"""
        symptom_lower = symptom_name.lower() if symptom_name else ""
        severity_lower = symptom_severity.lower()
        bp_lower = bp_category.lower()
        
        # Start with medium risk
        risk_label = 'medium'
        confidence = 0.7
        
        # Determine risk based on rules
        if severity_lower == 'mild' and bp_lower == 'normal':
            if 'nausea' in symptom_lower or 'back pain' in symptom_lower or 'headache' in symptom_lower:
                risk_label = 'low'
                confidence = 0.8
        
        elif severity_lower == 'severe':
            if bp_lower == 'high' or trimester == 3 or 'bleeding' in symptom_lower:
                risk_label = 'high'
                confidence = 0.85
            else:
                risk_label = 'medium'
                confidence = 0.75
        
        elif severity_lower == 'moderate':
            if bp_lower == 'high' or age > 35:
                risk_label = 'medium'
                confidence = 0.7
            else:
                risk_label = 'low'
                confidence = 0.65
        
        # Generate explanation
        explanation = self.generate_explanation(age, trimester, bp_category, symptom_severity, symptom_name, risk_label)
        
        return {
            'risk_level': risk_label,
            'confidence': confidence,
            'explanation': explanation,
            'factors': {
                'age': age,
                'trimester': trimester,
                'blood_pressure': bp_category,
                'symptom_severity': symptom_severity,
                'symptom_name': symptom_name
            },
            'is_emergency': risk_label == 'high' and self.is_emergency_case(symptom_name, symptom_severity)
        }
    
    def generate_explanation(self, age, trimester, bp_category, symptom_severity, symptom_name, risk_level):
        """Generate explanation for risk assessment"""
        import random
        
        explanations = {
            'high': [
                f"🚨 HIGH RISK ALERT: {symptom_severity} {symptom_name} requires immediate medical attention.",
                f"⚠️ EMERGENCY: Based on your symptoms ({symptom_name}), age ({age}), and trimester ({trimester}), urgent doctor consultation is needed.",
                f"🆘 CRITICAL: {symptom_name} at {symptom_severity} severity indicates possible complications. Contact healthcare provider immediately."
            ],
            'medium': [
                f"⚠️ MEDIUM RISK: {symptom_severity} {symptom_name} should be evaluated by a doctor within 24-48 hours.",
                f"📋 RECOMMENDED: Schedule an appointment to discuss your {symptom_name} symptoms.",
                f"👩‍⚕️ CONSULT DOCTOR: {symptom_name} at {symptom_severity} level needs medical evaluation."
            ],
            'low': [
                f"✅ LOW RISK: {symptom_severity} {symptom_name} appears normal for pregnancy.",
                f"👍 SAFE: Symptoms are common in trimester {trimester}. Monitor for changes.",
                f"💚 NORMAL: {symptom_name} at {symptom_severity} level is expected. Continue regular care."
            ]
        }
        
        base_exp = random.choice(explanations.get(risk_level, ['Assessment complete.']))
        
        # Add specific advice
        if risk_level == 'high':
            if bp_category.lower() == 'high':
                base_exp += " High blood pressure with these symptoms could indicate preeclampsia."
            if 'bleeding' in (symptom_name or '').lower():
                base_exp += " Vaginal bleeding always requires immediate evaluation."
        
        return base_exp
    
    def is_emergency_case(self, symptom_name, severity):
        """Check if this is an emergency case"""
        if not symptom_name:
            return False
            
        symptom_lower = symptom_name.lower()
        severity_lower = severity.lower()
        
        emergency_keywords = [
            'severe bleeding',
            'severe abdominal pain',
            'no fetal movement',
            'seizures',
            'chest pain',
            'difficulty breathing',
            'ruptured membranes'
        ]
        
        for emergency in emergency_keywords:
            if emergency in f"{severity_lower} {symptom_lower}":
                return True
        
        return False

# Initialize risk predictor globally
try:
    risk_predictor = RiskPredictor()
    print("✅ Risk predictor initialized successfully")
except Exception as e:
    print(f"❌ Error initializing risk predictor: {e}")
    risk_predictor = None

def check_emergency_risk(self, symptom_name, severity, bp_category, trimester):
    """Check for emergency conditions that always indicate high risk"""
    if not symptom_name:
        return None
        
    symptom_lower = symptom_name.lower()
    severity_lower = severity.lower()
    bp_lower = bp_category.lower()
    
    # Emergency conditions as a list of dictionaries
    emergency_conditions = [
        {
            'symptoms': ['bleeding'],
            'severity': 'severe',
            'risk': 'high',
            'message': 'Severe bleeding requires immediate medical attention.'
        },
        {
            'symptoms': ['abdominal pain', 'stomach pain'],
            'severity': 'severe',
            'risk': 'high',
            'message': 'Severe abdominal pain could indicate serious complications.'
        },
        {
            'symptoms': ['no fetal movement', 'decreased movement'],
            'severity': 'any',
            'risk': 'high',
            'message': 'Decreased fetal movement requires immediate evaluation.'
        },
        {
            'symptoms': ['contractions'],
            'severity': 'severe',
            'risk': 'high' if trimester < 3 else 'medium',
            'message': 'Severe contractions before term could indicate preterm labor.'
        },
        {
            'symptoms': ['ruptured membranes', 'water breaking'],
            'severity': 'any',
            'risk': 'high',
            'message': 'Ruptured membranes require immediate hospital evaluation.'
        },
        {
            'symptoms': ['seizures', 'convulsions'],
            'severity': 'any',
            'risk': 'high',
            'message': 'Seizures during pregnancy are a medical emergency.'
        },
        {
            'symptoms': ['chest pain'],
            'severity': 'severe',
            'risk': 'high',
            'message': 'Severe chest pain requires emergency evaluation.'
        },
        {
            'symptoms': ['difficulty breathing', 'shortness of breath'],
            'severity': 'severe',
            'risk': 'high',
            'message': 'Severe breathing difficulty is a medical emergency.'
        }
    ]
    
    # Check each emergency condition
    for condition in emergency_conditions:
        for symptom_keyword in condition['symptoms']:
            if symptom_keyword in symptom_lower:
                if condition['severity'] == 'any' or condition['severity'] in severity_lower:
                    return {
                        'risk_level': condition['risk'],
                        'confidence': 0.95,
                        'explanation': condition['message'],
                        'is_emergency': True
                    }
    
    # Special case: High BP with headache/vision changes
    if bp_lower == 'high' and severity_lower == 'severe':
        if any(symptom in symptom_lower for symptom in ['headache', 'vision', 'blurred', 'seeing spots']):
            return {
                'risk_level': 'high',
                'confidence': 0.90,
                'explanation': 'High blood pressure with severe neurological symptoms suggests preeclampsia - a medical emergency.',
                'is_emergency': True
            }
        
        if 'swelling' in symptom_lower and severity_lower == 'severe':
            return {
                'risk_level': 'high',
                'confidence': 0.85,
                'explanation': 'Severe swelling with high blood pressure requires immediate evaluation for preeclampsia.',
                'is_emergency': True
            }
    
        return None
    
def adjust_risk_based_on_conditions(self, current_risk, symptom_name, severity, bp_category, trimester, age):
        """Adjust risk based on medical knowledge"""
        if not symptom_name:
            return current_risk
            
        symptom_lower = symptom_name.lower()
        severity_lower = severity.lower()
        bp_lower = bp_category.lower()
        
        # Auto-upgrade to high risk for certain combinations
        high_risk_conditions = [
            # Third trimester with severe symptoms
            (trimester == 3 and severity_lower == 'severe' and 
             any(s in symptom_lower for s in ['pain', 'bleeding', 'headache', 'swelling'])),
            
            # High BP with moderate+ symptoms
            (bp_lower == 'high' and severity_lower in ['moderate', 'severe']),
            
            # Age > 35 with severe symptoms
            (age > 35 and severity_lower == 'severe'),
            
            # Specific symptom combinations
            ('bleeding' in symptom_lower and severity_lower in ['moderate', 'severe']),
            ('abdominal' in symptom_lower and 'pain' in symptom_lower and severity_lower == 'severe'),
            ('vision' in symptom_lower and 'change' in symptom_lower),
            ('decreased' in symptom_lower and 'movement' in symptom_lower)
        ]
        
        if any(high_risk_conditions):
            return 'high'
        
        # Upgrade to medium risk
        medium_risk_conditions = [
            # Second trimester with moderate symptoms
            (trimester == 2 and severity_lower == 'moderate'),
            
            # First trimester with severe symptoms (except normal morning sickness)
            (trimester == 1 and severity_lower == 'severe' and 
             'nausea' not in symptom_lower and 'vomiting' not in symptom_lower),
            
            # High BP with mild symptoms
            (bp_lower == 'high' and severity_lower == 'mild'),
            
            # Age > 35 with moderate symptoms
            (age > 35 and severity_lower == 'moderate')
        ]
        
        if any(medium_risk_conditions) and current_risk == 'low':
            return 'medium'
        
        return current_risk
    
def generate_explanation(self, age, trimester, bp_category, symptom_severity, symptom_name, risk_level):
        """Generate detailed explanation for risk assessment"""
        
        explanations = {
            'high': [
                f"⚠️ HIGH RISK: {symptom_severity} {symptom_name} in trimester {trimester} with {bp_category} BP indicates urgent medical attention is needed.",
                f"🚨 EMERGENCY ALERT: Combination of factors (age {age}, trimester {trimester}, {bp_category} BP, {symptom_severity} symptoms) suggests immediate doctor consultation.",
                f"🆘 CRITICAL: {symptom_name} at {symptom_severity} severity requires emergency evaluation. Please contact healthcare provider immediately."
            ],
            'medium': [
                f"⚠️ MEDIUM RISK: {symptom_severity} {symptom_name} requires monitoring. Schedule appointment within 24-48 hours.",
                f"📋 MONITOR: {symptom_name} symptoms at {symptom_severity} level need medical evaluation soon.",
                f"👩‍⚕️ RECOMMENDED: Consult your doctor about {symptom_name}. Symptoms suggest need for professional assessment."
            ],
            'low': [
                f"✅ LOW RISK: {symptom_severity} {symptom_name} appears normal for pregnancy. Continue regular checkups.",
                f"👍 NORMAL: Symptoms are within expected range for trimester {trimester}. Monitor for changes.",
                f"💚 SAFE: {symptom_name} at {symptom_severity} level is common. Maintain healthy habits."
            ]
        }
        
        import random
        base_explanation = random.choice(explanations.get(risk_level, ['Risk assessment completed.']))
        
        # Add specific advice
        if risk_level == 'high':
            if bp_category.lower() == 'high' and 'headache' in (symptom_name or '').lower():
                base_explanation += " This could indicate preeclampsia - a serious pregnancy complication."
            elif 'bleeding' in (symptom_name or '').lower():
                base_explanation += " Vaginal bleeding in pregnancy always requires immediate evaluation."
            elif trimester == 3 and 'contraction' in (symptom_name or '').lower():
                base_explanation += " Regular contractions before 37 weeks could indicate preterm labor."
        
        elif risk_level == 'medium':
            if trimester == 1 and 'nausea' in (symptom_name or '').lower():
                base_explanation += " Severe morning sickness (hyperemesis) may need treatment."
            elif 'fever' in (symptom_name or '').lower():
                base_explanation += " Fever in pregnancy requires medical attention to rule out infection."
        
        return base_explanation
    
def is_emergency_case(self, symptom_name, severity):
        """Check if this is an emergency case that needs immediate attention"""
        if not symptom_name:
            return False
            
        symptom_lower = symptom_name.lower()
        severity_lower = severity.lower()
        
        emergency_symptoms = [
            'severe bleeding',
            'severe abdominal pain',
            'no fetal movement',
            'seizures',
            'chest pain',
            'difficulty breathing',
            'ruptured membranes'
        ]
        
        for emergency in emergency_symptoms:
            if emergency in f"{severity_lower} {symptom_lower}" or emergency in symptom_lower:
                return True
        
        return False

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        user_type = request.form['user_type']
        phone = request.form.get('phone', '')
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        hashed_password = generate_password_hash(password)
        new_user = User(
            email=email,
            password=hashed_password,
            full_name=full_name,
            user_type=user_type,
            phone=phone
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Create patient profile if user is patient
        if user_type == 'patient':
            profile = PatientProfile(user_id=new_user.id)
            db.session.add(profile)
            db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            
            if user.user_type == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.user_type == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    
    try:
        # Get user's recent data
        recent_symptoms = SymptomLog.query.filter_by(
            patient_id=current_user.id
        ).order_by(SymptomLog.created_at.desc()).limit(5).all()
        
        recent_risks = RiskPrediction.query.filter_by(
            patient_id=current_user.id
        ).order_by(RiskPrediction.created_at.desc()).limit(5).all()
        
        recent_chats = ChatHistory.query.filter_by(
            user_id=current_user.id
        ).order_by(ChatHistory.created_at.desc()).limit(10).all()
        
        # Get recommendations based on trimester
        profile = PatientProfile.query.filter_by(user_id=current_user.id).first()
        trimester = profile.trimester if profile else 1
        
        recommendations = Recommendation.query.filter_by(
            trimester=trimester
        ).limit(5).all()
        
        # Get mental health stats
        mental_health_logs = MentalHealthLog.query.filter_by(
            patient_id=current_user.id
        ).order_by(MentalHealthLog.created_at.desc()).limit(10).all()
        
        mental_health_stats = calculate_mental_health_stats(mental_health_logs)
        
        # Get today's date
        from datetime import date
        today = date.today()
        
        # Get chat statistics - FIXED SYNTAX
        chat_stats = {
            'total_chats': len(recent_chats),
            'today_chats': ChatHistory.query.filter(
                ChatHistory.user_id == current_user.id,
                db.func.date(ChatHistory.created_at) == today
            ).count(),
            'common_intents': get_common_intents(current_user.id)
        }
        
        # Generate recent activity feed
        recent_activity = generate_activity_feed(
            recent_symptoms, 
            recent_risks, 
            recent_chats,
            mental_health_logs
        )
        
        # Generate reminders
        reminders = generate_reminders(profile)
        
        return render_template('dashboard.html',
                             symptoms=recent_symptoms,
                             risks=recent_risks,
                             chats=recent_chats,
                             recommendations=recommendations,
                             profile=profile,
                             mental_health_stats=mental_health_stats,
                             chat_stats=chat_stats,
                             recent_activity=recent_activity,
                             reminders=reminders)
                             
    except Exception as e:
        app.logger.error(f"Error loading dashboard: {str(e)}")
        flash('Error loading dashboard. Please try again.', 'danger')
        return render_template('dashboard.html',
                             symptoms=[],
                             risks=[],
                             chats=[],
                             recommendations=[],
                             profile=None,
                             mental_health_stats={},
                             chat_stats={},
                             recent_activity=[],
                             reminders=[])
    
def calculate_mental_health_stats(logs):
    """Calculate mental health statistics"""
    if not logs:
        return {}
    
    stats = {
        'avg_mood': 0,
        'avg_stress': 0,
        'avg_anxiety': 0,
        'trend': 'stable'
    }
    
    # Calculate averages
    mood_scores = []
    stress_levels = []
    anxiety_levels = []
    
    for log in logs:
        if log.mood:
            # Convert mood to score
            mood_score = {
                'very happy': 5,
                'happy': 4,
                'neutral': 3,
                'sad': 2,
                'very sad': 1
            }.get(log.mood.lower(), 3)
            mood_scores.append(mood_score)
        
        if log.stress_level:
            stress_levels.append(log.stress_level)
        
        if log.anxiety_level:
            anxiety_levels.append(log.anxiety_level)
    
    if mood_scores:
        stats['avg_mood'] = sum(mood_scores) / len(mood_scores)
    
    if stress_levels:
        stats['avg_stress'] = sum(stress_levels) / len(stress_levels)
    
    if anxiety_levels:
        stats['avg_anxiety'] = sum(anxiety_levels) / len(anxiety_levels)
    
    # Determine trend (if we have enough data)
    if len(logs) >= 3:
        recent = logs[:3]
        previous = logs[3:6] if len(logs) >= 6 else logs[:3]
        
        recent_avg = sum(log.stress_level or 0 for log in recent) / 3
        previous_avg = sum(log.stress_level or 0 for log in previous) / 3
        
        if recent_avg < previous_avg - 1:
            stats['trend'] = 'improving'
        elif recent_avg > previous_avg + 1:
            stats['trend'] = 'worsening'
    
    return stats

def get_common_intents(user_id):
    """Get most common chat intents for a user"""
    try:
        # Get intent distribution from chat history
        intents = db.session.query(
            ChatHistory.intent,
            db.func.count(ChatHistory.intent).label('count')
        ).filter(
            ChatHistory.user_id == user_id,
            ChatHistory.intent.isnot(None)
        ).group_by(ChatHistory.intent).order_by(db.desc('count')).limit(5).all()
        
        return [{'intent': i[0], 'count': i[1]} for i in intents]
    except Exception as e:
        app.logger.error(f"Error getting common intents: {str(e)}")
        return []

def generate_activity_feed(symptoms, risks, chats, mental_health_logs):
    """Generate recent activity feed"""
    activities = []
    
    # Add symptoms
    for symptom in symptoms[:3]:
        activities.append({
            'title': f'Symptom logged: {symptom.symptom_name}',
            'description': f'Severity: {symptom.severity}',
            'time': symptom.created_at.strftime('%H:%M') if symptom.created_at else 'Recently',
            'icon': 'heartbeat'
        })
    
    # Add risks
    for risk in risks[:2]:
        activities.append({
            'title': f'{risk.prediction.title()} risk detected',
            'description': f'Confidence: {(risk.confidence * 100):.0f}%',
            'time': risk.created_at.strftime('%H:%M') if risk.created_at else 'Recently',
            'icon': 'exclamation-triangle'
        })
    
    # Add chats
    for chat in chats[:2]:
        activities.append({
            'title': 'Chat with PregBot',
            'description': chat.user_message[:50] + ('...' if len(chat.user_message) > 50 else ''),
            'time': chat.created_at.strftime('%H:%M') if chat.created_at else 'Recently',
            'icon': 'robot'
        })
    
    # Add mental health logs
    for log in mental_health_logs[:2]:
        activities.append({
            'title': f'Mood check: {log.mood}',
            'description': f'Stress: {log.stress_level}/10',
            'time': log.created_at.strftime('%H:%M') if log.created_at else 'Recently',
            'icon': 'brain'
        })
    
    # Sort by time (newest first)
    activities.sort(key=lambda x: x['time'], reverse=True)
    
    return activities[:5]  # Return top 5 activities

def generate_reminders(profile):
    """Generate pregnancy reminders"""
    reminders = []
    
    if not profile:
        return reminders
    
    # Appointment reminders
    reminders.append({
        'title': 'Next Prenatal Checkup',
        'description': 'Regular checkup with your obstetrician',
        'date': 'Tomorrow, 10:00 AM',
        'icon': 'calendar-check'
    })
    
    # Medication reminders
    reminders.append({
        'title': 'Take Prenatal Vitamins',
        'description': 'Daily vitamin routine',
        'date': 'Daily, 8:00 AM',
        'icon': 'pills'
    })
    
    # Trimester-specific reminders
    if profile.trimester == 1:
        reminders.append({
            'title': 'First Trimester Screening',
            'description': 'Schedule your first trimester screening',
            'date': 'This week',
            'icon': 'stethoscope'
        })
    elif profile.trimester == 2:
        reminders.append({
            'title': 'Anatomy Ultrasound',
            'description': 'Detailed scan of baby\'s development',
            'date': 'Next week',
            'icon': 'baby'
        })
    else:
        reminders.append({
            'title': 'Birth Preparation Class',
            'description': 'Attend childbirth education class',
            'date': 'This month',
            'icon': 'graduation-cap'
        })
    
    return reminders

def generate_activity_feed(symptoms, risks, chats, mental_health_logs):
    """Generate recent activity feed"""
    activities = []
    
    # Add symptoms
    for symptom in symptoms[:3]:
        activities.append({
            'title': f'Symptom logged: {symptom.symptom_name}',
            'description': f'Severity: {symptom.severity}',
            'time': symptom.created_at.strftime('%H:%M') if symptom.created_at else 'Recently',
            'icon': 'heartbeat'
        })
    
    # Add risks
    for risk in risks[:2]:
        activities.append({
            'title': f'{risk.prediction.title()} risk detected',
            'description': f'Confidence: {(risk.confidence * 100):.0f}%',
            'time': risk.created_at.strftime('%H:%M') if risk.created_at else 'Recently',
            'icon': 'exclamation-triangle'
        })
    
    # Add chats
    for chat in chats[:2]:
        activities.append({
            'title': 'Chat with PregBot',
            'description': chat.user_message[:50] + ('...' if len(chat.user_message) > 50 else ''),
            'time': chat.created_at.strftime('%H:%M') if chat.created_at else 'Recently',
            'icon': 'robot'
        })
    
    # Add mental health logs
    for log in mental_health_logs[:2]:
        activities.append({
            'title': f'Mood check: {log.mood}',
            'description': f'Stress: {log.stress_level}/10',
            'time': log.created_at.strftime('%H:%M') if log.created_at else 'Recently',
            'icon': 'brain'
        })
    
    # Sort by time (newest first)
    activities.sort(key=lambda x: x['time'], reverse=True)
    
    return activities[:5]  # Return top 5 activities

def generate_reminders(profile):
    """Generate pregnancy reminders"""
    reminders = []
    
    if not profile:
        return reminders
    
    # Appointment reminders
    reminders.append({
        'title': 'Next Prenatal Checkup',
        'description': 'Regular checkup with your obstetrician',
        'date': 'Tomorrow, 10:00 AM',
        'icon': 'calendar-check'
    })
    
    # Medication reminders
    reminders.append({
        'title': 'Take Prenatal Vitamins',
        'description': 'Daily vitamin routine',
        'date': 'Daily, 8:00 AM',
        'icon': 'pills'
    })
    
    # Trimester-specific reminders
    if profile.trimester == 1:
        reminders.append({
            'title': 'First Trimester Screening',
            'description': 'Schedule your first trimester screening',
            'date': 'This week',
            'icon': 'stethoscope'
        })
    elif profile.trimester == 2:
        reminders.append({
            'title': 'Anatomy Ultrasound',
            'description': 'Detailed scan of baby\'s development',
            'date': 'Next week',
            'icon': 'baby'
        })
    else:
        reminders.append({
            'title': 'Birth Preparation Class',
            'description': 'Attend childbirth education class',
            'date': 'This month',
            'icon': 'graduation-cap'
        })
    
    return reminders

@app.route('/api/dashboard/stats')
@login_required
def api_dashboard_stats():
    """API endpoint for dashboard statistics"""
    try:
        if current_user.user_type == 'doctor':
            return jsonify({'error': 'Doctors cannot access patient dashboard stats'}), 403
        
        # Calculate statistics
        chat_count = ChatHistory.query.filter_by(user_id=current_user.id).count()
        symptom_count = SymptomLog.query.filter_by(patient_id=current_user.id).count()
        
        high_risk_count = RiskPrediction.query.filter_by(
            patient_id=current_user.id,
            prediction='high'
        ).count()
        
        # Check for new alerts created in the last 24 hours
        from datetime import datetime, timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        new_alerts = DoctorAlert.query.filter(
            DoctorAlert.patient_id == current_user.id,
            DoctorAlert.status == 'pending',
            DoctorAlert.created_at >= yesterday
        ).count()
        
        # Calculate mental health average mood
        mental_health_logs = MentalHealthLog.query.filter_by(
            patient_id=current_user.id
        ).order_by(MentalHealthLog.created_at.desc()).limit(10).all()
        
        avg_mood = 0
        if mental_health_logs:
            mood_scores = []
            mood_map = {
                'very happy': 5,
                'happy': 4,
                'neutral': 3,
                'sad': 2,
                'very sad': 1
            }
            
            for log in mental_health_logs:
                if log.mood:
                    score = mood_map.get(log.mood.lower(), 3)
                    mood_scores.append(score)
            
            if mood_scores:
                avg_mood = sum(mood_scores) / len(mood_scores)
        
        return jsonify({
            'chat_count': chat_count,
            'symptom_count': symptom_count,
            'high_risk_count': high_risk_count,
            'new_alerts': new_alerts,
            'avg_mood': round(avg_mood, 1),
            'updated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Error in api_dashboard_stats: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch dashboard statistics',
            'chat_count': 0,
            'symptom_count': 0,
            'high_risk_count': 0,
            'new_alerts': 0,
            'avg_mood': 0
        }), 500

@app.route('/doctor_dashboard')
@login_required
def doctor_dashboard():
    if current_user.user_type != 'doctor':
        return redirect(url_for('dashboard'))
    
    try:
        # Get all pending alerts sorted by priority (high first)
        pending_alerts = DoctorAlert.query.filter_by(
            status='pending'
        ).order_by(
            db.case(
                (DoctorAlert.priority == 'high', 1),
                (DoctorAlert.priority == 'medium', 2),
                (DoctorAlert.priority == 'low', 3),
                else_=4
            )
        ).order_by(DoctorAlert.created_at.desc()).all()
        
        # Get high risk patients (patients with high risk predictions)
        high_risk_predictions = RiskPrediction.query.filter_by(
            prediction='high'
        ).order_by(RiskPrediction.created_at.desc()).limit(20).all()
        
        # Get emergency cases
        emergency_cases = RiskPrediction.query.filter_by(
            is_emergency=True
        ).order_by(RiskPrediction.created_at.desc()).all()
        
        # Get all patients
        patients = User.query.filter_by(user_type='patient').all()
        
        # Get statistics
        stats = {
            'total_patients': len(patients),
            'pending_alerts': len(pending_alerts),
            'high_risk_cases': len(high_risk_predictions),
            'emergency_cases': len(emergency_cases),
            'today_alerts': DoctorAlert.query.filter(
                DoctorAlert.created_at >= datetime.utcnow().date(),
                DoctorAlert.status == 'pending'
            ).count()
        }
        
        # Get patient details for high risk cases
        high_risk_patients = []
        for prediction in high_risk_predictions[:10]:  # Limit to 10
            patient = User.query.get(prediction.patient_id)
            profile = PatientProfile.query.filter_by(user_id=patient.id).first()
            high_risk_patients.append({
                'patient': patient,
                'profile': profile,
                'prediction': prediction,
                'recent_symptoms': SymptomLog.query.filter_by(
                    patient_id=patient.id
                ).order_by(SymptomLog.created_at.desc()).limit(3).all()
            })
        
        # Get emergency patient details
        emergency_patients = []
        for prediction in emergency_cases[:5]:  # Limit to 5
            patient = User.query.get(prediction.patient_id)
            profile = PatientProfile.query.filter_by(user_id=patient.id).first()
            emergency_patients.append({
                'patient': patient,
                'profile': profile,
                'prediction': prediction
            })
        
    except Exception as e:
        app.logger.error(f"Error loading doctor dashboard: {str(e)}")
        pending_alerts = []
        high_risk_predictions = []
        emergency_cases = []
        patients = []
        stats = {}
        high_risk_patients = []
        emergency_patients = []
    
    return render_template('doctor_dashboard.html',
                         pending_alerts=pending_alerts,
                         high_risk_predictions=high_risk_predictions,
                         emergency_cases=emergency_cases,
                         patients=patients,
                         stats=stats,
                         high_risk_patients=high_risk_patients,
                         emergency_patients=emergency_patients)

@app.route('/chatbot', methods=['GET', 'POST'])
@login_required
def chatbot_interface():
    if current_user.user_type == 'doctor':
        flash('Doctors have access to medical dashboard. Chatbot is for patient support.', 'info')
        return redirect(url_for('doctor_dashboard'))
    
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
                message = data.get('message', '').strip()
                chat_session_id = data.get('session_id', str(uuid.uuid4()))
            else:
                message = request.form.get('message', '').strip()
                chat_session_id = request.form.get('session_id', str(uuid.uuid4()))
            
            if not message:
                if request.is_json:
                    return jsonify({'error': 'Message cannot be empty'}), 400
                flash('Please enter a message', 'warning')
                return redirect(url_for('chatbot_interface'))
            
            # Get patient profile for context
            profile = PatientProfile.query.filter_by(user_id=current_user.id).first()
            trimester = profile.trimester if profile else 1
            age = profile.age if profile else 25
            
            # Enhanced chatbot with context
            chat_context = {
                'user_id': current_user.id,
                'trimester': trimester,
                'age': age,
                'session_id': chat_session_id,
                'previous_context': session.get('chat_context', {})
            }
            
            # Process message with simple NLP (for now)
            intent = chatbot.classify_intent(message)
            response = chatbot.get_response(intent)
            
            # Calculate confidence score
            confidence = 0.8  # Default confidence
            
            # Store context for next conversation
            session['chat_context'] = {
                'last_intent': intent,
                'trimester': trimester,
                'session_id': chat_session_id
            }
            session['chat_session_id'] = chat_session_id
            
            # Save chat history
            chat = ChatHistory(
                user_id=current_user.id,
                user_message=message,
                bot_response=response,
                intent=intent,
                entities=json.dumps({}),
                confidence=confidence,
                session_id=chat_session_id,
                chat_metadata=json.dumps({
                    'trimester': trimester,
                    'context_used': True,
                    'response_time': 0.1
                }),
                sentiment='neutral'
            )
            db.session.add(chat)
            db.session.commit()
            
            # Check if doctor alert is needed
            trigger_alert = False
            emergency_keywords = ['emergency', 'urgent', '911', 'help immediately', 'severe pain', 'heavy bleeding']
            message_lower = message.lower()
            
            for keyword in emergency_keywords:
                if keyword in message_lower:
                    trigger_alert = True
                    break
            
            if trigger_alert:
                alert = DoctorAlert(
                    patient_id=current_user.id,
                    alert_type='chatbot_concern',
                    priority='high',
                    doctor_notes=f"Chatbot concern: {message[:100]}...",
                    alert_metadata=json.dumps({
                        'session_id': chat_session_id,
                        'intent': intent,
                        'confidence': confidence,
                        'user_message': message[:200]
                    })
                )
                db.session.add(alert)
                db.session.commit()
            
            if request.is_json:
                return jsonify({
                    'response': response,
                    'intent': intent,
                    'confidence': confidence,
                    'entities': {},
                    'session_id': chat_session_id,
                    'suggestions': [],
                    'show_doctor_alert': trigger_alert,
                    'chat_id': chat.id
                })
            
            flash('Chat response generated', 'success')
            return redirect(url_for('chatbot_interface'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error in chatbot: {str(e)}", exc_info=True)
            
            if request.is_json:
                return jsonify({
                    'response': "I'm experiencing technical difficulties. Please try again in a moment.",
                    'error': str(e),
                    'session_id': session.get('chat_session_id', str(uuid.uuid4()))
                }), 500
            
            flash('Error processing your message. Please try again.', 'danger')
            return redirect(url_for('chatbot_interface'))
    
    # GET request - display chatbot interface
    try:
        # Get chat history for current session
        chat_session_id = session.get('chat_session_id', str(uuid.uuid4()))
        session['chat_session_id'] = chat_session_id
        
        # Get last 50 messages from current user
        chats = ChatHistory.query.filter_by(
            user_id=current_user.id
        ).order_by(ChatHistory.created_at.desc()).limit(50).all()
        
        # Get patient profile for personalized suggestions
        profile = PatientProfile.query.filter_by(user_id=current_user.id).first()
        
        # Get quick questions based on trimester
        trimester = profile.trimester if profile else 1
        quick_questions = get_quick_questions(trimester)
        
        # Get chatbot statistics
        chat_stats = {
            'total_chats': len(chats),
            'today_chats': ChatHistory.query.filter(
                ChatHistory.user_id == current_user.id,
                db.func.date(ChatHistory.created_at) == datetime.utcnow().date()
            ).count(),
            'common_intents': get_common_intents(current_user.id)
        }
        
    except Exception as e:
        app.logger.error(f"Error loading chatbot page: {str(e)}")
        chats = []
        quick_questions = []
        chat_stats = {}
        profile = None
    
    return render_template('chatbot.html',
                         chats=chats[::-1] if chats else [],  # Reverse to show oldest first
                         quick_questions=quick_questions,
                         chat_stats=chat_stats,
                         profile=profile,
                         session_id=session.get('chat_session_id'))
# Helper functions for chatbot
def get_quick_questions(trimester):
    """Get quick question suggestions based on trimester"""
    questions = {
        1: [
            "What should I eat in first trimester?",
            "Is morning sickness normal?",
            "Can I exercise during first trimester?",
            "What vitamins should I take?",
            "How much weight should I gain?"
        ],
        2: [
            "What foods are good for baby's development?",
            "Is back pain normal in second trimester?",
            "Can I travel during pregnancy?",
            "What tests should I expect?",
            "How to deal with heartburn?"
        ],
        3: [
            "What are signs of labor?",
            "How to prepare for delivery?",
            "What to pack for hospital?",
            "Is swelling normal in third trimester?",
            "How to relieve pelvic pain?"
        ]
    }
    return questions.get(trimester, [
        "What foods are safe during pregnancy?",
        "How much exercise is recommended?",
        "What are warning signs to watch for?",
        "How to manage stress during pregnancy?",
        "When should I call my doctor?"
    ])

def get_common_intents(user_id):
    """Get most common chat intents for a user"""
    try:
        # Get intent distribution from chat history
        intents = db.session.query(
            ChatHistory.intent,
            db.func.count(ChatHistory.intent).label('count')
        ).filter(
            ChatHistory.user_id == user_id,
            ChatHistory.intent.isnot(None)
        ).group_by(ChatHistory.intent).order_by(db.desc('count')).limit(5).all()
        
        return [{'intent': i[0], 'count': i[1]} for i in intents]
    except Exception as e:
        app.logger.error(f"Error getting common intents: {str(e)}")
        return []

@app.route('/symptom_check', methods=['GET', 'POST'])
@login_required
def symptom_check():
    if current_user.user_type == 'doctor':
        flash('Doctors access patient data through dashboard.', 'info')
        return redirect(url_for('doctor_dashboard'))
    
    if request.method == 'POST':
        try:
            symptom_name = request.form['symptom_name']
            severity = request.form['severity']
            duration = request.form['duration']
            description = request.form.get('description', '')
            
            # Get patient profile
            profile = PatientProfile.query.filter_by(user_id=current_user.id).first()
            
            if not profile:
                flash('Please complete your profile first!', 'danger')
                return redirect(url_for('profile'))
            
            # Save symptom log
            symptom = SymptomLog(
                patient_id=current_user.id,
                symptom_name=symptom_name,
                severity=severity,
                duration_days=duration,
                description=description
            )
            db.session.add(symptom)
            db.session.flush()
            
            # Predict risk with enhanced system
            risk_result = risk_predictor.predict_risk(
                age=profile.age or 25,
                trimester=profile.trimester or 1,
                bp_category=profile.blood_pressure_category or 'normal',
                symptom_severity=severity,
                symptom_name=symptom_name
            )
            
            # Update age in factors if it was set to 0 (from emergency risk)
            if risk_result['factors'].get('age') == 0:
                risk_result['factors']['age'] = profile.age or 25
            
            # Save risk prediction
            risk_prediction = RiskPrediction(
                patient_id=current_user.id,
                prediction=risk_result['risk_level'],
                confidence=risk_result['confidence'],
                factors_age=risk_result['factors']['age'],
                factors_trimester=risk_result['factors']['trimester'],
                factors_bp_category=risk_result['factors']['blood_pressure'],
                factors_symptom_severity=risk_result['factors']['symptom_severity'],
                factors_symptom_name=risk_result['factors'].get('symptom_name', ''),
                explanation=risk_result['explanation'],
                is_emergency=risk_result.get('is_emergency', False)
            )
            db.session.add(risk_prediction)
            db.session.flush()
            
            # Create doctor alert for medium/high risks
            if risk_result['risk_level'] in ['medium', 'high']:
                alert_priority = 'high' if risk_result['risk_level'] == 'high' else 'medium'
                
                alert = DoctorAlert(
                    patient_id=current_user.id,
                    prediction_id=risk_prediction.id,
                    alert_type='symptom_risk',
                    priority=alert_priority,
                    doctor_notes=f"{symptom_name} - {severity} severity - {risk_result['risk_level'].upper()} risk",
                    metadata=json.dumps({
                        'symptom': symptom_name,
                        'severity': severity,
                        'duration': duration,
                        'risk_level': risk_result['risk_level'],
                        'confidence': risk_result['confidence'],
                        'explanation': risk_result['explanation'],
                        'is_emergency': risk_result.get('is_emergency', False)
                    })
                )
                db.session.add(alert)
                
                # Also send email notification for high risk
                if risk_result['risk_level'] == 'high':
                    send_high_risk_notification(current_user, symptom_name, severity, risk_result)
            
            db.session.commit()
            
            # Store in session for display
            session['last_risk_result'] = risk_result
            
            # Flash appropriate message
            if risk_result['risk_level'] == 'high':
                flash(f'🚨 HIGH RISK DETECTED: {risk_result["explanation"]}', 'danger')
                if risk_result.get('is_emergency'):
                    flash('🆘 EMERGENCY: Contact your healthcare provider immediately or go to emergency room.', 'danger')
            elif risk_result['risk_level'] == 'medium':
                flash(f'⚠️ MEDIUM RISK: {risk_result["explanation"]}', 'warning')
            else:
                flash(f'✅ LOW RISK: {risk_result["explanation"]}', 'success')
            
            return redirect(url_for('symptom_check'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error in symptom_check: {str(e)}", exc_info=True)
            flash(f'Error processing symptom check: {str(e)}', 'danger')
            return redirect(url_for('symptom_check'))
    
    # GET request
    try:
        symptoms = SymptomLog.query.filter_by(
            patient_id=current_user.id
        ).order_by(SymptomLog.created_at.desc()).all()
        
        risk_history = RiskPrediction.query.filter_by(
            patient_id=current_user.id
        ).order_by(RiskPrediction.created_at.desc()).all()
        
    except Exception as e:
        app.logger.error(f"Error fetching symptom history: {str(e)}")
        symptoms = []
        risk_history = []
    
    last_result = session.get('last_risk_result', None)
    
    return render_template('symptom_check.html',
                         symptoms=symptoms,
                         risk_history=risk_history,
                         last_result=last_result)

def send_high_risk_notification(user, symptom, severity, risk_result):
    """Send high risk notification (simulated)"""
    # In production, this would send email/SMS
    app.logger.info(f"HIGH RISK ALERT for {user.email}: {symptom} ({severity}) - {risk_result['explanation']}")

@app.route('/mental_health', methods=['GET', 'POST'])
@login_required
def mental_health():
    if current_user.user_type == 'doctor':
        flash('Doctors cannot access patient mental health tracking.', 'warning')
        return redirect(url_for('doctor_dashboard'))
    
    if request.method == 'POST':
        try:
            # Get form data with defaults
            mood = request.form.get('mood', '').strip()
            stress_level = request.form.get('stress_level', '5')
            anxiety_level = request.form.get('anxiety_level', '5')
            sleep_hours = request.form.get('sleep_hours', '7.5')
            notes = request.form.get('notes', '').strip()
            physical_symptoms = request.form.getlist('physical_symptoms')
            
            # Validate required fields
            if not mood:
                flash('Please select a mood.', 'danger')
                return redirect(url_for('mental_health'))
            
            # Convert to appropriate types with error handling
            try:
                stress_level_int = int(stress_level)
                if not 1 <= stress_level_int <= 10:
                    flash('Stress level must be between 1 and 10.', 'danger')
                    return redirect(url_for('mental_health'))
            except ValueError:
                flash('Invalid stress level. Please enter a number between 1-10.', 'danger')
                return redirect(url_for('mental_health'))
            
            try:
                anxiety_level_int = int(anxiety_level)
                if not 1 <= anxiety_level_int <= 10:
                    flash('Anxiety level must be between 1 and 10.', 'danger')
                    return redirect(url_for('mental_health'))
            except ValueError:
                flash('Invalid anxiety level. Please enter a number between 1-10.', 'danger')
                return redirect(url_for('mental_health'))
            
            try:
                sleep_hours_float = float(sleep_hours)
                if not 0 <= sleep_hours_float <= 24:
                    flash('Sleep hours must be between 0 and 24.', 'danger')
                    return redirect(url_for('mental_health'))
            except ValueError:
                flash('Invalid sleep hours. Please enter a number.', 'danger')
                return redirect(url_for('mental_health'))
            
            # Analyze sentiment using helper function
            sentiment, recommendation = analyze_mental_health_sentiment(
                mood=mood,
                stress_level=stress_level_int,
                anxiety_level=anxiety_level_int,
                sleep_hours=sleep_hours_float,
                notes=notes
            )
            
            # Add physical symptoms to notes if any
            if physical_symptoms and 'none' not in [s.lower() for s in physical_symptoms]:
                symptoms_text = ", ".join([s.replace('_', ' ').title() for s in physical_symptoms if s != 'none'])
                notes += f"\n\nPhysical symptoms noted: {symptoms_text}"
            
            # Save mental health log
            mental_log = MentalHealthLog(
                patient_id=current_user.id,
                mood=mood,
                stress_level=stress_level_int,
                anxiety_level=anxiety_level_int,
                sleep_hours=sleep_hours_float,
                notes=notes.strip(),
                sentiment=sentiment,
                recommendation=recommendation
            )
            db.session.add(mental_log)
            db.session.commit()
            
            # Get log ID for potential alert creation
            log_id = mental_log.id
            
            # Create doctor alert for extreme cases
            if stress_level_int >= 9 or anxiety_level_int >= 9:
                alert = DoctorAlert(
                    patient_id=current_user.id,
                    alert_type='mental_health_crisis',
                    priority='high',
                    doctor_notes=f'Extreme levels detected - Stress: {stress_level_int}/10, Anxiety: {anxiety_level_int}/10, Mood: {mood}'
                )
                db.session.add(alert)
                db.session.commit()
                
                flash('Mental health log saved! High stress detected - your doctor has been notified.', 'warning')
            elif stress_level_int >= 7 or anxiety_level_int >= 7:
                # Check for persistent moderate-high stress
                recent_logs = MentalHealthLog.query.filter_by(
                    patient_id=current_user.id
                ).order_by(MentalHealthLog.created_at.desc()).limit(3).all()
                
                if len(recent_logs) >= 3:
                    high_stress_count = sum(1 for log in recent_logs if log.stress_level and log.stress_level >= 7)
                    if high_stress_count >= 2:
                        alert = DoctorAlert(
                            patient_id=current_user.id,
                            alert_type='persistent_stress',
                            priority='medium',
                            doctor_notes=f'Persistent moderate-high stress detected over last {len(recent_logs)} entries'
                        )
                        db.session.add(alert)
                        db.session.commit()
                        flash('Mental health log saved! Persistent stress pattern detected.', 'info')
                    else:
                        flash('Mental health log saved successfully!', 'success')
                else:
                    flash('Mental health log saved successfully!', 'success')
            else:
                flash('Mental health log saved successfully!', 'success')
            
            return redirect(url_for('mental_health'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error in mental_health POST: {str(e)}", exc_info=True)
            flash(f'Error saving mental health log. Please try again. Error: {str(e)}', 'danger')
            return redirect(url_for('mental_health'))
    
    # GET request - display mental health page
    try:
        # Get mental health history
        logs = MentalHealthLog.query.filter_by(
            patient_id=current_user.id
        ).order_by(MentalHealthLog.created_at.desc()).all()
        
        # Get patient profile
        profile = PatientProfile.query.filter_by(user_id=current_user.id).first()
        
    except Exception as e:
        app.logger.error(f"Error fetching data for mental health page: {str(e)}")
        logs = []
        profile = None
        flash('Error loading your mental health data. Please try again.', 'warning')
    
    # Calculate statistics safely
    stats = {
        'total_logs': len(logs),
        'avg_stress': 0,
        'avg_anxiety': 0,
        'avg_sleep': 0,
        'recent_trend': 'stable',
        'most_common_mood': 'No data'
    }
    
    if logs:
        # Calculate averages using safe getters if available
        valid_stress = []
        valid_anxiety = []
        valid_sleep = []
        
        for log in logs:
            # Use safe getter methods if they exist, otherwise direct access
            stress = log.stress_level if hasattr(log, 'stress_level') else 0
            anxiety = log.anxiety_level if hasattr(log, 'anxiety_level') else 0
            sleep_hrs = log.sleep_hours if hasattr(log, 'sleep_hours') else 0.0
            
            if stress is not None:
                valid_stress.append(stress)
            if anxiety is not None:
                valid_anxiety.append(anxiety)
            if sleep_hrs is not None:
                valid_sleep.append(sleep_hrs)
        
        if valid_stress:
            stats['avg_stress'] = round(sum(valid_stress) / len(valid_stress), 1)
        if valid_anxiety:
            stats['avg_anxiety'] = round(sum(valid_anxiety) / len(valid_anxiety), 1)
        if valid_sleep:
            stats['avg_sleep'] = round(sum(valid_sleep) / len(valid_sleep), 1)
        
        # Determine recent trend (last 3 entries vs previous 3)
        if len(logs) >= 6:
            recent = logs[:3]
            previous = logs[3:6]
            
            recent_avg_stress = sum(log.stress_level or 0 for log in recent) / 3
            previous_avg_stress = sum(log.stress_level or 0 for log in previous) / 3
            
            if recent_avg_stress < previous_avg_stress - 1:
                stats['recent_trend'] = 'improving'
            elif recent_avg_stress > previous_avg_stress + 1:
                stats['recent_trend'] = 'worsening'
            else:
                stats['recent_trend'] = 'stable'
        
        # Find most common mood
        mood_counts = {}
        for log in logs:
            mood = log.mood or 'Not specified'
            mood_counts[mood] = mood_counts.get(mood, 0) + 1
        
        if mood_counts:
            stats['most_common_mood'] = max(mood_counts.items(), key=lambda x: x[1])[0]
    
    # Get recommendations
    recommendations = []
    if profile and profile.trimester:
        try:
            trimester_recs = Recommendation.query.filter_by(
                trimester=profile.trimester
            ).filter(
                Recommendation.category.in_(['mental_health', 'general'])
            ).limit(3).all()
            
            if trimester_recs:
                recommendations = trimester_recs
        except Exception as e:
            app.logger.error(f"Error fetching recommendations: {str(e)}")
    
    # If no trimester-specific recommendations, get general ones
    if not recommendations:
        try:
            general_recs = Recommendation.query.filter_by(
                category='general'
            ).limit(3).all()
            
            if general_recs:
                recommendations = general_recs
        except Exception as e:
            app.logger.error(f"Error fetching general recommendations: {str(e)}")
    
    # Prepare data for template
    template_data = {
        'logs': logs or [],
        'profile': profile,
        'stats': stats,
        'recommendations': recommendations or [],
        'has_data': bool(logs)
    }
    
    return render_template('mental_health.html', **template_data)
def analyze_mental_health_sentiment(mood, stress_level, anxiety_level, sleep_hours, notes):
    """Analyze sentiment based on multiple factors"""
    sentiment_score = 0
    
    # Mood scoring
    mood_scores = {
        'very happy': 2,
        'happy': 1,
        'neutral': 0,
        'sad': -1,
        'very sad': -2
    }
    
    mood_lower = mood.lower()
    sentiment_score += mood_scores.get(mood_lower, 0)
    
    # Stress and anxiety scoring
    if stress_level <= 3:
        sentiment_score += 1
    elif stress_level >= 8:
        sentiment_score -= 2
    elif stress_level >= 5:
        sentiment_score -= 1
    
    if anxiety_level <= 3:
        sentiment_score += 1
    elif anxiety_level >= 8:
        sentiment_score -= 2
    elif anxiety_level >= 5:
        sentiment_score -= 1
    
    # Sleep scoring
    if 7 <= sleep_hours <= 9:
        sentiment_score += 1
    elif sleep_hours < 5:
        sentiment_score -= 1
    elif sleep_hours > 10:
        sentiment_score -= 0.5
    
    # Determine sentiment category
    if sentiment_score >= 2:
        sentiment = 'positive'
        recommendation = "Excellent emotional state! Keep up the good self-care practices."
    elif sentiment_score >= 0:
        sentiment = 'positive'
        recommendation = "Good emotional state. Continue with healthy habits."
    elif sentiment_score >= -2:
        sentiment = 'moderate'
        recommendation = "Moderate stress detected. Try relaxation techniques and consider discussing with your support system."
    else:
        sentiment = 'negative'
        recommendation = "High stress detected. Please consider professional support or talk to your healthcare provider."
    
    # Add personalized notes
    negative_keywords = ['worried', 'anxious', 'scared', 'afraid', 'stressed', 'overwhelmed', 'depressed', 'sad']
    positive_keywords = ['happy', 'good', 'better', 'improved', 'calm', 'peaceful', 'excited', 'hopeful']
    
    notes_lower = notes.lower()
    negative_count = sum(1 for word in negative_keywords if word in notes_lower)
    positive_count = sum(1 for word in positive_keywords if word in notes_lower)
    
    if negative_count > positive_count + 2 and sentiment != 'negative':
        sentiment = 'moderate' if sentiment == 'positive' else 'negative'
        recommendation += " Your notes suggest some concerns that might need attention."
    elif positive_count > negative_count + 2 and sentiment != 'positive':
        sentiment = 'positive' if sentiment == 'moderate' else 'moderate'
    
    return sentiment, recommendation

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    profile = PatientProfile.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        try:
            if not profile:
                profile = PatientProfile(user_id=current_user.id)
                db.session.add(profile)
            
            profile.age = int(request.form['age']) if request.form['age'] else None
            profile.trimester = int(request.form['trimester']) if request.form['trimester'] else None
            profile.blood_pressure_category = request.form['blood_pressure']
            profile.weight = float(request.form['weight']) if request.form.get('weight') else None
            profile.height = float(request.form['height']) if request.form.get('height') else None
            profile.medical_history = request.form.get('medical_history', '')
            profile.allergies = request.form.get('allergies', '')
            
            # Update user info
            current_user.full_name = request.form['full_name']
            current_user.phone = request.form.get('phone', '')
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('profile'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'danger')
    
    return render_template('profile.html', profile=profile)

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.get_json()
    message = data.get('message', '')
    
    intent = chatbot.classify_intent(message)
    response = chatbot.get_response(intent)
    
    # Save to database
    chat = ChatHistory(
        user_id=current_user.id,
        user_message=message,
        bot_response=response,
        intent=intent,
        sentiment='neutral'
    )
    db.session.add(chat)
    db.session.commit()
    
    return jsonify({
        'response': response,
        'intent': intent
    })

@app.route('/api/predict_risk', methods=['POST'])
@login_required
def api_predict_risk():
    data = request.get_json()
    
    profile = PatientProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        return jsonify({'error': 'Profile not found'}), 400
    
    risk_result = risk_predictor.predict_risk(
        age=profile.age or data.get('age', 25),
        trimester=profile.trimester or data.get('trimester', 1),
        bp_category=data.get('bp_category', 'normal'),
        symptom_severity=data.get('severity', 'mild')
    )
    
    return jsonify(risk_result)

@app.route('/api/recommendations')
@login_required
def api_recommendations():
    profile = PatientProfile.query.filter_by(user_id=current_user.id).first()
    trimester = profile.trimester if profile else 1
    
    recommendations = Recommendation.query.filter_by(trimester=trimester).all()
    
    result = []
    for rec in recommendations:
        result.append({
            'id': rec.id,
            'category': rec.category,
            'title': rec.title,
            'description': rec.description,
            'condition': rec.for_condition
        })
    
    return jsonify(result)

@app.route('/doctor/alert/<int:alert_id>/review', methods=['POST'])
@login_required
def review_alert(alert_id):
    if current_user.user_type != 'doctor':
        return jsonify({'error': 'Unauthorized'}), 403
    
    alert = DoctorAlert.query.get_or_404(alert_id)
    data = request.get_json()
    
    alert.status = data.get('status', 'reviewed')
    alert.doctor_notes = data.get('notes', '')
    alert.reviewed_by = current_user.id
    alert.reviewed_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'message': 'Alert reviewed successfully'})

# Database initialization
def init_db():
    """Initialize database with required tables"""
    with app.app_context():
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(email='admin@gmail.com').first()
        if not admin:
            admin_user = User(
                email='admin@gmail.com',
                password=generate_password_hash('admin'),
                full_name='System Admin',
                user_type='doctor',
                phone='+1234567890'
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created: admin@gmail.com / admin")

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.errorhandler(mysql.connector.Error)
def handle_mysql_error(error):
    db.session.rollback()
    app.logger.error(f"MySQL Error: {str(error)}")
    flash('Database error occurred. Please try again.', 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    print("PregBot is running on http://localhost:5000")
    print("Admin credentials: admin@gmail.com / admin")
    app.run(debug=True, port=5000, host='0.0.0.0')

           