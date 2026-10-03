/* Reusable admin controls: time range popover and selectable table rows. */
(() => {
    const escapeHtml = (value = "") => String(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    }[char]));

    const actionIcon = (action) => {
        if (/^(Duyệt(?! đổi SĐT)|Kích hoạt|Áp dụng|Xác nhận|Chấp nhận|Đánh dấu (thành công|đã phản hồi))/i.test(action)) {
            return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
        }
        if (/^(Bàn giao|Đánh dấu đã giao)/i.test(action)) {
            return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 7h11v10H3zM14 10h4l3 3v4h-7z"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/></svg>`;
        }
        if (/^(Tạm ẩn|Tạm tắt|Ẩn đánh giá)/i.test(action)) {
            return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M3 3l18 18M10.6 10.7a2 2 0 0 0 2.7 2.7M9.9 5.2A10.8 10.8 0 0 1 12 5c6 0 9 7 9 7a16 16 0 0 1-2.1 3M6.6 6.6C4.3 8.2 3 12 3 12s3 7 9 7a9.7 9.7 0 0 0 3.4-.6" stroke-linecap="round"/></svg>`;
        }
        if (/^Xóa$/i.test(action)) {
            return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 7h16M9 7V4h6v3m3 0-1 13H7L6 7M10 11v5M14 11v5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
        }
        if (/^(Từ chối|Hủy|Tạm ngưng|Đánh dấu thất bại)/i.test(action)) {
            return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="m8.5 8.5 7 7m0-7-7 7" stroke-linecap="round"/></svg>`;
        }
        if (/^(Mở khóa|Khóa)/i.test(action)) {
            return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3" stroke-linecap="round"/></svg>`;
        }
        if (/^(Chuyển xác minh|Tiếp nhận xử lý)/i.test(action)) {
            return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m16 16 4 4M11 8v6m-3-3h6" stroke-linecap="round"/></svg>`;
        }
        if (/^(Đưa về|Gửi nhắc|Nhắc shop)/i.test(action)) {
            return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
        }
        if (/^Duyệt đổi SĐT/i.test(action)) {
            return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 3h4l2 5-3 2a16 16 0 0 0 5 5l2-3 5 2v4a3 3 0 0 1-3 3C10 21 3 14 3 6a3 3 0 0 1 3-3Z" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
        }
        if (/^Gán vai trò/i.test(action)) {
            return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="9" cy="8" r="4"/><path d="M3 21v-2a6 6 0 0 1 10.5-4M18 14v6m-3-3h6" stroke-linecap="round"/></svg>`;
        }
        if (/^Xuất/i.test(action)) {
            return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 3h9l4 4v14H6zM14 3v5h5M12 11v6m-3-3 3 3 3-3" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
        }
        if (/^Gắn cờ/i.test(action)) {
            return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M5 21V4m0 1h11l-1 4 1 4H5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
        }
        return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 8v8" stroke-linecap="round"/></svg>`;
    };

    const initTimeFilters = () => {
        const pad = (value) => String(value).padStart(2, "0");
        const today = new Date();
        const todayValue = `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`;
        const formatDate = (value) => {
            if (!value) return "";
            const [year, month, day] = value.split("-");
            return day ? `${day}/${month}/${year}` : value;
        };

        document.querySelectorAll("[data-time-filter]").forEach((trigger) => {
            if (trigger.dataset.timeReady === "1") return;
            trigger.dataset.timeReady = "1";
            trigger.classList.add("time-filter-trigger");
            trigger.setAttribute("aria-haspopup", "dialog");
            trigger.setAttribute("aria-expanded", "false");

            const wrapper = document.createElement("div");
            wrapper.className = "time-filter";
            trigger.parentNode.insertBefore(wrapper, trigger);
            wrapper.appendChild(trigger);

            const label = trigger.querySelector("[data-time-label]");
            if (!label) return;
            label.setAttribute("data-time-label", "");

            const popover = document.createElement("div");
            popover.className = "reusable-popover time-popover";
            popover.setAttribute("role", "dialog");
            popover.setAttribute("aria-label", "Chọn khoảng thời gian");
            popover.innerHTML = `
                <div class="time-popover__quick" role="group" aria-label="Khoảng thời gian nhanh">
                    ${["Tất cả", "Hôm nay", "7 ngày qua", "30 ngày qua", "Tháng này", "Quý này", "Năm nay"].map((item) => `<button class="time-chip${item === "Hôm nay" ? " is-active" : ""}" type="button" data-time-value="${escapeHtml(item)}">${escapeHtml(item)}</button>`).join("")}
                </div>
                <div class="time-popover__divider"></div>
                <div class="time-popover__modes" role="group" aria-label="Đơn vị thời gian">
                    <button class="is-active" type="button" data-time-mode="day">Ngày</button>
                    <button type="button" data-time-mode="month">Tháng</button>
                    <button type="button" data-time-mode="year">Năm</button>
                </div>
                <div class="time-popover__single">
                    <input type="date" value="${todayValue}" aria-label="Chọn ngày" data-time-single>
                    <button type="button" data-time-single-apply>Áp dụng</button>
                </div>
                <div class="time-popover__divider"></div>
                <p class="time-popover__caption">Khoảng tùy chỉnh</p>
                <div class="time-popover__range">
                    <input type="date" aria-label="Từ ngày" data-time-start>
                    <span>–</span>
                    <input type="date" aria-label="Đến ngày" data-time-end>
                </div>
                <button class="time-popover__apply" type="button" data-time-apply>Áp dụng khoảng</button>
            `;
            wrapper.appendChild(popover);

            const close = () => {
                wrapper.classList.remove("is-open");
                trigger.setAttribute("aria-expanded", "false");
            };
            const open = () => {
                document.querySelectorAll(".time-filter.is-open").forEach((item) => {
                    item.classList.remove("is-open");
                    item.querySelector("[data-time-label]")?.closest("button")?.setAttribute("aria-expanded", "false");
                });
                wrapper.classList.add("is-open");
                trigger.setAttribute("aria-expanded", "true");
            };

            trigger.addEventListener("click", (event) => {
                event.stopPropagation();
                wrapper.classList.contains("is-open") ? close() : open();
            });
            popover.addEventListener("click", (event) => event.stopPropagation());
            popover.querySelectorAll("[data-time-value]").forEach((button) => {
                button.addEventListener("click", () => {
                    popover.querySelectorAll("[data-time-value]").forEach((item) => item.classList.remove("is-active"));
                    button.classList.add("is-active");
                    label.textContent = button.dataset.timeValue === "Tất cả"
                        ? "Tất cả thời gian"
                        : button.dataset.timeValue === "Hôm nay"
                            ? `Hôm nay · ${formatDate(todayValue)}`
                            : button.dataset.timeValue;
                    trigger.dispatchEvent(new CustomEvent("time-filter-change", {
                        bubbles: true,
                        detail: { preset: button.dataset.timeValue }
                    }));
                    close();
                });
            });
            popover.querySelectorAll("[data-time-mode]").forEach((button) => {
                button.addEventListener("click", () => {
                    popover.querySelectorAll("[data-time-mode]").forEach((item) => item.classList.remove("is-active"));
                    button.classList.add("is-active");
                    const input = popover.querySelector("[data-time-single]");
                    input.type = button.dataset.timeMode === "month" ? "month" : button.dataset.timeMode === "year" ? "number" : "date";
                    input.value = button.dataset.timeMode === "month"
                        ? todayValue.slice(0, 7)
                        : button.dataset.timeMode === "year"
                            ? String(today.getFullYear())
                            : todayValue;
                    input.min = button.dataset.timeMode === "year" ? "2000" : "";
                    input.max = button.dataset.timeMode === "year" ? "2100" : "";
                    input.placeholder = button.dataset.timeMode === "year" ? "yyyy" : "";
                });
            });
            popover.querySelector("[data-time-single-apply]").addEventListener("click", () => {
                const mode = popover.querySelector("[data-time-mode].is-active").dataset.timeMode;
                const value = popover.querySelector("[data-time-single]").value;
                label.textContent = mode === "day" ? formatDate(value) : value || "Chọn thời gian";
                trigger.dispatchEvent(new CustomEvent("time-filter-change", {
                    bubbles: true,
                    detail: { mode, value }
                }));
                close();
            });
            popover.querySelector("[data-time-apply]").addEventListener("click", () => {
                const start = popover.querySelector("[data-time-start]").value;
                const end = popover.querySelector("[data-time-end]").value;
                label.textContent = start && end ? `${formatDate(start)} – ${formatDate(end)}` : "Khoảng tùy chỉnh";
                trigger.dispatchEvent(new CustomEvent("time-filter-change", {
                    bubbles: true,
                    detail: { start, end }
                }));
                close();
            });
            wrapper._closeTimeFilter = close;
        });

        document.addEventListener("click", (event) => {
            document.querySelectorAll(".time-filter.is-open").forEach((item) => {
                if (!item.contains(event.target)) item._closeTimeFilter?.();
            });
        });
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape") {
                document.querySelectorAll(".time-filter.is-open").forEach((item) => item._closeTimeFilter?.());
            }
        });
    };

    const initSelectableTables = () => {
        document.querySelectorAll("table[data-selectable-table]").forEach((table) => {
            if (table.dataset.selectionReady === "1") return;
            table.dataset.selectionReady = "1";

            const headCheckbox = table.querySelector("thead input[type='checkbox']");
            const rowCheckboxes = [...table.querySelectorAll("tbody input[type='checkbox']")];
            if (!headCheckbox || rowCheckboxes.length === 0) return;

            const container = table.closest("[data-selection-container]") || table.parentElement;
            const scrollWrap = table.closest(".table-scroll") || table.parentElement;
            const noun = table.dataset.selectionNoun || "bản ghi";
            const actions = (container.dataset.selectionActions || "Xử lý đã chọn").split("|").filter(Boolean);
            const primaryAction = container.dataset.selectionPrimaryAction || actions[0];
            const selectionLimit = Number.parseInt(table.dataset.selectionLimit || "", 10);
            const bar = document.createElement("div");
            bar.className = "bulk-action-bar";
            bar.hidden = true;
            bar.innerHTML = `
                <div class="bulk-action-bar__summary"><span data-selected-count>0</span><span>${escapeHtml(noun)} đã chọn</span></div>
                <div class="bulk-action-bar__actions">
                    ${actions.map((action, index) => {
                        const isPrimary = action === primaryAction;
                        const isDanger = /^(Từ chối|Xóa|Hủy|Tạm ngưng|Đánh dấu thất bại)/i.test(action);
                        return `<button type="button" class="bulk-action-bar__button${isPrimary ? " is-primary" : ""}${isDanger ? " is-danger" : ""}" data-bulk-action>${actionIcon(action)}<span>${escapeHtml(action)}</span></button>`;
                    }).join("")}
                </div>
                <button class="bulk-action-bar__clear" type="button" data-clear-selection aria-label="Bỏ chọn"><span aria-hidden="true">×</span><span>Bỏ chọn</span></button>
            `;
            const insertionPoint = scrollWrap === container ? table : scrollWrap;
            container.insertBefore(bar, insertionPoint);

            const count = bar.querySelector("[data-selected-count]");
            const availableCheckboxes = () => {
                const visible = rowCheckboxes.filter((checkbox) => {
                    const row = checkbox.closest("tr");
                    return row && !row.hidden && getComputedStyle(row).display !== "none";
                });
                return Number.isFinite(selectionLimit) && selectionLimit > 0
                    ? visible.slice(0, selectionLimit)
                    : visible;
            };
            const update = () => {
                const checked = rowCheckboxes.filter((checkbox) => checkbox.checked);
                const available = availableCheckboxes();
                const availableChecked = available.filter((checkbox) => checkbox.checked);
                const selected = checked.length;
                count.textContent = String(selected);
                bar.hidden = selected === 0;
                headCheckbox.checked = available.length > 0 && availableChecked.length === available.length;
                headCheckbox.indeterminate = availableChecked.length > 0 && availableChecked.length < available.length;
                rowCheckboxes.forEach((checkbox) => checkbox.closest("tr")?.classList.toggle("is-row-selected", checkbox.checked));
                container.dispatchEvent(new CustomEvent("table-selection-change", {
                    bubbles: true,
                    detail: { selected, checkboxes: checked }
                }));
            };
            const clear = () => {
                rowCheckboxes.forEach((checkbox) => { checkbox.checked = false; });
                update();
            };

            headCheckbox.addEventListener("change", () => {
                availableCheckboxes().forEach((checkbox) => { checkbox.checked = headCheckbox.checked; });
                update();
            });
            rowCheckboxes.forEach((checkbox) => checkbox.addEventListener("change", update));
            bar.querySelector("[data-clear-selection]").addEventListener("click", clear);
            bar.querySelectorAll("[data-bulk-action]").forEach((button) => button.addEventListener("click", () => {
                container.dispatchEvent(new CustomEvent("table-bulk-action", {
                    bubbles: true,
                    detail: { action: button.textContent.trim(), checkboxes: rowCheckboxes.filter((item) => item.checked) }
                }));
            }));
            new MutationObserver(update).observe(table.tBodies[0], {
                attributes: true,
                attributeFilter: ["hidden", "style"],
                subtree: true
            });
            update();
        });
    };

    const init = () => {
        initTimeFilters();
        initSelectableTables();
    };
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init, { once: true });
    else init();
})();
