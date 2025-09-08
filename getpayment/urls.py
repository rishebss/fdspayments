from django.urls import path
from . import views

urlpatterns = [
    path('', views.payment_portal, name='payment_portal'),
    path('search-students/', views.search_students, name='search_students'),
    path('create-payment/', views.create_payment, name='create_payment'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-failed/', views.payment_failed, name='payment_failed'),
    path('razorpay-webhook/', views.razorpay_webhook, name='razorpay_webhook'),
]