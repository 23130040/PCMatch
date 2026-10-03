/* Policy page: fee editor and platform policy editor. */
(() => {
    const createDrawerShell = (className) => {
        const backdrop = document.createElement("div");
        backdrop.className = "policy-drawer-backdrop";
        backdrop.hidden = true;
        const drawer = document.createElement("aside");
        drawer.className = `policy-edit-drawer ${className}`;
        drawer.hidden = true;
        drawer.setAttribute("aria-hidden", "true");
        document.body.append(backdrop, drawer);
        return { backdrop, drawer };
    };

    const createFeeDrawer = () => {
        const shell = createDrawerShell("policy-fee-drawer");
        shell.drawer.innerHTML = `
            <header><div><h2 data-fee-title>Biểu phí</h2><p><span data-fee-code>PB-01</span> · Cập nhật gần nhất theo kỳ 09/2026</p></div><button type="button" data-drawer-close aria-label="Đóng">×</button></header>
            <form data-fee-form>
                <div class="policy-edit-drawer__body">
                    <div class="policy-fee-form__grid">
                        <label><span>Hoa hồng sàn (%)</span><input type="number" name="commission" min="0" step="0.1" required></label>
                        <label><span>Phí thanh toán (%)</span><input type="number" name="payment" min="0" step="0.1" required></label>
                    </div>
                    <label><span>Phí dịch vụ mỗi đơn (đ)</span><input type="number" name="service" min="0" step="100" required></label>
                    <div class="policy-fee-toggle-row">
                        <div><strong>Áp dụng biểu phí này</strong><span>Tắt để tạm dừng thu phí với nhóm ngành hàng này</span></div>
                        <label class="policy-switch"><input type="checkbox" name="enabled" checked><span></span></label>
                    </div>
                    <div class="policy-edit-drawer__notice">Khi lưu, biểu phí mới sẽ được áp dụng từ chủ shop thuộc nhóm ngành hàng này trong mục “Phí &amp; Chính sách” và áp dụng cho các đơn phát sinh sau thời điểm cập nhật.</div>
                </div>
                <footer><button type="button" class="is-secondary" data-drawer-cancel>Hủy</button><button type="submit" class="is-primary">▣ Lưu biểu phí</button></footer>
            </form>`;
        return shell;
    };

    const createPolicyDrawer = () => {
        const shell = createDrawerShell("policy-content-drawer");
        shell.drawer.innerHTML = `
            <header><div><h2>Chỉnh sửa chính sách</h2><p><span data-policy-code>CS-01</span> · Hiển thị cho chủ shop và người mua</p></div><button type="button" data-drawer-close aria-label="Đóng">×</button></header>
            <form data-policy-form>
                <div class="policy-edit-drawer__body">
                    <label><span>Tiêu đề chính sách</span><input type="text" name="title" required></label>
                    <label class="policy-content-field"><span>Nội dung chính sách</span><textarea name="content" maxlength="500" required></textarea><small><span data-character-count>0</span>/500 ký tự</small></label>
                </div>
                <footer><button type="button" class="is-secondary" data-drawer-cancel>Hủy</button><button type="submit" class="is-primary">▣ Lưu chính sách</button></footer>
            </form>`;
        return shell;
    };

    const initPolicyEffects = () => {
        const feeRows = [...document.querySelectorAll(".policy-fee-table tbody tr")];
        const policyCards = [...document.querySelectorAll(".policy-card")];
        if (feeRows.length === 0 || document.querySelector(".policy-edit-drawer")) return;

        const feeShell = createFeeDrawer();
        const policyShell = createPolicyDrawer();
        const feeForm = feeShell.drawer.querySelector("[data-fee-form]");
        const policyForm = policyShell.drawer.querySelector("[data-policy-form]");
        const content = policyForm.elements.content;
        const charCount = policyShell.drawer.querySelector("[data-character-count]");
        let activeFeeRow = null;
        let activePolicyCard = null;

        const close = (shell) => {
            shell.drawer.classList.remove("is-open");
            shell.backdrop.classList.remove("is-open");
            document.body.classList.remove("has-policy-drawer");
            window.setTimeout(() => {
                shell.drawer.hidden = true;
                shell.backdrop.hidden = true;
            }, 260);
        };

        const show = (shell) => {
            shell.drawer.hidden = false;
            shell.backdrop.hidden = false;
            document.body.classList.add("has-policy-drawer");
            requestAnimationFrame(() => {
                shell.drawer.classList.add("is-open");
                shell.backdrop.classList.add("is-open");
            });
        };

        const openFee = (row) => {
            activeFeeRow = row;
            const cells = row.querySelectorAll("td");
            const name = row.querySelector(".fee-group-name")?.textContent.trim() || "Biểu phí";
            const code = cells[1]?.querySelector("small")?.textContent.trim() || "PB-01";
            feeShell.drawer.querySelector("[data-fee-title]").textContent = `Biểu phí: ${name}`;
            feeShell.drawer.querySelector("[data-fee-code]").textContent = code;
            feeForm.elements.commission.value = (cells[2]?.textContent.match(/[\d.]+/) || ["0"])[0];
            feeForm.elements.payment.value = (cells[3]?.textContent.match(/[\d.]+/) || ["0"])[0];
            feeForm.elements.service.value = (cells[4]?.textContent.match(/[\d.]+/) || ["0"])[0];
            feeForm.elements.enabled.checked = row.querySelector(".fee-status")?.textContent.trim() === "Đang áp dụng";
            show(feeShell);
        };

        const openPolicy = (card) => {
            activePolicyCard = card;
            const title = card.querySelector("h3")?.textContent.trim() || "Chính sách";
            const description = card.querySelector(":scope > p")?.textContent.trim() || "";
            const code = card.querySelector(".policy-card__body small")?.textContent.trim() || "CS-01";
            policyShell.drawer.querySelector("[data-policy-code]").textContent = code;
            policyForm.elements.title.value = title;
            content.value = description;
            charCount.textContent = String(content.value.length);
            show(policyShell);
        };

        feeForm.addEventListener("submit", (event) => {
            event.preventDefault();
            if (!activeFeeRow) return;
            const cells = activeFeeRow.querySelectorAll("td");
            cells[2].textContent = `${feeForm.elements.commission.value}%`;
            cells[3].textContent = `${feeForm.elements.payment.value}%`;
            cells[4].textContent = `${new Intl.NumberFormat("vi-VN").format(Number(feeForm.elements.service.value))} đ`;
            const status = activeFeeRow.querySelector(".fee-status");
            status.textContent = feeForm.elements.enabled.checked ? "Đang áp dụng" : "Tạm tắt";
            status.className = `fee-status ${feeForm.elements.enabled.checked ? "fee-status--active" : "fee-status--paused"}`;
            close(feeShell);
        });

        content.addEventListener("input", () => {
            charCount.textContent = String(content.value.length);
        });

        policyForm.addEventListener("submit", (event) => {
            event.preventDefault();
            if (!activePolicyCard) return;
            activePolicyCard.querySelector("h3").textContent = policyForm.elements.title.value.trim();
            activePolicyCard.querySelector(":scope > p").textContent = content.value.trim();
            close(policyShell);
        });

        [feeShell, policyShell].forEach((shell) => {
            shell.drawer.querySelectorAll("[data-drawer-close], [data-drawer-cancel]").forEach((button) => button.addEventListener("click", () => close(shell)));
            shell.backdrop.addEventListener("click", () => close(shell));
        });
        document.addEventListener("keydown", (event) => {
            if (event.key !== "Escape") return;
            if (policyShell.drawer.classList.contains("is-open")) close(policyShell);
            else if (feeShell.drawer.classList.contains("is-open")) close(feeShell);
        });

        feeRows.forEach((row) => {
            row.classList.add("policy-fee-row-clickable");
            row.addEventListener("click", (event) => {
                if (event.target.closest("input, button, a, select")) return;
                openFee(row);
            });
            row.querySelector(".fee-edit")?.addEventListener("click", (event) => {
                event.stopPropagation();
                openFee(row);
            });
        });

        policyCards.forEach((card) => {
            card.classList.add("policy-card-clickable");
            card.addEventListener("click", (event) => {
                if (event.target.closest("input, button, a, textarea, select")) return;
                openPolicy(card);
            });
            card.querySelector("footer button")?.addEventListener("click", (event) => {
                event.stopPropagation();
                openPolicy(card);
            });
        });
    };

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initPolicyEffects, { once: true });
    else initPolicyEffects();
})();
