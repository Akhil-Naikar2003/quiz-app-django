from django.urls import path
from . import views
from .views import CreateQuizView

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('analysis/', views.analysis, name='analysis'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('create-quiz/', views.CreateQuizView.as_view(), name='create_quiz'),
    path('quiz/<uuid:quiz_id>/', views.take_quiz, name='take_quiz'),
    path('quiz/<uuid:quiz_id>/results/', views.quiz_results_detail, name='quiz_results_detail'),
    path('quiz/results/', views.quiz_results, name='quiz_results'),
    path('quiz/<uuid:quiz_id>/submit/', views.submit_quiz, name='submit_quiz'),
    path('quiz/<uuid:quiz_id>/delete/', views.delete_quiz, name='delete_quiz'),
    # Chat URLs
    path('chat/', views.chat_sessions, name='chat_sessions'),
    path('chat/<uuid:session_id>/', views.chat_session, name='chat_session'),
    path('chat/<uuid:session_id>/delete/', views.delete_chat_session, name='delete_chat_session'),
] 