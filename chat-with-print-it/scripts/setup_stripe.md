# Stripe Setup Guide

## Prerequisites

- Stripe account (https://stripe.com)
- Access to Stripe Dashboard
- Have your `STRIPE_SECRET_KEY` ready (from dashboard)

## Create Product & Pricing

### 1. Create Product

1. **Navigate to Products:**
   - Dashboard → Products → `+ Add product`

2. **Product Details:**
   - **Name:** `Chat with Print Pro`
   - **Description:** `Unlimited AI-powered electrical panel analysis. Expert troubleshooting guidance for field technicians.`
   - **Image:** (Optional) Upload product/logo image

3. **Pricing:**
   - **Price:** `$29.00`
   - **Billing period:** `Monthly`
   - **Price description:** `Pro Monthly Subscription`

4. **Click** `Save product`

5. **Copy the Price ID:**
   - After saving, click on the price
   - Copy the Price ID (starts with `price_`)
   - Save as: `STRIPE_PRICE_ID=price_xxxxxxxxxxxxx`

### 2. Create Checkout Page (Option A: Stripe-Hosted)

1. **Navigate to Payment Links:**
   - Dashboard → More → Payment links → `+ New`

2. **Configure:**
   - Select your "Chat with Print Pro" product
   - Quantity: Fixed at 1
   - Collect customer email: Yes
   - Collect customer phone: Optional
   - After payment: Redirect to URL (optional)

3. **Create link** and copy the URL

4. **Save as:** `STRIPE_CHECKOUT_URL=https://buy.stripe.com/xxxxx`

### 2. Create Checkout Page (Option B: Custom Integration)

If you prefer programmatic checkout:

1. Use Stripe Checkout API in your landing page
2. Create session with `price_id` from above
3. The n8n workflow handles webhook callbacks

For MVP, **Option A is recommended** (faster to deploy).

## Configure Webhook Endpoint

### 1. Add Endpoint

1. **Navigate to Webhooks:**
   - Dashboard → Developers → Webhooks → `+ Add endpoint`

2. **Endpoint URL:**
   ```
   http://72.60.175.144:5678/webhook/stripe-webhook
   ```
   (Replace with your actual n8n URL)

3. **Select events to listen to:**
   - `checkout.session.completed`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`

4. **Click** `Add endpoint`

### 2. Get Signing Secret

1. Click on the webhook endpoint you just created

2. **Click** `Reveal` in the "Signing secret" section

3. **Copy the secret** (starts with `whsec_`)

4. **Save as:** `STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx`

## Test Mode vs Production

During initial testing:

1. **Use Test Mode**
   - Toggle "View test data" in Stripe Dashboard
   - All API keys will start with `sk_test_`
   - All webhooks will start with `whsec_test_`
   - Use test cards: `4242 4242 4242 4242` (any future date, any CVC)

2. **For Production**
   - Toggle to live mode
   - Re-create product, pricing, and webhook in live mode
   - Update all API keys and secrets to live versions

## Environment Variables Summary

After completing this guide, you should have:

```bash
# From Stripe Dashboard → Developers → API Keys
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxxx  # or sk_test_ for testing

# From Product creation
STRIPE_PRICE_ID=price_xxxxxxxxxxxxx

# From Payment Link or Checkout page
STRIPE_CHECKOUT_URL=https://buy.stripe.com/xxxxx

# From Webhook endpoint
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
```

## Verify Setup

1. **Test checkout flow:**
   - Visit your `STRIPE_CHECKOUT_URL`
   - Use test card (if in test mode): `4242 4242 4242 4242`
   - Complete purchase
   - Check Stripe Dashboard → Payments (should show successful payment)

2. **Test webhook:**
   - After test purchase, check Developers → Webhooks
   - Click on your endpoint
   - Should show recent events with status `succeeded`

Setup complete! Continue to Phase 2 to configure n8n workflows.
