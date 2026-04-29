# API Design

## Authentication assumption
- Prototype uses bearer token authentication
- Patients can register and log in
- Admin users can be seeded manually at first
- Protected endpoints require `Authorization: Bearer <token>`

---

## 1. Register patient
**Endpoint path:** `/auth/register`

**HTTP method:** `POST`

**Request body:**
```json
{
  "name": "Alice",
  "email": "alice@example.com",
  "password": "secret123"
}
```

**Response body:**
```json
{
  "id": 1,
  "name": "Alice",
  "email": "alice@example.com",
  "role": "patient"
}
```

**Error responses:**
- `400 Bad Request` - invalid input
- `409 Conflict` - email already exists

**Basic validation rules:**
- name is required
- email must be valid format
- email must be unique
- password should have a minimum length

---

## 2. Login
**Endpoint path:** `/auth/login`

**HTTP method:** `POST`

**Request body:**
```json
{
  "email": "alice@example.com",
  "password": "secret123"
}
```

**Response body:**
```json
{
  "access_token": "token_here",
  "token_type": "bearer"
}
```

**Error responses:**
- `400 Bad Request` - missing fields
- `401 Unauthorized` - invalid credentials

**Basic validation rules:**
- email and password are required

---

## 3. List doctors
**Endpoint path:** `/doctors`

**HTTP method:** `GET`

**Request body:**
- None

**Query params:**
- `specialty` (optional)

**Response body:**
```json
[
  {
    "id": 1,
    "name": "Dr Tan",
    "specialty": "Cardiology"
  }
]
```

**Error responses:**
- `500 Internal Server Error`

**Basic validation rules:**
- specialty filter is optional
- specialty match can be exact or case-insensitive contains

---

## 4. Get doctor availability
**Endpoint path:** `/doctors/{doctor_id}/availability`

**HTTP method:** `GET`

**Request body:**
- None

**Response body:**
```json
[
  {
    "slot_id": 10,
    "start_time": "2026-05-04T10:00:00Z",
    "end_time": "2026-05-04T10:30:00Z",
    "is_available": true
  }
]
```

**Error responses:**
- `404 Not Found` - doctor not found

**Basic validation rules:**
- doctor_id must exist

---

## 5. Book appointment
**Endpoint path:** `/appointments`

**HTTP method:** `POST`

**Request body:**
```json
{
  "doctor_id": 1,
  "slot_id": 10
}
```

**Response body:**
```json
{
  "id": 101,
  "patient_id": 5,
  "doctor_id": 1,
  "slot_id": 10,
  "status": "booked"
}
```

**Error responses:**
- `400 Bad Request` - invalid request
- `404 Not Found` - doctor or slot not found
- `409 Conflict` - slot already booked
- `401 Unauthorized` - not logged in

**Basic validation rules:**
- patient must be authenticated
- slot must belong to the doctor
- slot must still be available

---

## 6. Cancel appointment
**Endpoint path:** `/appointments/{appointment_id}`

**HTTP method:** `DELETE`

**Request body:**
- None

**Response body:**
```json
{
  "message": "Appointment cancelled successfully"
}
```

**Error responses:**
- `404 Not Found` - appointment not found
- `403 Forbidden` - appointment belongs to another patient
- `409 Conflict` - appointment already cancelled

**Basic validation rules:**
- patient must own the appointment unless admin support is added
- only booked appointments can be cancelled

---

## 7. View patient appointment history
**Endpoint path:** `/appointments/me`

**HTTP method:** `GET`

**Request body:**
- None

**Response body:**
```json
[
  {
    "id": 101,
    "doctor_name": "Dr Tan",
    "specialty": "Cardiology",
    "start_time": "2026-05-04T10:00:00Z",
    "status": "booked"
  }
]
```

**Error responses:**
- `401 Unauthorized`

**Basic validation rules:**
- user must be authenticated as patient

---

## 8. Add doctor
**Endpoint path:** `/admin/doctors`

**HTTP method:** `POST`

**Request body:**
```json
{
  "name": "Dr Lee",
  "specialty": "Neurology"
}
```

**Response body:**
```json
{
  "id": 4,
  "name": "Dr Lee",
  "specialty": "Neurology"
}
```

**Error responses:**
- `400 Bad Request`
- `401 Unauthorized`
- `403 Forbidden`

**Basic validation rules:**
- admin role required
- name and specialty are required

---

## 9. Update doctor availability
**Endpoint path:** `/admin/doctors/{doctor_id}/availability`

**HTTP method:** `PUT`

**Request body:**
```json
{
  "slots": [
    {
      "start_time": "2026-05-05T11:00:00Z",
      "end_time": "2026-05-05T11:30:00Z"
    }
  ]
}
```

**Response body:**
```json
{
  "message": "Availability updated successfully"
}
```

**Error responses:**
- `400 Bad Request`
- `401 Unauthorized`
- `403 Forbidden`
- `404 Not Found`

**Basic validation rules:**
- admin role required
- doctor must exist
- end_time must be after start_time
- overlapping slots for the same doctor should be rejected

---

## 10. View all bookings
**Endpoint path:** `/admin/appointments`

**HTTP method:** `GET`

**Request body:**
- None

**Response body:**
```json
[
  {
    "id": 101,
    "patient_name": "Alice",
    "doctor_name": "Dr Tan",
    "start_time": "2026-05-04T10:00:00Z",
    "status": "booked"
  }
]
```

**Error responses:**
- `401 Unauthorized`
- `403 Forbidden`

**Basic validation rules:**
- admin role required

---

## Optional simple health check
**Endpoint path:** `/health`

**HTTP method:** `GET`

**Response body:**
```json
{
  "status": "ok"
}
```
