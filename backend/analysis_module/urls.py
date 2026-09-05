from django.urls import path
from . import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index-page'),
    path('create/', views.CreateProjectView.as_view(), name='create-project-page'),
    path('project/<int:pk>/', views.ProjectDetailView.as_view(), name='project-detail-page'),
    path('api/projects/search/', views.SearchProjectsView.as_view(), name='search-projects-api'),
    path('api/projects/delete/<int:pk>/', views.DeleteProjectView.as_view(), name='delete-project-api'),
    path('api/projects/<int:pk>/clear-analyses/', views.ClearProjectAnalysesAPIView.as_view(), name='clear-project-analyses-api'),
    path('api/columns/<int:pk>/analyze-single/', views.AnalyzeSingleColumnAPIView.as_view(), name='analyze-single-column-api'),
    path('api/columns/<int:pk>/analysis/', views.ColumnAnalysisAPIView.as_view(), name='column-analysis-api'),
]
