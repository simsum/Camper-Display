from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

import display_scheduler
import arrival_service
import calendar_client
import geocode_client
import gps_client
import moon_phase
import operating_state
import photo_api
import photo_share
import photo_frame_service
import settings_store
import weather_client
import traccar_api
import traccar_cache
from models import (
    GpsStatus,
    ArrivalTestRequest,
    MoonStatus,
    OperatingStateOverride,
    OperatingStatus,
    DisplayStatus,
    Settings,
    SimulatedPosition,
    StatusResponse,
    TrailPoint,
    TripReset,
    WeatherStatus,
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
APP_VERSION = "0.6.5"


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings_store.load_settings()
    stop_events = [
        traccar_cache.start_background_thread(),
        calendar_client.start_background_thread(),
        gps_client.start_background_thread(),
        operating_state.start_background_thread(),
        display_scheduler.start_background_thread(),
        display_scheduler.start_touch_watch_thread(),
        arrival_service.start_background_thread(),
    ]
    try:
        yield
    finally:
        for stop_event in stop_events:
            stop_event.set()


app = FastAPI(title="Camper-Display", version=APP_VERSION, lifespan=lifespan)
app.include_router(traccar_api.router)
app.include_router(photo_api.router)
app.include_router(photo_share.router)


@app.get("/api/health", include_in_schema=False)
def get_health() -> dict:
    return {
        "status": "ok" if settings_store.healthcheck() else "degraded",
        "app": "camper-uhr",
        "version": APP_VERSION,
    }


@app.get("/api/settings", response_model=Settings)
def get_settings() -> Settings:
    return settings_store.load_settings()


@app.put("/api/settings", response_model=Settings)
def put_settings(settings: Settings) -> Settings:
    previous = settings_store.load_settings()
    settings_store.save_settings(settings)

    current_gps = gps_client.get_status()
    route = settings_store.load_trip_route()

    dest_lat, dest_lon = route["dest_lat"], route["dest_lon"]
    if settings.trip_destination_name != previous.trip_destination_name:
        geocoded = geocode_client.geocode(settings.trip_destination_name)
        dest_lat, dest_lon = geocoded if geocoded else (None, None)

    settings_store.save_trip_route(
        start_lat=current_gps["latitude"],
        start_lon=current_gps["longitude"],
        dest_name=settings.trip_destination_name or None,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
    )
    return settings


@app.get("/api/calendar/status")
def get_calendar_status() -> dict:
    return calendar_client.get_status()


@app.post("/api/calendar/refresh", status_code=202)
def refresh_calendar() -> dict:
    calendar_client.request_refresh()
    return {"ok": True}


@app.post("/api/trip/reset")
def post_trip_reset(_: TripReset) -> dict:
    settings_store.reset_trip()
    return {"ok": True}


@app.post("/api/debug/simulate-position")
def post_simulate_position(pos: SimulatedPosition) -> dict:
    lat, lon = pos.latitude, pos.longitude
    if pos.place_name.strip():
        geocoded = geocode_client.geocode(pos.place_name)
        if not geocoded:
            raise HTTPException(status_code=404, detail="Ort nicht gefunden")
        lat, lon = geocoded
    if lat is None or lon is None:
        raise HTTPException(status_code=422, detail="Ort oder Koordinaten angeben")
    gps_client.set_simulated_fix(lat, lon, pos.speed_kmh, pos.altitude_m, pos.heading_deg)
    return {
        "ok": True,
        "latitude": lat,
        "longitude": lon,
        "altitude_m": pos.altitude_m,
    }


@app.post("/api/debug/simulate-disconnect")
def post_simulate_disconnect() -> dict:
    gps_client.clear_simulated_fix()
    return {"ok": True, "simulation_active": False}


@app.post("/api/debug/operating-state")
def post_operating_state(state: OperatingStateOverride) -> dict:
    operating_state.set_forced_mode(None if state.mode == "auto" else state.mode)
    return {"ok": True, **operating_state.get_status()}


@app.get("/api/gps/trail", response_model=list[TrailPoint])
def get_gps_trail() -> list[dict]:
    return gps_client.get_trail()


@app.post("/api/debug/display-off")
def post_display_off() -> dict:
    display_scheduler.force_display_power(turn_on=False)
    return {"ok": True}


@app.post("/api/debug/display-on")
def post_display_on() -> dict:
    display_scheduler.force_display_power(turn_on=True)
    return {"ok": True}


@app.post("/api/display/wake")
def post_display_wake() -> dict:
    return {"ok": True, "woken": display_scheduler.wake_from_touch()}


@app.get("/api/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    settings = settings_store.load_settings()
    gps = gps_client.get_status()
    weather = weather_client.get_weather(
        gps["latitude"], gps["longitude"], settings.weather_unit_celsius
    )
    moon = (
        moon_phase.phase_from_fraction(weather["moon_phase_fraction"])
        if weather["moon_phase_fraction"] is not None
        else moon_phase.current_phase()
    )
    moon.update(moonrise=weather["moonrise"], moonset=weather["moonset"])
    return StatusResponse(
        server_time_iso=datetime.now(timezone.utc).astimezone().isoformat(),
        gps=GpsStatus(**gps),
        weather=WeatherStatus(**weather),
        moon=MoonStatus(**moon),
        operating=OperatingStatus(**operating_state.get_status()),
        display=DisplayStatus(**display_scheduler.get_status()),
        calendar=calendar_client.get_status(settings),
        arrival=arrival_service.get_status(),
        photo_frame=photo_frame_service.status(),
    )


@app.get("/api/arrival/status")
def get_arrival_status() -> dict:
    return arrival_service.get_status()


@app.post("/api/arrival/test", status_code=202)
def test_arrival(request: ArrivalTestRequest) -> dict:
    if not arrival_service.request_test(request.place_name):
        raise HTTPException(status_code=429, detail="Bitte den laufenden Test abwarten (maximal einmal pro Minute).")
    return {"ok": True, "message": "Ankunftstest für den Simulationsort gestartet; GPS-Einstellungen bleiben unverändert."}


@app.get("/api/arrival/image/{event_id}")
def get_arrival_image(event_id: str) -> Response:
    result = arrival_service.image_for(event_id)
    if not result:
        raise HTTPException(status_code=404, detail="Kein Ankunftsfoto")
    data, mime = result
    return Response(data, media_type=mime, headers={"Cache-Control":"private, max-age=300", "X-Content-Type-Options":"nosniff"})


@app.get("/settings")
def get_settings_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "settings.html", headers={"Cache-Control": "no-store"})


@app.get("/photos")
def get_photos_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "photos.html", headers={"Cache-Control": "no-store"})


@app.get("/")
@app.get("/index.html")
def get_kiosk_page() -> FileResponse:
    # The entry document selects versioned scripts. Never reuse an old manifest
    # after deployment, even when the kiosk retains its Chromium profile.
    return FileResponse(FRONTEND_DIR / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/journey")
def get_journey_page() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "journey-preview.html", headers={"Cache-Control": "no-store"})


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
