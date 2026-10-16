import {mineSeller,sdb,stx,seller,uid,money} from './shop-store.js';
import {esc,params,go,link,a,btn,field,select,textarea,submit,form,notice,empty,panel,head,badge,statusBadge,mount,toast,dialog,requireSeller} from './shop-ui.js';
import {models,model as getModel,money as dataMoney} from './data.js';

export function buildRequests(){
  if(!requireSeller())return;
  const statusFilter=params.get('status')||'';
  let list=mineSeller('shopBuildRequests');
  if(statusFilter)list=list.filter(b=>b.status===statusFilter);
  list=list.slice().reverse();

  const counts={
    'Mới':mineSeller('shopBuildRequests').filter(b=>b.status==='Mới').length,
    'Đã gửi báo giá':mineSeller('shopBuildRequests').filter(b=>b.status==='Đã gửi báo giá').length,
    'Đang thương lượng':mineSeller('shopBuildRequests').filter(b=>b.status==='Đang thương lượng').length,
    'Đã chốt':mineSeller('shopBuildRequests').filter(b=>b.status==='Đã chốt').length,
    'Đã hủy báo giá':mineSeller('shopBuildRequests').filter(b=>b.status==='Đã hủy báo giá').length
  };
  const totalAll=mineSeller('shopBuildRequests').length;

  mount('Yêu cầu build',`
    <section class="sa-page-heading">
      <div>
        <div class="sa-breadcrumbs">
          <a href="${link('dashboard')}">Kênh bán</a>
          <span>/</span>
          <span>Yêu cầu build</span>
        </div>
        <h1>Yêu cầu cấu hình build</h1>
        <p>Khách hàng muốn shop tư vấn và báo giá cấu hình máy tính</p>
      </div>
    </section>

    <div class="sa-table-card">
      <div class="sa-filter-tabs">
        <button class="sa-tab ${!statusFilter?'is-active':''}" data-action="build-tab" data-status="">Tất cả <span>${totalAll}</span></button>
        ${Object.entries(counts).map(([s,c])=>`<button class="sa-tab ${statusFilter===s?'is-active':''}" data-action="build-tab" data-status="${esc(s)}">${esc(s)} <span>${c}</span></button>`).join('')}
      </div>

      ${list.length?`
        <div style="padding:16px;display:grid;gap:12px">
          ${list.map(b=>`
            <div class="shop-card">
              <div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px">${statusBadge(b.status)} <span style="color:#94a3b8;font-size:11px">Yêu cầu ${new Date(b.createdAt).toLocaleDateString('vi-VN')}</span></div>
                <strong style="font-size:14px">${esc(b.buyerName)}</strong>
                <p style="margin:4px 0;color:#475569;font-size:13px">Ngân sách: <strong>${money(b.budget)}</strong> · Mục đích: ${esc(b.purpose)}</p>
                <p style="margin:4px 0;color:#94a3b8;font-size:12px">${esc(b.notes)}</p>
                ${b.offers.length?`<p style="margin:4px 0;font-size:12px;color:#475569">Báo giá: ${b.offers.map(o=>{const m=getModel(o.modelId);return esc(m?.name||o.modelId)+' — '+money(o.price);}).join(', ')}</p>`:''}
              </div>
              <div class="stack">
                ${a('Xem & báo giá','build-request-detail',{id:b.id},'primary')}
                ${b.status==='Mới'?btn('Bỏ qua','dismiss-build',b.id):''}
              </div>
            </div>
          `).join('')}
        </div>
      `:`<div class="sa-empty-table">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 9h6m-6 4h6m-6 4h4"/></svg>
          <h3>Không có yêu cầu build</h3>
          <p>Khách hàng chưa gửi yêu cầu tư vấn nào.${statusFilter?' Thử bỏ bộ lọc.':''}</p>
        </div>`}
    </div>
  `);

  document.querySelectorAll('[data-action="build-tab"]').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const s=btn.dataset.status;
      const newParams=new URLSearchParams(location.search);
      if(s)newParams.set('status',s);else newParams.delete('status');
      location.href=link('build-requests',Object.fromEntries(newParams));
    });
  });
}

