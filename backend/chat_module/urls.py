from django.urls import path
from . import views

urlpatterns = [
    path('', views.ChatView.as_view(), name='chat-page'),
    path('api/sessions/', views.ChatSessionListAPIView.as_view(), name='chat-session-list-api'),
    path('api/sessions/create/', views.CreateChatSessionAPIView.as_view(), name='chat-session-create-api'),
    path('api/sessions/<int:session_id>/messages/', views.ChatMessageListAPIView.as_view(), name='chat-message-list-api'),
    path('api/sessions/<int:session_id>/stream/', views.ChatMessageStreamAPIView.as_view(), name='chat-message-stream-api'),
]
