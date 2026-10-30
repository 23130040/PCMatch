# PCMatch

Django marketplace with database-backed buyer sign-in, registration, home page,
product catalog and cart. Business operations belong to Python views and services.
Buyer and staff screens retain their HTML layouts without simulated transactions.
Shop screens render directly through Django templates and read existing database records.

## Run Locally (PowerShell)

The repaired environment uses Python 3.12. From the project directory:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

To create an environment on another machine, install Python 3.12 or later and run
`py -3.12 -m venv .venv` before installing dependencies. Virtual environments depend
on their base Python installation; do not copy a virtual environment between machines.
The previous environment is preserved in `.venv-backup-20261004`.

## Pages

- Buyer home (default entry): `/`
- Buyer: `/buyer/home/`
- Sign out: `/auth/logout/` (buyer), `/shop/logout/` (seller), `/staff/logout/` (admin)
- Shared sign-in (buyer): `/auth/login/`
- Shared registration: `/auth/login/?mode=register`
- Facebook sign-in starts at `/auth/facebook/` and returns to `/auth/facebook/callback/`
- Database cart: `/buyer/cart/`
- Checkout information: `/buyer/checkout/`
- Shop sign-in: `/shop/login/`
- Shop: `/shop/dashboard/`
- Admin sign-in: `/staff/login/`
- Staff UI: `/staff/dashboard/`
- Django admin: `/django-admin/`

Buyer, Shop and staff share one Django account store, but they are three
separate portals and each role only opens its own area:

- buyer area (`is_active_buyer`, roles `BUYER`/`CUSTOMER`) → `/buyer/...`
- shop area (`is_active_seller`, role `SELLER`) → `/shop/...`
- staff area (`is_staff_user`, `ADMIN` or `is_staff`) → `/staff/...`

Because of this, one session never leaks into another portal: after signing in
at `/staff/login/`, opening `/buyer/account/` redirects to
`/auth/login/?next=...` and opening `/shop/dashboard/` redirects to
`/shop/login/?next=...`, so each portal always asks for its own sign-in.

Sign-out is per portal: `auth_logout`, `shop_logout` and `staff_logout` end the
session and return to `/auth/login/`, `/shop/login/` and `/staff/login/`. They
accept `GET` as well as `POST` and the sign-out control is a plain link, because
Django rotates the CSRF token on every login: a POST form rendered before a
login elsewhere in the same browser would fail with “CSRF token from POST
incorrect”. Signing out only ends a session and has no other side effect.
`auth_logout` remains CSRF-protected for POST requests.

Shop has its own sign-in page (`templates/shop/login.html`, form in
`shops/forms.py`) that calls `shops.views.shop_login` and authenticates the same
`users.User` accounts used elsewhere — it is a separate screen, not a separate
account store. The admin
channel has its own sign-in page (`templates/staff/login.html`, form
`StaffLoginForm` in `users/forms.py`) served by `users.views.staff_login` at
`/staff/login/`. It offers a "Ghi nhớ đăng nhập" (remember-me) session and,
when `User.two_factor_enabled` is set, a second OTP step whose code is emailed
to the account (printed to the console in development and shown on the page
while `DEBUG` is on). Unknown accounts, wrong passwords and non-staff accounts
get distinct messages. Only staff/`ADMIN` accounts are
admitted and a successful sign-in redirects to `/staff/dashboard/`. `staff_required`
sends unauthorised visitors to `/staff/login/`, not the buyer form. Seller
password recovery lives at `/shop/forgot/` and `/shop/reset/<token>/`;
admin password recovery lives at `/staff/forgot/` and `/staff/reset/<token>/`.
Buyer screens continue to use
`templates/auth/login.html`; `/auth/register/` redirects to the shared
registration mode for old links. Registration creates an ordinary buyer account;
it does not grant staff access or create a Shop.

Buyer registration requires a six-digit email OTP. The code expires after three
minutes; users can request a replacement immediately, and five incorrect entries
require entering the email again. The account can sign in after successful
verification. OTP mail uses SMTP (it is not printed to the terminal), configured
through environment variables. The default SMTP settings are already configured
for `pcmatchcomputer@gmail.com`. For Gmail, use an App Password rather than the
regular account password; enter it in the current PowerShell session without
adding it to source control:

