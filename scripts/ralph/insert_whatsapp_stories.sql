-- WhatsApp Cloud API Adapter Stories
-- Run this to insert WhatsApp adapter stories into ralph_stories table
-- Based on plan: eager-knitting-creek.md

-- Clear any existing WhatsApp stories (idempotent)
DELETE FROM ralph_stories WHERE story_id LIKE 'WHATSAPP-%';

-- Insert WhatsApp adapter stories
INSERT INTO ralph_stories (project_id, story_id, title, description, acceptance_criteria, priority, status) VALUES
(1, 'WHATSAPP-001', 'Update Config Settings',
'Update the WhatsApp configuration fields in Settings class with proper descriptions. Add 5 WhatsApp config fields: whatsapp_phone_number_id, whatsapp_business_account_id, whatsapp_access_token, whatsapp_verify_token, whatsapp_app_secret. All fields should be Optional with clear descriptions.',
'["All 5 WhatsApp config fields have clear descriptions", "Fields are Optional (adapter disabled if not set)", "Existing settings unchanged"]'::jsonb,
1, 'todo'),

(1, 'WHATSAPP-002', 'Update .env.example',
'Add a commented WhatsApp section to .env.example with all required env vars: WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_BUSINESS_ACCOUNT_ID, WHATSAPP_ACCESS_TOKEN, WHATSAPP_VERIFY_TOKEN, WHATSAPP_APP_SECRET. Include helpful comments explaining where to get these values from Meta Developer Portal.',
'["WhatsApp section clearly commented", "All 5 env vars listed", "Noted as optional (adapter disabled if not set)"]'::jsonb,
2, 'todo'),

(1, 'WHATSAPP-003', 'Create WhatsApp Client Module',
'Create rivet_pro/adapters/whatsapp/client.py with stubbed functions for sending messages via WhatsApp Cloud API. Include: send_whatsapp_text(to_whatsapp_id, body), send_whatsapp_image(to_whatsapp_id, image_url, caption), mark_as_read(message_id). All functions async with proper type hints and docstrings. Log what would be sent without exposing secrets.',
'["Three functions defined: send_whatsapp_text, send_whatsapp_image, mark_as_read", "All functions are async", "Proper type hints and docstrings", "Logging shows what would be sent (no secrets in logs)", "Uses settings for config access"]'::jsonb,
3, 'todo'),

(1, 'WHATSAPP-004', 'Create WhatsApp Webhook Router',
'Create rivet_pro/adapters/web/routers/whatsapp.py with FastAPI router. Include GET endpoint for Meta webhook verification (hub.mode, hub.verify_token, hub.challenge) and POST endpoint for receiving messages. Implement HMAC-SHA256 signature verification. Handle text and image message types. Return 403 for invalid token, 401 for invalid signature.',
'["GET /whatsapp handles webhook verification", "POST /whatsapp receives and validates messages", "Signature verification using HMAC-SHA256", "Returns 403 for invalid verify token", "Returns 401 for invalid signature", "Handles text and image message types", "No secrets logged", "Pure function for signature verification (testable)"]'::jsonb,
4, 'todo'),

(1, 'WHATSAPP-005', 'Update WhatsApp __init__.py',
'Update rivet_pro/adapters/whatsapp/__init__.py to export the WhatsApp adapter entry points. Include module docstring explaining purpose and listing required config vars. Export send_whatsapp_text, send_whatsapp_image, mark_as_read from client module.',
'["Module docstring explains purpose", "Exports all client functions", "Lists required config vars in docstring"]'::jsonb,
5, 'todo'),

(1, 'WHATSAPP-006', 'Wire Router into FastAPI App',
'Modify rivet_pro/adapters/web/main.py to include the WhatsApp router. Import whatsapp router from routers module. Register with /whatsapp prefix and WhatsApp tag. Add comment explaining adapter isolation. Ensure app still starts without WhatsApp config.',
'["WhatsApp router imported", "Router registered with /whatsapp prefix", "Comment explains adapter isolation", "Import does not pull in Telegram code", "FastAPI app still starts without WhatsApp config"]'::jsonb,
6, 'todo'),

(1, 'WHATSAPP-007', 'Add WhatsApp Setup Documentation',
'Create docs/WHATSAPP_SETUP.md with setup instructions. Include: Prerequisites (Meta Business Account, WhatsApp Business API), Configuration steps with Meta Developer Portal, .env setup, Webhook setup with ngrok for local testing, curl examples for testing both endpoints, Security notes about secrets.',
'["Clear step-by-step setup instructions", "ngrok local testing guide", "curl examples for both endpoints", "Security warnings about secrets"]'::jsonb,
7, 'todo');

-- Verify insertion
SELECT story_id, title, priority, status FROM ralph_stories WHERE story_id LIKE 'WHATSAPP-%' ORDER BY priority;
