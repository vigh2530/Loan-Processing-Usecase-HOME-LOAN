# services/auth_service.py

import random
import time

class AuthService:
    def __init__(self):
        # OTP storage (in production, use Redis or database)
        self.otp_storage = {}

    def generate_and_store_otp(self, mobile_number):
        """Generate and store a 6-digit OTP for the given mobile number"""
        otp = str(random.randint(100000, 999999))
        self.otp_storage[mobile_number] = {
            'otp': otp,
            'timestamp': time.time()
        }
        return otp

    def send_otp_via_sms(self, mobile_number, otp):
        """Simulate sending OTP via SMS"""
        print(f"OTP for {mobile_number}: {otp}")
        # In production, integrate with SMS gateway like Twilio, Msg91, etc.
        return True

    def verify_otp(self, mobile_number, entered_otp):
        """Verify the entered OTP"""
        stored_data = self.otp_storage.get(mobile_number)
        if not stored_data:
            return False
        
        # Check if OTP is expired (5 minutes)
        if time.time() - stored_data['timestamp'] > 300:
            del self.otp_storage[mobile_number]
            return False
        
        if stored_data['otp'] == entered_otp:
            del self.otp_storage[mobile_number]
            return True
        
        return False