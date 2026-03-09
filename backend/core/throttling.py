"""
Plan-based rate throttling.

StorePlanRateThrottle reads the rate limit from the store's subscription
plan (request.store.subscription.plan.api_rate_limit) and enforces it
per-store. Default: 100 req/min when no plan is assigned.

Implementation: Story 1.5
"""

from rest_framework.throttling import SimpleRateThrottle


class StorePlanRateThrottle(SimpleRateThrottle):
    """
    Throttle API requests per store based on subscription plan.

    Rate is dynamic — read from plan.api_rate_limit on each request.
    Falls back to 100/min if no store, no subscription, or no plan.
    """

    scope = "store_plan"

    def get_cache_key(self, request, view):
        store = getattr(request, "store", None)
        if store is None:
            # Platform-level requests (admin, auth) — no store throttle
            return None
        return f"throttle_store_{store.pk}"

    def get_rate(self):
        # Rate is set dynamically in allow_request, not from settings
        return None

    def allow_request(self, request, view):
        store = getattr(request, "store", None)
        if store is None:
            return True  # platform endpoints not throttled per-store

        # Read rate from plan
        rate_limit = 100  # default
        try:
            plan = store.subscription.plan
            if plan and plan.api_rate_limit:
                rate_limit = plan.api_rate_limit
        except Exception:
            pass  # no subscription or plan — use default

        self.rate = f"{rate_limit}/min"
        self.num_requests, self.duration = self.parse_rate(self.rate)

        return super().allow_request(request, view)
