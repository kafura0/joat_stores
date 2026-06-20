
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

## 5. Twilio / WhatsApp Cloud API Setup (Optional)

If you want real WhatsApp notification delivery (order confirmations, loyalty rewards) and inbound WhatsApp ordering:

### Twilio Account Setup (Outbound Messages)
1. Register at [twilio.com](https://twilio.com/).
2. In the Twilio Console, navigate to **Messaging** > **Try it out** > **Send a WhatsApp message**.
3. Follow the sandbox onboarding to connect your WhatsApp number to the Twilio sandbox.
4. Once connected, note your:
   - **Account SID** — found on the Console home page.
   - **Auth Token** — also on the Console home page (reveal with the eye icon).
   - **WhatsApp sender number** — in the sandbox section (e.g. `+14155238886`).
5. Set these as environment variables on Render:

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_WHATSAPP_FROM=+14155238886
```

> ⚠ **Production upgrade:** The Twilio sandbox is limited to pre-approved message templates. For production, you must register a Twilio-approved WhatsApp Business Profile and use pre-approved message templates. See [Twilio WhatsApp API docs](https://www.twilio.com/docs/whatsapp/api).

### Meta WhatsApp Cloud API (Inbound Webhook)

The inbound webhook at `POST /api/v1/notifications/whatsapp/inbound/` accepts incoming messages from Meta's WhatsApp Cloud API.

1. Go to the [Meta Developer Portal](https://developers.facebook.com/) and create (or open) a WhatsApp app.
2. Under **WhatsApp** > **Configuration**, set:
   - **Callback URL**: `https://[your-render-api-url]/api/v1/notifications/whatsapp/inbound/`
   - **Verify Token**: `joat-stores-verify` (or a custom value you set in `WHATSAPP_WEBHOOK_VERIFY_TOKEN`)
3. Subscribe to the **messages** webhook field.
4. Add a test number under **WhatsApp** > **Getting Started** and send a message to your business number to verify the webhook.

Required environment variable on Render:

```
WHATSAPP_WEBHOOK_VERIFY_TOKEN=joat-stores-verify
```

### Full Twilio + Meta Environment Variables Block

Add to your Render dashboard (all optional — the system runs in stub mode without them):

| Variable | Description |
|---|---|
| `TWILIO_ACCOUNT_SID` | Twilio Account SID (outbound WhatsApp) |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token |
| `TWILIO_WHATSAPP_FROM` | WhatsApp sender number (e.g. `+14155238886`) |
| `WHATSAPP_WEBHOOK_VERIFY_TOKEN` | Webhook verification token for Meta Cloud API |

## 6. First-Time Setup & Seeding
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
