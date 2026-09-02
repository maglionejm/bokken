# Lanzadera

On-demand commuter shuttle for Spanish suburbs. Riders book a seat on a
shared van for their daily commute; routes adapt nightly to demand.

## Shipped capabilities

- **Booking**: reserve a recurring weekday seat (`/reservar`); changes allowed
  until 21:00 the night before.
- **Live tracking**: van position on a map with an estimated pickup window
  of +/- 6 minutes (`/en-vivo`).
- **Route engine**: nightly re-optimization; riders may be assigned a pickup
  point up to 400 m from home to keep routes efficient.
- **Pricing**: monthly pass at 89 EUR (Madrid ring) covering 2 trips/day;
  pay-per-ride at 3.20 EUR.
- **Notifications**: push 15 minutes before pickup; SMS fallback.

## Design principles

- Spanish-first UI (ES default, EN available).
- No account required to see routes and prices; booking requires phone
  verification only.
- The pickup-window promise (+/- 6 min) is the product's core covenant:
  every feature defends it.
