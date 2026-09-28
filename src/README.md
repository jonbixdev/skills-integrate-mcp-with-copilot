# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Create a teacher account. You will be prompted for its password, and only a salted password hash is stored:

   ```
   python src/create_teacher.py teachername
   ```

3. Run the application from the repository root:

   ```
   uvicorn app:app --app-dir src --reload
   ```

4. Open the app at http://localhost:8000. API documentation is available at `/docs` and `/redoc`.

Teacher credentials are stored in `src/teachers.json`, which is ignored by Git. Teacher sessions use an HTTP-only, same-site cookie and expire after eight hours. Set `SECURE_COOKIES=true` when serving the app over HTTPS.

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/auth/login`                                                     | Log in as a teacher                                                  |
| POST   | `/auth/logout`                                                    | End the current teacher session                                      |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Register a student (teachers only)                                  |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teachers only)                             |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity data and teacher sessions are stored in memory, which means activity data resets and teacher sessions end when the server restarts. Teacher credential hashes are stored separately in `src/teachers.json`.
