from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .services.firebase_service import FirebaseService
from .services.razorpay_service import RazorpayService
from django.conf import settings

# Initialize services
firebase_service = FirebaseService()
razorpay_service = RazorpayService()

def payment_portal(request):
    """Render the main payment portal page"""
    return render(request, 'payment_portal.html')  # Now looks in root templates

@require_http_methods(["GET"])
def search_students(request):
    """AJAX endpoint to search students"""
    try:
        name_query = request.GET.get('name', '')
        print(f"Received search query: '{name_query}', length: {len(name_query)}")
        
        # Debug request information
        print("Request GET parameters:", dict(request.GET))
        print("Request headers:", dict(request.headers))
        
        if not name_query:
            print("Query is empty")
            return JsonResponse({'success': False, 'error': 'Enter at least 2 characters'})
            
        if len(name_query) < 2:
            print(f"Query length {len(name_query)} is less than 2")
            return JsonResponse({'success': False, 'error': 'Enter at least 2 characters'})
        
        print("Query validation passed, searching students...")
        students = firebase_service.search_students(name_query)
        print(f"Found {len(students)} students matching query")
        
        # Debug the students data
        for i, student in enumerate(students):
            print(f"Student {i+1}: {student.get('name', 'No name')} (ID: {student.get('id', 'No ID')})")
        
        return JsonResponse({'success': True, 'data': students})
    except Exception as e:
        print(f"Error in search_students: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_http_methods(["POST"])
def create_payment(request):
    """Create payment and initiate Razorpay checkout"""
    try:
        # Handle both form data and JSON data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            student_id = data.get('student_id')
        else:
            student_id = request.POST.get('student_id')
        
        amount = 2000  
        
        # Get student details
        student = firebase_service.get_student(student_id)
        if not student:
            return JsonResponse({'success': False, 'error': 'Student not found'})
        
        # Create payment record in Firebase
        payment_data = {
            'studentId': student_id,
            'studentName': student.get('name'),
            'amount': amount,
            'status': 'pending',
        }
        
        payment = firebase_service.create_payment(payment_data)
        if not payment:
            return JsonResponse({'success': False, 'error': 'Failed to create payment record'})
        
        # Create Razorpay order
        order = razorpay_service.create_order(
            amount=amount,
            receipt=f"payment_{payment['id']}"
        )
        
        if not order:
            return JsonResponse({'success': False, 'error': 'Failed to create payment order'})
        
        # Return JSON response for AJAX requests
        return JsonResponse({
            'success': True,
            'payment_id': payment['id'],
            'razorpay_order_id': order['id'],
            'razorpay_amount': order['amount'],
            'razorpay_currency': order['currency'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error processing payment: {str(e)}'})

def payment_success(request):
    """Show success page after payment"""
    payment_id = request.GET.get('payment_id')
    razorpay_payment_id = request.GET.get('razorpay_payment_id')
    
    if payment_id and razorpay_payment_id:
        # Update payment status in Firebase
        firebase_service.update_payment_status(
            payment_id, 
            'completed', 
            razorpay_payment_id
        )
    
    context = {
        'payment_id': payment_id,
        'razorpay_payment_id': razorpay_payment_id
    }
    
    return render(request, 'success.html', context)  # Root template

def payment_failed(request):
    """Show failure page"""
    payment_id = request.GET.get('payment_id')
    
    if payment_id:
        # Update payment status in Firebase
        firebase_service.update_payment_status(payment_id, 'failed')
    
    context = {
        'payment_id': payment_id
    }
    
    return render(request, 'failed.html', context)  # Root template

@csrf_exempt
@require_http_methods(["POST"])
def razorpay_webhook(request):
    """Handle Razorpay webhook for payment verification"""
    try:
        # For now, we'll just log webhook requests
        webhook_data = json.loads(request.body)
        print("Webhook received:", webhook_data)
        
        # You can add proper webhook handling logic here later
        return JsonResponse({'status': 'success'})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)