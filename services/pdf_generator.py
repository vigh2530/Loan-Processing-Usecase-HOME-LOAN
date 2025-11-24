# services/pdf_generator.py
import io
from datetime import datetime
from fpdf import FPDF
from services.ai_summary_generator import AISummaryGenerator

class CasaFlowPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'CasaFlow AI - Loan Management System', 0, 1, 'C')
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Generated on: {datetime.now().strftime("%d %b %Y %H:%M")}', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} - Confidential - AI Powered Analysis', 0, 0, 'C')
    
    def add_ai_summary_section(self, title, summary):
        """Add an AI summary section to the PDF without emojis"""
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(230, 240, 255)  # Light blue background
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(2)
        
        self.set_font('Arial', '', 9)
        self.set_text_color(0, 0, 0)  # Black text
        
        # Clean summary text of any unsupported characters
        cleaned_summary = self.clean_text(summary)
        self.multi_cell(0, 5, cleaned_summary)
        self.ln(5)
    
    def clean_text(self, text):
        """Remove unsupported characters from text"""
        if not text:
            return text
        
        # Remove emojis and other non-ASCII characters that might cause issues
        cleaned = ''.join(char for char in text if ord(char) < 128)
        return cleaned

def format_currency(amount):
    """Format currency without using ₹ symbol"""
    if amount is None:
        return "N/A"
    return "Rs. {:,.0f}".format(amount)

def save_pdf_to_buffer(pdf):
    """Helper function to save PDF to buffer with proper byte handling"""
    buffer = io.BytesIO()
    pdf_output = pdf.output(dest='S')
    
    if isinstance(pdf_output, str):
        pdf_output = pdf_output.encode('latin-1')
    
    buffer.write(pdf_output)
    buffer.seek(0)
    return buffer

def generate_credit_risk_report(application):
    try:
        pdf = CasaFlowPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'CREDIT RISK ASSESSMENT REPORT', 0, 1, 'C')
        pdf.ln(10)
        
        # Application Info
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Application Information', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        info_lines = [
            f"Application ID: #{getattr(application, 'id', 'N/A')}",
            f"Applicant Name: {getattr(application, 'first_name', '')} {getattr(application, 'last_name', '')}",
            f"Loan Amount: {format_currency(getattr(application, 'loan_amount', 0))}",
            f"Risk Score: {getattr(application, 'overall_risk_score', 'N/A')}",
            f"Status: {getattr(application, 'status', 'N/A')}"
        ]
        
        for line in info_lines:
            pdf.cell(0, 8, line, 0, 1)
        
        pdf.ln(5)
        
        # Financial Info
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Financial Information', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        financial_lines = [
            f"Monthly Salary: {format_currency(getattr(application, 'monthly_salary', 0))}" if getattr(application, 'monthly_salary', 0) else "Monthly Salary: N/A",
            f"Existing EMI: {format_currency(getattr(application, 'existing_emi', 0))}" if getattr(application, 'existing_emi', 0) else "Existing EMI: N/A",
            f"Property Value: {format_currency(getattr(application, 'property_valuation', 0))}" if getattr(application, 'property_valuation', 0) else "Property Value: N/A"
        ]
        
        for line in financial_lines:
            pdf.cell(0, 8, line, 0, 1)
        
        # AI Summary Section (without emoji)
        pdf.ln(8)
        ai_generator = AISummaryGenerator()
        ai_summary = ai_generator.generate_credit_risk_summary(application)
        pdf.add_ai_summary_section('AI CREDIT RISK ANALYSIS', ai_summary)
        
        # Risk Assessment
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Risk Assessment', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        risk_score = getattr(application, 'overall_risk_score', 0)
        if risk_score:
            risk_level = "LOW" if risk_score <= 25 else "MEDIUM" if risk_score <= 50 else "HIGH" if risk_score <= 75 else "VERY HIGH"
            pdf.cell(0, 8, f"Risk Level: {risk_level}", 0, 1)
        
        pdf.cell(0, 8, f"AI Recommendation: {'APPROVE' if getattr(application, 'status', '') == 'APPROVED' else 'REJECT' if getattr(application, 'status', '') == 'REJECTED' else 'REVIEW REQUIRED'}", 0, 1)
        
        return save_pdf_to_buffer(pdf)
        
    except Exception as e:
        return generate_error_pdf(f"Credit Risk Report Error: {str(e)}")