export function buildRequestDetail(){
  if(!requireSeller())return;
  const b=mineSeller('shopBuildRequests').find(x=>x.id===params.get('id'));
  if(!b){mount('Yêu cầu build',`<div class="sa-empty-table"><h3>Không tìm thấy yêu cầu</h3><p>Yêu cầu không tồn tại.</p>${a('Quay lại','build-requests')}</div>`);return;}

  const allModels=models;
  const catGroups={};
  allModels.forEach(m=>{if(!catGroups[m.category])catGroups[m.category]=[];catGroups[m.category].push(m);});

  mount('Yêu cầu build '+b.id,`
    <section class="sa-page-heading">
      <div>
        <div class="sa-breadcrumbs">
          <a href="${link('dashboard')}">Kênh bán</a>
          <span>/</span>
          <a href="${link('build-requests')}">Yêu cầu build</a>
          <span>/</span>
          <span>${esc(b.id)}</span>
        </div>
        <h1>Báo giá cho ${esc(b.buyerName)}</h1>
        <p>${esc(b.id)}</p>
      </div>
      <div class="sa-page-actions">
        ${a('← Tất cả yêu cầu','build-requests')}
      </div>
    </section>

    <div class="shop-grid">
      <div class="stack">
        ${panel('Thông tin yêu cầu',`
          <dl class="info-dl">
            <dt>Khách hàng</dt><dd>${esc(b.buyerName)}</dd>
            <dt>Ngân sách</dt><dd>${money(b.budget)}</dd>
            <dt>Mục đích</dt><dd>${esc(b.purpose)}</dd>
            <dt>Yêu cầu thêm</dt><dd>${esc(b.notes)}</dd>
            <dt>Trạng thái</dt><dd>${statusBadge(b.status)}</dd>
          </dl>
        `)}

        ${b.offers.length?panel('Báo giá hiện tại',`
          <div class="shop-slot-grid">
            ${b.offers.map((o,i)=>{const m=getModel(o.modelId);return `<div class="shop-slot">
              <div class="shop-slot__code">${m?.category||'?'}</div>
              <div><strong>${esc(m?.name||o.modelId)}</strong><small>Qty: ${o.qty}</small></div>
              <div>${money(o.price*o.qty)}</div>
            </div>`;}).join('')}
          </div>
          <div class="shop-total shop-total--grand"><span>Tổng báo giá</span><strong>${money(b.offers.reduce((s,o)=>s+o.price*o.qty,0))}</strong></div>
        `):''}

        ${b.status!=='Đã chốt'&&b.status!=='Đã hủy báo giá'?panel('Tạo/cập nhật báo giá',form('build-proposal',`
          <input type="hidden" name="buildId" value="${esc(b.id)}">
          ${notice('Chọn linh kiện từ catalogue và thêm vào báo giá. Mỗi nhóm danh mục một linh kiện.')}
          <div id="proposal-slots">
            ${b.offers.length?b.offers.map((o,i)=>{const m=getModel(o.modelId);return renderProposalSlot(i,allModels,o.modelId,o.price,o.qty);}).join(''):renderProposalSlot(0,allModels)}
          </div>
          <div class="cluster">
            ${btn('+ Thêm linh kiện','add-proposal-slot','')}
            ${submit('Gửi báo giá cho khách')}
          </div>
          <input type="hidden" name="slotCount" id="slot-count" value="${Math.max(1,b.offers.length)}">
        `)):''}
      </div>

      <div class="shop-summary">
        ${panel('Phân tích ngân sách',`
          <p>Ngân sách: <strong>${money(b.budget)}</strong></p>
          <p>Báo giá hiện tại: <strong>${money(b.offers.reduce((s,o)=>s+o.price*o.qty,0))}</strong></p>
          ${b.offers.length?`<p style="color:${b.offers.reduce((s,o)=>s+o.price*o.qty,0)>b.budget?'var(--color-red-deep)':'var(--color-teal-deep)'}">
            ${b.offers.reduce((s,o)=>s+o.price*o.qty,0)>b.budget?'⚠️ Vượt ngân sách '+money(b.offers.reduce((s,o)=>s+o.price*o.qty,0)-b.budget):'✓ Trong ngân sách, còn '+money(b.budget-b.offers.reduce((s,o)=>s+o.price*o.qty,0))}
          </p>`:''}
          ${b.status!=='Đã chốt'?`<div class="stack">
            ${b.status==='Đang thương lượng'?btn('Đánh dấu đã chốt','close-build',b.id,'primary'):''}
            ${btn('Hủy yêu cầu này','dismiss-build',b.id,'danger')}
          </div>`:'<p class="muted">Đã chốt.</p>'}
        `)}
      </div>
    </div>
  `);
}

function renderProposalSlot(index,allModels,selectedModel='',price='',qty=1){
  return `<div class="shop-slot" data-slot="${index}">
    <div class="shop-slot__code">${index+1}</div>
    <div>
      <label class="field"><span>Sản phẩm</span>
        <select name="model_${index}" required>
          <option value="">-- Chọn sản phẩm --</option>
          ${allModels.map(m=>`<option value="${esc(m.id)}" ${m.id===selectedModel?'selected':''}>${esc(m.name)} — ${money(m.price)}</option>`).join('')}
        </select>
      </label>
      <div class="two-col">
        <label class="field"><span>Giá báo</span><input type="number" name="price_${index}" value="${price||''}" min="1000" step="1000" required></label>
        <label class="field"><span>Số lượng</span><input type="number" name="qty_${index}" value="${qty}" min="1" step="1" required></label>
      </div>
    </div>
    <button type="button" class="btn" data-action="remove-proposal-slot" data-id="${index}" aria-label="Xóa dòng">×</button>
  </div>`;
}

