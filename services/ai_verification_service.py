# services/ai_verification_service.py
import ollama
import json
import re
from typing import Dict, Any, List
from datetime import datetime

class AIVerificationService:
    def __init__(self):
        self.model_name = "mistral"
        try:
            self.client = ollama.Client()
        except Exception as e:
            print(f"⚠️  Ollama client initialization failed: {e}")
            self.client = None
    
    def generate_comprehensive_verification_report(self, application_data: Dict, documents_data: Dict) -> Dict[str, Any]:
        """Generate comprehensive KYC and document verification report using Ollama"""
        
        if not self.client:
            return self._get_fallback_verification_report()
        
        try:
            # Generate KYC Verification Report
            kyc_report = self._generate_kyc_verification(application_data)
            
            # Generate Document Verification Report
            document_report = self._generate_document_verification(documents_data)
            
            # Generate Composite Risk Score
            risk_assessment = self._generate_composite_risk_score(application_data, kyc_report, document_report)
            
            return {
                'ai_model_used': 'Ollama Mistral 7B',
                'model_analysis': 'The Ollama Mistral model was tasked with a multi-faceted analysis of the application. Its primary role was to assess consistency, identify potential red flags, and evaluate the overall coherence of the provided data.',
                'kyc_verification_report': kyc_report,
                'document_verification_report': document_report,
                'composite_risk_score': risk_assessment,
                'generated_at': datetime.now().isoformat(),
                'report_version': 'AI_VERIFICATION_V1'
            }
            
        except Exception as e:
            print(f"⚠️  AI Verification error: {e}")
            return self._get_fallback_verification_report()
    
    def _generate_kyc_verification(self, application_data: Dict) -> List[Dict]:
        """Generate KYC verification report using AI"""
        
        prompt = f"""
        ACT as a senior KYC verification analyst at a financial institution.
        Analyze this loan applicant's KYC information and provide a structured verification report.

        APPLICANT DATA:
        - Name: {application_data.get('first_name', '')} {application_data.get('last_name', '')}
        - Email: {application_data.get('email', 'N/A')}
        - Phone: {application_data.get('phone', 'N/A')}
        - Address: {application_data.get('current_address', 'N/A')}
        - PAN: {application_data.get('pan_number', 'N/A')}
        - Aadhaar: {application_data.get('aadhar_number', 'N/A')}
        - Monthly Salary: ₹{application_data.get('monthly_salary', 0):,}
        - Company: {application_data.get('company_name', 'N/A')}

        Provide analysis in JSON format with this structure:
        {{
            "kyc_checks": [
                {{
                    "check_item": "Applicant Identity",
                    "status": "Passed/Partial/Failed",
                    "details": "Detailed analysis with LLM reasoning",
                    "risk_level": "LOW/MEDIUM/HIGH"
                }},
                ... more checks ...
            ]
        }}

        Check these specific items:
        1. Applicant Identity (name consistency, institutional vs personal names)
        2. Contact Information (email format, phone validity)
        3. Address Verification (completeness, plausibility)
        4. Financial Profile (salary consistency, employment details)
        5. Document Consistency (cross-reference available data)

        Be factual and identify potential red flags.
        """
        
        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={'temperature': 0.1, 'max_tokens': 1500}
            )
            return self._parse_kyc_response(response['response'])
        except Exception as e:
            return self._get_default_kyc_checks()
    
    def _generate_document_verification(self, documents_data: Dict) -> List[Dict]:
        """Generate AI-powered document verification report"""
        
        prompt = f"""
        ACT as a senior document verification analyst.
        Analyze these loan application documents and provide verification status with AI reasoning.

        DOCUMENTS DATA:
        {json.dumps(documents_data, indent=2)}

        Provide analysis in JSON format with this structure:
        {{
            "document_checks": [
                {{
                    "document_type": "Employment Verification",
                    "verification_status": "Verified/Not Verified/Conditional",
                    "llm_reasoning": "Detailed reasoning and justification",
                    "confidence_level": "HIGH/MEDIUM/LOW"
                }},
                ... more document checks ...
            ]
        }}

        Analyze these document types:
        1. Employment Verification (consistency, supporting docs)
        2. Banking Behavior (transaction patterns, overdrafts)
        3. Loan Agreement (terms, amounts, validity)
        4. Identity Documents (KYC completeness)
        5. Income Proofs (salary slips, bank statements)

        Focus on logical consistency, completeness, and potential red flags.
        """
        
        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={'temperature': 0.1, 'max_tokens': 1500}
            )
            return self._parse_document_response(response['response'])
        except Exception as e:
            return self._get_default_document_checks()
    
    def _generate_composite_risk_score(self, application_data: Dict, kyc_report: List, document_report: List) -> List[Dict]:
        """Generate composite risk score with AI analysis"""
        
        prompt = f"""
        ACT as a senior risk analyst.
        Based on the KYC and document verification results, provide a comprehensive risk assessment.

        APPLICATION SUMMARY:
        - Loan Amount: ₹{application_data.get('loan_amount', 0):,}
        - Applicant: {application_data.get('first_name', '')} {application_data.get('last_name', '')}
        - Monthly Income: ₹{application_data.get('monthly_salary', 0):,}

        KYC VERIFICATION RESULTS:
        {json.dumps(kyc_report, indent=2)}

        DOCUMENT VERIFICATION RESULTS:
        {json.dumps(document_report, indent=2)}

        Provide risk assessment in JSON format:
        {{
            "risk_categories": [
                {{
                    "risk_category": "Data Integrity Risk",
                    "score": "LOW/MEDIUM/HIGH/VERY HIGH",
                    "llm_analysis": "Detailed risk analysis",
                    "recommendation": "Specific action items"
                }},
                ... more risk categories ...
            ],
            "overall_risk": "LOW/MEDIUM/HIGH/VERY HIGH",
            "final_recommendation": "APPROVE/REJECT/MANUAL REVIEW with reasoning"
        }}

        Assess these risk categories:
        1. Data Integrity Risk (data consistency, format validity)
        2. Fraud & Identity Risk (identity verification, document authenticity)
        3. Financial Risk (income stability, debt burden)
        4. Compliance Risk (regulatory compliance, KYC completeness)
        5. Overall Application Risk (combined assessment)

        Be thorough and provide actionable insights.
        """
        
        try:
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={'temperature': 0.1, 'max_tokens': 2000}
            )
            return self._parse_risk_response(response['response'])
        except Exception as e:
            return self._get_default_risk_assessment()
    
    def _parse_kyc_response(self, response: str) -> List[Dict]:
        """Parse KYC verification response"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get('kyc_checks', [])
            return self._get_default_kyc_checks()
        except:
            return self._get_default_kyc_checks()
    
    def _parse_document_response(self, response: str) -> List[Dict]:
        """Parse document verification response"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data.get('document_checks', [])
            return self._get_default_document_checks()
        except:
            return self._get_default_document_checks()
    
    def _parse_risk_response(self, response: str) -> List[Dict]:
        """Parse risk assessment response"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return self._get_default_risk_assessment()
        except:
            return self._get_default_risk_assessment()
    
    def _get_fallback_verification_report(self) -> Dict[str, Any]:
        """Fallback verification report"""
        return {
            'ai_model_used': 'Ollama Mistral 7B (Fallback Mode)',
            'model_analysis': 'AI analysis temporarily unavailable. Using standard verification procedures.',
            'kyc_verification_report': self._get_default_kyc_checks(),
            'document_verification_report': self._get_default_document_checks(),
            'composite_risk_score': self._get_default_risk_assessment(),
            'generated_at': datetime.now().isoformat(),
            'report_version': 'FALLBACK_VERIFICATION'
        }
    
    def _get_default_kyc_checks(self) -> List[Dict]:
        """Default KYC verification checks"""
        return [
            {
                "check_item": "Applicant Identity",
                "status": "Pending",
                "details": "KYC verification pending - AI service unavailable",
                "risk_level": "MEDIUM"
            },
            {
                "check_item": "Contact Information", 
                "status": "Pending",
                "details": "Contact verification pending",
                "risk_level": "MEDIUM"
            },
            {
                "check_item": "Address Verification",
                "status": "Pending", 
                "details": "Address verification pending",
                "risk_level": "MEDIUM"
            },
            {
                "check_item": "Financial Profile",
                "status": "Pending",
                "details": "Financial profile analysis pending",
                "risk_level": "MEDIUM"
            }
        ]
    
    def _get_default_document_checks(self) -> List[Dict]:
        """Default document verification checks"""
        return [
            {
                "document_type": "Employment Verification",
                "verification_status": "Pending",
                "llm_reasoning": "Document verification pending - AI service unavailable",
                "confidence_level": "LOW"
            },
            {
                "document_type": "Banking Behavior",
                "verification_status": "Pending",
                "llm_reasoning": "Banking behavior analysis pending",
                "confidence_level": "LOW"
            },
            {
                "document_type": "Loan Agreement", 
                "verification_status": "Pending",
                "llm_reasoning": "Loan agreement review pending",
                "confidence_level": "LOW"
            }
        ]
    
    def _get_default_risk_assessment(self) -> Dict:
        """Default risk assessment"""
        return {
            "risk_categories": [
                {
                    "risk_category": "Data Integrity Risk",
                    "score": "MEDIUM",
                    "llm_analysis": "Risk assessment pending - AI service unavailable",
                    "recommendation": "Proceed with manual verification"
                },
                {
                    "risk_category": "Fraud & Identity Risk", 
                    "score": "MEDIUM",
                    "llm_analysis": "Identity verification pending",
                    "recommendation": "Complete KYC verification"
                },
                {
                    "risk_category": "Financial Risk",
                    "score": "MEDIUM", 
                    "llm_analysis": "Financial risk assessment pending",
                    "recommendation": "Review income and employment details"
                }
            ],
            "overall_risk": "MEDIUM",
            "final_recommendation": "MANUAL REVIEW REQUIRED - AI analysis unavailable"
        }