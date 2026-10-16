import {mineSeller,sdb,stx,seller,uid,money} from './shop-store.js';
import {esc,params,go,link,a,btn,field,select,textarea,submit,form,notice,empty,panel,head,badge,statusBadge,mount,toast,dialog,operation,requireSeller} from './shop-ui.js';

const ORDER_STATUSES=['Chờ xác nhận','Đang xử lý','Đang giao','Đã giao','Đã hủy','Chờ hoàn hàng','Đã hoàn hàng'];
const NEXT_ACTIONS={
  'Chờ xác nhận':[{label:'Xác nhận đơn',next:'Đang xử lý',action:'order-confirm'}],
  'Đang xử lý':[{label:'Bắt đầu giao hàng',next:'Đang giao',action:'order-ship'},{label:'Hủy đơn',next:'Đã hủy',action:'order-cancel'}],
  'Đang giao':[{label:'Xác nhận đã giao',next:'Đã giao',action:'order-deliver'},{label:'Giao thất bại',next:'Chờ hoàn hàng',action:'order-fail'}],
  'Chờ hoàn hàng':[{label:'Đã nhận lại hàng',next:'Đã hoàn hàng',action:'order-return'}],
};

export function orders(){
  if(!requireSeller())return;
  const statusFilter=params.get('status')||'';
  const q=(params.get('q')||'').toLowerCase();
  let list=mineSeller('shopOrders');
  if(statusFilter)list=list.filter(o=>o.status===statusFilter);
  if(q)list=list.filter(o=>o.id.toLowerCase().includes(q)||o.buyerName.toLowerCase().includes(q));
  list=list.slice().reverse();

  const countByStatus=Object.fromEntries(ORDER_STATUSES.map(s=>[s,mineSeller('shopOrders').filter(o=>o.status===s).length]));
  const totalAll=mineSeller('shopOrders').length;

  mount('Đơn hàng',`
    <section class="sa-page-heading">
      <div>
        <div class="sa-breadcrumbs">
          <a href="${link('dashboard')}">Kênh bán</a>
          <span>/</span>
          <span>Quản lý đơn hàng</span>
        </div>
        <h1>Quản lý đơn hàng</h1>
        <p>Theo dõi và xử lý tất cả đơn hàng của shop</p>
      </div>
    </section>

    <div class="sa-table-card">
      <div class="sa-table-toolbar">
        <div class="sa-table-filters">
          <label class="sa-table-search">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            <input type="text" id="order-search-input" placeholder="Tìm mã đơn hoặc tên khách..." value="${esc(params.get('q')||'')}">
          </label>
        </div>
        <span class="sa-result-count"><strong>${list.length}</strong> đơn khớp bộ lọc</span>
      </div>

      <div class="sa-filter-tabs">
        <button class="sa-tab ${!statusFilter?'is-active':''}" data-action="order-filter-tab" data-status="">Tất cả <span>${totalAll}</span></button>
        ${ORDER_STATUSES.map(s=>`<button class="sa-tab ${statusFilter===s?'is-active':''}" data-action="order-filter-tab" data-status="${esc(s)}">${esc(s)} <span>${countByStatus[s]||0}</span></button>`).join('')}
      </div>

      <div class="table-scroll">
        ${list.length?`<table>
          <thead><tr>
            <th>MÃ ĐƠN</th><th>KHÁCH HÀNG</th><th>TỔNG TIỀN</th><th>GIAO HÀNG</th><th>TRẠNG THÁI</th><th>NGÀY TẠO</th><th>THAO TÁC</th>
          </tr></thead>
          <tbody>
            ${list.map(o=>`<tr>
              <td><strong>${esc(o.id)}</strong></td>
              <td><strong>${esc(o.buyerName)}</strong><small>${esc(o.buyerPhone)}</small></td>
              <td><strong>${money(o.total)}</strong></td>
              <td><small>${esc(o.shippingService)}</small>${o.tracking?'<br><small>'+esc(o.tracking)+'</small>':''}</td>
              <td>${statusBadge(o.status)}</td>
              <td><small>${new Date(o.createdAt).toLocaleDateString('vi-VN')}</small></td>
              <td><div class="sa-table-actions">${a('Chi tiết','order',{id:o.id},'sa-detail-btn')}</div></td>
            </tr>`).join('')}
          </tbody>
        </table>`:`<div class="sa-empty-table">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 9h6m-6 4h6m-6 4h4"/></svg>
          <h3>Không có đơn hàng</h3>
          <p>Chưa có đơn nào phù hợp bộ lọc.</p>
        </div>`}
      </div>

      ${list.length?`<footer class="sa-table-pagination">
        <p>Hiển thị <strong>1 - ${list.length}</strong> trên <strong>${list.length}</strong> bản ghi</p>
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
  `);

  // Filter tabs
  document.querySelectorAll('[data-action="order-filter-tab"]').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const s=btn.dataset.status;
      const newParams=new URLSearchParams(location.search);
      if(s)newParams.set('status',s);else newParams.delete('status');
      newParams.delete('q');
      location.href=link('orders',Object.fromEntries(newParams));
    });
  });
  // Search inline
  const si=document.getElementById('order-search-input');
  if(si){
    si.addEventListener('keydown',e=>{
      if(e.key==='Enter'){
        const newParams=new URLSearchParams(location.search);
        if(si.value.trim())newParams.set('q',si.value.trim());else newParams.delete('q');
        location.href=link('orders',Object.fromEntries(newParams));
      }
    });
  }
}

export function order(){
  if(!requireSeller())return;
  const o=mineSeller('shopOrders').find(x=>x.id===params.get('id'));
  if(!o){mount('Đơn hàng',`<div class="sa-empty-table" style="padding:60px 20px"><h3>Không tìm thấy đơn hàng</h3><p>Đơn không tồn tại hoặc không thuộc shop của bạn.</p>${a('Quay lại','orders')}</div>`);return;}

  const nextActions=NEXT_ACTIONS[o.status]||[];

  mount('Đơn '+o.id,`
    <section class="sa-page-heading">
      <div>
        <div class="sa-breadcrumbs">
          <a href="${link('dashboard')}">Kênh bán</a>
          <span>/</span>
          <a href="${link('orders')}">Đơn hàng</a>
          <span>/</span>
          <span>${esc(o.id)}</span>
        </div>
        <h1>${esc(o.id)}</h1>
        <p>${new Date(o.createdAt).toLocaleString('vi-VN')}</p>
      </div>
      <div class="sa-page-actions">
        ${a('← Tất cả đơn','orders')}
      </div>
    </section>

    ${notice('Trạng thái hiện tại: '+o.status+(o.status==='Chờ xác nhận'?' · Vui lòng xác nhận hoặc hủy đơn sớm.':''),'info')}

    <div class="shop-grid">
      <div class="stack">
        ${panel('Thông tin người mua',`
          <dl class="info-dl">
            <dt>Khách hàng</dt><dd>${esc(o.buyerName)}</dd>
            <dt>Điện thoại</dt><dd>${esc(o.buyerPhone)}</dd>
            <dt>Địa chỉ</dt><dd>${esc(o.address)}</dd>
            <dt>Dịch vụ giao</dt><dd>${esc(o.shippingService)}</dd>
            ${o.tracking?`<dt>Mã vận đơn</dt><dd>${esc(o.tracking)}</dd>`:''}
          </dl>
        `)}

        ${panel('Sản phẩm trong đơn',`
          <div class="shop-order-items">
            ${o.items.map(i=>`<div class="shop-order-item">
              <div><strong>${esc(i.name)}</strong><p>${i.qty} × ${money(i.price)} = ${money(i.qty*i.price)}</p></div>
            </div>`).join('')}
          </div>
          <div class="shop-total shop-total--grand"><span>Tổng đơn</span><strong>${money(o.total)}</strong></div>
          <p><small>Thanh toán: ${esc(o.payment)}</small></p>
        `)}

        ${panel('Lịch sử đơn hàng',`
          <ul class="shop-timeline">
            ${o.timeline.map(t=>`<li><strong>${new Date(t.at).toLocaleString('vi-VN')}</strong><span>${esc(t.text)}</span></li>`).join('')}
          </ul>
        `)}
      </div>

      <div class="shop-summary stack">
        ${panel('Xử lý đơn hàng',`
          <p>Trạng thái: ${statusBadge(o.status)}</p>
          ${nextActions.length?`<div class="stack">
            ${nextActions.map(action=>`<button type="button" class="btn ${action.action==='order-cancel'?'btn--danger':'btn--primary'}" data-action="${action.action}" data-id="${o.id}">${action.label}</button>`).join('')}
          </div>`:'<p class="muted">Không có hành động tiếp theo.</p>'}
        `)}

        ${o.status==='Đang xử lý'||o.status==='Đang giao'?panel('Cập nhật vận đơn',form('update-tracking',`
          <input type="hidden" name="orderId" value="${esc(o.id)}">
          ${field('Mã vận đơn','tracking',o.tracking||'')}
          ${submit('Lưu mã vận đơn')}
        `)):''}

        ${panel('Ghi chú nội bộ',form('order-note',`
          <input type="hidden" name="orderId" value="${esc(o.id)}">
          ${textarea('Ghi chú','note',o.note||'','maxlength="500" placeholder="Ghi chú nội bộ về đơn hàng..."')}
          ${submit('Lưu ghi chú')}
        `))}
      </div>
    </div>
  `);
}

export function fulfillment(){
  if(!requireSeller())return;
  const delivering=mineSeller('shopOrders').filter(o=>['Đang giao','Chờ hoàn hàng'].includes(o.status));
  const confirmed=mineSeller('shopOrders').filter(o=>o.status==='Đang xử lý');

  mount('Giao nhận',`
    <section class="sa-page-heading">
      <div>
        <div class="sa-breadcrumbs">
          <a href="${link('dashboard')}">Kênh bán</a>
          <span>/</span>
          <span>Giao nhận</span>
        </div>
        <h1>Quản lý giao nhận</h1>
        <p>Theo dõi các đơn đang trong quá trình giao hàng</p>
      </div>
    </section>

    <section class="sa-kpi-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:24px">
      ${[
        {label:'Chờ lấy hàng',count:confirmed.length,cls:'sa-kpi-card--blue'},
        {label:'Đang giao',count:delivering.filter(o=>o.status==='Đang giao').length,cls:'sa-kpi-card--sky'},
        {label:'Chờ hoàn hàng',count:delivering.filter(o=>o.status==='Chờ hoàn hàng').length,cls:'sa-kpi-card--amber'},
        {label:'Đã giao hôm nay',count:mineSeller('shopOrders').filter(o=>o.status==='Đã giao'&&Date.now()-o.deliveredAt<86400000).length,cls:'sa-kpi-card--rose'}
      ].map(s=>`<article class="sa-kpi-card ${s.cls}">
        <h2>${esc(s.label).toUpperCase()}</h2>
        <div class="sa-kpi-value"><strong>${s.count}</strong><span>đơn</span></div>
      </article>`).join('')}
    </section>

    ${confirmed.length?`
      <div class="sa-table-card" style="margin-bottom:20px">
        <div class="sa-table-toolbar"><h3 style="margin:0;font-size:14px;font-weight:600;color:#0f172a">Cần chuẩn bị hàng (${confirmed.length})</h3></div>
        <div style="padding:12px 16px;display:grid;gap:12px">
          ${confirmed.map(o=>`
            <div class="shop-card">
              <div>
                <h3>${esc(o.id)}</h3>
                <p>${esc(o.buyerName)} · ${esc(o.address)}</p>
                <p>${o.items.map(i=>esc(i.name)+' × '+i.qty).join(' · ')}</p>
                <p>${money(o.total)} · ${esc(o.shippingService)}</p>
              </div>
              <div class="stack">
                ${btn('Bắt đầu giao','order-ship',o.id,'primary')}
                ${a('Chi tiết','order',{id:o.id})}
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `:''}

    ${delivering.filter(o=>o.status==='Đang giao').length?`
      <div class="sa-table-card">
        <div class="sa-table-toolbar"><h3 style="margin:0;font-size:14px;font-weight:600;color:#0f172a">Đang giao (${delivering.filter(o=>o.status==='Đang giao').length})</h3></div>
        <div style="padding:12px 16px;display:grid;gap:12px">
          ${delivering.filter(o=>o.status==='Đang giao').map(o=>`
            <div class="shop-card">
              <div>
                <h3>${esc(o.id)}</h3>
                <p>${esc(o.buyerName)} · ${esc(o.address)}</p>
                <p>Vận đơn: ${o.tracking||'Chưa có'}</p>
              </div>
              <div class="stack">
                ${btn('Đã giao','order-deliver',o.id,'primary')}
                ${btn('Giao thất bại','order-fail',o.id,'danger')}
                ${a('Chi tiết','order',{id:o.id})}
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `:''}
  `);
}

export function action(act,id){
  if(!requireSeller())return true;
  const o=mineSeller('shopOrders').find(x=>x.id===id);
  if(['order-confirm','order-ship','order-deliver','order-fail','order-cancel','order-return'].includes(act)){
    if(!o)throw Error('Không tìm thấy đơn hàng.');
    const transitions={
      'order-confirm':{from:'Chờ xác nhận',to:'Đang xử lý',text:'Shop xác nhận đơn'},
      'order-ship':{from:'Đang xử lý',to:'Đang giao',text:'Bắt đầu giao hàng',tracking:true},
      'order-deliver':{from:'Đang giao',to:'Đã giao',text:'Giao hàng thành công',delivered:true},
      'order-fail':{from:'Đang giao',to:'Chờ hoàn hàng',text:'Giao thất bại — đang hoàn'},
      'order-cancel':{from:'Đang xử lý',to:'Đã hủy',text:'Shop hủy đơn hàng'},
      'order-return':{from:'Chờ hoàn hàng',to:'Đã hoàn hàng',text:'Đã nhận lại hàng'}
    };
    const t=transitions[act];
    if(o.status!==t.from)throw Error('Trạng thái đơn không phù hợp để thực hiện thao tác này.');
    dialog(`${t.text}?`,`Đơn ${o.id} của ${esc(o.buyerName)} sẽ chuyển sang "${t.to}".`,()=>{
      stx(()=>{
        o.status=t.to;
        if(t.tracking&&!o.tracking)o.tracking='SHIP-'+uid('TR');
        if(t.delivered)o.deliveredAt=Date.now();
        o.timeline.push({at:Date.now(),text:t.text});
      });
      if(location.href.includes('order='))orders();
      else order();
      toast(t.text+'.');
    });
    return true;
  }
  return false;
}

export async function submitForm(name,f,d){
  if(!requireSeller())return true;
  if(name==='order-filter'){go('orders',Object.fromEntries(Object.entries(d).filter(([,v])=>v)));return true;}
  if(name==='update-tracking'){
    const o=mineSeller('shopOrders').find(x=>x.id===d.orderId);
    if(!o)throw Error('Không tìm thấy đơn hàng.');
    if(!d.tracking.trim())throw Error('Nhập mã vận đơn.');
    stx(()=>{o.tracking=d.tracking.trim();o.timeline.push({at:Date.now(),text:'Cập nhật mã vận đơn: '+d.tracking.trim()});});
    order();
    toast('Đã cập nhật mã vận đơn.');
    return true;
  }
  if(name==='order-note'){
    const o=mineSeller('shopOrders').find(x=>x.id===d.orderId);
    if(!o)throw Error('Không tìm thấy đơn hàng.');
    stx(()=>o.note=d.note.trim());
    toast('Đã lưu ghi chú.');
    return true;
  }
  return false;
}
