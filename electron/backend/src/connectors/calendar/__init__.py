"""
Google Calendar Connector Module

This module provides Google Calendar integration for LocalBrain,
allowing users to sync their calendar events for ingestion and search.
"""

from .calendar_connector import CalendarConnector, sync_calendar_events

__all__ = ['CalendarConnector', 'sync_calendar_events']
