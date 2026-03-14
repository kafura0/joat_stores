"""
Bar domain views.

Stories 5.1-5.5.

Endpoints:
  POST   /api/v1/bar/tabs/                         — open a new tab (5.1)
  GET    /api/v1/bar/tabs/{id}/                    — tab detail (5.1)
  POST   /api/v1/bar/tabs/{id}/rounds/             — add a round (5.2)
  DELETE /api/v1/bar/tabs/{id}/items/{item_id}/   — staff removes item with audit (5.2)
  POST   /api/v1/bar/tabs/{id}/request-bill/      — OPEN → BILL_REQUESTED (5.5)
  POST   /api/v1/bar/tabs/{id}/split/             — initiate split payment (5.5)
  GET/POST /api/v1/bar/happy-hours/               — manage happy hours (5.4)
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bar.models import (
    AgeRestrictionLog,
    HappyHour,
    InvalidTabTransition,
    Tab,
    TabItem,
    TabRound,
    TabShare,
    get_active_happy_hour,
)
from apps.bar.serializers import (
    AddRoundSerializer,
    HappyHourSerializer,
    SplitTabSerializer,
    TabDetailSerializer,
    TabSerializer,
    TabShareSerializer,
)
from apps.payment.services import initiate_payment


class TabListView(APIView):
    """
    GET  /api/v1/bar/tabs/  — list open tabs for this store
    POST /api/v1/bar/tabs/  — open a new tab
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        tabs = Tab.objects.filter(store=request.store).order_by("-opened_at")
        return Response(TabSerializer(tabs, many=True).data)

    def post(self, request):
        customer_name = request.data.get("customer_name", "").strip()
        with transaction.atomic():
            tab = Tab.objects.create(
                store=request.store,
                customer=request.user if request.user.is_authenticated else None,
                customer_name=customer_name,
                status=Tab.STATUS_OPEN,
            )
        return Response(TabSerializer(tab).data, status=201)


class TabDetailView(APIView):
    """GET /api/v1/bar/tabs/{tab_id}/ — full tab detail with rounds + items."""

    permission_classes = [IsAuthenticated]

    def get(self, request, tab_id):
        try:
            tab = Tab.objects.get(id=tab_id, store=request.store)
        except Tab.DoesNotExist:
            return Response(status=404)
        return Response(TabDetailSerializer(tab).data)


class AddRoundView(APIView):
    """
    POST /api/v1/bar/tabs/{tab_id}/rounds/

    Adds a new round of items to an OPEN tab.
    - Resolves MenuItem by ID, validates it exists and belongs to store
    - Applies happy hour discount if active
    - Enforces age restriction acknowledgement (AgeRestrictionLog)
    - Returns 422 TAB_NOT_OPEN if tab is not OPEN
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, tab_id):
        try:
            tab = Tab.objects.get(id=tab_id, store=request.store)
        except Tab.DoesNotExist:
            return Response(status=404)

        if tab.status != Tab.STATUS_OPEN:
            return Response(
                {"code": "TAB_NOT_OPEN", "detail": "Tab must be OPEN to add rounds."},
                status=422,
            )

        serializer = AddRoundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        customer_phone = data.get("customer_phone", "")

        # Resolve MenuItems
        from apps.restaurant.models import MenuItem

        item_defs = []
        for item_data in data["items"]:
            menu_item_id = item_data["menu_item_id"]
            quantity = int(item_data.get("quantity", 1))
            acknowledge_age = item_data.get("acknowledge_age_restriction", False)

            try:
                menu_item = MenuItem.objects.get(id=menu_item_id, store=request.store)
            except MenuItem.DoesNotExist:
                return Response(
                    {"code": "MENU_ITEM_NOT_FOUND", "menu_item_id": str(menu_item_id)},
                    status=404,
                )

            # Age restriction check (Story 5.3)
            if getattr(menu_item, "is_age_restricted", False):
                existing_log = AgeRestrictionLog.objects.filter(
                    tab=tab,
                    customer=request.user if request.user.is_authenticated else None,
                ).first()

                if not existing_log and not acknowledge_age:
                    return Response(
                        {
                            "code": "AGE_RESTRICTION_ACKNOWLEDGEMENT_REQUIRED",
                            "menu_item_id": str(menu_item_id),
                            "detail": (
                                "This item is age-restricted. You must be 18+ to order. "
                                "Re-submit with acknowledge_age_restriction=true."
                            ),
                        },
                        status=403,
                    )

            item_defs.append(
                {"menu_item": menu_item, "quantity": quantity, "acknowledge_age": acknowledge_age}
            )

        # Get active happy hour once for the round
        active_hh = get_active_happy_hour(request.store)

        with transaction.atomic():
            # Create AgeRestrictionLog entries for age-restricted items if not already logged
            for item_def in item_defs:
                menu_item = item_def["menu_item"]
                if getattr(menu_item, "is_age_restricted", False):
                    log_filter = {"tab": tab}
                    if request.user.is_authenticated:
                        log_filter["customer"] = request.user
                    existing = AgeRestrictionLog.objects.filter(**log_filter).exists()
                    if not existing:
                        AgeRestrictionLog.objects.create(
                            store=request.store,
                            tab=tab,
                            customer=request.user if request.user.is_authenticated else None,
                            customer_phone=customer_phone,
                        )

            # Determine next round number
            last_round = tab.rounds.order_by("-round_number").first()
            round_number = (last_round.round_number + 1) if last_round else 1

            tab_round = TabRound.objects.create(
                store=request.store,
                tab=tab,
                round_number=round_number,
            )

            created_items = []
            for item_def in item_defs:
                menu_item = item_def["menu_item"]
                quantity = item_def["quantity"]

                # Price snapshot (Story 5.4)
                base_price = menu_item.price
                if active_hh:
                    unit_price = active_hh.apply_discount(base_price)
                    is_happy_hour = True
                else:
                    unit_price = base_price
                    is_happy_hour = False

                tab_item = TabItem.objects.create(
                    store=request.store,
                    tab=tab,
                    round=tab_round,
                    menu_item=menu_item,
                    name=menu_item.name,
                    unit_price=unit_price,
                    quantity=quantity,
                    is_happy_hour=is_happy_hour,
                )
                created_items.append(tab_item)

        return Response(
            {
                "round": round_number,
                "happy_hour_active": active_hh is not None,
                "items_added": len(created_items),
            },
            status=201,
        )


class RemoveTabItemView(APIView):
    """
    DELETE /api/v1/bar/tabs/{tab_id}/items/{item_id}/

    Staff removes an item from the tab. Creates an audit trail.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, tab_id, item_id):
        try:
            tab = Tab.objects.get(id=tab_id, store=request.store)
        except Tab.DoesNotExist:
            return Response(status=404)

        if tab.status != Tab.STATUS_OPEN:
            return Response(
                {"code": "TAB_NOT_OPEN", "detail": "Items can only be removed from OPEN tabs."},
                status=422,
            )

        try:
            item = TabItem.objects.get(id=item_id, tab=tab)
        except TabItem.DoesNotExist:
            return Response(status=404)

        if item.removed_at:
            return Response(
                {"code": "ITEM_ALREADY_REMOVED", "detail": "Item has already been removed."},
                status=409,
            )

        staff_name = request.user.get_full_name() or str(request.user)
        item.removed_at = timezone.now()
        item.removed_by = request.user
        item.removed_by_name = staff_name
        item.save(update_fields=["removed_at", "removed_by", "removed_by_name"])

        return Response(
            {
                "removed": True,
                "removed_by": staff_name,
                "at": item.removed_at.strftime("%H:%M"),
            }
        )


