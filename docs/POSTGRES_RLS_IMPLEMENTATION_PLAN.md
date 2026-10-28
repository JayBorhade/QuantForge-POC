# PostgreSQL Row-Level Security (RLS) — implementation and release plan

Status: **OPEN — design documented, not enabled**  
Scope: QuantForge multi-user financial and strategy data  
Last reviewed: 2026-10-11

## Why this is a release gate

Application-level ownership predicates are necessary but do not protect against a future route that accidentally omits a predicate. PostgreSQL RLS can provide defense in depth, but only when the request identity is established safely and every runtime path uses a role subject to the policies. Adding policies without that foundation can either leak data (owner/superuser bypass) or break authentication, workers, billing webhooks, and scheduled execution.

## Required architecture before enabling policies

1. **Separate roles**
   - A non-owner runtime role for API requests, Celery workers, schedulers, and WebSocket-related database access.
   - A migration role that owns schema objects and is used only by migrations.
   - No runtime role may be superuser, have `BYPASSRLS`, or own protected tables.
   - Enable and force RLS only after deployment confirms the runtime role is not the table owner and policy tests run under that role.

2. **Transaction-scoped identity**
   - Establish `app.user_id` with `SELECT set_config('app.user_id', '<validated UUID>', true)` inside the same database transaction as the protected work.
   - Set identity only after token signature, session revocation, and active-account checks have succeeded.
   - Never use session-level (non-local) settings with pooled connections.
   - Ensure the value is reset automatically at transaction end and cannot be inherited by a later request on the same pooled connection.
   - Do not accept tenant identity from request headers or body.

3. **Non-user execution contexts**
   - Define explicit least-privilege handling for Celery/scheduler tasks, Stripe webhooks, administrative workflows, health probes, and migrations.
   - Worker tasks must derive the owner from a persisted resource and establish the context before accessing user rows.
   - Webhooks must resolve the user through verified provider identifiers and use a constrained service role or a validated owner context.
   - Admin access must be audited and must not silently bypass all tenant policies.
   - Health checks must not need access to tenant data.

4. **Table inventory and policy semantics**
   - Direct-owner tables: `portfolios`, `strategies`, `deployments`, `broker_tokens`, `notifications`, `subscriptions`, plus any additional tables with `user_id`.
   - Child tables without `user_id` must use parent ownership predicates, for example `orders`, `positions`, `trades`, `risk_limits`, `cash_ledger_entries`, `execution_fills`, `portfolio_snapshots`, and `strategy_runs`.
   - Session/authentication tables and globally scoped billing/webhook/idempotency records require separate policies; do not apply a generic `user_id` policy without testing authentication bootstrap.
   - Audit logs require both owner visibility rules and a separate restricted admin/audit-reader policy.

5. **Write policies**
   - Use matching `USING` and `WITH CHECK` expressions for SELECT/UPDATE/DELETE and INSERT/UPDATE.
   - For child resources, use `EXISTS` predicates that join to the parent resource and compare its owner to `current_setting('app.user_id', true)::uuid`.
   - Missing or malformed context must deny access, not fall back to unrestricted access.
   - Never use permissive default policies or a policy that trusts a caller-supplied owner ID.

## Required tests before enabling

- PostgreSQL integration tests run as the actual non-owner runtime role, not the migration role.
- Two-user tests for every protected direct-owner and child table: read, insert, update, delete, nested-resource access, and bulk queries.
- Verify no context, empty context, malformed context, and pooled-connection reuse all deny access.
- Verify a transaction for user A cannot expose A's context to user B.
- Exercise API authentication bootstrap, refresh/revocation, MFA, Celery tasks, scheduler, Stripe webhook processing, and admin workflows.
- Verify table owner, migration role, runtime role, superuser, and `BYPASSRLS` behavior explicitly.
- Test migration upgrade and rollback strategy on a disposable PostgreSQL database populated with representative records.
- Keep a rollout kill switch limited to deployment configuration; do not silently disable RLS in production after a policy failure.

## Rollout order

1. Inventory all tables, query paths, background jobs, webhooks, and DB roles.
2. Create/verify separate roles and secret provisioning in staging.
3. Implement a transaction-local identity helper and add it to authenticated API and worker entry points.
4. Add policies in a migration, initially validated in a disposable PostgreSQL environment.
5. Run two-user integration tests using the runtime role and all non-request contexts.
6. Deploy to staging, inspect denial logs and application errors, and test migrations/rollback.
7. Enable RLS in production only after security review and evidence are attached to the release.
8. Update the security audit only when these checks pass.

## Current release decision

RLS is **not implemented or verified**. Do not describe this document as a mitigation. Until the implementation and tests above are complete, keep the RLS release gate open and do not approve production deployment.
