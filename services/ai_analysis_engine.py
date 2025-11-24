# services/ai_analysis.py
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


class EnhancedRiskEngine:
    """Enhanced risk assessment engine with AI capabilities"""
    
    def __init__(self):
        self.risk_factors = {
            'credit_score': {'weight': 0.25, 'threshold': 750},
            'income_stability': {'weight': 0.20, 'threshold': 0.5},
            'employment_history': {'weight': 0.15, 'threshold': 2},
            'debt_to_income': {'weight': 0.20, 'threshold': 0.4},
            'loan_to_value': {'weight': 0.20, 'threshold': 0.8}
        }
    
    def calculate_risk_score(self, application_data):
        """Calculate comprehensive risk score"""
        try:
            risk_components = {}
            total_score = 0
            
            # Credit Score Component
            credit_score = application_data.get('cibil_score', 0)
            credit_risk = max(0, (850 - credit_score) / 100)
            risk_components['credit_risk'] = credit_risk
            total_score += credit_risk * self.risk_factors['credit_score']['weight']
            
            # Income Stability Component
            monthly_salary = application_data.get('monthly_salary', 0)
            loan_amount = application_data.get('loan_amount', 1)
            income_ratio = monthly_salary / (loan_amount / 60) if loan_amount > 0 else 0
            income_risk = max(0, 1 - income_ratio)
            risk_components['income_risk'] = income_risk
            total_score += income_risk * self.risk_factors['income_stability']['weight']
            
            # Debt-to-Income Component
            existing_emis = application_data.get('existing_emis', 0)
            dti_ratio = existing_emis / monthly_salary if monthly_salary > 0 else 1
            dti_risk = min(1, dti_ratio / 0.6)
            risk_components['dti_risk'] = dti_risk
            total_score += dti_risk * self.risk_factors['debt_to_income']['weight']
            
            # Loan-to-Value Component
            property_value = application_data.get('property_valuation', 0)
            ltv_ratio = loan_amount / property_value if property_value > 0 else 1
            ltv_risk = min(1, ltv_ratio / 0.9)
            risk_components['ltv_risk'] = ltv_risk
            total_score += ltv_risk * self.risk_factors['loan_to_value']['weight']
            
            # Employment History Component
            employment_years = application_data.get('employment_years', 0)
            employment_risk = max(0, 1 - (employment_years / 5))
            risk_components['employment_risk'] = employment_risk
            total_score += employment_risk * self.risk_factors['employment_history']['weight']
            
            # Normalize to 0-100 scale
            final_score = min(100, total_score * 100)
            
            return {
                'risk_score': round(final_score, 2),
                'risk_grade': self._get_risk_grade(final_score),
                'risk_components': risk_components,
                'recommendation': self._get_risk_recommendation(final_score)
            }
            
        except Exception as e:
            return {
                'risk_score': 50,
                'risk_grade': 'MEDIUM',
                'risk_components': {},
                'recommendation': 'Manual review required - risk calculation error',
                'error': str(e)
            }
    
    def _get_risk_grade(self, score):
        """Convert risk score to grade"""
        if score <= 25:
            return 'LOW'
        elif score <= 50:
            return 'MEDIUM'
        elif score <= 75:
            return 'HIGH'
        else:
            return 'VERY_HIGH'
    
    def _get_risk_recommendation(self, score):
        """Get recommendation based on risk score"""
        if score <= 25:
            return "STRONG APPROVAL - Low risk profile"
        elif score <= 50:
            return "APPROVAL - Moderate risk, standard terms"
        elif score <= 75:
            return "CONDITIONAL APPROVAL - Higher risk, consider additional collateral"
        else:
            return "REJECT - Very high risk profile"


