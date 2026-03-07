---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - _bmad-output/planning-artifacts/product-brief-joat_stores-2026-02-23.md
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/project-context.md
workflowType: 'ux-design'
project_name: 'joat_stores'
user_name: 'KAFURAHA'
date: '2026-02-25'
---

# UX Design Specification — joat_stores

**Author:** KAFURAHA
**Date:** 2026-02-25

---

<!-- UX design content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

### Project Vision

joat_stores is a B2B2C multi-vertical commerce operating system for Kenyan SMEs — retail, restaurant, and bar — on a single platform. Merchants own their branded storefront outright. M-Pesa is a first-class payment rail across all verticals. 3G mobile performance is a hard constraint on every UX decision, not a nice-to-have.

### Target Users

**Consumer Personas:**

**Daniel** — first-time or repeat Kenyan digital shopper. WhatsApp-native, M-Pesa literate, distrustful of "paying online" without familiar trust signals. Has been scammed before — social proof and brand recognition matter more than SSL badges. Wants to buy without registering. Primary fear: paying twice because the STK Push appeared to fail. Primarily on mobile, often 3G.

**Amara** — restaurant or bar customer in a group setting. Sharing a phone around the table, ordering with modifiers, wanting to split the bill without awkwardness. One-handed usability is a real constraint (other hand holds a drink). Primary anxiety: "did the kitchen actually get our order?"

**Operator Personas:**

**Store Manager** — runs daily operations on a budget Android device (Samsung A-series, Tecno, Infinix). Not a tech person. Checks revenue in the morning in 30 seconds. Manages staff who make mistakes (wrong table, wrong item) and needs self-service recovery flows. Needs the kitchen display to scream when it goes offline — not quietly badge.

**KAFURAHA (Platform Admin)** — manages all tenants and demos to investors live. Needs merchant onboarding to feel like a narrative story with a "go live" reveal moment. Needs tenant health readable in a traffic-light view in under 10 seconds. The platform admin has a secondary audience: investors watching over the shoulder.

### Key Design Challenges

1. **Multi-vertical single codebase** — retail checkout, QR dine-in, and bar tab are three fundamentally different journeys sharing one Next.js storefront; UX patterns must flex without fracturing
2. **M-Pesa STK Push waiting state** — the 3–8 second dead air between "we sent you a prompt" and the phone buzzing is the highest-risk trust moment; silence = perceived failure = double-tap = double payment
3. **3G performance budget** — every UX decision has a hard < 200KB weight and < 2s load constraint; decorative UX is a liability
4. **Per-tenant brand isolation** — components must feel owned by each merchant; customers must never see "joat_stores"
5. **Admin complexity across verticals** — retail, restaurant, and bar admins have fundamentally different mental models; one app must serve all three
6. **Error states as primary UX** — M-Pesa timeouts, network drops, and sync delays are frequent in a 3G-first market; failure states need the same design care as happy paths
7. **Budget Android admin** — store manager UX must work on mid-range Android browsers with large tap targets and minimal data usage
8. **Group dining coordination** — multiple people at one table, shared device, split bill expectation — the dine-in flow must handle group dynamics, not just individual orders

### Design Opportunities

1. **M-Pesa-native checkout delight** — design the STK Push waiting state and confirmation as a first-class mobile moment; countdown animation + "don't tap again" message eliminates the double-payment fear
2. **QR dine-in as the showpiece experience** — scan → branded menu → one-handed modifier selection → split bill → M-Pesa payment; no waiter required; the demo that converts restaurant owners
3. **Kitchen view as a precision tool** — full-screen alarming offline state; glanceable ticket list; large touch targets for wet hands; auto-refresh failure impossible to miss
4. **Analytics as answers, not data** — "is my business okay right now?" answered in one mobile screen in < 3 seconds; one revenue number, one trend, one alert — not twelve charts
5. **Investor demo flow** — merchant onboarding as a narrative with a "go live" reveal moment; tenant health as a traffic-light view; "first order" milestone highlighted; designed to be demoed live
6. **WhatsApp-native sharing** — order confirmations and receipts designed to be screenshot-friendly; WhatsApp share as a primary action
7. **Trust signals for Kenyan digital commerce** — M-Pesa branding, recognizable merchant identity, and community social proof replace Western SSL badges as primary trust signals

### Specific Design Requirements (from persona research)

