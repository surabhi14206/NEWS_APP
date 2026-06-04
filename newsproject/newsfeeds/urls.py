from django.urls import path
# pyrefly: ignore [missing-import]
from .views import DashboardView, trigger_fetch, manual_analysis_view

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('fetch/', trigger_fetch, name='fetch_news'),
    path('manual-analysis/', manual_analysis_view, name='manual_analysis'),
]