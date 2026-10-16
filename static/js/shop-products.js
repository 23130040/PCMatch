import {mineSeller,sdb,stx,seller,uid,money,clone} from './shop-store.js';
import {esc,params,go,link,a,btn,field,select,textarea,submit,form,notice,empty,panel,head,badge,statusBadge,mount,toast,dialog,operation,requireSeller} from './shop-ui.js';
import {models,categories,model as getModel} from './data.js';

const CAT_OPTS=Object.fromEntries(Object.entries(categories));

export function offers(){
  if(!requireSeller())return;
  const q=(params.get('q')||'').toLowerCase();
  const cat=params.get('cat')||'';
  const statusFilter=params.get('status')||'';
  let products=mineSeller('shopProducts');
  const total=products.length;
  const selling=products.filter(p=>p.active&&p.stock>0).length;
  const outOfStock=products.filter(p=>p.stock===0&&p.active).length;
  const hidden=products.filter(p=>!p.active).length;

  if(q)products=products.filter(p=>p.name.toLowerCase().includes(q)||p.brand?.toLowerCase().includes(q));
  if(cat)products=products.filter(p=>p.category===cat);
  if(statusFilter==='active')products=products.filter(p=>p.active&&p.stock>0);
  else if(statusFilter==='out')products=products.filter(p=>p.stock===0&&p.active);
  else if(statusFilter==='inactive')products=products.filter(p=>!p.active);

  const isNew=params.has('new');
  const editId=params.get('edit');
  const editProduct=editId?mineSeller('shopProducts').find(p=>p.id===editId):null;

  const allCount=mineSeller('shopProducts').length;
  const activeCount=mineSeller('shopProducts').filter(p=>p.active&&p.stock>0).length;
  const outCount=mineSeller('shopProducts').filter(p=>p.stock===0&&p.active).length;
  const hiddenCount=mineSeller('shopProducts').filter(p=>!p.active).length;

  mount('Sản phẩm bán',`
    <section class="sa-page-heading">
      <div>
        <div class="sa-breadcrumbs">
          <a href="${link('dashboard')}">Kênh bán</a>
          <span>/</span>
          <span>Quản lý sản phẩm</span>
        </div>
        <h1>Quản lý sản phẩm</h1>
        <p>Theo dõi sản phẩm shop đang bán, tồn kho và tình trạng bán hàng.</p>
        <div class="sa-pending-note">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" width="14" height="14"><path d="M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
          <span>${total} sản phẩm trong danh mục hiện tại</span>
        </div>
      </div>
      <div class="sa-page-actions">
        ${a('+ Thêm sản phẩm','offers',{new:'1'},'primary')}
      </div>
    </section>

    <section class="sa-kpi-grid" aria-label="Số liệu sản phẩm">
      <article class="sa-kpi-card sa-kpi-card--blue">
        <h2>Tổng sản phẩm</h2>
        <div class="sa-kpi-value"><strong>${total}</strong><span>sản phẩm</span></div>
        <p>Toàn bộ linh kiện và module đang được đăng bán trên sàn</p>
      </article>
      <article class="sa-kpi-card sa-kpi-card--amber">
        <h2>Hết hàng</h2>
        <div class="sa-kpi-value"><strong>${outOfStock}</strong><span>sản phẩm</span></div>
        <p>Sản phẩm hết tồn kho hoặc được đánh dấu hết hàng</p>
      </article>
      <article class="sa-kpi-card sa-kpi-card--sky">
        <h2>Đang bán</h2>
        <div class="sa-kpi-value"><strong>${selling}</strong><span>sản phẩm</span></div>
        <p>Sản phẩm đang hoạt động và còn hàng trong kho</p>
      </article>
      <article class="sa-kpi-card sa-kpi-card--rose">
        <h2>Tạm ẩn</h2>
        <div class="sa-kpi-value"><strong>${hidden}</strong><span>sản phẩm</span></div>
        <p>Sản phẩm đang được đặt ở trạng thái tạm ẩn</p>
      </article>
    </section>

    ${isNew||editProduct?renderProductForm(editProduct):`
      <div class="sa-table-card">
        <div class="sa-table-toolbar">
          <div class="sa-table-filters">
            <label class="sa-table-search">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
              <input type="text" id="sa-search-input" placeholder="Tìm theo tên sản phẩm hoặc thương hiệu..." value="${esc(params.get('q')||'')}">
            </label>
            <select class="sa-filter-select" id="sa-cat-select">
              <option value="">Tất cả danh mục</option>
              ${Object.entries(CAT_OPTS).map(([k,v])=>`<option value="${esc(k)}" ${k===cat?'selected':''}>${esc(v)}</option>`).join('')}
            </select>
          </div>
          <span class="sa-result-count"><strong>${products.length}</strong> sản phẩm khớp bộ lọc</span>
        </div>

        <div class="sa-filter-tabs">
          <button class="sa-tab ${!statusFilter?'is-active':''}" data-action="sa-filter" data-status="">Tất cả <span>${allCount}</span></button>
          <button class="sa-tab ${statusFilter==='active'?'is-active':''}" data-action="sa-filter" data-status="active">Đang bán <span>${activeCount}</span></button>
          <button class="sa-tab ${statusFilter==='out'?'is-active':''}" data-action="sa-filter" data-status="out">Hết hàng <span>${outCount}</span></button>
          <button class="sa-tab ${statusFilter==='inactive'?'is-active':''}" data-action="sa-filter" data-status="inactive">Tạm ẩn <span>${hiddenCount}</span></button>
        </div>

        <div class="table-scroll">
          ${products.length?`<table>
            <thead><tr>
              <th class="checkbox-cell"><input type="checkbox" aria-label="Chọn tất cả"></th>
              <th>SẢN PHẨM</th>
              <th>DANH MỤC</th>
              <th>GIÁ BÁN</th>
              <th class="center">TỒN KHO</th>
              <th class="center">ĐÃ BÁN</th>
              <th class="center">TRẠNG THÁI</th>
              <th class="center">THAO TÁC</th>
            </tr></thead>
            <tbody>
              ${products.map(p=>`<tr>
                <td class="checkbox-cell"><input type="checkbox" aria-label="Chọn ${esc(p.name)}"></td>
                <td>
                  <div class="sa-product-cell">
                    <div class="sa-product-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 9h6m-6 4h6m-6 4h4"/></svg>
                    </div>
                    <div>
                      <strong>${esc(p.name)}</strong>
                      <small>Mã SP: #${esc(p.id)}</small>
                    </div>
                  </div>
                </td>
                <td>${esc(categories[p.category]||p.category)}</td>
                <td class="sa-product-price"><strong>${money(p.price)}</strong></td>
                <td class="center sa-product-number ${p.stock===0?'text-danger':p.stock<=3?'text-warn':''}">${p.stock}</td>
                <td class="center sa-product-number">${p.sold||0}</td>
                <td class="center">${_productStatus(p)}</td>
                <td class="center">
                  <div class="sa-table-actions">
                    ${a('✎ Sửa','offers',{edit:p.id},'sa-detail-btn')}
                    <button type="button" class="sa-detail-btn ${p.active?'sa-detail-btn--warn':''}" data-action="toggle-product" data-id="${esc(p.id)}">${p.active?'Ẩn':'Hiện'}</button>
                    <button type="button" class="sa-detail-btn sa-detail-btn--danger" data-action="delete-product" data-id="${esc(p.id)}">Xóa</button>
                  </div>
                </td>
              </tr>`).join('')}
            </tbody>
          </table>`:`<div class="sa-empty-table">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true" width="48" height="48"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 9h6m-6 4h6m-6 4h4"/></svg>
            <h3>Không có sản phẩm</h3>
            <p>Thêm sản phẩm đầu tiên hoặc thay đổi bộ lọc.</p>
            ${a('+ Thêm sản phẩm','offers',{new:'1'},'primary')}
          </div>`}
        </div>

        ${products.length?`<footer class="sa-table-pagination">
          <p>Hiển thị <strong>1 - ${products.length}</strong> trên <strong>${products.length}</strong> bản ghi</p>
          <nav aria-label="Phân trang">
            <button type="button" disabled aria-label="Trang trước">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m15 18-6-6 6-6" stroke-linecap="round"/></svg>
            </button>
            <span>Trang 1 / 1</span>
            <button type="button" disabled aria-label="Trang sau">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6" stroke-linecap="round"/></svg>
            </button>
          </nav>
        </footer>`:''}
      </div>
    `}
  `);

  // Gắn filter tabs
  document.querySelectorAll('[data-action="sa-filter"]').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const s=btn.dataset.status;
      const newParams=new URLSearchParams(location.search);
      if(s)newParams.set('status',s);else newParams.delete('status');
      location.href=link('offers',Object.fromEntries(newParams));
    });
  });
  // Search inline
  const si=document.getElementById('sa-search-input');
  if(si){
    si.addEventListener('keydown',e=>{
      if(e.key==='Enter'){
        const newParams=new URLSearchParams(location.search);
        if(si.value.trim())newParams.set('q',si.value.trim());else newParams.delete('q');
        location.href=link('offers',Object.fromEntries(newParams));
      }
    });
  }
  const cs=document.getElementById('sa-cat-select');
  if(cs){
    cs.addEventListener('change',()=>{
      const newParams=new URLSearchParams(location.search);
      if(cs.value)newParams.set('cat',cs.value);else newParams.delete('cat');
      location.href=link('offers',Object.fromEntries(newParams));
    });
  }
}