**Consumer (Daniel — Retail):**
- Guest checkout required — account registration must never block first purchase
- Trust signals displayed before the product grid loads
- STK Push waiting state: visible pulse animation + countdown + "don't tap again" message
- Double-payment prevention: disable pay button immediately on first tap, show "payment sent" confirmation

**Consumer (Amara — Restaurant/Bar):**
- Table session supports multiple payers and split bill as first-class feature
- Post-order submission shows whole-table-visible confirmation ("your order is with the kitchen")
- Modifier selection modal usable one-handed with large touch targets
- Bill view shows per-person itemization with individual M-Pesa pay buttons

**Store Manager (Admin):**
- Morning summary: revenue + unresolved items on one mobile screen, loads < 3s
- Kitchen display offline state: full-screen alarming warning, not a badge
- Staff error recovery: wrong table / wrong item correctable without manager intervention
- Admin designed mobile-first — primary device is a budget Android, not a laptop

**Platform Admin (KAFURAHA):**
- Merchant onboarding: step-by-step progress with "go live" reveal moment and auto-navigate to new store URL
- Tenant health view: traffic-light status (green/amber/red) per tenant, sortable by health score
- "First order" milestone highlighted per tenant in platform dashboard
- Investor demo path: guided flow through GMV → tenant health → new merchant onboarding in under 5 minutes

### Edge Case Design Requirements (from What If Scenarios)

**Retail — Payment & Stock:**
- Post-3rd STK Push failure: show "your cart is saved — try again later" + "check your M-Pesa messages for any deductions" — never leave user uncertain if they were charged
- Stock validation at checkout start, not at payment initiation — show specific out-of-stock item with "remove and continue" or "save for later" options; never fail at payment stage for a stock issue
- In-app browser detection (WhatsApp, Facebook): localStorage cart fallback + "open in Chrome" prompt before checkout; session-less cart recovery on return visit

**Restaurant — Session & Kitchen:**
- QR scan detects existing open table session → "Table 4 has an order in progress — join this session?" flow; never create duplicate sessions for the same table
- QR code always has short URL fallback printed below (`store.joat.com/t/12`) — manually enterable if QR scan fails
- Kitchen display: "last updated X seconds ago" timestamp always visible; amber state at 15s since last refresh; full-screen red "CONNECTION LOST — REFRESH NOW" + optional sound alert at 30s; frozen display must be visually impossible to miss
- Post-kitchen additional orders create a new ticket labeled "ADDITIONAL ORDER — Table 4 (2nd round)" — never merged with original order status

**Bar — Settlement & Disputes:**
- Tab settlement failure at closing: "record as unpaid — settle later" option captures customer phone; bar manager view shows all unsettled tabs; automated M-Pesa retry Celery task fires at 9am next day
- Per-round item attribution: each item shows who added it (staff member name or customer) + timestamp — visible in dispute resolution flow
- Item removal requires manager PIN for amounts > KES 500; all removals logged in `TabAuditLog` — never deleted
- Happy hour price transitions: "HH" badge on discounted items; automatic notice when first full-price item is added to tab — customer never surprised at settlement

---

## Core User Experience

### Defining Experience

The defining experience of joat_stores is the moment a Kenyan SME customer
completes a payment and knows — without doubt — that their money arrived and
their order is confirmed.

On 3G, with M-Pesa STK Push, in a market where payment anxiety is acute and
double-payment fear is real, this moment is anything but simple. Getting it
right is the entire product.

The platform serves three different core loops across its verticals, but they
all converge on this single moment of confirmed trust:

- **Retail loop:** Browse → Add to Cart → Checkout → M-Pesa STK Push →
  ✅ Payment Confirmed → Order Created
- **Restaurant loop:** QR Scan → Browse Branded Menu → Order with Modifiers →
  Submit → ✅ "Your order is with the kitchen" → M-Pesa at bill time
- **Bar loop:** Join Tab → Add Rounds → Track Per-Person Items → Settlement →
  ✅ Tab Settled via M-Pesa

**First Principles:** The retail core loop is confirm → pay → done, not
browse → discover → pay. Many Kenyan SME customers arrive knowing exactly
what they want from a WhatsApp referral — the catalog is validation, not
discovery. Commerce in this market is social — WhatsApp share is not optional;
it is the growth loop.

### Platform Strategy

**Primary platform: Mobile web (Progressive Web App)**

