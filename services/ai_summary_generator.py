# services/ai_summary_generator.py
import requests
import json
import re
import ollama
from datetime import datetime

class AISummaryGenerator:
    def __init__(self, ollama_base_url="http://localhost:11434"):
        self.ollama_base_url = ollama_base_url
        self.ai_available = self._check_ai_availability()
    
    def _check_ai_availability(self):
        """Check if Ollama is available and mistral model is installed"""
        try:
            # Check if Ollama service is running
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=5)
            if response.status_code != 200:
                print("Ollama service not available")
                return False
            
            # Check if mistral model is available
            models = response.json().get('models', [])
            mistral_available = any('mistral' in model.get('name', '').lower() for model in models)
            
            if not mistral_available:
                print("Mistral model not found in Ollama. Please install with: ollama pull mistral")
                return False
                
            print("AI Service Available - Using Ollama Mistral for summaries")
            return True
            
        except Exception as e:
            print(f"AI Service Not Available: {str(e)}")
            return False

    def generate_credit_risk_summary(self, application):
        """Generate AI summary for credit risk report using Ollama"""
        try:
            # Always try to use AI first if available
            if self.ai_available:
                prompt = self._create_credit_risk_prompt(application)
                response = self._call_ollama(prompt)
                if response and self._is_valid_response(response):
                    return self._format_ai_summary(response, "CREDIT RISK ASSESSMENT")
            
            # Only fallback if AI is truly unavailable
            print("AI unavailable, using enhanced fallback for credit risk")
            return self._generate_enhanced_credit_summary(application)
            
        except Exception as e:
            print(f"Error in credit risk summary: {str(e)}")
            return self._generate_enhanced_credit_summary(application)
    
    def generate_document_verification_summary(self, application):
        """Generate AI summary for document verification report using Ollama"""
        try:
            from services.document_service import DocumentService
            
            # Get document verification summary safely
            doc_summary = {}
            try:
                doc_summary = DocumentService.get_document_verification_summary(application.id)
            except Exception as e:
                print(f"Error getting document summary: {str(e)}")
                doc_summary = {
                    'total_documents': 0,
                    'verified_count': 0, 
                    'pending_count': 0,
                    'rejected_count': 0,
                    'verification_rate': 0
                }
            
            # Always try to use AI first if available
            if self.ai_available:
                try:
                    prompt = self._create_document_verification_prompt(application, doc_summary)
                    response = self._call_ollama(prompt)
                    if response and self._is_valid_response(response):
                        return self._format_ai_summary(response, "DOCUMENT VERIFICATION SUMMARY")
                except Exception as ai_error:
                    print(f"AI generation failed: {str(ai_error)}")
                    # Continue to fallback
            
            # Use enhanced fallback
            return self._generate_basic_document_summary(application)
            
        except Exception as e:
            print(f"Critical error in document verification summary: {str(e)}")
            return self._generate_basic_document_summary(application)

    def generate_property_verification_summary(self, application):
        """Generate AI summary for property verification report using Ollama"""
        try:
            # Always try to use AI first if available
            if self.ai_available:
                prompt = self._create_property_verification_prompt(application)
                response = self._call_ollama(prompt)
                if response and self._is_valid_response(response):
                    return self._format_ai_summary(response, "PROPERTY VERIFICATION ASSESSMENT")
            
            # Only fallback if AI is truly unavailable
            print("AI unavailable, using enhanced fallback for property verification")
            return self._generate_enhanced_property_summary(application)
    
        except Exception as e:
            print(f"Error in property verification summary: {str(e)}")
            return self._generate_enhanced_property_summary(application)

    def generate_final_comprehensive_summary(self, application):
        """Generate AI summary for final comprehensive report using Ollama"""
        try:
            # Always try to use AI first if available
            if self.ai_available:
                prompt = self._create_comprehensive_prompt(application)
                response = self._call_ollama(prompt)
                if response and self._is_valid_response(response):
                    return self._format_ai_summary(response, "COMPREHENSIVE EXECUTIVE SUMMARY")
            
            # Only fallback if AI is truly unavailable
            print("AI unavailable, using enhanced fallback for comprehensive summary")
            return self._generate_enhanced_comprehensive_summary(application)
            
        except Exception as e:
            print(f"Error in comprehensive summary: {str(e)}")
            return self._generate_enhanced_comprehensive_summary(application)

    # Enhanced prompt creation methods
    def _create_credit_risk_prompt(self, application):
        """Create detailed prompt for credit risk analysis"""
        monthly_salary = getattr(application, 'monthly_salary', 0)
        existing_emi = getattr(application, 'existing_emi', 0)
        loan_amount = getattr(application, 'loan_amount', 0)
        risk_score = getattr(application, 'overall_risk_score', 'Not available')
        
        dti_ratio = (existing_emi / monthly_salary * 100) if monthly_salary > 0 else 0
        
        return f"""
        CREDIT RISK ANALYSIS REQUEST

        Please provide a professional credit risk assessment for this loan application:

        APPLICANT INFORMATION:
        - Name: {application.first_name} {application.last_name}
        - Loan Amount: ₹{loan_amount:,}
        - Monthly Salary: ₹{monthly_salary:,}
        - Existing EMI: ₹{existing_emi:,}
        - Debt-to-Income Ratio: {dti_ratio:.1f}%
        - Risk Score: {risk_score}

        Please analyze and provide:
        1. FINANCIAL CAPACITY ASSESSMENT: Evaluate the applicant's ability to repay
        2. RISK FACTORS IDENTIFIED: List key risk factors with severity
        3. CREDITWORTHINESS ANALYSIS: Overall assessment of creditworthiness
        4. RECOMMENDATION: Clear approval/decline recommendation with rationale
        5. CONDITIONS: Any special conditions if approved

        Provide this as a professional banking summary suitable for credit committee review.
        Be specific, data-driven, and objective in your assessment.
        """

    def _create_document_verification_prompt(self, application, doc_summary):
        """Create detailed prompt for document verification analysis"""
        return f"""
        DOCUMENT VERIFICATION ANALYSIS REQUEST

        Please provide a professional document verification assessment:

        APPLICATION DETAILS:
        - Applicant: {application.first_name} {application.last_name}
        - Application ID: {application.id}

        DOCUMENT STATUS:
        - Total Documents: {doc_summary.get('total_documents', 0)}
        - Verified: {doc_summary.get('verified_count', 0)} documents
        - Pending: {doc_summary.get('pending_count', 0)} documents  
        - Rejected: {doc_summary.get('rejected_count', 0)} documents
        - Verification Rate: {doc_summary.get('verification_rate', 0):.1f}%

        Please analyze and provide:
        1. COMPLIANCE STATUS: Overall document compliance assessment
        2. COMPLETENESS EVALUATION: Assessment of document completeness
        3. RISK ASSESSMENT: Risks related to document verification
        4. RECOMMENDATIONS: Clear next steps and recommendations
        5. DECISION READINESS: Whether documents support proceeding with application

        Provide this as a professional verification summary for loan processing team.
        Be specific about the {doc_summary.get('verification_rate', 0):.1f}% verification rate and what it means for loan approval.
        """

    def _create_property_verification_prompt(self, application):
        """Create detailed prompt for property verification analysis"""
        property_valuation = getattr(application, 'property_valuation', 0)
        loan_amount = getattr(application, 'loan_amount', 0)
        ltv_ratio = (loan_amount / property_valuation * 100) if property_valuation > 0 else 0
        
        return f"""
        PROPERTY VERIFICATION ANALYSIS REQUEST

        Please provide a professional property assessment for this loan application:

        PROPERTY DETAILS:
        - Address: {getattr(application, 'property_address', 'Not provided')}
        - Valuation: ₹{property_valuation:,}
        - Loan Amount: ₹{loan_amount:,}
        - Loan-to-Value Ratio: {ltv_ratio:.1f}%

        Please analyze and provide:
        1. VALUATION ADEQUACY: Assessment of property valuation
        2. LTV ANALYSIS: Risk assessment based on LTV ratio
        3. COLLATERAL SECURITY: Evaluation of property as collateral
        4. RISK ASSESSMENT: Property-related risks identified
        5. RECOMMENDATIONS: Recommendations regarding property security

        Focus on the property's suitability as loan collateral and provide data-driven insights.
        Provide this as a professional property assessment for banking professionals.
        """

    def _create_comprehensive_prompt(self, application):
        """Create detailed prompt for comprehensive analysis"""
        monthly_salary = getattr(application, 'monthly_salary', 0)
        existing_emi = getattr(application, 'existing_emi', 0)
        loan_amount = getattr(application, 'loan_amount', 0)
        property_valuation = getattr(application, 'property_valuation', 0)
        risk_score = getattr(application, 'overall_risk_score', 'Not available')
        
        dti_ratio = (existing_emi / monthly_salary * 100) if monthly_salary > 0 else 0
        ltv_ratio = (loan_amount / property_valuation * 100) if property_valuation > 0 else 0
        
        return f"""
        COMPREHENSIVE LOAN APPLICATION ANALYSIS REQUEST

        Please provide an executive summary for final decision-making:

        APPLICATION OVERVIEW:
        - Applicant: {application.first_name} {application.last_name}
        - Loan Amount: ₹{loan_amount:,}
        - Property: {getattr(application, 'property_address', 'Not specified')}
        - Status: {getattr(application, 'status', 'Not available')}

        FINANCIAL PROFILE:
        - Monthly Income: ₹{monthly_salary:,}
        - Existing EMI: ₹{existing_emi:,}
        - Property Valuation: ₹{property_valuation:,}
        - Debt-to-Income Ratio: {dti_ratio:.1f}%
        - Loan-to-Value Ratio: {ltv_ratio:.1f}%
        - Risk Score: {risk_score}

        Please provide a comprehensive executive summary covering:
        1. OVERALL ASSESSMENT: Holistic evaluation of application quality
        2. KEY STRENGTHS: Major positive factors supporting approval
        3. KEY CONCERNS: Significant risks or concerns identified
        4. FINANCIAL VIABILITY: Analysis of repayment capacity
        5. FINAL RECOMMENDATION: Clear approve/decline recommendation with detailed rationale
        6. CONDITIONS: Any special conditions or monitoring requirements

        This summary should be suitable for senior management decision-making.
        Be comprehensive yet concise, data-driven, and professionally formatted.
        """

    def _call_ollama(self, prompt):
        """Call Ollama API with better error handling and retry logic"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                payload = {
                    "model": "mistral",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for more consistent results
                        "top_p": 0.9,
                        "num_ctx": 4096  # Larger context window for detailed analysis
                    }
                }
                
                response = requests.post(
                    f"{self.ollama_base_url}/api/generate",
                    json=payload,
                    timeout=60  # Longer timeout for complex analysis
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get('response', '').strip()
                else:
                    print(f"Ollama API error (attempt {attempt + 1}): {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"Ollama timeout (attempt {attempt + 1})")
            except requests.exceptions.ConnectionError:
                print(f"Ollama connection error (attempt {attempt + 1})")
            except Exception as e:
                print(f"Ollama error (attempt {attempt + 1}): {str(e)}")
            
            # Wait before retry
            if attempt < max_retries - 1:
                import time
                time.sleep(2)
        
        return None

    def _is_valid_response(self, response):
        """Check if the AI response is valid and usable"""
        if not response:
            return False
        
        # Check for minimum length and content
        if len(response.strip()) < 50:
            return False
            
        # Check for error indicators
        error_indicators = ['error', 'unavailable', 'cannot', 'unable', 'failed']
        if any(indicator in response.lower() for indicator in error_indicators):
            return False
            
        return True

    def _format_ai_summary(self, response, title):
        """Format the AI response with proper title and cleaning"""
        cleaned_response = self.clean_ai_response(response)
        if not cleaned_response:
            return None
            
        return f"""
        {title}
        {'=' * len(title)}

        {cleaned_response}

        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        Source: AI Analysis (Ollama Mistral)
        """

    def clean_ai_response(self, text):
        """Clean AI response while preserving meaningful content"""
        if not text:
            return None
        
        # Remove excessive whitespace but keep structure
        cleaned = re.sub(r'\n\s*\n', '\n\n', text)
        # Remove any remaining unwanted characters but keep punctuation and numbers
        cleaned = re.sub(r'[^\w\s\.\,\!\?\-\:\;\(\)\%₹]', '', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned

    def _generate_basic_document_summary(self, application):
        """Generate a basic document summary that works with your document structure"""
        try:
            from services.document_service import DocumentService
            
            # Get the actual document summary from your service
            doc_summary = DocumentService.get_document_verification_summary(application.id)
            
            verification_rate = doc_summary.get('verification_rate', 0)
            total_docs = doc_summary.get('total_documents', 0)
            verified_count = doc_summary.get('verified_count', 0)
            pending_count = doc_summary.get('pending_count', 0)
            rejected_count = doc_summary.get('rejected_count', 0)
            
            # Determine status based on verification rate
            if verification_rate == 100:
                status = "COMPLETE"
                assessment = "All documents successfully verified"
                recommendation = "Proceed with loan processing"
            elif verification_rate >= 80:
                status = "NEARLY COMPLETE" 
                assessment = "Most documents verified, minor items pending"
                recommendation = "Complete remaining verifications"
            elif verification_rate >= 60:
                status = "PARTIAL"
                assessment = "Significant number of documents verified"
                recommendation = "Review and complete pending documents"
            else:
                status = "INCOMPLETE"
                assessment = "Substantial verification pending"
                recommendation = "Urgent attention required for document completion"
            
            summary = f"""
            DOCUMENT VERIFICATION SUMMARY

            Application: {application.first_name} {application.last_name}
            Application ID: {application.id}

            VERIFICATION STATUS:
            • Total Documents: {total_docs}
            • Verified: {verified_count} documents
            • Pending: {pending_count} documents
            • Rejected: {rejected_count} documents
            • Verification Rate: {verification_rate:.1f}%

            ASSESSMENT:
            • Overall Status: {status}
            • Compliance Level: {assessment}
            • Recommendation: {recommendation}

            NEXT STEPS:
            • {'All documents verified - ready for approval' if verification_rate == 100 else 'Complete pending document verification'}
            • Update application status in system
            • Proceed to next verification stage

            Overall Verification: {status}
            """
            return summary.strip()
            
        except Exception as e:
            # Ultimate fallback if everything fails
            return f"""
            DOCUMENT VERIFICATION SUMMARY
            
            Application: {application.first_name} {application.last_name}
            Application ID: {application.id}
            
            Status: Document verification in progress
            Note: Basic verification completed. Please check system for detailed status.
            
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
            """

    def _format_document_details_for_prompt(self, documents):
        """Format document details for AI prompt - robust version"""
        if not documents:
            return "No documents available for verification."
        
        details = ""
        for doc in documents:
            try:
                # Try multiple possible attribute names for document type
                doc_type = (getattr(doc, 'document_type', None) or 
                           getattr(doc, 'doc_type', None) or 
                           getattr(doc, 'type', None) or 
                           getattr(doc, 'name', 'Unknown Document'))
                doc_type = str(doc_type).replace('_', ' ').title()
                
                # Try multiple possible attribute names for status
                status = (getattr(doc, 'verification_status', None) or
                         getattr(doc, 'document_verification_status', None) or
                         getattr(doc, 'status', None) or
                         getattr(doc, 'verification_state', 'PENDING'))
                
                details += f"  - {doc_type}: {status}\n"
            except Exception as e:
                # If we can't get the attributes, provide generic info
                details += f"  - Document: Status information unavailable\n"
                continue
        
        return details

    # Keep your existing enhanced fallback methods (they should only be used when AI truly fails)
    def _generate_enhanced_credit_summary(self, application):
        """Enhanced fallback - only used when AI is completely unavailable"""
        monthly_salary = getattr(application, 'monthly_salary', 0)
        existing_emi = getattr(application, 'existing_emi', 0)
        loan_amount = getattr(application, 'loan_amount', 0)
        risk_score = getattr(application, 'overall_risk_score', 0)
        
        # Calculate debt-to-income ratio
        dti_ratio = (existing_emi / monthly_salary * 100) if monthly_salary > 0 else 0
        
        # Risk assessment based on score
        if risk_score <= 20:
            risk_level = "LOW RISK"
            recommendation = "STRONGLY RECOMMEND APPROVAL"
        elif risk_score <= 40:
            risk_level = "MODERATE RISK"
            recommendation = "RECOMMEND APPROVAL"
        else:
            risk_level = "HIGH RISK"
            recommendation = "REQUIRES ADDITIONAL REVIEW"
        
        summary = f"""
        CREDIT RISK ASSESSMENT SUMMARY

        Applicant: {application.first_name} {application.last_name}
        Loan Amount: ₹{loan_amount:,}

        FINANCIAL ANALYSIS:
        • Monthly Income: ₹{monthly_salary:,}
        • Existing EMI: ₹{existing_emi:,}
        • Debt-to-Income Ratio: {dti_ratio:.1f}%
        • Risk Score: {risk_score}

        ASSESSMENT:
        1. Financial Capacity: {'Strong' if dti_ratio < 30 else 'Adequate' if dti_ratio < 50 else 'Constrained'}
        2. Risk Factors: {'Minimal concerns identified' if risk_score <= 20 else 'Standard risk factors present' if risk_score <= 40 else 'Elevated risk factors noted'}
        3. Income Stability: Appears sufficient for proposed obligations
        4. Creditworthiness: {'Good' if risk_score <= 30 else 'Acceptable' if risk_score <= 50 else 'Requires scrutiny'}

        RECOMMENDATION:
        {recommendation}

        Overall Risk Level: {risk_level}
        """
        return summary.strip()

    def _generate_enhanced_document_summary(self, application, doc_summary):
        """Enhanced fallback - only used when AI is completely unavailable"""
        verification_rate = doc_summary.get('verification_rate', 0)
        total_docs = doc_summary.get('total_documents', 0)
        verified_count = doc_summary.get('verified_count', 0)
        pending_count = doc_summary.get('pending_count', 0)
        rejected_count = doc_summary.get('rejected_count', 0)
        
        if verification_rate == 100:
            status = "COMPLETE"
            assessment = "All documents successfully verified and approved"
            recommendation = "Proceed with loan processing"
        elif verification_rate >= 80:
            status = "NEARLY COMPLETE"
            assessment = "Most documents verified, minor items pending"
            recommendation = "Complete remaining verifications"
        elif verification_rate >= 60:
            status = "PARTIAL"
            assessment = "Significant number of documents verified"
            recommendation = "Review and complete pending documents"
        else:
            status = "INCOMPLETE"
            assessment = "Substantial verification pending"
            recommendation = "Urgent attention required for document completion"
        
        summary = f"""
        DOCUMENT VERIFICATION SUMMARY

        Application: {application.first_name} {application.last_name}
        Application ID: {application.id}

        VERIFICATION STATUS:
        • Total Documents: {total_docs}
        • Verified: {verified_count} documents
        • Pending: {pending_count} documents
        • Rejected: {rejected_count} documents
        • Verification Rate: {verification_rate:.1f}%

        ASSESSMENT:
        • Overall Status: {status}
        • Compliance Level: {assessment}
        • Recommendation: {recommendation}

        NEXT STEPS:
        • {'All documents verified - ready for approval' if verification_rate == 100 else 'Complete pending document verification'}
        • Update application status in system
        • Proceed to next verification stage

        Overall Verification: {status}
        """
        return summary.strip()

    def _generate_enhanced_property_summary(self, application):
        """Enhanced fallback - only used when AI is completely unavailable"""
        property_valuation = getattr(application, 'property_valuation', 0)
        loan_amount = getattr(application, 'loan_amount', 0)
        property_address = getattr(application, 'property_address', 'Not provided')
        
        ltv_ratio = 0
        if property_valuation and property_valuation > 0:
            ltv_ratio = (loan_amount / property_valuation) * 100
        
        # LTV Assessment
        if ltv_ratio == 0:
            ltv_assessment = "LTV ratio cannot be calculated - valuation missing"
            risk_level = "HIGH"
        elif ltv_ratio <= 70:
            ltv_assessment = f"Excellent LTV ratio of {ltv_ratio:.1f}% - well within safe limits"
            risk_level = "LOW"
        elif ltv_ratio <= 80:
            ltv_assessment = f"Good LTV ratio of {ltv_ratio:.1f}% - within acceptable banking norms"
            risk_level = "MODERATE"
        elif ltv_ratio <= 90:
            ltv_assessment = f"Moderate LTV ratio of {ltv_ratio:.1f}% - requires careful assessment"
            risk_level = "MEDIUM HIGH"
        else:
            ltv_assessment = f"High LTV ratio of {ltv_ratio:.1f}% - significant risk identified"
            risk_level = "HIGH"
        
        # Property valuation assessment
        if property_valuation == 0:
            valuation_assessment = "Property valuation not provided - critical information missing"
            collateral_status = "INSUFFICIENT"
        elif loan_amount > property_valuation:
            valuation_assessment = "Loan amount exceeds property valuation - high risk scenario"
            collateral_status = "INADEQUATE"
        else:
            coverage = property_valuation - loan_amount
            coverage_ratio = (coverage / property_valuation) * 100
            valuation_assessment = f"Property provides adequate security coverage of ₹{coverage:,.0f} ({coverage_ratio:.1f}%)"
            collateral_status = "SATISFACTORY"
        
        summary = f"""
        PROPERTY VERIFICATION ASSESSMENT

        Property Details:
        • Address: {property_address}
        • Valuation: ₹{property_valuation:,.0f}
        • Loan Amount: ₹{loan_amount:,.0f}
        • Loan-to-Value Ratio: {ltv_ratio:.1f}%

        PROPERTY ANALYSIS:
        1. Valuation Assessment: {valuation_assessment}
        2. LTV Analysis: {ltv_assessment}
        3. Collateral Security: Property serves as {'adequate' if collateral_status == 'SATISFACTORY' else 'inadequate'} collateral
        4. Risk Level: {risk_level}

        RECOMMENDATIONS:
        • {'✓ Valuation adequate' if property_valuation > 0 else '⚠️ URGENT: Property valuation required'}
        • {'✓ LTV ratio acceptable' if ltv_ratio <= 80 else '⚠️ High LTV requires additional collateral'}
        • Standard property insurance recommended
        • Legal verification of property documents advised

        Overall Assessment: {collateral_status}
        """
        return summary.strip()

    def _generate_enhanced_comprehensive_summary(self, application):
        """Enhanced fallback - only used when AI is completely unavailable"""
        monthly_salary = getattr(application, 'monthly_salary', 0)
        existing_emi = getattr(application, 'existing_emi', 0)
        loan_amount = getattr(application, 'loan_amount', 0)
        property_valuation = getattr(application, 'property_valuation', 0)
        risk_score = getattr(application, 'overall_risk_score', 0)
        status = getattr(application, 'status', 'PENDING')
        
        # Calculate key ratios
        dti_ratio = (existing_emi / monthly_salary * 100) if monthly_salary > 0 else 0
        ltv_ratio = (loan_amount / property_valuation * 100) if property_valuation > 0 else 0
        
        # Overall risk assessment
        if risk_score <= 20:
            risk_level = "LOW RISK"
            recommendation = "STRONGLY RECOMMEND APPROVAL"
        elif risk_score <= 40:
            risk_level = "MODERATE RISK"
            recommendation = "RECOMMEND APPROVAL"
        else:
            risk_level = "HIGH RISK"
            recommendation = "REQUIRES ADDITIONAL REVIEW"
        
        summary = f"""
        EXECUTIVE SUMMARY - COMPREHENSIVE ASSESSMENT

        APPLICATION OVERVIEW:
        • Applicant: {application.first_name} {application.last_name}
        • Loan Request: ₹{loan_amount:,}
        • Property: {getattr(application, 'property_address', 'Not specified')}
        • AI Risk Score: {risk_score}
        • Final Status: {status}

        FINANCIAL ANALYSIS:
        • Monthly Income: ₹{monthly_salary:,}
        • Existing Liabilities: ₹{existing_emi:,}
        • Property Valuation: ₹{property_valuation:,}
        • Debt-to-Income Ratio: {dti_ratio:.1f}%
        • Loan-to-Value Ratio: {ltv_ratio:.1f}%

        KEY STRENGTHS:
        • {'Strong income base' if monthly_salary >= 100000 else 'Adequate income'}
        • {'Excellent collateral coverage' if ltv_ratio <= 70 else 'Sufficient collateral'}
        • {'Low existing debt burden' if dti_ratio <= 30 else 'Manageable debt levels'}

        KEY CONCERNS:
        • {'None significant' if risk_score <= 30 else 'Standard risk factors' if risk_score <= 50 else 'Elevated risk profile'}

        FINAL RECOMMENDATION:
        {recommendation}

        SPECIAL CONDITIONS:
        • Standard monitoring during loan tenure
        • Regular income verification
        • Property insurance maintenance

        Overall Application Quality: {'EXCELLENT' if risk_score <= 20 else 'GOOD' if risk_score <= 40 else 'SATISFACTORY'}
        Risk Level: {risk_level}
        """
        return summary.strip()