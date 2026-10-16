import {renderTemplate,esc,params,link,a,btn,submit,form,notice,panel,statusBadge,mount,toast,dialog,requireSeller} from './shop-ui.js';
import {mineSeller,stx,money} from './shop-store.js';
import {models,model as getModel} from './shop-data.js';

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

  mount('Yêu cầu build',renderTemplate("shop-builds-buildRequests-4", {
    dashboardUrl: link('dashboard'),
    contentContent: !statusFilter?'is-active':'',
    totalAll: totalAll,
    entriesRows: Object.entries(counts).map(([s,c])=>renderTemplate("shop-builds-buildRequests-5", {
      statusFilterContent: statusFilter===s?'is-active':'',
      s: esc(s),
      s2: esc(s),
      c: c
    })).join(''),
    lengthContent: list.length?renderTemplate("shop-builds-buildRequests-6", {
      listRows: list.map(b=>renderTemplate("shop-builds-buildRequests-2", {
        statusBadge: statusBadge(b.status),
        toLocaleDateString: new Date(b.createdAt).toLocaleDateString('vi-VN'),
        buyerName: esc(b.buyerName),
        budgetMoney: money(b.budget),
        purpose: esc(b.purpose),
        notes: esc(b.notes),
        lengthContent: b.offers.length?renderTemplate("shop-builds-buildRequests-1", {
          offersRows: b.offers.map(o=>{const m=getModel(o.modelId);return esc(m?.name||o.modelId)+' — '+money(o.price);}).join(', ')
        }):'',
        buildRequestDetailLink: a('Xem & báo giá','build-request-detail',{id:b.id},'primary'),
        statusContent: b.status==='Mới'?btn('Bỏ qua','dismiss-build',b.id):''
      })).join('')
    }):renderTemplate("shop-builds-buildRequests-3", {
      statusFilterContent: statusFilter?' Thử bỏ bộ lọc.':''
    })
  }));

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
  if(!b){mount('Yêu cầu build',renderTemplate("shop-builds-buildRequestDetail-1", {
    buildRequestsLink: a('Quay lại','build-requests')
  }));return;}

  const allModels=models;

  mount('Yêu cầu build '+b.id,renderTemplate("shop-builds-buildRequestDetail-5", {
    dashboardUrl: link('dashboard'),
    buildRequestsUrl: link('build-requests'),
    id: esc(b.id),
    buyerName: esc(b.buyerName),
    id2: esc(b.id),
    buildRequestsLink: a('← Tất cả yêu cầu','build-requests'),
    ThongTinYeuCauPanel: panel('Thông tin yêu cầu',renderTemplate("shop-builds-buildRequestDetail-6", {
      buyerName: esc(b.buyerName),
      budgetMoney: money(b.budget),
      purpose: esc(b.purpose),
      notes: esc(b.notes),
      statusBadge: statusBadge(b.status)
    })),
    lengthContent: b.offers.length?panel('Báo giá hiện tại',renderTemplate("shop-builds-buildRequestDetail-8", {
      offersRows: b.offers.map((o,i)=>{const m=getModel(o.modelId);return renderTemplate("shop-builds-buildRequestDetail-7", {
        category: m?.category||'?',
        name: esc(m?.name||o.modelId),
        qty: o.qty,
        priceMoney: money(o.price*o.qty)
      });}).join(''),
      reduceMoney: money(b.offers.reduce((s,o)=>s+o.price*o.qty,0))
    })):'',
    statusContent: b.status!=='Đã chốt'&&b.status!=='Đã hủy báo giá'?panel('Tạo/cập nhật báo giá',form('build-proposal',renderTemplate("shop-builds-buildRequestDetail-9", {
      id: esc(b.id),
      content: notice('Chọn linh kiện từ catalogue và thêm vào báo giá. Mỗi nhóm danh mục một linh kiện.'),
      lengthContent: b.offers.length?b.offers.map((o,i)=>{const m=getModel(o.modelId);return renderProposalSlot(i,allModels,o.modelId,o.price,o.qty);}).join(''):renderProposalSlot(0,allModels),
      addProposalSlotButton: btn('+ Thêm linh kiện','add-proposal-slot',''),
      content2: submit('Gửi báo giá cho khách'),
      max: Math.max(1,b.offers.length)
    }))):'',
    PhanTichNganSachPanel: panel('Phân tích ngân sách',renderTemplate("shop-builds-buildRequestDetail-4", {
      budgetMoney: money(b.budget),
      reduceMoney: money(b.offers.reduce((s,o)=>s+o.price*o.qty,0)),
      lengthContent: b.offers.length?renderTemplate("shop-builds-buildRequestDetail-2", {
        reduceContent: b.offers.reduce((s,o)=>s+o.price*o.qty,0)>b.budget?'var(--color-red-deep)':'var(--color-teal-deep)',
        reduceContent2: b.offers.reduce((s,o)=>s+o.price*o.qty,0)>b.budget?'⚠️ Vượt ngân sách '+money(b.offers.reduce((s,o)=>s+o.price*o.qty,0)-b.budget):'✓ Trong ngân sách, còn '+money(b.budget-b.offers.reduce((s,o)=>s+o.price*o.qty,0))
      }):'',
      statusContent: b.status!=='Đã chốt'?renderTemplate("shop-builds-buildRequestDetail-10", {
        statusContent: b.status==='Đang thương lượng'?btn('Đánh dấu đã chốt','close-build',b.id,'primary'):'',
        dismissBuildButton: btn('Hủy yêu cầu này','dismiss-build',b.id,'danger')
      }):renderTemplate("shop-builds-buildRequestDetail-3")
    }))
  }));
}