| Layer | Device Target | Connectivity | Optimization Focus |
|---|---|---|---|
| Customer (retail) | Any Android/iOS phone | 3G | < 200KB / < 2s LCP |
| Customer (restaurant/bar) | Shared table device | 3G/4G | Touch-first, split-variant modifiers |
| Store Manager (admin) | Budget Android (A-series, Tecno, Infinix) | 3G/WiFi | Mobile-first, large tap targets |
| Kitchen Display | Wall-mounted Android tablet, Chrome | WiFi | WebSocket viable, alarming offline |
| Platform Admin | Laptop / desktop | WiFi | Desktop-optimized ≥ 1024px breakpoint |

**Hard platform constraints:**
- Storefront: < 200KB initial payload, < 2s LCP on 3G
- Touch targets: 44×44px minimum; 48×48px in kitchen/bar/admin contexts
- Above-fold content (logo, store name, tagline, hero) must be SSR/SSG —
  first painted frame is branded, never skeletal; this is a trust requirement
- In-app browser detection: localStorage cart persistence + "open in Chrome"
  prompt before checkout
- Degraded-connectivity fallback defined for every interactive state —
  connectivity is a session parameter, not a baseline assumption
- Platform Admin has a responsive breakpoint ≥ 1024px for investor demo
  context (multi-column layout: tenant health grid + GMV chart + onboarding
  wizard side by side)

### Effortless Interactions

Six interactions that must require zero conscious thought:

1. **Guest checkout** — buying never requires account creation; registration
   prompt appears only post-payment as an optional "save your order history"
   offer

2. **M-Pesa STK Push flow** — from tap to confirmation:
   - Full-screen modal lock from the moment "Pay" is tapped (impossible to
     double-tap; evokes the learned Safaricom PIN modal behavior)
   - Merchant brand color as pulse animation (feels like *this store*)
   - Cycling micro-reassurances: "✓ Your cart is saved" → "✓ Your order
     number is ready" → "✓ Check your Safaricom phone"
   - Pre-filled M-Pesa number for returning visitors: "Paying from 07XX XXX
     XXX. Change?" — no account required
   - On any app re-open during pending payment: always resume waiting state,
     never the cart

3. **Cart persistence** — cart intact across session loss, browser switch,
   signal drop; cart state promoted to PostgreSQL the moment payment is
   initiated (Redis = fast path; PostgreSQL = safety net)

4. **QR-to-table session** — scan → immediately in the correct branded menu;
   always shows "You're joining Table [N]'s session at [Store Name]. Is this
   correct?" confirmation before joining (wrong-table guard, not friction)

5. **Kitchen ticket visibility** — priority-ranked workflow queue, not a
   flat notification list; additional orders render in amber with a distinct
   chime; on reconnect after outage: "CONNECTION RESTORED — X orders received
   while offline. Tap to review."

6. **Admin login → answer** — mobile admin always deep-links to dashboard
   on login; login → dashboard, no intermediary; the first screen IS the
   answer to "is my business okay?"

### M-Pesa Payment Confirmation Design

The confirmation screen is the product's most important moment. It is:

- A **receipt card** visually evoking M-Pesa receipt conventions — M-Pesa
  green, transaction ID prominent, "Confirmed by Safaricom" language,
  designed to be screenshotted
- **Two-stage transition:** "Order #1234 created — awaiting M-Pesa
  confirmation" → "✅ Payment confirmed" when webhook fires (matches Kenyan
  mental model: order first, payment confirmation second)
- **"Share on WhatsApp" as primary button** — copyable as a WhatsApp
  commerce message: "Hi [name], your order for [items] confirmed. Total:
  KES X. M-Pesa ref: [#]. — [Store Name]"
- **Always recoverable** — on any page load after payment initiation, check
  localStorage for `pending_payment_order_id`; if found and DB-confirmed,
  render confirmation screen regardless of navigation path
- **Idempotent** — if user lands twice (back button, duplicate webhook),
  shows same order: "Payment already confirmed at [HH:MM]"
- 1 soft cross-sell during STK Push wait (no button — awareness only)

### Critical Success Moments

**For Daniel (retail customer):**
He types his M-Pesa number at checkout — immediately sees "Welcome back.
Your last order was [items]." The store knows him by his phone number, not
his browser. The M-Pesa confirmation card loads, branded and
screenshot-ready, before he has time to doubt.

**For Amara (restaurant/bar customer):**
Ordering Nyama Choma ×4 for the table, she splits the modifiers: ×2 extra
sauce / ×2 no sauce — from one product selection on the shared phone. The
full-screen "Your order is with the kitchen" confirmation holds 3 seconds —
visible to everyone at the table. Order status progression: "Order received
→ Kitchen confirmed → Ready."

**For the Store Manager:**
Monday morning: revenue number + trend arrow + unresolved items count +
staff corrections made yesterday — all on one mobile screen, in under 3
seconds. No navigation required.

**For KAFURAHA (Platform Admin):**
During investor demo: clicks a tenant on the health dashboard — a slide-out
panel shows last order time, today's revenue, active alerts. Never leaves
the dashboard. New merchant onboarded in under 5 minutes, ending with the
"go live" reveal. The product tells its own story.

**For the Kitchen (make-or-break failure states):**
Display offline 30s — full-screen red, audible beep. Reconnects — banner:
"3 orders received while offline." Additional orders in amber — distinct
chime. Nothing is silent. Nothing is missed.

**For the Bar (dispute resolution):**
Customer challenges a removed item — bill shows ~~Item~~ "removed by [staff
name]" with timestamp, visible to the customer in real time. The audit trail
is customer-facing, not just internal.