class ProfessionalPDFReport:
    """Professional PDF report generator"""
    
    def generate_ai_analysis_report(self, analysis_results):
        """Generate comprehensive PDF report from AI analysis"""
        try:
            report_data = {
                'report_id': f"AI-ANALYSIS-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                'generated_at': datetime.now().isoformat(),
                'summary': self._generate_executive_summary(analysis_results),
                'risk_assessment': analysis_results.get('risk_assessment', {}),
                'verification_analysis': analysis_results.get('verification_analysis', {}),
                'ai_insights': analysis_results.get('ai_insights', {}),
                'recommendations': self._generate_recommendations(analysis_results)
            }
            return report_data
        except Exception as e:
            return {
                'error': f"PDF report generation failed: {str(e)}",
                'fallback_report': analysis_results
            }
    
    def _generate_executive_summary(self, analysis_results):
        """Generate executive summary"""
        risk_grade = analysis_results.get('risk_assessment', {}).get('risk_grade', 'UNKNOWN')
        verification_status = analysis_results.get('verification_analysis', {}).get('success', False)
        
        return {
            'overall_risk': risk_grade,
            'verification_complete': verification_status,
            'key_findings': self._extract_key_findings(analysis_results),
            'decision_support': self._get_decision_support(risk_grade)
        }
    
    def _extract_key_findings(self, analysis_results):
        """Extract key findings from analysis"""
        findings = []
        
        risk_score = analysis_results.get('risk_assessment', {}).get('risk_score', 0)
        if risk_score > 75:
            findings.append("High risk score detected - requires careful review")
        
        verification = analysis_results.get('verification_analysis', {})
        if not verification.get('success', False):
            findings.append("AI verification incomplete - manual review recommended")
        
        return findings if findings else ["No critical issues detected"]
    
    def _generate_recommendations(self, analysis_results):
        """Generate actionable recommendations"""
        recommendations = []
        risk_grade = analysis_results.get('risk_assessment', {}).get('risk_grade', 'MEDIUM')
        
        if risk_grade in ['HIGH', 'VERY_HIGH']:
            recommendations.append("Consider additional collateral or co-applicant")
            recommendations.append("Verify employment and income documents manually")
            recommendations.append("Request additional bank statements")
        
        if risk_grade == 'LOW':
            recommendations.append("Proceed with standard approval process")
            recommendations.append("Consider preferential interest rates")
        
        return recommendations if recommendations else ["Proceed with standard underwriting process"]
    
    def _get_decision_support(self, risk_grade):
        """Get decision support based on risk grade"""
        decision_map = {
            'LOW': 'AUTO_APPROVAL',
            'MEDIUM': 'STANDARD_APPROVAL', 
            'HIGH': 'CONDITIONAL_APPROVAL',
            'VERY_HIGH': 'MANUAL_REVIEW',
            'UNKNOWN': 'MANUAL_REVIEW'
        }
        return decision_map.get(risk_grade, 'MANUAL_REVIEW')