class RequestBillView(APIView):
    """
    POST /api/v1/bar/tabs/{tab_id}/request-bill/

    Transitions tab from OPEN → BILL_REQUESTED.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, tab_id):
        try:
            tab = Tab.objects.get(id=tab_id, store=request.store)
        except Tab.DoesNotExist:
            return Response(status=404)

        try:
            tab.transition(Tab.STATUS_BILL_REQUESTED)
        except InvalidTabTransition as exc:
            return Response(
                {
                    "code": "INVALID_TAB_TRANSITION",
                    "detail": str(exc),
                },
                status=422,
            )

        return Response(
            {
                "status": tab.status,
                "total_amount": str(tab.total_amount),
            }
        )


class SplitTabView(APIView):
    """
    POST /api/v1/bar/tabs/{tab_id}/split/

    Creates TabShare records and initiates an STK Push for each payer.
    Tab must be in BILL_REQUESTED status.

    Request body:
    {
        "shares": [
            {"payer_phone": "+254...", "amount": "500.00"},
            {"payer_phone": "+254...", "percentage": "50"}
        ]
    }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, tab_id):
        try:
            tab = Tab.objects.get(id=tab_id, store=request.store)
        except Tab.DoesNotExist:
            return Response(status=404)

        if tab.status != Tab.STATUS_BILL_REQUESTED:
            return Response(
                {
                    "code": "INVALID_TAB_STATUS",
                    "detail": "Tab must be in BILL_REQUESTED status to split.",
                },
                status=422,
            )

        serializer = SplitTabSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        shares_data = serializer.validated_data["shares"]

        total = tab.total_amount
        results = []

        with transaction.atomic():
            for share_data in shares_data:
                payer_phone = share_data["payer_phone"]

                if "amount" in share_data:
                    amount = Decimal(str(share_data["amount"]))
                    percentage = None
                else:
                    pct = Decimal(str(share_data["percentage"]))
                    amount = (total * pct / Decimal("100")).quantize(Decimal("0.01"))
                    percentage = pct

                tab_share = TabShare.objects.create(
                    store=request.store,
                    tab=tab,
                    payer_phone=payer_phone,
                    amount=amount,
                    percentage=percentage,
                )

                # Initiate STK Push per payer
                reference = f"tab-share-{tab_share.id}"
                try:
                    from apps.payment.exceptions import (
                        InvalidPhoneNumberError,
                        StkPushInitiationError,
                        StkPushRateLimitedError,
                    )

                    txn = initiate_payment(
                        store=request.store,
                        method="mpesa",
                        amount=amount,
                        phone=payer_phone,
                        reference=reference,
                    )
                    results.append(
                        {
                            "share_id": str(tab_share.id),
                            "payer_phone": payer_phone,
                            "amount": str(amount),
                            "transaction_id": str(txn.id),
                            "status": "stk_push_sent",
                        }
                    )
                except (InvalidPhoneNumberError, StkPushRateLimitedError, StkPushInitiationError) as exc:
                    tab_share.status = TabShare.STATUS_FAILED
                    tab_share.save(update_fields=["status"])
                    results.append(
                        {
                            "share_id": str(tab_share.id),
                            "payer_phone": payer_phone,
                            "amount": str(amount),
                            "status": "stk_push_failed",
                            "error": str(exc),
                        }
                    )

        return Response({"shares": results}, status=202)


class HappyHourListView(APIView):
    """
    GET  /api/v1/bar/happy-hours/ — list happy hours for this store
    POST /api/v1/bar/happy-hours/ — create a happy hour window
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        hours = HappyHour.objects.filter(store=request.store)
        return Response(HappyHourSerializer(hours, many=True).data)

    def post(self, request):
        serializer = HappyHourSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hh = HappyHour.objects.create(store=request.store, **serializer.validated_data)
        return Response(HappyHourSerializer(hh).data, status=201)