### Experience Principles

Seven refined principles — unified for clarity and strength:

1. **Trust and payment are one surface** — M-Pesa branding, merchant
   identity (never "joat_stores"), and receipt design are all facets of the
   same trust surface. Above-fold content is SSR/SSG not for performance
   alone, but because the first painted frame is the first trust signal.

2. **Every system state is a designed, readable moment — silence is the
   only unacceptable state** — loading skeletons, progress indicators,
   "last updated X seconds ago", offline alerts, reconnect banners, and
   error messages are primary UX. Any state the user cannot read is a
   failure state, regardless of whether the underlying system is working.

3. **Budget Android-first; platform admin desktop-first** — consumer
   storefront and manager admin designed for Tecno Camon on Chrome mobile
   at 3G and scaled up; platform admin designed for ≥ 1024px laptop and
   scaled down. Two distinct optimization targets, never conflated.

4. **Repeat customers get frictionless shortcuts — recognition via M-Pesa
   number** — when a returning customer enters their M-Pesa number at
   checkout, that is the moment of recognition: show their last order,
   pre-fill, reduce to one confirmation tap. Phone number is identity;
   browser storage is a cache, not the source of truth.

5. **The operator's tool must not embarrass them** — self-service correction
   for every common staff error; admin home is the dashboard, not navigation;
   morning screen includes revenue + unresolved items + staff corrections
   count; no manager should need to call for help to fix a routine mistake.

6. **Empty states are onboarding** — every zero-state (empty catalog, no
   orders, blank kitchen display, first admin login) is a teaching moment
   that moves the user forward, not a dead end.

7. **Delight is post-transaction** — animation, wit, personality, and
   surprise live in the confirmation screen, empty states, and the "first
   order" milestone. They never appear in the checkout path. Trust must
   land before delight is earned.

### Resilience Design Principles

Five hardened behaviors derived from chaos testing:

1. **Cart-to-database on payment initiation** — cart state written to
   PostgreSQL `pending_cart` the moment "Pay" is tapped; Redis is the fast
   path, PostgreSQL is the safety net; webhook processing never depends
   solely on Redis availability

2. **Reconnection is an acknowledged event** — on any system reconnect
   (kitchen display, admin real-time feed), always surface a banner
   confirming the gap duration and any items missed; silent resume is
   forbidden

3. **QR scan always shows table confirmation** — "You're joining Table [N]'s
   session at [Store Name]. Correct?" before joining any session; prevents
   wrong-table scenarios caused by moved physical QR stickers

4. **Confirmation always self-recovers** — check localStorage for
   `pending_payment_order_id` on any page load post-payment; if found and
   DB-confirmed, render the confirmation screen regardless of navigation path

5. **Idempotent confirmation UI** — confirmation screen rendered twice shows
   same order with timestamp: "Payment already confirmed at [HH:MM]"; the
   UI expresses idempotency, not just the backend

### Group Ordering Design

For Amara's dine-in group scenario — distinct from single-item modifier flow:

- Product quantity selector surfaces a **split-variant control** when
  quantity > 1: "How do you want these split?" with modifier options per
  sub-quantity
- Example: Nyama Choma ×4 → ×2 [extra sauce] / ×2 [no sauce] — two line
  items, one product selection
- Order summary shows per-person attribution before submission for group
  review on the shared phone
- Each line item shows who added it (customer-visible in the dine-in flow,
  not just the internal audit log)

---

## Desired Emotional Response

### Primary Emotional Goals

joat_stores operates across four distinct emotional contexts — each persona
has a different primary emotional goal, but they all share a common arc:

**Trust → Confidence → Relief → Satisfaction**

This arc is the emotional spine of every joat_stores interaction. The product
earns trust before asking for commitment. It builds confidence during the
transaction. It delivers relief at the moment of confirmation. It leaves
the user with lasting satisfaction that creates return behavior.

| Persona | Primary Emotion | The Feeling | What Creates It |
|---|---|---|---|
| Daniel (retail) | **Relief** | "It worked. I didn't get scammed." | M-Pesa receipt card, two-stage confirmation, no silence |
| Amara (restaurant/bar) | **Calm certainty** | "The kitchen has our order. We're sorted." | Full-screen kitchen confirmation, order status progression |
| Store Manager | **Control** | "I know what's happening in my business." | Dashboard-first login, self-service recovery, real-time queue |
| KAFURAHA (platform admin) | **Pride** | "This is mine. This works. Watch." | Go-live reveal, tenant health, first order milestone |

### Emotional Journey Mapping

**Daniel's journey — from WhatsApp link to receipt:**

| Stage | Current Emotion | Target Emotion | Design Response |
|---|---|---|---|
| Arriving (from WhatsApp link) | Skepticism — "is this real?" | Cautious interest | Merchant brand + M-Pesa logo in first painted frame |
| Browsing products | Tentative evaluation | Growing trust | Social proof, recognizable merchant identity |
| Adding to cart (guest) | Hesitation — "will I need to register?" | Relief — "no signup required" | Guest checkout, no friction |
| Checkout initiated | Anxiety building | Steady confidence | Clear progress steps, no hidden costs |
| STK Push sent | Peak anxiety — "did it go through?" | Controlled waiting | Modal lock + cycling reassurances + merchant brand pulse |
| Payment confirmed | Relief wave | Satisfaction + delight | M-Pesa receipt card, WhatsApp share, two-stage confirmation |
| Post-purchase | Residual uncertainty | Settled confidence | Order number + "you'll receive an M-Pesa confirmation" note |
| Returning next time | Neutral | Welcomed back | M-Pesa number recognized: "Welcome back. Last order: [items]" |

**Amara's journey — from QR scan to settled bill:**

| Stage | Target Emotion | Design Response |
|---|---|---|
| QR scan | Curiosity → instant delight | Branded menu loads fast, table confirmed visually |
| Browsing menu | Appetite + pleasure | Food photography optimized for mobile, readable portions |
| Split-variant ordering | Focus, not confusion | "How do you want these split?" surfaces naturally at quantity > 1 |
| Order submission | Calm certainty | Full-screen 3-second confirmation visible to whole table |
| Watching status | Positive anticipation | "Order received → Kitchen confirmed → Ready" progression |
| Bill time | Ease, no awkwardness | Per-person itemization, individual M-Pesa pay buttons |

**Store Manager's morning routine:**

| Stage | Target Emotion | Design Response |
|---|---|---|
| Login | Anticipation (how did we do?) | Dashboard IS the landing — revenue answered in < 3s |
| Revenue check | Reassurance or alert readiness | One number, one trend, one alert — not 12 charts |
| Reviewing staff corrections | Control | Staff corrections count visible; review is one tap |
| Handling a mistake | Empowerment | Self-service recovery flows; never needs IT help |
| Kitchen display monitoring | Confidence | Real-time queue; offline state impossible to miss |

**KAFURAHA's investor demo:**

| Stage | Target Emotion | Design Response |
|---|---|---|
| Opening platform dashboard | Pride + readiness | Traffic-light tenant health, GMV visible at a glance |
| Clicking a tenant | Confidence | Slide-out panel: last order, today's revenue, no navigation |
| Starting merchant onboarding | Narrative excitement | Step-by-step flow that builds like a story |
| "Go live" moment | Celebration + pride | Reveal animation, auto-navigate to new store URL |
| First order notification | Vindication | "First order" milestone card highlighted in tenant view |

### Micro-Emotions

**Micro-emotions to cultivate:**

- **Trust** (pre-transaction) — earned through merchant brand-first rendering,
  M-Pesa familiarity signals, and social proof before product grids
- **Confidence** (during transaction) — built through full-screen modal lock,
  cycling reassurances, and the designed STK Push waiting state
- **Relief** (post-payment) — delivered through the receipt card visual
  language and two-stage "order placed → payment confirmed" sequence
- **Control** (operator daily use) — created by dashboard-first navigation,
  visible staff corrections, and priority-ranked kitchen queues
