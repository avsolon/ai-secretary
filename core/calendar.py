import datetime
import logging
import os
import pickle
from typing import List, Dict, Any, Optional, Tuple

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarClient:
    def __init__(self, config):
        self.config = config
        self._service = None

    def _authenticate(self):
        creds = None
        token_file = self.config.GOOGLE_CALENDAR_TOKEN
        cred_file = self.config.GOOGLE_CALENDAR_CRED

        if os.path.exists(token_file):
            with open(token_file, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(cred_file):
                    raise FileNotFoundError(
                        f"Google Calendar credentials file not found: {cred_file}"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(cred_file, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_file, "wb") as token:
                pickle.dump(creds, token)

        self._service = build("calendar", "v3", credentials=creds)

    def _get_service(self):
        if self._service is None:
            self._authenticate()
        return self._service

    def get_free_slots(
        self,
        date: datetime.date,
        work_start: str = "09:00",
        work_end: str = "18:00",
        slot_duration: int = 60,
    ) -> List[Dict[str, str]]:
        service = self._get_service()
        calendar_id = self.config.GOOGLE_CALENDAR_ID

        start_datetime = datetime.datetime.combine(
            date, datetime.time.fromisoformat(work_start)
        )
        end_datetime = datetime.datetime.combine(
            date, datetime.time.fromisoformat(work_end)
        )

        events_result = (
            service.events()
            .list(
                calendarId=calendar_id,
                timeMin=start_datetime.isoformat() + "Z",
                timeMax=end_datetime.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        busy_slots = []
        for event in events_result.get("items", []):
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            busy_slots.append(
                (
                    datetime.datetime.fromisoformat(start),
                    datetime.datetime.fromisoformat(end),
                )
            )

        free_slots = []
        current = start_datetime
        while current + datetime.timedelta(minutes=slot_duration) <= end_datetime:
            slot_end = current + datetime.timedelta(minutes=slot_duration)
            is_busy = any(
                start < slot_end and end > current for start, end in busy_slots
            )
            if not is_busy:
                free_slots.append(
                    {
                        "start": current.strftime("%H:%M"),
                        "end": slot_end.strftime("%H:%M"),
                        "start_iso": current.isoformat(),
                        "end_iso": slot_end.isoformat(),
                    }
                )
            current += datetime.timedelta(minutes=slot_duration)

        return free_slots

    def create_event(
        self,
        summary: str,
        start_time: datetime.datetime,
        end_time: datetime.datetime,
        description: str = "",
        attendee_email: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        service = self._get_service()
        calendar_id = self.config.GOOGLE_CALENDAR_ID

        event = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "Europe/Moscow",
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "Europe/Moscow",
            },
        }

        if attendee_email:
            event["attendees"] = [{"email": attendee_email}]

        try:
            created = (
                service.events()
                .insert(calendarId=calendar_id, body=event)
                .execute()
            )
            logger.info("Event created: %s", created.get("htmlLink"))
            return created
        except HttpError as e:
            logger.error("Failed to create event: %s", e)
            return None
