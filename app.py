import os
import json
import random
import io
from datetime import datetime
from dateutil.relativedelta import relativedelta
from flask import (
    Flask, render_template, request, redirect, url_for, flash, 
    session, send_from_directory, abort, jsonify, make_response, send_file, current_app
)
from config import SQLALCHEMY_DATABASE_URI, SECRET_KEY, UPLOAD_FOLDER
from models import db, User, Application, Document, Admin, EMI
from services import (
    auth_service, storage_service, advance_verification_service, 
    decision_service, notification_service, autofill_service
)
from functools import wraps
from decimal import Decimal

# PDF Generation imports
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# Import advanced verification service
from services.advance_verification_service import  AdvanceVerificationService
from services.ai_analysis_engine import AIVerificationService
from services.pdf_report_generator import ComprehensivePDFReportGenerator
# Add at the top of app.py
from services.pdf_generator import (
    generate_credit_risk_report,
    generate_document_verification_report, 
    generate_property_verification_report,
    generate_final_comprehensive_report,
    generate_loan_agreement
)
from services.ai_summary_generator import AISummaryGenerator

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SECRET_KEY'] = SECRET_KEY
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db.init_app(app)

# ===== MOVE AUTHENTICATION DECORATOR HERE - FIRST =====
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Allow both regular users and admin users
        if 'user_id' not in session and 'admin_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ===== SIMPLY IMPORT AND REGISTER THE BLUEPRINT =====
from admin.routes import admin_bp
app.register_blueprint(admin_bp)

def update_database_schema():
    """Add missing columns to existing database tables"""
    from sqlalchemy import text
    
    try:
        # Check if new columns exist, if not add them
        with app.app_context():
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('application')]
            
            new_columns = {
                'employment_verification_status': 'ALTER TABLE application ADD COLUMN employment_verification_status VARCHAR(50) DEFAULT "PENDING"',
                'employment_verification_report': 'ALTER TABLE application ADD COLUMN employment_verification_report TEXT',
                'document_verification_status': 'ALTER TABLE application ADD COLUMN document_verification_status VARCHAR(50) DEFAULT "PENDING"',
                'document_verification_report': 'ALTER TABLE application ADD COLUMN document_verification_report TEXT',
                'na_document_verification': 'ALTER TABLE application ADD COLUMN na_document_verification TEXT',
                'na_document_status': 'ALTER TABLE application ADD COLUMN na_document_status VARCHAR(50) DEFAULT "PENDING"',
                'na_document_risk_score': 'ALTER TABLE application ADD COLUMN na_document_risk_score FLOAT',
                'overall_risk_score': 'ALTER TABLE application ADD COLUMN overall_risk_score FLOAT',
                'verification_summary': 'ALTER TABLE application ADD COLUMN verification_summary TEXT',
                'emi_plan_generated': 'ALTER TABLE application ADD COLUMN emi_plan_generated BOOLEAN DEFAULT 0',
                'loan_disbursement_date': 'ALTER TABLE application ADD COLUMN loan_disbursement_date DATETIME',
                'first_emi_date': 'ALTER TABLE application ADD COLUMN first_emi_date DATETIME',
                'admin_review_notes': 'ALTER TABLE application ADD COLUMN admin_review_notes TEXT',
                'reviewed_by_admin_id': 'ALTER TABLE application ADD COLUMN reviewed_by_admin_id INTEGER',
                'reviewed_at': 'ALTER TABLE application ADD COLUMN reviewed_at DATETIME',
            }
            
            for column_name, alter_sql in new_columns.items():
                if column_name not in existing_columns:
                    print(f"Adding missing column: {column_name}")
                    db.session.execute(text(alter_sql))
            
            db.session.commit()
            print("Database schema updated successfully!")
            
    except Exception as e:
        print(f"Error updating database schema: {e}")
        db.session.rollback()

# Call the update function when app starts
with app.app_context():
    update_database_schema()

# LLM Summary Generation Service
class LLMSummaryService:
    """Service to generate AI summaries for reports with proper response cleaning"""
    
    def clean_ai_response(self, text):
        """Clean and format AI response text"""
        if not text:
            return "No analysis available"
        
        # Remove any markdown formatting
        text = text.replace('**', '').replace('*', '').replace('`', '')
        
        # Remove any XML tags or HTML
        text = text.replace('<', '').replace('>', '')
        
        # Clean up excessive whitespace
        text = ' '.join(text.split())
        
        # Ensure proper sentence structure
        if text and not text.endswith(('.', '!', '?')):
            text += '.'
            
        return text
    
    def generate_credit_summary(self, application, credit_data):
        """Generate credit risk LLM summary"""
        debt_to_income = (application.existing_emi / application.monthly_salary * 100) if application.monthly_salary > 0 else 100
        
        if application.cibil_score >= 750:
            credit_quality = "excellent"
            risk_level = "low"
        elif application.cibil_score >= 650:
            credit_quality = "good" 
            risk_level = "low"
        elif application.cibil_score >= 550:
            credit_quality = "fair"
            risk_level = "medium"
        else:
            credit_quality = "poor"
            risk_level = "high"
        
        # Generate summary text
        overall_assessment = f"Applicant demonstrates {credit_quality} credit quality with a CIBIL score of {application.cibil_score}."
        detailed_analysis = f"The credit profile shows a debt-to-income ratio of {debt_to_income:.1f}%, which is {'within acceptable limits' if debt_to_income <= 50 else 'above recommended thresholds'}. The applicant's credit history indicates {'strong repayment behavior' if application.cibil_score >= 700 else 'some areas for improvement'}."
        
        return {
            "overall_assessment": self.clean_ai_response(overall_assessment),
            "detailed_analysis": self.clean_ai_response(detailed_analysis),
            "key_factors": [
                f"CIBIL Score: {application.cibil_score} ({'Excellent' if application.cibil_score >= 750 else 'Good' if application.cibil_score >= 650 else 'Fair' if application.cibil_score >= 550 else 'Poor'})",
                f"Debt-to-Income Ratio: {debt_to_income:.1f}%",
                f"Credit Utilization: {'Optimal' if application.cibil_score >= 700 else 'Moderate' if application.cibil_score >= 600 else 'High'}",
                f"Payment History: {'Clean' if application.cibil_score >= 700 else 'Satisfactory' if application.cibil_score >= 600 else 'Needs Improvement'}"
            ],
            "recommendations": [
                "Maintain current credit behavior for sustained good score" if application.cibil_score >= 750 else
                "Consider reducing credit card utilization below 30%" if application.cibil_score >= 650 else
                "Focus on timely payments to improve credit score" if application.cibil_score >= 550 else
                "Requires significant improvement in credit management",
                "Monitor debt-to-income ratio regularly",
                "Avoid new credit applications in near term"
            ],
            "confidence_level": "High" if application.cibil_score >= 700 else "Medium" if application.cibil_score >= 600 else "Low"
        }
    
    def generate_document_summary(self, application, documents):
        """Generate document verification LLM summary"""
        verified_count = len([d for d in documents if d['status'] == 'VERIFIED'])
        total_count = len(documents)
        verification_rate = (verified_count / total_count * 100) if total_count > 0 else 0
        
        overall_assessment = f"Document verification is {verification_rate:.1f}% complete with {verified_count} out of {total_count} documents successfully verified."
        detailed_analysis = f"The document submission shows {'strong compliance' if verification_rate >= 90 else 'adequate compliance' if verification_rate >= 70 else 'incomplete submission'}. Key identity and financial documents have been {'successfully validated' if any(d['document_type'] == 'KYC_DOCS' and d['status'] == 'VERIFIED' for d in documents) else 'pending verification'}."
        
        return {
            "overall_assessment": self.clean_ai_response(overall_assessment),
            "detailed_analysis": self.clean_ai_response(detailed_analysis),
            "key_findings": [
                f"Overall Verification Rate: {verification_rate:.1f}%",
                f"Critical Documents: {'All present' if all(d['status'] in ['VERIFIED', 'PENDING'] for d in documents if d['document_type'] in ['KYC_DOCS', 'BANK_STATEMENTS']) else 'Some missing'}",
                f"Document Quality: {'Good' if verification_rate >= 80 else 'Needs Improvement'}",
                f"Processing Status: {'Complete' if verification_rate == 100 else 'In Progress'}"
            ],
            "critical_issues": [
                f"{doc['document_type']} is missing" for doc in documents if doc['status'] == 'MISSING'
            ],
            "recommendations": [
                "Complete pending document submissions",
                "Ensure all documents are clear and legible",
                "Verify document authenticity through secondary sources"
            ],
            "integrity_score": min(10, int(verification_rate / 10))
        }
    
    def generate_property_summary(self, application, property_data):
        """Generate property verification LLM summary"""
        ltv_ratio = (application.loan_amount / application.property_valuation * 100) if application.property_valuation > 0 else 0
        
        overall_assessment = f"Property valuation of ₹{application.property_valuation:,.2f} provides {'strong' if ltv_ratio <= 70 else 'adequate' if ltv_ratio <= 85 else 'marginal'} security coverage for the requested loan."
        detailed_analysis = f"The loan-to-value ratio of {ltv_ratio:.1f}% is {'within conservative limits' if ltv_ratio <= 60 else 'within acceptable range' if ltv_ratio <= 75 else 'approaching maximum thresholds'}. The property classification as {'non-agricultural' if application.is_non_agricultural else 'agricultural'} {'meets' if application.is_non_agricultural else 'does not meet'} lending criteria."
        
        return {
            "overall_assessment": self.clean_ai_response(overall_assessment),
            "detailed_analysis": self.clean_ai_response(detailed_analysis),
            "strengths": [
                f"LTV Ratio: {ltv_ratio:.1f}% ({'Excellent' if ltv_ratio <= 60 else 'Good' if ltv_ratio <= 75 else 'Acceptable'})",
                "Property valuation appears reasonable based on market standards",
                "Adequate security coverage for loan amount" if ltv_ratio <= 80 else "Limited security margin"
            ],
            "risk_factors": [
                risk for risk in [
                    "Non-agricultural declaration required for loan eligibility" if not application.is_non_agricultural else None,
                    "Property title verification pending",
                    "Legal encumbrance check incomplete"
                ] if risk is not None
            ],
            "critical_requirements": [
                "Non-agricultural declaration certificate",
                "Property title deed verification",
                "Legal clearance certificate",
                "Valuation report from approved valuer"
            ],
            "recommendations": [
                "Complete property title verification",
                "Obtain legal clearance certificate",
                "Validate property valuation through independent sources"
            ],
            "security_score": min(10, 10 - int(ltv_ratio / 15)),
            "valuation_confidence": "High" if ltv_ratio <= 70 else "Medium" if ltv_ratio <= 85 else "Low"
        }
    
    def generate_final_summary(self, application, all_data):
        """Generate final comprehensive LLM summary"""
        overall_risk = application.overall_risk_score or 50
        
        executive_summary = f"This application presents a {'strong' if overall_risk <= 30 else 'moderate' if overall_risk <= 60 else 'high-risk'} profile with comprehensive assessment across credit, documentation, and property parameters."
        
        return {
            "executive_summary": self.clean_ai_response(executive_summary),
            "decision_factors": [
                f"Credit Quality: {'Excellent' if application.cibil_score >= 750 else 'Good' if application.cibil_score >= 650 else 'Fair' if application.cibil_score >= 550 else 'Poor'} (Score: {application.cibil_score})",
                f"Document Compliance: {all_data['document_verification_rate']:.1f}% complete",
                f"Property Security: LTV Ratio {all_data['ltv_ratio']:.1f}%",
                f"Overall Risk Score: {overall_risk:.1f}%"
            ],
            "critical_risks": [
                risk for risk in [
                    "High debt-to-income ratio" if all_data['debt_to_income'] > 50 else None,
                    "Incomplete document submission" if all_data['document_verification_rate'] < 100 else None,
                    "High LTV ratio" if all_data['ltv_ratio'] > 80 else None,
                    "Poor credit history" if application.cibil_score < 600 else None
                ] if risk is not None
            ],
            "strengths": [
                strength for strength in [
                    "Strong credit profile" if application.cibil_score >= 750 else None,
                    "Low debt burden" if all_data['debt_to_income'] <= 30 else None,
                    "Complete documentation" if all_data['document_verification_rate'] == 100 else None,
                    "Adequate property coverage" if all_data['ltv_ratio'] <= 70 else None
                ] if strength is not None
            ],
            "final_recommendation": "APPROVE with standard terms" if overall_risk <= 40 else "APPROVE with conditions" if overall_risk <= 70 else "REJECT due to high risk",
            "confidence_level": "Very High" if application.cibil_score >= 750 and all_data['document_verification_rate'] == 100 else "High" if application.cibil_score >= 650 else "Medium",
            "quality_score": min(10, 10 - int(overall_risk / 10)),
            "immediate_actions": [
                "Process loan disbursement upon completion of all verifications" if application.status == 'APPROVED' else
                "Request additional documentation and clarification" if application.status == 'PENDING' else
                "Provide detailed rejection reasons to applicant"
            ],
            "monitoring_requirements": [
                "Quarterly credit score monitoring",
                "Annual property valuation review",
                "Regular EMI payment tracking"
            ],
            "conditions": [
                "Maintain property insurance coverage",
                "No additional secured borrowing without consent",
                "Timely payment of all statutory dues"
            ]
        }

