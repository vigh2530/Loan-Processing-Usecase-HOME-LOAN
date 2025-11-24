# services/notification_service.py

class NotificationService:
    def send_decision_notification(self, application, reason):
        """Send notification about application decision"""
        # In production, integrate with email/SMS services
        print(f"Notification: Application {application.id} - {application.status}")
        print(f"Reason: {reason}")
        
        if application.status == 'APPROVED':
            print(f"Loan Details: {application.interest_rate}% interest, EMI: ₹{application.emi_amount:.2f}")
        
        return True