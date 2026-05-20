from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import User
from django.utils import timezone


class DriverProfile(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    ]

    VEHICLE_BRANDS = [
        ('toyota', 'Toyota'), ('nissan', 'Nissan'), ('tata', 'Tata'),
        ('hyundai', 'Hyundai'), ('bmw', 'BMW'), ('mercedes', 'Mercedes-Benz'),
        ('audi', 'Audi'), ('honda', 'Honda'), ('ford', 'Ford'),
        ('volkswagen', 'Volkswagen'), ('kia', 'Kia'), ('mahindra', 'Mahindra'),
        ('suzuki', 'Suzuki'), ('tesla', 'Tesla'), ('rivian', 'Rivian'),
        ('other', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='driver_profile')
    full_name = models.CharField(max_length=150)
    age = models.PositiveIntegerField()
    date_of_birth = models.DateField()
    mobile = models.CharField(max_length=15)
    address = models.TextField()
    vehicle_number = models.CharField(max_length=20)
    license_number = models.CharField(max_length=30, unique=True)
    vehicle_brand = models.CharField(max_length=20, choices=VEHICLE_BRANDS)
    vehicle_model = models.CharField(max_length=100)
    profile_photo = models.ImageField(upload_to='drivers/', blank=True, null=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active = models.DateTimeField(null=True, blank=True)
    total_sessions = models.PositiveIntegerField(default=0)
    total_alerts = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Driver Profile'

    def __str__(self):
        return f"{self.full_name} ({self.vehicle_number})"

    @property
    def is_active_driver(self):
        return self.status == 'approved'

    def get_status_badge(self):
        badges = {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'suspended': 'secondary',
        }
        return badges.get(self.status, 'secondary')


class MonitoringSession(models.Model):
    SESSION_STATUS = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('interrupted', 'Interrupted'),
    ]

    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='sessions')
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=15, choices=SESSION_STATUS, default='active')
    total_alerts = models.PositiveIntegerField(default=0)
    total_fatigue_events = models.PositiveIntegerField(default=0)
    eye_closure_count = models.PositiveIntegerField(default=0)
    max_closure_duration = models.FloatField(default=0.0)
    route_start_lat = models.FloatField(null=True, blank=True)
    route_start_lng = models.FloatField(null=True, blank=True)
    last_known_lat = models.FloatField(null=True, blank=True)
    last_known_lng = models.FloatField(null=True, blank=True)
    safety_score = models.FloatField(default=100.0)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_time']

    def __str__(self):
        return f"Session: {self.driver.full_name} @ {self.start_time.strftime('%Y-%m-%d %H:%M')}"

    def get_duration_display(self):
        if self.duration_seconds < 60:
            return f"{self.duration_seconds}s"
        elif self.duration_seconds < 3600:
            m = self.duration_seconds // 60
            s = self.duration_seconds % 60
            return f"{m}m {s}s"
        else:
            h = self.duration_seconds // 3600
            m = (self.duration_seconds % 3600) // 60
            return f"{h}h {m}m"


class AlertLog(models.Model):
    ALERT_TYPES = [
        ('drowsiness', 'Drowsiness Detected'),
        ('eye_closure', 'Prolonged Eye Closure'),
        ('fatigue', 'Fatigue Warning'),
        ('distraction', 'Driver Distraction'),
        ('accident', 'Accident Detected'),
        ('emergency', 'Emergency Alert'),
        ('yawning', 'Yawning Detected'),
    ]

    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    session = models.ForeignKey(MonitoringSession, on_delete=models.CASCADE, related_name='alerts')
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='all_alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='medium')
    timestamp = models.DateTimeField(default=timezone.now)
    duration_seconds = models.FloatField(default=0.0)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    ear_value = models.FloatField(null=True, blank=True)  # Eye Aspect Ratio
    snapshot_path = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_alert_type_display()} — {self.driver.full_name} @ {self.timestamp.strftime('%H:%M:%S')}"

    def get_severity_color(self):
        colors = {
            'low': '#00ff88',
            'medium': '#ffcc00',
            'high': '#ff8800',
            'critical': '#ff0033',
        }
        return colors.get(self.severity, '#888')


class AccidentReport(models.Model):
    STATUS_CHOICES = [
        ('reported', 'Reported'),
        ('investigating', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('false_alarm', 'False Alarm'),
    ]

    session = models.ForeignKey(MonitoringSession, on_delete=models.CASCADE, related_name='accidents')
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, related_name='accidents')
    timestamp = models.DateTimeField(default=timezone.now)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='reported')
    description = models.TextField(blank=True)
    admin_notes = models.TextField(blank=True)
    emergency_contacted = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Accident: {self.driver.full_name} @ {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


class CompanyNotification(models.Model):
    NOTIF_TYPES = [
        ('new_registration', 'New Driver Registration'),
        ('fatigue_alert', 'Fatigue Alert'),
        ('accident_alert', 'Accident Alert'),
        ('session_complete', 'Session Completed'),
        ('system', 'System Notification'),
    ]

    notification_type = models.CharField(max_length=25, choices=NOTIF_TYPES)
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE, null=True, blank=True)
    session = models.ForeignKey(MonitoringSession, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    priority = models.CharField(max_length=10, choices=[('low','Low'),('normal','Normal'),('high','High'),('urgent','Urgent')], default='normal')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class DriverLocation(models.Model):
    driver = models.ForeignKey(DriverProfile, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    location_name = models.CharField(max_length=255, blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.driver.full_name} - {self.location_name}"