class OllamaMistralService:
    """Ollama Mistral AI service for advanced analysis"""
    
    def __init__(self):
        try:
            self.client = ollama.Client()
            self.model_name = "mistral"
        except Exception as e:
            print(f"⚠️  Ollama initialization failed: {e}")
            self.client = None
    
    def analyze_application_patterns(self, application_data):
        """Analyze application patterns using Mistral AI"""
        if not self.client:
            return self._get_fallback_analysis()
        
        try:
            prompt = self._build_analysis_prompt(application_data)
            response = self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={'temperature': 0.1, 'max_tokens': 1000}
            )
            return self._parse_ai_response(response['response'])
        except Exception as e:
            print(f"⚠️  AI analysis failed: {e}")
            return self._get_fallback_analysis()
    
    def _build_analysis_prompt(self, application_data):
        """Build analysis prompt for Mistral"""
        return f"""
        ACT as a senior loan risk analyst. Analyze this home loan application and provide insights.

        APPLICATION DATA:
        - Applicant: {application_data.get('first_name', '')} {application_data.get('last_name', '')}
        - Age: {application_data.get('age', 'N/A')}
        - Monthly Salary: ₹{application_data.get('monthly_salary', 0):,}
        - Loan Amount: ₹{application_data.get('loan_amount', 0):,}
        - Property Value: ₹{application_data.get('property_valuation', 0):,}
        - CIBIL Score: {application_data.get('cibil_score', 'N/A')}
        - Employment: {application_data.get('company_name', 'N/A')} ({application_data.get('employment_years', 0)} years)

        Provide analysis in this JSON format:
        {{
            "risk_insights": ["list of key risk insights"],
            "strengths": ["list of application strengths"],
            "red_flags": ["list of potential red flags"],
            "ai_recommendation": "APPROVE/REJECT/MANUAL_REVIEW with reasoning"
        }}

        Focus on:
        1. Income stability and adequacy for loan amount
        2. Credit history quality
        3. Employment stability
        4. Property valuation consistency
        5. Overall application coherence

        Be objective and data-driven.
        """
    
    def _parse_ai_response(self, response):
        """Parse AI response"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return self._get_fallback_analysis()
        except:
            return self._get_fallback_analysis()
    
    def _get_fallback_analysis(self):
        """Fallback analysis when AI is unavailable"""
        return {
            "risk_insights": ["AI analysis temporarily unavailable"],
            "strengths": ["Manual review required"],
            "red_flags": ["None identified through automated checks"],
            "ai_recommendation": "MANUAL_REVIEW - AI service unavailable"
        }


class CasaFlowAIAnalyzer:
    """Main AI Analysis Engine for CasaFlow Loan Processing"""
    
    def __init__(self):
        self.risk_thresholds = {
            'cibil_min': 750,
            'salary_to_emi_ratio': 0.5,
            'loan_to_value_max': 0.8
        }
        # Initialize all AI services
        self.risk_engine = EnhancedRiskEngine()
        self.pdf_reporter = ProfessionalPDFReport()
        self.ollama_service = OllamaMistralService()
        self.verification_service = AIVerificationService()  # NEW
    
    def analyze_application(self, application_data):
        """Comprehensive AI analysis of loan application with enhanced AI capabilities"""
        try:
            # Run traditional analysis
            traditional_analysis = self._run_traditional_analysis(application_data)
            
            # Run enhanced AI analysis
            ai_analysis = self._run_enhanced_ai_analysis(application_data)
            
            # Run AI Verification Analysis (NEW)
            verification_analysis = self._run_ai_verification_analysis(application_data)
            
            # Combine results
            combined_analysis = self._combine_analyses(
                traditional_analysis, ai_analysis, verification_analysis, application_data
            )
            
            # Generate professional report
            final_report = self.pdf_reporter.generate_ai_analysis_report(combined_analysis)
            
            return final_report
            
        except Exception as e:
            return self._get_error_analysis(str(e))
    
    def _run_traditional_analysis(self, application_data):
        """Run traditional financial analysis"""
        try:
            # Basic eligibility checks
            cibil_score = application_data.get('cibil_score', 0)
            monthly_salary = application_data.get('monthly_salary', 0)
            loan_amount = application_data.get('loan_amount', 0)
            property_value = application_data.get('property_valuation', 0)
            
            # Calculate ratios
            ltv_ratio = loan_amount / property_value if property_value > 0 else 0
            eligible_loan_amount = monthly_salary * 60  # Standard 5-year multiplier
            
            # Check thresholds
            cibil_eligible = cibil_score >= self.risk_thresholds['cibil_min']
            ltv_eligible = ltv_ratio <= self.risk_thresholds['loan_to_value_max']
            loan_affordable = loan_amount <= eligible_loan_amount
            
            return {
                'analysis_type': 'TRADITIONAL',
                'cibil_eligible': cibil_eligible,
                'ltv_eligible': ltv_eligible,
                'loan_affordable': loan_affordable,
                'calculated_ratios': {
                    'ltv_ratio': round(ltv_ratio, 3),
                    'eligible_loan_amount': eligible_loan_amount,
                    'salary_multiplier': 60
                },
                'threshold_checks': {
                    'cibil_min_met': cibil_eligible,
                    'ltv_max_met': ltv_eligible,
                    'affordability_met': loan_affordable
                }
            }
        except Exception as e:
            return {
                'analysis_type': 'TRADITIONAL',
                'error': str(e),
                'cibil_eligible': False,
                'ltv_eligible': False,
                'loan_affordable': False
            }
    
    def _run_enhanced_ai_analysis(self, application_data):
        """Run enhanced AI-powered analysis"""
        try:
            # Calculate risk score
            risk_assessment = self.risk_engine.calculate_risk_score(application_data)
            
            # Get AI insights
            ai_insights = self.ollama_service.analyze_application_patterns(application_data)
            
            return {
                'analysis_type': 'ENHANCED_AI',
                'risk_assessment': risk_assessment,
                'ai_insights': ai_insights,
                'model_used': 'Ollama Mistral 7B'
            }
        except Exception as e:
            return {
                'analysis_type': 'ENHANCED_AI',
                'error': str(e),
                'risk_assessment': self.risk_engine.calculate_risk_score(application_data),
                'ai_insights': self.ollama_service._get_fallback_analysis()
            }
    
    def _run_ai_verification_analysis(self, application_data):
        """Run comprehensive AI verification analysis"""
        try:
            # Prepare documents data for verification
            documents_data = self._prepare_documents_data(application_data)
            
            # Generate comprehensive verification report
            verification_report = self.verification_service.generate_comprehensive_verification_report(
                application_data, documents_data
            )
            
            return {
                'analysis_type': 'AI_VERIFICATION',
                'success': True,
                **verification_report
            }
            
        except Exception as e:
            return {
                'analysis_type': 'AI_VERIFICATION',
                'success': False,
                'error': str(e),
                'verification_report': self.verification_service._get_fallback_verification_report()
            }
    
    def _prepare_documents_data(self, application_data):
        """Prepare documents data for AI verification"""
        return {
            'documents_provided': application_data.get('uploaded_documents', []),
            'employment_documents': ['Salary Slips', 'Employment Letter'] if application_data.get('company_name') else [],
            'identity_documents': ['PAN Card', 'Aadhaar Card'] if application_data.get('pan_number') else [],
            'financial_documents': ['Bank Statements'] if application_data.get('monthly_salary', 0) > 0 else [],
            'property_documents': ['Property Valuation'] if application_data.get('property_valuation', 0) > 0 else [],
            'verification_status': {
                'employment_verified': application_data.get('employment_verified', False),
                'income_verified': application_data.get('income_verified', False),
                'identity_verified': application_data.get('identity_verified', False)
            }
        }
    
    def _combine_analyses(self, traditional_analysis, ai_analysis, verification_analysis, application_data):
        """Combine traditional, AI, and verification analyses"""
        try:
            # Calculate overall decision
            overall_decision = self._calculate_overall_decision(
                traditional_analysis, ai_analysis, verification_analysis
            )
            
            combined_analysis = {
                'application_id': application_data.get('application_id', 'UNKNOWN'),
                'applicant_name': f"{application_data.get('first_name', '')} {application_data.get('last_name', '')}",
                'analysis_timestamp': datetime.now().isoformat(),
                'overall_decision': overall_decision,
                'traditional_analysis': traditional_analysis,
                'ai_analysis': ai_analysis,
                'verification_analysis': verification_analysis,  # NEW
                'summary_metrics': self._generate_summary_metrics(
                    traditional_analysis, ai_analysis, verification_analysis
                )
            }
            
            return combined_analysis
            
        except Exception as e:
            return {
                'error': f"Analysis combination failed: {str(e)}",
                'traditional_analysis': traditional_analysis,
                'ai_analysis': ai_analysis,
                'verification_analysis': verification_analysis,
                'overall_decision': 'MANUAL_REVIEW'
            }
    
    def _calculate_overall_decision(self, traditional, ai, verification):
        """Calculate overall decision based on all analyses"""
        try:
            # Check traditional eligibility
            traditional_eligible = (
                traditional.get('cibil_eligible', False) and
                traditional.get('ltv_eligible', False) and
                traditional.get('loan_affordable', False)
            )
            
            if not traditional_eligible:
                return "REJECT - Basic eligibility criteria not met"
            
            # Check risk assessment
            risk_grade = ai.get('risk_assessment', {}).get('risk_grade', 'MEDIUM')
            if risk_grade in ['HIGH', 'VERY_HIGH']:
                return "MANUAL_REVIEW - High risk profile detected"
            
            # Check verification status
            verification_success = verification.get('success', False)
            if not verification_success:
                return "MANUAL_REVIEW - Verification incomplete"
            
            # Check AI recommendation
            ai_recommendation = ai.get('ai_insights', {}).get('ai_recommendation', 'MANUAL_REVIEW')
            if 'APPROVE' in ai_recommendation:
                return "APPROVE - All checks passed"
            elif 'REJECT' in ai_recommendation:
                return "MANUAL_REVIEW - AI recommends rejection"
            else:
                return "MANUAL_REVIEW - Requires human assessment"
                
        except Exception as e:
            return f"MANUAL_REVIEW - Decision calculation error: {str(e)}"
    
    def _generate_summary_metrics(self, traditional, ai, verification):
        """Generate summary metrics for quick assessment"""
        try:
            risk_score = ai.get('risk_assessment', {}).get('risk_score', 0)
            verification_status = verification.get('success', False)
            traditional_passed = (
                traditional.get('cibil_eligible', False) and
                traditional.get('ltv_eligible', False) and
                traditional.get('loan_affordable', False)
            )
            
            return {
                'risk_score': risk_score,
                'verification_complete': verification_status,
                'traditional_checks_passed': traditional_passed,
                'ai_confidence': 'HIGH' if risk_score < 50 else 'MEDIUM' if risk_score < 75 else 'LOW',
                'comprehensive_check': traditional_passed and verification_status and risk_score < 75
            }
        except Exception as e:
            return {
                'error': f"Metrics generation failed: {str(e)}",
                'risk_score': 0,
                'verification_complete': False,
                'traditional_checks_passed': False
            }
    
    def _get_error_analysis(self, error_message):
        """Return error analysis when main analysis fails"""
        return {
            'application_id': 'UNKNOWN',
            'analysis_timestamp': datetime.now().isoformat(),
            'overall_decision': 'ANALYSIS_FAILED',
            'error': error_message,
            'traditional_analysis': {'analysis_type': 'ERROR', 'error': error_message},
            'ai_analysis': {'analysis_type': 'ERROR', 'error': error_message},
            'verification_analysis': {'analysis_type': 'ERROR', 'error': error_message},
            'summary_metrics': {
                'risk_score': 0,
                'verification_complete': False,
                'traditional_checks_passed': False,
                'ai_confidence': 'LOW',
                'comprehensive_check': False
            }
        }


# Example usage and testing
if __name__ == "__main__":
    # Test the AI analysis engine
    analyzer = CasaFlowAIAnalyzer()
    
    # Sample application data
    sample_application = {
        'application_id': 'APP123456',
        'first_name': 'Rajesh',
        'last_name': 'Kumar',
        'email': 'rajesh.kumar@example.com',
        'phone': '+919876543210',
        'age': 35,
        'monthly_salary': 75000,
        'loan_amount': 2500000,
        'property_valuation': 3200000,
        'cibil_score': 780,
        'company_name': 'Tech Solutions Ltd',
        'employment_years': 5,
        'existing_emis': 15000,
        'pan_number': 'ABCDE1234F',
        'aadhar_number': '1234-5678-9012',
        'current_address': '123 Main Street, Bangalore, Karnataka',
        'uploaded_documents': ['pan_card.pdf', 'aadhaar_card.pdf', 'salary_slips.pdf']
    }
    
    # Run analysis
    print("🚀 Starting comprehensive AI analysis...")
    result = analyzer.analyze_application(sample_application)
    
    print(f"📊 Analysis Complete!")
    print(f"Overall Decision: {result.get('overall_decision')}")
    print(f"Risk Score: {result.get('summary_metrics', {}).get('risk_score')}")
    print(f"Verification Complete: {result.get('summary_metrics', {}).get('verification_complete')}")