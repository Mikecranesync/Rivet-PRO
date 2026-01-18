# Fix Plan: RIVET Pro - WhatsApp Cloud API Adapter

**Branch**: `ralph/whatsapp-adapter`
**Description**: Add WhatsApp Cloud API support as a completely separate adapter. Uses Meta Cloud API webhooks. Does NOT touch existing Telegram code. Uses existing database whatsapp_id field.

---

## Current Tasks

### ✅ WHATSAPP-001: Update Config Settings

Update the WhatsApp configuration fields in Settings class with proper descriptions. Add 5 WhatsApp config fields: whatsapp_phone_number_id, whatsapp_business_account_id, whatsapp_access_token, whatsapp_verify_token, whatsapp_app_secret. All fields should be Optional with clear descriptions.

**File**: `rivet_pro/config/settings.py`

**Acceptance Criteria**:
- [x] All 5 WhatsApp config fields have clear descriptions
- [x] Fields are Optional (adapter disabled if not set)
- [x] Existing settings unchanged

---

### ✅ WHATSAPP-002: Update .env.example

Add a commented WhatsApp section to .env.example with all required env vars: WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_BUSINESS_ACCOUNT_ID, WHATSAPP_ACCESS_TOKEN, WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET. Include helpful comments explaining where to get these values from Meta Developer Portal.

**File**: `.env.example` or `rivet_pro/.env.example`

**Acceptance Criteria**:
- [x] WhatsApp section clearly commented
- [x] All 5 env vars listed
- [x] Noted as optional (adapter disabled if not set)

---

### ✅ WHATSAPP-003: Create WhatsApp Client Module

Create rivet_pro/adapters/whatsapp/client.py with stubbed functions for sending messages via WhatsApp Cloud API. Include: send_whatsapp_text(to_whatsapp_id, body), send_whatsapp_image(to_whatsapp_id, image_url, caption), mark_as_read(message_id). All functions async with proper type hints and docstrings. Log what would be sent without exposing secrets.

**File**: `rivet_pro/adapters/whatsapp/client.py` (CREATE NEW FILE)

**Acceptance Criteria**:
- [x] Three functions defined: send_whatsapp_text, send_whatsapp_image, mark_as_read
- [x] All functions are async
- [x] Proper type hints and docstrings
- [x] Logging shows what would be sent (no secrets in logs)
- [x] Uses settings for config access

---

### ✅ WHATSAPP-004: Create WhatsApp Webhook Router

Create rivet_pro/adapters/web/routers/whatsapp.py with FastAPI router. Include GET endpoint for Meta webhook verification (hub.mode, hub.verify_token, hub.challenge) and POST endpoint for receiving messages. Implement HMAC-SHA256 signature verification. Handle text and image message types. Return 403 for invalid token, 401 for invalid signature.

**File**: `rivet_pro/adapters/web/routers/whatsapp.py` (CREATE NEW FILE)

**Acceptance Criteria**:
- [x] GET /whatsapp handles webhook verification
- [x] POST /whatsapp receives and validates messages
- [x] Signature verification using HMAC-SHA256
- [x] Returns 403 for invalid verify token
- [x] Returns 401 for invalid signature
- [x] Handles text and image message types
- [x] No secrets logged
- [x] Pure function for signature verification (testable)

---

### ✅ WHATSAPP-005: Update WhatsApp __init__.py

Update rivet_pro/adapters/whatsapp/__init__.py to export the WhatsApp adapter entry points. Include module docstring explaining purpose and listing required config vars. Export send_whatsapp_text, send_whatsapp_image, mark_as_read from client module.

**File**: `rivet_pro/adapters/whatsapp/__init__.py` (MODIFY)

**Acceptance Criteria**:
- [x] Module docstring explains purpose
- [x] Exports all client functions
- [x] Lists required config vars in docstring

---

### ✅ WHATSAPP-006: Wire Router into FastAPI App

Modify rivet_pro/adapters/web/main.py to include the WhatsApp router. Import whatsapp router from routers module. Register with /whatsapp prefix and WhatsApp tag. Add comment explaining adapter isolation. Ensure app still starts without WhatsApp config.

**File**: `rivet_pro/adapters/web/main.py` (MODIFY)

**Acceptance Criteria**:
- [x] WhatsApp router imported
- [x] Router registered with /whatsapp prefix
- [x] Comment explains adapter isolation
- [x] Import does not pull in Telegram code
- [x] FastAPI app still starts without WhatsApp config

---

### ✅ WHATSAPP-007: Add WhatsApp Setup Documentation

Create docs/WHATSAPP_SETUP.md with setup instructions. Include: Prerequisites (Meta Business Account, WhatsApp Business API), Configuration steps with Meta Developer Portal, .env setup, Webhook setup with ngrok for local testing, curl examples for testing both endpoints, Security notes about secrets.

**File**: `docs/WHATSAPP_SETUP.md` (CREATE NEW FILE)

**Acceptance Criteria**:
- [x] Clear step-by-step setup instructions
- [x] ngrok local testing guide
- [x] curl examples for both endpoints
- [x] Security warnings about secrets

---

## Summary

- **Total Stories**: 7
- **Completed**: 7 ✅ (ALL COMPLETE)
- **In Progress**: 0
- **Pending**: 0

**IMPORTANT**: This adapter is COMPLETELY SEPARATE from Telegram. Do NOT modify any Telegram code. The existing `whatsapp_id` field in the users table is already ready to use. No database migrations needed.
