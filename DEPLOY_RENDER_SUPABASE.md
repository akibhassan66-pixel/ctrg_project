# Render + Supabase deployment

This project can be deployed on Render with Supabase as the PostgreSQL database.

## Important constraint

Do not start from an empty Supabase database and expect `python manage.py migrate` to build everything.

This project contains unmanaged models and historical migrations that were written for MySQL. The safe path is:

1. import your already-converted PostgreSQL database into Supabase
2. point Render at that database with `DATABASE_URL`
3. start the app

## 1. Push this repo to GitHub

Render deploys from GitHub, GitLab, or Bitbucket. GitHub is the simplest option.

## 2. Create a Supabase project

Create a new Supabase project and keep the database password you choose. After the project is ready, copy the PostgreSQL connection string from Supabase.

Use the direct PostgreSQL connection string with `sslmode=require`.

## 3. Export your current local PostgreSQL database

Run this from a terminal on your machine:

```powershell
pg_dump `
  --schema=public `
  --no-owner `
  --no-privileges `
  --file C:\cse299\ctrg_project\ctrg_project\supabase_seed.sql `
  "postgresql://ctrg_app:[LOCAL_DB_PASSWORD]@127.0.0.1:5432/ctrg_grant_system"
```

## 4. Import that dump into Supabase

Replace the placeholder connection string with your actual Supabase one:

```powershell
psql "postgresql://postgres:[YOUR_PASSWORD]@[YOUR_HOST]:5432/postgres?sslmode=require" `
  -f C:\cse299\ctrg_project\ctrg_project\supabase_seed.sql
```

If Supabase gives you a pooled connection string, prefer the direct PostgreSQL connection for the initial import.

## 5. Deploy on Render

This repo now includes:

- `build.sh`
- `render.yaml`
- production-ready env-based Django settings

In Render:

1. open `Blueprints`
2. create a new Blueprint from this repository
3. when prompted, set `DATABASE_URL` to your Supabase PostgreSQL connection string
4. apply the Blueprint

The service will use:

- `bash build.sh`
- `gunicorn ctrg_project.wsgi:application --bind 0.0.0.0:$PORT --log-file -`

## 6. Create or verify an admin user

After the app is live, open a Render shell and run:

```bash
python manage.py createsuperuser
```

If you already imported your current database, your existing admin users should already be present.

## 7. Media files

`SERVE_MEDIA=True` is enabled in `render.yaml` so Django can serve files from the local `media/` directory for a demo deployment.

This is not durable storage.

- committed files inside `media/` will be available after deploy
- new uploads can disappear on redeploy or instance restart

For a long-term deployment, move media storage to S3, Cloudinary, or Supabase Storage.

## 8. Email on Render free

Do not rely on Gmail SMTP on a free Render web service.

Render announced that free web services block outbound SMTP traffic on ports `25`, `465`, and `587`, so SMTP-based delivery is the wrong transport for this deployment.

The project now supports API-based email delivery. The fastest path is Brevo because you can verify a sender email address even if you do not own a full sending domain.

Set these Render environment variables:

- `BREVO_API_KEY`
- `BREVO_FROM_EMAIL`
- `BREVO_FROM_NAME`

Keep `DEFAULT_FROM_EMAIL` aligned with `BREVO_FROM_EMAIL`.

If `BREVO_API_KEY` is present, reviewer-assignment emails and reminder emails will use the Brevo HTTP API instead of SMTP.

Resend is also supported, but it is usually slower to set up because sending to other recipients requires a verified domain.
