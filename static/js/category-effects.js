/* Category editor drawer and delete confirmation. */
(() => {
    const createCategoryDrawer = () => {
        const backdrop = document.createElement("div");
        backdrop.className = "category-drawer-backdrop";
        backdrop.hidden = true;

        const drawer = document.createElement("aside");
        drawer.className = "category-edit-drawer";
        drawer.hidden = true;
        drawer.setAttribute("aria-hidden", "true");
        drawer.innerHTML = `
            <header class="category-edit-drawer__header">
                <div>
                    <h2>Chỉnh sửa danh mục</h2>
                    <p>Cập nhật <span data-category-code>DM-01</span></p>
                </div>
                <button type="button" data-category-close aria-label="Đóng">×</button>
            </header>
            <form class="category-edit-drawer__form" data-category-form>
                <div class="category-edit-drawer__body">
                    <label><span>Tên danh mục</span><input type="text" name="name" required></label>
                    <label><span>Đường dẫn (slug)</span><input type="text" name="slug" required></label>
                    <label><span>Danh mục cấp cha</span><select name="parent"><option>Danh mục cấp 1</option><option>Vi điều khiển &amp; Board mạch</option><option>Cảm biến</option><option>Linh kiện thụ động</option></select></label>
                    <fieldset class="category-status-switch">
                        <legend>Trạng thái</legend>
                        <label><input type="radio" name="status" value="active"><span>Đang hoạt động</span></label>
                        <label><input type="radio" name="status" value="hidden"><span>Tạm ẩn</span></label>
                    </fieldset>
                    <div class="category-edit-drawer__notice">
                        <span>Danh mục đang hoạt động sẽ hiển thị công khai cho người mua và cho phép shop đăng bán sản phẩm mới. Danh mục tạm ẩn vẫn giữ sản phẩm cũ nhưng không nhận sản phẩm mới.</span>
                    </div>
                </div>
                <footer>
                    <button type="button" class="is-secondary" data-category-cancel>Hủy</button>
                    <button type="submit" class="is-primary">▣ Lưu thay đổi</button>
                </footer>
            </form>
        `;

        const confirmBackdrop = document.createElement("div");
        confirmBackdrop.className = "category-confirm-backdrop";
        confirmBackdrop.hidden = true;
        confirmBackdrop.innerHTML = `
            <div class="category-confirm" role="alertdialog" aria-modal="true" aria-labelledby="category-delete-title">
                <span class="category-confirm__icon">!</span>
                <h2 id="category-delete-title">Xóa danh mục?</h2>
                <p>Bạn có chắc chắn muốn xóa <strong data-category-delete-name></strong>? Hành động này không thể hoàn tác.</p>
                <div><button type="button" data-category-delete-cancel>Hủy</button><button type="button" class="is-danger" data-category-delete-confirm>Xóa danh mục</button></div>
            </div>`;

        document.body.append(backdrop, drawer, confirmBackdrop);
        return { backdrop, drawer, confirmBackdrop };
    };

    const slugify = (value) => value
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .replace(/đ/g, "d")
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");

    const initCategoryEffects = () => {
        const rows = [...document.querySelectorAll(".category-table tbody tr")];
        if (rows.length === 0 || document.querySelector(".category-edit-drawer")) return;
        const { backdrop, drawer, confirmBackdrop } = createCategoryDrawer();
        const form = drawer.querySelector("[data-category-form]");
        let activeRow = null;
        let pendingDeleteRow = null;

        const closeDrawer = () => {
            drawer.classList.remove("is-open");
            backdrop.classList.remove("is-open");
            document.body.classList.remove("has-category-drawer");
            window.setTimeout(() => {
                drawer.hidden = true;
                backdrop.hidden = true;
            }, 260);
        };

        const openDrawer = (row) => {
            activeRow = row;
            const name = row.querySelector(".category-name")?.textContent.trim() || "";
            const slug = row.querySelector("td:nth-child(2) small")?.textContent.trim().replace(/^\//, "") || "";
            const parent = row.querySelector("td:nth-child(3)")?.textContent.trim() || "Danh mục cấp 1";
            const status = row.querySelector(".category-status")?.textContent.trim() || "Đang hoạt động";
            const code = String(rows.indexOf(row) + 1).padStart(2, "0");

            drawer.querySelector("[data-category-code]").textContent = `DM-${code}`;
            form.elements.name.value = name;
            form.elements.slug.value = slug;
            form.elements.parent.value = parent;
            form.querySelector(`input[name="status"][value="${status === "Tạm ẩn" ? "hidden" : "active"}"]`).checked = true;
            drawer.hidden = false;
            backdrop.hidden = false;
            document.body.classList.add("has-category-drawer");
            requestAnimationFrame(() => {
                drawer.classList.add("is-open");
                backdrop.classList.add("is-open");
            });
        };

        const closeConfirm = () => {
            confirmBackdrop.classList.remove("is-open");
            window.setTimeout(() => {
                confirmBackdrop.hidden = true;
                pendingDeleteRow = null;
            }, 180);
        };

        const openConfirm = (row) => {
            pendingDeleteRow = row;
            confirmBackdrop.querySelector("[data-category-delete-name]").textContent = row.querySelector(".category-name")?.textContent.trim() || "danh mục này";
            confirmBackdrop.hidden = false;
            requestAnimationFrame(() => confirmBackdrop.classList.add("is-open"));
        };

        form.addEventListener("submit", (event) => {
            event.preventDefault();
            if (!activeRow) return;
            const name = form.elements.name.value.trim();
            const slug = form.elements.slug.value.trim().replace(/^\//, "");
            const parent = form.elements.parent.value;
            const isActive = form.elements.status.value === "active";

            activeRow.querySelector(".category-name").textContent = name;
            activeRow.querySelector("td:nth-child(2) small").textContent = `/${slug}`;
            activeRow.querySelector("td:nth-child(3)").textContent = parent;
            const status = activeRow.querySelector(".category-status");
            status.textContent = isActive ? "Đang hoạt động" : "Tạm ẩn";
            status.className = `category-status ${isActive ? "category-status--active" : "category-status--hidden"}`;
            closeDrawer();
        });

        drawer.querySelectorAll("[data-category-close], [data-category-cancel]").forEach((button) => button.addEventListener("click", closeDrawer));
        backdrop.addEventListener("click", closeDrawer);
        confirmBackdrop.querySelector("[data-category-delete-cancel]").addEventListener("click", closeConfirm);
        confirmBackdrop.addEventListener("click", (event) => {
            if (event.target === confirmBackdrop) closeConfirm();
        });
        confirmBackdrop.querySelector("[data-category-delete-confirm]").addEventListener("click", () => {
            if (!pendingDeleteRow) return;
            pendingDeleteRow.remove();
            const result = document.querySelector(".category-result strong");
            if (result) result.textContent = String(Math.max(0, Number(result.textContent) - 1));
            closeConfirm();
        });
        document.addEventListener("keydown", (event) => {
            if (event.key !== "Escape") return;
            if (confirmBackdrop.classList.contains("is-open")) closeConfirm();
            else if (drawer.classList.contains("is-open")) closeDrawer();
        });

        rows.forEach((row) => {
            row.classList.add("category-row-clickable");
            row.addEventListener("click", (event) => {
                if (event.target.closest("input, button, a, select")) return;
                openDrawer(row);
            });
            const buttons = row.querySelectorAll(".category-actions button");
            buttons[0]?.addEventListener("click", (event) => {
                event.stopPropagation();
                openDrawer(row);
            });
            buttons[1]?.addEventListener("click", (event) => {
                event.stopPropagation();
                openConfirm(row);
            });
        });
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initCategoryEffects, { once: true });
    } else {
        initCategoryEffects();
    }
})();
