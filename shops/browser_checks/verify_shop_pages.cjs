const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const base = 'http://127.0.0.1:8767';

(async () => {
    const browser = await chromium.launch({headless: true, channel: 'chrome'});
    const failures = [];
    try {
        const context = await browser.newContext({javaScriptEnabled: false, viewport: {width: 1440, height: 1000}});
        const page = await context.newPage();
        page.on('response', response => {
            if (response.url().startsWith(base) && response.status() >= 400 && !response.url().endsWith('/favicon.ico')) failures.push(`${response.status()} ${response.url()}`);
        });
        await page.goto(base + '/auth/login/?next=/shop/dashboard/');
        await page.locator('main [name=email]').fill('backendshop@example.test');
        await page.locator('main [name=password]').fill('BackendShop!9472');
        await page.locator('main').getByRole('button', {name: 'Đăng nhập', exact: true}).click();
        await page.waitForURL('**/shop/dashboard/');
        const pages = ['dashboard', 'offers', 'inventory', 'orders', 'order', 'fulfillment', 'revenue', 'questions', 'aftersales', 'build-requests', 'build-request-detail', 'proposal-builder', 'proposal-list', 'proposal'];
        for (const name of pages) {
            const response = await page.goto(`${base}/shop/${name}/`);
            assert.equal(response.status(), 200, name);
            assert.equal(await page.locator('#shop-main h1').count(), 1, name);
            const body = await page.locator('#shop-main').textContent();
            for (const forbidden of ['[[', 'Đang tải giao diện', 'BuildPro Demo', 'Sản phẩm riêng tư của shop khác']) assert(!body.includes(forbidden), `${name}: ${forbidden}`);
            assert.equal(await page.locator('script[id^="shop-templates-"]').count(), 0);
            assert.equal(await page.locator('template[data-shop-template]').count(), 0);
        }
        await page.goto(base + '/shop/offers/');
        await page.getByText('CPU của gian hàng kiểm thử', {exact: true}).waitFor();
        const edit = await page.locator('tr').filter({hasText: 'CPU của gian hàng kiểm thử'}).getByRole('link', {name: 'Sửa', exact: true}).getAttribute('href');
        await page.goto(base + edit);
        assert.equal(await page.locator('[name=product_name]').inputValue(), 'CPU của gian hàng kiểm thử');
        assert(await page.locator('[name=product_name]').isDisabled());
        await page.goto(base + '/shop/offers/?q=khong-co-san-pham');
        await page.getByRole('heading', {name: 'Không có sản phẩm', exact: true}).waitFor();
        await page.goto(base + '/shop/orders/');
        const detail = await page.getByRole('link', {name: 'Chi tiết', exact: true}).first().getAttribute('href');
        await page.goto(base + detail);
        await page.getByText('CPU của gian hàng kiểm thử', {exact: true}).waitFor();
        await page.goto(base + '/shop/questions/?answered=1');
        await page.getByText('Nội dung trả lời từ cơ sở dữ liệu', {exact: true}).waitFor();
        await page.goto(base + '/shop/revenue/?period=7');
        assert.equal(await page.locator('.shop-revenue-bar').count(), 7);
        await page.screenshot({path: 'artifacts/screenshots/backend-shop-revenue-no-js.png', fullPage: true, animations: 'disabled'});
        await page.goto(base + '/shop/aftersales/');
        const caseUrl = await page.getByRole('link', {name: 'Xem hồ sơ', exact: true}).getAttribute('href');
        await page.goto(base + caseUrl);
        await page.getByText('Lý do đổi trả kiểm thử', {exact: true}).waitFor();

        const mobile = await browser.newContext({storageState: await context.storageState(), viewport: {width: 390, height: 844}});
        const active = await mobile.newPage();
        active.on('pageerror', error => failures.push(error.message));
        for (const name of ['dashboard', 'offers', 'orders', 'questions', 'revenue']) {
            await active.goto(`${base}/shop/${name}/`);
            const dimensions = await active.evaluate(() => ({width: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth}));
            assert.equal(dimensions.width, dimensions.scroll, `Mobile overflow: ${name}`);
            await active.screenshot({path: `artifacts/screenshots/backend-shop-${name}-mobile.png`, fullPage: true, animations: 'disabled'});
        }
        await active.locator('[data-sidebar-toggle]').click();
        assert.match(await active.locator('#shop-shell').getAttribute('class'), /is-sidebar-open/);
        await active.keyboard.press('Escape');
        assert.doesNotMatch(await active.locator('#shop-shell').getAttribute('class'), /is-sidebar-open/);
        assert.deepEqual(await active.evaluate(() => Object.keys(localStorage)), []);
        await page.locator('#shop-user-btn').click();
        await page.getByRole('button', {name: 'Đăng xuất', exact: true}).click();
        await page.waitForURL('**/auth/login/');
        await page.goto(base + '/shop/dashboard/');
        await page.waitForURL(url => url.pathname === '/auth/login/' && url.searchParams.has('next'));
        const staffPage = await browser.newPage();
        staffPage.on('pageerror', error => failures.push(error.message));
        await staffPage.goto(base + '/staff/dashboard/');
        await staffPage.waitForURL(url => url.pathname === '/auth/login/' && url.searchParams.get('next') === '/staff/dashboard/');
        await staffPage.locator('main [name=email]').fill('backend-staff-check');
        await staffPage.locator('main [name=password]').fill('BackendStaff!9472');
        await staffPage.locator('main').getByRole('button', {name: 'Đăng nhập', exact: true}).click();
        await staffPage.waitForURL('**/staff/dashboard/');
        await staffPage.locator('.admin-link').click();
        await staffPage.getByRole('button', {name: 'Đăng xuất', exact: true}).click();
        await staffPage.waitForURL('**/auth/login/');
        await page.goto(base + '/auth/login/?mode=register');
        await page.locator('[name=full_name]').fill('Tài khoản đăng ký kiểm thử');
        await page.locator('[name=email]').fill('backendregister@example.test');
        await page.locator('[name=password1]').fill('BackendRegister!9472');
        await page.locator('[name=password2]').fill('BackendRegister!9472');
        await page.getByRole('button', {name: 'Đăng ký', exact: true}).click();
        await page.waitForURL('**/buyer/cart/');
        assert.deepEqual(failures, []);
        console.log('PASS: 14 Shop pages without JavaScript; shared auth registration, Shop/staff login and logout; database records, filters, details, responsive layouts and presentation interactions');
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exit(1); });
