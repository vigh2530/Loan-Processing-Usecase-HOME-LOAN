# models.py
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import uuid
from sqlalchemy import event, DDL
from sqlalchemy.ext.hybrid import hybrid_property
import re

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    mobile_number = db.Column(db.String(15), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, index=True)
    is_verified = db.Column(db.Boolean, default=False)
    otp_secret = db.Column(db.String(32))
    last_otp_sent = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    applications = db.relationship('Application', backref='user', lazy=True, 
                                 cascade='all, delete-orphan', order_by='Application.created_at.desc()')

    def __repr__(self):
        return f'<User {self.mobile_number}>'

    def to_dict(self):
        return {
            'id': self.id,
            'mobile_number': self.mobile_number,
            'email': self.email,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'applications_count': len(self.applications)
        }

class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.String(20), primary_key=True, default=lambda: f'APP{uuid.uuid4().hex[:16].upper()}')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # Personal Information
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, index=True)
    gender = db.Column(db.String(10))
    current_address = db.Column(db.Text)
    date_of_birth = db.Column(db.Date)
    
    # Residence Details
    is_rented = db.Column(db.Boolean, default=False)
    has_own_property = db.Column(db.Boolean, default=False)
    years_at_current_address = db.Column(db.Integer, default=0)
    
    # Identification
    aadhar_number = db.Column(db.String(12), nullable=False, index=True)
    pan_number = db.Column(db.String(10), nullable=False, index=True)
    
    # Financial Information
    monthly_salary = db.Column(db.Float, nullable=False)
    company_name = db.Column(db.String(200))
    employment_type = db.Column(db.String(50), default='SALARIED')  # SALARIED, SELF_EMPLOYED, BUSINESS
    experience_years = db.Column(db.Integer, default=0)
    existing_emi = db.Column(db.Float, default=0.0)
    cibil_score = db.Column(db.Integer)
    
    # DTI Validation Fields
    dti_ratio = db.Column(db.Float, default=0.0)
    eligibility_status = db.Column(db.String(50), default='PENDING', index=True)
    rejection_reason = db.Column(db.Text)
    total_existing_emi = db.Column(db.Float, default=0.0)
    proposed_emi = db.Column(db.Float, default=0.0)
    existing_loans_count = db.Column(db.Integer, default=0)
    
    # Loan Details
    loan_amount = db.Column(db.Float, nullable=False)
    property_valuation = db.Column(db.Float, nullable=False)
    property_address = db.Column(db.Text)
    is_non_agricultural = db.Column(db.Boolean, default=True)
    has_existing_mortgage = db.Column(db.Boolean, default=False)
    loan_purpose = db.Column(db.String(200), default='HOME_PURCHASE')
    
    # Application Status
    status = db.Column(db.String(20), default='PENDING', index=True)
    employment_status = db.Column(db.String(20), default='PENDING')
    kyc_status = db.Column(db.String(20), default='PENDING')
    match_score = db.Column(db.Float, default=0.0)
    confidence_score = db.Column(db.Float, default=0.0)
    
    # Reports
    banking_analysis_report = db.Column(db.Text)
    fraud_detection_report = db.Column(db.Text)
    
    # Loan Terms
    interest_rate = db.Column(db.Float)
    loan_term_years = db.Column(db.Integer)
    emi_amount = db.Column(db.Float)
    ai_analysis_report = db.Column(db.Text)
    
    # Document Verification
    na_document_verification = db.Column(db.Text)
    na_document_status = db.Column(db.String(20), default='PENDING')
    na_document_risk_score = db.Column(db.Float, default=0.0)
    
    # AI Verification Fields
    ai_verification_report = db.Column(db.Text)
    employment_verification_status = db.Column(db.String(50), default='PENDING')
    employment_verification_report = db.Column(db.Text)
    document_verification_status = db.Column(db.String(50), default='PENDING')
    document_verification_report = db.Column(db.Text)
    overall_risk_score = db.Column(db.Float)
    verification_summary = db.Column(db.Text)
    
    # AI Summaries
    credit_risk_ai_summary = db.Column(db.Text)
    document_verification_ai_summary = db.Column(db.Text)
    property_verification_ai_summary = db.Column(db.Text)
    final_comprehensive_ai_summary = db.Column(db.Text)
    ai_summary_generated_at = db.Column(db.DateTime)
    
    # EMI and Loan Details
    emi_plan_generated = db.Column(db.Boolean, default=False)
    loan_disbursement_date = db.Column(db.DateTime)
    first_emi_date = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = db.relationship('Document', backref='application', lazy=True, 
                              cascade='all, delete-orphan', order_by='Document.uploaded_at.desc()')
    emis = db.relationship('EMI', backref='application', lazy=True, 
                          cascade='all, delete-orphan', order_by='EMI.emi_number')
    existing_loans = db.relationship('ExistingLoan', backref='application', lazy=True, 
                                   cascade='all, delete-orphan')
    status_logs = db.relationship('ApplicationStatusLog', backref='application', lazy=True,
                                cascade='all, delete-orphan', order_by='ApplicationStatusLog.created_at.desc()')

    def __repr__(self):
        return f'<Application {self.id}>'

    @hybrid_property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @hybrid_property
    def loan_to_value_ratio(self):
        if self.property_valuation and self.loan_amount:
            return (self.loan_amount / self.property_valuation) * 100
        return 0.0

    @hybrid_property
    def application_age_days(self):
        if self.created_at:
            return (datetime.utcnow() - self.created_at).days
        return 0

    def to_dict(self, include_relationships=False):
        data = {
            'id': self.id,
            'user_id': self.user_id,
            'full_name': self.full_name,
            'email': self.email,
            'pan_number': self.pan_number,
            'aadhar_number': self.aadhar_number,
            'monthly_salary': self.monthly_salary,
            'loan_amount': self.loan_amount,
            'property_valuation': self.property_valuation,
            'dti_ratio': self.dti_ratio,
            'eligibility_status': self.eligibility_status,
            'status': self.status,
            'cibil_score': self.cibil_score,
            'interest_rate': self.interest_rate,
            'loan_term_years': self.loan_term_years,
            'emi_amount': self.emi_amount,
            'overall_risk_score': self.overall_risk_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'loan_to_value_ratio': round(self.loan_to_value_ratio, 2),
            'application_age_days': self.application_age_days
        }
        
        if include_relationships:
            data['documents_count'] = len(self.documents)
            data['existing_loans_count'] = len(self.existing_loans)
            data['status_logs'] = [log.to_dict() for log in self.status_logs[:5]]
            
        return data

    def update_status(self, new_status, changed_by='system', reason=None):
        """Helper method to update application status and log the change"""
        old_status = self.status
        self.status = new_status
        
        # Create status log
        status_log = ApplicationStatusLog(
            application_id=self.id,
            from_status=old_status,
            to_status=new_status,
            changed_by=changed_by,
            reason=reason
        )
        db.session.add(status_log)
        
        return status_log

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.String(20), db.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False, index=True)
    document_type = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    
    # Document Verification Fields (ADD THESE)
    verification_status = db.Column(db.String(20), default='PENDING')  # PENDING, VERIFIED, REJECTED
    verification_notes = db.Column(db.Text)
    verified_by = db.Column(db.String(100))
    verified_at = db.Column(db.DateTime)
    risk_score = db.Column(db.Float, default=0.0)  # 0.0 to 1.0
    ai_verification_report = db.Column(db.Text)
    
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Document {self.document_type} for {self.application_id}>'

