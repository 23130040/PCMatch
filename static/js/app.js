const selectAll = (selector, scope = document) => [...scope.querySelectorAll(selector)];

document.body.classList.add("admin-ui");

// Normalize the compact KPI cards shared by the admin screens.
selectAll(".admin-metrics, .dashboard-metrics, .kpi-grid, .policy-kpi-grid, .support-kpi-grid, .stat-grid, .summary-cards").forEach((grid) => {
    grid.classList.add("quick-stats");
    [...grid.children].forEach((card) => card.classList.add("quick-stat-card"));
});

selectAll([
    ".quick-stats .metric-value > .status",
    ".quick-stats .metric-value > em",
    ".quick-stats .trend",
    ".quick-stats .product-trend",
    ".quick-stats .category-trend",
    ".quick-stats .policy-trend",
    ".quick-stats .stat-sub > span",
    ".quick-stats .sc-badge",
    ".quick-stats article > div > em"
].join(",")).forEach((trend) => {
    const rawText = trend.textContent.trim();
    const className = trend.className.toLowerCase();
    const isDown = /^[↓↘]/.test(rawText) ||
        trend.querySelector(".fa-arrow-down") ||
        /(^|[-_\s])(down|bad|red|negative)($|[-_\s])/.test(className);
    const label = rawText.replace(/^[↑↓↗↘]\s*/, "");
    const icon = document.createElement("i");

    icon.className = `fa-solid fa-arrow-${isDown ? "down" : "up"}`;
    icon.setAttribute("aria-hidden", "true");
    trend.classList.add("quick-trend", isDown ? "quick-trend--down" : "quick-trend--up");
    trend.replaceChildren(icon, document.createTextNode(label));
});

// Activity cards keep the trend beside the primary value instead of on a separate row.
selectAll(".quick-stat-card .stat-sub > .quick-trend").forEach((trend) => {
    const holder = trend.parentElement;
    const value = trend.closest(".quick-stat-card")?.querySelector(".stat-value");

    if (!value) return;
    value.appendChild(trend);
    if (holder && !holder.textContent.trim()) holder.remove();
});

// Snap legacy page-specific font sizes to the shared admin typography scale.
const adminTypeClasses = [
    "admin-type-caption",
    "admin-type-small",
    "admin-type-body",
    "admin-type-section",
    "admin-type-page",
    "admin-type-metric"
];

selectAll(".shell__content *").forEach((element) => {
    if (["SCRIPT", "STYLE", "SVG", "PATH", "TEXT", "TITLE", "DESC", "I", "BR"].includes(element.tagName)) return;

    const hasDirectText = [...element.childNodes].some((node) =>
        node.nodeType === Node.TEXT_NODE && node.textContent.trim()
    );
    if (!hasDirectText) return;

    const size = Number.parseFloat(getComputedStyle(element).fontSize);
    if (!Number.isFinite(size)) return;

    let typeClass;
    if (element.matches(".admin-section-title h2, .admin-section-title h3, .panel__head h2, .panel__head h3, .panel-header h2, .support-section-heading h2, .policy-content-title, .policy-section h3")) {
        typeClass = "admin-type-section";
    } else if (size <= 11.49) {
        typeClass = "admin-type-caption";
    } else if (size <= 12.49) {
        typeClass = "admin-type-small";
    } else if (size <= 14.49) {
        typeClass = "admin-type-body";
    } else if (size <= 22) {
        typeClass = "admin-type-section";
    } else if (size <= 27.5) {
        typeClass = "admin-type-page";
    } else {
        typeClass = "admin-type-metric";
    }

    element.classList.remove(...adminTypeClasses);
    element.classList.add(typeClass);
});

selectAll("[data-menu-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
        const target = document.querySelector(button.dataset.menuToggle);
        if (!target) return;
        const open = target.classList.toggle("is-open");
        button.setAttribute("aria-expanded", String(open));
    });
});

selectAll("[data-sidebar-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
        const shell = document.querySelector(".shell");
        if (!shell) return;
        const open = shell.classList.toggle("is-sidebar-open");
        button.setAttribute("aria-expanded", String(open));
    });
});

selectAll(".sidebar a").forEach((link) => {
    if (link.pathname === window.location.pathname) {
        link.setAttribute("aria-current", "page");
    }
});

selectAll("[role='tablist']").forEach((tablist) => {
    const tabs = selectAll("[role='tab']", tablist);
    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            tabs.forEach((item) => item.setAttribute("aria-selected", "false"));
            selectAll("[role='tabpanel']").forEach((panel) => {
                panel.hidden = true;
            });
            tab.setAttribute("aria-selected", "true");
            const panel = document.getElementById(tab.getAttribute("aria-controls"));
            if (panel) panel.hidden = false;
        });
    });
});

selectAll("[data-modal-open]").forEach((button) => {
    button.addEventListener("click", () => {
        const dialog = document.getElementById(button.dataset.modalOpen);
        if (dialog?.showModal) dialog.showModal();
    });
});