def generate_document_verification_report(application):
    try:
        pdf = CasaFlowPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'DOCUMENT VERIFICATION REPORT', 0, 1, 'C')
        pdf.ln(10)
        
        # Application Info
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Application Information', 0, 1)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 8, f"Application ID: #{getattr(application, 'id', 'N/A')}", 0, 1)
        pdf.cell(0, 8, f"Applicant: {getattr(application, 'first_name', '')} {getattr(application, 'last_name', '')}", 0, 1)
        pdf.cell(0, 8, f"Loan Amount: {format_currency(getattr(application, 'loan_amount', 0))}", 0, 1)
        pdf.ln(5)
        
        # Document Status
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Document Status', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        # Add document rows
        documents = getattr(application, 'documents', [])
        if documents:
            for doc in documents:
                status = getattr(doc, 'document_verification_status', 'PENDING')
                doc_type = getattr(doc, 'document_type', 'Unknown').replace('_', ' ').title()
                pdf.cell(0, 8, f"- {doc_type}: {status}", 0, 1)
        else:
            pdf.cell(0, 8, "No documents uploaded", 0, 1)
        
        # Count summary
        verified_count = len([d for d in documents if getattr(d, 'document_verification_status', '') == 'VERIFIED'])
        total_count = len(documents)
        pdf.ln(5)
        pdf.cell(0, 8, f"Documents Verified: {verified_count}/{total_count}", 0, 1)
        
        # AI Summary Section (without emoji)
        pdf.ln(8)
        ai_generator = AISummaryGenerator()
        ai_summary = ai_generator.generate_document_verification_summary(application)
        pdf.add_ai_summary_section('AI DOCUMENT ANALYSIS', ai_summary)
        
        return save_pdf_to_buffer(pdf)
        
    except Exception as e:
        return generate_error_pdf(f"Document Verification Report Error: {str(e)}")

def generate_property_verification_report(application):
    try:
        pdf = CasaFlowPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'PROPERTY VERIFICATION REPORT', 0, 1, 'C')
        pdf.ln(10)
        
        # Property Info
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Property Information', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        property_lines = [
            f"Application ID: #{getattr(application, 'id', 'N/A')}",
            f"Property Address: {getattr(application, 'property_address', 'Not Provided')}",
            f"Property Valuation: {format_currency(getattr(application, 'property_valuation', 0))}" if getattr(application, 'property_valuation', 0) else "Property Valuation: Not Provided",
            f"Loan Amount: {format_currency(getattr(application, 'loan_amount', 0))}"
        ]
        
        for line in property_lines:
            pdf.cell(0, 8, line, 0, 1)
        
        # LTV Calculation
        property_val = getattr(application, 'property_valuation', 0)
        loan_amt = getattr(application, 'loan_amount', 0)
        if property_val and loan_amt:
            ltv_ratio = (loan_amt / property_val) * 100
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, 'Loan-to-Value Analysis', 0, 1)
            pdf.set_font('Arial', '', 10)
            pdf.cell(0, 8, f"LTV Ratio: {ltv_ratio:.1f}%", 0, 1)
            assessment = "Excellent" if ltv_ratio <= 60 else "Good" if ltv_ratio <= 80 else "High"
            pdf.cell(0, 8, f"Assessment: {assessment}", 0, 1)
        
        # AI Summary Section (without emoji)
        pdf.ln(8)
        ai_generator = AISummaryGenerator()
        ai_summary = ai_generator.generate_property_verification_summary(application)
        pdf.add_ai_summary_section('AI PROPERTY ASSESSMENT', ai_summary)
        
        return save_pdf_to_buffer(pdf)
        
    except Exception as e:
        return generate_error_pdf(f"Property Verification Report Error: {str(e)}")

