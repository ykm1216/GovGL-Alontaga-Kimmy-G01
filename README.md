# GovGL: Quotations and Government Guarantee Letters Tracker

**Name:** Kimmy Swain C. Alontaga
**Section:** G1

GovGL helps Filipino families track Government Guarantee Letter (GL)
applications, store medical records, and compare pharmacy price quotations.

## Tech Stack
- Django (full stack, Django templates)
- PostgreSQL / Supabase
- Bootstrap 5

## Current Phase: Account Feature
- [ ] Registration
- [ ] Login / Logout
- [ ] Role-based dashboards
- [ ] User profile

## How to Run
1. Clone the repo and enter the folder
2. Create and activate a virtual environment
   ```
   python -m venv venv
   venv\Scripts\activate           # Windows
   source venv/bin/activate        # macOS/Linux
   ```
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and fill in your database credentials
5. `python manage.py makemigrations accounts`
6. `python manage.py migrate`
7. `python manage.py runserver`
