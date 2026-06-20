"""
Management command: seed_demo

Creates realistic demo data for prototype presentations.
Idempotent — safe to run multiple times (skips existing records).

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --reset  # wipe existing demo data first
"""

import random
import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

User = get_user_model()

DEMO_RETAIL_SLUG = "joat-demo-shop"
DEMO_RESTAURANT_SLUG = "joat-demo-restaurant"
DEMO_BAR_SLUG = "joat-demo-bar"


class Command(BaseCommand):
    help = "Seed demo data for prototype presentations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo data before seeding",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        self._seed_plans()
        retail_store = self._seed_retail_store()
        restaurant_store = self._seed_restaurant_store()
        bar_store = self._seed_bar_store()
        self._seed_users(retail_store, restaurant_store, bar_store)
        self._seed_retail_products(retail_store)
        self._seed_restaurant_menu(restaurant_store)
        self._seed_bar_products(bar_store)
        self._seed_orders(retail_store)

        self.stdout.write(self.style.SUCCESS("\nDemo data seeded successfully!"))
        self.stdout.write("")
        self.stdout.write("  Platform admin : admin@joat.com / Demo@1234")
        self.stdout.write("  Retail owner   : retail@joat.com / Demo@1234")
        self.stdout.write("  Restaurant owner: restaurant@joat.com / Demo@1234")
        self.stdout.write("  Bar owner       : bar@joat.com / Demo@1234")
        self.stdout.write("")
        self.stdout.write(f"  Retail store slug : {DEMO_RETAIL_SLUG}")
        self.stdout.write(f"  Restaurant slug   : {DEMO_RESTAURANT_SLUG}")
        self.stdout.write(f"  Bar slug          : {DEMO_BAR_SLUG}")

    # -------------------------------------------------------------------------
    # Reset
    # -------------------------------------------------------------------------

    def _reset(self):
        from safedelete.models import HARD_DELETE

        from apps.store.models import Store

        for slug in [DEMO_RETAIL_SLUG, DEMO_RESTAURANT_SLUG, DEMO_BAR_SLUG]:
            for store in Store.all_objects.filter(slug=slug):
                store.delete(force_policy=HARD_DELETE)
        User.objects.filter(email__in=[
            "admin@joat.com", "retail@joat.com", "restaurant@joat.com", "bar@joat.com",
        ]).delete()
        self.stdout.write("Existing demo data cleared.")

    # -------------------------------------------------------------------------
    # Plans
    # -------------------------------------------------------------------------

    def _seed_plans(self):
        from apps.saas.models import BillingCycle, Plan

        plans = [
            dict(
                slug="free", name="Free", price_kes=Decimal("0"), billing_cycle=BillingCycle.MONTHLY,
                trial_days=0, max_products=20, max_orders_per_month=50, max_staff=1,
                has_analytics=False, has_qr_codes=False, has_ai_features=False,
                has_whatsapp=False, api_rate_limit=30,
            ),
            dict(
                slug="starter", name="Starter", price_kes=Decimal("1500"), billing_cycle=BillingCycle.MONTHLY,
                trial_days=14, max_products=100, max_orders_per_month=500, max_staff=3,
                has_analytics=True, has_qr_codes=True, has_ai_features=False,
                has_whatsapp=False, api_rate_limit=60,
            ),
            dict(
                slug="growth", name="Growth", price_kes=Decimal("4500"), billing_cycle=BillingCycle.MONTHLY,
                trial_days=14, max_products=500, max_orders_per_month=2000, max_staff=10,
                has_analytics=True, has_qr_codes=True, has_ai_features=True,
                has_whatsapp=True, api_rate_limit=120,
            ),
            dict(
                slug="pro", name="Pro", price_kes=Decimal("12000"), billing_cycle=BillingCycle.MONTHLY,
                trial_days=14, max_products=None, max_orders_per_month=None, max_staff=None,
                has_analytics=True, has_qr_codes=True, has_ai_features=True,
                has_whatsapp=True, api_rate_limit=300,
            ),
        ]
        for p in plans:
            Plan.objects.get_or_create(slug=p.pop("slug"), defaults=p)
        self.stdout.write("  Plans: done")

    # -------------------------------------------------------------------------
    # Stores
    # -------------------------------------------------------------------------

    def _seed_retail_store(self):
        from apps.saas.models import Plan, StoreSubscription
        from apps.store.models import Store, StoreSettings, StoreStatus, StoreTheme, TenantType

        store, created = Store.objects.get_or_create(
            slug=DEMO_RETAIL_SLUG,
            defaults=dict(
                name="JOAT Demo Shop",
                domain="demo-shop.joat.com",
                tenant_type=TenantType.RETAIL,
                status=StoreStatus.ACTIVE,
                currency="KES",
                payment_methods=["mpesa"],
            ),
        )
        if created:
            StoreSettings.objects.get_or_create(store=store, defaults=dict(
                low_stock_threshold=5,
            ))
            from apps.store.presets import apply_preset
            theme, _ = StoreTheme.objects.get_or_create(store=store)
            apply_preset(theme, "modern")
            growth_plan = Plan.objects.filter(slug="growth").first()
            if growth_plan:
                StoreSubscription.objects.get_or_create(
                    store=store,
                    defaults=dict(
                        plan=growth_plan,
                        status="active",
                        period_start=timezone.now().date(),
                        period_end=(timezone.now() + timedelta(days=30)).date(),
                    ),
                )
        self.stdout.write(f"  Retail store: {'created' if created else 'exists'}")
        return store

    def _seed_restaurant_store(self):
        from apps.saas.models import Plan, StoreSubscription
        from apps.store.models import Store, StoreSettings, StoreStatus, StoreTheme, TenantType

        store, created = Store.objects.get_or_create(
            slug=DEMO_RESTAURANT_SLUG,
            defaults=dict(
                name="JOAT Demo Restaurant",
                domain="demo-restaurant.joat.com",
                tenant_type=TenantType.RESTAURANT,
                status=StoreStatus.ACTIVE,
                currency="KES",
                payment_methods=["mpesa"],
            ),
        )
        if created:
            StoreSettings.objects.get_or_create(store=store, defaults=dict(
                low_stock_threshold=3,
            ))
            from apps.store.presets import apply_preset
            theme, _ = StoreTheme.objects.get_or_create(store=store)
            apply_preset(theme, "classic")
            pro_plan = Plan.objects.filter(slug="pro").first()
            if pro_plan:
                StoreSubscription.objects.get_or_create(
                    store=store,
                    defaults=dict(
                        plan=pro_plan,
                        status="active",
                        period_start=timezone.now().date(),
                        period_end=(timezone.now() + timedelta(days=30)).date(),
                    ),
                )
        self.stdout.write(f"  Restaurant store: {'created' if created else 'exists'}")
        return store

    def _seed_bar_store(self):
        from apps.saas.models import Plan, StoreSubscription
        from apps.store.models import Store, StoreSettings, StoreStatus, StoreTheme, TenantType

        store, created = Store.objects.get_or_create(
            slug=DEMO_BAR_SLUG,
            defaults=dict(
                name="JOAT Demo Bar",
                domain="demo-bar.joat.com",
                tenant_type=TenantType.BAR,
                status=StoreStatus.ACTIVE,
                currency="KES",
                payment_methods=["mpesa"],
            ),
        )
        if created:
            StoreSettings.objects.get_or_create(store=store, defaults=dict(
                low_stock_threshold=2,
            ))
            from apps.store.presets import apply_preset
            theme, _ = StoreTheme.objects.get_or_create(store=store)
            apply_preset(theme, "bold")
            starter_plan = Plan.objects.filter(slug="starter").first()
            if starter_plan:
                StoreSubscription.objects.get_or_create(
                    store=store,
                    defaults=dict(
                        plan=starter_plan,
                        status="active",
                        period_start=timezone.now().date(),
                        period_end=(timezone.now() + timedelta(days=30)).date(),
                    ),
                )
        self.stdout.write(f"  Bar store: {'created' if created else 'exists'}")
        return store

    # -------------------------------------------------------------------------
    # Users
    # -------------------------------------------------------------------------

    def _seed_users(self, retail_store, restaurant_store, bar_store):
        # Platform admin (no store)
        if not User.objects.filter(email="admin@joat.com", store=None).exists():
            u = User(
                email="admin@joat.com",
                role=User.Role.PLATFORM_ADMIN,
                first_name="Demo",
                last_name="Admin",
                is_staff=True,
                is_superuser=True,
            )
            u.set_password("Demo@1234")
            u.save()

        for email, name, role, store in [
            ("retail@joat.com", "Retail Owner", User.Role.STORE_OWNER, retail_store),
            ("restaurant@joat.com", "Restaurant Owner", User.Role.STORE_OWNER, restaurant_store),
            ("bar@joat.com", "Bar Owner", User.Role.STORE_OWNER, bar_store),
        ]:
            if not User.objects.filter(email=email, store=store).exists():
                first, last = name.split(" ", 1)
                u = User(email=email, role=role, store=store, first_name=first, last_name=last)
                u.set_password("Demo@1234")
                u.save()

        self.stdout.write("  Users: done")

    # -------------------------------------------------------------------------
    # Retail Products
    # -------------------------------------------------------------------------

    def _seed_retail_products(self, store):
        from apps.product.models import Category, Product, Variant

        categories = {
            "Electronics": [
                ("Samsung Galaxy A15", "4G smartphone with 128GB storage and 5000mAh battery", [
                    ("128GB / Black", {"Storage": "128GB", "Colour": "Black"}, Decimal("18500"), 25),
                    ("128GB / Blue", {"Storage": "128GB", "Colour": "Blue"}, Decimal("18500"), 18),
                    ("256GB / Black", {"Storage": "256GB", "Colour": "Black"}, Decimal("22000"), 10),
                ]),
                ("Oraimo Earbuds FreePods 3", "True wireless earbuds with 30hr playtime", [
                    ("White", {"Colour": "White"}, Decimal("2800"), 40),
                    ("Black", {"Colour": "Black"}, Decimal("2800"), 35),
                ]),
                ("Anker 20W USB-C Charger", "Fast charging wall adapter with PowerIQ 3.0", [
                    ("Default", {}, Decimal("1200"), 60),
                ]),
            ],
            "Clothing": [
                ("Classic Polo Shirt", "100% cotton polo shirt, machine washable", [
                    ("S / White", {"Size": "S", "Colour": "White"}, Decimal("850"), 20),
                    ("M / White", {"Size": "M", "Colour": "White"}, Decimal("850"), 30),
                    ("L / White", {"Size": "L", "Colour": "White"}, Decimal("850"), 25),
                    ("M / Navy", {"Size": "M", "Colour": "Navy"}, Decimal("850"), 22),
                    ("L / Navy", {"Size": "L", "Colour": "Navy"}, Decimal("850"), 18),
                ]),
                ("Cargo Trousers", "Slim-fit cargo trousers with 6 pockets", [
                    ("30 / Khaki", {"Waist": "30", "Colour": "Khaki"}, Decimal("1800"), 15),
                    ("32 / Khaki", {"Waist": "32", "Colour": "Khaki"}, Decimal("1800"), 20),
                    ("34 / Khaki", {"Waist": "34", "Colour": "Khaki"}, Decimal("1800"), 12),
                    ("32 / Black", {"Waist": "32", "Colour": "Black"}, Decimal("1800"), 18),
                ]),
            ],
            "Home & Kitchen": [
                ("Stainless Steel Water Bottle 1L", "Double-wall insulated, keeps cold 24hr / hot 12hr", [
                    ("Black", {"Colour": "Black"}, Decimal("950"), 50),
                    ("Silver", {"Colour": "Silver"}, Decimal("950"), 45),
                    ("Red", {"Colour": "Red"}, Decimal("950"), 30),
                ]),
                ("Non-stick Frying Pan 28cm", "Granite-coated with glass lid, induction compatible", [
                    ("Default", {}, Decimal("2400"), 20),
                ]),
            ],
            "Beauty & Personal Care": [
                ("Nivea Body Lotion 400ml", "Express hydration lotion for fast absorption", [
                    ("Default", {}, Decimal("580"), 80),
                ]),
                ("Dove Shampoo 400ml", "Intensive repair for damaged hair", [
                    ("Default", {}, Decimal("650"), 60),
                ]),
            ],
        }

        for cat_name, products in categories.items():
            cat, _ = Category.objects.get_or_create(store=store, name=cat_name)
            for prod_name, description, variants in products:
                prod, created = Product.objects.get_or_create(
                    store=store,
                    name=prod_name,
                    defaults=dict(
                        category=cat,
                        description=description,
                        attribute_names=list({k for v in variants for k in v[1].keys()}),
                        is_available=True,
                    ),
                )
                if created:
                    for label, attrs, price, stock in variants:
                        Variant.objects.create(
                            store=store,
                            product=prod,
                            attribute_values=attrs,
                            price=price,
                            inventory_count=stock,
                            sku=f"DEMO-{str(prod.id)[:8].upper()}-{label[:4].upper().replace(' ', '')}",
                        )

        self.stdout.write("  Retail products: done")

    # -------------------------------------------------------------------------
    # Restaurant Menu
    # -------------------------------------------------------------------------

    def _seed_restaurant_menu(self, store):
        from apps.product.models import Category, Product, Variant

        menu = {
            "Starters": [
                ("Chicken Wings (6 pcs)", "Crispy fried wings with choice of sauce", Decimal("650")),
                ("Samosa Plate (4 pcs)", "Beef or vegetable samosas with chutney", Decimal("350")),
                ("Soup of the Day", "Chef's daily soup served with bread roll", Decimal("450")),
            ],
            "Mains": [
                ("Nyama Choma (500g)", "Grilled goat ribs served with ugali and kachumbari", Decimal("1200")),
                ("Grilled Tilapia", "Whole tilapia grilled over charcoal, served with chips", Decimal("950")),
                ("Chicken Biryani", "Fragrant basmati rice with spiced chicken thighs", Decimal("850")),
                ("Beef Burger", "Quarter-pound patty with lettuce, tomato, cheese", Decimal("750")),
                ("Vegetable Stir Fry", "Seasonal vegetables in garlic sauce, served with rice", Decimal("550")),
            ],
            "Pizzas": [
                ("Margherita (12\")", "Tomato base, mozzarella, fresh basil", Decimal("950")),
                ("BBQ Chicken (12\")", "BBQ sauce, grilled chicken, red onion, coriander", Decimal("1150")),
                ("Pepperoni (12\")", "Tomato base, mozzarella, spicy pepperoni", Decimal("1100")),
            ],
            "Drinks": [
                ("Freshly Squeezed Juice", "Orange, mango, or passion fruit", Decimal("300")),
                ("Soda 350ml", "Coca-Cola, Fanta, Sprite, or Stoney", Decimal("150")),
                ("Bottled Water 500ml", "Still or sparkling", Decimal("100")),
                ("Masala Chai", "Spiced Kenyan tea with milk", Decimal("120")),
            ],
            "Desserts": [
                ("Chocolate Lava Cake", "Warm chocolate cake with vanilla ice cream", Decimal("550")),
                ("Fruit Salad", "Seasonal fresh fruit with honey and mint", Decimal("350")),
            ],
        }

        for cat_name, items in menu.items():
            cat, _ = Category.objects.get_or_create(store=store, name=cat_name)
            for name, description, price in items:
                prod, created = Product.objects.get_or_create(
                    store=store, name=name,
                    defaults=dict(category=cat, description=description, is_available=True),
                )
                if created:
                    Variant.objects.create(
                        store=store, product=prod,
                        attribute_values={}, price=price, inventory_count=999,
                        sku=f"REST-{str(prod.id)[:8].upper()}",
                    )

        self.stdout.write("  Restaurant menu: done")

    # -------------------------------------------------------------------------
    # Bar Products
    # -------------------------------------------------------------------------

    def _seed_bar_products(self, store):
        from apps.product.models import Category, Product, Variant

        bar_menu = {
            "Beers": [
                ("Tusker Lager 500ml", "Kenya's favourite lager", Decimal("320")),
                ("Guinness 500ml", "Classic Irish stout", Decimal("380")),
                ("White Cap 330ml", "Crisp light lager", Decimal("280")),
                ("Heineken 330ml", "Premium imported lager", Decimal("420")),
            ],
            "Spirits": [
                ("Johnnie Walker Red (shot)", "Scotch whisky", Decimal("450")),
                ("Jameson (shot)", "Irish whiskey", Decimal("480")),
                ("Smirnoff Vodka (shot)", "Premium vodka", Decimal("350")),
                ("Bacardi Rum (shot)", "White rum", Decimal("380")),
            ],
            "Wine": [
                ("House Red (glass)", "Medium-bodied red wine", Decimal("650")),
                ("House White (glass)", "Crisp dry white wine", Decimal("650")),
                ("Sparkling (glass)", "Brut sparkling wine", Decimal("800")),
            ],
            "Cocktails": [
                ("Mojito", "Rum, mint, lime, soda water", Decimal("950")),
                ("Dawa", "Vodka, honey, lime — Kenya's classic cocktail", Decimal("900")),
                ("Gin & Tonic", "Premium gin with tonic and garnish", Decimal("850")),
            ],
            "Non-Alcoholic": [
                ("Fresh Juice", "Orange, mango, or passion", Decimal("300")),
                ("Soda 350ml", "Coke, Sprite, Fanta", Decimal("150")),
                ("Red Bull 250ml", "Energy drink", Decimal("450")),
            ],
        }

        for cat_name, items in bar_menu.items():
            cat, _ = Category.objects.get_or_create(store=store, name=cat_name)
            for name, description, price in items:
                prod, created = Product.objects.get_or_create(
                    store=store, name=name,
                    defaults=dict(category=cat, description=description, is_available=True),
                )
                if created:
                    Variant.objects.create(
                        store=store, product=prod,
                        attribute_values={}, price=price, inventory_count=999,
                        sku=f"BAR-{str(prod.id)[:8].upper()}",
                    )

        self.stdout.write("  Bar products: done")

    # -------------------------------------------------------------------------
    # Orders (retail — shows history in analytics)
    # -------------------------------------------------------------------------

    def _seed_orders(self, store):
        from apps.order.models import Order, OrderStatus
        from apps.product.models import Variant

        if Order.objects.filter(store=store).count() >= 20:
            self.stdout.write("  Orders: already seeded")
            return

        variants = list(Variant.objects.filter(store=store).select_related("product")[:20])
        if not variants:
            return

        phones = ["0712345678", "0723456789", "0734567890", "0745678901", "0756789012"]
        names = ["John Kamau", "Faith Wanjiku", "Brian Otieno", "Mary Njeri", "Peter Mwangi"]
        statuses = [
            OrderStatus.COMPLETED, OrderStatus.COMPLETED, OrderStatus.COMPLETED,
            OrderStatus.FULFILLED, OrderStatus.CONFIRMED, OrderStatus.CANCELLED,
        ]

        for i in range(25):
            num_items = random.randint(1, 3)
            selected = random.sample(variants, min(num_items, len(variants)))
            items_snapshot = []
            total = Decimal("0")
            for v in selected:
                qty = random.randint(1, 4)
                line_total = v.price * qty
                total += line_total
                items_snapshot.append({
                    "product_id": str(v.product.id),
                    "variant_id": str(v.id),
                    "product_name": v.product.name,
                    "attribute_values": v.attribute_values,
                    "quantity": qty,
                    "unit_price": str(v.price),
                    "line_total": str(line_total),
                })

            days_ago = random.randint(0, 90)
            order = Order.objects.create(
                store=store,
                customer_phone=random.choice(phones),
                customer_name=random.choice(names),
                items_snapshot=items_snapshot,
                total_amount=total,
                status=random.choice(statuses),
            )
            # Backdate for realistic analytics — bypasses auto_now_add via update()
            Order.objects.filter(pk=order.pk).update(
                created_at=timezone.now() - timedelta(days=days_ago)
            )

        self.stdout.write("  Orders: done (25 demo orders)")