- **Empowerment** (error recovery) — from self-service mistake correction
  that never requires calling for help
- **Pride** (platform admin) — from go-live reveals, first order milestones,
  and an investor demo path designed to be narrated live
- **Belonging** (repeat customers) — from M-Pesa number recognition and
  "welcome back" moments without account registration

**Micro-emotions to eliminate:**

- **Anxiety about payment** — eliminated by the designed STK Push waiting
  state; silence during payment is the product's most dangerous UX state
- **Distrust of the platform** — eliminated by merchant-branding-first;
  customers must never see "joat_stores" or feel they're on a generic platform
- **Embarrassment** (operator) — eliminated by self-service recovery; no
  operator should feel exposed by a staff mistake
- **Overwhelm** (admin complexity) — eliminated by vertical-specific admin
  views; a bar manager never sees restaurant tables
- **Uncertainty during errors** — eliminated by the principle that every
  system state is readable; ambiguous states are designed out

### Design Implications

**Relief (Daniel's primary goal):**
→ Receipt card designed in M-Pesa visual language — green, transaction ID
  large, screenshot-ready; the visual communicates "this is real proof"
→ Two-stage confirmation matches Kenyan mental model (order first, receipt
  second)
→ "Check your M-Pesa messages" note anchors the experience to a trusted
  external source the user already knows

**Controlled confidence (STK Push anxiety management):**
→ Full-screen modal lock makes the user feel held, not abandoned
→ Cycling reassurances give the user something to read each second
→ Merchant brand color in the pulse animation keeps the experience branded

**Calm certainty (Amara's primary goal):**
→ Full-screen kitchen confirmation designed to be seen by a whole table —
  large text, 3-second hold, no dismissal required
→ Order status progression creates positive anticipation, not anxious waiting
→ Split-variant ordering handles group dynamics in one flow

**Control (Store Manager):**
→ Dashboard-first post-login — "is my business okay?" answered before
  any navigation happens
→ Staff corrections count on the morning screen
→ Kitchen display reconnect banner — gap acknowledged, missed orders surfaced

**Pride (KAFURAHA):**
→ Go-live reveal moment: animation + auto-navigate to the new store URL
→ Tenant health slide-out: investor question answered in 5 seconds
→ First order milestone card: the moment marked, not just logged

### Emotional Design Principles

1. **Earn trust, then earn delight** — trust must be established before any
   moment of delight. Animation and surprise in the checkout path reads as
   "flashy scam" to a user who hasn't trusted the platform yet. Delight is
   post-transaction.

2. **Design for the anxiety peak, not the average state** — the STK Push
   waiting state is the moment of maximum user anxiety in the entire product.
   This is where the most design effort is concentrated.

3. **Relief is a design deliverable** — "it worked" is not an accidental
   outcome; it is designed through the receipt card visual language, the
   two-stage confirmation, and the M-Pesa external anchor.

4. **The operator's emotional safety is a product feature** — a store
   manager who feels exposed by a staff mistake will not trust the platform.
   Self-service recovery flows are emotional safety features, not convenience.

5. **Celebrate the merchant's milestones as if they are your own** — the
   go-live moment and the first order milestone are the most important
   emotional moments in a merchant's digital commerce journey. The product
   expresses this with reveal animations and milestone cards — not just
   logs it in a database.

---

## UX Pattern Analysis & Inspiration

### Inspiring Products Analysis

Six products analyzed — chosen because their users overlap directly with
joat_stores' personas.

---

**1. M-Pesa / Safaricom App**
*Why it matters: Daniel uses it daily. It is the most trusted mobile
interface in Kenya.*

- **What it does brilliantly:** The full-screen PIN entry modal trains
  users to expect a takeover interaction during payment — a learned behavior
  joat_stores can leverage. The M-Pesa receipt SMS format (green, transaction
  ID, amount, counterparty, timestamp) is the canonical Kenyan "proof of
  payment" — burned into memory.
- **Trust mechanism:** Safaricom brand recognition is the highest trust
  signal in Kenyan mobile. Any payment UI that visually references M-Pesa
  green and receipt conventions inherits that trust.
- **Key pattern:** The 2–4 second silence between initiating payment and
  receiving the PIN prompt is inherent to STK Push. Safaricom accepts this
  silence. joat_stores must fill it — which Safaricom itself does not.

---

**2. WhatsApp**
*Why it matters: Amara and Daniel live here. Kenyan commerce already
happens in WhatsApp — joat_stores is the infrastructure layer underneath.*

- **What it does brilliantly:** One-tap share. Location sharing via maps.
  Photo as product catalog. The established Kenyan buyer flow: see product
  screenshot in chat → "I want this" → share location → pay via M-Pesa →
  photo of receipt.
- **Key pattern:** Every joat_stores confirmation screen is a WhatsApp
  message waiting to be composed. The confirmation is pre-formatted as:
  "Order confirmed: [items]. Total: KES X. Ref: [M-Pesa #]. — [Store Name]"
  — copyable with one tap.
- **Key pattern:** "Share Location" button in delivery address — opens
  native maps, not a text field. This is how Kenyan customers already do it.
- **What to avoid:** WhatsApp's lack of structure (no order numbers, no
  inventory management) is exactly what joat_stores replaces — don't
  replicate its informality in the commerce layer.

---

**3. Bolt Kenya**
*Why it matters: Real-time status during a high-anxiety "in-progress"
transaction — the closest UX analogue to the STK Push waiting state.*

- **What it does brilliantly:** "Booking confirmed → driver found → driver
  arriving → arrived" status progression converts anxiety into positive
  anticipation. Each state transition is a micro-reassurance.
- **Key pattern (adapted):** The STK Push waiting state maps directly to
  "booking confirmed, driver being assigned." joat_stores: "Payment sent →
  Safaricom processing → ✅ Confirmed." Each transition visually distinct
  and emotionally forward.
- **Key pattern:** Bolt's failure recovery is fast and shame-free — the
  error is the system's fault, not the user's. Same philosophy for M-Pesa
  timeout recovery.
- **What to avoid:** Bolt's surge pricing anxiety — the unexpected cost
  change at checkout. joat_stores shows final totals before STK Push is
  sent, never after.

---

**4. Jumia Kenya**
*Why it matters: The established Kenyan e-commerce reference — what users
compare joat_stores against.*

- **What it does brilliantly:** Order status tracking ("packed → shipped →
  delivered"), category navigation, cash-on-delivery trust signal.
- **Key pattern:** Status progression as trust — "packed" and "shipped"
  convert waiting into evidence of real activity. joat_stores restaurant
  order status ("received → kitchen confirmed → ready") borrows this.
- **What to avoid (critical):** Mandatory account creation before checkout.
  Jumia's registration wall is the most cited friction point for first-time
  Kenyan buyers. joat_stores guest checkout is a direct competitive response.
- **What to avoid:** Jumia's page weight is punishing on 3G. joat_stores
  storefront must be 10× lighter.

---

**5. Shopify Admin (Mobile)**
*Why it matters: The gold standard merchant dashboard — what Store Manager
and KAFURAHA intuitively compare against.*

- **What it does brilliantly:** "Today at a glance" card on mobile —
  revenue, orders, sessions in one card. Analytics as answers: "Sales are
  up 12% vs last week" rather than raw numbers.
- **Key pattern:** The "overview card" model — one summary card per domain
  with a single headline number and trend indicator. Direct inspiration for
  the Store Manager morning screen.
- **Key pattern:** Low stock alert as an orange banner surfaced at the
  top — urgency-appropriate, not buried in inventory settings.
- **What to adapt:** Shopify mobile still assumes a decent device and WiFi.
  joat_stores achieves the same density at 3G on a Tecno A-series —
  fewer elements, larger text, aggressive data caching.
- **What to avoid:** Shopify's onboarding is a checklist of tasks —
  functional but not emotional. joat_stores' onboarding is a narrative
  with a go-live reveal, not a checklist.

---

**6. Toast POS (Restaurant/Bar Operations)**
*Why it matters: The closest operational UX reference for the kitchen
display, table management, and bar tab.*

- **What it does brilliantly:** Kitchen Display System (KDS) with ticket
  priority by time elapsed — tickets go white → yellow → red as they age.
  Table grid with color-coded status. Tab management with per-seat
  itemization and split bill.
- **Key pattern:** Time-based color escalation — joat_stores adapts as:
  white (new order) → amber (additional order) → red (offline/aged).
  Time elapsed visible on each ticket.
- **Key pattern:** Table grid view where each tile shows occupancy and
  order activity — Store Manager operational overview for restaurant vertical.
- **What to adapt:** Toast is a native app on dedicated hardware. joat_stores
  runs in Chrome on a wall-mounted Android tablet — touch targets must be
  larger, offline state more aggressive (no native OS notification layer).

### Transferable UX Patterns

**Navigation Patterns:**

- **Dashboard-first (Shopify)** — post-login landing is the operational
  summary, not a navigation menu; adapted for joat_stores mobile admin
  with three headline numbers (revenue / unresolved / staff corrections)
- **Vertical-scoped navigation (Toast)** — a restaurant operator never
  sees bar tab management; navigation scope set at the tenant's vertical
- **Slide-out detail panel (modern SaaS)** — click tenant/table/order
  to see detail without leaving the list; adopted for platform admin
  tenant health and store manager order view

**Interaction Patterns:**

- **Status progression as trust (Bolt + Jumia)** — every "in progress"
  state has at least 3 visible stages; users see forward movement, not
  a spinner
- **Full-screen modal for high-stakes actions (M-Pesa)** — payment
  initiation and order confirmation warrant full-screen treatment; partial
  modals feel insufficiently important for payment moments
- **Time-based ticket escalation (Toast)** — kitchen tickets age visually;
  color communicates urgency without requiring text to be read
- **Soft cross-sell during wait** — one non-intrusive suggestion during
  the STK Push wait; no button, awareness only; turns dead air into
  discovery
- **Split-variant quantity selector (joat_stores innovation)** — no
  existing product handles "×4 with 2 different modifiers" group ordering
  well; this is a genuine UX innovation opportunity

**Visual Patterns:**

- **Receipt card (M-Pesa)** — green accent, large transaction reference,
  screenshot-ready; the "proof of payment" visual language users already
  trust
- **Traffic-light status (operations universal)** — green/amber/red for
  tenant health, ticket age, alert severity; zero learning curve
- **WhatsApp-optimized card layout** — product cards with 1:1 image ratio,
  price prominent, name in 2 lines max; designed to look good as a
  WhatsApp screenshot, not just in a browser
- **"Last updated X seconds ago" timestamp (monitoring tools)** — data
  freshness signal without requiring calculation; borrowed from ops
  dashboards

### Anti-Patterns to Avoid

1. **Mandatory registration before checkout** — any account prompt before
   first purchase loses the majority of Kenyan first-time digital buyers;
   registration is a post-purchase optional offer, never a gate

2. **Silent loading states** — blank screen or invisible spinner during
   STK Push, page transition, or reconnect communicates failure on 3G;
   every loading state has a visible, branded skeleton or progress indicator

3. **Desktop-first admin shrunk to mobile** — horizontal data tables,
   small buttons, and sidebar navigation do not work on a Tecno A-series;
   mobile admin is designed mobile-first and expanded to desktop

4. **Multi-page checkout with data re-entry** — address page → payment
   page → confirm page is 3 pages too many; joat_stores checkout is a
   single scrollable screen with M-Pesa number pre-filled for returning
   customers

5. **Western trust signals** — SSL padlock icons and "256-bit encryption"
   badges mean nothing to Daniel; M-Pesa logo, merchant brand, and
   social proof are the actual trust signals in this market

6. **Technical error language** — "Error 502: Bad Gateway" creates panic;
   all errors in plain Kenyan English: "Your payment didn't go through —
   your money is safe. Try again or check your M-Pesa messages."

7. **Silent kitchen display failures** — any display that continues showing
   a frozen state without surfacing the outage is a kitchen liability;
   offline state must be impossible to miss

8. **Happy path-only design** — in a 3G market with M-Pesa timeouts, the
   error path IS the product for a meaningful percentage of sessions

### Design Inspiration Strategy

**Adopt directly:**
- M-Pesa receipt visual language → payment confirmation card design
- Bolt's status progression → STK Push waiting state + order status
- Shopify's "overview card" dashboard → Store Manager morning screen
- Toast's time-based ticket escalation → kitchen display priority system
- WhatsApp's "share location" → delivery address input

**Adapt for joat_stores context:**
- Jumia's order status tracking → 3-stage restaurant progression without
  Jumia's page weight or registration wall
- Shopify mobile admin → rebuilt for Tecno A-series at 3G; same
  information hierarchy, 10× lighter
- Toast's table grid → lightweight web component with larger touch targets
  and more aggressive offline state than Toast's native approach
- M-Pesa's STK Push silence → filled with designed waiting state
  (cycling reassurances, modal lock, merchant brand pulse) — something
  Safaricom itself doesn't provide

**Avoid entirely:**
- Jumia's mandatory registration gate
- Western SSL/security badge trust signals
- Desktop-first admin shrunk to mobile
- Silent loading and error states
- Multi-page checkout with separate address/payment/confirm pages
