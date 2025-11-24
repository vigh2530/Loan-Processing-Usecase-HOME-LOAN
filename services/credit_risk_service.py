import requests
import logging
from datetime import datetime
import time
from models import db

logger = logging.getLogger(__name__)

class CreditRiskService:
    def __init__(self):
        self.fallback_enabled = True
        self.max_retries = 3
        self.timeout = 10
    
    def calculate_credit_risk(self, application):
        """
        Main method to calculate credit risk with fallback mechanisms
        """
        try:
            # Try primary method first
            risk_data = self._get_credit_risk_primary(application)
            if risk_data and risk_data.get('success'):
                return risk_data
            
            # If primary fails, use fallback
            if self.fallback_enabled:
                logger.warning(f"Primary credit risk failed for {application.id}, using fallback")
                return self._calculate_fallback_risk(application)
            else:
                return self._create_error_response("Credit risk assessment failed")
                
        except Exception as e:
            logger.error(f"Credit risk calculation error: {str(e)}")
            return self._create_error_response(f"System error: {str(e)}")
    
    def _get_credit_risk_primary(self, application):
        """
        Primary method using external credit bureau API
        """
        for attempt in range(self.max_retries):
            try:
                # Simulate API call to credit bureau
                api_response = self._call_credit_bureau_api(application)
                
                if api_response.get('status') == 'success':
                    return self._parse_credit_response(api_response, application)
                else:
                    logger.warning(f"Credit API attempt {attempt + 1} failed")
                    time.sleep(1)  # Wait before retry
                    
            except requests.exceptions.Timeout:
                logger.error(f"Credit API timeout on attempt {attempt + 1}")
            except requests.exceptions.ConnectionError:
                logger.error(f"Credit API connection error on attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Unexpected error in credit API: {str(e)}")
        
        return None
    
    def _call_credit_bureau_api(self, application):
        """
        Simulate credit bureau API call
        In production, replace with actual API integration
        """
        # This is a simulation - replace with actual API call
        api_data = {
            'pan_number': application.pan_number,
            'aadhar_number': application.aadhar_number,
            'applicant_name': f"{application.first_name} {application.last_name}"
        }
        
        # Simulate API response based on application data
        if application.cibil_score and application.cibil_score > 0:
            return {
                'status': 'success',
                'cibil_score': application.cibil_score,
                'credit_history': 'good',
                'active_loans': 2,
                'defaults': 0,
                'credit_age_months': 48
            }
        else:
            return {'status': 'error', 'message': 'Score not available'}
    
    def _calculate_fallback_risk(self, application):
        """
        Fallback risk calculation when primary API fails
        """
        try:
            # Calculate risk based on available application data
            risk_score = 0
            risk_factors = []
            
            # Factor 1: CIBIL Score (40% weight)
            if application.cibil_score:
                if application.cibil_score >= 800:
                    risk_score += 40
                    risk_factors.append({"factor": "CIBIL Score", "rating": "Excellent", "score": 40})
                elif application.cibil_score >= 750:
                    risk_score += 35
                    risk_factors.append({"factor": "CIBIL Score", "rating": "Very Good", "score": 35})
                elif application.cibil_score >= 700:
                    risk_score += 25
                    risk_factors.append({"factor": "CIBIL Score", "rating": "Good", "score": 25})
                else:
                    risk_score += 15
                    risk_factors.append({"factor": "CIBIL Score", "rating": "Fair", "score": 15})
            else:
                risk_factors.append({"factor": "CIBIL Score", "rating": "Not Available", "score": 0})
            
            # Factor 2: Banking Behavior (30% weight)
            banking_behavior = getattr(application, 'banking_behavior', 'FAIR')
            if banking_behavior == 'EXCELLENT':
                risk_score += 30
                risk_factors.append({"factor": "Banking Behavior", "rating": "Excellent", "score": 30})
            elif banking_behavior == 'GOOD':
                risk_score += 25
                risk_factors.append({"factor": "Banking Behavior", "rating": "Good", "score": 25})
            elif banking_behavior == 'FAIR':
                risk_score += 15
                risk_factors.append({"factor": "Banking Behavior", "rating": "Fair", "score": 15})
            else:  # POOR
                risk_score += 5
                risk_factors.append({"factor": "Banking Behavior", "rating": "Poor", "score": 5})
            
            # Factor 3: Employment Verification (20% weight)
            if application.employment_status == 'VERIFIED':
                risk_score += 20
                risk_factors.append({"factor": "Employment", "rating": "Verified", "score": 20})
            else:
                risk_score += 5
                risk_factors.append({"factor": "Employment", "rating": "Unverified", "score": 5})
            
            # Factor 4: Fraud Risk (10% weight)
            fraud_risk = getattr(application, 'fraud_risk', 'LOW')
            if fraud_risk == 'LOW':
                risk_score += 10
                risk_factors.append({"factor": "Fraud Risk", "rating": "Low", "score": 10})
            elif fraud_risk == 'MEDIUM':
                risk_score += 5
                risk_factors.append({"factor": "Fraud Risk", "rating": "Medium", "score": 5})
            else:  # HIGH
                risk_score += 0
                risk_factors.append({"factor": "Fraud Risk", "rating": "High", "score": 0})
            
            # Determine risk category
            if risk_score >= 80:
                risk_category = "EXCELLENT"
                risk_level = "LOW"
            elif risk_score >= 60:
                risk_category = "GOOD"
                risk_level = "LOW"
            elif risk_score >= 40:
                risk_category = "FAIR"
                risk_level = "MEDIUM"
            else:
                risk_category = "POOR"
                risk_level = "HIGH"
            
            return {
                'success': True,
                'risk_score': risk_score,
                'risk_category': risk_category,
                'risk_level': risk_level,
                'risk_factors': risk_factors,
                'cibil_score': application.cibil_score,
                'calculation_method': 'FALLBACK',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Fallback risk calculation failed: {str(e)}")
            return self._create_error_response("Fallback calculation failed")
    
    def _parse_credit_response(self, api_response, application):
        """Parse and standardize credit API response"""
        return {
            'success': True,
            'risk_score': self._calculate_risk_from_cibil(api_response['cibil_score']),
            'risk_category': self._get_risk_category(api_response['cibil_score']),
            'risk_level': self._get_risk_level(api_response['cibil_score']),
            'cibil_score': api_response['cibil_score'],
            'credit_history': api_response.get('credit_history', 'unknown'),
            'active_loans': api_response.get('active_loans', 0),
            'defaults': api_response.get('defaults', 0),
            'calculation_method': 'PRIMARY_API',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _calculate_risk_from_cibil(self, cibil_score):
        """Convert CIBIL score to risk score (0-100)"""
        if cibil_score >= 800:
            return 90
        elif cibil_score >= 750:
            return 80
        elif cibil_score >= 700:
            return 70
        elif cibil_score >= 650:
            return 60
        elif cibil_score >= 600:
            return 50
        else:
            return 30
    
    def _get_risk_category(self, cibil_score):
        """Convert CIBIL score to risk category"""
        if cibil_score >= 800:
            return "EXCELLENT"
        elif cibil_score >= 750:
            return "VERY_GOOD"
        elif cibil_score >= 700:
            return "GOOD"
        elif cibil_score >= 650:
            return "FAIR"
        else:
            return "POOR"
    
    def _get_risk_level(self, cibil_score):
        """Convert CIBIL score to risk level"""
        if cibil_score >= 750:
            return "LOW"
        elif cibil_score >= 650:
            return "MEDIUM"
        else:
            return "HIGH"
    
    def _create_error_response(self, message):
        """Create standardized error response"""
        return {
            'success': False,
            'error': message,
            'risk_score': None,
            'risk_category': 'UNAVAILABLE',
            'risk_level': 'UNKNOWN',
            'timestamp': datetime.utcnow().isoformat()
        }