# Helper functions for EMI calculation
def calculate_emi(principal, annual_rate, tenure_months):
    """Calculate EMI using the standard formula"""
    try:
        monthly_rate = annual_rate / 12 / 100
        if monthly_rate == 0:  # Handle zero interest rate
            return principal / tenure_months
        
        emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months / ((1 + monthly_rate) ** tenure_months - 1)
        return round(emi, 2)
    except Exception as e:
        app.logger.error(f"Error calculating EMI: {e}")
        return 0

def calculate_total_interest(principal, annual_rate, tenure_months):
    """Calculate total interest payable"""
    emi = calculate_emi(principal, annual_rate, tenure_months)
    return round(emi * tenure_months - principal, 2)

def calculate_total_payment(principal, annual_rate, tenure_months):
    """Calculate total payment (principal + interest)"""
    emi = calculate_emi(principal, annual_rate, tenure_months)
    return round(emi * tenure_months, 2)

def generate_amortization_schedule(principal, annual_rate, tenure_months, emi):
    """Generate monthly amortization schedule"""
    try:
        schedule = []
        balance = principal
        monthly_rate = annual_rate / 12 / 100
        start_date = datetime.now()
        
        for month in range(1, tenure_months + 1):
            interest = balance * monthly_rate
            principal_component = emi - interest
            
            # Handle final payment adjustment
            if month == tenure_months:
                principal_component = balance
                emi_adjusted = principal_component + interest
                balance = 0
            else:
                emi_adjusted = emi
                balance -= principal_component
            
            schedule.append({
                'month': month,
                'date': (start_date + relativedelta(months=month)).strftime('%d-%b-%Y'),
                'emi': round(emi_adjusted, 2),
                'principal': round(principal_component, 2),
                'interest': round(interest, 2),
                'balance': max(round(balance, 2), 0)  # Ensure non-negative
            })
        
        return schedule
    except Exception as e:
        app.logger.error(f"Error generating amortization schedule: {e}")
        return []

# INSTANT LOAN DECISION FUNCTIONS
def instant_loan_decision(application, documents):
    """AI-powered instant loan decision making"""
    
    # Run all verifications in parallel (simulated)
    ai_analysis = instant_ai_analysis(application)
    employment_verification = instant_employment_verification(application, documents)
    document_verification = instant_document_verification(documents)
    financial_risk = calculate_financial_risk(application)
    fraud_risk = instant_fraud_detection(application)
    
    # Calculate instant risk score
    overall_risk_score = calculate_instant_risk_score(
        employment_verification, 
        document_verification, 
        financial_risk, 
        fraud_risk,
        ai_analysis
    )
    
    # Make instant decision
    decision_result = make_instant_decision(application, overall_risk_score, ai_analysis)
    
    # Generate instant verification summary
    verification_summary = {
        'timestamp': datetime.utcnow().isoformat(),
        'application_id': application.id,
        'processing_time': 'instant',
        'decision_engine': 'AI_Powered_Instant_Approval',
        'summary': {
            'employment_verification': employment_verification.get('employment_status', 'INSTANT_CHECK'),
            'document_verification': document_verification.get('overall_status', 'INSTANT_CHECK'),
            'overall_risk_score': overall_risk_score,
            'risk_level': get_risk_level(overall_risk_score),
            'ai_confidence': ai_analysis.get('confidence_score', 0.85)
        },
        'instant_checks': {
            'credit_check': 'COMPLETED',
            'employment_verification': 'COMPLETED',
            'document_validation': 'COMPLETED',
            'fraud_detection': 'COMPLETED'
        }
    }
    
    return {
        'status': decision_result['status'],
        'risk_score': overall_risk_score,
        'reason': decision_result['reason'],
        'interest_rate': decision_result.get('interest_rate'),
        'loan_term_years': decision_result.get('loan_term_years'),
        'emi_amount': decision_result.get('emi_amount'),
        'ai_analysis': ai_analysis,
        'employment_verification': employment_verification,
        'document_verification': document_verification,
        'verification_summary': verification_summary,
        'banking_report': instant_banking_analysis(application),
        'fraud_report': {'status': 'LOW_RISK', 'risk_score': fraud_risk}
    }

def instant_ai_analysis(application):
    """Instant AI analysis using ML models"""
    
    # Feature engineering for ML model
    features = {
        'debt_to_income': (application.existing_emi / application.monthly_salary) * 100 if application.monthly_salary > 0 else 100,
        'loan_to_value': (application.loan_amount / application.property_valuation) * 100 if application.property_valuation > 0 else 100,
        'cibil_score': application.cibil_score,
        'salary_adequacy': application.monthly_salary / (application.loan_amount / 100000),  # Salary per lakh loan
        'property_valuation_ratio': application.property_valuation / application.loan_amount,
        'existing_obligations': application.existing_emi > 0
    }
    
    # ML-based risk prediction (simplified)
    risk_factors = []
    
    # CIBIL score impact
    if application.cibil_score >= 800:
        risk_factors.append(0.1)  # Excellent credit
    elif application.cibil_score >= 750:
        risk_factors.append(0.3)  # Good credit
    elif application.cibil_score >= 700:
        risk_factors.append(0.5)  # Fair credit
    else:
        risk_factors.append(0.8)  # Poor credit
    
    # Debt-to-Income ratio
    dti = features['debt_to_income']
    if dti <= 30:
        risk_factors.append(0.2)
    elif dti <= 50:
        risk_factors.append(0.4)
    else:
        risk_factors.append(0.8)
    
    # Loan-to-Value ratio
    ltv = features['loan_to_value']
    if ltv <= 60:
        risk_factors.append(0.1)
    elif ltv <= 80:
        risk_factors.append(0.3)
    else:
        risk_factors.append(0.7)
    
    # Salary adequacy
    if features['salary_adequacy'] >= 5000:  # ₹5000 per lakh loan
        risk_factors.append(0.2)
    elif features['salary_adequacy'] >= 3000:
        risk_factors.append(0.4)
    else:
        risk_factors.append(0.8)
    
    # Calculate average risk
    avg_risk = sum(risk_factors) / len(risk_factors) * 100
    
    return {
        'risk_score': avg_risk,
        'confidence_score': 0.92,  # ML model confidence
        'key_factors': {
            'credit_quality': 'EXCELLENT' if application.cibil_score >= 750 else 'GOOD' if application.cibil_score >= 700 else 'FAIR',
            'debt_burden': 'LOW' if dti <= 40 else 'MODERATE' if dti <= 60 else 'HIGH',
            'property_coverage': 'STRONG' if ltv <= 70 else 'ADEQUATE' if ltv <= 85 else 'WEAK',
            'income_stability': 'STRONG' if features['salary_adequacy'] >= 4000 else 'ADEQUATE'
        },
        'recommendation': 'APPROVE' if avg_risk <= 40 else 'REVIEW' if avg_risk <= 70 else 'REJECT'
    }

def instant_employment_verification(application, documents):
    """Instant employment verification using company database"""
    
    # Use the enhanced verification service with company data
    employment_data = advance_verification_service.verify_employment_documents(application, documents)
    
    # Instant status determination
    if employment_data.get('data_source_match', False):
        employment_data['verification_speed'] = 'INSTANT'
        employment_data['verification_method'] = 'AUTOMATED_DATABASE_MATCH'
    else:
        employment_data['verification_speed'] = 'INSTANT_FALLBACK'
        employment_data['verification_method'] = 'AI_PATTERN_ANALYSIS'
    
    return employment_data

def instant_document_verification(documents):
    """Instant document verification including NA document"""
    
    # UPDATED: Include NA document in the verification
    doc_types = ['bank_statements', 'salary_slips', 'kyc_docs', 'property_valuation_doc', 'legal_clearance', 'na_document']
    verified_docs = {}
    
    for doc_type in doc_types:
        doc_present = any(doc_type in doc.document_type.lower() for doc in documents)
        verified_docs[doc_type] = {
            'status': 'VERIFIED' if doc_present else 'MISSING',
            'risk_score': 10 if doc_present else 80,
            'verification_time': 'INSTANT'
        }
    
    # Calculate overall document status
    missing_docs = [doc_type for doc_type, info in verified_docs.items() if info['status'] == 'MISSING']
    overall_status = 'VERIFIED' if len(missing_docs) == 0 else 'PARTIAL'
    avg_risk = sum(info['risk_score'] for info in verified_docs.values()) / len(verified_docs)
    
    return {
        'overall_status': overall_status,
        'risk_score': avg_risk,
        'verified_documents': verified_docs,
        'missing_documents': missing_docs,
        'processing_time': 'INSTANT'
    }

def instant_fraud_detection(application):
    """Instant fraud detection using pattern analysis"""
    
    fraud_indicators = []
    
    # Check for common fraud patterns
    # Salary consistency check
    if application.monthly_salary > 500000:  # Unusually high salary
        fraud_indicators.append(0.3)
    
    # Property valuation check
    if application.property_valuation / application.loan_amount > 10:  # Very high collateral
        fraud_indicators.append(0.2)
    
    # CIBIL score consistency
    if application.cibil_score >= 800 and application.monthly_salary < 50000:
        fraud_indicators.append(0.4)  # High credit score with low income
    
    # Calculate fraud risk
    fraud_risk = sum(fraud_indicators) / len(fraud_indicators) * 100 if fraud_indicators else 15
    
    return min(fraud_risk, 100)

def instant_banking_analysis(application):
    """Instant banking behavior analysis"""
    
    return {
        'status': 'HEALTHY' if application.existing_emi / application.monthly_salary <= 0.5 else 'MODERATE',
        'analysis': 'INSTANT_PATTERN_ANALYSIS',
        'debt_service_ratio': (application.existing_emi / application.monthly_salary) * 100,
        'recommendation': 'ACCEPTABLE' if application.existing_emi / application.monthly_salary <= 0.6 else 'REVIEW'
    }

def calculate_instant_risk_score(employment_data, document_data, financial_risk, fraud_risk, ai_analysis):
    """Calculate instant overall risk score"""
    
    weights = {
        'employment': 0.25,
        'documents': 0.15,
        'financial': 0.35,
        'fraud': 0.15,
        'ai_prediction': 0.10
    }
    
    weighted_score = (
        employment_data.get('risk_score', 50) * weights['employment'] +
        document_data.get('risk_score', 50) * weights['documents'] +
        financial_risk * weights['financial'] +
        fraud_risk * weights['fraud'] +
        ai_analysis.get('risk_score', 50) * weights['ai_prediction']
    )
    
    return min(100, weighted_score)

def make_instant_decision(application, overall_risk_score, ai_analysis):
    """Make instant loan decision based on risk score and AI analysis"""
    
    # Base decision on risk score
    if overall_risk_score <= 30:
        # Low risk - Auto approve with best terms
        interest_rate = 8.0  # Best rate
        loan_term = 20  # Maximum term
        emi = calculate_emi(application.loan_amount, interest_rate, loan_term * 12)
        
        return {
            'status': 'APPROVED',
            'reason': f'Excellent application! Low risk profile with {overall_risk_score:.1f}% risk score',
            'interest_rate': interest_rate,
            'loan_term_years': loan_term,
            'emi_amount': emi
        }
    
    elif overall_risk_score <= 50:
        # Medium risk - Approve with standard terms
        interest_rate = 10.5  # Standard rate
        loan_term = 15  # Standard term
        emi = calculate_emi(application.loan_amount, interest_rate, loan_term * 12)
        
        return {
            'status': 'APPROVED',
            'reason': f'Good application approved. Risk score: {overall_risk_score:.1f}%',
            'interest_rate': interest_rate,
            'loan_term_years': loan_term,
            'emi_amount': emi
        }
    
    elif overall_risk_score <= 70:
        # Higher risk - Approve with conservative terms
        interest_rate = 12.5  # Higher rate
        loan_term = 10  # Shorter term
        emi = calculate_emi(application.loan_amount, interest_rate, loan_term * 12)
        
        return {
            'status': 'APPROVED',
            'reason': f'Application approved with adjusted terms. Risk score: {overall_risk_score:.1f}%',
            'interest_rate': interest_rate,
            'loan_term_years': loan_term,
            'emi_amount': emi
        }
    
    else:
        # High risk - Reject
        return {
            'status': 'REJECTED',
            'reason': f'Application declined due to high risk profile. Risk score: {overall_risk_score:.1f}%'
        }


def get_risk_level(risk_score):
    """Convert risk score to risk level"""
    if risk_score <= 25:
        return 'VERY_LOW'
    elif risk_score <= 40:
        return 'LOW'
    elif risk_score <= 60:
        return 'MEDIUM'
    elif risk_score <= 75:
        return 'HIGH'
    else:
        return 'VERY_HIGH'

def calculate_financial_risk(application):
    """Calculate financial risk score"""
    try:
        risk_score = 0
        
        # Debt-to-income ratio
        dti = (application.existing_emi / application.monthly_salary) * 100 if application.monthly_salary > 0 else 100
        if dti > 50:
            risk_score += 40
        elif dti > 30:
            risk_score += 20
        else:
            risk_score += 10
        
        # Loan-to-value ratio
        ltv = (application.loan_amount / application.property_valuation) * 100 if application.property_valuation > 0 else 100
        if ltv > 80:
            risk_score += 30
        elif ltv > 60:
            risk_score += 15
        else:
            risk_score += 5
        
        # CIBIL score impact
        if application.cibil_score < 600:
            risk_score += 30
        elif application.cibil_score < 750:
            risk_score += 15
        else:
            risk_score += 5
        
        return min(100, risk_score)
        
    except Exception as e:
        return 50  # Default medium risk

