# 📦 Event Management CRM – Backend

A backend system built with Django to manage events, users, and administrative operations. It provides RESTful APIs and admin interfaces.

---

## 📚 Table of Contents

1. [Introduction](#1-introduction)  
2. [Project Structure](#2-project-structure)  
3. [Technologies Used](#3-technologies-used)  
4. [Local Development Setup](#4-local-development-setup)  
5. [Deployment to AWS](#5-deployment-to-aws)

---

## 1. Introduction

This project is a backend CRM system built using Django, focusing on managing events and related users.

### 1.1. Document Feature

_Link to detailed feature documentation will be added here._

### 1.2. Video Demo

_Link to project video demonstration will be added here._

---

## 2. Project Structure

```text
event-crm-django/
├── venv/                      # Python virtual environment
├── config/                    # Django project configuration (settings, urls, wsgi, asgi)
│   ├── settings.py
│   └── wsgi.py
├── crm_events/                # Main Django app for event management
│   ├── migrations/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── ...
├── manage.py
├── requirements.txt
├── staticfiles/               # Collected static files (CSS, JS, images)
└── README.md
```

## 3. Technologies Used

| Component     | Technology                                       |
|---------------|--------------------------------------------------|
| **Backend**   | Python, Django                                   |
| **Database**  | PostgreSQL (AWS RDS for production)              |
| **Server**    | Gunicorn, Nginx                                  |
| **Deployment**| AWS EC2 (Ubuntu 22.04 LTS), systemd              |
| **Source Code**| [GitHub Repository](https://github.com/kjnamtv2010/event-crm-django) |

## 4. Local Development Setup

Follow these steps to run the project locally:

### 4.1 Install System Dependencies

#### Ubuntu / Debian
```bash
sudo apt update
sudo apt install -y git python3-pip python3-venv libpq-dev zlib1g-dev libjpeg-dev postgresql-client
```

### 4.2 Clone the Repository
```bash
git clone https://github.com/kjnamtv2010/event-crm-django.git
cd event-crm-django
```

### 4.3 Create and Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4.4 Install Python Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.5 Configure PostgreSQL Database

#### Option 1: Using `psql` shell

```bash
psql -U postgres
```
then
```sql
sudo -u postgres psql -c "CREATE DATABASE eventcrmdb;"
sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'postgres';"
sudo -u postgres psql -c "ALTER ROLE postgres SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE postgres SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE postgres SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE eventcrmdb TO postgres;"

```

### 4.6 Update `config/settings.py`

Ensure your database configuration matches the database you created:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'eventcrmdb',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 4.7 Run Migrations
Apply database schema migrations:
```bash
python manage.py migrate
```

### 4.8 Create Superuser
Create an admin account to access the Django admin panel:
```bash
python manage.py createsuperuser
```

### 4.9 Load Dummy Data (Optional)
You can populate the database with test data for development:
```bash
python manage.py create_dummy_data
```

### 4.10 Collect Static Files
Collect all static files into the `staticfiles/` directory:
```bash
python manage.py collectstatic --noinput
```

### 4.11 Run Development Server
Start the Django development server:
```bash
python manage.py runserver
```
Access:

App: http://127.0.0.1:8000/

Admin: http://127.0.0.1:8000/admin/

## 5. Deployment to AWS

### 5.1 Production Stack

| Component        | Description                                  |
|------------------|----------------------------------------------|
| **EC2 Instance** | Virtual server (Ubuntu 22.04 LTS)            |
| **Nginx**        | Web server and reverse proxy                 |
| **Gunicorn**     | WSGI application server for Django           |
| **AWS RDS**      | PostgreSQL managed database                  |
| **systemd**      | Service manager for Gunicorn and Nginx       |
| **Environment Vars** | Used for secrets and credentials         |

