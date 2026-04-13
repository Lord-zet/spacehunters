# Space Hunters

Browser-based strategy game built with Django, focused on backend-driven game logic, time-based resource simulation, 
and state management.

- [Overview](#Overview)
- [Screenshots](#screenshots)
- [Core Mechanics](#core-mechanics)
- [Project Start Guide](#Project-Start-Guide)
  * [Requirements](#Requirements)
  * [Installation & Setup](#Installation-&-Setup)
  * [Database & Initial Data](#Database-&-Initial-Data)
  * [Running the Application](#Running-the-Application)
  * [Authentication](#Authentication)
- [Architecture and Technical Aspects](#Architecture-and-Technical-Aspects)
- [Contribution policy](#Contribution-policy)


## Overview

Space Hunters is a web application that implements non-trivial game mechanics such as time-based 
resource production, build progression systems, and fleet movement resolution. The current version 
focuses on a single-player experience with multiple planets and deterministic state calculation.

The project emphasizes backend architecture, domain modeling, and handling time-dependent logic 
without relying on external background workers (like Celery).


## Screenshots
![dashboard](https://github.com/user-attachments/assets/58de7beb-2745-4c1f-a525-4214c2ce45e6)


## Core Mechanics

### Resource Production

* Resources (metal, crystal) are generated continuously based on building levels.
* The system calculates resource changes on demand using timestamps and the previous state, ensuring high performance and simplified infrastructure.

### Building System

* Players can upgrade planet infrastructure.
* Costs are calculated dynamically based on current levels.
* Upgrades immediately affect production rates and storage capacities.

### Fleet System

* Transport fleets between owned or neutral planets.
* Real-time validation of cargo capacity and resource availability.
* Travel time is calculated based on distance between coordinates.
* Missions (arrival, resource transfer, return) are resolved based on arrival timestamps.


## Project Start Guide

Follow the steps below to run the project locally in a development environment.


### Requirements
* Python **3.10+** 
* pip
* PostgreSQL (must be installed, configured, with a dedicated database and user created)


### Installation & Setup

#### 1. Clone the repository

```
git clone https://github.com/Lord-zet/spacehunters
cd spacehunters
```

#### 2. Create and activate a virtual environment
**Windows:**

```
python -m venv venv
venv\Scripts\activate
```

**Linux:**
```
python -m venv venv
source venv/bin/activate
```

#### 3. Install dependencies
```
pip install -r requirements.txt
```

#### 4. Install the application
This project uses a src-layout, so the application must be installed as a package:
```
pip install -e .
```

#### 5. Environment variables configuration
Copy the example configuration file:

**Windows:**
```
xcopy .env.example .env
```

**Linux:**
```
cp .env.example .env
```

[!IMPORTANT]
Edit the `.env` file and provide your PostgreSQL database credentials, any required environment variables, and a secure Django secret key.

You can generate a new Django secret key by running this command in your terminal:
`python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`

The application will not start without a properly configured .env file. The .env file should not be committed to the repository.


### Database & Initial Data
#### 6. Apply database migrations
```
cd src
python manage.py migrate
```

#### 7. Create a superuser
```
python manage.py createsuperuser
```

#### 8. Seed initial data
The project includes a custom management command for seeding data. This will generate initial game objects and 
a default test user:

```
python manage.py seed_game
```


### Running the Application

#### 9. Run the development server

```
python manage.py runserver
```

The application will be available at: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

### Authentication
* **Login page:** [http://127.0.0.1:8000/login/](http://127.0.0.1:8000/login/)
* **Credentials:** If you ran seed_game, use the test account:
  * **Username**: `user1`
  * **Password**: `Test1234`

(Alternatively, use the superuser account you created in step 7).


## Architecture and Technical Aspects

### Technical Highlights

* Deterministic Simulation: All game states are calculated based on time deltas, ensuring consistency without cron jobs.
* Service Layer Pattern: Business logic is encapsulated in a dedicated service layer, keeping models focused on data and views focused on request handling.
* Server-side Validation: All game actions (building, moving fleets) are strictly validated on the server.

### Project Structure

* `models.py` — Core domain models (Planet, Fleet, Resources) using a "fat models" approach where appropriate for data integrity.
* `services.py` — Service Layer handling complex business logic such as fleet mission resolution and production math.
* `views.py` — Thin controllers handling routing and template rendering.


## Contribution policy

This repository is a portfolio/showcase project created for presentation purposes.
I am not accepting external contributions, pull requests, or feature proposals for this repository.

Please treat it as a read-only code sample demonstrating my Python and Django work.
