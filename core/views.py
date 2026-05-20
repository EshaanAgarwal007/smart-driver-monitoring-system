import json
import base64
import os
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q
from django.conf import settings

from .models import DriverProfile, MonitoringSession, AlertLog, AccidentReport, CompanyNotification,DriverLocation

from .forms import DriverRegistrationForm, DriverLoginForm


# ─── Helpers ────────────────────────────────────────────────────────────────

def is_admin(user):
    return user.is_staff or user.is_superuser


def get_or_none(model, **kwargs):
    try:
        return model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None


# ─── Public Views ────────────────────────────────────────────────────────────

def home(request):
    stats = {}

    tech_stack = [
        "Python",
        "Django",
        "OpenCV",
        "MediaPipe",
        "JavaScript",
        "SQLite",
        "Bootstrap",
        "GPS API"
    ]

    return render(request, 'home.html', {
        'stats': stats,
        'tech_stack': tech_stack
    })


def register_driver(request):
    """Driver self-registration."""
    if request.user.is_authenticated:
        return redirect('driver_dashboard')

    if request.method == 'POST':
        form = DriverRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save()
            # Create admin notification
            CompanyNotification.objects.create(
                notification_type='new_registration',
                driver=profile,
                title=f'New Driver Registration: {profile.full_name}',
                message=f'{profile.full_name} has registered with vehicle {profile.vehicle_number}. Pending approval.',
                priority='normal',
            )
            messages.success(request, f'Registration successful! Your account is pending admin approval. We\'ll notify you soon.')
            return redirect('login')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = DriverRegistrationForm()

    return render(request, 'auth/register.html', {'form': form})


