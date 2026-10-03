/* Product-only detail drawer. */
(() => {
    const createProductDrawer = () => {
        const backdrop = document.createElement("div");
        backdrop.className = "product-drawer-backdrop";
        backdrop.hidden = true;

        const drawer = document.createElement("aside");
        drawer.className = "product-detail-drawer";
        drawer.hidden = true;
        drawer.setAttribute("aria-hidden", "true");
        drawer.innerHTML = `
            <header class="product-drawer__header">
                <div>
                    <h2 data-product-drawer-title>Sản phẩm</h2>
                    <p data-product-drawer-sub>Mã sản phẩm</p>
                </div>
                <button type="button" data-product-drawer-close aria-label="Đóng chi tiết">×</button>
            </header>
            <div class="product-drawer__body">
                <article class="product-drawer__product-card">
                    <div class="product-drawer__image" data-product-drawer-icon></div>
                    <div class="product-drawer__product-info">
                        <h3 data-product-drawer-name>Sản phẩm</h3>
                        <strong data-product-drawer-price>0 đ</strong>
                        <div><span data-product-drawer-status>Đang bán</span><small data-product-drawer-sold>Đã bán 0 sản phẩm</small></div>
                    </div>
                </article>

                <section class="product-drawer__section">
                    <h3>Thông tin đăng bán</h3>
                    <dl>
                        <dt>Shop</dt><dd data-product-drawer-shop>—</dd>
                        <dt>Danh mục</dt><dd data-product-drawer-category>—</dd>
                        <dt>Tồn kho</dt><dd data-product-drawer-stock>—</dd>
                        <dt>Đã bán</dt><dd data-product-drawer-total-sold>—</dd>
                        <dt>Đánh giá</dt><dd data-product-drawer-rating>4.8/5</dd>
                    </dl>
                </section>

                <section class="product-drawer__revenue">
                    <span>Doanh thu thuốc từ sản phẩm</span>
                    <strong data-product-drawer-revenue>0 đ</strong>
                </section>
            </div>
            <footer class="product-drawer__footer">
                <button type="button" data-product-drawer-hide>◉ Tạm ẩn sản phẩm</button>
                <button type="button" data-product-drawer-reject>⊗ Từ chối / Gỡ bỏ</button>
            </footer>
        `;

        document.body.append(backdrop, drawer);
        return { backdrop, drawer };
    };

    const formatCurrency = (value) => {
        const number = Number(String(value).replace(/\D/g, ""));
        return number ? new Intl.NumberFormat("vi-VN").format(number) + " đ" : "0 đ";
    };

    const initProductDrawer = () => {
        const rows = [...document.querySelectorAll(".product-table tbody tr")];
        if (rows.length === 0 || document.querySelector(".product-detail-drawer")) return;

        const { backdrop, drawer } = createProductDrawer();

        const close = () => {
            drawer.classList.remove("is-open");
            backdrop.classList.remove("is-open");
            document.body.classList.remove("has-product-drawer");
            window.setTimeout(() => {
                drawer.hidden = true;
                backdrop.hidden = true;
            }, 260);
        };

        const open = (row) => {
            const productCell = row.querySelector(".product-cell");
            const name = productCell?.querySelector("strong")?.textContent.trim() || "Sản phẩm";
            const id = productCell?.querySelector("small")?.textContent.trim() || "—";
            const shop = row.querySelector(".cell-primary")?.textContent.trim() || "—";
            const category = row.querySelector("td:nth-child(4)")?.textContent.trim() || "—";
            const price = row.querySelector(".product-price")?.textContent.trim() || "0 đ";
            const stock = row.querySelector("td:nth-child(6)")?.textContent.trim() || "0";
            const sold = row.querySelector("td:nth-child(7)")?.textContent.trim() || "0";
            const status = row.querySelector(".product-status")?.textContent.trim() || "—";
            const statusClass = row.querySelector(".product-status")?.className || "product-status product-status--selling";
            const icon = productCell?.querySelector(".product-icon")?.innerHTML || "";
            const numericPrice = Number(price.replace(/\D/g, ""));
            const numericSold = Number(sold.replace(/\D/g, ""));
            const revenue = formatCurrency(numericPrice * numericSold);

            drawer.querySelector("[data-product-drawer-title]").textContent = name;
            drawer.querySelector("[data-product-drawer-sub]").textContent = `${id} · Đăng lúc 20/09/2026 · 09:12`;
            drawer.querySelector("[data-product-drawer-icon]").innerHTML = icon;
            drawer.querySelector("[data-product-drawer-name]").textContent = name;
            drawer.querySelector("[data-product-drawer-price]").textContent = price;
            drawer.querySelector("[data-product-drawer-sold]").textContent = `Đã bán ${sold} sản phẩm`;

            const statusBadge = drawer.querySelector("[data-product-drawer-status]");
            statusBadge.textContent = status;
            statusBadge.className = statusClass;

            drawer.querySelector("[data-product-drawer-shop]").textContent = shop;
            drawer.querySelector("[data-product-drawer-category]").textContent = category;
            drawer.querySelector("[data-product-drawer-stock]").textContent = `${stock} sản phẩm`;
            drawer.querySelector("[data-product-drawer-total-sold]").textContent = `${sold} sản phẩm`;
            drawer.querySelector("[data-product-drawer-revenue]").textContent = revenue;

            drawer.dataset.productId = id;
            drawer.dataset.productName = name;
            drawer.hidden = false;
            backdrop.hidden = false;
            document.body.classList.add("has-product-drawer");
            requestAnimationFrame(() => {
                drawer.classList.add("is-open");
                backdrop.classList.add("is-open");
            });
        };

        drawer.querySelector("[data-product-drawer-close]").addEventListener("click", close);
        backdrop.addEventListener("click", close);
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && drawer.classList.contains("is-open")) close();
        });

        rows.forEach((row) => {
            row.classList.add("product-row-clickable");
            row.addEventListener("click", (event) => {
                if (event.target.closest("input, button, a, select")) return;
                open(row);
            });
            row.querySelector(".product-detail")?.addEventListener("click", (event) => {
                event.stopPropagation();
                open(row);
            });
        });
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initProductDrawer, { once: true });
    } else {
        initProductDrawer();
    }
})();
