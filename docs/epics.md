---
project: joat_stores
status: draft
inputDocuments:
  - CLAUDE.md
epicsCount: 2
storiesCount: 8
---

# Epics — joat_stores: Store Branding & Product Images

## Extracted Requirements

### Functional Requirements

FR1: Platform admin can upload a store logo when creating a new store
FR2: Store logo is stored in Supabase storage (or local media in dev)
FR3: Store logo URL is included in the onboarding email sent to store owner
FR4: Store owner can upload/change their store logo from the admin dashboard
FR5: Store owner can add product images when creating/editing products
FR6: Product images are stored and accessible via API
FR7: Store logo appears in the storefront header/branding
FR8: Product images display in the storefront product catalog

### Non-Functional Requirements

NFR1: Image uploads must be max 5MB, accepted formats: jpg, png, webp
NFR2: Images must be resized to optimal dimensions (logo: 512x512, product: 1024x1024)
NFR3: Image uploads must use pre-signed URLs for direct browser-to-storage upload
NFR4: Existing products already have an images relationship (ProductImage model exists)
NFR5: StoreTheme model already exists for branding tokens

### Architecture Notes

- `Store` model has `name`, `slug`, `domain` — no logo field yet
- `StoreSettings` model exists with `logo_url` field — use this for store logo
- `ProductImage` model exists with `image`, `alt_text`, `position`, `is_default` fields
- Supabase storage configured in production for media
- Local `MEDIA_ROOT` in dev
- Backend `BrandingSerializer` already serves `logo_url` from `StoreSettings`

---

## Epic 1: Store Logo Management

### Story 1.1: Add store logo upload to platform admin store creation

**As a** platform admin
**I want to** upload a store logo when creating a new store
**So that** the store owner's branding is set up from day one

**Acceptance Criteria:**
- [ ] Store creation form includes a logo upload field (drag & drop or click to browse)
- [ ] Accepted formats: jpg, png, webp, max 5MB
- [ ] Logo is uploaded to storage on form submit (not before)
- [ ] On success, logo URL is saved to `StoreSettings.logo_url`
- [ ] Onboarding email includes the store logo inline
- [ ] Onboarding dialog shows the uploaded logo preview

**Technical Notes:**
- Add `logo` field to `StoreProvisionSerializer` (optional, base64 or URL)
- After store creation, update `StoreSettings.logo_url`
- Pass logo URL to `send_store_onboarding_email` task
- Frontend: add file upload component to Create Store dialog

---

### Story 1.2: Store owner can upload/change store logo

**As a** store owner
**I want to** upload or change my store logo
**So that** my storefront reflects my brand

**Acceptance Criteria:**
- [ ] Settings page has a logo upload section with current logo preview
- [ ] Click to upload or drag-and-drop a new logo
- [ ] Accepted formats: jpg, png, webp, max 5MB
- [ ] Upload triggers immediate preview update
- [ ] Save button persists the logo to backend
- [ ] Logo appears in the storefront header after save

**Technical Notes:**
- PATCH `/api/v1/store/themes/` already accepts theme updates
- Add `logo_url` field to `ThemeSerializer` or create dedicated endpoint
- Frontend: Settings page gets logo upload component

---

### Story 1.3: Store logo in onboarding email

**As a** platform admin
**I want** the onboarding email to include the store logo
**So that** the store owner sees their branding from the first touchpoint

**Acceptance Criteria:**
- [ ] Onboarding HTML email renders the store logo at the top
- [ ] Logo is displayed at 200x200px with rounded corners
- [ ] If no logo uploaded, fallback to JOAT Stores generic logo
- [ ] Logo URL is passed to the Celery task
- [ ] Email template renders logo from URL (not inline attachment)

**Technical Notes:**
- Update `send_store_onboarding_email` task to accept `logo_url` parameter
- Update HTML email template with `<img>` tag for logo
- Logo hosted on Supabase storage — use direct URL in email

---

## Epic 2: Product Image Management

### Story 2.1: Product creation includes image upload

**As a** store owner
**I want to** upload images when creating a product
**So that** customers can see what they're buying

**Acceptance Criteria:**
- [ ] Product create/edit form has an image upload section
- [ ] Can upload up to 5 images per product
- [ ] First image is automatically marked as default
- [ ] Images can be reordered via drag-and-drop
- [ ] Each image has an alt text field (auto-populated from product name)
- [ ] Accepted formats: jpg, png, webp, max 5MB each
- [ ] Images upload in parallel (not blocking form submission)

**Technical Notes:**
- `ProductImage` model already exists with required fields
- Use existing `POST /api/v1/store/products/{id}/images/` endpoint (or create if missing)
- Frontend: add ImageUpload component to product form
- Use pre-signed URLs for direct upload to Supabase storage

---

### Story 2.2: Product images display in product list and detail

**As a** store owner
**I want to** see product images in my product list
**So that** I can quickly identify products

**Acceptance Criteria:**
- [ ] Product list shows thumbnail of default image (48x48px)
- [ ] Product detail page shows all images in a gallery/carousel
- [ ] Images load lazily for performance
- [ ] Missing images show a placeholder icon

**Technical Notes:**
- Product API already returns `images` array with `image` URL
- Frontend DataTable component needs optional image column
- Product detail page needs image gallery component

---

### Story 2.3: Product images in storefront

**As a** customer
**I want to** see product images when browsing the store
**So that** I can make informed purchase decisions

**Acceptance Criteria:**
- [ ] Storefront product cards show the default product image
- [ ] Product detail page shows image gallery with zoom on tap
- [ ] Images are responsive and optimized for mobile
- [ ] WebP format served when browser supports it

**Technical Notes:**
- Storefront already fetches products via API (images included)
- Update storefront product card component to render images
- Add image optimization middleware or use Supabase image transformations

---

### Story 2.4: Product image CRUD API

**As a** developer
**I want** proper API endpoints for product image management
**So that** the frontend can upload, update, and delete images

**Acceptance Criteria:**
- [ ] `POST /api/v1/store/products/{id}/images/` — upload image (multipart)
- [ ] `PATCH /api/v1/store/products/{id}/images/{img_id}/` — update alt_text, position, is_default
- [ ] `DELETE /api/v1/store/products/{id}/images/{img_id}/` — delete image
- [ ] `GET /api/v1/store/products/{id}/images/` — list images
- [ ] All endpoints are tenant-scoped (store_id enforced)
- [ ] Max 5 images per product enforced at API level

**Technical Notes:**
- Check if these endpoints exist in `apps/product/urls.py`
- If not, create `ProductImageViewSet` in `apps/product/views.py`
- Use `MultiPartParser` for file uploads
- Delete image from storage when record is deleted

---

## Requirements Coverage Map

| FR | Story |
|----|-------|
| FR1: Platform admin upload logo | 1.1 |
| FR2: Logo stored in Supabase | 1.1, 1.2 |
| FR3: Logo in onboarding email | 1.3 |
| FR4: Store owner upload logo | 1.2 |
| FR5: Product images on create | 2.1 |
| FR6: Product images API | 2.4 |
| FR7: Logo in storefront | 1.2 (implicit) |
| FR8: Product images in storefront | 2.3 |
