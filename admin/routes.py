import os
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for, 
    flash, session, jsonify, current_app
)
from models import db, Application, User, Document, Admin, EMI
from services import decision_service, notification_service
from functools import wraps

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please log in as admin to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Helper function for EMI calculation (same as in app.py)
def calculate_emi(principal, annual_rate, tenure_months):
    """Calculate EMI using the standard formula"""
    try:
        monthly_rate = annual_rate / 12 / 100
        if monthly_rate == 0:  # Handle zero interest rate
            return principal / tenure_months
        
        emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months / ((1 + monthly_rate) ** tenure_months - 1)
        return round(emi, 2)
    except Exception as e:
        current_app.logger.error(f"Error calculating EMI: {e}")
        return 0

# Safe JSON loading function
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

# ===== ALL ADMIN TEMPLATE ROUTES =====

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard showing application statistics with AI insights"""
    try:
        # Get application statistics
        total_applications = Application.query.count()
        approved_count = Application.query.filter_by(status='APPROVED').count()
        rejected_count = Application.query.filter_by(status='REJECTED').count()
        pending_count = Application.query.filter_by(status='PENDING').count()
        
        # AI-specific statistics
        high_risk_count = Application.query.filter(Application.overall_risk_score > 75).count()
        auto_approved = Application.query.filter(
            Application.status == 'APPROVED', 
            Application.overall_risk_score <= 25
        ).count()
        
        # Get risk distribution for visualization
        risk_distribution = {
            'low_risk': Application.query.filter(Application.overall_risk_score <= 25).count(),
            'medium_risk': Application.query.filter(
                (Application.overall_risk_score > 25) & 
                (Application.overall_risk_score <= 50)
            ).count(),
            'high_risk': Application.query.filter(
                (Application.overall_risk_score > 50) & 
                (Application.overall_risk_score <= 75)
            ).count(),
            'very_high_risk': Application.query.filter(Application.overall_risk_score > 75).count()
        }
        
        # Get monthly application trends
        monthly_trends = []
        for i in range(6):
            month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
            month_end = month_start + timedelta(days=30)
            month_count = Application.query.filter(
                Application.created_at >= month_start,
                Application.created_at < month_end
            ).count()
            monthly_trends.append({
                'month': month_start.strftime('%b %Y'),
                'count': month_count
            })
        monthly_trends.reverse()
        
        stats = {
            'total_applications': total_applications,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'pending_count': pending_count,
            'approval_rate': (approved_count / total_applications * 100) if total_applications > 0 else 0,
            'high_risk_count': high_risk_count,
            'auto_approved': auto_approved,
            'risk_distribution': risk_distribution,
            'monthly_trends': monthly_trends
        }
        
        # Get recent applications (last 20)
        recent_apps = Application.query.order_by(Application.created_at.desc()).limit(20).all()
        
        return render_template('admin/dashboard.html', 
                             stats=stats, 
                             applications=recent_apps)
    
    except Exception as e:
        current_app.logger.error(f"Error loading admin dashboard: {str(e)}")
        flash('Error loading dashboard.', 'error')
        return render_template('admin/dashboard.html', stats={}, applications=[])

@admin_bp.route('/applications')
@admin_required
def applications():
    """View all applications with filtering options"""
    try:
        status_filter = request.args.get('status', 'all')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Build query based on filters
        if status_filter == 'all':
            applications_query = Application.query
        else:
            applications_query = Application.query.filter_by(status=status_filter.upper())
        
        # Paginate results
        applications_paginated = applications_query.order_by(
            Application.created_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
        
        # Get counts for each status
        status_counts = {
            'all': Application.query.count(),
            'pending': Application.query.filter_by(status='PENDING').count(),
            'approved': Application.query.filter_by(status='APPROVED').count(),
            'rejected': Application.query.filter_by(status='REJECTED').count()
        }
        
        return render_template('admin/applications.html',
                             applications=applications_paginated,
                             status_counts=status_counts,
                             current_status=status_filter)
    
    except Exception as e:
        current_app.logger.error(f"Error loading applications list: {str(e)}")
        flash('Error loading applications.', 'error')
        return render_template('admin/applications.html', 
                             applications=[], 
                             status_counts={}, 
                             current_status='all')

@admin_bp.route('/application/<app_id>/detail')
@admin_required
def application_detail(app_id):
    """View detailed application information"""
    try:
        application = Application.query.filter_by(id=app_id).first_or_404()
        user = User.query.get(application.user_id)
        
        # Load all reports
        banking_report = safe_json_loads(application.banking_analysis_report)
        fraud_report = safe_json_loads(application.fraud_detection_report)
        credit_report = safe_json_loads(application.ai_analysis_report)
        employment_report = safe_json_loads(application.employment_verification_report)
        document_report = safe_json_loads(application.document_verification_report)
        na_report = safe_json_loads(application.na_document_verification)
        verification_summary = safe_json_loads(application.verification_summary)
        
        # Get documents
        documents = application.documents
        
        # Calculate amortization schedule if approved
        amortization_schedule = []
        if application.status == 'APPROVED' and application.interest_rate:
            try:
                tenure_months = application.loan_term_years * 12
                emi = application.emi_amount or calculate_emi(application.loan_amount, application.interest_rate, tenure_months)
                amortization_schedule = []
                balance = application.loan_amount
                monthly_rate = application.interest_rate / 12 / 100
                start_date = datetime.now()
                
                for month in range(1, tenure_months + 1):
                    interest = balance * monthly_rate
                    principal_component = emi - interest
                    
                    if month == tenure_months:
                        principal_component = balance
                        emi_adjusted = principal_component + interest
                        balance = 0
                    else:
                        emi_adjusted = emi
                        balance -= principal_component
                    
                    amortization_schedule.append({
                        'month': month,
                        'date': (start_date + relativedelta(months=month)).strftime('%d-%b-%Y'),
                        'emi': round(emi_adjusted, 2),
                        'principal': round(principal_component, 2),
                        'interest': round(interest, 2),
                        'balance': max(round(balance, 2), 0)
                    })
            except Exception as e:
                current_app.logger.error(f"Error generating amortization schedule: {e}")
                amortization_schedule = []
        
        return render_template('admin/application_detail.html',
                             application=application,
                             user=user,
                             banking_report=banking_report,
                             fraud_report=fraud_report,
                             credit_report=credit_report,
                             employment_report=employment_report,
                             document_report=document_report,
                             na_report=na_report,
                             verification_summary=verification_summary,
                             documents=documents,
                             amortization_schedule=amortization_schedule)
    
    except Exception as e:
        current_app.logger.error(f"Error loading application detail {app_id}: {str(e)}")
        flash('Error loading application details.', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/application/<app_id>/review', methods=['GET', 'POST'])
@admin_required
def review_application(app_id):
    """Admin review and decision making for applications"""
    try:
        application = Application.query.filter_by(id=app_id).first_or_404()
        
        if request.method == 'POST':
            new_status = request.form.get('status')
            admin_notes = request.form.get('admin_notes')
            interest_rate = request.form.get('interest_rate')
            loan_term_years = request.form.get('loan_term_years')
            
            # Update application status
            application.status = new_status
            application.admin_review_notes = admin_notes
            
            if new_status == 'APPROVED' and interest_rate and loan_term_years:
                application.interest_rate = float(interest_rate)
                application.loan_term_years = int(loan_term_years)
                application.emi_amount = calculate_emi(
                    application.loan_amount, 
                    application.interest_rate, 
                    application.loan_term_years * 12
                )
                
                # Create EMI records
                EMI.query.filter_by(application_id=application.id).delete()
                for i in range(1, application.loan_term_years * 12 + 1):
                    due_date = datetime.utcnow().date() + relativedelta(months=i)
                    new_emi_record = EMI(
                        application_id=application.id,
                        emi_number=i,
                        due_date=due_date,
                        amount_due=application.emi_amount,
                        status='DUE'
                    )
                    db.session.add(new_emi_record)
            
            application.reviewed_by_admin_id = session['admin_id']
            application.reviewed_at = datetime.utcnow()
            
            db.session.commit()
            
            # Send notification to user
            notification_service.send_decision_notification(
                application, 
                f"Application reviewed by admin. Status: {new_status}. Notes: {admin_notes}"
            )
            
            flash(f'Application #{application.id} status updated to {new_status}', 'success')
            return redirect(url_for('admin.dashboard'))
        
        # GET request - load all reports for the review
        banking_report = safe_json_loads(application.banking_analysis_report)
        fraud_report = safe_json_loads(application.fraud_detection_report)
        credit_report = safe_json_loads(application.ai_analysis_report)
        employment_report = safe_json_loads(application.employment_verification_report)
        document_report = safe_json_loads(application.document_verification_report)
        na_report = safe_json_loads(application.na_document_verification)
        verification_summary = safe_json_loads(application.verification_summary)
        
        return render_template('admin/application_review.html',
                             application=application,
                             banking_report=banking_report,
                             fraud_report=fraud_report,
                             credit_report=credit_report,
                             employment_report=employment_report,
                             document_report=document_report,
                             na_report=na_report,
                             verification_summary=verification_summary)
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in admin review for application {app_id}: {str(e)}")
        flash(f'Error reviewing application: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/application/<app_id>/approve', methods=['POST'])
@admin_required
def approve_application(app_id):
    """Manually approve an application"""
    try:
        application = Application.query.filter_by(id=app_id).first_or_404()
        
        # Get approval parameters from form
        interest_rate = float(request.form.get('interest_rate', 8.5))
        loan_term_years = int(request.form.get('loan_term_years', 5))
        admin_notes = request.form.get('admin_notes', 'Manually approved by admin')
        
        # Calculate EMI
        emi_amount = calculate_emi(application.loan_amount, interest_rate, loan_term_years * 12)
        
        # Update application
        application.status = 'APPROVED'
        application.interest_rate = interest_rate
        application.loan_term_years = loan_term_years
        application.emi_amount = emi_amount
        application.admin_review_notes = admin_notes
        application.reviewed_by_admin_id = session['admin_id']
        application.reviewed_at = datetime.utcnow()
        
        # Create EMI records
        EMI.query.filter_by(application_id=application.id).delete()
        for i in range(1, loan_term_years * 12 + 1):
            due_date = datetime.utcnow().date() + relativedelta(months=i)
            new_emi_record = EMI(
                application_id=application.id,
                emi_number=i,
                due_date=due_date,
                amount_due=emi_amount,
                status='DUE'
            )
            db.session.add(new_emi_record)
        
        db.session.commit()
        
        # Send notification
        notification_service.send_decision_notification(
            application, 
            f"Application approved by admin. Interest Rate: {interest_rate}%, EMI: ₹{emi_amount:,.2f}"
        )
        
        flash(f'Application #{application.id} approved successfully!', 'success')
        return redirect(url_for('admin.dashboard'))
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving application {app_id}: {str(e)}")
        flash(f'Error approving application: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/application/<app_id>/reject', methods=['POST'])
@admin_required
def reject_application(app_id):
    """Manually reject an application"""
    try:
        application = Application.query.filter_by(id=app_id).first_or_404()
        rejection_reason = request.form.get('rejection_reason', 'Rejected by admin')
        
        # Update application
        application.status = 'REJECTED'
        application.admin_review_notes = rejection_reason
        application.reviewed_by_admin_id = session['admin_id']
        application.reviewed_at = datetime.utcnow()
        
        db.session.commit()
        
        # Send notification
        notification_service.send_decision_notification(
            application, 
            f"Application rejected by admin. Reason: {rejection_reason}"
        )
        
        flash(f'Application #{application.id} rejected.', 'success')
        return redirect(url_for('admin.dashboard'))
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error rejecting application {app_id}: {str(e)}")
        flash(f'Error rejecting application: {str(e)}', 'error')
        return redirect(url_for('admin.dashboard'))

@admin_bp.route('/application/<app_id>/verify-documents', methods=['POST'])
@admin_required
def verify_documents(app_id):
    """Manually verify documents"""
    try:
        application = Application.query.filter_by(id=app_id).first_or_404()
        
        # Get verification results from form
        document_status = request.form.get('document_status')
        verification_notes = request.form.get('verification_notes', '')
        
        # Update document verification status
        application.document_verification_status = document_status
        if verification_notes:
            current_notes = application.admin_review_notes or ''
            application.admin_review_notes = f"{current_notes}\nDocument Verification: {verification_notes}".strip()
        
        db.session.commit()
        
        flash(f'Documents for application #{application.id} marked as {document_status}', 'success')
        return redirect(url_for('admin.review_application', app_id=app_id))
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error verifying documents for {app_id}: {str(e)}")
        flash(f'Error verifying documents: {str(e)}', 'error')
        return redirect(url_for('admin.review_application', app_id=app_id))

@admin_bp.route('/reports')
@admin_required
def application_reports():
    """Generate comprehensive application reports and analytics"""
    try:
        # Overall statistics
        total_applications = Application.query.count()
        approved_applications = Application.query.filter_by(status='APPROVED').count()
        rejected_applications = Application.query.filter_by(status='REJECTED').count()
        pending_applications = Application.query.filter_by(status='PENDING').count()
        
        # Risk analysis
        low_risk_count = Application.query.filter(Application.overall_risk_score <= 25).count()
        medium_risk_count = Application.query.filter(
            (Application.overall_risk_score > 25) & 
            (Application.overall_risk_score <= 50)
        ).count()
        high_risk_count = Application.query.filter(
            (Application.overall_risk_score > 50) & 
            (Application.overall_risk_score <= 75)
        ).count()
        very_high_risk_count = Application.query.filter(Application.overall_risk_score > 75).count()
        
        # Monthly trends
        monthly_data = []
        for i in range(6):
            month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
            month_end = month_start + timedelta(days=30)
            
            month_total = Application.query.filter(
                Application.created_at >= month_start,
                Application.created_at < month_end
            ).count()
            
            month_approved = Application.query.filter(
                Application.created_at >= month_start,
                Application.created_at < month_end,
                Application.status == 'APPROVED'
            ).count()
            
            monthly_data.append({
                'month': month_start.strftime('%b %Y'),
                'total': month_total,
                'approved': month_approved,
                'approval_rate': (month_approved / month_total * 100) if month_total > 0 else 0
            })
        monthly_data.reverse()
        
        # Loan amount statistics
        total_loan_amount = db.session.query(db.func.sum(Application.loan_amount)).scalar() or 0
        avg_loan_amount = db.session.query(db.func.avg(Application.loan_amount)).scalar() or 0
        
        # Recent high-risk applications
        high_risk_apps = Application.query.filter(
            Application.overall_risk_score > 75
        ).order_by(Application.created_at.desc()).limit(10).all()
        
        # Document verification status
        documents_verified = Application.query.filter_by(document_verification_status='VERIFIED').count()
        documents_pending = Application.query.filter_by(document_verification_status='PENDING').count()
        documents_review = Application.query.filter_by(document_verification_status='REVIEW_NEEDED').count()
        
        reports_data = {
            'total_applications': total_applications,
            'approved_applications': approved_applications,
            'rejected_applications': rejected_applications,
            'pending_applications': pending_applications,
            'approval_rate': (approved_applications / total_applications * 100) if total_applications > 0 else 0,
            'risk_distribution': {
                'low_risk': low_risk_count,
                'medium_risk': medium_risk_count,
                'high_risk': high_risk_count,
                'very_high_risk': very_high_risk_count
            },
            'monthly_trends': monthly_data,
            'loan_statistics': {
                'total_loan_amount': total_loan_amount,
                'avg_loan_amount': avg_loan_amount
            },
            'high_risk_applications': high_risk_apps,
            'document_verification': {
                'verified': documents_verified,
                'pending': documents_pending,
                'review_needed': documents_review
            }
        }
        
        return render_template('admin/application_reports.html', reports=reports_data)
    
    except Exception as e:
        current_app.logger.error(f"Error generating admin reports: {str(e)}")
        flash('Error generating reports.', 'error')
        return render_template('admin/application_reports.html', reports={})

@admin_bp.route('/logout')
def admin_logout():
    """Admin logout route"""
    session.pop('admin_id', None)
    session.pop('admin_logged_in', None)
    flash('You have been logged out from admin panel.', 'success')
    return redirect(url_for('login'))

# API endpoints for admin
@admin_bp.route('/api/applications/stats')
@admin_required
def api_application_stats():
    """API endpoint for application statistics"""
    try:
        # Weekly application counts
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        
        weekly_stats = {
            'total': Application.query.count(),
            'last_week': Application.query.filter(Application.created_at >= one_week_ago).count(),
            'approved': Application.query.filter_by(status='APPROVED').count(),
            'pending': Application.query.filter_by(status='PENDING').count(),
            'rejected': Application.query.filter_by(status='REJECTED').count()
        }
        
        return jsonify(weekly_stats)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

from services.document_verifier import DocumentVerificationService

@admin_bp.route('/application/<app_id>/verify-documents', methods=['POST'])
def verify_application_documents(app_id):
    """Verify all documents for an application"""
    try:
        application = Application.query.filter_by(id=app_id).first()
        if not application:
            return jsonify({"error": "Application not found"}), 404
        
        verifier = DocumentVerificationService()
        results = []
        
        for document in application.documents:
            # Verify each document
            verification_result = verifier.verify_document(
                document_data={
                    'content': document.content,  # Adjust based on your document model
                    'file_type': document.file_type,
                    'file_size': document.file_size,
                    'metadata': document.metadata if hasattr(document, 'metadata') else {}
                },
                document_type=document.document_type
            )
            
            # Update document status
            document.document_verification_status = verification_result['status']
            document.verification_reason = verification_result['reason']
            document.risk_level = verification_result['risk_level']
            document.verified_at = verification_result['verified_at']
            document.ai_analysis = verification_result['ai_analysis']
            
            results.append({
                'document_type': document.document_type,
                'status': verification_result['status'],
                'risk_level': verification_result['risk_level']
            })
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": f"Verified {len(results)} documents",
            "results": results
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@admin_bp.route('/document/<doc_id>/verify', methods=['POST'])
def verify_single_document(doc_id):
    """Verify a single document"""
    try:
        document = Document.query.filter_by(id=doc_id).first()
        if not document:
            return jsonify({"error": "Document not found"}), 404
        
        verifier = DocumentVerificationService()
        verification_result = verifier.verify_document(
            document_data={
                'content': document.content,
                'file_type': document.file_type,
                'file_size': document.file_size,
                'metadata': getattr(document, 'metadata', {})
            },
            document_type=document.document_type
        )
        
        # Update document
        document.document_verification_status = verification_result['status']
        document.verification_reason = verification_result['reason']
        document.risk_level = verification_result['risk_level']
        document.verified_at = verification_result['verified_at']
        document.ai_analysis = verification_result['ai_analysis']
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "document_type": document.document_type,
            "status": verification_result['status'],
            "risk_level": verification_result['risk_level'],
            "reason": verification_result['reason']
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500