function _productStatus(p){
  if(p.active&&p.stock>0)return '<span class="sa-product-status sa-product-status--selling">Đang bán</span>';
  if(p.active&&p.stock===0)return '<span class="sa-product-status sa-product-status--out">Hết hàng</span>';
  return '<span class="sa-product-status sa-product-status--hidden">Tạm ẩn</span>';
}

function renderProductForm(product){
  const isEdit=!!product;
  return `<section class="panel panel--padded sa-form-panel">
    <h2>${isEdit?'Sửa sản phẩm: '+esc(product.name):'Thêm sản phẩm mới'}</h2>
    ${form('product-form',`
      <input type="hidden" name="id" value="${isEdit?esc(product.id):''}">
      <div class="two-col">
        ${select('Danh mục sản phẩm','category',CAT_OPTS,isEdit?product.category:'CPU')}
        ${field('Tên sản phẩm','name',isEdit?product.name:'','text','required maxlength="200"')}
      </div>
      <div class="two-col">
        ${field('Thương hiệu','brand',isEdit?product.brand||'':'','text','required maxlength="60"')}
        ${field('Giá bán (VND)','price',isEdit?product.price:'','number','required min="1000" step="1000"')}
      </div>
      <div class="two-col">
        ${field('Số lượng tồn kho','stock',isEdit?product.stock:'','number','required min="0" step="1"')}
        ${field('Thời gian bảo hành (tháng)','warranty',isEdit?product.warranty||36:'36','number','required min="0" max="120"')}
      </div>
      ${textarea('Mô tả sản phẩm','description',isEdit?product.description||'':'')}
      <div class="cluster">
        ${submit(isEdit?'Lưu thay đổi':'Thêm sản phẩm')}
        ${a('Hủy','offers')}
      </div>
    `)}
  </section>`;
}

