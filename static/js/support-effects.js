/* Support topic filtering, search and article drawer. */
(() => {
    const articleSteps = {
        "Xác nhận đơn hàng và bàn giao cho đơn vị vận chuyển": [
            "Đơn hàng mới sẽ nằm ở trạng thái “Chờ xác nhận”. Bạn vào mục Đơn hàng, lọc theo trạng thái này để xử lý theo thứ tự thời gian.",
            "Với mỗi đơn, hãy kiểm tra người mua, địa chỉ giao hàng, shop phụ trách và giờ trị thanh toán. Nếu thông tin hợp lệ, bấm “Xác nhận đơn” để chuyển đơn sang giao hàng.",
            "Khi shop đã đóng gói xong, dùng nút “Bàn giao vận chuyển” để chuyển đơn sang trạng thái giao hàng. Hệ thống sẽ ghi nhận toàn bộ thao tác vào nhật ký hoạt động.",
            "Đơn quá hạn xác nhận sẽ được đánh dấu cảnh báo. Bạn có thể chọn nhiều đơn và xử lý hàng loạt để tiết kiệm thời gian."
        ],
        "Cách đối soát giao dịch và xử lý giao dịch lệch số tiền": [
            "Mở Giao dịch, lọc theo kỳ cần đối soát và tải báo cáo chi tiết.",
            "Đối chiếu tổng tiền hàng, phí vận chuyển, giảm giá và phí sàn với từng đơn liên quan.",
            "Với giao dịch lệch, kiểm tra lịch sử cập nhật trước khi tạo giao dịch điều chỉnh.",
            "Ghi chú lý do điều chỉnh và xác nhận với shop trước khi tất toán."
        ],
        "Duyệt hồ sơ shop tham gia sàn": [
            "Kiểm tra đầy đủ thông tin pháp lý và tài khoản ngân hàng của shop.",
            "Đối chiếu danh mục shop đăng ký với sản phẩm thực tế.",
            "Đánh giá lịch sử vận hành, chính sách bảo hành và khả năng xử lý đơn.",
            "Duyệt hồ sơ hoặc từ chối kèm lý do để shop có thể cập nhật."
        ],
        "Bật xác thực hai lớp và quản lý phiên đăng nhập": [
            "Vào Bảo mật & tài khoản và chọn Bật xác thực hai lớp.",
            "Quét mã QR bằng ứng dụng xác thực.",
            "Lưu mã khôi phục ở nơi an toàn.",
            "Kiểm tra danh sách phiên đăng nhập và đăng xuất các thiết bị không nhận diện."
        ]
    };

    const createArticleDrawer = () => {
        const backdrop = document.createElement("div");
        backdrop.className = "support-article-backdrop";
        backdrop.hidden = true;
        const drawer = document.createElement("aside");
        drawer.className = "support-article-drawer";
        drawer.hidden = true;
        drawer.setAttribute("aria-hidden", "true");
        drawer.innerHTML = `
            <header><div><h2 data-article-title>Bài viết</h2><p><span data-article-code>HD-001</span> · <span data-article-views>0 lượt xem</span></p></div><button type="button" data-article-close aria-label="Đóng">×</button></header>
            <div class="support-article-drawer__body">
                <div class="support-article-drawer__summary">Quy trình thực hiện rõ ràng, từng bước để bạn kiểm tra thông tin, xác nhận và hoàn tất thao tác đúng hạn.</div>
                <ol data-article-steps></ol>
            </div>
            <footer><span>Bài viết này có hữu ích không?</span><div><button type="button" data-helpful>👍 Hữu ích</button><button type="button" data-unhelpful>👎 Chưa rõ</button></div></footer>`;
        document.body.append(backdrop, drawer);
        return { backdrop, drawer };
    };

    const initSupport = () => {
        const search = document.querySelector("[data-support-search]");
        const articles = [...document.querySelectorAll("[data-article-list] > article")];
        const topics = [...document.querySelectorAll("[data-topic]")].filter((item) => item.classList.contains("support-topic"));
        const count = document.querySelector("[data-article-count]");
        const filterLabel = document.querySelector("[data-article-filter-label]");
        const empty = document.querySelector("[data-article-empty]");
        let activeTopic = "all";
        let activeQuery = "";

        const render = () => {
            let visible = 0;
            articles.forEach((article) => {
                const matchesTopic = activeTopic === "all" || article.dataset.topic === activeTopic;
                const matchesQuery = !activeQuery || article.textContent.toLowerCase().includes(activeQuery);
                const show = matchesTopic && matchesQuery;
                article.hidden = !show;
                if (show) visible += 1;
            });
            if (count) count.textContent = String(visible);
            if (filterLabel) filterLabel.textContent = topics.find((item) => item.dataset.topic === activeTopic)?.querySelector("strong").textContent || "Tất cả danh mục";
            if (empty) empty.hidden = visible !== 0;
        };

        topics.forEach((topic) => topic.addEventListener("click", () => {
            topics.forEach((item) => item.classList.remove("is-active"));
            topic.classList.add("is-active");
            activeTopic = topic.dataset.topic;
            render();
        }));
        search?.addEventListener("input", () => {
            activeQuery = search.value.trim().toLowerCase();
            render();
        });
        document.querySelectorAll("[data-search-term]").forEach((button) => button.addEventListener("click", () => {
            if (search) search.value = button.dataset.searchTerm;
            activeQuery = button.dataset.searchTerm.toLowerCase();
            render();
        }));

        const { backdrop, drawer } = createArticleDrawer();
        const stepsContainer = drawer.querySelector("[data-article-steps]");
        let openArticle = null;
        let openCode = 1;
        const close = () => {
            drawer.classList.remove("is-open");
            backdrop.classList.remove("is-open");
            document.body.classList.remove("has-support-article");
            window.setTimeout(() => { drawer.hidden = true; backdrop.hidden = true; }, 260);
        };
        const open = (title, views) => {
            openArticle = title;
            openCode += 1;
            drawer.querySelector("[data-article-title]").textContent = title;
            drawer.querySelector("[data-article-code]").textContent = `HD-${String(openCode).padStart(3, "0")}`;
            drawer.querySelector("[data-article-views]").textContent = views || "Bài viết hướng dẫn";
            const steps = articleSteps[title] || [
                `Mở phần quản trị tương ứng với chủ đề “${title}”.`,
                "Kiểm tra thông tin đầu vào và các trạng thái hiện tại trước khi thực hiện.",
                "Thực hiện thao tác theo hướng dẫn của đội nghiệp vụ và kiểm tra kết quả.",
                "Nếu cần hỗ trợ thêm, liên hệ hotline 1900 6868 trong giờ hành chính."
            ];
            stepsContainer.innerHTML = steps.map((step) => `<li>${step}</li>`).join("");
            drawer.hidden = false;
            backdrop.hidden = false;
            document.body.classList.add("has-support-article");
            requestAnimationFrame(() => { drawer.classList.add("is-open"); backdrop.classList.add("is-open"); });
        };

        articles.forEach((article) => article.addEventListener("click", () => open(article.dataset.title)));
        document.querySelectorAll("[data-most-read]").forEach((button) => button.addEventListener("click", () => open(button.dataset.mostRead, button.dataset.views)));
        drawer.querySelector("[data-article-close]").addEventListener("click", close);
        backdrop.addEventListener("click", close);
        document.addEventListener("keydown", (event) => { if (event.key === "Escape" && drawer.classList.contains("is-open")) close(); });
        drawer.querySelectorAll("[data-helpful], [data-unhelpful]").forEach((button) => button.addEventListener("click", () => {
            drawer.querySelectorAll("[data-helpful], [data-unhelpful]").forEach((item) => item.classList.remove("is-selected"));
            button.classList.add("is-selected");
        }));
        render();
    };

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initSupport, { once: true });
    else initSupport();
})();
