# services/advanced_verification_service.py

import json
import random
import csv
import os
from datetime import datetime
from models import db

class AdvanceVerificationService:
    def __init__(self):
        self.risk_weights = {
            'employment': 0.25,
            'document': 0.20,
            'financial': 0.30,
            'property': 0.15,
            'fraud': 0.10
        }
        self.company_data = self._load_company_data()
    
    def _load_company_data(self):
        """Load company data from CSV file"""
        company_data = {}
        csv_path = os.path.join(os.path.dirname(__file__), 'company_data.csv')
        
        try:
            if os.path.exists(csv_path):
                with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        pan_number = row.get('pan_number', '').strip().upper()
                        if pan_number:
                            company_data[pan_number] = {
                                'employee_name': row.get('employee_name', '').strip(),
                                'company_name': row.get('company_name', '').strip(),
                                'monthly_salary': float(row.get('monthly_salary', 0))
                            }
                print(f"Loaded company data for {len(company_data)} employees")
            else:
                print(f"Company data file not found at: {csv_path}")
        except Exception as e:
            print(f"Error loading company data: {e}")
        
        return company_data
    
    def verify_employment_documents(self, application, documents):
        """Enhanced employment verification with company data matching"""
        try:
            employment_data = {
                'company_name': application.company_name,
                'monthly_salary': application.monthly_salary,
                'employment_status': 'PENDING',
                'risk_score': 0,
                'verification_details': {},
                'red_flags': [],
                'green_flags': [],
                'data_source': 'CSV Database'
            }
            
            # Get PAN number from application
            pan_number = application.pan_number.strip().upper() if application.pan_number else None
            
            if not pan_number:
                employment_data.update({
                    'employment_status': 'FAILED',
                    'risk_score': 100,
                    'red_flags': ['PAN number not provided'],
                    'verification_details': {'error': 'PAN number missing for employment verification'}
                })
                return employment_data
            
            # Check if PAN exists in company database
            if pan_number in self.company_data:
                company_record = self.company_data[pan_number]
                
                # Verify employment details
                verification_result = self._verify_employment_details(application, company_record)
                
                employment_data.update(verification_result)
                employment_data['data_source_match'] = True
                employment_data['company_record'] = company_record
                
            else:
                # PAN not found in database - use fallback verification
                employment_data.update(self._fallback_employment_verification(application, documents))
                employment_data['data_source_match'] = False
                employment_data['red_flags'].append('PAN not found in employment database')
            
            return employment_data
            
        except Exception as e:
            return {
                'employment_status': 'FAILED',
                'risk_score': 100,
                'error': str(e),
                'red_flags': ['Employment verification failed'],
                'data_source': 'Error'
            }
    
    def _verify_employment_details(self, application, company_record):
        """Verify employment details against company database record"""
        verification_result = {
            'employment_status': 'VERIFIED',
            'risk_score': 0,
            'verification_details': {},
            'red_flags': [],
            'green_flags': []
        }
        
        # Check name match
        app_full_name = f"{application.first_name} {application.last_name}".strip().upper()
        record_name = company_record['employee_name'].strip().upper()
        name_match = self._check_name_match(app_full_name, record_name)
        
        # Check company match
        app_company = application.company_name.strip().upper() if application.company_name else ""
        record_company = company_record['company_name'].strip().upper()
        company_match = app_company == record_company if app_company else False
        
        # Check salary match (within 10% tolerance)
        app_salary = application.monthly_salary
        record_salary = company_record['monthly_salary']
        salary_match = self._check_salary_match(app_salary, record_salary)
        
        # Calculate risk score based on matches
        risk_score = 0
        
        if not name_match:
            risk_score += 40
            verification_result['red_flags'].append('Name does not match employment records')
        else:
            verification_result['green_flags'].append('Name verified with employment records')
        
        if not company_match:
            risk_score += 30
            verification_result['red_flags'].append('Company name does not match employment records')
        else:
            verification_result['green_flags'].append('Company verified')
        
        if not salary_match:
            risk_score += 20
            verification_result['red_flags'].append('Salary discrepancy detected')
        else:
            verification_result['green_flags'].append('Salary verified')
        
        # Document quality check
        document_quality = self._check_document_quality([], 'salary_slips')
        risk_score += document_quality['risk'] * 10
        
        verification_result['risk_score'] = risk_score
        verification_result['verification_details'] = {
            'name_match': {
                'status': 'MATCH' if name_match else 'MISMATCH',
                'application_name': app_full_name,
                'record_name': record_name
            },
            'company_match': {
                'status': 'MATCH' if company_match else 'MISMATCH',
                'application_company': app_company,
                'record_company': record_company
            },
            'salary_match': {
                'status': 'MATCH' if salary_match else 'MISMATCH',
                'application_salary': app_salary,
                'record_salary': record_salary,
                'difference_percentage': abs((app_salary - record_salary) / record_salary * 100) if record_salary > 0 else 100
            },
            'document_quality': document_quality
        }
        
        # Determine final employment status
        if risk_score <= 20:
            verification_result['employment_status'] = 'VERIFIED'
        elif risk_score <= 50:
            verification_result['employment_status'] = 'VERIFIED_WITH_NOTES'
        else:
            verification_result['employment_status'] = 'UNDER_REVIEW'
        
        return verification_result
    
    def _fallback_employment_verification(self, application, documents):
        """Fallback employment verification when no company data is available"""
        verification_result = {
            'employment_status': 'UNDER_REVIEW',
            'risk_score': 60,  # Higher risk without database verification
            'verification_details': {},
            'red_flags': ['Employment not verified through database'],
            'green_flags': []
        }
        
        # Basic checks without company data
        salary_consistency = self._check_salary_consistency(application.monthly_salary)
        company_verification = self._verify_company(application.company_name)
        document_quality = self._check_document_quality(documents, 'salary_slips')
        
        # Calculate risk score
        employment_risk = (
            salary_consistency['risk'] * 0.4 +
            company_verification['risk'] * 0.4 +
            document_quality['risk'] * 0.2
        ) * 100
        
        verification_result['risk_score'] = employment_risk
        verification_result['verification_details'] = {
            'salary_consistency': salary_consistency,
            'company_verification': company_verification,
            'document_quality': document_quality,
            'note': 'Verified through alternative methods (database record not found)'
        }
        
        # Adjust status based on risk
        if employment_risk <= 30:
            verification_result['employment_status'] = 'VERIFIED_WITH_NOTES'
            verification_result['green_flags'].append('Basic employment verification passed')
        elif employment_risk <= 60:
            verification_result['employment_status'] = 'UNDER_REVIEW'
        else:
            verification_result['employment_status'] = 'HIGH_RISK'
        
        return verification_result
    
    def _check_name_match(self, app_name, record_name):
        """Check if names match with some flexibility for minor differences"""
        # Simple exact match first
        if app_name == record_name:
            return True
        
        # Allow for minor differences (middle names, initials, etc.)
        app_parts = set(app_name.split())
        record_parts = set(record_name.split())
        
        # If at least 2 name parts match, consider it a match
        common_parts = app_parts.intersection(record_parts)
        return len(common_parts) >= 2
    
    def _check_salary_match(self, app_salary, record_salary, tolerance=0.1):
        """Check if salaries match within tolerance"""
        if record_salary == 0:
            return False
        
        difference = abs(app_salary - record_salary)
        percentage_diff = difference / record_salary
        
        return percentage_diff <= tolerance
    
    def _check_salary_consistency(self, salary):
        """Check if salary is consistent with industry standards"""
        if salary >= 100000:
            return {'status': 'EXCELLENT', 'risk': 0.1, 'note': 'Salary well above average'}
        elif salary >= 50000:
            return {'status': 'GOOD', 'risk': 0.2, 'note': 'Salary above average'}
        elif salary >= 25000:
            return {'status': 'AVERAGE', 'risk': 0.4, 'note': 'Salary within normal range'}
        else:
            return {'status': 'LOW', 'risk': 0.8, 'note': 'Salary below average'}
    
    def _verify_company(self, company_name):
        """Verify company existence and reputation"""
        reputable_companies = ['TCS', 'Infosys', 'Wipro', 'HCL', 'Tech Mahindra', 'Google', 'Microsoft', 'Amazon', 
                              'NextGen Analytics', 'Quantum IT Solutions']
        
        if not company_name:
            return {'status': 'MISSING', 'risk': 0.9, 'note': 'Company name not provided'}
        
        company_upper = company_name.upper()
        if any(rep.upper() in company_upper for rep in reputable_companies):
            return {'status': 'VERIFIED', 'risk': 0.2, 'note': 'Company verified - good reputation'}
        else:
            return {'status': 'UNVERIFIED', 'risk': 0.6, 'note': 'Company not in verified list'}
    
    def _check_document_quality(self, documents, doc_type):
        """Check document quality and authenticity"""
        if documents and any(doc_type in doc.document_type for doc in documents):
            return {'status': 'PRESENT', 'risk': 0.2, 'note': f'{doc_type} documents uploaded'}
        else:
            return {'status': 'MISSING', 'risk': 0.8, 'note': f'{doc_type} documents not uploaded'}
    
    def verify_all_documents(self, application, documents):
        """Comprehensive document verification"""
        try:
            document_verification = {
                'overall_status': 'VERIFIED',
                'risk_score': 0,
                'verified_documents': {},
                'missing_documents': [],
                'quality_issues': [],
                'verification_details': {}
            }
            
            # Check each document type
            doc_types = ['bank_statements', 'salary_slips', 'kyc_docs', 'property_valuation_doc', 'legal_clearance']
            
            for doc_type in doc_types:
                doc_verification = self._verify_single_document(doc_type, documents)
                document_verification['verified_documents'][doc_type] = doc_verification
                
                if doc_verification['status'] != 'VERIFIED':
                    document_verification['overall_status'] = 'UNDER_REVIEW'
                    document_verification['quality_issues'].append(f"{doc_type}: {doc_verification['issue']}")
                
                document_verification['risk_score'] += doc_verification['risk_score']
            
            # Calculate average risk score
            if document_verification['verified_documents']:
                document_verification['risk_score'] /= len(document_verification['verified_documents'])
            
            return document_verification
            
        except Exception as e:
            return {
                'overall_status': 'FAILED',
                'risk_score': 100,
                'error': str(e)
            }
    
    def verify_na_document(self, application, documents):
        """Verify Non-Agricultural (NA) document"""
        try:
            na_verification = {
                'status': 'VERIFIED',
                'risk_score': 0,
                'verification_details': {},
                'issues': []
            }
            
            # Check if property is non-agricultural
            if application.is_non_agricultural:
                na_doc = next((doc for doc in documents if 'legal' in doc.document_type.lower() or 'clearance' in doc.document_type.lower()), None)
                
                if na_doc:
                    # Simulate NA document verification
                    na_verification['verification_details'] = {
                        'document_present': True,
                        'property_type': 'Non-Agricultural',
                        'zoning_clearance': 'Verified',
                        'land_use_certificate': 'Verified'
                    }
                    na_verification['risk_score'] = random.randint(0, 20)  # Low risk if document present
                else:
                    na_verification['status'] = 'MISSING'
                    na_verification['risk_score'] = 80
                    na_verification['issues'].append('NA document missing for non-agricultural property')
            else:
                na_verification['status'] = 'NOT_REQUIRED'
                na_verification['risk_score'] = 0
                na_verification['verification_details'] = {'property_type': 'Agricultural - NA document not required'}
            
            return na_verification
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'risk_score': 100,
                'error': str(e)
            }
    
    def calculate_overall_risk_score(self, employment_data, document_data, na_data, financial_risk, fraud_risk):
        """Calculate overall risk score"""
        try:
            weighted_score = (
                employment_data.get('risk_score', 0) * self.risk_weights['employment'] +
                document_data.get('risk_score', 0) * self.risk_weights['document'] +
                financial_risk * self.risk_weights['financial'] +
                na_data.get('risk_score', 0) * self.risk_weights['property'] +
                fraud_risk * self.risk_weights['fraud']
            )
            
            return min(100, max(0, weighted_score))
            
        except Exception as e:
            return 50  # Default medium risk
    
    def generate_final_verification_report(self, application, all_verification_data):
        """Generate comprehensive verification report"""
        try:
            report = {
                'timestamp': datetime.utcnow().isoformat(),
                'application_id': application.id,
                'overall_verification_status': 'COMPLETED',
                'summary': {
                    'employment_verification': all_verification_data['employment']['employment_status'],
                    'document_verification': all_verification_data['documents']['overall_status'],
                    'na_verification': all_verification_data['na_document']['status'],
                    'overall_risk_score': all_verification_data['overall_risk_score'],
                    'risk_level': self._get_risk_level(all_verification_data['overall_risk_score'])
                },
                'detailed_reports': all_verification_data,
                'recommendations': self._generate_recommendations(all_verification_data)
            }
            
            return report
            
        except Exception as e:
            return {'error': f'Report generation failed: {str(e)}'}
    
    def _verify_single_document(self, doc_type, documents):
        """Verify individual document"""
        doc = next((doc for doc in documents if doc_type in doc.document_type), None)
        
        if doc:
            # Simulate document verification
            verification_score = random.randint(10, 90)  # Simulated verification score
            status = 'VERIFIED' if verification_score >= 70 else 'REVIEW_NEEDED'
            
            return {
                'status': status,
                'risk_score': 100 - verification_score,
                'issue': 'No issues' if status == 'VERIFIED' else 'Quality needs review'
            }
        else:
            return {
                'status': 'MISSING',
                'risk_score': 80,
                'issue': 'Document not uploaded'
            }
    
    def _get_risk_level(self, risk_score):
        """Convert risk score to risk level"""
        if risk_score <= 25:
            return 'LOW'
        elif risk_score <= 50:
            return 'MEDIUM'
        elif risk_score <= 75:
            return 'HIGH'
        else:
            return 'VERY_HIGH'
    
    def _generate_recommendations(self, verification_data):
        """Generate recommendations based on verification results"""
        recommendations = []
        
        employment_data = verification_data.get('employment', {})
        
        # Employment-specific recommendations
        if not employment_data.get('data_source_match', False):
            recommendations.append('Verify employment through alternative channels')
        
        if employment_data.get('risk_score', 0) > 50:
            recommendations.append('Manual employment verification required')
        
        if verification_data['documents']['risk_score'] > 40:
            recommendations.append('Review document quality and authenticity')
        
        if verification_data['na_document']['risk_score'] > 30:
            recommendations.append('Obtain proper NA certification for property')
        
        if verification_data['overall_risk_score'] > 60:
            recommendations.append('Recommend manual underwriting review')
        elif verification_data['overall_risk_score'] <= 30:
            recommendations.append('Application appears low risk - consider fast track approval')
        
        return recommendations

# Initialize the service
