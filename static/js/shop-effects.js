/* Shop-only interactions: fee dropdown, table filtering and detail drawer. */
(() => {
    const productSamples = {
        "Linh Kiện Sao Việt": [["Kit Arduino Uno R3 kèm 30 cảm biến", "1.290.000 đ · Đã bán 312"], ["Bộ dây jumper đực - cái 40 sợi", "35.000 đ · Đã bán 845"]],
        "Linh Kiện TechZone": [["Module Relay 5V 4 kênh", "145.000 đ · Đã bán 210"], ["ESP32 DevKit V1", "320.000 đ · Đã bán 96"]],
        "Module & Cảm Biến 24H": [["Cảm biến DHT22", "85.000 đ · Đã bán 428"], ["Cảm biến siêu âm HC-SR04", "45.000 đ · Đã bán 243"]],
        "Chip Bán Dẫn Á Châu": [["MOSFET IRF540N", "12.000 đ · Đã bán 720"], ["Tụ nhôm 1000uF 35V", "3.500 đ · Đã bán 1.120"]],
        "PCB Express Việt": [["PCB chấm vuông 7×9cm", "78.000 đ · Đã bán 612"], ["PCB điện tử 20×30cm", "42.000 đ · Đã bán 286"]],
        "Nguồn & Adapter Pro": [["Adapter 12V 5A", "130.000 đ · Đã bán 54"], ["Nguồn ATX 500W", "690.000 đ · Đã bán 37"]],
        "Board Mạch Thông Minh": [["Board STM32F103C8T6", "65.000 đ · Đã bán 380"], ["Mạch nạp ST-Link V2", "48.000 đ · Đã bán 510"]],
        "IoT Maker Store": [["Raspberry Pi 4 Model B 4GB", "1.650.000 đ · Đã bán 210"], ["Vỏ nhôm kèm quạt tản nhiệt", "140.000 đ · Đã bán 390"]]
    };

    const createDrawer = () => {
        const backdrop = document.createElement("div");
        backdrop.className = "shop-drawer-backdrop";
        backdrop.hidden = true;
        const drawer = document.createElement("aside");
        drawer.className = "shop-detail-drawer";
        drawer.hidden = true;
        drawer.setAttribute("aria-hidden", "true");
        drawer.innerHTML = `
            <header class="shop-drawer__header">
                <div><h2 data-drawer-name>Linh Kiện Sao Việt</h2><p data-drawer-sub>SH-100241 · Tham gia 12/03/2024</p></div>
                <button type="button" data-drawer-close aria-label="Đóng">×</button>
            </header>
            <div class="shop-drawer__body">
                <div class="shop-drawer__summary"><div><span>Doanh thu luỹ kế</span><strong data-drawer-revenue>1,42 tỷ đ</strong></div><div><span data-drawer-status>Đang hoạt động</span><span data-drawer-fee>Đã thanh toán</span></div></div>
                <section><h3>Thông tin shop</h3><dl><dt>Chủ shop</dt><dd data-drawer-owner>Trần Văn Hùng</dd><dt>Điện thoại</dt><dd data-drawer-phone>0903 118 224</dd><dt>Email</dt><dd data-drawer-email>hung@linhkienviet.vn</dd><dt>Ngành hàng</dt><dd data-drawer-category>Vi điều khiển &amp; Board mạch</dd><dt>Địa chỉ</dt><dd data-drawer-address>128 Nguyễn Trãi, Thanh Xuân, Hà Nội</dd></dl></section>
                <section><h3>Phí sàn &amp; chất lượng</h3><dl><dt>Tổng sản phẩm</dt><dd data-drawer-products>128 sản phẩm</dd><dt>Điểm đánh giá</dt><dd data-drawer-rating>4.8/5</dd><dt>Phí còn nợ</dt><dd data-drawer-debt>Không có</dd></dl></section>
                <section><h3 data-drawer-product-title>Sản phẩm tiêu biểu (2)</h3><div class="shop-drawer__products"><div data-drawer-item="0"><strong></strong><span></span></div><div data-drawer-item="1"><strong></strong><span></span></div></div></section>
            </div>
            <footer><button type="button">⊘ Tạm ngưng shop</button></footer>`;
        document.body.append(backdrop, drawer);
        return { backdrop, drawer };
    };

    const initFeeFilter = () => {
        const trigger = document.querySelector(".table-filters .filter-button");
        const table = document.querySelector("table");
        if (!trigger || !table || trigger.dataset.feeReady) return;
        trigger.dataset.feeReady = "1";
        const wrapper = document.createElement("div");
        wrapper.className = "fee-filter";
        trigger.parentNode.insertBefore(wrapper, trigger);
        wrapper.appendChild(trigger);
        const label = trigger.querySelector("span");
        const menu = document.createElement("div");
        menu.className = "fee-filter__menu";
        menu.innerHTML = ["Tất cả tình trạng phí", "Đã thanh toán phí", "Đang nợ phí", "Quá hạn phí"].map((item) => `<button type="button" data-fee-option="${item}">${item}</button>`).join("");
        wrapper.appendChild(menu);
        const close = () => wrapper.classList.remove("is-open");
        trigger.addEventListener("click", (event) => { event.stopPropagation(); wrapper.classList.toggle("is-open"); });
        menu.addEventListener("click", (event) => {
            const option = event.target.closest("[data-fee-option]");
            if (!option) return;
            label.textContent = option.dataset.feeOption;
            table.dataset.activeFee = option.dataset.feeOption;
            wrapper.dispatchEvent(new CustomEvent("shop-filter-change", { bubbles: true }));
            close();
        });
        document.addEventListener("click", (event) => { if (!wrapper.contains(event.target)) close(); });
    };

    const initFiltering = () => {
        const table = document.querySelector("table");
        const search = document.querySelector(".table-search input");
        const count = document.querySelector(".result-count strong");
        if (!table || table.dataset.shopFilterReady) return;
        table.dataset.shopFilterReady = "1";
        const tabs = [...document.querySelectorAll(".filter-tabs button")];
        const apply = () => {
            const query = search?.value.trim().toLowerCase() || "";
            const tab = tabs
                .find((item) => item.classList.contains("is-active"))
                ?.textContent.replace(/\d+$/, "")
                .trim() || "";
            const fee = table.dataset.activeFee || "Tất cả tình trạng phí";
            let visible = 0;
            table.querySelectorAll("tbody tr").forEach((row) => {
                const text = row.textContent.toLowerCase();
                const status = row.querySelector(".status")?.textContent.trim() || "";
                const feeText = row.querySelector(".badge")?.textContent.trim() || "";
                const matchSearch = !query || text.includes(query);
                const matchTab = tab === "Tất cả" || status.includes(tab);
                const matchFee = fee.startsWith("Tất cả") || (fee.startsWith("Đã") ? feeText.includes("Đã thanh toán") : feeText.includes("Đang nợ phí") || feeText.includes("Quá hạn"));
                const match = matchSearch && matchTab && matchFee;
                row.hidden = !match;
                if (match) visible += 1;
            });
            if (count) count.textContent = String(visible);
        };
        search?.addEventListener("input", apply);
        tabs.forEach((tab) => tab.addEventListener("click", () => {
            tabs.forEach((item) => item.classList.remove("is-active"));
            tab.classList.add("is-active");
            apply();
        }));
        document.querySelector(".table-filters")?.addEventListener("shop-filter-change", apply);
        apply();
    };

    const initDrawer = () => {
        const { backdrop, drawer } = createDrawer();
        const close = () => {
            drawer.classList.remove("is-open");
            backdrop.classList.remove("is-open");
            document.body.classList.remove("has-shop-drawer");
            window.setTimeout(() => { drawer.hidden = true; backdrop.hidden = true; }, 260);
        };
        const open = (row) => {
            const name = row.querySelector(".shop-name")?.textContent.trim() || "Shop";
            const id = row.querySelector("td:nth-child(2) small")?.textContent.trim() || "—";
            const owner = row.querySelector("td:nth-child(3) strong")?.textContent.trim() || "—";
            const phone = row.querySelector("td:nth-child(3) small")?.textContent.trim() || "—";
            const category = row.querySelector("td:nth-child(4)")?.textContent.trim() || "—";
            const products = row.querySelector(".products")?.textContent.trim() || "0";
            const revenue = row.querySelector(".revenue")?.textContent.trim() || "—";
            const status = row.querySelector(".status")?.textContent.trim() || "—";
            const fee = row.querySelector(".badge")?.textContent.trim() || "—";
            const debt = row.querySelector(".debt-amount")?.textContent.trim() || "Không có";
            const samples = productSamples[name] || [["Sản phẩm tiêu biểu", "Cập nhật gần đây"], ["Sản phẩm nổi bật", "Đang cung cấp"]];
            drawer.querySelector("[data-drawer-name]").textContent = name;
            drawer.querySelector("[data-drawer-sub]").textContent = `${id} · Tham gia 12/03/2024`;
            drawer.querySelector("[data-drawer-revenue]").textContent = revenue;
            drawer.querySelector("[data-drawer-status]").textContent = status;
            drawer.querySelector("[data-drawer-fee]").textContent = fee;
            drawer.querySelector("[data-drawer-owner]").textContent = owner;
            drawer.querySelector("[data-drawer-phone]").textContent = phone;
            drawer.querySelector("[data-drawer-email]").textContent = owner.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replaceAll(" ", "") + "@shop.vn";
            drawer.querySelector("[data-drawer-category]").textContent = category;
            drawer.querySelector("[data-drawer-products]").textContent = `${products} sản phẩm`;
            drawer.querySelector("[data-drawer-rating]").textContent = "4.8/5";
            drawer.querySelector("[data-drawer-debt]").textContent = debt;
            samples.forEach((sample, index) => {
                const item = drawer.querySelector(`[data-drawer-item="${index}"]`);
                item.querySelector("strong").textContent = sample[0];
                item.querySelector("span").textContent = sample[1];
            });
            drawer.hidden = false;
            backdrop.hidden = false;
            document.body.classList.add("has-shop-drawer");
            requestAnimationFrame(() => { drawer.classList.add("is-open"); backdrop.classList.add("is-open"); });
        };
        drawer.querySelector("[data-drawer-close]").addEventListener("click", close);
        backdrop.addEventListener("click", close);
        document.addEventListener("keydown", (event) => { if (event.key === "Escape" && drawer.classList.contains("is-open")) close(); });
        document.querySelectorAll(".table-scroll tbody tr").forEach((row) => {
            row.classList.add("shop-row-clickable");
            row.addEventListener("click", (event) => {
                if (event.target.closest("input, button, a")) return;
                open(row);
            });
            row.querySelector(".detail-button")?.addEventListener("click", (event) => { event.stopPropagation(); open(row); });
        });
    };

    const init = () => { initFeeFilter(); initFiltering(); initDrawer(); };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
})();
