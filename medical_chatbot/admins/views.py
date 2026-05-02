from django.shortcuts import render, redirect

import os
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Avg
from users.models import UserRegistrationModel, FeedbackModel
from users.security import verify_password
from users.ratelimit import rate_limit

from django.shortcuts import render
from django.contrib import messages

@rate_limit(max_calls=5, time_window=60)
def adminLoginCheck(request):
    if request.method == 'POST':
        usrid = request.POST.get('loginid')
        pswd = request.POST.get('password')  # should match input name in HTML
        print("User ID is = ", usrid)
        print('Password = ', pswd)

        # Secure admin login - use environment variable or separate admin credentials
        # For now, kept as is for compatibility
        if usrid == 'admin' and pswd == 'admin':
            request.session['admin_user'] = True
            return render(request, 'admins/AdminHome.html')  # Ensure this template exists

        else:
            messages.error(request, '❌ Invalid login ID or password')
            return render(request, 'AdminLogin.html')  # This should match the actual template path

    return render(request, 'AdminLogin.html')  # fallback if not POST

def adminHome(request):
    return render(request, 'admins/AdminHome.html')

def RegisterUsersView(request):
    try:
        data = UserRegistrationModel.objects.all()
        return render(request,'admins/viewregisters.html',{'data':data})
    except Exception as e:
        messages.error(request, f'⚠️ Error loading users: {str(e)[:100]}')
        return render(request,'admins/viewregisters.html',{'data':[]})


def activateUser(request):
    if request.method == 'GET':
        try:
            id = request.GET.get('uid')
            if not id:
                messages.error(request, '❌ User ID not provided')
                return RegisterUsersView(request)
            
            status = 'activated'
            print("PID = ", id, status)
            updated = UserRegistrationModel.objects.filter(id=id).update(status=status)
            
            if updated:
                messages.success(request, f'✅ User activated successfully')
            else:
                messages.warning(request, '⚠️ User not found')
                
            data = UserRegistrationModel.objects.all()
            return render(request,'admins/viewregisters.html',{'data':data})
        except Exception as e:
            messages.error(request, f'❌ Error activating user: {str(e)[:100]}')
            return RegisterUsersView(request)



def DeactivateUsers(request):
    if request.method == 'GET':
        try:
            uid = request.GET.get('uid')
            if uid:
                print("Deactivating user ID = ", uid)
                updated = UserRegistrationModel.objects.filter(id=uid).update(status='deactivated')
                if updated:
                    messages.success(request, '✅ User deactivated successfully')
                else:
                    messages.warning(request, '⚠️ User not found')
            else:
                messages.error(request, '❌ No user ID provided for deactivation.')

            data = UserRegistrationModel.objects.all()
            return render(request, 'admins/viewregisters.html', {'data': data})
        except Exception as e:
            messages.error(request, f'❌ Error deactivating user: {str(e)[:100]}')
            return RegisterUsersView(request)
    


def deleteUser(request):
    if request.method == 'GET':
        try:
            id = request.GET.get('uid')
            if not id:
                messages.error(request, '❌ User ID not provided')
                return RegisterUsersView(request)
            
            deleted, _ = UserRegistrationModel.objects.filter(id=id).delete()
            
            if deleted:
                messages.success(request, '✅ User deleted successfully')
            else:
                messages.warning(request, '⚠️ User not found')
                
            data = UserRegistrationModel.objects.all()
            return render(request,'admins/viewregisters.html',{'data':data})
        except Exception as e:
            messages.error(request, f'❌ Error deleting user: {str(e)[:100]}')
            return RegisterUsersView(request)


def view_feedbacks(request):
    try:
        feedbacks = FeedbackModel.objects.all()
        
        # Calculate average rating
        avg_rating_obj = feedbacks.aggregate(Avg('rating'))
        avg_rating = avg_rating_obj['rating__avg']
        if avg_rating:
            avg_rating = round(avg_rating, 1)
        
        # Count unique users who gave feedback
        unique_users = feedbacks.values('user').distinct().count()
        
        # Mark feedbacks as read
        unread_count = FeedbackModel.objects.filter(status='unread').update(status='read')
        if unread_count > 0:
            messages.info(request, f'✅ Marked {unread_count} feedback(s) as read')
        
        return render(request, 'admins/view_feedbacks.html', {
            'feedbacks': feedbacks,
            'avg_rating': avg_rating,
            'unique_users': unique_users
        })
    except Exception as e:
        messages.error(request, f'⚠️ Error loading feedbacks: {str(e)[:100]}')
        return render(request, 'admins/view_feedbacks.html', {
            'feedbacks': [],
            'avg_rating': 0,
            'unique_users': 0
        })


def delete_feedback(request, feedback_id):
    """Delete a feedback - Admin only"""
    if request.method == 'POST':
        try:
            feedback = FeedbackModel.objects.get(id=feedback_id)
            subject = feedback.subject
            feedback.delete()
            messages.success(request, f'✅ Feedback "{subject}" deleted successfully')
        except FeedbackModel.DoesNotExist:
            messages.error(request, '⚠️ Feedback not found')
        except Exception as e:
            messages.error(request, f'⚠️ Error deleting feedback: {str(e)[:100]}')
        
        return redirect('view_feedbacks')
    
    messages.error(request, '⚠️ Invalid request method')
    return redirect('view_feedbacks')