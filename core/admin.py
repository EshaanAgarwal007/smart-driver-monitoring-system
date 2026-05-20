from django.contrib import admin
from .models import DriverProfile, MonitoringSession, AlertLog, AccidentReport, CompanyNotification


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'vehicle_number', 'vehicle_brand', 'status', 'total_sessions', 'total_alerts', 'created_at']
    list_filter  = ['status', 'vehicle_brand']
    search_fields= ['full_name', 'vehicle_number', 'license_number', 'mobile']
    list_editable= ['status']
    readonly_fields = ['created_at', 'updated_at', 'last_active']
    ordering = ['-created_at']


@admin.register(MonitoringSession)
class MonitoringSessionAdmin(admin.ModelAdmin):
    list_display = ['driver', 'start_time', 'status', 'duration_seconds', 'total_alerts', 'safety_score']
    list_filter  = ['status']
    search_fields= ['driver__full_name', 'driver__vehicle_number']
    readonly_fields = ['start_time']
    ordering = ['-start_time']


@admin.register(AlertLog)
class AlertLogAdmin(admin.ModelAdmin):
    list_display = ['driver', 'alert_type', 'severity', 'timestamp', 'duration_seconds', 'acknowledged']
    list_filter  = ['alert_type', 'severity', 'acknowledged']
    search_fields= ['driver__full_name']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']


@admin.register(AccidentReport)
class AccidentReportAdmin(admin.ModelAdmin):
    list_display = ['driver', 'timestamp', 'status', 'emergency_contacted']
    list_filter  = ['status']
    ordering = ['-timestamp']


@admin.register(CompanyNotification)
class CompanyNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'notification_type', 'priority', 'is_read', 'created_at']
    list_filter  = ['notification_type', 'priority', 'is_read']
    ordering = ['-created_at']
