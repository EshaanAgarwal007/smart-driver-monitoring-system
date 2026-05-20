from django.urls import path
from . import views


urlpatterns = [
    # Publicurlpatterns = [
    path('', views.home, name='home'),
    
    
    path('api/save-location/', views.save_driver_location, name='save_driver_location'),
    # Auth
    path('auth/register/', views.register_driver, name='register'),
    path('auth/login/', views.driver_login, name='login'),
    path('auth/logout/', views.driver_logout, name='logout'),

    # Driver
    path('driver/dashboard/', views.driver_dashboard, name='driver_dashboard'),
    path('driver/monitoring/start/', views.start_monitoring, name='start_monitoring'),
    path('driver/history/', views.monitoring_history, name='monitoring_history'),

    # Driver API
    path('api/alert/log/', views.log_alert, name='log_alert'),
    path('api/session/end/', views.end_session, name='end_session'),
    path('api/location/update/', views.update_location, name='update_location'),

    # Admin
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/drivers/', views.admin_drivers, name='admin_drivers'),
    path('admin-panel/drivers/<int:driver_id>/', views.admin_driver_detail, name='admin_driver_detail'),
    path('admin-panel/drivers/<int:driver_id>/<str:action>/', views.driver_action, name='driver_action'),
    path('admin-panel/notifications/<int:notif_id>/read/', views.mark_notification_read, name='mark_notif_read'),
    path('api/admin/live-alerts/', views.get_live_alerts, name='live_alerts'),
]
