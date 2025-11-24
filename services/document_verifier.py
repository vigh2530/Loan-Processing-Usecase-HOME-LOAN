import os
import re
import pdfplumber
import requests
from datetime import datetime
from flask import current_app
from services.anomaly_detector import AnomalyDetector
class DocumentVerificationService:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.anomaly_detector = AnomalyDetector() 
    def verify_document(self, document, application):
        """Complete document verification process"""
        try:
            # Step 1: Check if document is uploaded
            if not self._is_document_uploaded(document):
                return self._get_failed_verification("Document not uploaded")
            
            # Step 2: Extract content from PDF using pdfplumber
            extracted_content = self._extract_pdf_content(document)
            if not extracted_content:
                return self._get_failed_verification("Unable to extract content from PDF")
            
            # Step 3: Match content with application data
            content_match_result = self._match_content_with_application(extracted_content, application)
            
            # Step 4: AI Risk Assessment
            ai_risk_assessment = self._ai_risk_assessment(extracted_content, application, document.document_type)
            
            # Step 5: Determine final status
            verification_result = self._determine_verification_status(
                content_match_result, 
                ai_risk_assessment, 
                document.document_type
            )
            # Step 6: Anomaly Detection
            application_data = {
                'applicant_name': application.applicant_name,
                'monthly_salary': application.monthly_salary,
                'loan_amount': application.loan_amount,
                'property_valuation': application.property_valuation
            }
            
            anomaly_result = self.anomaly_detector.detect_document_anomalies(
                extracted_content, document.document_type, application_data
            )
            
            # Step 7: Determine final status considering anomalies
            verification_result = self._determine_verification_status(
                content_match_result, 
                ai_risk_assessment, 
                document.document_type,
                anomaly_result  # Include anomaly results
            )
            # Add match_score and confidence_score to result
            verification_result['anomaly_detection'] = anomaly_result
            verification_result['match_score'] = content_match_result.get('match_score', 0)
            verification_result['confidence_score'] = ai_risk_assessment.get('confidence_score', 0)
            
            return verification_result
            
        except Exception as e:
            current_app.logger.error(f"Document verification error: {str(e)}")
            return self._get_failed_verification(f"Verification error: {str(e)}")
    
    def _is_document_uploaded(self, document):
        """Check if document file exists"""
        if hasattr(document, 'file_path') and document.file_path:
            return os.path.exists(document.file_path)
        elif hasattr(document, 'content') and document.content:
            return True
        return False
    
    def _extract_pdf_content(self, document):
        """Extract text content from PDF using pdfplumber"""
        try:
            content = ""
            
            if hasattr(document, 'file_path') and document.file_path and os.path.exists(document.file_path):
                # Extract from file path using pdfplumber
                with pdfplumber.open(document.file_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            content += text + "\n"
                        
            elif hasattr(document, 'content') and document.content:
                # Extract from binary content using pdfplumber
                from io import BytesIO
                pdf_file = BytesIO(document.content)
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            content += text + "\n"
            
            return content.strip() if content else None
            
        except Exception as e:
            current_app.logger.error(f"PDF extraction error: {str(e)}")
            return None
    
    def _match_content_with_application(self, content, application):
        """Match extracted content with application data"""
        matches = {
            'applicant_name': False,
            'income': False,
            'property_value': False,
            'pan_number': False,
            'aadhaar_number': False
        }
        
        content_lower = content.lower()
        
        # Match applicant name
        if application.applicant_name:
            applicant_name_lower = application.applicant_name.lower()
            matches['applicant_name'] = applicant_name_lower in content_lower
        
        # Match income/salary
        if application.monthly_salary:
            salary_patterns = [
                str(int(application.monthly_salary)),
                f"₹{application.monthly_salary}",
                f"rs.{application.monthly_salary}",
                f"inr {application.monthly_salary}",
                f"salary: {application.monthly_salary}",
                f"income: {application.monthly_salary}"
            ]
            matches['income'] = any(pattern in content for pattern in salary_patterns if pattern)
        
        # Match property value
        if application.property_valuation:
            property_patterns = [
                str(int(application.property_valuation)),
                f"₹{application.property_valuation}",
                f"rs.{application.property_valuation}",
                f"valuation: {application.property_valuation}",
                f"value: {application.property_valuation}",
                f"price: {application.property_valuation}"
            ]
            matches['property_value'] = any(pattern in content for pattern in property_patterns if pattern)
        
        # Match PAN number
        if application.pan_number:
            matches['pan_number'] = application.pan_number.lower() in content_lower
        
        # Match Aadhaar number
        if application.aadhar_number:
            matches['aadhaar_number'] = application.aadhar_number in content
        
        # Calculate match score
        total_matches = sum(matches.values())
        match_score = (total_matches / len(matches)) * 100 if matches else 0
        
        return {
            'matches': matches,
            'match_score': match_score,
            'total_possible': len(matches),
            'actual_matches': total_matches
        }
    
    def _ai_risk_assessment(self, content, application, doc_type):
        """Use AI for advanced risk assessment"""
        try:
            prompt = f"""
            Analyze this {doc_type} document for loan application verification:
            
            Document Content Excerpt: {content[:1500]}  # Limit content length
            
            Application Details:
            - Applicant: {application.applicant_name}
            - Loan Amount: ₹{application.loan_amount}
            - Monthly Salary: ₹{application.monthly_salary}
            - Property Value: ₹{application.property_valuation}
            
            Assess the following:
            1. Document authenticity and consistency
            2. Risk factors and red flags
            3. Data consistency with application
            4. Overall verification confidence
            
            Respond in this exact JSON format:
            {{
                "risk_level": "LOW|MEDIUM|HIGH",
                "confidence_score": 0-100,
                "risk_factors": ["list", "of", "factors"],
                "verification_notes": "detailed analysis",
                "recommendation": "VERIFIED|REJECTED|REVIEW_NEEDED"
            }}
            """
            
            response = requests.post(
                self.ollama_url,
                json={
                    'model': 'mistral',
                    'prompt': prompt,
                    'stream': False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return self._parse_ai_response(response.json().get('response', ''))
            else:
                return self._get_default_risk_assessment()
                
        except Exception as e:
            current_app.logger.error(f"AI risk assessment error: {str(e)}")
            return self._get_default_risk_assessment()
    
    def _parse_ai_response(self, ai_response):
        """Parse AI response safely"""
        try:
            # Extract JSON from AI response
            import json
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return self._get_default_risk_assessment()
        except:
            return self._get_default_risk_assessment()
    
    def _get_default_risk_assessment(self):
        """Default risk assessment when AI fails"""
        return {
            "risk_level": "MEDIUM",
            "confidence_score": 50,
            "risk_factors": ["AI analysis unavailable"],
            "verification_notes": "Basic verification completed",
            "recommendation": "REVIEW_NEEDED"
        }
    
    def _determine_verification_status(self, content_match, ai_assessment, doc_type, anomaly_result):
        """Determine final verification status considering anomalies"""
        match_score = content_match.get('match_score', 0)
        ai_recommendation = ai_assessment.get('recommendation', 'REVIEW_NEEDED')
        risk_level = ai_assessment.get('risk_level', 'MEDIUM')
        confidence_score = ai_assessment.get('confidence_score', 0)
        anomaly_score = anomaly_result.get('anomaly_score', 0)
        
        # Document-specific rules
        doc_rules = {
            'BANK_STATEMENT': {'min_match_score': 40, 'min_confidence': 60, 'max_anomaly': 30},
            'SALARY_SLIP': {'min_match_score': 60, 'min_confidence': 70, 'max_anomaly': 20},
            'PAN_CARD': {'min_match_score': 80, 'min_confidence': 80, 'max_anomaly': 10},
            'AADHAAR': {'min_match_score': 80, 'min_confidence': 80, 'max_anomaly': 10},
            'PROPERTY_DOCUMENT': {'min_match_score': 50, 'min_confidence': 60, 'max_anomaly': 40},
            'KYC_DOCS': {'min_match_score': 70, 'min_confidence': 70, 'max_anomaly': 25},
            'LEGAL_CLEARANCE': {'min_match_score': 60, 'min_confidence': 65, 'max_anomaly': 35},
            'NA_DOCUMENT': {'min_match_score': 50, 'min_confidence': 60, 'max_anomaly': 45}
        }
        
        rule = doc_rules.get(doc_type, {'min_match_score': 50, 'min_confidence': 60, 'max_anomaly': 40})
        
        # Determine status considering anomalies
        has_high_anomalies = any(anom.get('severity') == 'HIGH' for anom in anomaly_result.get('anomalies', []))
        
        if (match_score >= rule['min_match_score'] and 
            confidence_score >= rule['min_confidence'] and 
            ai_recommendation == 'VERIFIED' and
            risk_level != 'HIGH' and
            anomaly_score <= rule['max_anomaly'] and
            not has_high_anomalies):
            status = 'VERIFIED'
        elif (anomaly_score > 70 or has_high_anomalies or 
              match_score < 20 or risk_level == 'HIGH'):
            status = 'REJECTED'
        else:
            status = 'UNDER_REVIEW'
        
        return {
            'status': status,
            'risk_level': risk_level,
            'match_score': match_score,
            'confidence_score': confidence_score,
            'anomaly_score': anomaly_score,
            'verified_at': datetime.utcnow(),
            'verification_reason': ai_assessment.get('verification_notes', 'Document verification completed'),
            'ai_analysis': ai_assessment,
            'anomaly_detection': anomaly_result,
            'content_matches': content_match['matches']
        }
    
    def _get_failed_verification(self, reason):
        """Return failed verification result"""
        return {
            'status': 'REJECTED',
            'risk_level': 'HIGH',
            'match_score': 0,
            'confidence_score': 0,
            'verified_at': None,
            'verification_reason': reason,
            'ai_analysis': {},
            'content_matches': {}
        }