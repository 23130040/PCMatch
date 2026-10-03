const config = JSON.parse(document.getElementById('pcmatch-config').textContent);

export const pageName = document.documentElement.dataset.page;
export const indexUrl = config.index;

export function pageUrl(section, page, args = {}) {
    const path = config.urls[section]?.[page];
    if (!path) throw new Error('Unknown page: ' + section + '/' + page);
    const query = new URLSearchParams(args).toString();
    return path + (query ? '?' + query : '');
}

export const assetUrl = path => config.staticUrl + path.replace(/^\/+/, '');

// Accept old demo notification links without redirecting outside buyer pages.
export function buyerDestination(value) {
    const fallback = pageUrl('buyer', 'account');
    try {
        const base = new URL('../', new URL(pageUrl('buyer', 'home'), location.origin));
        const target = new URL(value || fallback, base);
        if (target.origin !== location.origin) return fallback;
        const legacy = target.pathname.match(/\/buyer\/([\w-]+)\.html$/);
        if (legacy && config.urls.buyer[legacy[1]]) {
            target.pathname = pageUrl('buyer', legacy[1]);
        }
        if (Object.values(config.urls.buyer).includes(target.pathname)) {
            return target.pathname + target.search + target.hash;
        }
    } catch {}
    return fallback;
}
