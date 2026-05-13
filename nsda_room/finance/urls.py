from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('fines/', views.FineListView.as_view(), name='fine_list'),
    path('fines/create/', views.FineCreateView.as_view(), name='fine_create'),
    path('fines/<int:pk>/paid/', views.MarkPaidView.as_view(), name='mark_paid'),
]
