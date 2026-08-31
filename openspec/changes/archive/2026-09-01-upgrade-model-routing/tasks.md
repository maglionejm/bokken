# Tasks: upgrade-model-routing

## 1. Routing

- [x] 1.1 Extend `RoutingClass` to research/challenge/cognition/generation/
  extraction; update defaults + allowlist; verify router unit tests
- [x] 1.2 Provider: per-model request shape (Fable: no thinking, effort high,
  server-side fallback beta; Opus: adaptive + effort high); verify with a
  stub client asserting kwargs
- [x] 1.3 Reclassify call sites (empathize/persona → research; skeptic,
  converge lenses, test → challenge; handoff specify → generation); verify
  offline e2e journals the new classes

## 2. Definition of done

- [x] 2.1 `make check` green; report cost table knows fable pricing
