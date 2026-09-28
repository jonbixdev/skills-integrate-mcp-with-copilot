"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

TEACHERS_FILE = current_dir / "teachers.json"
PASSWORD_HASH_ITERATIONS = 600_000
TEACHER_SESSION_TTL_SECONDS = 8 * 60 * 60
teacher_sessions: dict[str, tuple[str, float]] = {}


class TeacherCredentials(BaseModel):
    username: str
    password: str


def load_teachers() -> list[dict[str, str]]:
    try:
        data = json.loads(TEACHERS_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=503, detail="Teacher credentials are unavailable") from error

    teachers = data.get("teachers") if isinstance(data, dict) else None
    if not isinstance(teachers, list):
        raise HTTPException(status_code=503, detail="Teacher credentials are unavailable")
    return [teacher for teacher in teachers if isinstance(teacher, dict)]


def verify_teacher_password(username: str, password: str) -> bool:
    for teacher in load_teachers():
        if teacher.get("username") != username:
            continue

        salt = teacher.get("salt")
        password_hash = teacher.get("password_hash")
        if not isinstance(salt, str) or not isinstance(password_hash, str):
            return False
        try:
            expected_hash = bytes.fromhex(password_hash)
            salt_bytes = bytes.fromhex(salt)
        except ValueError:
            return False

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt_bytes, PASSWORD_HASH_ITERATIONS
        )
        return hmac.compare_digest(actual_hash, expected_hash)
    return False


def require_teacher(teacher_session: str | None = Cookie(default=None)) -> str:
    if teacher_session is None:
        raise HTTPException(status_code=401, detail="Teacher login required")

    session = teacher_sessions.get(teacher_session)
    if session is None or session[1] <= time.time():
        teacher_sessions.pop(teacher_session, None)
        raise HTTPException(status_code=401, detail="Teacher login required")
    return session[0]


@app.post("/auth/login")
def login(credentials: TeacherCredentials, response: Response):
    if not verify_teacher_password(credentials.username, credentials.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    session_token = secrets.token_urlsafe(32)
    teacher_sessions[session_token] = (
        credentials.username,
        time.time() + TEACHER_SESSION_TTL_SECONDS,
    )
    response.set_cookie(
        key="teacher_session",
        value=session_token,
        max_age=TEACHER_SESSION_TTL_SECONDS,
        httponly=True,
        secure=os.getenv("SECURE_COOKIES", "").lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"username": credentials.username}


@app.get("/auth/session")
def get_teacher_session(teacher_username: str = Depends(require_teacher)):
    return {"username": teacher_username}


@app.post("/auth/logout")
def logout(response: Response, teacher_session: str | None = Cookie(default=None)):
    if teacher_session is not None:
        teacher_sessions.pop(teacher_session, None)
    response.delete_cookie(
        key="teacher_session",
        secure=os.getenv("SECURE_COOKIES", "").lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"message": "Logged out"}


# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    teacher_username: str = Depends(require_teacher),
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    teacher_username: str = Depends(require_teacher),
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