```powershell
$env:EMAIL_HOST_PASSWORD = "PASTE_GMAIL_APP_PASSWORD_HERE"
$env:SHOP_PUBLIC_BASE_URL = "http://127.0.0.1:8000"
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Do not commit the App Password or share it in chat. Both buyer OTP and seller
activation email use Gmail SMTP. Seller activation links use `SHOP_PUBLIC_BASE_URL`;
set it to the public HTTPS domain in deployed environments.

### Facebook sign-in configuration

Create a Meta app in Meta for Developers, add the Facebook Login product, and
allow the exact OAuth redirect URI provided by your HTTPS tunnel, ending in
`/auth/facebook/callback/` (for example,
`https://example-tunnel.ngrok-free.app/auth/facebook/callback/`). Facebook does
not accept the plain HTTP `127.0.0.1` callback for this OAuth flow. Use the
matching HTTPS URI and domain in production. The login requests `email` and
`public_profile`; accounts without an accessible email cannot sign in. In
development mode, add test users or app roles in Meta before testing.

For local development, copy `.env.example` to `.env` and fill in the Facebook
app ID, secret, callback URI, and allowed host there. Django loads `.env`
automatically when it starts. Keep `.env` private; it is ignored by Git and
must never be committed or shared.

Then start Django normally:

