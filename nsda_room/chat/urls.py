from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.ChatRoomListView.as_view(), name='room_list'),
    path('room/<int:pk>/', views.ChatRoomView.as_view(), name='room'),
    path('create/', views.CreateChatRoomView.as_view(), name='create_room'),
]
