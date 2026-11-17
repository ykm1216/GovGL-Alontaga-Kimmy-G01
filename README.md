# GovGL: Quotations and Government Guarantee Letters Tracker

**Name:** Kimmy Swain C. Alontaga
**Section:** G1

GovGL helps Filipino families track Government Guarantee Letter (GL)
applications, keep medical records in one place, and compare pharmacy
price quotations.

This repository covers **Project Development 1: the Account Feature**.

## Tech Stack
- Django (full stack, Django templates)
- PostgreSQL / Supabase
- python-dotenv for environment variables

## Account Feature
- [x] Registration with validation (required fields, valid e-mail, unique username and e-mail, matching passwords)
- [x] Passwords hashed with Django's built-in authentication
- [x] Login and logout, with error messages for invalid credentials
- [x] Protected pages with `@login_required`
- [x] Two roles, Patient and Administrator, each with its own dashboard
- [x] Users cannot open another role's dashboard by typing its URL
- [x] Profile page where users view and edit their own details

## User Roles
| Role | Created by | Dashboard |
|---|---|---|
| Patient | Public registration | `/accounts/dashboard/patient/` |
| Administrator | Set by an existing admin in `/admin/` | `/accounts/dashboard/admin/` |

## How to Run
1. Clone the repository and open the folder
2. Create and activate a virtual environment
   ```
   python3 -m venv venv
   source venv/bin/activate        # macOS/Linux
   venv\Scripts\activate           # Windows
   ```
3. Install dependencies
   ```
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your own PostgreSQL / Supabase credentials
5. Create the database tables
   ```
   python manage.py migrate
   ```
6. Create an admin account, then open `/admin/`, edit that user, and set **Role** to Administrator
   ```
   python manage.py createsuperuser
   ```
7. Start the server and open http://127.0.0.1:8000/
   ```
   python manage.py runserver
   ```

## Project Structure
```
accounts/    registration, login, logout, dashboards, profile
govgl/       project settings and URLs
templates/   HTML templates
static/css/  stylesheet
```