function renderProposalSlot(index,allModels,selectedModel='',price='',qty=1){
  return renderTemplate("shop-builds-renderProposalSlot-2", {
    index: index,
    index2: index+1,
    index3: index,
    allModelsRows: allModels.map(m=>renderTemplate("shop-builds-renderProposalSlot-1", {
      id: esc(m.id),
      idContent: m.id===selectedModel?'selected':'',
      name: esc(m.name),
      priceMoney: money(m.price)
    })).join(''),
    index4: index,
    price: price||'',
    index5: index,
    qty: qty,
    index6: index
  });
}

export function proposalList(){
  if(!requireSeller())return;
  const requests=mineSeller('shopBuildRequests').filter(b=>b.status!=='Mới');

  mount('Báo giá đã gửi',renderTemplate("shop-builds-proposalList-5", {
    dashboardUrl: link('dashboard'),
    lengthContent: requests.length?renderTemplate("shop-builds-proposalList-6", {
      requestsRows: requests.map(b=>renderTemplate("shop-builds-proposalList-3", {
        statusBadge: statusBadge(b.status),
        buyerName: esc(b.buyerName),
        budgetMoney: money(b.budget),
        purpose: esc(b.purpose),
        toLocaleDateString: new Date(b.createdAt).toLocaleDateString('vi-VN'),
        lengthContent: b.offers.length?renderTemplate("shop-builds-proposalList-1", {
          reduceMoney: money(b.offers.reduce((s,o)=>s+o.price*o.qty,0))
        }):renderTemplate("shop-builds-proposalList-2"),
        buildRequestDetailLink: a('Xem chi tiết','build-request-detail',{id:b.id})
      })).join('')
    }):renderTemplate("shop-builds-proposalList-4", {
      buildRequestsLink: a('Xem yêu cầu mới','build-requests','','primary')
    })
  }));
}

export function proposal(){
  buildRequestDetail();
}

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
    const offers=[];
    // Removed rows leave gaps in their indices; process only the remaining rows.
    for(const slot of f.querySelectorAll('[data-slot]')){
      const i=Number(slot.dataset.slot);
      const modelId=d[`model_${i}`];
      const price=+d[`price_${i}`];
      const qty=+d[`qty_${i}`];
      if(!getModel(modelId))throw Error(`Chọn sản phẩm cho dòng ${i+1}.`);
      if(!Number.isFinite(price)||price<1000)throw Error(`Giá dòng ${i+1} không hợp lệ.`);
      if(!Number.isSafeInteger(qty)||qty<1)throw Error(`Số lượng dòng ${i+1} không hợp lệ.`);
      offers.push({modelId,price,qty});
    }
    if(!offers.length)throw Error('Báo giá cần ít nhất một linh kiện.');
    stx(()=>{b.offers=offers;b.status='Đã gửi báo giá';});
    buildRequestDetail();
    toast('Đã gửi báo giá cho khách hàng.');
    return true;
  }
  return false;
}