export function inventory(){
  if(!requireSeller())return;
  const products=mineSeller('shopProducts');
  const low=products.filter(p=>p.active&&p.stock<=3);
  const out=products.filter(p=>p.active&&p.stock===0);
  const ok=products.filter(p=>p.active&&p.stock>3);
  const inactive=products.filter(p=>!p.active);

  mount('Tồn kho',`
    <section class="sa-page-heading">
      <div>
        <div class="sa-breadcrumbs"><a href="${link('dashboard')}">Kênh bán</a><span>/</span><span>Tồn kho</span></div>
        <h1>Quản lý tồn kho</h1>
        <p>Theo dõi và cập nhật số lượng hàng trong kho.</p>
      </div>
    </section>

    <section class="sa-kpi-grid">
      <article class="sa-kpi-card sa-kpi-card--blue"><h2>Tổng sản phẩm</h2><div class="sa-kpi-value"><strong>${products.length}</strong><span>sản phẩm</span></div><p>Tổng số sản phẩm đang quản lý</p></article>
      <article class="sa-kpi-card sa-kpi-card--sky"><h2>Tồn ổn định</h2><div class="sa-kpi-value"><strong>${ok.length}</strong><span>sản phẩm</span></div><p>Sản phẩm còn đủ hàng trong kho</p></article>
      <article class="sa-kpi-card sa-kpi-card--amber"><h2>Sắp hết (&le;3)</h2><div class="sa-kpi-value"><strong>${low.length}</strong><span>sản phẩm</span></div><p>Cần nhập thêm hàng sớm</p></article>
      <article class="sa-kpi-card sa-kpi-card--rose"><h2>Hết hàng</h2><div class="sa-kpi-value"><strong>${out.length}</strong><span>sản phẩm</span></div><p>Sản phẩm cần nhập hàng ngay</p></article>
    </section>

    ${low.length?`<div class="sa-table-card sa-table-card--compact" style="margin-bottom:20px">
      <div class="sa-table-toolbar"><h3 style="margin:0;font-size:14px;font-weight:600;">⚠️ Cần nhập thêm hàng</h3></div>
      <div class="table-scroll"><table>
        <thead><tr><th>SẢN PHẨM</th><th class="center">TỒN</th><th class="center">ĐÃ BÁN</th><th>CẬP NHẬT TỒN</th></tr></thead>
        <tbody>
          ${low.map(p=>`<tr class="${p.stock===0?'sa-row--danger':'sa-row--warn'}">
            <td><strong>${esc(p.name)}</strong></td>
            <td class="center"><strong style="color:${p.stock===0?'var(--color-red)':'var(--color-amber)'}">${p.stock}</strong></td>
            <td class="center">${p.sold||0}</td>
            <td><form data-form="update-stock" class="inv-update-form"><input type="hidden" name="id" value="${esc(p.id)}"><input type="number" name="qty" value="${p.stock}" min="0" step="1"><button type="submit" class="inv-update-btn">Cập nhật</button></form></td>
          </tr>`).join('')}
        </tbody>
      </table></div>
    </div>`:''}

    <div class="sa-table-card sa-table-card--compact">
      <div class="sa-table-toolbar"><h3 style="margin:0;font-size:14px;font-weight:600;">Toàn bộ sản phẩm đang bán</h3></div>
      <div class="table-scroll"><table>
        <thead><tr><th>SẢN PHẨM</th><th>DANH MỤC</th><th>GIÁ</th><th class="center">TỒN</th><th class="center">ĐÃ BÁN</th><th>CẬP NHẬT</th></tr></thead>
        <tbody>
          ${products.filter(p=>p.active).map(p=>`<tr>
            <td><strong>${esc(p.name)}</strong></td>
            <td>${esc(categories[p.category]||p.category)}</td>
            <td>${money(p.price)}</td>
            <td class="center ${p.stock===0?'text-danger':p.stock<=3?'text-warn':''}">${p.stock}</td>
            <td class="center">${p.sold||0}</td>
            <td><form data-form="update-stock" class="inv-update-form"><input type="hidden" name="id" value="${esc(p.id)}"><input type="number" name="qty" value="${p.stock}" min="0" step="1"><button type="submit" class="inv-update-btn">Cập nhật</button></form></td>
          </tr>`).join('')}
        </tbody>
      </table></div>
    </div>
  `);
}

