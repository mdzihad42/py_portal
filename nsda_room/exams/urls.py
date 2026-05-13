from django.urls import path
from . import views

app_name = 'exams'

urlpatterns = [
    path('', views.QuizListView.as_view(), name='quiz_list'),
    path('<int:pk>/', views.QuizDetailView.as_view(), name='quiz_detail'),
    path('<int:pk>/take/', views.TakeQuizView.as_view(), name='take_quiz'),
    path('<int:pk>/results/', views.QuizResultsView.as_view(), name='quiz_results'),
    path('submission/<int:pk>/reset/', views.ResetSubmissionView.as_view(), name='reset_submission'),
    
    # Teacher views
    path('manage/', views.TeacherQuizListView.as_view(), name='teacher_quiz_list'),
    path('create/', views.QuizCreateView.as_view(), name='quiz_create'),
    path('<int:pk>/add-question/', views.AddQuestionView.as_view(), name='add_question'),
]
