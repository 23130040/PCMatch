// Static help articles are written in HTML; this script only filters and opens them.
(() => {
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


    const backdrop = document.querySelector('.support-article-backdrop');
    let activeDrawer = null;
    const close = () => {
        if (!activeDrawer) return;
        activeDrawer.classList.remove('is-open');
        activeDrawer.hidden = true;
        activeDrawer.setAttribute('aria-hidden', 'true');
        backdrop.classList.remove('is-open');
        backdrop.hidden = true;
        document.body.classList.remove('has-support-article');
        activeDrawer = null;
    };
    const open = title => {
        close();
        const drawer = [...document.querySelectorAll('[data-help-title]')].find(node => node.dataset.helpTitle === title);
        if (!drawer) return;
        activeDrawer = drawer;
        drawer.hidden = false;
        drawer.setAttribute('aria-hidden', 'false');
        backdrop.hidden = false;
        document.body.classList.add('has-support-article');
        requestAnimationFrame(() => {drawer.classList.add('is-open'); backdrop.classList.add('is-open');});
    };
    articles.forEach(article => article.addEventListener('click', () => open(article.dataset.title)));
    document.querySelectorAll('[data-most-read]').forEach(button => button.addEventListener('click', () => open(button.dataset.mostRead)));
    document.querySelectorAll('[data-article-close]').forEach(button => button.addEventListener('click', close));
    backdrop?.addEventListener('click', close);
    document.addEventListener('keydown', event => {if (event.key === 'Escape') close();});
    document.querySelectorAll('[data-helpful], [data-unhelpful]').forEach(button => button.addEventListener('click', () => {
        button.closest('footer').querySelectorAll('button').forEach(node => node.classList.toggle('is-selected', node === button));
    }));
    render();
})();