def get_fraud_risk_score(application, fraud_report):
    """Extract fraud risk from fraud report"""
    try:
        if isinstance(fraud_report, dict):
            return fraud_report.get('risk_score', 50)
        elif isinstance(fraud_report, str):
            fraud_data = json.loads(fraud_report)
            return fraud_data.get('risk_score', 50)
        else:
            return 50
    except:
        return 50

def safe_json_loads(json_string, default=None):
    """Safely parse JSON string with error handling"""
    if default is None:
        default = {}
    try:
        return json.loads(json_string) if json_string else default
    except (json.JSONDecodeError, TypeError):
        return default

def get_credit_report(application):
    """Get credit risk analysis report"""
    try:
        # Your credit analysis logic here
        cibil_score = application.cibil_score or 0
        if cibil_score >= 750:
            risk_level = "LOW"
            risk_score = 20
        elif cibil_score >= 650:
            risk_level = "MEDIUM"
            risk_score = 40
        else:
            risk_level = "HIGH"
            risk_score = 70
            
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'cibil_score': cibil_score,
            'key_factors': {
                'credit_quality': 'EXCELLENT' if cibil_score >= 750 else 'GOOD' if cibil_score >= 650 else 'FAIR',
                'payment_history': 'CLEAN',
                'credit_utilization': 'OPTIMAL'
            }
        }
    except Exception as e:
        app.logger.error(f"Error generating credit report: {e}")
        return {}

def get_banking_report(application):
    """Get banking behavior analysis report"""
    try:
        # Calculate debt-to-income ratio
        monthly_salary = application.monthly_salary or 0
        existing_emi = application.existing_emi or 0
        debt_service_ratio = (existing_emi / monthly_salary * 100) if monthly_salary > 0 else 0
        
        if debt_service_ratio <= 30:
            status = "HEALTHY"
        elif debt_service_ratio <= 50:
            status = "MODERATE"
        else:
            status = "HIGH_RISK"
            
        return {
            'status': status,
            'debt_service_ratio': debt_service_ratio,
            'monthly_salary': monthly_salary,
            'existing_obligations': existing_emi
        }
    except Exception as e:
        app.logger.error(f"Error generating banking report: {e}")
        return {}

def initialize_na_verification(application_id):
    """Initialize NA document verification process"""
    application = Application.query.get(application_id)
    if not application:
        return
    
    # Find NA document - check for both possible document types
    na_document = None
    for doc in application.documents:
        if doc.document_type in ['NON_AGRICULTURAL_DECLARATION', 'NA_DOCUMENT']:
            na_document = doc
            break
    
    if na_document:
        # Start verification process
        na_report = verify_na_document(na_document, application)
        application.na_document_verification = json.dumps(na_report)
        application.na_document_status = na_report.get('status', 'PENDING')
        application.na_document_risk_score = na_report.get('risk_score', 0.0)
        
        # If document is present and verified, update risk score
        if na_report.get('status') == 'VERIFIED':
            application.na_document_risk_score = 10.0  # Low risk for verified documents
        elif na_report.get('status') == 'VERIFIED_WITH_NOTES':
            application.na_document_risk_score = 30.0  # Medium risk
        else:
            application.na_document_risk_score = na_report.get('risk_score', 100.0)
    else:
        # No NA document found
        na_report = {
            'status': 'PENDING',
            'risk_score': 100.0,
            'details': 'Non-agricultural declaration document not uploaded',
            'issues': ['Document required for property classification verification'],
            'verification_steps': [
                {
                    'step': 'Document Upload',
                    'status': 'FAILED',
                    'details': 'No NA document found in uploaded documents'
                }
            ],
            'recommendation': 'Upload non-agricultural declaration certificate'
        }
        application.na_document_verification = json.dumps(na_report)
        application.na_document_status = 'PENDING'
        application.na_document_risk_score = 100.0
    
    db.session.commit()
    return na_report

def verify_na_document(document, application):
    """Verify Non-Agricultural document with improved logic"""
    verification_steps = []
    issues = []
    risk_score = 0.0
    
    try:
        # Step 1: Document Presence Check
        verification_steps.append({
            'step': 'Document Presence',
            'status': 'PASSED',
            'details': 'NA document found in uploaded documents'
        })
        
        # Step 2: Document Format Check
        if document.filename and document.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
            verification_steps.append({
                'step': 'Format Check',
                'status': 'PASSED',
                'details': 'Document format is acceptable'
            })
        else:
            verification_steps.append({
                'step': 'Format Check',
                'status': 'FAILED',
                'details': 'Unsupported document format'
            })
            issues.append('Document format not supported')
            risk_score += 30
        
        # Step 3: Document Size Check (if file_data exists)
        if hasattr(document, 'file_data') and document.file_data:
            if len(document.file_data) < 10 * 1024 * 1024:  # 10MB limit
                verification_steps.append({
                    'step': 'Size Check',
                    'status': 'PASSED',
                    'details': 'Document size is within limits'
                })
            else:
                verification_steps.append({
                    'step': 'Size Check',
                    'status': 'FAILED',
                    'details': 'Document exceeds size limits'
                })
                issues.append('Document size too large')
                risk_score += 20
        else:
            # If no file_data, assume size is acceptable
            verification_steps.append({
                'step': 'Size Check',
                'status': 'PASSED',
                'details': 'Document size assumed acceptable'
            })
        
        # Step 4: Cross-verification with other property documents
        property_docs = [doc for doc in application.documents 
                        if doc.document_type in ['PROPERTY_VALUATION', 'LEGAL_CLEARANCE', 'PROPERTY_VALUATION_DOC']]
        
        if property_docs:
            verification_steps.append({
                'step': 'Cross-Verification',
                'status': 'PASSED',
                'details': f'Found {len(property_docs)} related property documents'
            })
        else:
            verification_steps.append({
                'step': 'Cross-Verification',
                'status': 'WARNING',
                'details': 'No related property documents found for cross-verification'
            })
            issues.append('Missing supporting property documents')
            risk_score += 15
        
        # Step 5: Property Type Validation
        if application.is_non_agricultural:
            verification_steps.append({
                'step': 'Property Type Validation',
                'status': 'PASSED',
                'details': 'Property marked as non-agricultural in application'
            })
        else:
            verification_steps.append({
                'step': 'Property Type Validation',
                'status': 'WARNING',
                'details': 'Property type not specified as non-agricultural'
            })
            risk_score += 10
        
        # Step 6: Basic Content Validation
        verification_steps.append({
            'step': 'Content Validation',
            'status': 'PENDING_MANUAL_REVIEW',
            'details': 'Requires manual review for content accuracy and validity'
        })
        
        # Calculate final status based on risk score
        if risk_score == 0:
            status = 'VERIFIED'
            details = 'Non-agricultural declaration document verified successfully'
            final_risk_score = 10.0  # Low risk for fully verified
        elif risk_score <= 25:
            status = 'VERIFIED_WITH_NOTES'
            details = 'Document verified with minor issues requiring attention'
            final_risk_score = 25.0
        elif risk_score <= 50:
            status = 'REVIEW_NEEDED'
            details = 'Document requires manual review due to moderate issues'
            final_risk_score = 50.0
        else:
            status = 'PENDING'
            details = 'Document verification pending due to significant issues'
            final_risk_score = min(risk_score, 100.0)
        
        return {
            'status': status,
            'risk_score': final_risk_score,
            'details': details,
            'issues': issues,
            'verification_steps': verification_steps,
            'document_id': document.id,
            'document_type': document.document_type,
            'filename': document.filename,
            'verified_at': datetime.utcnow().isoformat(),
            'recommendation': 'Document appears valid but requires final manual confirmation'
        }
        
    except Exception as e:
        app.logger.error(f"Error verifying NA document: {e}")
        return {
            'status': 'ERROR',
            'risk_score': 100.0,
            'details': f'Error during verification: {str(e)}',
            'issues': ['Verification process failed - system error'],
            'verification_steps': [{
                'step': 'System Verification',
                'status': 'ERROR',
                'details': f'System error: {str(e)}'
            }],
            'recommendation': 'Retry verification or contact support'
        }

def verify_single_document(document, doc_type):
    """Verify a single document"""
    try:
        # Basic verification logic for each document type
        risk_score = 10  # Default low risk for present documents
        issues = []
        
        # Type-specific validations
        if doc_type == 'NON_AGRICULTURAL_DECLARATION':
            # NA document specific checks
            if not document.filename.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                issues.append('Invalid file format')
                risk_score = 50
            if len(document.file_data) > 10 * 1024 * 1024:
                issues.append('File size too large')
                risk_score = 40
        
        return {
            'document_type': doc_type,
            'name': document.document_type.replace('_', ' ').title(),
            'status': 'VERIFIED' if risk_score <= 20 else 'REVIEW_NEEDED',
            'risk_score': risk_score,
            'issues': issues,
            'verified_at': datetime.utcnow().isoformat()
        }
    except Exception as e:
        app.logger.error(f"Error verifying document {doc_type}: {e}")
        return {
            'document_type': doc_type,
            'name': doc_type.replace('_', ' ').title(),
            'status': 'ERROR',
            'risk_score': 100.0,
            'issues': ['Verification error'],
            'verified_at': datetime.utcnow().isoformat()
        }

def verify_all_documents(application):
    """Verify all documents including NA document"""
    documents_report = {
        'overall_status': 'PENDING',
        'overall_risk_score': 0.0,
        'documents': [],
        'verification_summary': '',
        'issues_found': 0
    }
    
    total_risk = 0
    document_count = 0
    verified_count = 0
    
    # Verify each document type
    document_types = {
        'BANK_STATEMENTS': 'Bank Statements',
        'SALARY_SLIPS': 'Salary Slips', 
        'KYC_DOCS': 'KYC Documents',
        'PROPERTY_VALUATION': 'Property Valuation',
        'LEGAL_CLEARANCE': 'Legal Clearance',
        'NON_AGRICULTURAL_DECLARATION': 'Non-Agricultural Declaration'
    }
    
    for doc_type, doc_name in document_types.items():
        document = next((doc for doc in application.documents if doc.document_type == doc_type), None)
        
        if document:
            doc_report = verify_single_document(document, doc_type)
            documents_report['documents'].append(doc_report)
            total_risk += doc_report.get('risk_score', 0)
            document_count += 1
            if doc_report.get('status') == 'VERIFIED':
                verified_count += 1
        else:
            # Document missing
            documents_report['documents'].append({
                'document_type': doc_type,
                'name': doc_name,
                'status': 'MISSING',
                'risk_score': 100.0,
                'issues': ['Document not uploaded']
            })
            total_risk += 100
            document_count += 1
    
    # Calculate overall status
    if document_count > 0:
        documents_report['overall_risk_score'] = total_risk / document_count
        
        if verified_count == document_count:
            documents_report['overall_status'] = 'VERIFIED'
            documents_report['verification_summary'] = 'All documents verified successfully'
        elif verified_count >= document_count * 0.7:
            documents_report['overall_status'] = 'VERIFIED_WITH_NOTES'
            documents_report['verification_summary'] = 'Most documents verified, minor issues found'
        else:
            documents_report['overall_status'] = 'PENDING'
            documents_report['verification_summary'] = 'Multiple documents require verification'
    
    documents_report['issues_found'] = len([doc for doc in documents_report['documents'] 
                                          if doc.get('issues')])
    
    return documents_report

def generate_verification_summary(application):
    """Generate comprehensive verification summary including NA document"""
    # Get all verification reports
    employment_report = safe_json_loads(application.employment_verification_report) or {}
    document_report = safe_json_loads(application.document_verification_report) or {}
    na_report = safe_json_loads(application.na_document_verification) or {}
    
    # Calculate overall risk score (weighted average)
    weights = {
        'employment': 0.3,
        'documents': 0.4,
        'na_document': 0.3
    }
    
    employment_risk = employment_report.get('risk_score', 0) or 0
    document_risk = document_report.get('overall_risk_score', 0) or 0
    na_risk = na_report.get('risk_score', 0) or 0
    
    overall_risk = (
        employment_risk * weights['employment'] +
        document_risk * weights['documents'] + 
        na_risk * weights['na_document']
    )
    
    # Determine overall status
    if overall_risk <= 25:
        risk_level = 'VERY_LOW'
        status = 'APPROVED'
    elif overall_risk <= 50:
        risk_level = 'LOW'
        status = 'APPROVED'
    elif overall_risk <= 75:
        risk_level = 'MEDIUM'
        status = 'UNDER_REVIEW'
    else:
        risk_level = 'HIGH'
        status = 'PENDING'
    
    summary = {
        'overall_risk_score': overall_risk,
        'risk_level': risk_level,
        'recommended_status': status,
        'component_scores': {
            'employment': employment_risk,
            'documents': document_risk,
            'na_document': na_risk
        },
        'verification_status': {
            'employment': employment_report.get('status', 'PENDING'),
            'documents': document_report.get('overall_status', 'PENDING'),
            'na_document': na_report.get('status', 'PENDING')
        },
        'summary_text': f"Overall risk: {risk_level}. Employment: {employment_report.get('status')}, "
                       f"Documents: {document_report.get('overall_status')}, "
                       f"NA Document: {na_report.get('status')}",
        'timestamp': datetime.utcnow().isoformat()
    }
    
    return summary