export function proposalList(){
  if(!requireSeller())return;
  const requests=mineSeller('shopBuildRequests').filter(b=>b.status!=='Mới');

  mount('Báo giá đã gửi',`
    <section class="sa-page-heading">
      <div>
        <div class="sa-breadcrumbs">
          <a href="${link('dashboard')}">Kênh bán</a>
          <span>/</span>
          <span>Báo giá đã gửi</span>
        </div>
        <h1>Danh sách báo giá</h1>
        <p>Các yêu cầu build đã xử lý</p>
      </div>
    </section>

    <div class="sa-table-card">
      ${requests.length?`
        <div style="padding:16px;display:grid;gap:12px">
          ${requests.map(b=>`
            <div class="shop-card">
              <div>
                <div style="display:flex;gap:8px;margin-bottom:6px">${statusBadge(b.status)}</div>
                <strong style="font-size:14px">${esc(b.buyerName)} · ${money(b.budget)}</strong>
                <p style="margin:4px 0;color:#475569;font-size:13px">${esc(b.purpose)} · ${new Date(b.createdAt).toLocaleDateString('vi-VN')}</p>
                ${b.offers.length?`<p style="margin:4px 0;font-size:13px">Báo giá: ${money(b.offers.reduce((s,o)=>s+o.price*o.qty,0))}</p>`:'<p style="margin:4px 0;color:#94a3b8;font-size:12px">Chưa có báo giá</p>'}
              </div>
              ${a('Xem chi tiết','build-request-detail',{id:b.id})}
            </div>
          `).join('')}
        </div>
      `:`<div class="sa-empty-table">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 9h6m-6 4h6m-6 4h4"/></svg>
          <h3>Chưa có báo giá nào</h3>
          <p>Các yêu cầu đã xử lý sẽ xuất hiện ở đây.</p>
          ${a('Xem yêu cầu mới','build-requests','','primary')}
        </div>`}
    </div>
  `);
}

export function proposal(){
  buildRequestDetail();
}

let slotCount=1;

export function action(act,id){
  if(!requireSeller())return true;
  if(act==='add-proposal-slot'){
    const slots=document.getElementById('proposal-slots');
    const countEl=document.getElementById('slot-count');
    if(!slots||!countEl)return true;
    const index=parseInt(countEl.value)||1;
    slots.insertAdjacentHTML('beforeend',renderProposalSlot(index,models));
    countEl.value=String(index+1);
    return true;
  }
  if(act==='remove-proposal-slot'){
    const slot=document.querySelector(`[data-slot="${id}"]`);
    if(slot&&document.querySelectorAll('[data-slot]').length>1)slot.remove();
    return true;
  }
  if(act==='dismiss-build'){
    const b=mineSeller('shopBuildRequests').find(x=>x.id===id);
    if(!b)throw Error('Không tìm thấy yêu cầu.');
    dialog('Hủy yêu cầu build?',`Bỏ qua yêu cầu của ${esc(b.buyerName)}? Không thể hoàn tác.`,()=>{
      stx(()=>b.status='Đã hủy báo giá');
      buildRequests();
      toast('Đã hủy yêu cầu build.');
    });
    return true;
  }
  if(act==='close-build'){
    const b=mineSeller('shopBuildRequests').find(x=>x.id===id);
    if(!b)throw Error('Không tìm thấy yêu cầu.');
    dialog('Đánh dấu đã chốt?','Xác nhận khách hàng đã đồng ý báo giá này?',()=>{
      stx(()=>b.status='Đã chốt');
      buildRequestDetail();
      toast('Đã đánh dấu chốt báo giá.');
    });
    return true;
  }
  return false;
}

export async function submitForm(name,f,d){
  if(!requireSeller())return true;
  if(name==='build-proposal'){
    const b=mineSeller('shopBuildRequests').find(x=>x.id===d.buildId);
    if(!b)throw Error('Không tìm thấy yêu cầu build.');
    const count=parseInt(d.slotCount)||1;
    const offers=[];
    for(let i=0;i<count;i++){
      const modelId=d[`model_${i}`];
      const price=+d[`price_${i}`];
      const qty=+d[`qty_${i}`];
      if(!modelId)throw Error(`Chọn sản phẩm cho dòng ${i+1}.`);
      if(!price||price<1000)throw Error(`Giá dòng ${i+1} không hợp lệ.`);
      if(!qty||qty<1)throw Error(`Số lượng dòng ${i+1} không hợp lệ.`);
      offers.push({modelId,price,qty});
    }
    stx(()=>{b.offers=offers;b.status='Đã gửi báo giá';});
    buildRequestDetail();
    toast('Đã gửi báo giá cho khách hàng.');
    return true;
  }
  return false;
}
