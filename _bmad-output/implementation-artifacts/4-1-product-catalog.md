# Story 4.1 — Product Catalog (Categories, Variants, Inventory, Images)

## Status: done

## Models (`apps/product/models.py`)

| Model | Key fields |
|-------|-----------|
| `Category` | name, description, parent (self FK), position |
| `Product` | category FK, name, description, attribute_names (JSON list), is_available |
| `Variant` | product FK, attribute_values (JSON dict), price, inventory_count, is_available, sku |
| `ProductImage` | product FK, variant FK (nullable), ImageField, alt_text, position, is_default |

`StoreSettings.low_stock_threshold` added (migration 0005, default=5).

## Low-Stock Alert
`Variant.save()` fires `transaction.on_commit` → `send_low_stock_alert.apply_async()` to
`inventory.alerts` queue when `inventory_count <= threshold`. Never blocks the save path.

## Product QR Code
`GET /api/v1/store/products/{id}/qr/` → PNG download.
Token format: `{store_id}.{product_id}.{hmac_sha256}` — same signing scheme as restaurant table QR (FR22).
`GET /p/scan/?token=<token>` (AllowAny) verifies HMAC + returns product_id; returns 403 on invalid token.

## Image Upload & WebP Compression
`POST /api/v1/store/product-images/` accepts multipart image.
View compresses to WebP ≤ 800KB via Pillow (quality iterates 85→75→65→50→35→20).
Only the WebP file is saved; original upload is never written to disk as a separate file.

## API Endpoints (mounted at `/api/v1/store/`)
- `GET/POST /categories/`
- `GET/PUT/PATCH/DELETE /categories/{id}/`
- `GET/POST /products/` (list: available only, paginated)
- `GET /products/{id}/` (detail: full variant + image nesting)
- `GET /products/{id}/qr/` (PNG download)
- `GET/POST /variants/`
- `GET/POST /product-images/` (POST: WebP compression)

## Dependencies added
- `qrcode[pil]==8.*` added to `requirements/base.txt`

## Tests (`apps/product/tests/test_catalog.py`)
10 tests covering all ACs. Key assertions:
- Independent inventory_count per variant
- Product detail includes variants with attribute_values + price
- List paginated + excludes unavailable
- Low-stock dispatch called (mocked) when inventory ≤ threshold
- QR returns PNG; invalid token → 403; valid token → 200 + product_id

## Storefront UI ACs (frontend work)
The following ACs require Next.js storefront implementation:
- Pill/chip variant selector + colour swatches for "Colour"/"Color" attribute
- First in-stock variant as default selection
- Image gallery updates on variant switch (client-side)
- Price update on variant switch (pre-loaded in payload — no extra API call)
- Disabled state for out-of-stock variant chips
- Hide single-option attributes from selector
These rely on the `/products/{id}/` API response which pre-loads all variant prices.
