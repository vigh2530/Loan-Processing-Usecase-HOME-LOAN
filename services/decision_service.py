# services/decision_service.py

import json

class DecisionService:
    def make_decision(self, application):
        banking_report = json.loads(application.banking_analysis_report or '{}')
        fraud_report = json.loads(application.fraud_detection_report or '{}')
        
        if application.employment_status != 'VERIFIED':
            return 'REJECTED', "Employment could not be verified.", None
            
        if application.kyc_status != 'VERIFIED':
            return 'REJECTED', "KYC verification failed.", None

        if banking_report.get('status') == 'POOR':
            return 'REJECTED', f"Rejected due to poor banking behavior: {banking_report.get('summary')}", None

        if fraud_report.get('status') == 'HIGH RISK':
            return 'REJECTED', f"Application flagged for high fraud risk: {fraud_report.get('summary')}", None

        loan_term_years = 20
        loan_term_months = loan_term_years * 12
        interest_rate = 8.5 if application.cibil_score >= 780 else 9.5
        if application.gender == 'Female':
            interest_rate -= 0.25
            
        monthly_interest_rate = (interest_rate / 100) / 12
        try:
            emi = application.loan_amount * (monthly_interest_rate * (1 + monthly_interest_rate)**loan_term_months) / ((1 + monthly_interest_rate)**loan_term_months - 1)
        except (ZeroDivisionError, OverflowError):
            emi = float('inf')
        
        total_emi = application.existing_emi + emi
        dti_ratio = total_emi / application.monthly_salary if application.monthly_salary > 0 else 1
        
        if dti_ratio > 0.50:
            return 'REJECTED', f"Debt-to-Income ratio is too high ({dti_ratio:.2%}).", None

        loan_details = { 'rate': interest_rate, 'term': loan_term_years, 'emi': emi }
        return 'APPROVED', 'Application meets all verification and financial checks.', loan_details