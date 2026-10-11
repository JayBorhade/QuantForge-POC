# QuantForge UX, Accessibility & Product Polish Audit

**Branch:** `quality/pony-tail-hardening`  
**Validation snapshot:** the prior branch revision passed frontend and backend CI. The newest additions below require the latest commit CI run and browser-based manual checks before merge. This document is not an accessibility or security certification.

## Repository findings

- Frontend: Next.js App Router, React 19, TypeScript, Tailwind CSS, Radix UI primitives, Axios.
- Backend: FastAPI, SQLAlchemy/Alembic, JWT authentication, broker adapters and trading workflows.
- Existing test/build commands: `npm run typecheck`, `npm run lint`, `npm run build` in `frontend/`; Python unittest discovery and migration/startup checks in `.github/workflows/ci.yml`.
- Existing auth uses server-backed endpoints and cookies. Pricing data is sourced from the billing API. No analytics provider or contact submission API was found during this pass.
- Work is isolated to `quality/pony-tail-hardening`; `main` has not been modified.

## Feature acceptance matrix

| # | Feature | Status | Implementation / reason |
|---|---|---|---|
| 1 | Dark mode toggle | PARTIAL | Added persisted light/dark preference, system preference fallback, early theme initialization, shared color tokens and light-theme overrides. Contrast and visual regression still require manual verification. |
| 2 | Cookie banner | NOT APPLICABLE | The repository currently has essential authentication/session cookies and no configured optional analytics/tracking service. A misleading accept/reject banner would imply consent controls for processing that is not configured. Reassess when optional cookies or analytics are introduced. |
| 3 | Site search | PARTIAL | Added keyboard-dismissible, focus-managed search over known application pages/features. It deliberately does not query private records or claim to index all content. |
| 4 | Back-to-top | PARTIAL | Added a threshold-based control with reduced-motion support and accessible naming; visual overlap needs responsive manual review. |
| 5 | Responsive mobile menu | PARTIAL | Improved marketing navigation and added a mobile dashboard sidebar with Escape dismissal, focus trapping, focus restoration, hidden closed navigation, route-close behavior and overlay. Keyboard and screen-reader behavior still need manual accessibility review. |
| 6 | Loading animations | PARTIAL | Added/standardized truthful loading feedback for dashboard, portfolio, live-trading, backtesting, strategy, deployment, broker, settings, logs and password-recovery operations. Other async views still need a route-by-route audit. |
| 7 | Hover and interaction states | PARTIAL | Improved shared focus-visible, hover, disabled and motion styles. Some page-specific hard-coded colors remain and need theme review. |
| 8 | Scroll progress | PARTIAL | Added a lightweight reading progress indicator to docs and blog routes only; it uses document scroll and is intentionally omitted from compact dashboards. |
| 9 | Copy-to-clipboard | PARTIAL | Added a reusable copy button for the real quick-start commands, with success/failure announcements. Requires secure-context browser testing. |
| 10 | Print stylesheet | PARTIAL | Added print rules to hide navigation/floating controls and preserve readable text/tables. Representative pages still require print-preview review. |
| 11 | Sticky headers | PARTIAL | Marketing navigation is already fixed/sticky. Dashboard navigation remains fixed; individual dashboard header behavior has not been standardized. |
| 12 | Skip-to-content | PARTIAL | Added a visible-on-focus skip link and main landmarks for primary public, auth and dashboard routes. Verify every secondary route manually. |
| 13 | Password visibility | PARTIAL | Password-type shared inputs now have a show/hide button that preserves the field value and uses accessible labels. Verify password-manager and screen-reader behavior. |
| 14 | UTM tracking | BLOCKED | No analytics provider, attribution endpoint, or consent configuration exists. The implementation does not persist or transmit UTM data without a configured purpose/consent path. Add only after the owner chooses the provider and privacy requirements. |
| 15 | Form success states | PARTIAL | Auth success continues through existing server-confirmed flows; strategy, broker and deployment actions show feedback only after API success. Contact uses a mail draft and explicitly does not claim delivery. |
| 16 | Form error states | PARTIAL | Added actionable, non-diagnostic errors and live announcements to login/signup/password recovery/contact, strategy, broker, deployment, risk, settings and log workflows. Other forms still need review. |
| 17 | Confirmation dialog | PARTIAL | Added native browser confirmation before strategy/deployment stop requests, disabling two-factor authentication and changing the portfolio kill switch. Native dialogs are accessible but are not branded custom modals; review other consequential actions before expanding. |
| 18 | Last-updated date | NOT APPLICABLE | No authoritative content/data-updated timestamp is exposed for the pages changed in this pass. Existing blog dates are publication dates and are labelled as such; no current date is fabricated as an update time. |
| 19 | Expandable FAQ | PARTIAL | Added product-specific native `details/summary` FAQ entries to pricing. Content and keyboard behavior still need manual review. |
| 20 | Floating contact button | PARTIAL | Added a contact link on public marketing routes. The contact page prepares a mail draft only when `NEXT_PUBLIC_SUPPORT_EMAIL` is configured; no server-side delivery endpoint exists. Configure and test the real destination before claiming full support intake. |

## Additional integrity changes

- Removed unsupported landing-page performance metrics, the randomized synthetic performance chart, hard-coded market ticker prices and hard-coded marketing prices. Subscription plans now come from the billing API and show an unavailable state instead of fabricated fallback pricing.
- Added real article destinations for the existing blog links and labelled their dates as publication dates.
- Added date-range/capital validation and truthful completed/failed/timeout handling to the backtest form; prevented undefined metric labels from being presented as results.
- Fixed CSRF-cookie parsing in the Axios client and made network-error refresh handling safer.
- Added a real `/dashboard/logs` page backed by the existing user-scoped strategy-run and audit-log endpoints; the synthetic system-log endpoint is intentionally not presented as genuine monitoring data.
- Hardened settings workflows with explicit 2FA loading/error/success states, six-digit OTP validation, confirmation before disabling 2FA, billing portal destination validation, and removed an unsaved email-alert checkbox that did not persist any preference.
- Added signup duplicate-submit protection, numeric-only 2FA input and registration success feedback on login; validated contact email input before preparing a mail draft.
- Throttled scroll progress updates to animation frames and made the closed mobile dashboard drawer non-focusable. Added safer generic error messages for selected forms; credentials and server diagnostic details are not intentionally surfaced by these UI messages.
- No database schema, trading algorithms, broker API contracts or live-execution rules were intentionally changed.

## Verification still required

- [ ] Latest GitHub Actions run for the final documentation and code commit succeeds for backend tests, frontend typecheck, lint, production build, migration validation and startup smoke tests.
- [ ] Manually inspect light/dark themes on landing, docs, pricing, auth, dashboard and admin screens.
- [ ] Keyboard-only pass: skip link, mobile menus, search dialog focus trap/restore, password visibility, FAQ and all forms.
- [ ] Test copy success/failure in secure and unsupported clipboard contexts.
- [ ] Test strategy/deployment stop cancellation and API failure behavior.
- [ ] Verify `NEXT_PUBLIC_SUPPORT_EMAIL` in a deployment and test mail-client behavior.
- [ ] Decide on analytics provider and privacy/consent requirements before implementing UTM persistence.
- [ ] Review npm audit findings from CI separately; dependencies were not force-upgraded as part of this UX pass.

**Completion rule:** no feature should be labelled COMPLETE until its relevant automated checks and manual edge cases have been verified. UTM attribution remains intentionally blocked pending a chosen analytics provider and consent requirements; a cookie banner and last-updated date remain omitted because there is no configured optional tracking or authoritative content-updated timestamp.
