from django.urls import path
from . import views

app_name="game"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("planet/<int:pk>/", views.planet_detail, name="planet_detail"),
    path("planet/<int:pk>/switch/", views.switch_planet, name="switch_planet"),
]
