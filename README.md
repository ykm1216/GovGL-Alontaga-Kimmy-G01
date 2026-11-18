# GovGL: Quotations and Government Guarantee Letters Tracker

**Name:** Kimmy Swain C. Alontaga
**Section:** G1

GovGL helps Filipino families track Government Guarantee Letter (GL)
applications, keep medical records in one place, and compare pharmacy
price quotations.

This repository includes the account feature and the **Project Development 2 core feature: Government Guarantee Letter (GL) applications**.

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

## Core Feature: Guarantee Letter Applications
- Patients can create, view, update, and delete their own draft applications.
- An application records its assistance program, type, patient, hospital, diagnosis, and requested amount.
- Patients upload the required supporting documents and record supplier quotations before submitting.
- Required document and quotation checks run before submission; uploads accept PDF, JPG, and PNG files up to 5 MB.
- Administrators can review submitted applications, accept or reject individual documents, and approve or reject the application with remarks.
- Patients can view the status and reviewer remarks for their own applications. Administrators can access the review queue.
- Application, document, and quotation data are stored in PostgreSQL/Supabase and related to the creating user.

The program and document requirements are reference information for this academic project. Confirm current requirements with the relevant agency.

## User Roles
| Role | Created by | Dashboard |
|---|---|---|
| Patient | Public registration | `/accounts/dashboard/patient/` |
| Administrator | Set by an existing admin in `/admin/` | `/accounts/dashboard/admin/` |

## Application Routes
| Role | Page |
|---|---|
| Patient | `/applications/` — own applications |
| Patient | `/applications/new/` — start an application |
| Administrator | `/applications/review/` — review submitted applications |

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
8. Uploaded application files are served from `media/` during local development. Keep that folder private in production and configure private storage before deploying.

## Project Structure
```
accounts/    registration, login, logout, dashboards, profile
applications/ Guarantee Letter applications, document uploads, quotations, review
govgl/       project settings and URLs
templates/   HTML templates
static/css/  stylesheet
```