# services/application_processor.py
from services.credit_risk_service import CreditRiskService
from models import Application, AIAnalysisReport, db
import logging

logger = logging.getLogger(__name__)

class ApplicationProcessor:
    def __init__(self):
        self.credit_service = CreditRiskService()
    
    def process_application(self, application_id):
        """
        Process application with enhanced credit risk assessment
        """
        try:
            application = Application.query.get(application_id)
            if not application:
                return {'success': False, 'error': 'Application not found'}
            
            # Step 1: Perform credit risk assessment
            credit_risk_result = self.credit_service.calculate_credit_risk(application)
            
            # Step 2: Update application with credit risk data
            self._update_application_risk(application, credit_risk_result)
            
            # Step 3: Generate AI analysis report
            ai_report = self._generate_ai_analysis(application, credit_risk_result)
            
            # Step 4: Make final decision
            decision = self._make_decision(application, credit_risk_result, ai_report)
            
            # Step 5: Save all changes
            db.session.commit()
            
            return {
                'success': True,
                'application_id': application_id,
                'decision': decision,
                'credit_risk': credit_risk_result,
                'ai_report_id': ai_report.id if ai_report else None
            }
            
        except Exception as e:
            logger.error(f"Application processing failed: {str(e)}")
            db.session.rollback()
            return {'success': False, 'error': str(e)}
    
    def _update_application_risk(self, application, credit_risk_result):
        """Update application with credit risk information"""
        if credit_risk_result.get('success'):
            application.credit_risk_score = credit_risk_result.get('risk_score')
            
            # Map risk category to banking_behavior if not set
            if not application.banking_behavior:
                risk_category = credit_risk_result.get('risk_category', 'FAIR')
                application.banking_behavior = risk_category
            
            # Update fraud risk if not set
            if not application.fraud_risk:
                application.fraud_risk = 'LOW'
                
        else:
            # Mark for manual review if credit assessment failed
            application.status = 'MANUAL_REVIEW'
            application.credit_risk_score = None
    
    def _generate_ai_analysis(self, application, credit_risk_result):
        """Generate comprehensive AI analysis report"""
        try:
            # Create or update AI analysis report
            ai_report = AIAnalysisReport.query.filter_by(application_id=application.id).first()
            if not ai_report:
                ai_report = AIAnalysisReport(application_id=application.id)
                db.session.add(ai_report)
            
            # Generate rejection reasons if any
            rejection_reasons = self._assess_rejection_reasons(application, credit_risk_result)
            ai_report.set_rejection_reasons(rejection_reasons)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(application, credit_risk_result)
            ai_report.set_recommendations(recommendations)
            
            # Generate alternative offers if rejected
            if rejection_reasons:
                alternative_offers = self._generate_alternative_offers(application)
                ai_report.set_alternative_offers(alternative_offers)
            
            # Set financial health score
            ai_report.financial_health_score = credit_risk_result.get('risk_score', 50)
            
            # Generate explanation
            ai_report.generated_explanation = self._generate_explanation(
                application, credit_risk_result, rejection_reasons
            )
            
            return ai_report
            
        except Exception as e:
            logger.error(f"AI analysis generation failed: {str(e)}")
            return None
    
    def _assess_rejection_reasons(self, application, credit_risk_result):
        """Assess reasons for potential rejection"""
        reasons = []
        
        # Check credit risk
        if not credit_risk_result.get('success'):
            reasons.append({
                'factor': 'Credit Assessment',
                'severity': 'High',
                'description': 'Unable to complete credit risk assessment',
                'impact': 'Cannot evaluate creditworthiness'
            })
        elif credit_risk_result.get('risk_level') == 'HIGH':
            reasons.append({
                'factor': 'Credit Risk',
                'severity': 'High',
                'description': f'High credit risk detected (Score: {credit_risk_result.get("risk_score")})',
                'impact': 'Increased default probability'
            })
        
        # Check loan affordability
        if application.loan_amount > application.monthly_salary * 60:  # 5 years salary
            reasons.append({
                'factor': 'Loan Affordability',
                'severity': 'Medium',
                'description': 'Loan amount exceeds affordable limit',
                'impact': 'High debt-to-income ratio'
            })
        
        return reasons
    
    def _generate_recommendations(self, application, credit_risk_result):
        """Generate improvement recommendations"""
        recommendations = []
        
        if not credit_risk_result.get('success'):
            recommendations.append({
                'action': 'Manual Credit Review',
                'priority': 'High',
                'description': 'System credit assessment failed - requires manual review',
                'timeline': 'Immediate'
            })
        
        if application.cibil_score and application.cibil_score < 750:
            recommendations.append({
                'action': 'Improve Credit Score',
                'priority': 'Medium',
                'description': 'Increase credit score above 750 for better rates',
                'timeline': '3-6 months'
            })
        
        return recommendations
    
    def _generate_alternative_offers(self, application):
        """Generate alternative loan offers"""
        offers = []
        
        # Suggest smaller loan amount
        if application.loan_amount > application.monthly_salary * 48:
            suggested_amount = application.monthly_salary * 36  # 3 years salary
            offers.append({
                'type': 'Reduced Loan Amount',
                'amount': suggested_amount,
                'tenure': '60 months',
                'reason': 'Better aligned with income',
                'improvement': 'Lower EMI burden'
            })
        
        return offers
    
    def _generate_explanation(self, application, credit_risk_result, rejection_reasons):
        """Generate natural language explanation"""
        if not rejection_reasons:
            return "Application meets all criteria. Recommended for approval."
        
        explanation = "Application analysis completed. Key findings:\n\n"
        
        if credit_risk_result.get('success'):
            explanation += f"Credit Risk: {credit_risk_result.get('risk_category')} "
            explanation += f"(Score: {credit_risk_result.get('risk_score')}/100)\n"
        else:
            explanation += "Credit Risk: Assessment Failed - Manual Review Required\n"
        
        if rejection_reasons:
            explanation += "\nAreas needing improvement:\n"
            for reason in rejection_reasons:
                explanation += f"- {reason['description']}\n"
        
        return explanation
    
    def _make_decision(self, application, credit_risk_result, ai_report):
        """Make final decision on application"""
        # If credit assessment failed completely
        if not credit_risk_result.get('success'):
            application.status = 'MANUAL_REVIEW'
            return 'MANUAL_REVIEW'
        
        # Check risk level
        risk_level = credit_risk_result.get('risk_level')
        risk_score = credit_risk_result.get('risk_score', 0)
        
        if risk_level == 'LOW' and risk_score >= 70:
            application.status = 'APPROVED'
            return 'APPROVED'
        elif risk_level == 'MEDIUM' and risk_score >= 50:
            application.status = 'MANUAL_REVIEW'
            return 'MANUAL_REVIEW'
        else:
            application.status = 'REJECTED'
            return 'REJECTED'