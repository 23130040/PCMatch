import {money} from './data.js';
import {esc, link, button, toast, page} from './ui.js';

const storageKey = 'pcmatch-product-compare';
let selected = [];

function readSelection() {
    try {
        const items = JSON.parse(localStorage.getItem(storageKey) || '[]');
        return Array.isArray(items) ? items.filter(item => item && /^\d+$/.test(item.id) && /^\d+$/.test(item.category) && typeof item.name === 'string').slice(0, 4) : [];
    } catch {
        return [];
    }
}

function saveSelection() {
    localStorage.setItem(storageKey, JSON.stringify(selected));
}

function comparisonUrl() {
    return link('compare', {source: 'database', products: selected.map(item => item.id).join(',')});
}

function updateSelection() {
    document.querySelectorAll('[data-compare-link]').forEach(node => {
        node.textContent = 'So sánh (' + selected.length + ')';
        node.href = comparisonUrl();
    });
    document.querySelectorAll('[data-action="product-compare-add"]').forEach(node => {
        const added = selected.some(item => item.id === node.dataset.id);
        node.textContent = added ? 'Đã thêm so sánh' : 'Thêm so sánh';
        node.setAttribute('aria-pressed', String(added));
    });
    document.querySelectorAll('[data-content="compare-tray"]').forEach(node => {
        node.innerHTML = selected.length ? '<div class="compare-tray-inner"><strong>Đang so sánh ' + selected.length + '/4</strong><div class="cluster">' + selected.map(item => button(esc(item.name) + ' · Bỏ', 'product-compare-remove', item.id)).join('') + '</div><div class="cluster"><a class="btn btn--primary" href="' + esc(comparisonUrl()) + '">Xem bảng so sánh</a>' + button('Xóa danh sách', 'product-compare-clear') + '</div></div>' : '';
    });
}

export function initProductCatalog() {
    document.querySelectorAll('[data-product-price]').forEach(node => {
        node.textContent = money(Number(node.dataset.productPrice));
    });
    const compared = document.getElementById('product-compare-items');
    selected = compared ? JSON.parse(compared.textContent) : readSelection();
    if (compared) saveSelection();
    updateSelection();
}

export function productCatalogAction(action, id) {
    if (document.documentElement.dataset.catalogSource !== 'database') return false;
    if (action === 'product-shop-open') {
        document.getElementById('product-shop-' + id)?.showModal();
        return true;
    }
    if (action === 'product-compare-add') {
        const card = document.querySelector('[data-product-id="' + id + '"]');
        if (!card) return true;
        selected = readSelection();
        if (selected.some(item => item.id === id)) return true;
        if (selected.some(item => item.category !== card.dataset.productCategory)) throw Error('Chỉ so sánh sản phẩm cùng danh mục. Xóa danh sách hiện tại để chọn danh mục khác.');
        if (selected.length >= 4) throw Error('Chỉ được so sánh tối đa 4 sản phẩm.');
        selected.push({id, category: card.dataset.productCategory, name: card.dataset.productName});
        saveSelection();
        updateSelection();
        toast('Đã thêm ' + card.dataset.productName + ' vào so sánh.');
        return true;
    }
    if (action === 'product-compare-remove' || action === 'product-compare-clear') {
        selected = readSelection();
        selected = action === 'product-compare-clear' ? [] : selected.filter(item => item.id !== id);
        saveSelection();
        if (page === 'compare') location.href = comparisonUrl();
        else updateSelection();
        return true;
    }
    return false;
}
