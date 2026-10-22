# Deskly: Helpdesk & Ticketing System

Django + Django REST Framework helpdesk. Customers raise tickets, support staff resolve them, admins manage everything. Includes a web UI, REST API (Swagger docs), dashboards, CSV/PDF reports and email notifications.

## Features

- **Roles:** Admin, Support Staff, Customer, with role-based permissions
- **Auth:** register, login/logout, token auth for the API, forgot/reset password by email, change password
- **Tickets:** lifecycle New → In Progress → Resolved → Closed, manual and auto assignment, attachments, tags, comments (with internal notes), history
- **Dashboards:** separate for admin, support and customer. Admin sees tickets by status/priority/category and staff performance (closed per staff); support gets quick filters
- **Search & filters:** by ID, title, keyword, status, priority, category, tag, date range
- **Real-time notifications:** bell icon + live pop-ups over WebSocket (Django Channels). Works without WebSocket too (bell refreshes every 30 s)
- **Reports:** CSV and PDF export, summary report
- **Admin UI:** users, categories, priorities, tags, system settings (uploads, registration, notifications), email server status with a "send test email" button
- **API docs:** Swagger at `/api/docs/`, ReDoc at `/api/redoc/`

## Local setup

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser  # superusers automatically get the Admin role
python manage.py runserver
```

Open http://127.0.0.1:8000/ and sign in. In development, emails (ticket updates, password reset links) are printed in the terminal.

Create support staff and extra admins from **Administration → Users** in the web UI.

## Real-time notifications (WebSocket)

- Uses **Django Channels**. In `settings.py`, `daphne` is the first app in `INSTALLED_APPS`, so `python manage.py runserver` runs in ASGI mode and WebSocket works out of the box.
- Browser connects to `ws://<host>/ws/notifications/?token=<API token>`. Each user receives only their own events: new ticket, status change, assignment, new comment.
- Notifications are also saved in the database (`Notification` model, API: `GET /api/notifications/`, `POST /api/notifications/read/`), so nothing is lost if the user was offline.
- **Production:** run with `daphne -b 0.0.0.0 -p $PORT config.asgi:application` (the `Procfile` already does this). If you run more than one server/process, set `REDIS_URL` so they share the channel layer.

## Run tests

```bash
python manage.py test
```

## Configuration (environment variables)

Copy `.env.example` to `.env` for local use, or set these on your host.

| Variable | Purpose | Default |
|---|---|---|
| `DJANGO_SECRET_KEY` | Secret key (**required** when `DJANGO_DEBUG=False`) | dev key |
| `DJANGO_DEBUG` | `True` / `False` | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma separated hosts | localhost |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | e.g. `https://your-app.up.railway.app` | empty |
| `SITE_URL` | Public URL, used in reset-password emails | `http://127.0.0.1:8000` |
| `DATABASE_URL` | PostgreSQL URL; SQLite is used if empty | SQLite |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` | SMTP; console backend if `EMAIL_HOST` is empty | console |
| `DEFAULT_FROM_EMAIL` | Sender address | `Deskly Helpdesk <no-reply@deskly.local>` |
| `DJANGO_MEDIA_ROOT` | Folder for uploaded attachments | `./media` |
| `SERVE_MEDIA` | Serve `/media/` from Django in production | `1` |
| `REDIS_URL` | Redis for WebSocket when running several processes | in-memory |

## Deployment

The repo already contains `Procfile`, `requirements.txt` and `runtime.txt`. WhiteNoise serves static files; Daphne (ASGI) runs the app so that WebSocket works.

### Railway

1. Push the repo to GitHub and create a new Railway project from it.
2. Add a **PostgreSQL** plugin. Railway sets `DATABASE_URL` for you.
3. Set variables: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `SITE_URL`, and the `EMAIL_*` values.
4. Deploy. The `release` step runs `migrate` and `collectstatic` automatically.
5. Open the service shell and run `python manage.py createsuperuser`.

### Heroku

```bash
heroku create
heroku addons:create heroku-postgresql:essential-0
heroku config:set DJANGO_SECRET_KEY=... DJANGO_DEBUG=False DJANGO_ALLOWED_HOSTS=<app>.herokuapp.com \
  DJANGO_CSRF_TRUSTED_ORIGINS=https://<app>.herokuapp.com SITE_URL=https://<app>.herokuapp.com
git push heroku main
heroku run python manage.py createsuperuser
```

> **Uploaded files:** Railway and Heroku disks are temporary, so attachments disappear on redeploy. Mount a persistent volume (Railway: Volume, then set `DJANGO_MEDIA_ROOT` to its path) or move to S3-style storage for real use.

## Project structure

```
accounts/   users, auth, admin/support/customer API views, dashboards, reports, web UI pages + templates
tickets/    Ticket, Comment, Attachment, Category, Priority, Tag models, notifications, system settings
config/     settings, root URLs
```

## Web UI pages

`/login/`, `/register/`, `/forgot-password/`, `/reset-password/`, `/dashboard/`, `/tickets/`, `/tickets/new/`, `/tickets/<id>/`, `/profile/`, and for admins `/manage/users/`, `/manage/setup/`, `/manage/settings/`.
