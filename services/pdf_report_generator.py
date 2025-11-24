# services/pdf_report_generator.py
import os
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
import json

class ComprehensivePDFReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='Title',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            alignment=1  # Center
        ))
        
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='Body',
            parent=self.styles['BodyText'],
            fontSize=10,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=6
        ))
        
        self.styles.add(ParagraphStyle(
            name='RiskHigh',
            parent=self.styles['BodyText'],
            fontSize=10,
            textColor=colors.red,
            backColor=colors.HexColor('#ffe6e6')
        ))
        
        self.styles.add(ParagraphStyle(
            name='RiskMedium',
            parent=self.styles['BodyText'],
            fontSize=10,
            textColor=colors.orange,
            backColor=colors.HexColor('#fff2e6')
        ))
        
        self.styles.add(ParagraphStyle(
            name='RiskLow',
            parent=self.styles['BodyText'],
            fontSize=10,
            textColor=colors.green,
            backColor=colors.HexColor('#e6ffe6')
        ))
    
    def generate_combined_report(self, application_data, kyc_reports, risk_analysis, output_path):
        """Generate comprehensive combined report"""
        
        doc = SimpleDocTemplate(output_path, pagesize=A4, topMargin=1*inch)
        story = []
        
        # Cover Page
        story.extend(self._generate_cover_page(application_data))
        story.append(Spacer(1, 0.5*inch))
        
        # Table of Contents
        story.extend(self._generate_table_of_contents())
        story.append(Spacer(1, 0.5*inch))
        
        # Executive Summary
        story.extend(self._generate_executive_summary(application_data, kyc_reports, risk_analysis))
        story.append(Spacer(1, 0.3*inch))
        
        # KYC Reports
        story.extend(self._generate_kyc_section(kyc_reports))
        story.append(Spacer(1, 0.3*inch))
        
        # Risk Analysis
        story.extend(self._generate_risk_section(risk_analysis))
        story.append(Spacer(1, 0.3*inch))
        
        # EMI Plan
        story.extend(self._generate_emi_section(application_data))
        story.append(Spacer(1, 0.3*inch))
        
        # Recommendations
        story.extend(self._generate_recommendations_section(kyc_reports, risk_analysis))
        
        doc.build(story)
        return output_path
    
    def _generate_cover_page(self, application_data):
        """Generate cover page"""
        elements = []
        
        # Title
        title = Paragraph("LOAN APPLICATION REPORT", self.styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.5*inch))
        
        # Applicant Info
        applicant_name = f"{application_data.get('first_name', '')} {application_data.get('last_name', '')}"
        applicant_info = [
            ["Applicant Name:", applicant_name],
            ["Application ID:", application_data.get('application_id', 'N/A')],
            ["Loan Amount:", f"₹{application_data.get('loan_amount', 0):,}"],
            ["Report Date:", datetime.now().strftime('%B %d, %Y')]
        ]
        
        applicant_table = Table(applicant_info, colWidths=[2*inch, 3*inch])
        applicant_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6'))
        ]))
        
        elements.append(applicant_table)
        elements.append(Spacer(1, 1*inch))
        
        # Confidential Notice
        confidential = Paragraph(
            "<b>CONFIDENTIAL</b><br/><br/>"
            "This report contains sensitive financial and personal information. "
            "It is intended solely for the use of the applicant and authorized financial institution personnel.",
            ParagraphStyle(
                name='Confidential',
                parent=self.styles['BodyText'],
                fontSize=9,
                textColor=colors.gray,
                alignment=1
            )
        )
        elements.append(confidential)
        
        return elements
    
    def _generate_table_of_contents(self):
        """Generate table of contents"""
        elements = []
        
        toc_title = Paragraph("TABLE OF CONTENTS", self.styles['Subtitle'])
        elements.append(toc_title)
        elements.append(Spacer(1, 0.2*inch))
        
        toc_items = [
            ["1.", "Executive Summary", "2"],
            ["2.", "KYC Verification Reports", "3"],
            ["2.1", "Identity Verification", "3"],
            ["2.2", "Address Verification", "4"],
            ["2.3", "Financial Verification", "5"],
            ["3.", "Risk Analysis", "6"],
            ["3.1", "Risk Assessment", "6"],
            ["3.2", "Existing Loan Analysis", "7"],
            ["4.", "EMI Payment Plan", "8"],
            ["5.", "Recommendations", "9"]
        ]
        
        toc_table = Table(toc_items, colWidths=[0.3*inch, 4*inch, 0.5*inch])
        toc_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 9),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(toc_table)
        return elements
    
    def _generate_executive_summary(self, application_data, kyc_reports, risk_analysis):
        """Generate executive summary section"""
        elements = []
        
        title = Paragraph("EXECUTIVE SUMMARY", self.styles['Subtitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Overall Status
        kyc_summary = kyc_reports.get('summary', {})
        risk_assessment = risk_analysis.get('risk_analysis_report', {}).get('risk_assessment', {})
        
        summary_data = [
            ["Overall KYC Status:", kyc_summary.get('overall_kyc_status', 'PENDING')],
            ["Risk Grade:", risk_assessment.get('risk_grade', 'MEDIUM')],
            ["Approval Probability:", f"{risk_analysis.get('risk_analysis_report', {}).get('approval_probability', 0)}%"],
            ["Debt-to-Income Ratio:", f"{risk_analysis.get('existing_loan_analysis', {}).get('financial_ratios', {}).get('debt_to_income_ratio', 0)}%"]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 3*inch])
        summary_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e3f2fd')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#bbdefb')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bbdefb'))
        ]))
        
        elements.append(summary_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Key Findings
        key_findings = risk_analysis.get('ai_summary', {}).get('key_findings', [])
        if key_findings:
            findings_text = "<b>Key Findings:</b><br/>" + "<br/>".join([f"• {finding}" for finding in key_findings])
            findings_para = Paragraph(findings_text, self.styles['Body'])
            elements.append(findings_para)
        
        return elements
    
    def _generate_kyc_section(self, kyc_reports):
        """Generate KYC reports section"""
        elements = []
        
        title = Paragraph("KYC VERIFICATION REPORTS", self.styles['Subtitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Identity Verification
        identity_report = kyc_reports.get('identity_report', {})
        elements.extend(self._generate_kyc_subsection("Identity Verification", identity_report))
        
        # Address Verification
        address_report = kyc_reports.get('address_report', {})
        elements.extend(self._generate_kyc_subsection("Address Verification", address_report))
        
        # Financial Verification
        financial_report = kyc_reports.get('financial_report', {})
        elements.extend(self._generate_kyc_subsection("Financial Verification", financial_report))
        
        return elements
    
    def _generate_kyc_subsection(self, title, report):
        """Generate KYC subsection"""
        elements = []
        
        subtitle = Paragraph(title, self.styles['Heading3'])
        elements.append(subtitle)
        elements.append(Spacer(1, 0.1*inch))
        
        # Verification Checks Table
        checks = report.get('verification_checks', [])
        if checks:
            check_data = [["Check", "Status", "Risk Level", "Details"]]
            for check in checks:
                check_data.append([
                    check.get('check_name', ''),
                    check.get('status', ''),
                    check.get('risk_level', ''),
                    check.get('details', '')[:50] + '...' if len(check.get('details', '')) > 50 else check.get('details', '')
                ])
            
            check_table = Table(check_data, colWidths=[1.5*inch, 1*inch, 1*inch, 2.5*inch])
            check_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, -1), 'Helvetica', 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#343a40')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa'))
            ]))
            
            elements.append(check_table)
            elements.append(Spacer(1, 0.1*inch))
        
        return elements
    
    def _generate_risk_section(self, risk_analysis):
        """Generate risk analysis section"""
        elements = []
        
        title = Paragraph("RISK ANALYSIS", self.styles['Subtitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        risk_report = risk_analysis.get('risk_analysis_report', {})
        existing_loan_report = risk_analysis.get('existing_loan_analysis', {})
        
        # Risk Assessment
        risk_assessment = risk_report.get('risk_assessment', {})
        risk_data = [
            ["Risk Score:", f"{risk_assessment.get('risk_score', 0)}/100"],
            ["Risk Grade:", risk_assessment.get('risk_grade', 'MEDIUM')],
            ["Approval Probability:", f"{risk_report.get('approval_probability', 0)}%"]
        ]
        
        risk_table = Table(risk_data, colWidths=[2*inch, 3*inch])
        risk_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#fff3cd')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#ffeaa7'))
        ]))
        
        elements.append(risk_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Existing Loan Analysis
        financial_ratios = existing_loan_report.get('financial_ratios', {})
        loan_data = [
            ["Debt-to-Income Ratio:", f"{financial_ratios.get('debt_to_income_ratio', 0)}%"],
            ["Affordability Ratio:", f"{financial_ratios.get('affordability_ratio', 0)}%"],
            ["Safe Threshold:", f"{financial_ratios.get('safe_threshold', 0)}%"]
        ]
        
        loan_table = Table(loan_data, colWidths=[2*inch, 3*inch])
        loan_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#d1ecf1')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#bee5eb'))
        ]))
        
        elements.append(loan_table)
        
        return elements
    
    def _generate_emi_section(self, application_data):
        """Generate EMI plan section"""
        elements = []
        
        title = Paragraph("EMI PAYMENT PLAN", self.styles['Subtitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Calculate EMI (simplified)
        loan_amount = application_data.get('loan_amount', 0)
        interest_rate = application_data.get('interest_rate', 8.5)
        loan_term = application_data.get('loan_term_years', 20)
        
        # EMI calculation formula
        monthly_rate = interest_rate / 12 / 100
        months = loan_term * 12
        emi = (loan_amount * monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
        
        emi_data = [
            ["Loan Amount:", f"₹{loan_amount:,.2f}"],
            ["Interest Rate:", f"{interest_rate}% p.a."],
            ["Loan Term:", f"{loan_term} years"],
            ["Monthly EMI:", f"₹{emi:,.2f}"],
            ["Total Payment:", f"₹{(emi * months):,.2f}"],
            ["Total Interest:", f"₹{((emi * months) - loan_amount):,.2f}"]
        ]
        
        emi_table = Table(emi_data, colWidths=[2*inch, 3*inch])
        emi_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#d4edda')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#c3e6cb'))
        ]))
        
        elements.append(emi_table)
        
        return elements
    
    def _generate_recommendations_section(self, kyc_reports, risk_analysis):
        """Generate recommendations section"""
        elements = []
        
        title = Paragraph("RECOMMENDATIONS & NEXT STEPS", self.styles['Subtitle'])
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Collect all recommendations
        all_recommendations = []
        
        # From KYC reports
        for report_type in ['identity_report', 'address_report', 'financial_report']:
            report = kyc_reports.get(report_type, {})
            recommendations = report.get('recommendations', [])
            all_recommendations.extend(recommendations)
        
        # From risk analysis
        risk_recommendations = risk_analysis.get('risk_analysis_report', {}).get('mitigation_recommendations', [])
        all_recommendations.extend(risk_recommendations)
        
        # From existing loan analysis
        loan_recommendations = risk_analysis.get('existing_loan_analysis', {}).get('recommendations', [])
        all_recommendations.extend(loan_recommendations)
        
        # Remove duplicates
        unique_recommendations = list(dict.fromkeys(all_recommendations))
        
        # Create recommendations list
        if unique_recommendations:
            rec_text = "<br/>".join([f"• {rec}" for rec in unique_recommendations])
            rec_para = Paragraph(rec_text, self.styles['Body'])
            elements.append(rec_para)
        else:
            no_rec_para = Paragraph("No specific recommendations at this time. Application appears satisfactory.", self.styles['Body'])
            elements.append(no_rec_para)
        
        return elements