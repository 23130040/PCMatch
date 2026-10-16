import {renderTemplate,esc,page,params,go,link,a,btn,field,textarea,submit,form,notice,panel,statusBadge,mount,toast,dialog,requireSeller} from './shop-ui.js';
import {mineSeller,stx,uid,money} from './shop-store.js';

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

  mount('Đơn hàng',renderTemplate("shop-orders-orders-3", {
    dashboardUrl: link('dashboard'),
    get: esc(params.get('q')||''),
    length: list.length,
    contentContent: !statusFilter?'is-active':'',
    totalAll: totalAll,
    ORDERSTATUSESRows: ORDER_STATUSES.map(s=>renderTemplate("shop-orders-orders-4", {
      statusFilterContent: statusFilter===s?'is-active':'',
      s: esc(s),
      s2: esc(s),
      value: countByStatus[s]||0
    })).join(''),
    lengthContent: list.length?renderTemplate("shop-orders-orders-7", {
      listRows: list.map(o=>renderTemplate("shop-orders-orders-6", {
        id: esc(o.id),
        buyerName: esc(o.buyerName),
        buyerPhone: esc(o.buyerPhone),
        totalMoney: money(o.total),
        shippingService: esc(o.shippingService),
        trackingContent: o.tracking?renderTemplate("shop-orders-orders-5", {
          tracking: esc(o.tracking)
        }):'',
        statusBadge: statusBadge(o.status),
        toLocaleDateString: new Date(o.createdAt).toLocaleDateString('vi-VN'),
        orderLink: a('Chi tiết','order',{id:o.id},'sa-detail-btn')
      })).join('')
    }):renderTemplate("shop-orders-orders-1"),
    lengthContent2: list.length?renderTemplate("shop-orders-orders-2", {
      length: list.length,
      length2: list.length
    }):''
  }));

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
  if(!o){mount('Đơn hàng',renderTemplate("shop-orders-order-1", {
    ordersLink: a('Quay lại','orders')
  }));return;}

  const nextActions=NEXT_ACTIONS[o.status]||[];

  mount('Đơn '+o.id,renderTemplate("shop-orders-order-6", {
    dashboardUrl: link('dashboard'),
    ordersUrl: link('orders'),
    id: esc(o.id),
    id2: esc(o.id),
    toLocaleString: new Date(o.createdAt).toLocaleString('vi-VN'),
    ordersLink: a('← Tất cả đơn','orders'),
    content: notice('Trạng thái hiện tại: '+o.status+(o.status==='Chờ xác nhận'?' · Vui lòng xác nhận hoặc hủy đơn sớm.':''),'info'),
    ThongTinNguoiMuaPanel: panel('Thông tin người mua',renderTemplate("shop-orders-order-8", {
      buyerName: esc(o.buyerName),
      buyerPhone: esc(o.buyerPhone),
      address: esc(o.address),
      shippingService: esc(o.shippingService),
      trackingContent: o.tracking?renderTemplate("shop-orders-order-7", {
        tracking: esc(o.tracking)
      }):''
    })),
    SanPhamTrongDonPanel: panel('Sản phẩm trong đơn',renderTemplate("shop-orders-order-3", {
      itemsRows: o.items.map(i=>renderTemplate("shop-orders-order-2", {
        name: esc(i.name),
        qty: i.qty,
        priceMoney: money(i.price),
        qtyMoney: money(i.qty*i.price)
      })).join(''),
      totalMoney: money(o.total),
      payment: esc(o.payment)
    })),
    LichSuDonHangPanel: panel('Lịch sử đơn hàng',renderTemplate("shop-orders-order-10", {
      timelineRows: o.timeline.map(t=>renderTemplate("shop-orders-order-9", {
        toLocaleString: new Date(t.at).toLocaleString('vi-VN'),
        text: esc(t.text)
      })).join('')
    })),
    XuLyDonHangPanel: panel('Xử lý đơn hàng',renderTemplate("shop-orders-order-5", {
      statusBadge: statusBadge(o.status),
      lengthContent: nextActions.length?renderTemplate("shop-orders-order-12", {
        nextActionsRows: nextActions.map(action=>renderTemplate("shop-orders-order-11", {
          actionContent: action.action==='order-cancel'?'btn--danger':'btn--primary',
          action: action.action,
          id: o.id,
          label: action.label
        })).join('')
      }):renderTemplate("shop-orders-order-4")
    })),
    statusContent: o.status==='Đang xử lý'||o.status==='Đang giao'?panel('Cập nhật vận đơn',form('update-tracking',renderTemplate("shop-orders-order-13", {
      id: esc(o.id),
      trackingField: field('Mã vận đơn','tracking',o.tracking||''),
      content: submit('Lưu mã vận đơn')
    }))):'',
    GhiChuNoiBoPanel: panel('Ghi chú nội bộ',form('order-note',renderTemplate("shop-orders-order-14", {
      id: esc(o.id),
      noteField: textarea('Ghi chú','note',o.note||'','maxlength="500" placeholder="Ghi chú nội bộ về đơn hàng..."'),
      content: submit('Lưu ghi chú')
    })))
  }));
}

