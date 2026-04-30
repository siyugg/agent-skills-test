# Junior Developer Tasks

## Task 1: Create project skeleton
- Set up FastAPI app
- Add folders for routes, models, schemas, services, and database
- Add requirements file

**Done when:** API starts locally and `/docs` is accessible.

---

## Task 2: Set up PostgreSQL connection
- Configure database URL from environment variables
- Add database session setup
- Test connection locally

**Done when:** App can connect to PostgreSQL without hardcoded credentials.

---

## Task 3: Create database models
- Create `User` model
- Create `Doctor` model
- Create `AvailabilitySlot` model
- Create `Appointment` model

**Done when:** Tables can be created successfully.

---

## Task 4: Add request and response schemas
- Create Pydantic schemas for auth
- Create schemas for doctors
- Create schemas for availability slots
- Create schemas for appointments

**Done when:** Route handlers use schemas instead of raw dictionaries.

---

## Task 5: Build auth endpoints
- Implement patient registration
- Implement login
- Hash passwords properly
- Return bearer token

**Done when:** A patient can register and log in successfully.

---

## Task 6: Build doctor listing and search
- Add endpoint to list doctors
- Add optional specialty filter
- Add endpoint to get doctor availability

**Done when:** User can search doctors and see available slots.

---

## Task 7: Build appointment booking
- Add endpoint to create appointment
- Check that slot exists
- Check that slot is not already booked
- Mark slot as unavailable after successful booking

**Done when:** Patient can book a valid slot and duplicate booking is blocked.

---

## Task 8: Build appointment cancellation
- Add endpoint to cancel appointment
- Make sure patient can only cancel their own appointment
- Update appointment status correctly
- Free the slot again if the system supports that behavior

**Done when:** Patient can cancel their own booking safely.

---

## Task 9: Build appointment history
- Add endpoint for current patient to view their appointments
- Include doctor name, time, and status

**Done when:** Logged-in patient can view current and past bookings.

---

## Task 10: Build admin doctor management
- Add admin-only endpoint to create doctors
- Add admin-only endpoint to update availability

**Done when:** Admin can add doctors and manage slots.

---

## Task 11: Build admin booking view
- Add admin-only endpoint to list all appointments
- Include patient and doctor details

**Done when:** Admin can review all bookings.

---

## Task 12: Add validation and error handling
- Validate email format
- Validate required fields
- Return proper HTTP status codes
- Add helpful error messages

**Done when:** Invalid requests return clear errors.

---

## Task 13: Add sample seed data
- Insert sample doctors from the requirement
- Insert sample availability
- Optionally add sample users

**Done when:** Demo data can be loaded with one command.

---

## Task 14: Add tests
- Test register
- Test login
- Test doctor search
- Test booking success
- Test booking conflict
- Test cancellation
- Test admin permissions

**Done when:** Core flows are covered by automated tests.

---

## Task 15: Add local run support
- Write Dockerfile
- Add compose file or Podman instructions
- Document setup steps in README

**Done when:** Another developer can run the project locally without guessing setup steps.

## Suggested order for the junior developer
1. Tasks 1-4
2. Task 5
3. Tasks 6-9
4. Tasks 10-11
5. Tasks 12-15

## Helpful coding tips
- Keep route functions small
- Move business logic into service functions
- Use clear names like `book_appointment` and `cancel_appointment`
- Test each endpoint before starting the next one
- Commit small working changes regularly
