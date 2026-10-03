BUYER_PAGES = (
    'home', 'search', 'model', 'shop', 'compare', 'cart', 'checkout',
    'payment', 'orders', 'order', 'builder', 'builds', 'consultation',
    'requests', 'proposals', 'account', 'addresses', 'notifications',
    'cases', 'help',
)

SHOP_PAGES = (
    'dashboard', 'offers', 'inventory', 'build-requests',
    'build-request-detail', 'proposal-builder', 'proposal-list',
    'proposal', 'orders', 'order', 'fulfillment',
)

STAFF_PAGES = (
    'dashboard', 'order', 'transaction', 'return', 'shop', 'products',
    'categories', 'guest', 'review', 'complain', 'authorization',
    'activityLog', 'activity-log', 'profile', 'password', 'policies',
    'support',
)

# Public route names may differ from the legacy HTML filenames.
PAGE_GROUPS = {
    'buyer': {page: f'buyer/{page}.html' for page in BUYER_PAGES},
    'shop': {page: f'shop/{page}.html' for page in SHOP_PAGES},
    'staff': {
        **{page: f'admin/{page}.html' for page in STAFF_PAGES},
        'fee-policies': 'admin/fee&policies.html',
    },
    'auth': {'login': 'auth/login.html'},
    'states': {'index': 'states/index.html'},
}


def route_name(section, page):
    return f'{section}_{page.replace("-", "_")}'