export function fulfillment(){
  if(!requireSeller())return;
  const delivering=mineSeller('shopOrders').filter(o=>['Đang giao','Chờ hoàn hàng'].includes(o.status));
  const confirmed=mineSeller('shopOrders').filter(o=>o.status==='Đang xử lý');

  mount('Giao nhận',renderTemplate("shop-orders-fulfillment-3", {
    dashboardUrl: link('dashboard'),
    contentRows: [
        {label:'Chờ lấy hàng',count:confirmed.length,cls:'sa-kpi-card--blue'},
        {label:'Đang giao',count:delivering.filter(o=>o.status==='Đang giao').length,cls:'sa-kpi-card--sky'},
        {label:'Chờ hoàn hàng',count:delivering.filter(o=>o.status==='Chờ hoàn hàng').length,cls:'sa-kpi-card--amber'},
        {label:'Đã giao hôm nay',count:mineSeller('shopOrders').filter(o=>o.status==='Đã giao'&&Date.now()-o.deliveredAt<86400000).length,cls:'sa-kpi-card--rose'}
      ].map(s=>renderTemplate("shop-orders-fulfillment-4", {
      cls: s.cls,
      toUpperCase: esc(s.label).toUpperCase(),
      count: s.count
    })).join(''),
    lengthContent: confirmed.length?renderTemplate("shop-orders-fulfillment-5", {
      length: confirmed.length,
      confirmedRows: confirmed.map(o=>renderTemplate("shop-orders-fulfillment-1", {
        id: esc(o.id),
        buyerName: esc(o.buyerName),
        address: esc(o.address),
        itemsRows: o.items.map(i=>esc(i.name)+' × '+i.qty).join(' · '),
        totalMoney: money(o.total),
        shippingService: esc(o.shippingService),
        orderShipButton: btn('Bắt đầu giao','order-ship',o.id,'primary'),
        orderLink: a('Chi tiết','order',{id:o.id})
      })).join('')
    }):'',
    lengthContent2: delivering.filter(o=>o.status==='Đang giao').length?renderTemplate("shop-orders-fulfillment-6", {
      length: delivering.filter(o=>o.status==='Đang giao').length,
      filterRows: delivering.filter(o=>o.status==='Đang giao').map(o=>renderTemplate("shop-orders-fulfillment-2", {
        id: esc(o.id),
        buyerName: esc(o.buyerName),
        address: esc(o.address),
        tracking: esc(o.tracking||'Chưa có'),
        orderDeliverButton: btn('Đã giao','order-deliver',o.id,'primary'),
        orderFailButton: btn('Giao thất bại','order-fail',o.id,'danger'),
        orderLink: a('Chi tiết','order',{id:o.id})
      })).join('')
    }):''
  }));
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
      if(page==='orders')orders();
      else if(page==='fulfillment')fulfillment();
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
