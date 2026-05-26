from django.contrib import admin
from django.urls import path
from ingestion.views import (
    UploadView, DashboardView, ReviewView, EditView, BatchListView
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/upload/', UploadView.as_view()),
    path('api/dashboard/', DashboardView.as_view()),
    path('api/review/<uuid:record_id>/', ReviewView.as_view()),
    path('api/edit/<uuid:record_id>/', EditView.as_view()),
    path('api/batches/', BatchListView.as_view()),
]