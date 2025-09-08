import firebase_admin
from firebase_admin import credentials, firestore
from django.conf import settings
from datetime import datetime, timedelta
import pytz

class FirebaseService:
    _initialized = False
    
    def __init__(self):
        if not FirebaseService._initialized:
            self.initialize_firebase()
            FirebaseService._initialized = True
        self.db = firestore.client()
    
    def initialize_firebase(self):
        try:
            # Use environment variables instead of JSON file
            cred = credentials.Certificate({
                'type': settings.FIREBASE_CONFIG['type'],
                'project_id': settings.FIREBASE_CONFIG['project_id'],
                'private_key_id': settings.FIREBASE_CONFIG['private_key_id'],
                'private_key': settings.FIREBASE_CONFIG['private_key'],
                'client_email': settings.FIREBASE_CONFIG['client_email'],
                'client_id': settings.FIREBASE_CONFIG['client_id'],
                'auth_uri': settings.FIREBASE_CONFIG['auth_uri'],
                'token_uri': settings.FIREBASE_CONFIG['token_uri'],
                'auth_provider_x509_cert_url': settings.FIREBASE_CONFIG['auth_provider_x509_cert_url'],
                'client_x509_cert_url': settings.FIREBASE_CONFIG['client_x509_cert_url'],
            })
            
            # Check if Firebase app is already initialized
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
                print("Firebase initialized successfully from environment variables")
            else:
                print("Firebase app already initialized")
                
        except Exception as e:
            print(f"Error initializing Firebase: {e}")
            raise
    
    # ... rest of your methods remain the same ...
    def get_student(self, student_id):
        try:
            doc_ref = self.db.collection('students').document(student_id)
            doc = doc_ref.get()
            if doc.exists:
                student_data = doc.to_dict()
                student_data['id'] = doc.id
                return student_data
            return None
        except Exception as e:
            print(f"Error getting student: {e}")
            return None
    
    def search_students(self, name_query):
        try:
            students_ref = self.db.collection('students')
            docs = students_ref.stream()
            
            results = []
            for doc in docs:
                student_data = doc.to_dict()
                student_name = student_data.get('name', '').lower()
                
                if name_query.lower() in student_name:
                    results.append({
                        'id': doc.id,
                        **student_data
                    })
            
            return results
        except Exception as e:
            print(f"Error searching students: {e}")
            return []
    
    def create_payment(self, payment_data):
        try:
            # Add timestamp
            payment_data['createdAt'] = datetime.now(pytz.utc).isoformat()
            
            # Add to Firebase
            doc_ref = self.db.collection('payments').document()
            doc_ref.set(payment_data)
            
            return {
                'id': doc_ref.id,
                **payment_data
            }
        except Exception as e:
            print(f"Error creating payment: {e}")
            return None
    
    def update_payment_status(self, payment_id, status, razorpay_payment_id=None):
        try:
            update_data = {
                'status': status,
                'updatedAt': datetime.now(pytz.utc).isoformat()
            }
            
            if razorpay_payment_id:
                update_data['razorpayPaymentId'] = razorpay_payment_id
            
            if status == 'completed':
                update_data['paymentDate'] = datetime.now(pytz.utc).isoformat()
            
            doc_ref = self.db.collection('payments').document(payment_id)
            doc_ref.update(update_data)
            
            return True
        except Exception as e:
            print(f"Error updating payment: {e}")
            return False
    
    def get_next_due_payment(self, student_id):
        """
        Get the next due payment for a student based on the 10th of each month rule
        Returns the payment month, year, due date, and status
        """
        try:
            # Get current date
            now = datetime.now(pytz.utc)
            current_day = now.day
            current_month = now.month
            current_year = now.year
            
            # Calculate due date for current month (10th of the month)
            due_date_current = datetime(current_year, current_month, 10, tzinfo=pytz.utc)
            
            # Check if current month payment already exists and is paid
            current_month_paid = self._check_payment_status(student_id, current_month, current_year)
            
            if current_month_paid == 'completed':
                # Current month is paid, check next month
                next_month = current_month + 1
                next_year = current_year
                if next_month > 12:
                    next_month = 1
                    next_year = current_year + 1
                
                next_month_paid = self._check_payment_status(student_id, next_month, next_year)
                
                if next_month_paid == 'completed':
                    # Both current and next month are paid
                    return None
                else:
                    # Next month payment is due
                    due_date_next = datetime(next_year, next_month, 10, tzinfo=pytz.utc)
                    return {
                        'month': next_month,
                        'year': next_year,
                        'due_date': due_date_next.isoformat(),
                        'status': 'due' if now > due_date_next else 'upcoming',
                        'amount': 1500
                    }
            else:
                # Current month payment is due or pending
                status = 'overdue' if now > due_date_current else 'due'
                return {
                    'month': current_month,
                    'year': current_year,
                    'due_date': due_date_current.isoformat(),
                    'status': status,
                    'amount': 1500
                }
                
        except Exception as e:
            print(f"Error getting next due payment: {e}")
            return None
    
    def _check_payment_status(self, student_id, month, year):
        """
        Check if a payment exists for the given month/year and return its status
        """
        try:
            # Get all payments for the student and filter manually (to avoid index issues)
            payments_ref = self.db.collection('payments') \
                .where('studentId', '==', student_id) \
                .stream()
            
            for doc in payments_ref:
                payment_data = doc.to_dict()
                if (payment_data.get('month') == month and 
                    payment_data.get('year') == year):
                    return payment_data.get('status', 'pending')
            
            return 'not_exists'  # No payment record exists
            
        except Exception as e:
            print(f"Error checking payment status: {e}")
            return 'error'
    
    def get_payment_history(self, student_id):
        """
        Get all payments for a student (simplified to avoid index requirements)
        """
        try:
            payments_ref = self.db.collection('payments') \
                .where('studentId', '==', student_id) \
                .stream()
            
            payments = []
            for doc in payments_ref:
                payment_data = doc.to_dict()
                payment_data['id'] = doc.id
                payments.append(payment_data)
            
            # Sort manually by year and month in descending order
            payments.sort(key=lambda x: (x.get('year', 0), x.get('month', 0)), reverse=True)
            
            return payments
            
        except Exception as e:
            print(f"Error getting payment history: {e}")
            return []