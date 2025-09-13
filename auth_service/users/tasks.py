
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import CustomUser
import random


@shared_task
def send_otp_via_mail(email):
    print("Task Started")
    subject = "Your verification email."
    otp = random.randint(1000, 9999)
    message = f"Your verification otp is {otp}, Expires in 10min."
    email_from = settings.EMAIL_HOST_USER
    try:
        send_mail(subject, message, email_from, [email])

        user_obj = CustomUser.objects.get(email = email)
        user_obj.otp = otp
        user_obj.save()
        print(f"email sent successfully to : {email}")
    except Exception as e:
        print(str(e))
        print(f"failed to send OTP to : {email}")


@shared_task
def otp_timer(email):
    try:
        user = CustomUser.objects.get(email=email)
        user.otp = None
        print("OTP expired!")
        user.save()
    except CustomUser.DoesNotExist:
        pass