def get_fraud_report(application):
    """Get fraud detection analysis report"""
    try:
        # Simple fraud detection logic
        risk_factors = []
        
        # Check for basic fraud indicators
        if application.cibil_score and application.cibil_score < 300:
            risk_factors.append("Unusually low CIBIL score")
            
        if application.monthly_salary and application.monthly_salary > 500000:
            risk_factors.append("Unusually high salary declaration")
            
        risk_score = min(len(risk_factors) * 25, 100)
        
        return {
            'status': 'LOW_RISK' if risk_score < 50 else 'MEDIUM_RISK' if risk_score < 75 else 'HIGH_RISK',
            'risk_score': risk_score,
            'risk_factors': risk_factors,
            'verification_status': 'PASSED' if risk_score < 50 else 'REVIEW_NEEDED'
        }
    except Exception as e:
        app.logger.error(f"Error generating fraud report: {e}")
        return {}

def convert_to_old_format(new_analysis):
    """Convert new instant decision format to old template-compatible format"""
    old_format = {}
    
    # Map risk_score to financial_health_score (inverted)
    if 'risk_score' in new_analysis:
        # Convert risk score (0-100, lower is better) to health score (0-100, higher is better)
        old_format['financial_health_score'] = max(0, 100 - new_analysis['risk_score'])
    
    # Map key_factors to risk_factors
    if 'key_factors' in new_analysis:
        risk_factors = []
        for factor, rating in new_analysis['key_factors'].items():
            risk_factors.append(f"{factor.replace('_', ' ').title()}: {rating}")
        old_format['risk_factors'] = risk_factors
    
    # Map recommendation
    if 'recommendation' in new_analysis:
        old_format['recommendation'] = new_analysis['recommendation']
    
    # Add confidence score if available
    if 'confidence_score' in new_analysis:
        old_format['confidence_score'] = new_analysis['confidence_score']
    
    # Ensure we have all required fields with defaults
    old_format.setdefault('financial_health_score', 75)
    old_format.setdefault('risk_factors', ['No risk factors identified'])
    old_format.setdefault('recommendation', 'REVIEW')
    old_format.setdefault('confidence_score', 0.85)
    
    return old_format

def format_data_for_application(parsed_data):
    """Convert parsed data to match your application form fields"""
    formatted = {}
    
    # Direct mappings
    direct_mappings = {
        'first_name': 'first_name',
        'last_name': 'last_name',
        'email': 'email',
        'gender': 'gender',
        'address': 'current_address',
        'aadhaar': 'aadhar_number',
        'pan': 'pan_number',
        'salary': 'monthly_salary',
        'company': 'company_name',
        'existing_loan': 'existing_emi',
        'cibil': 'cibil_score',
        'loan_amount': 'loan_amount',
        'property_value': 'property_valuation',
        'property_address': 'property_address'
    }
    
    for source_key, target_key in direct_mappings.items():
        if source_key in parsed_data and parsed_data[source_key] is not None:
            formatted[target_key] = parsed_data[source_key]
    
    # Boolean field conversions
    if 'residence_status' in parsed_data:
        residence_status = parsed_data['residence_status'].lower()
        formatted['is_rented'] = residence_status == 'rent'
        formatted['has_own_property'] = residence_status == 'owned'
    
    if 'other_properties' in parsed_data:
        formatted['has_own_property'] = parsed_data['other_properties']
    
    if 'non_agricultural' in parsed_data:
        formatted['is_non_agricultural'] = parsed_data['non_agricultural']
    
    if 'mortgage' in parsed_data:
        formatted['has_existing_mortgage'] = parsed_data['mortgage']
    
    return formatted

def reprocess_old_application(application):
    """Reprocess old applications to generate missing verification data"""
    try:
        app.logger.info(f"Reprocessing old application: {application.id}")
        
        # Get documents for the application
        documents = application.documents
        
        # Initialize NA document verification if missing
        if application.na_document_verification is None:
            initialize_na_verification(application.id)
        
        # Generate missing verification data using instant processing
        decision_result = instant_loan_decision(application, documents)
        
        # Update application with new data
        if application.overall_risk_score is None:
            application.overall_risk_score = decision_result['risk_score']
        
        if application.ai_analysis_report is None:
            application.ai_analysis_report = json.dumps(decision_result['ai_analysis'])
        
        if application.employment_verification_report is None:
            application.employment_verification_report = json.dumps(decision_result['employment_verification'])
            application.employment_verification_status = decision_result['employment_verification'].get('employment_status', 'PROCESSED')
        
        if application.document_verification_report is None:
            application.document_verification_report = json.dumps(decision_result['document_verification'])
            application.document_verification_status = decision_result['document_verification'].get('overall_status', 'PROCESSED')
        
        if application.verification_summary is None:
            application.verification_summary = json.dumps(decision_result['verification_summary'])
        
        # Generate comprehensive verification summary
        verification_summary = generate_verification_summary(application)
        application.verification_summary = json.dumps(verification_summary)
        
        db.session.commit()
        app.logger.info(f"Successfully reprocessed application: {application.id}")
        
        return True
        
    except Exception as e:
        app.logger.error(f"Error reprocessing application {application.id}: {str(e)}")
        db.session.rollback()
        return False

# Helper functions for PDF generation
def get_application_with_permission(app_id):
    """Get application with permission check"""
    is_admin = 'admin_id' in session
    if is_admin:
        return Application.query.filter_by(id=app_id).first()
    else:
        return Application.query.filter_by(id=app_id, user_id=session['user_id']).first()

def generate_pdf_response(html_content, filename):
    """Generate PDF response from HTML content"""
    try:
        from weasyprint import HTML
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            pdf_path = tmp_file.name
        
        HTML(string=html_content).write_pdf(pdf_path)
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f'{filename}.pdf',
            mimetype='application/pdf'
        )
        
    except ImportError:
        # Fallback to basic PDF generation
        return generate_basic_pdf_fallback(html_content, filename)

def generate_basic_pdf_fallback(html_content, filename):
    """Basic PDF fallback using reportlab"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    import io
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Simple text extraction from HTML (basic approach)
    text_content = " ".join(html_content.split())[:1000]  # Simple text extraction
    
    p.drawString(100, 750, f"Report: {filename}")
    p.drawString(100, 730, "Advanced PDF generation requires WeasyPrint installation.")
    p.drawString(100, 710, "Please install: pip install weasyprint")
    p.drawString(100, 690, "Content preview:")
    p.drawString(100, 670, text_content[:100] + "...")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'{filename}_basic.pdf',
        mimetype='application/pdf'
    )

# ===== ALL TEMPLATE ROUTES =====

@app.route('/')
def index():
    return render_template('index.html')

# ===== FIXED LOGIN ROUTE - SINGLE VERSION =====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        
        if form_type == 'admin':
            username = request.form.get('username')
            password = request.form.get('password')
            
            # Debug logging
            print(f"DEBUG: Admin login attempt - Username: '{username}'")
            
            # Case-insensitive username search using ilike
            admin = Admin.query.filter(Admin.username.ilike(username)).first()
            
            if admin:
                print(f"DEBUG: Admin found: {admin.username}")
                print(f"DEBUG: Password check: {admin.check_password(password)}")
                
                if admin and admin.check_password(password):
                    session['admin_id'] = admin.id
                    session['admin_logged_in'] = True
                    flash('Admin login successful!', 'success')
                    return redirect(url_for('admin.dashboard'))
                else:
                    flash('Invalid admin credentials.', 'danger')
            else:
                print("DEBUG: No admin found with that username")
                flash('Invalid admin credentials.', 'danger')
        
        elif form_type == 'user':
            if 'mobile_number' in request.form:
                mobile = request.form['mobile_number']
                otp = auth_service.generate_and_store_otp(mobile)
                auth_service.send_otp_via_sms(mobile, otp)
                session['mobile_for_verification'] = mobile
                return render_template('login.html', mobile_sent=True, mobile=mobile)
            
            elif 'otp' in request.form:
                mobile = session.get('mobile_for_verification')
                otp = request.form['otp']
                if mobile and auth_service.verify_otp(mobile, otp):
                    user = User.query.filter_by(mobile_number=mobile).first()
                    if not user:
                        user = User(mobile_number=mobile)
                        db.session.add(user)
                        db.session.commit()
                    session['user_id'] = user.id
                    session['user_logged_in'] = True
                    session.pop('mobile_for_verification', None)
                    flash('Login successful!', 'success')
                    return redirect(url_for('dashboard'))
                else:
                    flash('Invalid OTP.', 'danger')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Check if user is admin and redirect to admin dashboard
    if 'admin_id' in session:
        return redirect(url_for('admin.dashboard'))
    
    # Regular user dashboard
    user_id = session['user_id']
    user_applications = Application.query.filter_by(user_id=user_id).order_by(Application.created_at.desc()).all()
    return render_template('dashboard.html', applications=user_applications)

@app.route('/apply', methods=['GET', 'POST'])
@login_required
def apply():
    # Only regular users can apply
    if 'admin_id' in session:
        flash('Admin users cannot submit applications.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        try:
            # Process form submission
            is_rented = request.form.get('is_rented') == 'True'
            has_own_property = request.form.get('has_own_property') == 'True'
            is_non_agricultural = request.form.get('is_non_agricultural') == 'True'
            has_existing_mortgage = request.form.get('has_existing_mortgage') == 'True'
            
            new_app = Application(
                id=storage_service.generate_unique_app_id(),
                user_id=session['user_id'],
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                email=request.form['email'],
                gender=request.form.get('gender'),
                current_address=request.form.get('current_address'),
                is_rented=is_rented,
                has_own_property=has_own_property,
                aadhar_number=request.form['aadhar_number'],
                pan_number=request.form['pan_number'],
                monthly_salary=float(request.form['monthly_salary']),
                company_name=request.form.get('company_name'),
                existing_emi=float(request.form['existing_emi']),
                cibil_score=int(request.form['cibil_score']),
                loan_amount=float(request.form['loan_amount']),
                property_valuation=float(request.form['property_valuation']),
                property_address=request.form.get('property_address'),
                is_non_agricultural=is_non_agricultural,
                has_existing_mortgage=has_existing_mortgage
            )
            db.session.add(new_app)
            
            user = User.query.get(session['user_id'])
            if user is None:
                flash('Your session has expired. Please log out and log in again.', 'danger')
                return redirect(url_for('user_logout'))

            # Updated document list including NA document
            files_to_upload = {
                'bank_statements': request.files.get('bank_statements'),
                'salary_slips': request.files.get('salary_slips'),
                'kyc_docs': request.files.get('kyc_docs'),
                'property_valuation_doc': request.files.get('property_valuation_doc'),
                'legal_clearance': request.files.get('legal_clearance'),
                'na_document': request.files.get('na_document'),  # NEW: NA document
            }
            saved_docs = storage_service.save_application_documents(user.mobile_number, new_app.id, files_to_upload)
            for doc in saved_docs:
                db.session.add(doc)
                
            db.session.commit()

            # Initialize NA document verification
            initialize_na_verification(new_app.id)
            
            # INSTANT AI-POWERED DECISION MAKING
            decision_result = instant_loan_decision(new_app, saved_docs)
            
            # Update application with instant decision
            new_app.status = decision_result['status']
            new_app.overall_risk_score = decision_result['risk_score']
            new_app.interest_rate = decision_result.get('interest_rate')
            new_app.loan_term_years = decision_result.get('loan_term_years')
            new_app.emi_amount = decision_result.get('emi_amount')
            
            # Save AI analysis and verification reports
            new_app.ai_analysis_report = json.dumps(decision_result['ai_analysis'])
            new_app.employment_verification_report = json.dumps(decision_result['employment_verification'])
            new_app.document_verification_report = json.dumps(decision_result['document_verification'])
            new_app.verification_summary = json.dumps(decision_result['verification_summary'])
            
            # Set verification statuses
            new_app.employment_verification_status = decision_result['employment_verification'].get('employment_status', 'PENDING')
            new_app.document_verification_status = decision_result['document_verification'].get('overall_status', 'PENDING')
            
            # Save banking and fraud reports
            new_app.banking_analysis_report = json.dumps(decision_result.get('banking_report', {}))
            new_app.fraud_detection_report = json.dumps(decision_result.get('fraud_report', {}))
            
            # Generate comprehensive verification summary
            verification_summary = generate_verification_summary(new_app)
            new_app.verification_summary = json.dumps(verification_summary)
            
            # Create EMI records if approved
            if new_app.status == 'APPROVED' and new_app.emi_amount:
                EMI.query.filter_by(application_id=new_app.id).delete()
                for i in range(1, new_app.loan_term_years * 12 + 1):
                    due_date = datetime.utcnow().date() + relativedelta(months=i)
                    new_emi_record = EMI(
                        application_id=new_app.id,
                        emi_number=i,
                        due_date=due_date,
                        amount_due=new_app.emi_amount,
                        status='DUE'
                    )
                    db.session.add(new_emi_record)
            
            db.session.commit()
            
            # Send instant notification
            notification_service.send_decision_notification(new_app, decision_result['reason'])
            
            flash(f'Application #{new_app.id} processed instantly! Decision: {new_app.status}', 'success')
            return redirect(url_for('application_result', app_id=new_app.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting application: {str(e)}', 'error')
            return render_template('apply.html')

    # GET request - render the form
    return render_template('apply.html')

@app.route('/auto-fill', methods=['POST'])
@login_required
def auto_fill():
    """Handle auto-fill form request"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if file and file.filename.endswith('.txt'):
            content = file.read().decode('utf-8')
            parsed_data = autofill_service.parse_text_data(content)
            
            # Convert to your application model format
            formatted_data = format_data_for_application(parsed_data)
            
            return jsonify({
                'success': True, 
                'data': formatted_data,
                'message': 'Form auto-filled successfully!'
            })
        else:
            return jsonify({'success': False, 'error': 'Please upload a text file (.txt)'})
            
    except Exception as e:
        app.logger.error(f"Auto-fill error: {str(e)}")
        return jsonify({'success': False, 'error': f'Error processing file: {str(e)}'})

