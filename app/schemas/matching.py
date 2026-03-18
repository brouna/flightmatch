from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.matching import PilotResponse


class MatchingRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    rule_key: str
    enabled: bool
    parameters: dict
    created_at: datetime
    updated_at: datetime


class MatchingRuleUpdate(BaseModel):
    enabled: bool | None = None
    parameters: dict | None = None
    description: str | None = None


class MatchLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mission_id: int
    pilot_id: int
    matched_at: datetime
    hard_filter_pass: bool
    score: float | None
    rank: int | None
    features_json: dict | None
    notification_sent: bool
    pilot_response: PilotResponse
    response_at: datetime | None


class MatchLogUpdate(BaseModel):
    pilot_response: PilotResponse
    response_at: datetime | None = None


class RankedPilot(BaseModel):
    pilot_id: int
    pilot_name: str
    pilot_email: str
    home_airport: str
    score: float
    rank: int
    hard_filter_pass: bool
    features: dict
    match_log_id: int


class RankedMission(BaseModel):
    mission_id: int
    title: str
    origin_airport: str
    destination_airport: str
    earliest_departure: datetime
    score: float
    rank: int
    features: dict
