"""What to search for: cities near Nitzan x field-service categories."""

CITIES = [
    "אשדוד",
    "אשקלון",
    "ראשון לציון",
    "יבנה",
    "גן יבנה",
    "קריית מלאכי",
    "ניצן",
]

# category key -> Hebrew search phrase sent to Google Maps
CATEGORIES = {
    "pest_control": "הדברה",
    "plumbing": "אינסטלטור",
    "electrician": "חשמלאי",
    "elevators": "חברת מעליות",
    "gates_cameras": "שערים חשמליים ומצלמות אבטחה",
    "solar_boilers": "דודי שמש",
    "air_conditioning": "מיזוג אוויר",
    "cleaning": "חברת ניקיון",
    "gardening": "גינון",
    "appliance_repair": "תיקון מכשירי חשמל",
    "locksmith": "מנעולן",
    "movers": "הובלות",
}

# Google free tier for this SKU is 1,000 requests/month; the key's daily
# quota is set to 30 in Google Cloud, so stop before hitting it.
MAX_REQUESTS_PER_RUN = 30

# Re-query a city/category only after this many days.
CACHE_DAYS = 30
