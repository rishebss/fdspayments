import razorpay
from django.conf import settings
import json

class RazorpayService:
    def __init__(self):
        self.client = razorpay.Client(auth=(
            settings.RAZORPAY_KEY_ID, 
            settings.RAZORPAY_KEY_SECRET
        ))
    
    def create_order(self, amount, currency='INR', receipt=None):
        try:
            order = self.client.order.create({
                'amount': int(amount * 100),  # Convert to paise
                'currency': currency,
                'receipt': receipt,
                'payment_capture': 1  # Auto capture payment
            })
            return order
        except Exception as e:
            print(f"Error creating Razorpay order: {e}")
            return None
    
    def verify_payment_signature(self, parameters):
        try:
            return self.client.utility.verify_payment_signature(parameters)
        except Exception as e:
            print(f"Error verifying payment signature: {e}")
            return False
    
    def verify_webhook_signature(self, body, signature):
        try:
            # Razorpay webhook verification
            return self.client.utility.verify_webhook_signature(body, signature, settings.RAZORPAY_WEBHOOK_SECRET)
        except Exception as e:
            print(f"Error verifying webhook signature: {e}")
            return False