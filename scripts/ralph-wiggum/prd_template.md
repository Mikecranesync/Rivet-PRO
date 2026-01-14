# PRD Template for Ralph Wiggum

Use this template to plan features before running Ralph Wiggum autonomous loops.

---

## Feature: [Feature Name]

**Date:** [YYYY-MM-DD]
**Author:** [Your Name]
**Priority:** [High/Medium/Low]

---

## Goal

[What should Ralph accomplish? Be specific and measurable.]

Example: "Implement a user notification system that sends Telegram messages when work orders are assigned to technicians."

---

## Completion Promise

**Promise:** "[Specific, testable success criteria]"

Example: "tests pass and notifications sent"

This is what you'll pass to --completion-promise. Ralph will iterate until this condition is met.

---

## Complexity Estimate

**Estimated Iterations:** [5-25]

Use these guidelines:
- Simple (3-5): Add a command, create a simple function, update config
- Medium (5-10): Add service class, create migration, basic feature
- Complex (10-20): Multi-file feature, database changes, testing
- Very Complex (20-30): Full system integration, multiple services

**Timeout:** [600-3600 seconds]
- Simple: 600s (10 min)
- Medium: 1800s (30 min)
- Complex: 3600s (1 hour)

---

## Context

### Files to Modify
List files Ralph will need to work with:
- `rivet_pro/bot/handlers.py` - Add new command handler
- `rivet_pro/core/services/notification_service.py` - Create new service
- `rivet_pro/migrations/014_notifications.sql` - New migration

### Dependencies
- Python libraries: [list if new ones needed]
- External APIs: [list if any]
- Database changes: [describe]

### Related Code
- See `rivet_pro/core/services/usage_service.py` for service pattern example
- Bot command pattern in `rivet_pro/bot/commands/equip.py`

---

## Requirements

### Functional Requirements
1. [Requirement 1]
2. [Requirement 2]
3. [Requirement 3]

Example:
1. Notification service sends Telegram messages
2. Notifications triggered when work order assigned
3. Users can opt-out via /settings command

### Non-Functional Requirements
- Performance: [response time, throughput]
- Security: [authentication, data validation]
- Maintainability: [code quality, documentation]

Example:
- Notifications sent within 5 seconds
- Rate limit: 10 notifications per minute per user
- Service must be testable with mocks

---

## Test Requirements

### Unit Tests
- [Test 1 - what to test]
- [Test 2 - what to test]

Example:
- Test NotificationService.send_message() with valid message
- Test NotificationService.send_message() with invalid user_id

### Integration Tests
- [Test 1 - end-to-end scenario]

Example:
- Create work order → verify technician receives notification

### Manual Tests
- [Test 1 - manual verification]

Example:
- Send test notification via Telegram
- Verify message format and content

---

## Success Criteria

Ralph's task is complete when:
- [ ] All code changes implemented
- [ ] Database migration created and tested
- [ ] Unit tests written and passing
- [ ] Integration tests passing
- [ ] Manual test completed successfully
- [ ] Code follows Rivet Pro patterns
- [ ] No syntax errors or import issues

---

## Ralph Command

```bash
/ralph-loop "[Detailed task description with all context]" \
  --completion-promise "[your completion promise]" \
  --max-iterations [your estimate] \
  --timeout [your timeout] \
  --model claude-3-5-sonnet \
  --temperature 0.7
```

### Full Example

```bash
/ralph-loop "Implement notification system for Rivet Pro:

1. Create NotificationService in rivet_pro/core/services/notification_service.py
   - send_message(user_id, message) method
   - Uses existing Telegram bot instance
   - Handles errors gracefully

2. Create migration 014_add_notification_preferences.sql
   - user_id, notifications_enabled (default true)
   - Use IF NOT EXISTS pattern

3. Modify work order assignment in rivet_pro/atlas/services.py
   - Call NotificationService when work order assigned
   - Send message: 'New work order #{wo_id} assigned to you'

4. Add /notifications command to bot
   - Toggle notifications on/off
   - Update user preferences in DB

5. Write tests:
   - Unit tests for NotificationService
   - Integration test for work order assignment flow

6. Test manually:
   - Create work order
   - Verify notification sent
   - Toggle notifications off
   - Verify no notification sent

Complete when all tests pass and manual verification successful." \
  --completion-promise "tests pass and manual test successful" \
  --max-iterations 25 \
  --timeout 3600
```

---

## Notes

### Assumptions
- [List any assumptions]

Example:
- Telegram bot instance is globally available
- Database connection is already established
- Users table exists with proper structure

### Risks
- [Potential issues or blockers]

Example:
- Telegram API rate limits might affect testing
- Need to handle users who have blocked the bot
- Migration needs to run on production database

### Future Enhancements
- [Ideas for future iterations]

Example:
- Email notifications in addition to Telegram
- Customizable notification templates
- Notification history/audit log

---

## Post-Implementation

### What Worked
[After Ralph completes, document what worked well]

### What Didn't
[Document any issues or unexpected behaviors]

### Lessons Learned
[Key takeaways for future Ralph tasks]

### Actual Iterations Used
[How many iterations did it take?]

### Total Time
[How long did it run?]

### Cost Estimate
[Rough API cost if tracked]

---

## Quick Reference

**Simple Task Template:**
```bash
/ralph-loop "[Do X in file Y]" --completion-promise "X done" --max-iterations 5
```

**Medium Task Template:**
```bash
/ralph-loop "[Create service X, add command Y, test Z]" --completion-promise "tests pass" --max-iterations 10
```

**Complex Task Template:**
Use the full format above with detailed requirements.

---

## Tips

1. **Be Specific:** The more detail you provide, the better Ralph performs
2. **Test Requirements:** Always include testing requirements
3. **Completion Promise:** Make it specific and testable
4. **Iteration Estimate:** Start conservative, you can always run again
5. **Context:** Reference existing files/patterns for consistency
6. **Break Down:** If task feels too big, split into multiple Ralph runs

---

Save this PRD before running Ralph. After completion, update the "Post-Implementation" section with your findings.
