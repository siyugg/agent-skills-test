# Risks and Questions

## Missing information
1. **Auth details are not fully defined**
   - Should the prototype use JWT, session auth, or a hardcoded admin token?
   - How should admin users be created?

2. **Appointment slot duration is not defined**
   - Are slots fixed to 30 minutes, 60 minutes, or manually managed?

3. **Doctor availability format is too simple**
   - The inbox lists examples like "Monday 10:00" but not exact dates or durations
   - Real booking usually needs concrete timestamps

4. **Cancellation policy is not defined**
   - Can patients cancel anytime?
   - Should past appointments be protected from cancellation?

5. **Search behavior is not defined**
   - Should specialty search be exact match, partial match, or case-insensitive?

6. **Admin scope is not fully defined**
   - Can admin cancel bookings?
   - Can admin edit doctor details after creation?

7. **Patient profile fields are minimal**
   - Is name and email enough for the prototype?
   - Is phone number needed?

8. **Time zone handling is not defined**
   - This can cause booking mistakes if ignored

## Technical risks
1. **Double-booking risk**
   - If two users book the same slot at the same time, the backend needs protection using database constraints or transactions

2. **Weak auth for demo becoming permanent**
   - A simple prototype auth approach is okay short term, but it should not be treated as production-ready

3. **Availability data model may become messy**
   - If availability is stored as plain text, later changes will be hard
   - Better to store structured time slots from the beginning

4. **Insufficient validation**
   - Without validation, invalid emails, overlapping slots, and broken appointment states may appear

5. **Deployment differences**
   - Local Docker/Podman setup may differ from future OpenShift deployment

## Questions for the team lead
1. What auth method should be used for the prototype?
2. How will admin users be created and managed?
3. What is the default appointment duration?
4. Should availability be stored as exact date/time slots or repeating weekly schedule?
5. Can patients reschedule, or only cancel and rebook?
6. Should patients be allowed to see only future available slots or also all doctor schedules?
7. Should cancelled appointments remain visible in history?
8. Do we need audit logging for admin actions?
9. Should the prototype include database migrations and seed scripts?
10. Is OpenShift readiness required now, or only later?

## Recommended decisions for the prototype
If the team lead wants fast progress, a good simple choice is:
- JWT auth
- Seed one admin user
- Fixed 30-minute slots
- Store exact timestamps in UTC
- Allow cancel only for future booked appointments
- Keep cancelled appointments in history with status `cancelled`
