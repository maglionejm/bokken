# Tasks

- [x] Count all four billed token buckets in the replayed budget meter at face
      value; verified with replay tests.
- [x] Prove the stopping rule fires on cache-heavy spend; verified with a
      runner test whose engine bills 195,000 cache-read tokens.
- [x] Consolidate cost estimation into one `call_cost_usd` function over all
      four buckets with per-provider cache multipliers read off the model
      registry; verified with pricing tests for both providers.
- [x] Route the cost rows and the report's model usage lines through that one
      function and carry cache tokens on the usage lines; verified by pricing a
      single cache-heavy trace identically through both paths.
- [x] `make check` green.