```powershell
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

The callback URI must exactly match a URI registered in Meta. A Cloudflare
Quick Tunnel hostname can change when a new tunnel is created; saving that
temporary hostname in `.env` does not make it permanent. To avoid updating Meta
after a tunnel restart, use a fixed hostname (such as a Cloudflare Named Tunnel
on a domain you control) and keep that same hostname in `.env` and Meta. Open
the application through the HTTPS tunnel before clicking Facebook; starting
at localhost and returning to a tunnel can lose the OAuth session/state.

The secret is used only by the server during the code exchange; it is not
rendered into the page or sent to the browser. Facebook identity links are
stored in `users.SocialAccount`. A first-time Facebook sign-in links to one
active, email-verified buyer account with the same email, or creates a buyer
account when no matching email exists. Seller/admin accounts cannot sign in
through the buyer portal. Canceling or denying Facebook permissions returns
the user to the login page without creating or changing an account.

## Seller Onboarding

Clicking “Đăng ký làm người bán” on `/shop/login/` starts a four-step wizard.
Account details remain in the session while the seller completes the wizard; the
seller account and Shop are created together only after valid legal documents are
submitted. Email verification happens in step 2 before the seller can continue:

- `/shop/register/` — step 1: seller account (unique username/email, strong password).
- `/shop/verify/email/` — step 2: enter the registered email and receive a
  one-time verification link by SMTP. Following the link continues to the shop
  profile. The link expires after 24 hours.
- `/shop/onboarding/profile/` — step 3: unique shop name, contact info, logo upload.
- `/shop/onboarding/legal/` — step 4: CMND/CCCD and business-licence uploads. Only
  after successful submission are the email-verified account and Shop saved; the
  shop is set to `PENDING`. Email and legal documents are required for approval;
  phone OTP is not part of this onboarding flow.
- `/shop/onboarding/pending/` — shows
  “Shop của bạn đang chờ xét duyệt bởi admin”.
- Legal documents accept PDF/JPG/PNG up to 10 MB and are checked against their
  file signatures. Staff review downloads use authenticated attachment routes;
  the development media route blocks direct public access to `shop_docs`.
  Configure production storage/web-server rules so `shop_docs` remains private.
- `/shop/dashboard/` — available only once `Shop.status == 'ACTIVE'`; otherwise the
  seller is redirected back to the onboarding step. `/shop/notifications/` lists the
  notifications, including “Chúc mừng, shop của bạn đã sẵn sàng!”.

### Admin shop approval

`/staff/shop/` (`shops.views.staff_shop_list`) lists the real shops with a search
box (name, owner, email, phone), status tabs and pagination. Each row posts one
CSRF-protected action:

- `/staff/shop/<id>/approve/` — `PENDING`/`SUSPENDED` → `ACTIVE`. `Shop.save()`
  creates the `SHOP_APPROVED` notification and emails the owner, so the seller can
  open `/shop/dashboard/`. Approval is blocked unless the seller verified email
  and phone and submitted both legal documents. The list provides staff-only
  document downloads. Approving twice does not send a second notification.
- `/staff/shop/<id>/suspend/` — sets `SUSPENDED` and records a `SHOP_SUSPENDED`
  notification; the seller is sent back to `/shop/onboarding/pending/`.

`/shop/onboarding/pending/` redirects to `/shop/dashboard/` once the shop is
approved, so a seller who was waiting lands on the shop home page after signing
in. Django admin approval still works and behaves identically.

Admin can also approve from Django admin (`/django-admin/`) with the “Phê duyệt
shop đã chọn” action; both approval interfaces enforce email/phone verification
and complete legal documents. `Shop.save()` detects the transition to `ACTIVE`,
records a `Notification` and emails the owner “Shop của bạn đã được phê duyệt
thành công”.
Adding a product requires sign-in;
an interrupted add resumes after successful sign-in or registration. Cart rows are
stored in `Cart`/`CartItem`, with one cart per user and one row per product.
The cart is rendered in Django HTML templates and works with JavaScript disabled.
Quantity changes and removal use CSRF-protected POST forms. Buyer and staff screens
without a backend implementation keep their layouts with disabled business actions.
The cart's checkout button opens a Django-rendered review of the signed-in user's
profile, default delivery address (or first saved address), and current cart prices
and quantities. This review does not create an order or initiate a payment.

## Frontend Integration

`PCMatch/pages.py` explicitly lists page templates. `PCMatch/urls.py` serves them
with named URLs and page metadata. The frontend context processor publishes URLs
using Django `reverse()` and the configured static asset prefix as JSON in the head.
The original banners, category tiles, chat layout and other presentation content
are written directly in HTML templates. Product lists and cart previews use real
database data. JavaScript is limited to presentation, such
as menus, carousels, password visibility, drawers and selecting table rows. No
script replaces the document body. Buyer and staff scripts do not intercept
business forms or simulate successful transactions.

Comparison uses “Thêm so sánh” buttons and the original selection tray. Python
stores up to four products from one category in the Django session. The comparison
script submits only comparison forms to that backend and displays HTML rendered
by Django, so selections persist through filters and pagination. Native POST forms
also work when JavaScript is disabled.

Shop layouts live directly in `templates/shop/*.html`. Shared backend partials
in `templates/includes/shop/` provide the base, header, sidebar, pagination,
product form/status, revenue chart and build-detail form. Django renders headings,
tables, forms and empty states before JavaScript runs; no HTML is published as
JSON templates or generated by a browser renderer. `shop-interface.js` only
controls the sidebar, password visibility and row selection.

`shops/views.py` reads the signed-in user's first owned Shop and scopes products,
orders, questions and returns to that shop. Order details and revenue show only
that shop's items, including when an order contains several shops. Revenue uses
delivered items and excludes shipping/platform fees. Filters use native GET
forms. Shop uses the shared Django authentication view;
a newly registered account still needs a linked Shop.
Actions without a backend implementation retain disabled HTML controls. Build
requests/proposals retain their layouts and forms without fabricated records.
The prototype states page and all Shop browser-storage/demo rendering modules
have been removed. Buyer, auth and admin layouts remain available.

Keep static presentation content in HTML when extending Buyer or staff screens.
Implement authentication, payments, orders, account updates, comments, reports and
recommendations in Python before enabling their business actions.

Use `{% url %}` for template links, `{% static %}` for template assets, and
native GET/POST forms for backend operations. Header and sidebar fragments
for staff pages are included by Django, without a separate network request.

When adding a page, register its template and include
`includes/frontend_config.html` inside its head. Set `data-page="{{ page_name }}"`
and `data-section="{{ page_section }}"` on its html element. When a page gets a real
backend view, replace its `TemplateView` route while retaining its URL name.

## Uploaded Images

Uploaded files use `MEDIA_ROOT = BASE_DIR / 'media'` and `MEDIA_URL = '/media/'`.
An ImageField's `upload_to` selects its subdirectory, such as
`media/product_thumbnail/` or `media/avatar/`. These files are excluded from Git.
Django serves `/media/` while `DEBUG` is enabled for local development.
Production must serve uploaded files through the web server or a storage backend.

Product image fields can be edited in Django admin. A custom upload form must use
`enctype="multipart/form-data"`, and its view must pass `request.FILES` to the form.
The buyer home lists newest and bestselling products from the database. The
catalog filters and sorts through `CatalogFilterForm`; the product detail and
comparison pages also render directly from Django data.

## Verify

```powershell
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe manage.py test
```

The tests cover page rendering, route coverage, internal links, static assets,
shared staff components, and redirects that preserve search parameters.

Optional Shop browser checks require Node.js with Playwright and Chrome. From
the project root, start `.venv\Scripts\python.exe shops/browser_checks/serve_shop_checks.py`
in one terminal, then run `node shops/browser_checks/verify_shop_pages.cjs` in
another. The server uses a copy at `artifacts/backend_shop_browser.sqlite3` with a test
account; it leaves the working database untouched. Checks cover all Shop layouts
with JavaScript disabled, database-backed lists
and details, native filters/authentication, mobile layouts and UI interactions.
The Django suite also checks isolation between shops and mixed-shop order totals.


Mô tả hiện tại
Tóm tắt đồ án PCMatch
PCMatch là một sàn thương mại điện tử (marketplace) chuyên linh kiện / máy tính, viết bằng Django 6.1.1, cơ sở dữ liệu SQLite, giao diện render phía server bằng Django Template + CSS/JS thuần. Hệ thống chia thành 3 cổng độc lập: Người mua (Buyer), Người bán (Shop), Quản trị (Staff/Admin).

1. Cấu trúc tổng thể
PCMatch/
├── PCMatch/          # Cấu hình project: settings, urls, pages, context processor
├── users/            # Tài khoản, phân quyền 3 cổng, địa chỉ, đăng nhập/OTP/quên mật khẩu
├── shops/            # Shop, onboarding người bán, dashboard shop, duyệt/tạm ngưng shop
├── products/         # Sản phẩm, danh mục, thương hiệu, thông số, hỏi đáp, so sánh
├── carts/            # Giỏ hàng
├── orders/           # Đơn hàng, chi tiết đơn, lịch sử trạng thái, đổi trả
├── payments/         # Thanh toán COD + tích hợp VNPay sandbox
├── notifications/    # Thông báo người dùng
├── interactions/     # Lưu lượt xem / tương tác sản phẩm
├── recommendations/  # Mô hình gợi ý sản phẩm (mới chỉ có schema)
├── analytics/        # Thống kê doanh thu, dashboard admin
├── templates/        # ~100 template: buyer / shop / admin / auth
├── static/           # CSS, JS, ảnh mẫu
├── media/            # File upload (ảnh sản phẩm, avatar, giấy tờ shop)
├── db.sqlite3
└── README.md         # Tài liệu khá chi tiết về luồng và cách chạy
Quy mô hiện tại: ~5.300 dòng Python, ~10.250 dòng template, ~8.900 dòng CSS, 99 route, 65 migration, 147 test case.

2. Ba cổng và phân quyền
Cổng	Đường dẫn	Vai trò
Buyer	/, /buyer/...	BUYER, CUSTOMER
Shop	/shop/...	SELLER
Staff/Admin	/staff/..., /django-admin/	ADMIN hoặc is_staff
Mỗi cổng có trang đăng nhập riêng. Session không dùng chung: đăng nhập staff không vào được khu buyer/shop và ngược lại. Staff có thêm OTP 2 lớp và luồng quên/đặt lại mật khẩu qua email.

3. Nghiệp vụ chính đã hoạt động
Người mua

Đăng ký/đăng nhập, quản lý nhiều địa chỉ, chọn địa chỉ mặc định.
Trang chủ, danh mục, tìm kiếm/lọc theo giá – hãng – shop – thông số kỹ thuật, sắp xếp, phân trang.
Chi tiết sản phẩm + hỏi đáp nhiều lượt giữa buyer và shop.
So sánh tối đa 4 sản phẩm cùng danh mục, lưu trong session, có tray so sánh.
Giỏ hàng DB: thêm/sửa/xóa, kiểm tra tồn kho; nếu chưa đăng nhập thì lưu sản phẩm chờ và tự thêm sau khi login.
Đặt hàng: chọn COD hoặc VNPay, tạo đơn trong transaction, trừ tồn kho, chống tạo trùng bằng checkout_token.
Xem danh sách/chi tiết đơn hàng, lịch sử trạng thái.
Người bán

Wizard đăng ký 4 bước: tài khoản → xác thực email → hồ sơ shop → giấy tờ pháp lý.
Shop ở trạng thái PENDING chờ admin duyệt; được duyệt thì nhận notification + email.
Dashboard shop: sản phẩm, tồn kho, đơn hàng, giao nhận, doanh thu, câu hỏi, hậu mãi.
CRUD sản phẩm, ẩn/hiện, cập nhật tồn kho, trả lời câu hỏi, duyệt/từ chối đổi trả.
Cập nhật trạng thái đơn theo đúng thứ tự: COMFIRMED → PROCESSING → SHIPPING → DELIVERED; đơn COD phải xác nhận đã thu tiền.
Quản trị

Duyệt/tạm ngưng shop.
Xác nhận đơn hàng, xem danh sách đơn, quản lý sản phẩm (ẩn/hiện), khóa/mở khóa người dùng.
Dashboard doanh thu 12 tháng + top sản phẩm + biểu đồ trạng thái đơn.
Thanh toán

COD: đơn PENDING → admin xác nhận → shop xử lý → giao → thu tiền → cập nhật PAID, tăng sold_quantity.
VNPay: tạo URL có chữ ký HMAC-SHA512, xử lý IPN/return, xác thực số tiền/mã giao dịch; thất bại thì hủy đơn và hoàn tồn kho.
4. Phần mới ở mức khung / chưa triển khai
recommendations/: chỉ có model (ProductRecommendation, FrequentItemset, AssociationRule) và đăng ký admin — chưa có thuật toán/giao diện gợi ý.
interactions/: có bảng lưu view/tương tác nhưng chưa được ghi nhận từ view sản phẩm.
analytics.SalesStatistic: có model nhưng chưa dùng để tổng hợp.
Buyer: builder, builds, consultation, requests, proposals, account, notifications, cases, help, chat chủ yếu là template tĩnh.
Shop: nhóm build request / proposal / báo giá mới có giao diện, chưa có backend xử lý riêng.
Staff: transaction, return, categories, review, complain, authorization, profile, password, policies, support... phần lớn vẫn là TemplateView.
5. Dữ liệu dev hiện có
8 user: 4 buyer, 3 seller, 1 admin
3 shop (đều ACTIVE)
3 danh mục, 2 thương hiệu, 23 sản phẩm
41 đơn hàng, 42 order item, 1 payment, 3 câu hỏi, 4 câu trả lời
3 giỏ hàng, 4 cart item, 7 notification, 2 địa chỉ
Lưu ý: db.sqlite3 đang có thay đổi chưa commit (git status báo M db.sqlite3).

6. Điểm cần lưu ý
Cấu hình còn ở mức dev: SECRET_KEY hard-code, DEBUG=True, ALLOWED_HOSTS=[], email dùng console backend, VNPay lấy credential từ biến môi trường (nếu chưa set thì chỉ dùng COD).
Trong PCMatch/urls.py đang khai báo trùng route staff/logout/ (dòng 51 và 61) — nên gộp lại.
Trạng thái COMFIRMED bị viết sai chính tả nhưng đã ăn vào DB/logic; nếu sửa phải làm migration + đổi đồng loạt.
Nên bổ sung gợi ý sản phẩm/ghi nhận interaction nếu mục tiêu đồ án là “recommendation system”.
README.md đã mô tả khá đầy đủ luồng và cách kiểm thử — nên đọc kèm khi báo cáo.
7. Cách chạy
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
Kiểm thử toàn bộ:

.venv\Scripts\python.exe manage.py test
Kết luận ngắn: Đây là đồ án Django khá hoàn chỉnh về luồng marketplace 3 vai trò: catalog → giỏ hàng → đặt hàng → duyệt đơn → shop giao hàng → thanh toán COD/VNPay, kèm onboarding và duyệt shop. Phần còn dang dở tập trung ở gợi ý sản phẩm, build PC/báo giá, chat, một số trang quản trị phụ.