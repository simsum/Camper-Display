from datetime import date
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from calendar_url import normalize_calendar_url

DISPLAY_WIDTH = 1480
DISPLAY_HEIGHT = 320


class ScreenConfig(BaseModel):
    id: str
    stand_enabled: bool = True
    stand_duration_seconds: int = Field(default=30, ge=3, le=600)
    drive_enabled: bool = False
    drive_duration_seconds: int = Field(default=30, ge=3, le=600)


class VacationConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=80)
    start_date: date
    end_date: date
    destination: str = Field(default="", max_length=120)
    enabled: bool = True

    @model_validator(mode="after")
    def end_must_not_precede_start(self):
        if self.end_date < self.start_date:
            raise ValueError("Urlaubsende darf nicht vor dem Beginn liegen")
        return self


class Settings(BaseModel):
    config_version: int = 8
    screens: list[ScreenConfig] = Field(
        default_factory=lambda: [
            ScreenConfig(id="clock_flip", stand_enabled=True, drive_enabled=True),
            ScreenConfig(id="clock_blue", stand_enabled=False, drive_enabled=False),
            ScreenConfig(id="clock_blank", stand_enabled=False, drive_enabled=False),
            ScreenConfig(id="clock_panorama", stand_enabled=False, drive_enabled=False),
            ScreenConfig(id="clock_led", stand_enabled=False, drive_enabled=False),
            ScreenConfig(id="clock_linear", stand_enabled=False, drive_enabled=False),
            ScreenConfig(id="clock_marble", stand_enabled=False, drive_enabled=False),
            ScreenConfig(id="journey", stand_enabled=False, drive_enabled=False),
            ScreenConfig(id="calendar", stand_enabled=True, stand_duration_seconds=20, drive_enabled=False, drive_duration_seconds=20),
            ScreenConfig(id="weather", stand_enabled=True, stand_duration_seconds=20, drive_enabled=False, drive_duration_seconds=20),
            ScreenConfig(id="map", stand_enabled=False, stand_duration_seconds=30, drive_enabled=True, drive_duration_seconds=45),
            ScreenConfig(id="sun", stand_enabled=True, stand_duration_seconds=20, drive_enabled=False, drive_duration_seconds=20),
        ]
    )
    brightness_stand: int = Field(default=40, ge=10, le=100)
    brightness_drive: int = Field(default=100, ge=10, le=100)
    panel_opacity_percent: int = Field(default=52, ge=10, le=95)
    panel_blur_pixels: int = Field(default=0, ge=0, le=16)
    time_format_24h: bool = True
    theme: Literal["flip", "blue", "blank"] = "flip"
    theme_background_colors: dict[str, str] = Field(default_factory=dict)
    gpsd_host: str = ""
    gpsd_port: int = 2947
    weather_unit_celsius: bool = True
    display_width: int = Field(default=DISPLAY_WIDTH, frozen=True)
    display_height: int = Field(default=DISPLAY_HEIGHT, frozen=True)
    trip_destination_name: str = ""
    display_schedule_enabled: bool = True
    display_off_time: str = "22:30"
    display_on_time: str = "07:00"
    night_behavior: Literal["off", "clock", "normal"] = "clock"
    brightness_night: int = Field(default=5, ge=1, le=100)
    night_color: Literal["amber", "red", "white"] = "amber"
    night_wake_seconds: int = Field(default=30, ge=5, le=600)
    arrival_enabled: bool = True
    arrival_wait_seconds: int = Field(default=300, ge=1, le=3600)
    arrival_duration_seconds: int = Field(default=30, ge=5, le=180)
    touch_wake_enabled: bool = True
    touch_wake_hold_seconds: int = Field(default=120, ge=5, le=600)
    drive_enter_speed_kmh: float = Field(default=8.0, ge=1, le=50)
    drive_enter_seconds: int = Field(default=10, ge=1, le=120)
    stand_enter_speed_kmh: float = Field(default=3.0, ge=0, le=30)
    stand_enter_seconds: int = Field(default=180, ge=10, le=1800)
    gps_state_hold_seconds: int = Field(default=300, ge=10, le=3600)
    map_zoom_near: int = 16
    map_zoom_far: int = 11
    map_zoom_speed_threshold_kmh: int = 80
    map_trail_enabled: bool = True
    map_trail_max_hours: int = 12
    photo_frame_manual_seconds: int = Field(default=300, ge=30, le=3600)
    vacations: list[VacationConfig] = Field(default_factory=list)
    calendar_enabled: bool = False
    calendar_url: str = Field(default="", max_length=4096, repr=False)

    @model_validator(mode="before")
    @classmethod
    def migrate_arrival_minutes(cls, value):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if 'arrival_wait_seconds' not in data and 'arrival_wait_minutes' in data:
            try:
                data['arrival_wait_seconds'] = float(data['arrival_wait_minutes']) * 60
            except (ValueError, TypeError):
                raise ValueError('Ungültige bisherige Ankunftswartezeit') from None
        data.pop('arrival_wait_minutes', None)
        return data

    @field_validator("display_off_time", "display_on_time")
    @classmethod
    def valid_display_time(cls, value: str) -> str:
        import re
        if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value):
            raise ValueError("Uhrzeit muss im Format HH:MM angegeben werden")
        return value

    @field_validator("screens")
    @classmethod
    def remove_retired_modules(cls, value: list[ScreenConfig]) -> list[ScreenConfig]:
        # Also discard submissions from an old settings page left open during an update.
        return [screen for screen in value if screen.id not in {"trip", "news", "photo_frame"}]

    @field_validator("display_width", "display_height", mode="before")
    @classmethod
    def fixed_display_geometry(cls, value, info):
        # Keep response fields for older clients, but never accept custom geometry.
        return DISPLAY_WIDTH if info.field_name == "display_width" else DISPLAY_HEIGHT

    @field_validator("calendar_url")
    @classmethod
    def validate_calendar_url(cls, value: str) -> str:
        return normalize_calendar_url(value)

    @model_validator(mode="after")
    def calendar_requires_url(self):
        if self.calendar_enabled and not self.calendar_url:
            raise ValueError("Bitte zuerst einen iCloud-Kalenderlink eintragen.")
        return self