def generate_final_comprehensive_report(application):
    try:
        pdf = CasaFlowPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'FINAL COMPREHENSIVE REPORT', 0, 1, 'C')
        pdf.ln(10)
        
        # Summary
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Application Summary', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        summary_lines = [
            f"Application ID: #{getattr(application, 'id', 'N/A')}",
            f"Applicant: {getattr(application, 'first_name', '')} {getattr(application, 'last_name', '')}",
            f"Loan Amount: {format_currency(getattr(application, 'loan_amount', 0))}",
            f"Risk Score: {getattr(application, 'overall_risk_score', 'N/A')}",
            f"Final Status: {getattr(application, 'status', 'N/A')}",
            f"AI Recommendation: {'APPROVE' if getattr(application, 'status', '') == 'APPROVED' else 'REJECT' if getattr(application, 'status', '') == 'REJECTED' else 'REVIEW REQUIRED'}"
        ]
        
        for line in summary_lines:
            pdf.cell(0, 8, line, 0, 1)
        
        # AI Executive Summary Section (without emoji)
        pdf.ln(8)
        ai_generator = AISummaryGenerator()
        ai_summary = ai_generator.generate_final_comprehensive_summary(application)
        pdf.add_ai_summary_section('AI EXECUTIVE SUMMARY', ai_summary)
        
        # Detailed Analysis
        pdf.ln(5)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Detailed Analysis', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        analysis_text = f"""
        This comprehensive report provides a complete analysis of the loan application.
        
        Applicant Profile:
        - Name: {getattr(application, 'first_name', '')} {getattr(application, 'last_name', '')}
        - Loan Request: {format_currency(getattr(application, 'loan_amount', 0))}
        - Property: {getattr(application, 'property_address', 'Not specified')}
        
        Financial Assessment:
        - Monthly Income: {format_currency(getattr(application, 'monthly_salary', 0))}
        - Existing Liabilities: {format_currency(getattr(application, 'existing_emi', 0))}
        - Property Value: {format_currency(getattr(application, 'property_valuation', 0))}
        
        The application has been processed through CasaFlow AI's verification system
        and assigned an overall risk score of {getattr(application, 'overall_risk_score', 'N/A')}.
        """
        
        pdf.multi_cell(0, 8, analysis_text)
        
        return save_pdf_to_buffer(pdf)
        
    except Exception as e:
        return generate_error_pdf(f"Final Comprehensive Report Error: {str(e)}")

def generate_loan_agreement(application):
    try:
        pdf = CasaFlowPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'LOAN AGREEMENT', 0, 1, 'C')
        pdf.ln(10)
        
        # Agreement content
        pdf.set_font('Arial', '', 10)
        agreement_text = f"""
        This Loan Agreement is made and entered into on {datetime.now().strftime('%d %B %Y')} between:
        
        LENDER: CasaFlow Financial Services
        BORROWER: {getattr(application, 'first_name', '')} {getattr(application, 'last_name', '')}
        
        ARTICLE 1: LOAN TERMS
        
        1.1 Loan Amount: {format_currency(getattr(application, 'loan_amount', 0))}
        1.2 Purpose: Property Loan
        1.3 Property Address: {getattr(application, 'property_address', 'Not Specified')}
        1.4 Term: 20 Years
        1.5 Interest Rate: 8.5% per annum
        
        ARTICLE 2: REPAYMENT TERMS
        
        2.1 The Borrower shall repay the loan in equated monthly installments (EMI)
        2.2 First EMI due date: {datetime.now().strftime('%d %B %Y')}
        
        ARTICLE 3: SECURITY
        
        3.1 The loan is secured by the property located at {getattr(application, 'property_address', 'Not Specified')}
        3.2 Property Valuation: {format_currency(getattr(application, 'property_valuation', 0))}
        
        This agreement constitutes the entire understanding between the parties.
        """
        
        pdf.multi_cell(0, 8, agreement_text)
        
        return save_pdf_to_buffer(pdf)
        
    except Exception as e:
        return generate_error_pdf(f"Loan Agreement Error: {str(e)}")

def generate_error_pdf(error_message):
    """Generate a simple error PDF"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Error Generating Report', 0, 1)
    pdf.set_font('Arial', '', 12)
    
    # Clean error message of any unsupported characters
    cleaned_error = ''.join(char for char in error_message if ord(char) < 128)
    pdf.multi_cell(0, 10, f'Error: {cleaned_error}')
    
    return save_pdf_to_buffer(pdf)