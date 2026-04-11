# Space Hunters

Browser-based strategy game built with Django, focused on backend-driven game logic, time-based resource simulation, and state management.

- [Overview](#Overview)
- [Project Quick Start](#Project Quick Start Guide)
  * [Requirements](#Requirements)


## Overview

Space Hunters is a web application that implements non-trivial game mechanics such as:

* time-based resource production
* build progression systems
* fleet movement and resolution
* server-side state calculation without background workers

The project emphasizes backend architecture, domain modeling, and handling time-dependent logic.

## Project Quick Start Guide

Follow the steps below to run the project locally in a development environment.


### Requirements
* Python **3.10+** 
* pip 


### Installation & Setup

### 1. Clone the repository

```
git clone https://github.com/Lord-zet/spacehunters
cd spacehunters
```

### 2. Create and activate a virtual environment
**Windows:**

```
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies
```
pip install -r requirements.txt
```

### 4. Install the application
This project uses a src-layout, so the application must be installed as a package:
```
pip install -e .
```

### 5. Environment variables configuration
Copy the example configuration file:
```
cp .env.example .env
```

[!IMPORTANT]
Edit .env file and provide your database credentials and any required environment variables. The application will not start without a properly configured .env file. The .env file should not be committed to the repository.

---

## Database & Initial Data
### 6. Apply database migrations
```
python manage.py migrate
```

### 7. Create a superuser
```
python manage.py createsuperuser
```

### 8. Seed initial data
The project includes a custom management command for seeding data:

```
python manage.py seed_game
```


## Running the Application

### 9. Run the development server

```
python manage.py runserver
```

The application will be available at: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

### Authentication
* **Login page:** [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)
* **Credentials:** Use the users created in the system.


## Key technical aspects

* Domain modeling in Django (Planets, Fleets, Resources)
* Time-based state computation (no Celery / cron jobs)
* Business logic separated into service layer
* Server-side validation of all game actions
* Deterministic simulation of game state


## Core mechanics

### Resource production

Resources are generated continuously based on building levels.

Instead of using background jobs, the system calculates resource changes **on demand**, using timestamps and previous state.


### Building system

Player can upgrade planet's buildings:

* costs are calculated dynamically
* upgrades immediately affect production rates


### Fleet system

Player can send fleets between planets:

* transport capacity is validated
* resource availability is enforced
* travel time is calculated based on distance


### Time-based resolution

Fleet missions are resolved based on timestamps:

* arrival → resource transfer
* return → fleet restored
* mission lifecycle tracked on backend


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


## MVP scope

* single-player system
* multiple planets
* resource system (metal, crystal)
* building upgrades
* fleet transport system
* time-based mission resolution


## Contribution policy

This repository is a portfolio/showcase project created for presentation purposes.
I am not accepting external contributions, pull requests, or feature proposals for this repository.

Please treat it as a read-only code sample demonstrating my Python and Django work.