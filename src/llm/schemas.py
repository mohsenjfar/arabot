from pydantic import BaseModel, field_validator, ConfigDict, Field
from typing import Optional, List, Any
from datetime import datetime
import logging
import re

from core import timezone

logger = logging.getLogger(__name__)


class TaskBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    summary: Optional[str] = None
    dtstart: Optional[datetime] = None
    dtend: Optional[datetime] = None
    next_date: Optional[datetime] = None
    exdate: Optional[List[Any]] = None
    rxdate: Optional[List[Any]] = None
    is_recurrent: Optional[bool] = False
    rrule: Optional[str] = None
    rrule_human: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = False
    notified: Optional[bool] = False

    @field_validator("dtstart", "dtend", "next_date", mode="before")
    def convert_datetime_to_naive_utc(cls, v):
        try:
            if v is None:
                return None

            if isinstance(v, datetime):
                if v.tzinfo is not None:
                    return v.astimezone(None).replace(tzinfo=None)
                return v

            if isinstance(v, str):
                v = timezone.to_english_digits(v)
                return timezone.str_to_utc(v)

            raise ValueError("Invalid datetime format")

        except Exception as e:
            logger.warning(f"Error converting datetime: {e}")
            raise ValueError("Invalid datetime format")

    @field_validator("rrule", mode="before")
    def remove_time_from_daily_rrule(cls, v):
        if not isinstance(v, str):
            return v

        if "FREQ=DAILY" in v.upper():
            cleaned_v = re.sub(r';?(BYHOUR|BYMINUTE|BYSECOND)=[^;]*', '', v, flags=re.IGNORECASE)
            cleaned_v = re.sub(r';+', ';', cleaned_v).strip(';')
            if cleaned_v.upper() == "FREQ=DAILY":
                return "FREQ=DAILY"
            return cleaned_v

        return v


class TaskCreate(TaskBase):
    summary: str
    dtstart: datetime = Field(
        default_factory=lambda: timezone.now().replace(microsecond=0, tzinfo=None),
        description="Start date and time of the task (stored as naive UTC datetime)"
    )
    notified: bool = False

    @field_validator("summary")
    def summary_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("summary cannot be empty")
        return v.strip()


class TaskUpdate(TaskBase):
    notified: bool = False


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int
    summary: str
    dtstart: str
    dtend: str
    next_date: str
    description: Optional[str] = None
    completed: bool
    is_recurrent: bool
    rrule_human: str

