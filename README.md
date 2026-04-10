# Space Hunters

Browser-based strategy game built with Django, focused on backend-driven game logic, time-based resource simulation, and state management.

## Overview

Space Hunters is a web application that implements non-trivial game mechanics such as:

* time-based resource production
* build progression systems
* fleet movement and resolution
* server-side state calculation without background workers

The project emphasizes backend architecture, domain modeling, and handling time-dependent logic.

---

## Key technical aspects

* Domain modeling in Django (Planets, Fleets, Resources)
* Time-based state computation (no Celery / cron jobs)
* Business logic separated into service layer
* Server-side validation of all game actions
* Deterministic simulation of game state

---

## Core mechanics

### Resource production

Resources are generated continuously based on building levels.

Instead of using background jobs, the system calculates resource changes **on demand**, using timestamps and previous state.

---

### Building system

Player can upgrade planet's buildings:

* costs are calculated dynamically
* upgrades immediately affect production rates

---

### Fleet system

Player can send fleets between planets:

* transport capacity is validated
* resource availability is enforced
* travel time is calculated based on distance

---

### Time-based resolution

Fleet missions are resolved based on timestamps:

* arrival → resource transfer
* return → fleet restored
* mission lifecycle tracked on backend

---

## Architecture

The project is built using classic Django (no REST API).

### Main domain models

* **Planet**

  * resources, buildings, coordinates, last update timestamp

* **Fleet**

  * cargo, timing (departure / arrival / return), status

### Structure

* `models.py` — core domain models
* `services.py` — business logic (fleet handling, calculations)
* `views.py` — request handling and rendering

---

## MVP scope

* single-player system
* multiple planets
* resource system (metal, crystal)
* building upgrades
* fleet transport system
* time-based mission resolution

---