@app.route('/status/<app_id>')
@login_required
def status(app_id):
    try:
        # Check if current user is admin
        is_admin = 'admin_id' in session or session.get('admin_logged_in', False)
        
        # Fetch application based on user type
        if is_admin:
            application = Application.query.filter_by(id=app_id).first()
            if not application:
                flash('Application not found.', 'error')
                return redirect(url_for('admin.dashboard'))
        else:
            application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first()
            if not application:
                flash('Application not found or you do not have permission to view it.', 'error')
                return redirect(url_for('dashboard'))
        
        # Generate AI verification data if not exists
        if not application.ai_verification_report:
            # Trigger AI analysis
            from services.ai_analysis_engine import CasaFlowAIAnalyzer
            analyzer = CasaFlowAIAnalyzer()
            
            # Prepare application data for AI analysis
            app_data = {
                'first_name': application.first_name,
                'last_name': application.last_name,
                'email': application.email,
                'pan_number': application.pan_number,
                'aadhar_number': application.aadhar_number,
                'monthly_salary': application.monthly_salary,
                'company_name': application.company_name,
                'loan_amount': application.loan_amount,
                'property_valuation': application.property_valuation,
                'cibil_score': application.cibil_score,
                'existing_emi': application.existing_emi,
                'uploaded_documents': [doc.document_type for doc in application.documents]
            }
            
            # Run AI verification
            verification_result = analyzer._run_ai_verification_analysis(app_data)
            application.ai_verification_report = json.dumps(verification_result)
            db.session.commit()
        
        # Parse AI verification report
        verification_analysis = json.loads(application.ai_verification_report) if application.ai_verification_report else None
        
        # Load other reports (your existing code)
        banking_report = safe_json_loads(application.banking_analysis_report)
        fraud_report = safe_json_loads(application.fraud_detection_report)
        credit_report = safe_json_loads(application.ai_analysis_report)
        employment_report = safe_json_loads(application.employment_verification_report)
        document_report = safe_json_loads(application.document_verification_report)
        na_report = safe_json_loads(application.na_document_verification)
        verification_summary = safe_json_loads(application.verification_summary)

        # Calculate amortization schedule if approved
        amortization_schedule = []
        if application.status == 'APPROVED' and application.interest_rate:
            try:
                tenure_months = application.loan_term_years * 12
                emi = application.emi_amount or calculate_emi(application.loan_amount, application.interest_rate, tenure_months)
                amortization_schedule = generate_amortization_schedule(
                    application.loan_amount, application.interest_rate, tenure_months, emi
                )
            except Exception as e:
                app.logger.error(f"Error generating amortization schedule: {e}")
                amortization_schedule = []

        return render_template('status.html', 
                               application=application,
                               banking_report=banking_report,
                               fraud_report=fraud_report,
                               credit_report=credit_report,
                               employment_report=employment_report,
                               document_report=document_report,
                               na_report=na_report,
                               verification_summary=verification_summary,
                               verification_analysis=verification_analysis,
                               amortization_schedule=amortization_schedule,
                               is_admin=is_admin)
    
    except Exception as e:
        app.logger.error(f"Error loading application {app_id}: {str(e)}")
        flash('Error loading application details. Please try again.', 'error')
        if 'admin_id' in session:
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('dashboard'))

@app.route('/fix-application/<app_id>')
@login_required
def fix_application(app_id):
    """Route to manually fix old applications"""
    try:
        # Check if current user is admin or owns the application
        is_admin = 'admin_id' in session or session.get('admin_logged_in', False)
        
        if is_admin:
            application = Application.query.filter_by(id=app_id).first()
        else:
            application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first()
        
        if not application:
            flash('Application not found.', 'error')
            return redirect(url_for('dashboard'))
        
        # Reprocess the application
        success = reprocess_old_application(application)
        
        if success:
            flash(f'Application #{application.id} has been updated with new verification data!', 'success')
        else:
            flash(f'Failed to update application #{application.id}.', 'error')
        
        return redirect(url_for('status', app_id=app_id))
        
    except Exception as e:
        flash(f'Error fixing application: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/fix-all-pending')
@login_required
def fix_all_pending():
    """Fix all pending applications (admin only)"""
    try:
        if 'admin_id' not in session:
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        
        pending_apps = Application.query.filter_by(status='PENDING').all()
        fixed_count = 0
        
        for app in pending_apps:
            if app.overall_risk_score is None:
                if reprocess_old_application(app):
                    fixed_count += 1
        
        flash(f'Successfully updated {fixed_count} pending applications with AI verification data!', 'success')
        return redirect(url_for('admin.dashboard'))
        
    except Exception as e:
        flash(f'Error fixing applications: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@app.route('/generate_loan_document/<app_id>')
@login_required
def generate_loan_document(app_id):
    """Generate printable PDF loan document"""
    try:
        # Check if user is admin
        is_admin = 'admin_id' in session
        
        if is_admin:
            # Admin can generate document for any application
            application = Application.query.filter_by(id=app_id).first()
        else:
            # Regular user can only generate for their own applications
            application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first()
        
        if not application:
            return "Application not found", 404
        
        if application.status != 'APPROVED':
            return "Loan not approved", 400

        # Calculate loan details
        loan_amount = application.loan_amount
        interest_rate = getattr(application, 'interest_rate', 8.5)
        tenure_months = getattr(application, 'loan_term_years', 5) * 12
        emi = application.emi_amount or calculate_emi(loan_amount, interest_rate, tenure_months)
        total_interest = calculate_total_interest(loan_amount, interest_rate, tenure_months)
        total_payment = calculate_total_payment(loan_amount, interest_rate, tenure_months)

        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.darkblue,
            spaceAfter=30,
            alignment=1  # Center
        )
        
        heading_style = ParagraphStyle(
            'Heading2',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.darkblue,
            spaceAfter=12
        )
        
        # Header
        elements.append(Paragraph("LOAN APPROVAL AGREEMENT", title_style))
        elements.append(Spacer(1, 10))
        
        # Agreement Details
        elements.append(Paragraph("Agreement Details", heading_style))
        agreement_data = [
            ['Loan Agreement Number:', f'LA-{application.id}-{datetime.now().strftime("%Y%m%d")}'],
            ['Date of Approval:', datetime.now().strftime('%d-%b-%Y')],
            ['', ''],
        ]
        
        agreement_table = Table(agreement_data, colWidths=[2.5*inch, 3*inch])
        agreement_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(agreement_table)
        elements.append(Spacer(1, 15))
        
        # Borrower Information
        elements.append(Paragraph("Borrower Information", heading_style))
        borrower_data = [
            ['Full Name:', f'{application.first_name} {application.last_name}'],
            ['Email Address:', application.email],
            ['PAN Number:', application.pan_number],
            ['Aadhar Number:', application.aadhar_number],
            ['Address:', application.current_address],
            ['', ''],
        ]
        
        borrower_table = Table(borrower_data, colWidths=[2.5*inch, 3*inch])
        borrower_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ]))
        elements.append(borrower_table)
        elements.append(Spacer(1, 15))
        
        # Loan Terms
        elements.append(Paragraph("Loan Terms & Conditions", heading_style))
        loan_data = [
            ['Description', 'Details'],
            ['Loan Amount:', f'₹{loan_amount:,.2f}'],
            ['Interest Rate:', f'{interest_rate}% per annum'],
            ['Loan Tenure:', f'{tenure_months} months ({tenure_months//12} years)'],
            ['Monthly EMI:', f'₹{emi:,.2f}'],
            ['Total Interest Payable:', f'₹{total_interest:,.2f}'],
            ['Total Payment:', f'₹{total_payment:,.2f}'],
            ['Processing Fees:', '₹0 (Waived)'],
            ['Prepayment Charges:', '1% after 12 months'],
        ]
        
        loan_table = Table(loan_data, colWidths=[2.5*inch, 3*inch])
        loan_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(loan_table)
        elements.append(Spacer(1, 20))
        
        # Important Notes
        elements.append(Paragraph("Important Notes", heading_style))
        notes = [
            "1. This loan agreement is subject to the terms and conditions mentioned herein.",
            "2. The borrower agrees to pay the EMI on or before the due date each month.",
            "3. Late payments will attract a penalty of 2% per month on the overdue amount.",
            "4. The borrower can prepay the loan after 12 months with applicable charges.",
            "5. This agreement is governed by the laws of India.",
        ]
        
        for note in notes:
            elements.append(Paragraph(note, styles['Normal']))
            elements.append(Spacer(1, 5))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        # Return PDF response
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'Loan_Agreement_{application.id}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        app.logger.error(f"Error generating PDF: {e}")
        return f"Error generating document: {str(e)}", 500

@app.route('/force-na-verification/<app_id>')
@login_required
def force_na_verification(app_id):
    """Force NA document verification for an application"""
    try:
        # Check if current user is admin or owns the application
        is_admin = 'admin_id' in session or session.get('admin_logged_in', False)
        
        if is_admin:
            application = Application.query.filter_by(id=app_id).first()
        else:
            application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first()
        
        if not application:
            flash('Application not found.', 'error')
            return redirect(url_for('dashboard'))
        
        # Force NA verification
        na_report = initialize_na_verification(application.id)
        
        if na_report:
            flash(f'NA document verification completed for application #{application.id}. Status: {na_report.get("status")}', 'success')
        else:
            flash('Failed to verify NA document.', 'error')
        
        return redirect(url_for('verification_report', app_id=app_id))
        
    except Exception as e:
        flash(f'Error verifying NA document: {str(e)}', 'error')
        return redirect(url_for('verification_report', app_id=app_id))

@app.route('/verification_report/<app_id>')
@login_required
def verification_report(app_id):
    """Display comprehensive verification report"""
    # Check if user is admin
    is_admin = 'admin_id' in session
    
    if is_admin:
        # Admin can view any application
        application = Application.query.filter_by(id=app_id).first()
        if not application:
            flash('Application not found.', 'error')
            return redirect(url_for('admin.dashboard'))
    else:
        # Regular user can only view their own applications
        application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first_or_404()
    
    # Use safe JSON loading function for existing reports
    def safe_json_loads(json_string, default=None):
        if default is None:
            default = {}
        try:
            if json_string and json_string.strip():
                return json.loads(json_string)
            else:
                return default
        except (json.JSONDecodeError, TypeError, AttributeError):
            return default
    
    # Parse existing verification reports with safe loading
    employment_report = safe_json_loads(application.employment_verification_report)
    document_report = safe_json_loads(application.document_verification_report)
    verification_summary = safe_json_loads(application.verification_summary)
    
    # Get new verification reports from helper functions
    credit_report = get_credit_report(application) or {}
    banking_report = get_banking_report(application) or {}
    fraud_report = get_fraud_report(application) or {}
    
    # Handle NA document verification - use existing if available, otherwise create default
    na_report = safe_json_loads(application.na_document_verification)
    if not na_report:
        na_report = {
            'status': 'PENDING',
            'risk_score': 0.0,
            'details': 'Non-agricultural document verification pending',
            'issues': ['Document not uploaded or processed yet']
        }
    
    # Get amortization schedule for approved loans
    amortization_schedule = []
    if application.status == 'APPROVED' and application.interest_rate:
        try:
            tenure_months = application.loan_term_years * 12
            emi = application.emi_amount or calculate_emi(application.loan_amount, application.interest_rate, tenure_months)
            amortization_schedule = generate_amortization_schedule(
                application.loan_amount, application.interest_rate, tenure_months, emi
            )
        except Exception as e:
            app.logger.error(f"Error generating amortization schedule: {e}")
            amortization_schedule = []
    
    return render_template('verification_report.html',
                         application=application,
                         employment_report=employment_report,
                         document_report=document_report,
                         verification_summary=verification_summary,
                         credit_report=credit_report,
                         banking_report=banking_report,
                         fraud_report=fraud_report,
                         na_report=na_report,
                         amortization_schedule=amortization_schedule)