export function action(act,id){
  if(!requireSeller())return true;
  if(act==='toggle-product'){
    const p=mineSeller('shopProducts').find(x=>x.id===id);
    if(!p)throw Error('Không tìm thấy sản phẩm.');
    dialog(`${p.active?'Ẩn':'Hiện'} sản phẩm?`,`Sản phẩm "${esc(p.name)}" sẽ ${p.active?'không còn hiển thị':'được hiển thị trở lại'} với người mua.`,()=>{
      stx(()=>p.active=!p.active);
      offers();
      toast(`Đã ${p.active?'hiện':'ẩn'} sản phẩm.`);
    });
    return true;
  }
  if(act==='delete-product'){
    const p=mineSeller('shopProducts').find(x=>x.id===id);
    if(!p)throw Error('Không tìm thấy sản phẩm.');
    dialog('Xóa sản phẩm?',`Xóa "${esc(p.name)}" khỏi danh sách? Không thể khôi phục.`,()=>{
      stx(s=>s.shopProducts=s.shopProducts.filter(x=>x.id!==id));
      offers();
      toast('Đã xóa sản phẩm.');
    });
    return true;
  }
  return false;
}

export async function submitForm(name,f,d){
  if(!requireSeller())return true;
  if(name==='prod-filter'){go('offers',Object.fromEntries(Object.entries(d).filter(([,v])=>v)));return true;}
  if(name==='product-form'){
    if(!d.name.trim())throw Error('Nhập tên sản phẩm.');
    if(!d.brand.trim())throw Error('Nhập thương hiệu.');
    if(!d.price||+d.price<1000)throw Error('Giá cần ít nhất 1.000 đ.');
    if(d.id){
      const p=mineSeller('shopProducts').find(x=>x.id===d.id);
      if(!p)throw Error('Không có quyền sửa sản phẩm này.');
      stx(()=>Object.assign(p,{name:d.name.trim(),brand:d.brand.trim(),category:d.category,price:+d.price,stock:+d.stock,warranty:+d.warranty,description:d.description.trim()}));
      toast('Đã cập nhật sản phẩm.');
    }else{
      const sel=seller();
      const newProduct={id:uid('SP'),sellerId:sel.id,shopId:sel.shopId,name:d.name.trim(),brand:d.brand.trim(),category:d.category,price:+d.price,stock:+d.stock,sold:0,warranty:+d.warranty,description:d.description.trim(),active:true,createdAt:Date.now(),images:[]};
      stx(s=>s.shopProducts.push(newProduct));
      toast('Đã thêm sản phẩm mới.');
    }
    go('offers');
    return true;
  }
  if(name==='update-stock'){
    const p=mineSeller('shopProducts').find(x=>x.id===d.id);
    if(!p)throw Error('Không tìm thấy sản phẩm.');
    if(!Number.isInteger(+d.qty)||+d.qty<0)throw Error('Số lượng không hợp lệ.');
    stx(()=>p.stock=+d.qty);
    inventory();
    toast(`Đã cập nhật tồn kho: ${p.name} → ${d.qty} sản phẩm`);
    return true;
  }
  return false;
}