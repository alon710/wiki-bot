# WhatsApp Message Templates

This directory contains the simplified WhatsApp message templates used by the WikiBot. Only essential templates are included for daily facts and subscription management.

## Setup Instructions

1. **Create Templates in Twilio Console:**
   - Go to Twilio Console → Messaging → Content Templates
   - Create a new template for each file in this directory
   - Copy the content from each `.txt` file and paste it into Twilio Console
   - Submit for WhatsApp approval

2. **Update Environment Variables:**
   After creating templates, update your `.env` file with the template SIDs:
   ```
   TWILIO_SUBSCRIPTION_SUBSCRIBED_TEMPLATE_SID=HX...
   TWILIO_SUBSCRIPTION_UNSUBSCRIBED_TEMPLATE_SID=HX...
   TWILIO_DAILY_FACT_TEMPLATE_SID=HX...
   TWILIO_MENU_TEMPLATE_SID=HX...
   ```

## Template Variables

Templates use these variables:
- `{{1}}` - Dynamic content (fact text for daily_fact, content keys for other templates)
- `{{2}}` - User phone number for personalization (optional)

## Template Files

| File | Purpose | Code Usage | Content Type |
|------|---------|------------|--------------|
| `daily_fact.txt` | Daily Wikipedia facts | `MessageType.DAILY_FACT` | Standard |
| `subscription_subscribed.txt` | Subscription enabled | `MessageType.SUBSCRIPTION_CHANGED` (subscribed=true) | Standard |
| `subscription_unsubscribed.txt` | Subscription disabled | `MessageType.SUBSCRIPTION_CHANGED` (subscribed=false) | Standard |
| `menu_list_picker.txt` | Interactive menu with options | `MessageType.MENU` | List Picker |

## Special Template Notes

### List Picker Template (menu_list_picker.txt)
- **Content Type**: List Picker (Interactive)
- **Requires**: WhatsApp Business API (not sandbox)
- **Structure**: Header, Body, Button Text, List Items with IDs
- **User Experience**: Users tap a button to see the list, then select an option
- **Response**: Bot receives the selected item ID (e.g., "daily_fact", "subscription_toggle")

### Standard Templates
- **Content Type**: Standard (Text-based)
- **Simple text**: Plain Hebrew messages
- **Variables**: Support dynamic content insertion

## Important Notes

1. **Approval Required:** All templates must be approved by WhatsApp before they can be used
2. **Hebrew Content:** All templates contain Hebrew text as this is a Hebrew-only bot
3. **Template Matching:** The template SID in your environment must match the template name
4. **Testing:** Test templates manually in Twilio Console before deploying

## Troubleshooting

- **Messages not received:** Check template approval status
- **Template not found errors:** Verify template SIDs in environment variables
- **Variable errors:** Ensure template variables match what's being sent from code