selectAll("[data-modal-close]").forEach((button) => {
    button.addEventListener("click", () => button.closest("dialog")?.close());
});

selectAll(".build-slot[data-signal]").forEach((slot) => {
    slot.addEventListener("click", () => {
        selectAll(".build-slot[data-signal]").forEach((item) => item.classList.remove("is-active"));
        slot.classList.add("is-active");
        const signal = slot.dataset.signal;
        selectAll("[data-telemetry]").forEach((card) => {
            const active = card.dataset.telemetry === signal || card.dataset.telemetry === "all";
            card.style.opacity = active ? "1" : ".58";
        });
        const live = document.querySelector("[data-live-signal]");
        if (live) live.textContent = `Đang xem tín hiệu: ${slot.dataset.label}`;
    });
});

selectAll("[data-dropdown]").forEach((button) => {
    button.addEventListener("click", () => {
        const menu = document.getElementById(button.dataset.dropdown);
        if (!menu) return;
        const open = !menu.hidden;
        menu.hidden = open;
        button.setAttribute("aria-expanded", String(!open));
    });
});

// User dropdown toggle
document.addEventListener('click', function (e) {
    const trigger = e.target.closest('.user-dropdown > a');

    if (trigger) {
        e.preventDefault();

        const dropdown = trigger.closest('.user-dropdown');

        if (!dropdown) return;

        document.querySelectorAll('.user-dropdown.open').forEach(item => {
            if (item !== dropdown) {
                item.classList.remove('open');
            }
        });

        dropdown.classList.toggle('open');
        return;
    }

    if (!e.target.closest('.user-dropdown')) {
        document.querySelectorAll('.user-dropdown.open')
            .forEach(item => item.classList.remove('open'));
    }
});


document.addEventListener("DOMContentLoaded", function () {

    const points = Array.from(document.querySelectorAll(".chart-points circle"));
    const bars = Array.from(document.querySelectorAll(".chart-bars rect"));

    const tooltip = document.getElementById("chartTooltip");
    const tooltipTime = document.getElementById("tooltipTime");
    const tooltipRevenue = document.getElementById("tooltipRevenue");
    const tooltipFee = document.getElementById("tooltipFee");

    const chartContainer = document.querySelector(".admin-chart-wrap");

    if (!points.length || !bars.length || !tooltip || !chartContainer) {
        return;
    }

    const hideTooltip = () => {
        tooltip.classList.remove("show");
        bars.forEach((bar) => bar.classList.remove("is-active"));
    };

    const showTooltip = (target, dataPoint, bar) => {
            tooltipTime.textContent = dataPoint.dataset.time;
            tooltipRevenue.textContent = dataPoint.dataset.revenue;
            tooltipFee.textContent = dataPoint.dataset.fee;

            tooltip.classList.add("show");
            bars.forEach((item) => item.classList.toggle("is-active", item === bar));

            const targetRect = target.getBoundingClientRect();
            const containerRect =
                chartContainer.getBoundingClientRect();

            const pointX =
                targetRect.left -
                containerRect.left +
                targetRect.width / 2;

            const pointY =
                targetRect.top -
                containerRect.top;

            const tooltipWidth = tooltip.offsetWidth;
            const tooltipHeight = tooltip.offsetHeight;

            let left = pointX - tooltipWidth / 2;
            let top = pointY - tooltipHeight - 14;

            if (left < 5) {
                left = 5;
            }

            if (left + tooltipWidth >
                chartContainer.clientWidth - 5) {

                left =
                    chartContainer.clientWidth -
                    tooltipWidth -
                    5;
            }

            if (top < 5) {
                top = pointY + 18;
            }

            tooltip.style.left = `${left}px`;
            tooltip.style.top = `${top}px`;
    };

    bars.forEach((bar, index) => {
        const point = points[index];
        if (!point) return;

        const accessibleLabel = `${point.dataset.time}: Doanh thu ${point.dataset.revenue}, phí và hoa hồng ${point.dataset.fee}`;
        bar.setAttribute("tabindex", "0");
        bar.setAttribute("role", "img");
        bar.setAttribute("aria-label", accessibleLabel);

        bar.addEventListener("mouseenter", () => showTooltip(bar, point, bar));
        bar.addEventListener("mouseleave", hideTooltip);
        bar.addEventListener("focus", () => showTooltip(bar, point, bar));
        bar.addEventListener("blur", hideTooltip);

        point.addEventListener("mouseenter", () => showTooltip(point, point, bar));
        point.addEventListener("mouseleave", hideTooltip);
    });

});
// Keyboard navigation for legacy Shop/Admin tabs. Buyer state lives in buyer.js modules.
selectAll("[role=tablist]").forEach(list => list.addEventListener("keydown", event => {
    const tabs = selectAll("[role=tab]", list);
    const index = tabs.indexOf(document.activeElement);
    if (index < 0 || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    tabs[next].focus();
    tabs[next].click();
}));
