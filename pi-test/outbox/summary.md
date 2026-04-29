# Summary

The inbox describes a prototype healthcare appointment booking backend.

## Goal
Build a simple backend API for a healthcare appointment booking app.

## Main users
- Patient
- Admin

## Patient features
- Register an account
- Log in
- View available doctors
- Search doctors by specialty
- Book an appointment
- Cancel an appointment
- View appointment history

## Admin features
- Add doctors
- Update doctor availability
- View all bookings

## Technical direction
- Backend first
- Python + FastAPI
- PostgreSQL
- Docker or Podman for local setup
- Simple REST API
- Authentication can be basic for the prototype
- First version can run locally, with possible later deployment to OpenShift

## Sample domain data
Doctors have:
- Name
- Specialty
- Availability slots

Patients have:
- Name
- Email

## Suggested core backend entities
- User
- Doctor
- AvailabilitySlot
- Appointment

## Prototype focus
The first version should be simple, easy to demo, and junior-developer friendly. That means:
- Keep authentication simple
- Use straightforward REST endpoints
- Start with a small database schema
- Add validation to avoid double-booking and invalid cancellations