class TripReset(BaseModel):
    confirm: bool = False


class ArrivalTestRequest(BaseModel):
    place_name: str = Field(min_length=1, max_length=120)

    @field_validator('place_name', mode='before')
    @classmethod
    def trim_place_name(cls, value):
        return value.strip() if isinstance(value, str) else value


class TrailPoint(BaseModel):
    latitude: float
    longitude: float


class SimulatedPosition(BaseModel):
    place_name: str = ""
    latitude: float | None = None
    longitude: float | None = None
    speed_kmh: float = 0.0
    altitude_m: float | None = None
    heading_deg: float | None = Field(default=None, ge=0, lt=360)


class OperatingStateOverride(BaseModel):
    mode: Literal["auto", "stand", "drive"]


class RouteStatus(BaseModel):
    has_route: bool = False
    progress: float = 0.0
    start_label: str | None = None
    dest_label: str | None = None


class GpsStatus(BaseModel):
    connected: bool
    latitude: float | None = None
    longitude: float | None = None
    speed_kmh: float | None = None
    altitude_m: float | None = None
    altitude_reference: Literal["msl", "hae"] | None = None
    heading_deg: float | None = None
    trip_km: float = 0.0
    route: RouteStatus = RouteStatus()
    simulation_active: bool = False


class ForecastDay(BaseModel):
    date: str
    condition_code: int | None = None
    temp_max: float | None = None
    temp_min: float | None = None
    precipitation_probability: float | None = None
    precipitation_sum: float | None = None


class WeatherStatus(BaseModel):
    available: bool
    latitude: float | None = None
    longitude: float | None = None
    location_name: str | None = None
    temperature: float | None = None
    apparent_temperature: float | None = None
    precipitation: float | None = None
    wind_speed: float | None = None
    condition_code: int | None = None
    unit_celsius: bool = True
    forecast: list[ForecastDay] = Field(default_factory=list)
    sunrise: str | None = None
    sunset: str | None = None
    daylight_duration_seconds: float | None = None
    moonrise: str | None = None
    moonset: str | None = None
    moon_phase_fraction: float | None = None


class MoonStatus(BaseModel):
    phase_name: str
    emoji: str
    illumination_pct: float
    phase_fraction: float
    moonrise: str | None = None
    moonset: str | None = None


class OperatingStatus(BaseModel):
    mode: Literal["stand", "drive"]
    forced_mode: Literal["stand", "drive"] | None = None
    gps_connected: bool = False
    speed_kmh: float | None = None
    manual_wake_active: bool = False
    manual_wake_remaining_seconds: int = 0


class DisplayStatus(BaseModel):
    display_on: bool
    brightness_percent: int
    night_clock_active: bool = False
    manual_off: bool = False
    brightness_control: Literal["software", "hardware"] = "software"


class StatusResponse(BaseModel):
    server_time_iso: str
    gps: GpsStatus
    weather: WeatherStatus
    moon: MoonStatus
    operating: OperatingStatus
    display: DisplayStatus
    calendar: dict = Field(default_factory=dict)
    arrival: dict = Field(default_factory=dict)
    photo_frame: dict = Field(default_factory=dict)