class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='OPERATOR')  # OPERATOR, MANAGER, ADMIN
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime)
    login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<Admin {self.username}>'

class EMI(db.Model):
    __tablename__ = 'emis'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.String(20), db.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False, index=True)
    emi_number = db.Column(db.Integer, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    amount_due = db.Column(db.Float, nullable=False)
    principal_component = db.Column(db.Float)
    interest_component = db.Column(db.Float)
    status = db.Column(db.String(20), default='DUE', index=True)
    paid_at = db.Column(db.DateTime)
    paid_amount = db.Column(db.Float)
    late_fee = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Index for better query performance
    __table_args__ = (
        db.Index('idx_emi_due_status', 'due_date', 'status'),
        db.Index('idx_emi_application_due', 'application_id', 'due_date'),
        db.UniqueConstraint('application_id', 'emi_number', name='unique_emi_per_application')
    )

    def __repr__(self):
        return f'<EMI {self.emi_number} for {self.application_id}>'

    @hybrid_property
    def is_overdue(self):
        return self.status == 'DUE' and self.due_date < date.today()

    def to_dict(self):
        return {
            'id': self.id,
            'application_id': self.application_id,
            'emi_number': self.emi_number,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'amount_due': self.amount_due,
            'principal_component': self.principal_component,
            'interest_component': self.interest_component,
            'status': self.status,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'is_overdue': self.is_overdue,
            'late_fee': self.late_fee
        }

class CIBILData(db.Model):
    __tablename__ = 'cibil_data'
    
    id = db.Column(db.Integer, primary_key=True)
    pan_number = db.Column(db.String(10), nullable=False, unique=True, index=True)
    credit_score = db.Column(db.Integer)
    total_existing_emi = db.Column(db.Float, default=0.0)
    active_loans_count = db.Column(db.Integer, default=0)
    total_credit_limit = db.Column(db.Float)
    credit_utilization_ratio = db.Column(db.Float)
    overdue_amount = db.Column(db.Float, default=0.0)
    default_history = db.Column(db.Integer, default=0)
    data_json = db.Column(db.JSON)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<CIBILData {self.pan_number}>'

    @hybrid_property
    def credit_rating(self):
        if self.credit_score >= 800:
            return 'EXCELLENT'
        elif self.credit_score >= 750:
            return 'VERY_GOOD'
        elif self.credit_score >= 700:
            return 'GOOD'
        elif self.credit_score >= 650:
            return 'FAIR'
        else:
            return 'POOR'

    def to_dict(self):
        return {
            'pan_number': self.pan_number,
            'credit_score': self.credit_score,
            'credit_rating': self.credit_rating,
            'total_existing_emi': self.total_existing_emi,
            'active_loans_count': self.active_loans_count,
            'total_credit_limit': self.total_credit_limit,
            'credit_utilization_ratio': self.credit_utilization_ratio,
            'overdue_amount': self.overdue_amount,
            'default_history': self.default_history,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class ExistingLoan(db.Model):
    __tablename__ = 'existing_loans'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.String(20), db.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False, index=True)
    pan_number = db.Column(db.String(10), nullable=False, index=True)
    loan_type = db.Column(db.String(100), nullable=False)
    lender_name = db.Column(db.String(200))
    emi_amount = db.Column(db.Float, nullable=False)
    outstanding_amount = db.Column(db.Float)
    loan_start_date = db.Column(db.DateTime)
    loan_end_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Index for better query performance
    __table_args__ = (
        db.Index('idx_existing_loans_pan', 'pan_number', 'is_active'),
    )

    def __repr__(self):
        return f'<ExistingLoan {self.loan_type} for {self.pan_number}>'

    @hybrid_property
    def remaining_tenure_months(self):
        if self.loan_end_date and self.is_active:
            today = datetime.utcnow()
            if today < self.loan_end_date:
                months = (self.loan_end_date.year - today.year) * 12 + (self.loan_end_date.month - today.month)
                return max(0, months)
        return 0

    def to_dict(self):
        return {
            'id': self.id,
            'application_id': self.application_id,
            'pan_number': self.pan_number,
            'loan_type': self.loan_type,
            'lender_name': self.lender_name,
            'emi_amount': self.emi_amount,
            'outstanding_amount': self.outstanding_amount,
            'loan_start_date': self.loan_start_date.isoformat() if self.loan_start_date else None,
            'loan_end_date': self.loan_end_date.isoformat() if self.loan_end_date else None,
            'is_active': self.is_active,
            'remaining_tenure_months': self.remaining_tenure_months
        }

class ApplicationStatusLog(db.Model):
    __tablename__ = 'application_status_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.String(20), db.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False, index=True)
    from_status = db.Column(db.String(50))
    to_status = db.Column(db.String(50), nullable=False)
    changed_by = db.Column(db.String(100))  # 'system', 'admin', or user ID
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Index for better query performance
    __table_args__ = (
        db.Index('idx_status_log_application', 'application_id', 'created_at'),
    )

    def __repr__(self):
        return f'<StatusLog {self.application_id}: {self.from_status} -> {self.to_status}>'

    def to_dict(self):
        return {
            'id': self.id,
            'application_id': self.application_id,
            'from_status': self.from_status,
            'to_status': self.to_status,
            'changed_by': self.changed_by,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SystemConfig(db.Model):
    __tablename__ = 'system_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    config_key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    config_value = db.Column(db.Text, nullable=False)
    config_type = db.Column(db.String(50), default='STRING')  # STRING, NUMBER, BOOLEAN, JSON
    description = db.Column(db.Text)
    is_public = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(100))

    def __repr__(self):
        return f'<SystemConfig {self.config_key}>'

    def get_typed_value(self):
        """Get the config value in the proper type"""
        if self.config_type == 'NUMBER':
            try:
                return float(self.config_value)
            except (ValueError, TypeError):
                return 0
        elif self.config_type == 'BOOLEAN':
            return self.config_value.lower() in ('true', '1', 'yes')
        elif self.config_type == 'JSON':
            try:
                import json
                return json.loads(self.config_value)
            except (json.JSONDecodeError, TypeError):
                return {}
        else:
            return self.config_value

# Database triggers and indexes
def create_indexes():
    """Create additional indexes for better performance"""
    # This would be called during application startup
    pass

# Event listeners for automatic behaviors
@event.listens_for(Application, 'before_update')
def update_application_timestamp(mapper, connection, target):
    """Automatically update the updated_at timestamp"""
    target.updated_at = datetime.utcnow()

@event.listens_for(CIBILData, 'before_update')
def update_cibil_timestamp(mapper, connection, target):
    """Automatically update the last_updated timestamp for CIBIL data"""
    target.last_updated = datetime.utcnow()