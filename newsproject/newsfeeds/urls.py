from django.urls import path
# pyrefly: ignore [missing-import]
from .views import DashboardView, UserDashboardView, trigger_fetch, manual_analysis_view, login_register_view, logout_view, pipeline_logs_api

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('user-dashboard/', UserDashboardView.as_view(), name='user_dashboard'),
    path('login/', login_register_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('fetch/', trigger_fetch, name='fetch_news'),
    path('manual-analysis/', manual_analysis_view, name='manual_analysis'),
    path('api/pipeline-logs/', pipeline_logs_api, name='pipeline_logs_api'),
]