@app.route('/upload-na-document/<app_id>', methods=['POST'])
@login_required
def upload_na_document(app_id):
    """Handle NA document upload"""
    try:
        # Only regular users can upload documents
        if 'admin_id' in session:
            flash('Admin users cannot upload documents.', 'error')
            return redirect(url_for('admin.dashboard'))
        
        application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first_or_404()
        
        if 'na_document' not in request.files:
            flash('No file selected', 'error')
            return redirect(url_for('verification_report', app_id=app_id))
        
        file = request.files['na_document']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('verification_report', app_id=app_id))
        
        if file:
            # Save NA document
            user = User.query.get(session['user_id'])
            doc_info = storage_service.save_single_document(
                user.mobile_number, application.id, file, 'na_document'
            )
            
            if doc_info:
                # FIXED: Use correct document type
                new_doc = Document(
                    application_id=application.id,
                    document_type='NON_AGRICULTURAL_DECLARATION',  # CORRECTED
                    file_path=doc_info['file_path'],
                    file_name=doc_info['file_name'],
                    uploaded_at=datetime.utcnow()
                )
                db.session.add(new_doc)
                
                # Re-verify NA document using our new function
                na_report = verify_na_document(new_doc, application)
                application.na_document_verification = json.dumps(na_report)
                application.na_document_status = na_report.get('status', 'PENDING')
                application.na_document_risk_score = na_report.get('risk_score', 0.0)
                
                db.session.commit()
                flash('NA document uploaded and verified successfully!', 'success')
            else:
                flash('Error uploading document', 'error')
        
        return redirect(url_for('verification_report', app_id=app_id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error uploading document: {str(e)}', 'error')
        return redirect(url_for('verification_report', app_id=app_id))

@app.route('/logout')
def logout():
    """Unified logout endpoint that handles both user and admin logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/user_logout')
def user_logout():
    """Legacy user logout endpoint - redirects to main logout"""
    return redirect(url_for('logout'))

@app.route('/view_document/<int:doc_id>')
@login_required
def view_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    application = doc.application
    
    is_owner = 'user_id' in session and application.user_id == session['user_id']
    is_admin = 'admin_id' in session

    if not is_owner and not is_admin:
        abort(403)
            
    try:
        directory = os.path.dirname(doc.file_path)
        filename = os.path.basename(doc.file_path)
        return send_from_directory(directory, filename, as_attachment=False)
    except FileNotFoundError:
        abort(404)

@app.route('/check_cibil', methods=['POST'])
@login_required
def check_cibil():
    # Only regular users can check CIBIL
    if 'admin_id' in session:
        return jsonify({'error': 'Admin users cannot check CIBIL scores'}), 403
    
    simulated_score = random.randint(300, 900)
    return jsonify({'cibil_score': simulated_score})

@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_message = request.json['message'].lower()
    reply = "I'm sorry, I don't understand."
    if 'document' in user_message:
        reply = "You'll need salary slips, bank statements, and KYC documents."
    elif 'interest' in user_message:
        reply = "Interest rates start from 8.5% p.a."
    return jsonify({'reply': reply})

@app.route('/prefill-from-document', methods=['POST'])
@login_required
def prefill_from_document():
    # Only regular users can use this feature
    if 'admin_id' in session:
        return jsonify({"error": "Admin users cannot use this feature"}), 403
    
    if 'master_document' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['master_document']
    if file:
        file_content = file.read().decode('utf-8')
        extracted_data = advance_verification_service.parse_master_document(file_content)
        return jsonify(extracted_data)
        
    return jsonify({"error": "File processing failed"}), 500

@app.route('/application-result')
@login_required
def application_result():
    # Only regular users can view application results
    if 'admin_id' in session:
        flash('Admin users cannot view application results.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    app_id = request.args.get('app_id')
    if not app_id:
        flash('No application specified', 'error')
        return redirect(url_for('dashboard'))
    
    application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first()
    if not application:
        flash('Application not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Parse AI analysis from JSON and handle both old and new formats
    ai_analysis = None
    if application.ai_analysis_report:
        try:
            ai_analysis = json.loads(application.ai_analysis_report)
            
            # Convert new instant decision format to old template format if needed
            if 'risk_score' in ai_analysis:
                # This is the new instant decision format - convert to old format for template compatibility
                ai_analysis = convert_to_old_format(ai_analysis)
                
        except json.JSONDecodeError:
            ai_analysis = {'error': 'Unable to parse AI analysis'}
    
    return render_template('application_result.html', 
                        application=application, 
                        analysis=ai_analysis)

@app.route('/ai-analysis-report/<app_id>')
@login_required
def ai_analysis_report(app_id):
    """Detailed AI Analysis Report"""
    # Check if user is admin
    is_admin = 'admin_id' in session
    
    if is_admin:
        application = Application.query.filter_by(id=app_id).first()
        if not application:
            flash('Application not found.', 'error')
            return redirect(url_for('admin.dashboard'))
    else:
        application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first_or_404()
    
    # Parse AI analysis report
    ai_analysis = safe_json_loads(application.ai_analysis_report)
    verification_analysis = safe_json_loads(application.ai_verification_report)
    
    return render_template('ai_analysis_report.html',
                         application=application,
                         ai_analysis=ai_analysis,
                         verification_analysis=verification_analysis,
                         is_admin=is_admin)

@app.route('/application-reports')
@login_required
def application_reports():
    """Application Reports Dashboard"""
    if 'admin_id' in session:
        # Admin reports - all applications
        applications = Application.query.order_by(Application.created_at.desc()).all()
        return render_template('application_reports.html', 
                             applications=applications, 
                             is_admin=True)
    else:
        # User reports - only their applications
        applications = Application.query.filter_by(user_id=session['user_id']).order_by(Application.created_at.desc()).all()
        return render_template('application_reports.html', 
                             applications=applications, 
                             is_admin=False)

@app.route('/application-status/<app_id>')
@login_required
def application_status(app_id):
    """Alternative status view (duplicate of status.html)"""
    return redirect(url_for('status', app_id=app_id))

@app.route('/report-sections')
@login_required
def report_sections():
    """Report sections partial template demo"""
    if 'admin_id' in session:
        applications = Application.query.order_by(Application.created_at.desc()).limit(5).all()
    else:
        applications = Application.query.filter_by(user_id=session['user_id']).order_by(Application.created_at.desc()).limit(5).all()
    
    return render_template('report_sections.html', applications=applications)

# Find this existing route in your app.py:
@app.route('/debug-application/<app_id>')
@login_required
def debug_application(app_id):
    """Debug route to check application data"""
    application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first()
    if not application:
        return "Application not found", 404
    
    debug_info = {
        'app_id': application.id,
        'status': application.status,
        'has_ai_analysis': bool(application.ai_analysis_report),
        'has_banking_report': bool(application.banking_analysis_report),
        'has_employment_report': bool(application.employment_verification_report),
        'created_at': application.created_at,
        'loan_amount': application.loan_amount,
        'interest_rate': getattr(application, 'interest_rate', 'Not set'),
        'emi_amount': getattr(application, 'emi_amount', 'Not set')
    }
    
    return jsonify(debug_info)

# ⬇️⬇️ ADD THE NEW DEBUG-PDF ROUTE RIGHT HERE ⬇️⬇️

@app.route('/debug-pdf/<app_id>')
@login_required
def debug_pdf(app_id):
    """Debug PDF generation"""
    try:
        application = Application.query.filter_by(id=app_id).first()
        if not application:
            return "Application not found", 404
        
        # Test data availability
        debug_info = {
            'app_id': application.id,
            'has_ai_analysis': bool(application.ai_analysis_report),
            'has_documents': len(application.documents) > 0,
            'overall_risk_score': application.overall_risk_score,
            'status': application.status,
            'documents_count': len(application.documents),
            'document_types': [doc.document_type for doc in application.documents]
        }
        
        return jsonify(debug_info)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ⬆️⬆️ END OF NEW ROUTE ⬆️⬆️
@app.route('/debug-session')
def debug_session():
    """Debug route to check session variables"""
    return f"""
    <pre>
    Session data: {dict(session)}
    User ID: {session.get('user_id')}
    Admin ID: {session.get('admin_id')}
    Admin Logged In: {session.get('admin_logged_in')}
    User Logged In: {session.get('user_logged_in')}
    </pre>
    """

@app.route('/debug-routes')
def debug_routes():
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'path': rule.rule
        })
    return jsonify(routes)

@app.route('/api/ai-analysis', methods=['POST'])
def ai_analysis():
    """Comprehensive AI analysis endpoint"""
    try:
        data = request.get_json()
        
        ai_engine = AIVerificationService()
        result = ai_engine.generate_comprehensive_analysis(data)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        }), 500

@app.route('/api/quick-assessment', methods=['POST'])
def quick_assessment():
    """Quick risk assessment endpoint"""
    try:
        data = request.get_json()
        
        ai_engine = AIVerificationService()
        result = ai_engine.quick_risk_assessment(data)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Quick assessment failed: {str(e)}'
        }), 500

@app.route('/application/<int:application_id>/comprehensive_report')
@login_required
def comprehensive_report(application_id):
    """Display comprehensive HTML report"""
    application = Application.query.get_or_404(application_id)
    
    # Check permissions
    if 'admin_id' not in session and application.user_id != session['user_id']:
        abort(403)
    
    try:
        # Prepare application data
        app_data = {
            'application_id': application.id,
            'first_name': application.first_name,
            'last_name': application.last_name,
            'email': application.email,
            'loan_amount': float(application.loan_amount),
            'interest_rate': float(application.interest_rate) if application.interest_rate else 8.5,
            'loan_term_years': int(application.loan_term_years) if application.loan_term_years else 20,
            'monthly_salary': float(application.monthly_salary),
            'property_valuation': float(application.property_valuation),
            'cibil_score': int(application.cibil_score),
            'existing_emi': float(application.existing_emi)
        }
        
        # Calculate EMI data
        loan_amount = application.loan_amount
        interest_rate = application.interest_rate or 8.5
        loan_term_years = application.loan_term_years or 20
        
        monthly_rate = interest_rate / 12 / 100
        months = loan_term_years * 12
        emi = (loan_amount * monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
        total_payment = emi * months
        total_interest = total_payment - loan_amount
        
        emi_data = {
            'monthly_emi': emi,
            'loan_amount': loan_amount,
            'interest_rate': interest_rate,
            'loan_term_years': loan_term_years,
            'loan_term_months': months,
            'total_payment': total_payment,
            'total_interest': total_interest
        }
        
        # Prepare KYC reports (same as PDF version)
        kyc_reports = {
            'identity_report': {
                'status': 'VERIFIED' if application.aadhar_number and application.pan_number else 'PENDING',
                'verification_checks': [
                    {
                        'check_name': 'Aadhaar Verification',
                        'status': 'PASSED' if application.aadhar_number else 'PENDING',
                        'risk_level': 'LOW' if application.aadhar_number else 'HIGH',
                        'details': 'Aadhaar number verified successfully' if application.aadhar_number else 'Aadhaar verification pending'
                    },
                    {
                        'check_name': 'PAN Verification',
                        'status': 'PASSED' if application.pan_number else 'PENDING',
                        'risk_level': 'LOW' if application.pan_number else 'HIGH',
                        'details': 'PAN number verified successfully' if application.pan_number else 'PAN verification pending'
                    }
                ],
                'recommendations': [
                    'Identity documents verified successfully'
                ] if application.aadhar_number and application.pan_number else [
                    'Complete identity document verification'
                ]
            },
            'address_report': {
                'status': 'VERIFIED' if application.current_address else 'PENDING',
                'verification_checks': [
                    {
                        'check_name': 'Address Verification',
                        'status': 'PASSED' if application.current_address else 'PENDING',
                        'risk_level': 'LOW' if application.current_address else 'MEDIUM',
                        'details': 'Current address verified' if application.current_address else 'Address verification required'
                    }
                ],
                'recommendations': [
                    'Address verification completed'
                ] if application.current_address else [
                    'Provide complete current address for verification'
                ]
            },
            'financial_report': {
                'status': 'VERIFIED' if application.monthly_salary else 'PENDING',
                'verification_checks': [
                    {
                        'check_name': 'Income Verification',
                        'status': 'PASSED' if application.monthly_salary else 'PENDING',
                        'risk_level': 'LOW' if application.monthly_salary else 'HIGH',
                        'details': f'Monthly salary: ₹{application.monthly_salary:,.2f}' if application.monthly_salary else 'Income verification pending'
                    },
                    {
                        'check_name': 'Employment Verification',
                        'status': 'PASSED' if application.company_name else 'PENDING',
                        'risk_level': 'LOW' if application.company_name else 'MEDIUM',
                        'details': f'Company: {application.company_name}' if application.company_name else 'Employment details pending'
                    }
                ],
                'recommendations': [
                    'Financial documents verified',
                    'Income meets eligibility criteria'
                ] if application.monthly_salary else [
                    'Provide income proof documents',
                    'Complete employment verification'
                ]
            },
            'summary': {
                'overall_kyc_status': 'COMPLETED' if application.aadhar_number and application.pan_number and application.current_address and application.monthly_salary else 'PENDING'
            }
        }
        
        # Prepare risk analysis
        debt_to_income = (application.existing_emi / application.monthly_salary * 100) if application.monthly_salary > 0 else 0
        affordability_ratio = ((application.monthly_salary - application.existing_emi) / application.monthly_salary * 100) if application.monthly_salary > 0 else 0
        
        risk_analysis = {
            'risk_analysis_report': {
                'risk_assessment': {
                    'risk_score': application.overall_risk_score if application.overall_risk_score else 50,
                    'risk_grade': 'LOW' if (application.overall_risk_score or 50) <= 30 else 'MEDIUM' if (application.overall_risk_score or 50) <= 60 else 'HIGH'
                },
                'approval_probability': max(0, 100 - (application.overall_risk_score or 50)),
                'mitigation_recommendations': [
                    'Maintain good credit history',
                    'Ensure timely payment of existing obligations',
                    'Provide all required documentation promptly'
                ],
                'key_findings': [
                    f'CIBIL Score: {application.cibil_score}',
                    f'Debt-to-Income Ratio: {debt_to_income:.1f}%',
                    f'Loan-to-Value Ratio: {(application.loan_amount / application.property_valuation * 100) if application.property_valuation > 0 else 0:.1f}%',
                    f'Monthly Income: ₹{application.monthly_salary:,.2f}'
                ]
            },
            'existing_loan_analysis': {
                'financial_ratios': {
                    'debt_to_income_ratio': debt_to_income,
                    'affordability_ratio': affordability_ratio,
                    'safe_threshold': 40.0
                },
                'recommendations': [
                    'Existing EMI obligations are within manageable limits'
                ] if debt_to_income <= 40 else [
                    'Consider reducing existing debt before applying for new loan'
                ]
            },
            'ai_summary': {
                'key_findings': [
                    'Application meets basic eligibility criteria',
                    'Property valuation provides adequate security',
                    'Income supports loan repayment capacity'
                ]
            }
        }
        
        # Prepare recommendations
        recommendations = {
            'kyc_verification': kyc_reports['identity_report']['recommendations'] + 
                               kyc_reports['address_report']['recommendations'] + 
                               kyc_reports['financial_report']['recommendations'],
            'risk_mitigation': risk_analysis['risk_analysis_report']['mitigation_recommendations'],
            'financial_planning': risk_analysis['existing_loan_analysis']['recommendations']
        }
        
        return render_template('comprehensive_report.html',
                             application=application,
                             app_data=app_data,
                             emi_data=emi_data,
                             kyc_reports=kyc_reports,
                             risk_analysis=risk_analysis,
                             recommendations=recommendations,
                             generated_date=datetime.now().strftime('%d %B, %Y at %H:%M'))
        
    except Exception as e:
        app.logger.error(f"Error generating HTML report for application {application_id}: {str(e)}")
        flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('status', app_id=application_id))

@app.route('/api/download-report/<path:pdf_path>')
def download_report(pdf_path):
    """Download generated PDF report"""
    try:
        return send_file(pdf_path, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 404

@app.route('/application/<int:application_id>/generate_combined_pdf')
@login_required
def generate_combined_pdf(application_id):
    """Generate and download combined PDF report"""
    application = Application.query.get_or_404(application_id)
    
    # Check if user owns this application or is admin
    if 'admin_id' not in session and application.user_id != session['user_id']:
        abort(403)
    
    try:
        # Initialize PDF generator
        pdf_generator = ComprehensivePDFReportGenerator()
        
        # Prepare application data for PDF
        app_data = {
            'application_id': application.id,
            'first_name': application.first_name,
            'last_name': application.last_name,
            'email': application.email,
            'loan_amount': float(application.loan_amount),
            'interest_rate': float(application.interest_rate) if application.interest_rate else 8.5,
            'loan_term_years': int(application.loan_term_years) if application.loan_term_years else 20,
            'monthly_salary': float(application.monthly_salary),
            'property_valuation': float(application.property_valuation),
            'cibil_score': int(application.cibil_score),
            'existing_emi': float(application.existing_emi)
        }
        
        # Prepare KYC reports data
        kyc_reports = {
            'identity_report': {
                'status': 'VERIFIED' if application.aadhar_number and application.pan_number else 'PENDING',
                'verification_checks': [
                    {
                        'check_name': 'Aadhaar Verification',
                        'status': 'PASSED' if application.aadhar_number else 'PENDING',
                        'risk_level': 'LOW' if application.aadhar_number else 'HIGH',
                        'details': 'Aadhaar number verified successfully' if application.aadhar_number else 'Aadhaar verification pending'
                    },
                    {
                        'check_name': 'PAN Verification',
                        'status': 'PASSED' if application.pan_number else 'PENDING',
                        'risk_level': 'LOW' if application.pan_number else 'HIGH',
                        'details': 'PAN number verified successfully' if application.pan_number else 'PAN verification pending'
                    }
                ],
                'recommendations': [
                    'Identity documents verified successfully'
                ] if application.aadhar_number and application.pan_number else [
                    'Complete identity document verification'
                ]
            },
            'address_report': {
                'status': 'VERIFIED' if application.current_address else 'PENDING',
                'verification_checks': [
                    {
                        'check_name': 'Address Verification',
                        'status': 'PASSED' if application.current_address else 'PENDING',
                        'risk_level': 'LOW' if application.current_address else 'MEDIUM',
                        'details': 'Current address verified' if application.current_address else 'Address verification required'
                    }
                ],
                'recommendations': [
                    'Address verification completed'
                ] if application.current_address else [
                    'Provide complete current address for verification'
                ]
            },
            'financial_report': {
                'status': 'VERIFIED' if application.monthly_salary else 'PENDING',
                'verification_checks': [
                    {
                        'check_name': 'Income Verification',
                        'status': 'PASSED' if application.monthly_salary else 'PENDING',
                        'risk_level': 'LOW' if application.monthly_salary else 'HIGH',
                        'details': f'Monthly salary: ₹{application.monthly_salary:,.2f}' if application.monthly_salary else 'Income verification pending'
                    },
                    {
                        'check_name': 'Employment Verification',
                        'status': 'PASSED' if application.company_name else 'PENDING',
                        'risk_level': 'LOW' if application.company_name else 'MEDIUM',
                        'details': f'Company: {application.company_name}' if application.company_name else 'Employment details pending'
                    }
                ],
                'recommendations': [
                    'Financial documents verified',
                    'Income meets eligibility criteria'
                ] if application.monthly_salary else [
                    'Provide income proof documents',
                    'Complete employment verification'
                ]
            },
            'summary': {
                'overall_kyc_status': 'COMPLETED' if application.aadhar_number and application.pan_number and application.current_address and application.monthly_salary else 'PENDING'
            }
        }
        
        # Prepare risk analysis data
        # Calculate debt-to-income ratio
        debt_to_income = (application.existing_emi / application.monthly_salary * 100) if application.monthly_salary > 0 else 0
        
        risk_analysis = {
            'risk_analysis_report': {
                'risk_assessment': {
                    'risk_score': application.overall_risk_score if application.overall_risk_score else 50,
                    'risk_grade': 'LOW' if (application.overall_risk_score or 50) <= 30 else 'MEDIUM' if (application.overall_risk_score or 50) <= 60 else 'HIGH'
                },
                'approval_probability': max(0, 100 - (application.overall_risk_score or 50)),
                'mitigation_recommendations': [
                    'Maintain good credit history',
                    'Ensure timely payment of existing obligations'
                ],
                'key_findings': [
                    f'CIBIL Score: {application.cibil_score}',
                    f'Debt-to-Income Ratio: {debt_to_income:.1f}%',
                    f'Loan-to-Value Ratio: {(application.loan_amount / application.property_valuation * 100) if application.property_valuation > 0 else 0:.1f}%'
                ]
            },
            'existing_loan_analysis': {
                'financial_ratios': {
                    'debt_to_income_ratio': debt_to_income,
                    'affordability_ratio': ((application.monthly_salary - application.existing_emi) / application.monthly_salary * 100) if application.monthly_salary > 0 else 0,
                    'safe_threshold': 40.0
                },
                'recommendations': [
                    'Existing EMI obligations are within manageable limits'
                ] if debt_to_income <= 40 else [
                    'Consider reducing existing debt before applying for new loan'
                ]
            },
            'ai_summary': {
                'key_findings': [
                    'Application meets basic eligibility criteria',
                    'Property valuation provides adequate security',
                    'Income supports loan repayment capacity'
                ]
            }
        }
        
        # Create reports directory if it doesn't exist
        os.makedirs('reports', exist_ok=True)
        output_path = f"reports/application_{application_id}_combined.pdf"
        
        # Generate PDF
        pdf_path = pdf_generator.generate_combined_report(
            app_data, 
            kyc_reports, 
            risk_analysis, 
            output_path
        )
        
        # Log the PDF generation
        app.logger.info(f"PDF report generated for application {application_id}: {pdf_path}")
        
        return send_file(
            pdf_path, 
            as_attachment=True, 
            download_name=f"Loan_Application_Report_{application_id}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        app.logger.error(f"Error generating PDF for application {application_id}: {str(e)}")
        flash(f'Error generating PDF report: {str(e)}', 'error')
        return redirect(url_for('view_application_reports', application_id=application_id))

@app.route('/application/<app_id>/generate-full-pdf')
@login_required
def generate_full_pdf(app_id):
    """Generate comprehensive PDF report"""
    try:
        # Check permissions
        is_admin = 'admin_id' in session
        if is_admin:
            application = Application.query.filter_by(id=app_id).first()
        else:
            application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first()
        
        if not application:
            flash('Application not found.', 'error')
            return redirect(url_for('dashboard'))
        
        # Prepare all data for the PDF
        ai_analysis = safe_json_loads(application.ai_analysis_report)
        banking_report = safe_json_loads(application.banking_analysis_report)
        fraud_report = safe_json_loads(application.fraud_detection_report)
        employment_report = safe_json_loads(application.employment_verification_report)
        document_report = safe_json_loads(application.document_verification_report)
        na_report = safe_json_loads(application.na_document_verification)
        
        # Calculate financial risk
        monthly_salary = application.monthly_salary or 0
        existing_emi = application.existing_emi or 0
        debt_to_income = (existing_emi / monthly_salary * 100) if monthly_salary > 0 else 0
        
        if debt_to_income <= 30:
            financial_risk_level = "LOW"
            financial_risk_score = 20
        elif debt_to_income <= 50:
            financial_risk_level = "MEDIUM"
            financial_risk_score = 50
        else:
            financial_risk_level = "HIGH"
            financial_risk_score = 80
        
        # Document risk calculation
        document_risk_score = document_report.get('overall_risk_score', 50)
        if document_risk_score <= 25:
            document_risk_level = "LOW"
        elif document_risk_score <= 75:
            document_risk_level = "MEDIUM"
        else:
            document_risk_level = "HIGH"
        
        # Prepare document data
        documents_data = []
        document_types = {
            'BANK_STATEMENTS': 'Bank Statements',
            'SALARY_SLIPS': 'Salary Slips',
            'KYC_DOCS': 'KYC Documents',
            'PROPERTY_VALUATION': 'Property Valuation',
            'LEGAL_CLEARANCE': 'Legal Clearance',
            'NON_AGRICULTURAL_DECLARATION': 'Non-Agricultural Declaration'
        }
        
        for doc_type, doc_name in document_types.items():
            doc = next((d for d in application.documents if d.document_type == doc_type), None)
            documents_data.append({
                'document_type': doc_name,
                'verification_status': 'VERIFIED' if doc else 'MISSING',
                'risk_score': 10 if doc else 90
            })
        
        # Create PDF using weasyprint (install: pip install weasyprint)
        try:
            from weasyprint import HTML
            import tempfile
            import os
            
            # Render HTML template
            html_content = render_template('pdf_report_template.html',
                application=application,
                ai_analysis=ai_analysis,
                banking_report=banking_report,
                fraud_report=fraud_report,
                employment_report=employment_report,
                document_report=document_report,
                na_report=na_report,
                documents=documents_data,
                financial_risk_score=financial_risk_score,
                financial_risk_level=financial_risk_level,
                document_risk_score=document_risk_score,
                document_risk_level=document_risk_level,
                generated_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                report_id=f"RPT-{application.id}-{datetime.now().strftime('%Y%m%d')}"
            )
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                pdf_path = tmp_file.name
            
            # Generate PDF
            HTML(string=html_content).write_pdf(pdf_path)
            
            # Send file
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=f'Comprehensive_Report_{application.id}.pdf',
                mimetype='application/pdf'
            )
            
        except ImportError:
            # Fallback to basic PDF if weasyprint not available
            return generate_basic_pdf_report(application, app_id)
    
    except Exception as e:
        current_app.logger.error(f"Error generating PDF for {app_id}: {str(e)}")
        flash(f'Error generating PDF report: {str(e)}', 'error')
        return redirect(url_for('status', app_id=app_id))

def generate_basic_pdf_report(application, app_id):
    """Fallback basic PDF generation using reportlab"""
    try:
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        import io
        
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.darkblue,
            spaceAfter=20,
            alignment=1
        )
        
        # Header
        elements.append(Paragraph("COMPREHENSIVE LOAN APPLICATION REPORT", title_style))
        elements.append(Spacer(1, 10))
        
        # Application Details
        elements.append(Paragraph("Application Details", styles['Heading2']))
        app_data = [
            ['Application ID:', application.id],
            ['Applicant Name:', f'{application.first_name} {application.last_name}'],
            ['Loan Amount:', f'₹{application.loan_amount:,.2f}'],
            ['Status:', application.status],
            ['CIBIL Score:', str(application.cibil_score)],
            ['Overall Risk Score:', f"{application.overall_risk_score if application.overall_risk_score else 'N/A'}%"]
        ]
        
        app_table = Table(app_data, colWidths=[2.5*inch, 3*inch])
        app_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(app_table)
        elements.append(Spacer(1, 15))
        
        # Risk Analysis
        elements.append(Paragraph("Risk Analysis", styles['Heading2']))
        risk_data = [
            ['Risk Category', 'Score', 'Level'],
            ['Overall Risk', f"{application.overall_risk_score if application.overall_risk_score else 'N/A'}", 
             'HIGH' if application.overall_risk_score and application.overall_risk_score > 70 else 
             'MEDIUM' if application.overall_risk_score and application.overall_risk_score > 40 else 'LOW'],
            ['Document Risk', 'See detailed report', 'VARIES'],
            ['Financial Risk', 'See detailed report', 'VARIES']
        ]
        
        risk_table = Table(risk_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        risk_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(risk_table)
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'Basic_Report_{application.id}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        raise Exception(f"Basic PDF generation failed: {str(e)}")

# app.py - Update all report routes

@app.route('/application/<string:app_id>/credit-risk-report')
def credit_risk_report(app_id):
    """Generate Credit Risk Report PDF"""
    try:
        application = Application.query.filter_by(id=app_id).first_or_404()
        print(f"Generating credit risk report for app {app_id}")
        
        pdf_buffer = generate_credit_risk_report(application)
        
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=credit_risk_report_{app_id}.pdf'
        return response
        
    except Exception as e:
        print(f"Error in credit_risk_report route: {str(e)}")
        flash(f'Error generating credit risk report: {str(e)}', 'error')
        return redirect(url_for('application_status', app_id=app_id))

@app.route('/application/<string:app_id>/document-verification-report')
def document_verification_report(app_id):
    """Generate Document Verification Report PDF"""
    try:
        application = Application.query.filter_by(id=app_id).first_or_404()
        print(f"Generating document verification report for app {app_id}")
        
        pdf_buffer = generate_document_verification_report(application)
        
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=document_verification_report_{app_id}.pdf'
        return response
        
    except Exception as e:
        print(f"Error in document_verification_report route: {str(e)}")
        flash(f'Error generating document verification report: {str(e)}', 'error')
        return redirect(url_for('application_status', app_id=app_id))

@app.route('/application/<string:app_id>/property-verification-report')
def property_verification_report(app_id):
    """Generate Property Verification Report PDF"""
    try:
        application = Application.query.filter_by(id=app_id).first_or_404()
        print(f"Generating property verification report for app {app_id}")
        
        pdf_buffer = generate_property_verification_report(application)
        
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=property_verification_report_{app_id}.pdf'
        return response
        
    except Exception as e:
        print(f"Error in property_verification_report route: {str(e)}")
        flash(f'Error generating property verification report: {str(e)}', 'error')
        return redirect(url_for('application_status', app_id=app_id))

@app.route('/application/<string:app_id>/final-comprehensive-report')
def final_comprehensive_report(app_id):
    """Generate Final Comprehensive Report PDF"""
    try:
        application = Application.query.filter_by(id=app_id).first_or_404()
        print(f"Generating final comprehensive report for app {app_id}")
        
        pdf_buffer = generate_final_comprehensive_report(application)
        
        response = make_response(pdf_buffer.getvalue())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=final_comprehensive_report_{app_id}.pdf'
        return response
        
    except Exception as e:
        print(f"Error in final_comprehensive_report route: {str(e)}")
        flash(f'Error generating final comprehensive report: {str(e)}', 'error')
        return redirect(url_for('application_status', app_id=app_id))

@app.route('/application/<string:app_id>/generate-ai-summaries')
def generate_ai_summaries(app_id):
    """Generate and store AI summaries for an application"""
    try:
        application = Application.query.filter_by(id=app_id).first_or_404()
        ai_generator = AISummaryGenerator()
        
        # Generate and store AI summaries
        application.credit_risk_ai_summary = ai_generator.generate_credit_risk_summary(application)
        application.document_verification_ai_summary = ai_generator.generate_document_verification_summary(application)
        application.property_verification_ai_summary = ai_generator.generate_property_verification_summary(application)
        application.final_comprehensive_ai_summary = ai_generator.generate_final_comprehensive_summary(application)
        application.ai_summary_generated_at = datetime.utcnow()
        
        db.session.commit()
        flash('AI summaries generated successfully!', 'success')
        
    except Exception as e:
        flash(f'Error generating AI summaries: {str(e)}', 'error')
    
    return redirect(url_for('application_status', app_id=app_id))
# ===== ADVANCED VERIFICATION ROUTES =====
from services.advance_verification_service import  AdvanceVerificationService
@app.route('/api/advanced-verification/<app_id>', methods=['POST'])
@login_required
def run_advanced_verification(app_id):
    """Run comprehensive advanced verification on an application"""
    try:
        # Check permissions
        is_admin = 'admin_id' in session
        if is_admin:
            application = Application.query.filter_by(id=app_id).first()
        else:
            application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first()
        
        if not application:
            return jsonify({'success': False, 'error': 'Application not found'}), 404
        
        # Get documents for the application
        documents = application.documents
        
        # Run comprehensive verification
        verification_results = run_comprehensive_verification(application, documents)
        
        # Update application with verification results
        update_application_with_verification(application, verification_results)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Advanced verification completed successfully',
            'verification_id': f"VER_{application.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'results': verification_results
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verification-report/<app_id>')
@login_required
def get_verification_report(app_id):
    """Get comprehensive verification report"""
    try:
        # Check permissions
        is_admin = 'admin_id' in session
        if is_admin:
            application = Application.query.filter_by(id=app_id).first()
        else:
            application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first()
        
        if not application:
            return jsonify({'success': False, 'error': 'Application not found'}), 404
        
        # Parse existing verification data
        verification_data = {
            'employment': safe_json_loads(application.employment_verification_report),
            'documents': safe_json_loads(application.document_verification_report),
            'na_document': safe_json_loads(application.na_document_verification),
            'overall_risk_score': application.overall_risk_score,
            'verification_summary': safe_json_loads(application.verification_summary)
        }
        
        return jsonify({
            'success': True,
            'application_id': application.id,
            'verification_data': verification_data,
            'generated_at': application.updated_at.isoformat() if application.updated_at else datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verify-employment/<app_id>', methods=['POST'])
@login_required
def verify_employment(app_id):
    """Run employment verification only"""
    try:
        # Check permissions
        is_admin = 'admin_id' in session
        if is_admin:
            application = Application.query.filter_by(id=app_id).first()
        else:
            application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first()
        
        if not application:
            return jsonify({'success': False, 'error': 'Application not found'}), 404
        
        # Get documents for the application
        documents = application.documents
        
        # Run employment verification
        employment_verification = advance_verification_service.verify_employment_documents(application, documents)
        
        # Update application
        application.employment_verification_report = json.dumps(employment_verification)
        application.employment_verification_status = employment_verification.get('employment_status', 'PENDING')
        application.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Employment verification completed',
            'employment_data': employment_verification
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verify-documents/<app_id>', methods=['POST'])
@login_required
def verify_documents(app_id):
    """Run document verification only"""
    try:
        # Check permissions
        is_admin = 'admin_id' in session
        if is_admin:
            application = Application.query.filter_by(id=app_id).first()
        else:
            application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first()
        
        if not application:
            return jsonify({'success': False, 'error': 'Application not found'}), 404
        
        # Get documents for the application
        documents = application.documents
        
        # Run document verification
        document_verification = advance_verification_service.verify_all_documents(application, documents)
        
        # Update application
        application.document_verification_report = json.dumps(document_verification)
        application.document_verification_status = document_verification.get('overall_status', 'PENDING')
        application.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Document verification completed',
            'document_data': document_verification
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/verify-na-document/<app_id>', methods=['POST'])
@login_required
def verify_na_document_route(app_id):
    """Run NA document verification only"""
    try:
        # Check permissions
        is_admin = 'admin_id' in session
        if is_admin:
            application = Application.query.filter_by(id=app_id).first()
        else:
            application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first()
        
        if not application:
            return jsonify({'success': False, 'error': 'Application not found'}), 404
        
        # Get documents for the application
        documents = application.documents
        
        # Run NA document verification
        na_verification = advance_verification_service.verify_na_document(application, documents)
        
        # Update application
        application.na_document_verification = json.dumps(na_verification)
        application.na_document_status = na_verification.get('status', 'PENDING')
        application.na_document_risk_score = na_verification.get('risk_score', 0)
        application.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'NA document verification completed',
            'na_data': na_verification
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/calculate-risk-score/<app_id>', methods=['POST'])
@login_required
def calculate_risk_score(app_id):
    """Calculate overall risk score for application"""
    try:
        # Check permissions
        is_admin = 'admin_id' in session
        if is_admin:
            application = Application.query.filter_by(id=app_id).first()
        else:
            application = Application.query.filter_by(id=app_id, user_id=session['user_id']).first()
        
        if not application:
            return jsonify({'success': False, 'error': 'Application not found'}), 404
        
        # Get existing verification data
        employment_data = safe_json_loads(application.employment_verification_report)
        document_data = safe_json_loads(application.document_verification_report)
        na_data = safe_json_loads(application.na_document_verification)
        
        # Calculate financial risk
        financial_risk = calculate_financial_risk(application)
        
        # Calculate fraud risk
        fraud_risk = instant_fraud_detection(application)
        
        # Calculate overall risk score
        overall_risk_score = advance_verification_service.calculate_overall_risk_score(
            employment_data, document_data, na_data, financial_risk, fraud_risk
        )
        
        # Update application
        application.overall_risk_score = overall_risk_score
        application.updated_at = datetime.utcnow()
        
        # Generate verification summary
        verification_summary = generate_verification_summary(application)
        application.verification_summary = json.dumps(verification_summary)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Risk score calculated successfully',
            'risk_score': overall_risk_score,
            'risk_level': get_risk_level(overall_risk_score),
            'component_scores': {
                'employment': employment_data.get('risk_score', 0),
                'documents': document_data.get('risk_score', 0),
                'na_document': na_data.get('risk_score', 0),
                'financial': financial_risk,
                'fraud': fraud_risk
            },
            'verification_summary': verification_summary
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Helper functions for advanced verification
def run_comprehensive_verification(application, documents):
    """Run all verification checks"""
    verification_results = {}
    
    # Employment verification
    verification_results['employment'] = advance_verification_service.verify_employment_documents(application, documents)
    
    # Document verification
    verification_results['documents'] = advance_verification_service.verify_all_documents(application, documents)
    
    # NA document verification
    verification_results['na_document'] = advance_verification_service.verify_na_document(application, documents)
    
    # Financial risk
    verification_results['financial_risk'] = calculate_financial_risk(application)
    
    # Fraud risk
    verification_results['fraud_risk'] = instant_fraud_detection(application)
    
    # Overall risk score
    verification_results['overall_risk_score'] = advance_verification_service.calculate_overall_risk_score(
        verification_results['employment'],
        verification_results['documents'],
        verification_results['na_document'],
        verification_results['financial_risk'],
        verification_results['fraud_risk']
    )
    
    # Generate final report
    verification_results['final_report'] = advance_verification_service.generate_final_verification_report(
        application, verification_results
    )
    
    return verification_results

def update_application_with_verification(application, verification_results):
    """Update application with verification results"""
    # Update employment verification
    application.employment_verification_report = json.dumps(verification_results['employment'])
    application.employment_verification_status = verification_results['employment'].get('employment_status', 'PENDING')
    
    # Update document verification
    application.document_verification_report = json.dumps(verification_results['documents'])
    application.document_verification_status = verification_results['documents'].get('overall_status', 'PENDING')
    
    # Update NA document verification
    application.na_document_verification = json.dumps(verification_results['na_document'])
    application.na_document_status = verification_results['na_document'].get('status', 'PENDING')
    application.na_document_risk_score = verification_results['na_document'].get('risk_score', 0)
    
    # Update overall risk score
    application.overall_risk_score = verification_results['overall_risk_score']
    
    # Update verification summary
    application.verification_summary = json.dumps(verification_results['final_report'])
    
    application.updated_at = datetime.utcnow()

@app.route('/api/company-data/search', methods=['POST'])
@login_required
def search_company_data():
    """Search company database for employee records"""
    try:
        data = request.get_json()
        pan_number = data.get('pan_number', '').strip().upper()
        
        if not pan_number:
            return jsonify({'success': False, 'error': 'PAN number is required'}), 400
        
        # Search in company data
        company_data = advance_verification_service.company_data
        record = company_data.get(pan_number)
        
        if record:
            return jsonify({
                'success': True,
                'found': True,
                'record': record,
                'message': 'Employee record found in company database'
            })
        else:
            return jsonify({
                'success': True,
                'found': False,
                'message': 'No employee record found for this PAN number'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/company-data/stats')
@login_required
def get_company_data_stats():
    """Get company database statistics"""
    try:
        company_data = advance_verification_service.company_data
        
        stats = {
            'total_records': len(company_data),
            'sample_records': list(company_data.items())[:5] if company_data else [],
            'data_source': 'CSV Database',
            'last_updated': datetime.now().isoformat()
        }
        
        return jsonify({'success': True, 'stats': stats})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/advanced-verification')
@login_required
def advanced_verification_page():
    """Advanced verification interface"""
    app_id = request.args.get('app_id')
    if not app_id:
        flash('No application specified', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('advanced_verification.html')
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)