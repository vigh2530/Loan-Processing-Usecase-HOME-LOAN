# services/__init__.py

# Import classes
from .auth_service import AuthService
from .storage_service import StorageService
from .advance_verification_service import AdvanceVerificationService
from .decision_service import DecisionService
from .notification_service import NotificationService
from .autofill_service import AutoFillService

# Create instances
auth_service = AuthService()
storage_service = StorageService() 
advance_verification_service = AdvanceVerificationService()
decision_service = DecisionService()
notification_service = NotificationService()
autofill_service = AutoFillService()

# Export instances
__all__ = [
    'auth_service',
    'storage_service',
    'advance_verification_service', 
    'decision_service',
    'notification_service',
    'autofill_service'
]