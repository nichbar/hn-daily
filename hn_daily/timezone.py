"""Timezone settings for hn-daily."""

from datetime import timedelta, timezone


APP_TIMEZONE = timezone(timedelta(hours=8), "UTC+08:00")
