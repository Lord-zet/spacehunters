from django.urls import path
from . import views

app_name="game"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("planet/<int:pk>/", views.planet_detail, name="planet_detail"),
    path("planet/<int:pk>/switch/", views.switch_planet, name="switch_planet"),
    path("planet/<int:pk>/send-fleet/", views.send_fleet, name="send_fleet"),
    path("planet/<int:pk>/fleets/", views.fleet_list, name="fleet_list"),
    path("planet/<int:pk>/buildings/", views.planet_buildings, name="buildings"),
    path("planet/<int:pk>/shipyard/", views.planet_shipyard, name="shipyard"),
]