def driver_login(request):
    """Driver login view."""
    if request.user.is_authenticated:
        if is_admin(request.user):
            return redirect('admin_dashboard')
        return redirect('driver_dashboard')

    if request.method == 'POST':
        form = DriverLoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            if user:
                if is_admin(user):
                    login(request, user)
                    return redirect('admin_dashboard')

                profile = get_or_none(DriverProfile, user=user)
                if not profile:
                    messages.error(request, 'Driver profile not found.')
                elif profile.status == 'pending':
                    messages.warning(request, '⏳ Your account is pending admin approval. Please wait.')
                elif profile.status == 'rejected':
                    messages.error(request, '❌ Your registration has been rejected. Contact support.')
                elif profile.status == 'suspended':
                    messages.error(request, '🚫 Your account has been suspended. Contact support.')
                else:
                    login(request, user)
                    profile.last_active = timezone.now()
                    profile.save(update_fields=['last_active'])
                    return redirect('driver_dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = DriverLoginForm()

    return render(request, 'auth/login.html', {'form': form})


def driver_logout(request):
    logout(request)
    return redirect('home')


# ─── Driver Views ─────────────────────────────────────────────────────────────

@login_required
def driver_dashboard(request):
    if is_admin(request.user):
        return redirect('admin_dashboard')

    profile = get_object_or_404(DriverProfile, user=request.user)

    recent_sessions = profile.sessions.filter(status='completed').order_by('-start_time')[:5]
    recent_alerts = profile.all_alerts.order_by('-timestamp')[:8]
    active_session = profile.sessions.filter(status='active').first()

    # Stats
    total_sessions = profile.sessions.filter(status='completed').count()
    total_alerts = profile.all_alerts.count()
    avg_safety = profile.sessions.filter(status='completed').aggregate(
        avg=Avg('safety_score'))['avg'] or 100.0

    # Weekly data for chart
    week_ago = timezone.now() - timedelta(days=7)
    daily_alerts = []
    for i in range(7):
        day = timezone.now() - timedelta(days=6 - i)
        count = profile.all_alerts.filter(
            timestamp__date=day.date()
        ).count()
        daily_alerts.append({'day': day.strftime('%a'), 'count': count})

    ctx = {
        'profile': profile,
        'recent_sessions': recent_sessions,
        'recent_alerts': recent_alerts,
        'active_session': active_session,
        'total_sessions': total_sessions,
        'total_alerts': total_alerts,
        'avg_safety': round(avg_safety, 1),
        'daily_alerts': json.dumps(daily_alerts),
        
    }
    return render(request, 'driver/dashboard.html', ctx)


@login_required
def start_monitoring(request):
    """Launch monitoring session."""
    profile = get_object_or_404(DriverProfile, user=request.user)

    if profile.status != 'approved':
        messages.error(request, 'Your account is not approved for monitoring.')
        return redirect('driver_dashboard')

    # End any stale active sessions
    profile.sessions.filter(status='active').update(status='interrupted')

    session = MonitoringSession.objects.create(driver=profile)
    profile.total_sessions = (profile.total_sessions or 0) + 1
    profile.last_active = timezone.now()
    profile.save(update_fields=['total_sessions', 'last_active'])

    return render(request, 'driver/monitoring.html', {'profile': profile, 'session': session})


@login_required
@csrf_exempt
def log_alert(request):
    """API endpoint called by JS detection engine to log an alert."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    data = json.loads(request.body)
    profile = get_object_or_404(DriverProfile, user=request.user)
    session = get_object_or_404(MonitoringSession, id=data.get('session_id'), driver=profile)

    alert_type = data.get('alert_type', 'drowsiness')
    severity = data.get('severity', 'medium')
    duration = float(data.get('duration', 0))
    lat = data.get('lat')
    lng = data.get('lng')
    ear = data.get('ear')

    alert = AlertLog.objects.create(
        session=session,
        driver=profile,
        alert_type=alert_type,
        severity=severity,
        duration_seconds=duration,
        latitude=lat,
        longitude=lng,
        ear_value=ear,
        description=data.get('description', ''),
    )

    session.total_alerts += 1
    if alert_type in ['drowsiness', 'eye_closure', 'fatigue']:
        session.total_fatigue_events += 1
    session.eye_closure_count += 1
    if duration > session.max_closure_duration:
        session.max_closure_duration = duration
    # Reduce safety score
    deduction = {'low': 1, 'medium': 3, 'high': 7, 'critical': 15}.get(severity, 3)
    session.safety_score = max(0, session.safety_score - deduction)
    session.save()

    profile.total_alerts = (profile.total_alerts or 0) + 1
    profile.save(update_fields=['total_alerts'])

    # Company notification
    if severity in ('high', 'critical'):
        CompanyNotification.objects.create(
            notification_type='fatigue_alert',
            driver=profile,
            session=session,
            title=f'⚠️ {alert.get_alert_type_display()} — {profile.full_name}',
            message=f'Driver {profile.full_name} ({profile.vehicle_number}) triggered a {severity} {alert_type} alert at {alert.timestamp.strftime("%H:%M:%S")}.',
            priority='urgent' if severity == 'critical' else 'high',
        )

    return JsonResponse({'status': 'ok', 'alert_id': alert.id, 'safety_score': session.safety_score})


@login_required
@csrf_exempt
def end_session(request):
    """End monitoring session."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    data = json.loads(request.body)
    profile = get_object_or_404(DriverProfile, user=request.user)
    session = get_object_or_404(MonitoringSession, id=data.get('session_id'), driver=profile, status='active')

    session.end_time = timezone.now()
    session.status = 'completed'
    delta = session.end_time - session.start_time
    session.duration_seconds = int(delta.total_seconds())
    session.last_known_lat = data.get('lat')
    session.last_known_lng = data.get('lng')
    session.save()

    return JsonResponse({'status': 'ok', 'duration': session.get_duration_display()})


@login_required
@csrf_exempt
def update_location(request):
    """Update driver GPS location."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    data = json.loads(request.body)
    profile = get_object_or_404(DriverProfile, user=request.user)
    session = get_object_or_404(MonitoringSession, id=data.get('session_id'), driver=profile, status='active')

    session.last_known_lat = data.get('lat')
    session.last_known_lng = data.get('lng')
    if not session.route_start_lat:
        session.route_start_lat = data.get('lat')
        session.route_start_lng = data.get('lng')
    session.save(update_fields=['last_known_lat', 'last_known_lng', 'route_start_lat', 'route_start_lng'])

    return JsonResponse({'status': 'ok'})


@login_required
def monitoring_history(request):
    """Driver's monitoring history."""
    profile = get_object_or_404(DriverProfile, user=request.user)
    sessions = profile.sessions.all().order_by('-start_time')

    # Monthly chart data
    monthly = []
    for i in range(6):
        month = timezone.now() - timedelta(days=30 * (5 - i))
        count = profile.sessions.filter(
            start_time__year=month.year,
            start_time__month=month.month,
            status='completed'
        ).count()
        monthly.append({'month': month.strftime('%b'), 'count': count})

    ctx = {
        'profile': profile,
        'sessions': sessions,
        'monthly_data': json.dumps(monthly),
        'total_sessions': sessions.filter(status='completed').count(),
        'total_alerts': profile.all_alerts.count(),
    }
    return render(request, 'driver/history.html', ctx)


# ─── Admin Views ──────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin control center."""
    total_drivers = DriverProfile.objects.count()
    pending = DriverProfile.objects.filter(status='pending').count()
    approved = DriverProfile.objects.filter(status='approved').count()
    total_sessions = MonitoringSession.objects.filter(status='completed').count()
    total_alerts = AlertLog.objects.count()
    active_sessions = MonitoringSession.objects.filter(status='active').count()

    # Recent activity
    recent_alerts = AlertLog.objects.select_related('driver', 'session').order_by('-timestamp')[:10]
    recent_registrations = DriverProfile.objects.order_by('-created_at')[:5]
    notifications = CompanyNotification.objects.filter(is_read=False).order_by('-created_at')[:15]

    # Alerts by type for chart
    alert_distribution = list(
        AlertLog.objects.values('alert_type')
        .annotate(count=Count('id'))
        .order_by('-count')[:6]
    )

    # Daily sessions for last 7 days
    daily_sessions = []
    for i in range(7):
        day = timezone.now() - timedelta(days=6 - i)
        s_count = MonitoringSession.objects.filter(start_time__date=day.date()).count()
        a_count = AlertLog.objects.filter(timestamp__date=day.date()).count()
        daily_sessions.append({'day': day.strftime('%a'), 'sessions': s_count, 'alerts': a_count})

    # Active drivers right now
    active_drivers = MonitoringSession.objects.filter(
        status='active'
    ).select_related('driver').order_by('-start_time')

    ctx = {
        'total_drivers': total_drivers,
        'pending_count': pending,
        'approved_count': approved,
        'total_sessions': total_sessions,
        'total_alerts': total_alerts,
        'active_sessions': active_sessions,
        'recent_alerts': recent_alerts,
        'recent_registrations': recent_registrations,
        'notifications': notifications,
        'unread_count': notifications.count(),
        'alert_distribution': json.dumps(alert_distribution),
        'daily_data': json.dumps(daily_sessions),
        'active_drivers': active_drivers,
    }
    return render(request, 'admin_panel/dashboard.html', ctx)


@login_required
@user_passes_test(is_admin)
def admin_drivers(request):
    """Manage all drivers."""
    status_filter = request.GET.get('status', '')
    search = request.GET.get('q', '')

    drivers = DriverProfile.objects.select_related('user').all()
    if status_filter:
        drivers = drivers.filter(status=status_filter)
    if search:
        drivers = drivers.filter(
            Q(full_name__icontains=search) |
            Q(vehicle_number__icontains=search) |
            Q(license_number__icontains=search) |
            Q(mobile__icontains=search)
        )

    ctx = {
        'drivers': drivers,
        'status_filter': status_filter,
        'search': search,
        'counts': {
            'all': DriverProfile.objects.count(),
            'pending': DriverProfile.objects.filter(status='pending').count(),
            'approved': DriverProfile.objects.filter(status='approved').count(),
            'rejected': DriverProfile.objects.filter(status='rejected').count(),
            'suspended': DriverProfile.objects.filter(status='suspended').count(),
        },
        'status_list': ['all', 'pending', 'approved', 'rejected', 'suspended'],
    }
    return render(request, 'admin_panel/drivers.html', ctx)


@login_required
@user_passes_test(is_admin)
def driver_action(request, driver_id, action):
    """Approve/reject/suspend a driver."""
    profile = get_object_or_404(DriverProfile, id=driver_id)
    valid_actions = {'approve': 'approved', 'reject': 'rejected', 'suspend': 'suspended', 'activate': 'approved'}

    if action in valid_actions:
        old_status = profile.status
        profile.status = valid_actions[action]
        profile.save(update_fields=['status'])
        messages.success(request, f'Driver {profile.full_name} has been {profile.status}.')
    else:
        messages.error(request, 'Invalid action.')

    return redirect('admin_drivers')


@login_required
@user_passes_test(is_admin)
def admin_driver_detail(request, driver_id):
    """Admin: detailed view of a driver."""
    profile = get_object_or_404(DriverProfile, id=driver_id)
    locations = DriverLocation.objects.filter(driver=profile).order_by('-timestamp')
    sessions = profile.sessions.all().order_by('-start_time')[:10]
    alerts = profile.all_alerts.order_by('-timestamp')[:20]
    locations = DriverLocation.objects.filter(
    driver=profile
    ).order_by('-timestamp')[:10]
    ctx = {
        'profile': profile,
        'sessions': sessions,
        'alerts': alerts,
        'total_sessions': profile.sessions.filter(status='completed').count(),
        'total_alerts': profile.all_alerts.count(),
        'locations': locations,
        'avg_safety': profile.sessions.filter(status='completed').aggregate(
            avg=Avg('safety_score'))['avg'] or 100.0,
    }
    return render(request, 'admin_panel/driver_detail.html', ctx)


@login_required
@user_passes_test(is_admin)
def mark_notification_read(request, notif_id):
    notif = get_object_or_404(CompanyNotification, id=notif_id)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    return JsonResponse({'status': 'ok'})


@login_required
@user_passes_test(is_admin)
def get_live_alerts(request):
    """Polling endpoint for live admin alerts."""
    since = request.GET.get('since')
    qs = CompanyNotification.objects.filter(is_read=False)
    if since:
        try:
            qs = qs.filter(created_at__gt=datetime.fromisoformat(since))
        except:
            pass

    data = [
        {
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'priority': n.priority,
            'type': n.notification_type,
            'time': n.created_at.strftime('%H:%M:%S'),
        }
        for n in qs[:10]
    ]
    return JsonResponse({'notifications': data, 'count': len(data)})


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def save_driver_location(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(data)

            profile = DriverProfile.objects.get(user=request.user)

            DriverLocation.objects.create(
                driver=profile,
                latitude=data.get('latitude'),
                longitude=data.get('longitude'),
                location_name=data.get('location_name', 'Unknown Location')
            )

            return JsonResponse({
                'status': 'success'
            })

        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })

    return JsonResponse({
        'status': 'invalid request'
    })