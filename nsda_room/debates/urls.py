from django.urls import path
from . import views

app_name = 'debates'

urlpatterns = [
    path('', views.DebateListView.as_view(), name='list'),
    path('create/', views.DebateCreateView.as_view(), name='create'),
    path('<int:pk>/', views.DebateDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.DebateUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.DebateDeleteView.as_view(), name='delete'),
    path('<int:pk>/register/', views.DebateRegisterView.as_view(), name='register'),
    path('<int:pk>/unregister/', views.DebateUnregisterView.as_view(), name='unregister'),
    path('<int:pk>/results/', views.ResultInputView.as_view(), name='result_input'),
    path('my-debates/', views.MyDebatesView.as_view(), name='my_debates'),
    path('my-results/', views.MyResultsView.as_view(), name='my_results'),
]
