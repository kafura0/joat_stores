# JOAT Stores — Prototype Deployment Guide

This guide describes how to deploy the multi-tenant SaaS e-commerce platform to a production environment.

## 1. Database Provisioning (Supabase)
1. Register at [supabase.com](https://supabase.com/).
2. Create a new project named `joat-stores`.
3. Go to **Project Settings** > **Database** and copy the **URI Connection String** under "Connection String" (make sure to use the transaction pooling URL on port 5432 or connection pooling configuration).
4. Save this URI for later; you will insert your database password into it.

## 2. Redis Provisioning (Upstash)
1. Register at [upstash.com](https://upstash.com/).
2. Create a Serverless Redis database in the same region as your Render services (e.g., US West/Oregon if using Oregon on Render).
3. Copy the secure Redis connection URL (`rediss://...`). This URL will serve as the caching layer and Celery message broker.

## 3. API Backend & Celery Worker Deployment (Render)
1. Register at [render.com](https://render.com/).
2. Select **New** > **Blueprint** (or connect your GitHub repository and let Render read `render.yaml`).
3. If using `render.yaml` (recommended):
   - Set the following environment variables in the Render dashboard:
     - `DATABASE_URL`: Your Supabase connection string.
     - `REDIS_URL`: Your Upstash Redis connection string.
     - `CELERY_BROKER_URL`: Same as `REDIS_URL`.
     - `CELERY_RESULT_BACKEND`: Same as `REDIS_URL`.
     - `MPESA_CONSUMER_KEY`: Your Safaricom Daraja consumer key (sandbox or production).
     - `MPESA_CONSUMER_SECRET`: Your Safaricom Daraja consumer secret.
     - `MPESA_CALLBACK_URL`: `https://[your-render-api-url]/api/v1/payments/mpesa-callback/`
   - Render will automatically launch two services:
     - `joat-stores-api` (Django Web Service)
     - `joat-stores-celery` (Celery background worker)

## 4. Frontends Deployment (Vercel)
1. Register at [vercel.com](https://vercel.com/).
2. Click **Add New** > **Project** and import your GitHub repository.

### Deploy the Merchant Admin Panel
- **Project Name**: `joat-admin`
- **Framework Preset**: Next.js
- **Root Directory**: `admin`
- **Environment Variables**:
  - `NEXT_PUBLIC_API_URL`: `https://[your-render-api-url]/api/v1`
  - `NEXT_PUBLIC_DEMO_MODE`: `true` (Enables password-less dashboard exploration for pitches)

### Deploy the Storefront
- **Project Name**: `joat-storefront`
- **Framework Preset**: Next.js
- **Root Directory**: `storefront`
- **Environment Variables**:
  - `NEXT_PUBLIC_API_URL`: `https://[your-render-api-url]/api/v1`

## 5. First-Time Setup & Seeding
Once all deployments are green:
1. Open a terminal on the Django web container (via the Render dashboard under **Shell**).
2. Run migrations:
   ```bash
   python manage.py migrate
   ```
3. Seed the database with sample retail, restaurant, and bar stores:
   ```bash
   python manage.py seed_demo --reset
   ```
4. Verify the deployment by navigating to the Vercel admin URL and logging in with:
   - Email: `restaurant@joat.com`
   - Password: `Demo@1234`
