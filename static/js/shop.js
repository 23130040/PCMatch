import {categories,models,model,shop,money,regions} from './data.js';
import {db,tx,uid,currentOffer,clone} from './store.js';
import {compatibility} from './builds.js';
import {appendRefund,refundsFor,discountForSerials} from './aftersale-data.js';
import {pageName,pageUrl} from './routing.js';

const SHOP_ID='BP';
const qs=new URLSearchParams(location.search);
const page=pageName;
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmtDate=v=>v?new Date(v).toLocaleString('vi-VN',{dateStyle:'short',timeStyle:'short'}):'—';
const link=(name,p={})=>pageUrl('shop',name,p);
const closedOrderStates=['Đã hủy','Đã giao','Hoàn tất','Đã hoàn hàng'];

function statusClass(s){
 if(/Đã giao|Hoàn tất|Đã chọn|Đang bán|Khả dụng|Đã gửi|Chuẩn bị/.test(s))return 'status--ok';
 if(/Chờ|Cần|Sắp|Thấp|Hết hạn|Đang giao|Chưa/.test(s))return 'status--warn';
 if(/Từ chối|Hủy|Không tương thích|Thất bại|Đã rút/.test(s))return 'status--bad';
 return 'status--info';
}
const badge=s=>'<span class="status '+statusClass(s)+'">'+esc(s)+'</span>';
const button=(label,action,id='',kind='secondary',extra='')=>'<button type="button" class="btn btn--'+kind+'" data-action="'+action+'"'+(id?' data-id="'+esc(id)+'"':'')+' '+extra+'>'+esc(label)+'</button>';
const panel=(title,body,extra='')=>'<section class="panel panel--padded">'+(title?'<div class="panel__head"><div><h2 style="font-size:var(--text-xl)">'+esc(title)+'</h2>'+extra+'</div></div>':'')+body+'</section>';
const head=(title,desc,actions='')=>'<div class="page-head"><div><h1>'+esc(title)+'</h1><p>'+desc+'</p></div><div class="cluster">'+actions+'</div></div>';

function seed(){
 tx(s=>{
  s.shopMeta||={};
  s.shopMeta.packing||={};
  s.shopMeta.inventoryLog||=[];
  s.shopMeta.proposalDrafts||={};

  if(s.overrides['BP-CPU-7700']===undefined)s.overrides['BP-CPU-7700']={active:false,stock:0};
  if(s.overrides['BP-COOL-AK']===undefined)s.overrides['BP-COOL-AK']={active:false,stock:0};
  if(s.overrides['BP-GPU-4060']===undefined)s.overrides['BP-GPU-4060']={stock:2};

  const needsFallback=!s.requests.length&&!s.proposals.length&&!s.orders.length;
  if(!needsFallback)return;

  const userId='USER-DEMO-MINH';
  if(!s.users.some(u=>u.id===userId))s.users.push({id:userId,name:'Nguyễn Minh',email:'minh.demo@pcmatch.local',phone:'0900000128'});
  const req={
   id:'BR-260916-018',userId,version:1,status:'open',purpose:'Gaming 2K + lập trình',budget:20000000,
   scope:'CPU, mainboard, RAM, GPU, SSD, PSU, case',owned:'Đã có màn hình 2K, bàn phím và chuột',region:'HCM',assembly:true,
   accessories:'no',deadline:new Date(Date.now()+5*86400000).toISOString().slice(0,10),
   messages:[
    {author:'Nguyễn Minh',role:'buyer',shopId:SHOP_ID,text:'Mình ưu tiên case thoáng, không cần RGB. Tổng vẫn giữ dưới 20 triệu giúp mình nhé.',at:Date.now()-35*60000},
    {author:'BuildPro Sài Gòn',role:'shop',shopId:SHOP_ID,text:'Shop đã nhận yêu cầu. Mình sẽ kiểm tra lại case và nguồn trước khi gửi báo giá.',at:Date.now()-28*60000}
   ]
  };
  s.requests.push(req);
  const mids=['CPU-12400','MB-B660','RAM-C16','GPU-4060','SSD-MP44','PSU-550','CASE-MINI'];
  s.proposals.push({
   id:'PR-BP-260916-018',userId,requestId:req.id,requestVersion:1,version:1,shopId:SHOP_ID,status:'Cần sửa',
   sentAt:Date.now()-24*60000,expires:Date.now()+18*3600000,
   items:mids.map(mid=>{const o=currentOffer(SHOP_ID+'-'+mid);return {offerId:o.id,qty:1,price:o.price,warranty:o.warranty};}),
   fee:65000,assembly:150000,note:'Ưu tiên hiệu năng trong ngân sách.',
   feedback:[{version:1,text:'Đổi case thoáng hơn nhưng giữ tổng dưới 20 triệu.',at:Date.now()-20*60000}]
  });

  const items=['CPU-7600','MB-B650','SSD-SN770'].map(mid=>{const o=currentOffer(SHOP_ID+'-'+mid),m=model(mid);return {id:uid('OI'),offerId:o.id,modelId:m.id,name:m.name,qty:1,price:o.price,warranty:o.warranty,serial:'',serials:[],policy:'Tiếp nhận tại BuildPro Sài Gòn; bảo hành theo tin bán.'};});
  const subtotal=items.reduce((a,i)=>a+i.price,0),discount=200000,fee=65000,total=subtotal-discount+fee;
  s.orders.push({
   id:'PCM-260916-014',intentId:'SHOP-260916',userId,at:Date.now()-42*60000,proposalId:null,requestId:null,voucher:null,
   address:{name:'Nguyễn Minh',phone:'0900000128',detail:'72 Nguyễn Thị Minh Khai, Phường Xuân Hòa',region:'HCM'},
   payment:'paid',paymentId:'PAY-260916-771',total,subtotal,fee,discount,assembly:0,
   suborders:[{id:'SUB-BP-002',shopId:SHOP_ID,status:'Chờ shop xác nhận',shippingStatus:'Chưa tạo vận đơn',subtotal,fee,deliveryService:'standard',discount,assembly:0,total,timeline:[{at:Date.now()-42*60000,text:'Thanh toán thành công; chờ shop xác nhận'}],items}]
  });

  s.shopMeta.inventoryLog.unshift(
   {offerId:'BP-GPU-4060',before:4,after:2,delta:-2,reason:'Xuất cho đơn hàng',at:Date.now()-70*60000},
   {offerId:'BP-SSD-SN770',before:7,after:10,delta:3,reason:'Nhập thêm hàng',at:Date.now()-140*60000}
  );
 });
}
seed();

const shopInfo=shop(SHOP_ID);
const bpOffers=()=>models.map(m=>currentOffer(SHOP_ID+'-'+m.id)).filter(Boolean);
const liveRequests=()=>db().requests.filter(r=>r.status==='open'&&new Date(r.deadline+'T23:59:59')>new Date());
const proposals=()=>db().proposals.filter(p=>p.shopId===SHOP_ID);
const suborders=()=>db().orders.flatMap(o=>o.suborders.filter(s=>s.shopId===SHOP_ID).map(s=>({order:o,sub:s})));
const aftersalesCases=()=>db().cases.filter(c=>c.shopId===SHOP_ID&&['return','warranty','complaint'].includes(c.type));
const caseTypeLabel=t=>({return:'Đổi/trả',warranty:'Bảo hành',complaint:'Khiếu nại giao dịch'}[t]||t);
const caseClosed=c=>['Đã hoàn tiền','Đã nhận lại sản phẩm'].includes(c.status)||String(c.status||'').startsWith('Từ chối');
const caseContext=c=>{
 const order=db().orders.find(o=>o.id===c.orderId);
 const sub=order?.suborders.find(s=>s.id===c.subId&&s.shopId===SHOP_ID);
 const item=sub?.items.find(i=>i.id===c.itemId);
 return {order,sub,item};
};
const buyerNameById=id=>db().users.find(u=>u.id===id)?.name||'Người mua';
const buyerName=r=>buyerNameById(r.userId);
const proposalTotal=p=>p.items.reduce((sum,i)=>sum+i.price*i.qty,0)+(p.fee||0)+(p.assembly||0);
const activeReservation=s=>!closedOrderStates.includes(s.status);
const reservedFor=offerId=>suborders().filter(({sub})=>activeReservation(sub)).reduce((sum,{sub})=>sum+sub.items.filter(i=>i.offerId===offerId).reduce((a,i)=>a+i.qty,0),0);
const availableFor=offerId=>Math.max(0,(currentOffer(offerId)?.stock||0)-reservedFor(offerId));
const proposalState=p=>{
 if(['Đã rút','Đã thay thế','Đã chọn'].includes(p.status))return p.status;
 if(p.expires&&p.expires<=Date.now())return 'Hết hạn';
 return p.status||'Đã gửi';
};
const proposalHistory=(p)=>proposals().filter(x=>x.requestId===p.requestId&&x.shopId===p.shopId).sort((a,b)=>a.version-b.version);
const latestProposalForRequest=r=>proposals().filter(p=>p.requestId===r.id&&p.requestVersion===r.version).sort((a,b)=>b.version-a.version)[0];
const orderForProposal=p=>db().orders.find(o=>o.proposalId===p.id);
const remainingMs=r=>new Date(r.deadline+'T23:59:59').getTime()-Date.now();
const remainingLabel=r=>{const ms=remainingMs(r);if(ms<=0)return 'Hết hạn';const h=Math.ceil(ms/3600000);return h<48?'Còn '+h+' giờ':'Còn '+Math.ceil(h/24)+' ngày';};
const requestSignals=r=>{
 const list=[];
 if(r.region===shopInfo.region)list.push('Cùng khu vực');
 if(r.assembly)list.push('Cần lắp ráp');
 const count=String(r.scope||'').split(',').filter(Boolean).length;
 list.push(count>=5?'Build nhiều linh kiện':'Nâng cấp một phần');
 list.push(remainingLabel(r));
 const p=latestProposalForRequest(r);if(p)list.push('Proposal: '+proposalState(p));
 return list;
};
function pushBuyerNotification(state,userId,title,path){state.notifications.unshift({id:uid('NT'),userId,title,path,kind:'Cấu hình & báo giá',at:Date.now(),read:false});}

function sidebar(){
 const active=(file)=>file==='proposal-list'?['proposal-list','proposal','proposal-builder'].includes(page):file==='orders'?['orders','order'].includes(page):file==='fulfillment'?page==='fulfillment':page===file;
 const item=(file,label,count='')=>'<a href="'+link(file)+'" '+(active(file)?'aria-current="page"':'')+'>'+esc(label)+(count!==''?'<span class="sidebar__count">'+esc(count)+'</span>':'')+'</a>';
 return '<aside class="shop-sidebar"><div class="shop-sidebar__brand"><strong>'+esc(shopInfo.name)+'</strong><small>Shop đã xác minh · Chủ shop</small></div><nav><p class="sidebar__group">Vận hành</p>'+item('dashboard','Tổng quan')+item('offers','Tin bán',bpOffers().filter(o=>o.active).length)+item('inventory','Kho',bpOffers().filter(o=>o.active&&availableFor(o.id)<=2).length+' thấp')+'<p class="sidebar__group">Công việc</p>'+item('build-requests','Yêu cầu Build',liveRequests().length)+item('proposal-list','Proposal',proposals().filter(p=>['Cần sửa','Đã gửi'].includes(proposalState(p))).length)+item('orders','Đơn hàng',suborders().filter(x=>!closedOrderStates.includes(x.sub.status)).length)+item('fulfillment','Giao hàng')+item('aftersales','Hậu mãi',aftersalesCases().filter(c=>!caseClosed(c)).length)+'<p class="sidebar__group">Tài chính</p>'+item('revenue','Doanh thu')+'</nav></aside>';
}

function shell(content,title='Cổng Shop'){
 document.body.className='shop-app';
 document.body.innerHTML='<a class="skip-link" href="#main">Bỏ qua điều hướng</a><div class="service-bar">'+esc(shopInfo.name)+' · Trung tâm vận hành shop</div><header class="topbar"><div class="container topbar__inner" style="max-width:none"><button class="menu-toggle" type="button" data-sidebar-toggle aria-expanded="false" aria-label="Mở sidebar"><span></span></button><a class="logo" href="'+link('dashboard')+'"><i class="logo__mark"></i><span>PC</span><span>Match Shop</span></a><label class="search shop-top-search"><span class="sr-only">Tìm trong shop</span><input id="shop-global-search" placeholder="Tìm request, proposal, offer hoặc đơn"><i class="search__glyph"></i></label><nav class="nav-links"><a href="'+pageUrl('buyer','home')+'">Mở phía người mua</a><a href="'+link('dashboard')+'">'+esc(shopInfo.name)+'</a></nav></div></header><div class="shop-shell">'+sidebar()+'<main class="shop-main" id="main"><nav class="breadcrumb"><a href="'+link('dashboard')+'">Cổng Shop</a><span>'+esc(title)+'</span></nav>'+content+'</main></div><div id="shop-toast" class="shop-toast" hidden role="status"></div>';
}
function toast(msg){const el=document.querySelector('#shop-toast');if(!el)return;el.textContent=msg;el.hidden=false;clearTimeout(window.__shopToast);window.__shopToast=setTimeout(()=>el.hidden=true,2600);}
function closeDialog(dialog){if(dialog?.open)dialog.close();}

function dashboard(){
 const openOrders=suborders().filter(x=>!closedOrderStates.includes(x.sub.status));
 const low=bpOffers().filter(o=>o.active&&availableFor(o.id)<=2);
 const waiting=proposals().filter(p=>proposalState(p)==='Cần sửa');
 const openCases=aftersalesCases().filter(c=>!caseClosed(c));
 const tasks=[
  ...openOrders.filter(x=>x.sub.status==='Chờ shop xác nhận').slice(0,1).map(({sub})=>'<a class="task-row" href="'+link('order',{sub:sub.id})+'"><div><strong>Xác nhận '+esc(sub.id)+'</strong><small>'+sub.items.length+' item · chờ xử lý</small></div>'+badge(sub.status)+'</a>'),
  ...waiting.slice(0,1).map(p=>'<a class="task-row" href="'+link('proposal',{id:p.id})+'"><div><strong>'+esc(p.id)+' cần phản hồi</strong><small>'+(p.feedback?.at(-1)?.text?esc(p.feedback.at(-1).text):'Người mua yêu cầu cập nhật báo giá')+'</small></div>'+badge('Cần sửa')+'</a>'),
  ...low.slice(0,1).map(o=>'<a class="task-row" href="'+link('inventory',{offer:o.id})+'#history"><div><strong>'+esc(o.id)+' còn '+availableFor(o.id)+' khả dụng</strong><small>Tồn '+o.stock+' · đang giữ '+reservedFor(o.id)+'</small></div>'+badge('Tồn thấp')+'</a>'),
  ...openCases.slice(0,1).map(c=>'<a class="task-row" href="'+link('aftersales',{id:c.id})+'"><div><strong>'+esc(c.id)+' · '+esc(caseTypeLabel(c.type))+'</strong><small>'+esc(c.reason||'Hồ sơ hậu mãi cần xử lý')+'</small></div>'+badge(c.status)+'</a>')
 ].join('');
 shell(
  head('Hôm nay cần xử lý gì?','Theo dõi công việc đang chờ và các tín hiệu cần chú ý.','<a class="btn btn--secondary" href="'+link('proposal-list')+'">Xem Proposal</a><a class="btn btn--primary" href="'+link('build-requests')+'">Xem Build Request</a>')+
  '<div class="shop-kpis">'+
   '<article class="panel shop-kpi"><span class="metric-label">Đơn cần xử lý</span><strong class="metric-value">'+openOrders.length+'<small> đơn con</small></strong><p>Xác nhận, chuẩn bị hoặc bàn giao.</p></article>'+
   '<article class="panel shop-kpi"><span class="metric-label">Proposal cần phản hồi</span><strong class="metric-value">'+waiting.length+'<small> bản</small></strong><p>Ưu tiên các yêu cầu khách vừa phản hồi.</p></article>'+
   '<article class="panel shop-kpi"><span class="metric-label">Tồn thấp</span><strong class="metric-value">'+low.length+'<small> offer</small></strong><p>Tính theo tồn thực tế và lượng đang giữ.</p></article>'+
   '<article class="panel shop-kpi"><span class="metric-label">Request đang mở</span><strong class="metric-value">'+liveRequests().length+'<small> nhu cầu</small></strong><p>Lọc theo ngân sách, khu vực và thời hạn.</p></article>'+
  '</div><div class="shop-grid"><section class="panel panel--padded"><div class="panel__head"><div><h2 style="font-size:var(--text-xl)">Hàng chờ ưu tiên</h2><p>Các việc có thể xử lý ngay.</p></div></div><div class="task-list">'+(tasks||'<p>Không có việc cần ưu tiên.</p>')+'</div></section>'+panel('Thao tác nhanh','<div class="stack"><a class="btn btn--secondary" href="'+link('offers')+'">Tạo tin bán</a><a class="btn btn--secondary" href="'+link('inventory')+'">Điều chỉnh tồn kho</a><a class="btn btn--secondary" href="'+link('build-requests')+'">Mở yêu cầu Build</a><a class="btn btn--secondary" href="'+link('orders')+'">Mở hàng chờ đơn</a><a class="btn btn--secondary" href="'+link('aftersales')+'">Mở hậu mãi</a><a class="btn btn--secondary" href="'+link('revenue')+'">Xem doanh thu</a></div>')+'</div>',
  'Tổng quan'
 );
}

function offerEditorDialog(){
 return '<dialog class="modal shop-dialog" id="offer-editor"><form data-form="offer-editor"><div class="modal__head"><div><h2 data-dialog-title>Tạo tin bán</h2><p class="shop-mini">Tin bán luôn gắn với một model chuẩn.</p></div><button type="button" class="icon-button" data-dialog-close aria-label="Đóng"><span class="close-glyph"></span></button></div><div class="modal__body stack"><input type="hidden" name="offerId"><label class="field"><span>Model chuẩn</span><select name="modelId" required>'+models.map(m=>'<option value="'+esc(m.id)+'">'+esc(m.name)+' · '+esc(categories[m.category])+'</option>').join('')+'</select></label><div class="form-grid"><label class="field"><span>Giá bán (₫)</span><input name="price" type="number" min="1" step="1000" required></label><label class="field"><span>Bảo hành (tháng)</span><input name="warranty" type="number" min="0" step="1" required></label><label class="field"><span>Tồn thực tế</span><input name="stock" type="number" min="0" step="1" required></label><label class="field"><span>Trạng thái</span><select name="active"><option value="1">Đang bán</option><option value="0">Tạm ẩn</option></select></label></div></div><div class="modal__foot"><button type="button" class="btn btn--secondary" data-dialog-close>Hủy</button><button class="btn btn--primary">Lưu tin bán</button></div></form></dialog>';
}
function offersPage(){
 const q=(qs.get('q')||'').toLowerCase(),cat=qs.get('category')||'',active=qs.get('active')||'';
 const rows=bpOffers().filter(o=>{const m=model(o.modelId);return (!q||[m.name,m.brand,o.id].join(' ').toLowerCase().includes(q))&&(!cat||m.category===cat)&&(!active||String(Number(o.active))===active);});
 shell(
  head('Quản lý tin bán','Theo dõi model, giá, bảo hành, tồn và trạng thái bán.','<button class="btn btn--primary" type="button" data-action="offer-create-open">Tạo tin bán</button>')+
  '<form class="shop-toolbar--compact shop-toolbar" data-form="offer-filter"><label class="field"><span>Tìm offer / model</span><input name="q" value="'+esc(q)+'" placeholder="Ryzen, SSD, BP-CPU..."></label><label class="field"><span>Danh mục</span><select name="category"><option value="">Tất cả</option>'+Object.entries(categories).map(([k,v])=>'<option value="'+k+'" '+(cat===k?'selected':'')+'>'+esc(v)+'</option>').join('')+'</select></label><label class="field"><span>Trạng thái</span><select name="active"><option value="">Tất cả</option><option value="1" '+(active==='1'?'selected':'')+'>Đang bán</option><option value="0" '+(active==='0'?'selected':'')+'>Tạm ẩn</option></select></label><button class="btn btn--secondary">Lọc</button></form>'+
  '<div class="table-wrap"><table class="data-table"><thead><tr><th>Offer</th><th>Model chuẩn</th><th>Giá</th><th>Bảo hành</th><th>Tồn</th><th>Trạng thái</th><th></th></tr></thead><tbody>'+rows.map(o=>{const m=model(o.modelId);return '<tr><td><strong>'+esc(o.id)+'</strong><small>'+esc(categories[m.category])+'</small></td><td><strong>'+esc(m.name)+'</strong><small>'+esc(m.brand)+'</small></td><td>'+money(o.price)+'</td><td>'+o.warranty+' tháng</td><td>'+o.stock+'</td><td>'+badge(o.active?'Đang bán':'Tạm ẩn')+'</td><td><div class="shop-table-actions">'+button('Sửa','offer-edit-open',o.id)+button(o.active?'Ẩn tin':'Mở bán','offer-toggle',o.id)+'</div></td></tr>';}).join('')+'</tbody></table></div>'+offerEditorDialog(),
  'Tin bán'
 );
}

function stockDialog(){
 return '<dialog class="modal shop-dialog" id="stock-dialog"><form data-form="stock-adjust"><div class="modal__head"><div><h2>Điều chỉnh tồn kho</h2><p class="shop-mini" data-stock-caption></p></div><button type="button" class="icon-button" data-dialog-close aria-label="Đóng"><span class="close-glyph"></span></button></div><div class="modal__body stack"><input type="hidden" name="offerId"><div class="shop-detail-list"><div><span>Tồn hiện tại</span><strong data-stock-current>0</strong></div><div><span>Đang giữ</span><strong data-stock-reserved>0</strong></div><div><span>Khả dụng</span><strong data-stock-available>0</strong></div><div><span>Tồn sau điều chỉnh</span><strong data-stock-result>0</strong></div></div><label class="field"><span>Tồn mới</span><input name="stock" type="number" min="0" step="1" required></label><label class="field"><span>Lý do</span><select name="reason" required><option value="Nhập thêm hàng">Nhập thêm hàng</option><option value="Kiểm kê kho">Kiểm kê kho</option><option value="Hàng lỗi / thu hồi">Hàng lỗi / thu hồi</option><option value="Điều chỉnh khác">Điều chỉnh khác</option></select></label></div><div class="modal__foot"><button type="button" class="btn btn--secondary" data-dialog-close>Hủy</button><button class="btn btn--primary">Lưu điều chỉnh</button></div></form></dialog>';
}
function inventoryPage(){
 const selected=qs.get('offer')||'';
 const rows=bpOffers().filter(o=>o.active).sort((a,b)=>availableFor(a.id)-availableFor(b.id));
 const logs=db().shopMeta.inventoryLog.filter(l=>!selected||l.offerId===selected).slice(0,10);
 shell(
  head('Quản lý kho','Theo dõi tồn thực tế, lượng đang giữ và số lượng có thể tiếp tục bán.','<a class="btn btn--secondary" href="'+link('offers')+'">Mở tin bán</a>')+
  '<div class="table-wrap"><table class="data-table"><thead><tr><th>Offer</th><th>Model</th><th>Tồn thực tế</th><th>Đang giữ</th><th>Khả dụng</th><th>Cảnh báo</th><th></th></tr></thead><tbody>'+rows.map(o=>{const reserved=reservedFor(o.id),available=availableFor(o.id),m=model(o.modelId);return '<tr '+(selected===o.id?'style="background:var(--color-cobalt-soft)"':'')+'><td><strong>'+esc(o.id)+'</strong></td><td>'+esc(m.name)+'</td><td>'+o.stock+'</td><td>'+reserved+'</td><td><strong>'+available+'</strong></td><td>'+(available<=2?badge('Tồn thấp'):badge('Khả dụng'))+'</td><td><div class="shop-table-actions">'+button('Điều chỉnh','stock-adjust-open',o.id)+'<a class="btn btn--quiet" href="'+link('inventory',{offer:o.id})+'#history">Lịch sử</a></div></td></tr>';}).join('')+'</tbody></table></div>'+
  '<section class="panel panel--padded shop-section" id="history"><div class="panel__head"><div><h2 style="font-size:var(--text-xl)">Lịch sử điều chỉnh</h2><p>'+(selected?'Đang lọc '+esc(selected):'Các thay đổi gần đây')+'</p></div>'+(selected?'<a class="btn btn--quiet" href="'+link('inventory')+'#history">Bỏ lọc</a>':'')+'</div>'+(logs.length?'<div class="table-wrap"><table class="data-table"><thead><tr><th>Thời gian</th><th>Offer</th><th>Thay đổi</th><th>Tồn sau</th><th>Lý do</th></tr></thead><tbody>'+logs.map(l=>'<tr><td>'+fmtDate(l.at)+'</td><td><strong>'+esc(l.offerId)+'</strong></td><td><strong class="'+(l.delta>=0?'shop-positive':'shop-negative')+'">'+(l.delta>0?'+':'')+l.delta+'</strong></td><td>'+l.after+'</td><td>'+esc(l.reason||'Điều chỉnh kho')+'</td></tr>').join('')+'</tbody></table></div>':'<p>Chưa có điều chỉnh nào được ghi nhận.</p>')+'</section>'+stockDialog(),
  'Kho'
 );
}

function buildRequestsPage(){
 const budget=Number(qs.get('budget')||0),region=qs.get('region')||'',assembly=qs.get('assembly')||'',scope=qs.get('scope')||'',deadline=Number(qs.get('deadline')||0),q=(qs.get('q')||'').toLowerCase();
 const list=liveRequests().filter(r=>{
  const count=String(r.scope||'').split(',').filter(Boolean).length;
  return (!budget||r.budget>=budget)&&(!region||r.region===region)&&(!assembly||(assembly==='yes')===!!r.assembly)&&(!scope||(scope==='full'?count>=5:count<5))&&(!deadline||remainingMs(r)<=deadline*3600000)&&(!q||[r.id,r.purpose,r.scope,r.owned].join(' ').toLowerCase().includes(q));
 });
 shell(
  head('Yêu cầu Build đang mở','Lọc các nhu cầu theo thông tin người mua đã cung cấp.','<a class="btn btn--secondary" href="'+link('proposal-list')+'">Proposal của shop</a>')+
  '<form class="shop-toolbar" data-form="request-filter"><label class="field"><span>Tìm request</span><input name="q" value="'+esc(q)+'" placeholder="Gaming, GPU, REQ-..."></label><label class="field"><span>Ngân sách</span><select name="budget"><option value="0">Tất cả</option><option value="15000000" '+(budget===15000000?'selected':'')+'>Từ 15 triệu</option><option value="20000000" '+(budget===20000000?'selected':'')+'>Từ 20 triệu</option></select></label><label class="field"><span>Khu vực</span><select name="region"><option value="">Tất cả</option>'+Object.entries(regions).filter(([k])=>k!=='OTHER').map(([k,v])=>'<option value="'+k+'" '+(region===k?'selected':'')+'>'+esc(v)+'</option>').join('')+'</select></label><label class="field"><span>Phạm vi</span><select name="scope"><option value="">Tất cả</option><option value="full" '+(scope==='full'?'selected':'')+'>Build nhiều linh kiện</option><option value="upgrade" '+(scope==='upgrade'?'selected':'')+'>Nâng cấp một phần</option></select></label><label class="field"><span>Thời hạn</span><select name="deadline"><option value="0">Tất cả</option><option value="24" '+(deadline===24?'selected':'')+'>Trong 24 giờ</option><option value="72" '+(deadline===72?'selected':'')+'>Trong 3 ngày</option><option value="168" '+(deadline===168?'selected':'')+'>Trong 7 ngày</option></select></label><button class="btn btn--secondary">Lọc</button></form>'+
  '<div class="shop-list">'+(list.length?list.map(r=>{const p=latestProposalForRequest(r);return '<article class="shop-card"><div><div class="shop-badge-row">'+badge('Đang nhận')+requestSignals(r).map(x=>'<span class="shop-signal">'+esc(x)+'</span>').join('')+'</div><h2>'+esc(r.purpose)+'</h2><p><strong>'+money(r.budget)+'</strong> · '+esc(regions[r.region])+' · '+esc(r.id)+'</p><p>Phạm vi: '+esc(r.scope)+'</p><p class="shop-mini">Người mua: '+esc(buyerName(r))+(p?' · Proposal gần nhất v'+p.version:'')+'</p></div><a class="btn btn--primary" href="'+link('build-request-detail',{id:r.id})+'">Xem yêu cầu</a></article>';}).join(''):'<div class="panel shop-empty"><h2>Không có yêu cầu phù hợp bộ lọc</h2><p>Thử bỏ bớt điều kiện lọc để xem thêm request đang mở.</p></div>')+'</div>',
  'Yêu cầu Build'
 );
}

function messageBox(request){
 const msgs=(request.messages||[]).filter(m=>!m.shopId||m.shopId===SHOP_ID);
 return '<section class="panel shop-chat"><div class="panel__head" style="padding:var(--space-4);margin:0"><div><h2 style="font-size:var(--text-xl)">Trao đổi với người mua</h2><p>'+esc(buyerName(request))+' · '+esc(request.id)+'</p></div></div><div class="shop-chat__messages">'+(msgs.length?msgs.map(m=>'<div class="shop-message '+(m.role==='shop'?'shop-message--shop':'')+'"><strong>'+esc(m.author)+'</strong>'+esc(m.text)+'<small>'+fmtDate(m.at)+'</small></div>').join(''):'<p class="shop-mini">Chưa có tin nhắn.</p>')+'</div><form data-form="chat" data-request="'+esc(request.id)+'"><label class="field"><span>Tin nhắn</span><textarea name="text" required maxlength="500" placeholder="Nhập nội dung trao đổi..."></textarea></label><button class="btn btn--primary">Gửi</button></form></section>';
}
function requestDetailPage(){
 const r=db().requests.find(x=>x.id===(qs.get('id')||liveRequests()[0]?.id));
 if(!r){shell(head('Không tìm thấy yêu cầu','Mở một yêu cầu từ danh sách Build Request.','<a class="btn btn--primary" href="'+link('build-requests')+'">Về danh sách</a>'),'Chi tiết yêu cầu');return;}
 const current=latestProposalForRequest(r),state=current?proposalState(current):'';
 let primary='<a class="btn btn--primary" href="'+link('proposal-builder',{request:r.id})+'">Tạo proposal</a>';
 if(current&&state==='Cần sửa')primary='<a class="btn btn--primary" href="'+link('proposal-builder',{request:r.id,from:current.id})+'">Chỉnh proposal</a>';
 else if(current&&['Đã gửi','Đã chọn'].includes(state))primary='<a class="btn btn--primary" href="'+link('proposal',{id:current.id})+'">Mở proposal</a>';
 else if(current&&['Hết hạn','Đã rút'].includes(state))primary='<a class="btn btn--primary" href="'+link('proposal-builder',{request:r.id,from:current.id})+'">Tạo bản mới</a>';
 const info='<div class="shop-detail-list"><div><span>Ngân sách</span><strong>'+money(r.budget)+'</strong></div><div><span>Khu vực</span><strong>'+esc(regions[r.region])+'</strong></div><div><span>Phạm vi mua</span><strong>'+esc(r.scope)+'</strong></div><div><span>Linh kiện đang có</span><strong>'+esc(r.owned||'Không')+'</strong></div><div><span>Lắp ráp</span><strong>'+(r.assembly?'Có':'Không')+'</strong></div><div><span>Hạn nhận</span><strong>'+esc(r.deadline)+' · '+esc(remainingLabel(r))+'</strong></div></div>';
 const processing='<div class="shop-badge-row">'+requestSignals(r).map(x=>'<span class="shop-signal">'+esc(x)+'</span>').join('')+'</div>'+(current?'<div class="shop-section"><p><strong>Proposal gần nhất:</strong> '+esc(current.id)+' · v'+current.version+' · '+esc(state)+'</p><p>Tổng '+money(proposalTotal(current))+' · Hết hiệu lực '+fmtDate(current.expires)+'</p><a class="btn btn--secondary" href="'+link('proposal',{id:current.id})+'">Xem proposal</a></div>':'<p class="shop-section">Shop chưa gửi proposal cho phiên bản yêu cầu này.</p>');
 shell(head(r.purpose,r.id+' · phiên bản '+r.version+' · '+buyerName(r),'<a class="btn btn--secondary" href="'+link('build-requests')+'">Danh sách</a>'+primary)+'<div class="shop-grid"><div class="stack">'+panel('Thông tin nhu cầu',info)+panel('Tình trạng xử lý',processing)+'</div>'+messageBox(r)+'</div>','Chi tiết yêu cầu');
}

function offerOptions(category,selected=''){
 const opts=bpOffers().filter(o=>o.active&&model(o.modelId).category===category);
 return '<option value="">'+(category==='COOL'?'Không chọn tản rời':'Chọn tin bán')+'</option>'+opts.map(o=>'<option value="'+esc(o.id)+'" '+(selected===o.id?'selected':'')+'>'+esc(model(o.modelId).name)+' · '+money(o.price)+' · khả dụng '+availableFor(o.id)+'</option>').join('');
}
function builderSelection(form=document.querySelector('[data-form=proposal-builder]')){
 if(!form)return {};
 const slots={};
 for(const c of Object.keys(categories)){const id=form.elements['slot-'+c]?.value;if(id)slots[c]={offerId:id,qty:1};}
 return slots;
}
function proposalSummaryHTML(slots,r,fee,assembly){
 const items=Object.entries(slots).map(([cat,x])=>{const o=currentOffer(x.offerId),m=o&&model(o.modelId);if(!o||!m)return '';return '<div class="list-row"><div><strong>'+esc(m.name)+'</strong><p>'+esc(categories[cat])+' · BH '+o.warranty+' tháng · khả dụng '+availableFor(o.id)+'</p></div><strong>'+money(o.price)+'</strong></div>';}).join('');
 const parts=Object.values(slots).reduce((sum,x)=>sum+(currentOffer(x.offerId)?.price||0),0),total=parts+fee+assembly,delta=total-r.budget;
 const checks=compatibility({slots});
 return '<div class="shop-proposal-lines">'+(items||'<p class="shop-mini">Chọn linh kiện để xem tóm tắt.</p>')+'</div><div class="shop-total"><span>Tiền linh kiện</span><strong>'+money(parts)+'</strong></div><div class="shop-total"><span>Phí giao</span><strong>'+money(fee)+'</strong></div><div class="shop-total"><span>Lắp ráp</span><strong>'+money(assembly)+'</strong></div><div class="shop-total shop-total--grand"><span>Tổng</span><strong>'+money(total)+'</strong></div><p class="'+(delta>0?'shop-negative':'shop-positive')+'">'+(delta>0?'Vượt ngân sách ':'Còn trong ngân sách ')+money(Math.abs(delta))+'</p><ul class="shop-compat">'+checks.map(c=>'<li>'+badge(c.state)+'<div><strong>'+esc(c.title)+'</strong><p>'+esc(c.reason)+'</p></div></li>').join('')+'</ul>';
}
function proposalPreview(){
 const form=document.querySelector('[data-form=proposal-builder]'),target=document.querySelector('[data-proposal-preview]');if(!form||!target)return;
 const r=db().requests.find(x=>x.id===form.dataset.request),slots=builderSelection(form),fee=Number(form.elements.fee.value||0),assembly=Number(form.elements.assembly.value||0);
 target.innerHTML=proposalSummaryHTML(slots,r,fee,assembly);
}
function proposalBuilderPage(){
 const r=db().requests.find(x=>x.id===(qs.get('request')||liveRequests()[0]?.id));
 if(!r){shell(head('Chưa có Build Request','Mở một yêu cầu đang nhận proposal trước khi tạo báo giá.','<a class="btn btn--primary" href="'+link('build-requests')+'">Mở yêu cầu Build</a>'),'Tạo Proposal');return;}
 const from=proposals().find(p=>p.id===qs.get('from'));
 const draft=db().shopMeta.proposalDrafts[r.id];
 const selected=Object.fromEntries((draft?.slots?Object.entries(draft.slots).map(([k,v])=>[k,v.offerId]):from?.items.map(i=>[model(currentOffer(i.offerId).modelId).category,i.offerId])||[]));
 const fee=draft?.fee??from?.fee??65000,assembly=draft?.assembly??from?.assembly??(r.assembly?150000:0),hours=draft?.hours??24,note=draft?.note??from?.note??'';
 const title=from?'Cập nhật Proposal':'Tạo Proposal';
 shell(
  head(title,r.id+' · '+r.purpose+' · ngân sách '+money(r.budget),'<a class="btn btn--secondary" href="'+link('build-request-detail',{id:r.id})+'">Về yêu cầu</a>')+
  (draft?'<div class="alert alert--info shop-state-banner"><i class="alert__signal"></i><div><strong>Có bản nháp đã lưu</strong><p>Cập nhật '+fmtDate(draft.at)+'</p></div></div>':'')+
  '<form data-form="proposal-builder" data-request="'+esc(r.id)+'" data-from="'+esc(from?.id||'')+'"><div class="shop-grid"><section class="shop-slot-grid">'+Object.entries(categories).map(([c,label])=>'<div class="shop-slot"><div><span class="shop-slot__code">'+c+'</span><small>'+esc(label)+'</small></div><label class="field"><span>Tin bán của shop</span><select name="slot-'+c+'" '+(c==='COOL'?'':'required')+'>'+offerOptions(c,selected[c])+'</select></label><div class="shop-mini" data-slot-meta="'+c+'"></div></div>').join('')+'</section><aside class="stack shop-summary">'+panel('Tóm tắt','<div data-proposal-preview></div>')+panel('Chi phí và thời hạn','<label class="field"><span>Phí giao dự kiến</span><input name="fee" type="number" min="0" step="1000" value="'+fee+'"></label><label class="field"><span>Phí lắp ráp</span><input name="assembly" type="number" min="0" step="1000" value="'+assembly+'"></label><label class="field"><span>Hiệu lực (giờ)</span><input name="hours" type="number" min="1" max="72" value="'+hours+'" required></label><label class="field"><span>Ghi chú cho người mua</span><textarea name="note" maxlength="500">'+esc(note)+'</textarea></label><div class="shop-builder-actions"><button class="btn btn--secondary" type="button" data-action="proposal-save-draft">Lưu nháp</button><button class="btn btn--secondary" type="button" data-action="proposal-preview-open">Xem trước</button><button class="btn btn--primary" type="submit">Gửi proposal</button></div>')+'</aside></div></form><dialog class="modal shop-dialog shop-dialog--wide" id="proposal-preview-dialog"><div class="modal__head"><div><h2>Xem trước Proposal</h2><p class="shop-mini">'+esc(r.id)+' · '+esc(r.purpose)+'</p></div><button type="button" class="icon-button" data-dialog-close aria-label="Đóng"><span class="close-glyph"></span></button></div><div class="modal__body" data-proposal-preview-dialog></div><div class="modal__foot"><button type="button" class="btn btn--primary" data-dialog-close>Đóng</button></div></dialog>',
  'Tạo Proposal'
 );
 proposalPreview();
}

function proposalListPage(){
 const q=(qs.get('q')||'').toLowerCase(),state=qs.get('state')||'';
 const rows=proposals().map(p=>({p,state:proposalState(p),r:db().requests.find(r=>r.id===p.requestId)})).filter(x=>(!state||x.state===state)&&(!q||[x.p.id,x.p.requestId,x.r?.purpose,buyerNameById(x.p.userId)].join(' ').toLowerCase().includes(q))).sort((a,b)=>(b.p.sentAt||b.p.expires)-(a.p.sentAt||a.p.expires));
 const states=['Cần sửa','Đã gửi','Đã chọn','Hết hạn','Đã thay thế','Đã rút'];
 const counts=Object.fromEntries(states.map(s=>[s,proposals().filter(p=>proposalState(p)===s).length]));
 shell(
  head('Proposal của shop','Theo dõi báo giá đã gửi và các yêu cầu cần phản hồi.','<a class="btn btn--primary" href="'+link('build-requests')+'">Tạo từ Build Request</a>')+
  '<div class="shop-status-tabs"><a href="'+link('proposal-list')+'" '+(!state?'aria-current="page"':'')+'>Tất cả <strong>'+proposals().length+'</strong></a>'+states.map(s=>'<a href="'+link('proposal-list',{state:s})+'" '+(state===s?'aria-current="page"':'')+'>'+esc(s)+' <strong>'+counts[s]+'</strong></a>').join('')+'</div>'+
  '<form class="shop-toolbar--compact shop-toolbar" data-form="proposal-filter"><label class="field"><span>Tìm proposal / request</span><input name="q" value="'+esc(q)+'" placeholder="PR-, REQ-, mục đích..."></label><label class="field"><span>Trạng thái</span><select name="state"><option value="">Tất cả</option>'+states.map(s=>'<option value="'+esc(s)+'" '+(state===s?'selected':'')+'>'+esc(s)+'</option>').join('')+'</select></label><button class="btn btn--secondary">Lọc</button></form>'+
  '<div class="table-wrap"><table class="data-table"><thead><tr><th>Proposal</th><th>Request</th><th>Người mua</th><th>Tổng</th><th>Hiệu lực</th><th>Trạng thái</th><th></th></tr></thead><tbody>'+rows.map(({p,state,r})=>'<tr><td><strong>'+esc(p.id)+'</strong><small>Version '+p.version+'</small></td><td><strong>'+esc(p.requestId)+'</strong><small>'+esc(r?.purpose||'Yêu cầu Build')+'</small></td><td>'+esc(buyerNameById(p.userId))+'</td><td>'+money(proposalTotal(p))+'</td><td>'+fmtDate(p.expires)+'</td><td>'+badge(state)+'</td><td><a class="btn btn--quiet" href="'+link('proposal',{id:p.id})+'">Mở</a></td></tr>').join('')+'</tbody></table></div>',
  'Proposal'
 );
}

function proposalDetailPage(){
 const p=proposals().find(x=>x.id===(qs.get('id')||proposals().sort((a,b)=>b.version-a.version)[0]?.id));
 if(!p){shell(head('Chưa có Proposal','Tạo proposal từ một Build Request đang mở.','<a class="btn btn--primary" href="'+link('build-requests')+'">Mở Build Request</a>'),'Proposal');return;}
 const r=db().requests.find(x=>x.id===p.requestId),state=proposalState(p),feedback=p.feedback?.at(-1),history=proposalHistory(p),order=orderForProposal(p),sub=order?.suborders.find(s=>s.shopId===SHOP_ID);
 const changed=p.items.filter(i=>{const o=currentOffer(i.offerId);return !o||!o.active||o.price!==i.price||o.warranty!==i.warranty;});
 let actions='<a class="btn btn--secondary" href="'+link('proposal-list')+'">Danh sách</a>';
 if(state==='Cần sửa'||state==='Hết hạn')actions+='<a class="btn btn--primary" href="'+link('proposal-builder',{request:p.requestId,from:p.id})+'">Tạo bản cập nhật</a>';
 if(['Đã gửi','Cần sửa'].includes(state))actions+=button('Rút proposal','proposal-withdraw-open',p.id,'secondary');
 if(state==='Đã chọn'&&sub)actions+='<a class="btn btn--primary" href="'+link('order',{sub:sub.id})+'">Mở đơn hàng</a>';
 const lines=p.items.map(i=>{const o=currentOffer(i.offerId),m=o&&model(o.modelId);return '<div class="list-row"><div><strong>'+esc(m?.name||i.offerId)+'</strong><p>'+esc(i.offerId)+' · '+money(i.price)+' · BH '+i.warranty+' tháng'+(o?' · khả dụng '+availableFor(o.id):'')+'</p></div><strong>'+money(i.price*i.qty)+'</strong></div>';}).join('');
 shell(
  head('Proposal '+p.id,(r?.purpose||p.requestId)+' · Version '+p.version,actions)+
  (changed.length?'<div class="alert alert--danger shop-state-banner"><i class="alert__signal"></i><div><strong>Một số tin bán đã thay đổi</strong><p>'+changed.map(i=>esc(i.offerId)).join(', ')+'</p></div></div>':'')+
  '<div class="shop-grid"><div class="stack">'+panel('Báo giá','<div class="cluster">'+badge(state)+'<span class="status">Version '+p.version+'</span><span class="status">Hạn '+fmtDate(p.expires)+'</span></div><div class="shop-section">'+lines+'</div><div class="shop-total"><span>Phí giao</span><strong>'+money(p.fee)+'</strong></div><div class="shop-total"><span>Lắp ráp</span><strong>'+money(p.assembly)+'</strong></div><div class="shop-total shop-total--grand"><span>Tổng</span><strong>'+money(proposalTotal(p))+'</strong></div>'+(r?'<p>Chênh ngân sách: <strong>'+money(proposalTotal(p)-r.budget)+'</strong></p>':'')+(p.note?'<p>Ghi chú: '+esc(p.note)+'</p>':''))+(feedback?panel('Yêu cầu chỉnh sửa của người mua','<p>'+esc(feedback.text)+'</p><p class="shop-mini">'+fmtDate(feedback.at)+'</p>'):'')+panel('Các phiên bản',history.map(x=>'<div class="list-row"><div><strong><a href="'+link('proposal',{id:x.id})+'">Version '+x.version+'</a></strong><p>'+fmtDate(x.sentAt||x.expires)+' · '+esc(proposalState(x))+'</p></div><strong>'+money(proposalTotal(x))+'</strong></div>').join(''))+(order?panel('Đơn hàng liên quan','<p>'+esc(order.id)+(sub?' · '+esc(sub.id):'')+'</p>'+(sub?'<a class="btn btn--secondary" href="'+link('order',{sub:sub.id})+'">Mở đơn hàng</a>':'')):'')+'</div>'+(r?messageBox(r):'')+'</div><dialog class="modal shop-dialog" id="proposal-withdraw-dialog"><form data-form="proposal-withdraw"><div class="modal__head"><div><h2>Rút Proposal</h2><p class="shop-mini">'+esc(p.id)+'</p></div><button type="button" class="icon-button" data-dialog-close aria-label="Đóng"><span class="close-glyph"></span></button></div><div class="modal__body"><input type="hidden" name="proposalId" value="'+esc(p.id)+'"><label class="field"><span>Lý do</span><textarea name="reason" required maxlength="300" placeholder="Ví dụ: giá hoặc tồn kho đã thay đổi"></textarea></label></div><div class="modal__foot"><button type="button" class="btn btn--secondary" data-dialog-close>Hủy</button><button class="btn btn--danger">Rút proposal</button></div></form></dialog>',
  'Proposal'
 );
}

function orderListPage(){
 const q=(qs.get('q')||'').toLowerCase(),state=qs.get('state')||'';
 const all=suborders().map(x=>({...x,buyer:buyerNameById(x.order.userId)}));
 const states=[...new Set(all.map(x=>x.sub.status))];
 const rows=all.filter(x=>(!state||x.sub.status===state)&&(!q||[x.order.id,x.sub.id,x.buyer,x.order.proposalId,x.order.requestId].join(' ').toLowerCase().includes(q))).sort((a,b)=>b.order.at-a.order.at);
 shell(
  head('Đơn hàng','Theo dõi các đơn con của BuildPro theo trạng thái xử lý.','<a class="btn btn--secondary" href="'+link('fulfillment')+'">Mở giao hàng</a>')+
  '<div class="shop-status-tabs"><a href="'+link('orders')+'" '+(!state?'aria-current="page"':'')+'>Tất cả <strong>'+all.length+'</strong></a>'+states.map(s=>'<a href="'+link('orders',{state:s})+'" '+(state===s?'aria-current="page"':'')+'>'+esc(s)+' <strong>'+all.filter(x=>x.sub.status===s).length+'</strong></a>').join('')+'</div>'+
  '<form class="shop-toolbar--compact shop-toolbar" data-form="order-filter"><label class="field"><span>Tìm đơn</span><input name="q" value="'+esc(q)+'" placeholder="PCM-, SUB-, người mua..."></label><label class="field"><span>Trạng thái</span><select name="state"><option value="">Tất cả</option>'+states.map(s=>'<option value="'+esc(s)+'" '+(state===s?'selected':'')+'>'+esc(s)+'</option>').join('')+'</select></label><button class="btn btn--secondary">Lọc</button></form>'+
  '<div class="table-wrap"><table class="data-table"><thead><tr><th>Đơn con</th><th>Người mua</th><th>Nguồn</th><th>Tổng</th><th>Thanh toán</th><th>Trạng thái</th><th>Giao nhận</th><th></th></tr></thead><tbody>'+rows.map(({order:o,sub:s,buyer})=>'<tr><td><strong>'+esc(s.id)+'</strong><small>'+esc(o.id)+' · '+fmtDate(o.at)+'</small></td><td>'+esc(buyer)+'</td><td>'+(o.proposalId?'<a href="'+link('proposal',{id:o.proposalId})+'">'+esc(o.proposalId)+'</a>':o.requestId?esc(o.requestId):'Mua trực tiếp')+'</td><td>'+money(s.total)+'</td><td>'+badge(o.payment==='paid'?'Đã thanh toán':o.payment)+'</td><td>'+badge(s.status)+'</td><td>'+esc(s.shippingStatus||'Chưa tạo vận đơn')+'</td><td><a class="btn btn--quiet" href="'+link('order',{sub:s.id})+'">Mở</a></td></tr>').join('')+'</tbody></table></div>',
  'Đơn hàng'
 );
}

function orderRejectDialog(sub){
 return '<dialog class="modal shop-dialog" id="order-reject-dialog"><form data-form="order-reject"><div class="modal__head"><div><h2>Từ chối đơn</h2><p class="shop-mini">'+esc(sub.id)+'</p></div><button type="button" class="icon-button" data-dialog-close aria-label="Đóng"><span class="close-glyph"></span></button></div><div class="modal__body stack"><input type="hidden" name="subId" value="'+esc(sub.id)+'"><label class="field"><span>Lý do</span><select name="reason" required><option value="Hết hàng sau đối chiếu tồn">Hết hàng sau đối chiếu tồn</option><option value="Không đáp ứng điều kiện lắp ráp">Không đáp ứng điều kiện lắp ráp</option><option value="Không thể giao đúng thời gian">Không thể giao đúng thời gian</option><option value="Khác">Khác</option></select></label><label class="field"><span>Ghi chú</span><textarea name="note" maxlength="300" placeholder="Thông tin bổ sung"></textarea></label></div><div class="modal__foot"><button type="button" class="btn btn--secondary" data-dialog-close>Quay lại</button><button class="btn btn--danger">Xác nhận từ chối</button></div></form></dialog>';
}
function orderPage(){
 const entry=suborders().find(x=>x.sub.id===(qs.get('sub')||suborders()[0]?.sub.id));
 if(!entry){shell(head('Không có đơn hàng','Mở danh sách đơn để chọn một đơn con.','<a class="btn btn--primary" href="'+link('orders')+'">Danh sách đơn</a>'),'Đơn hàng');return;}
 const {order:o,sub:s}=entry,p=o.proposalId?proposals().find(x=>x.id===o.proposalId):null,r=o.requestId?db().requests.find(x=>x.id===o.requestId):null;
 let actions='<a class="btn btn--secondary" href="'+link('orders')+'">Danh sách</a>';
 if(s.status==='Chờ shop xác nhận'&&o.payment==='paid')actions+=button('Từ chối','order-reject-open',s.id,'secondary')+button('Xác nhận đơn','order-confirm',s.id,'primary');
 if(!['Chờ shop xác nhận','Đã hủy','Đã giao','Hoàn tất'].includes(s.status))actions+='<a class="btn btn--primary" href="'+link('fulfillment',{sub:s.id})+'">Xử lý giao hàng</a>';
 const itemRows=s.items.map(i=>{const offer=currentOffer(i.offerId),avail=offer?availableFor(i.offerId):0;return '<tr><td><strong>'+esc(i.name)+'</strong><small>'+esc(i.offerId)+'</small></td><td>'+i.qty+'</td><td>'+money(i.price)+'</td><td>'+i.warranty+' tháng</td><td>'+(offer?offer.stock:'—')+'</td><td>'+avail+'</td></tr>';}).join('');
 const source=(p||r)?'<div class="shop-detail-list">'+(r?'<div><span>Build Request</span><strong><a href="'+link('build-request-detail',{id:r.id})+'">'+esc(r.id)+'</a></strong></div>':'')+(p?'<div><span>Proposal</span><strong><a href="'+link('proposal',{id:p.id})+'">'+esc(p.id)+' · v'+p.version+'</a></strong></div>':'')+'</div>':'<p>Đơn mua trực tiếp, không đi từ Build Request.</p>';
 shell(
  head('Đơn '+s.id,o.id+' · '+buyerNameById(o.userId),actions)+
  (o.payment!=='paid'?'<div class="alert alert--danger shop-state-banner"><i class="alert__signal"></i><div><strong>Chưa thể xác nhận đơn</strong><p>Trạng thái thanh toán hiện tại: '+esc(o.payment)+'</p></div></div>':'')+
  '<div class="shop-grid"><div class="stack">'+panel('Nguồn đơn hàng',source)+panel('Sản phẩm','<div class="table-wrap"><table class="data-table"><thead><tr><th>Sản phẩm</th><th>SL</th><th>Giá snapshot</th><th>Bảo hành</th><th>Tồn hiện tại</th><th>Khả dụng</th></tr></thead><tbody>'+itemRows+'</tbody></table></div>')+panel('Dòng thời gian','<ul class="shop-timeline">'+s.timeline.map(t=>'<li><strong>'+fmtDate(t.at)+'</strong><span>'+esc(t.text)+'</span></li>').join('')+'</ul>')+'</div><div class="stack">'+panel('Trạng thái','<div class="shop-badge-row">'+badge(o.payment==='paid'?'Đã thanh toán':o.payment)+badge(s.status)+badge(s.shippingStatus||'Chưa tạo vận đơn')+'</div>')+panel('Giao hàng','<p><strong>'+esc(o.address.name)+'</strong> · '+esc(o.address.phone)+'</p><p>'+esc(o.address.detail)+' · '+esc(regions[o.address.region])+'</p>')+panel('Tài chính đơn con','<div class="shop-total"><span>Tiền hàng</span><strong>'+money(s.subtotal)+'</strong></div><div class="shop-total"><span>Giảm giá</span><strong>− '+money(s.discount)+'</strong></div><div class="shop-total"><span>Phí giao</span><strong>'+money(s.fee)+'</strong></div><div class="shop-total"><span>Lắp ráp</span><strong>'+money(s.assembly||0)+'</strong></div><div class="shop-total shop-total--grand"><span>Tổng đơn con</span><strong>'+money(s.total)+'</strong></div>')+'</div></div>'+orderRejectDialog(s),
  'Đơn hàng'
 );
}

function serialComplete(sub){return sub.items.every(i=>Array.isArray(i.serials)&&i.serials.length===i.qty&&i.serials.every(Boolean));}

const localDateValue=d=>{const x=new Date(d);x.setMinutes(x.getMinutes()-x.getTimezoneOffset());return x.toISOString().slice(0,10);};
const startDay=value=>new Date(value+'T00:00:00').getTime();
const endDay=value=>new Date(value+'T23:59:59.999').getTime();
const completedRefundTotal=sub=>refundsFor(sub).filter(r=>r.status==='Hoàn thành').reduce((sum,r)=>sum+(r.amount||0),0);
const revenueEntry=({order,sub})=>{
 const gross=sub.subtotal||0,discount=sub.discount||0,assembly=sub.assembly||0,refund=completedRefundTotal(sub);
 return {order,sub,gross,discount,assembly,refund,net:Math.max(0,gross-discount+assembly-refund)};
};
const settlementLabel=e=>{
 if(e.sub.status==='Đã hủy'&&e.refund>0)return 'Đã hoàn';
 if(['Đã giao','Hoàn tất'].includes(e.sub.status))return 'Chờ đối soát';
 return 'Chưa đủ điều kiện';
};
function revenueRange(){
 const today=new Date(),fallbackTo=localDateValue(today),fromDate=new Date(today);fromDate.setDate(fromDate.getDate()-6);const fallbackFrom=localDateValue(fromDate);
 const from=qs.get('from')||fallbackFrom,to=qs.get('to')||fallbackTo;
 return startDay(from)<=endDay(to)?{from,to,start:startDay(from),end:endDay(to)}:{from:to,to:from,start:startDay(to),end:endDay(from)};
}
function revenueDays(from,to){
 const out=[],cursor=new Date(from+'T00:00:00'),last=new Date(to+'T00:00:00');
 for(let n=0;cursor<=last&&n<92;n++,cursor.setDate(cursor.getDate()+1))out.push(localDateValue(cursor));
 return out;
}
function revenuePage(){
 const range=revenueRange();
 const entries=suborders().filter(({order})=>order.payment==='paid'&&order.at>=range.start&&order.at<=range.end).map(revenueEntry).sort((a,b)=>b.order.at-a.order.at);
 const totals=entries.reduce((a,e)=>({gross:a.gross+e.gross,discount:a.discount+e.discount,assembly:a.assembly+e.assembly,refund:a.refund+e.refund,net:a.net+e.net}),{gross:0,discount:0,assembly:0,refund:0,net:0});
 const days=revenueDays(range.from,range.to),daily=Object.fromEntries(days.map(d=>[d,0]));
 for(const e of entries){const k=localDateValue(e.order.at);if(k in daily)daily[k]+=e.net;}
 const max=Math.max(1,...Object.values(daily));
 const bars=days.map(d=>{const value=daily[d]||0,pct=Math.max(value?4:0,Math.round(value/max*100));return '<div class="shop-revenue-bar" title="'+esc(new Date(d+'T00:00:00').toLocaleDateString('vi-VN'))+' · '+esc(money(value))+'"><div class="shop-revenue-bar__value">'+(value?money(value):'0 ₫')+'</div><div class="shop-revenue-bar__track"><i style="--bar:'+pct+'%"></i></div><small>'+esc(new Date(d+'T00:00:00').toLocaleDateString('vi-VN',{day:'2-digit',month:'2-digit'}))+'</small></div>';}).join('');
 const catTotals={};
 for(const e of entries)for(const i of e.sub.items){const m=model(i.modelId||currentOffer(i.offerId)?.modelId);const label=m?categories[m.category]:'Khác';catTotals[label]=(catTotals[label]||0)+i.price*i.qty;}
 const catRows=Object.entries(catTotals).sort((a,b)=>b[1]-a[1]).slice(0,6),catSum=catRows.reduce((a,[,v])=>a+v,0);
 let running=0;const palette=['#135fd2','#05877e','#c87500','#566370','#8b5cf6','#c63b4b'];
 const stops=catRows.map(([name,value],i)=>{const from=catSum?running/catSum*100:0;running+=value;const to=catSum?running/catSum*100:0;return palette[i]+' '+from.toFixed(2)+'% '+to.toFixed(2)+'%';});
 const donut=catRows.length?'<div class="shop-revenue-donut" style="--donut:'+stops.join(',')+'"><div><strong>'+money(catSum)+'</strong><span>Tiền hàng</span></div></div><div class="shop-revenue-legend">'+catRows.map(([name,value],i)=>'<div><i style="background:'+palette[i]+'"></i><span>'+esc(name)+'</span><strong>'+money(value)+'</strong><small>'+(catSum?Math.round(value/catSum*100):0)+'%</small></div>').join('')+'</div>':'<div class="shop-empty"><p>Chưa có dữ liệu sản phẩm trong khoảng đã chọn.</p></div>';
 const rows=entries.map(e=>'<tr><td><strong><a href="'+link('order',{sub:e.sub.id})+'">'+esc(e.sub.id)+'</a></strong><small>'+esc(e.order.id)+' · '+fmtDate(e.order.at)+'</small></td><td>'+badge(e.sub.status)+'</td><td>'+money(e.gross)+'</td><td>− '+money(e.discount)+'</td><td>'+(e.refund?'− '+money(e.refund):'0 ₫')+'</td><td><strong>'+money(e.net)+'</strong></td><td>'+badge(settlementLabel(e))+'</td></tr>').join('');
 shell(
  head('Doanh thu','Theo dõi doanh số của shop, khoản giảm giá, hoàn tiền và thực nhận dự kiến.','<a class="btn btn--secondary" href="'+link('orders')+'">Mở đơn hàng</a>')+
  '<form class="shop-revenue-filter" data-form="revenue-filter"><label class="field"><span>Từ ngày</span><input type="date" name="from" value="'+esc(range.from)+'" required></label><label class="field"><span>Đến ngày</span><input type="date" name="to" value="'+esc(range.to)+'" required></label><button class="btn btn--secondary">Áp dụng</button></form>'+
  '<div class="shop-kpis">'+
   '<article class="panel shop-kpi"><span class="metric-label">Doanh số hàng hóa</span><strong class="metric-value">'+money(totals.gross)+'</strong><p>'+entries.length+' đơn con đã thanh toán trong khoảng chọn.</p></article>'+
   '<article class="panel shop-kpi"><span class="metric-label">Giảm giá của shop</span><strong class="metric-value">'+money(totals.discount)+'</strong><p>Khoản ưu đãi do shop tài trợ.</p></article>'+
   '<article class="panel shop-kpi"><span class="metric-label">Hoàn tiền hoàn tất</span><strong class="metric-value">'+money(totals.refund)+'</strong><p>Chỉ tính các khoản đã hoàn thành.</p></article>'+
   '<article class="panel shop-kpi"><span class="metric-label">Thực nhận dự kiến</span><strong class="metric-value">'+money(totals.net)+'</strong><p>Tiền hàng − giảm giá + lắp ráp − hoàn tiền.</p></article>'+
  '</div>'+
  '<div class="shop-grid shop-grid--equal"><section class="panel panel--padded"><div class="panel__head"><div><h2 style="font-size:var(--text-xl)">Doanh thu theo ngày</h2><p>Giá trị thực nhận dự kiến theo ngày đặt đơn.</p></div></div><div class="shop-revenue-bars" style="--days:'+Math.max(7,days.length)+'">'+bars+'</div></section><section class="panel panel--padded"><div class="panel__head"><div><h2 style="font-size:var(--text-xl)">Cơ cấu tiền hàng</h2><p>Phân bổ theo nhóm linh kiện trong các đơn đã thanh toán.</p></div></div><div class="shop-revenue-pie">'+donut+'</div></section></div>'+
  '<section class="panel panel--padded shop-section"><div class="panel__head"><div><h2 style="font-size:var(--text-xl)">Đối soát theo đơn</h2><p>Phí giao không cộng vào thực nhận của shop trong bảng này.</p></div></div><div class="table-wrap"><table class="data-table"><thead><tr><th>Đơn con</th><th>Trạng thái</th><th>Tiền hàng</th><th>Giảm giá</th><th>Hoàn tiền</th><th>Thực nhận dự kiến</th><th>Đối soát</th></tr></thead><tbody>'+(rows||'<tr><td colspan="7"><div class="shop-empty">Chưa có giao dịch trong khoảng thời gian này.</div></td></tr>')+'</tbody></table></div></section>',
  'Doanh thu'
 );
}


function aftersalesEvidenceHTML(c){
 const files=[c.evidence,...(c.attachments||[])].filter(Boolean);
 return files.length?'<div class="shop-evidence-list">'+files.map(f=>'<a class="shop-evidence" download="'+esc(f.name||'bang-chung')+'" href="'+esc(f.data||'#')+'"><strong>'+esc(f.name||'Bằng chứng')+'</strong><small>Mở / tải tệp khách đã gửi</small></a>').join('')+'</div>':'<p class="shop-mini">Chưa có tệp bằng chứng.</p>';
}
function aftersalesTimelineHTML(c){
 return '<ul class="shop-timeline">'+(c.timeline||[]).map(t=>'<li><strong>'+fmtDate(t.at)+'</strong><span>'+esc(t.text)+'</span></li>').join('')+'</ul>';
}
function aftersalesActionsHTML(c,ctx){
 if(caseClosed(c))return '<p class="shop-mini">Hồ sơ đã có kết quả. Có thể tiếp tục trao đổi trong tiến trình nếu cần.</p>';
 const common='<div class="shop-aftersales-actions">'+
  (['Đã gửi — chờ tiếp nhận','Cần bổ sung bằng chứng'].includes(c.status)?button('Tiếp nhận & hướng dẫn gửi hàng','case-inspect',c.id,'primary'):'')+
  (['Đã gửi — chờ tiếp nhận','Cần bổ sung bằng chứng'].includes(c.status)?'<form data-form="case-more" data-case="'+esc(c.id)+'" class="shop-action-form"><label class="field"><span>Yêu cầu bổ sung</span><textarea name="text" rows="2" placeholder="Ví dụ: bổ sung ảnh tem serial và tình trạng hộp" required></textarea></label><button class="btn btn--secondary">Gửi yêu cầu</button></form>':'')+
  (['Đã gửi — chờ tiếp nhận','Cần bổ sung bằng chứng','Đang kiểm tra hồ sơ','Đã nhận — kiểm tra bảo hành'].includes(c.status)?'<form data-form="case-reject" data-case="'+esc(c.id)+'" class="shop-action-form"><label class="field"><span>Lý do từ chối</span><textarea name="reason" rows="2" placeholder="Nêu rõ lý do" required></textarea></label><button class="btn btn--secondary">Từ chối hồ sơ</button></form>':'')+
 '</div>';
 if(c.type==='return'){
  const canRefund=['Đang kiểm tra hồ sơ','Đang gửi hàng cho shop'].includes(c.status);
  const refund=ctx.sub?refundsFor(ctx.sub).find(r=>r.caseId===c.id):null;
  return common+(refund?'<div class="shop-case-result"><strong>Khoản hoàn '+esc(refund.id)+'</strong><span>'+badge(refund.status)+'</span><p>'+money(refund.amount||0)+'</p></div>':canRefund?'<div class="shop-case-result"><strong>Đổi/trả đủ điều kiện xử lý</strong><p>Khoản hoàn được tính theo đúng serial và phần giảm giá đã phân bổ của dòng hàng.</p>'+button('Duyệt hoàn tiền','case-refund',c.id,'primary')+'</div>':'');
 }
 if(c.type==='warranty'){
  const canResolve=['Đang gửi hàng cho shop','Đã nhận — kiểm tra bảo hành'].includes(c.status);
  return common+(canResolve?'<div class="shop-aftersales-resolution"><div>'+button('Sửa xong, gửi lại','case-repair',c.id,'secondary')+'</div><form data-form="case-replace" data-case="'+esc(c.id)+'"><label class="field"><span>Serial sản phẩm thay thế</span><input name="serial" placeholder="Nhập serial mới" required></label><button class="btn btn--primary">Đổi sản phẩm</button></form></div>':'');
 }
 if(c.type==='complaint'){
  return '<div class="shop-case-result"><strong>Phản hồi khiếu nại</strong><p>Shop cung cấp giải trình; kết luận cuối cùng thuộc luồng xử lý của nền tảng.</p>'+(!String(c.status||'').startsWith('Shop đã phản hồi')?button('Đánh dấu đã phản hồi','case-complaint-replied',c.id,'primary'):'')+'</div>';
 }
 return common;
}
function aftersalesDetailPage(c){
 const ctx=caseContext(c),{order:o,sub:s,item:i}=ctx;
 if(!o||!s){shell(head('Hồ sơ '+c.id,'Không tìm thấy đơn con tương ứng của shop.','<a class="btn btn--secondary" href="'+link('aftersales')+'">Về danh sách</a>')+panel('Thông tin hồ sơ','<p>'+esc(c.reason||'')+'</p>'+badge(c.status)),'Hậu mãi');return;}
 const serials=(c.serials?.length?c.serials:[c.serial]).filter(Boolean);
 const buyer=buyerNameById(c.userId);
 const related='<div class="shop-detail-list"><div><span>Khách hàng</span><strong>'+esc(buyer)+'</strong></div><div><span>Đơn con</span><strong><a href="'+link('order',{sub:s.id})+'">'+esc(s.id)+'</a></strong></div><div><span>Sản phẩm</span><strong>'+esc(i?.name||c.itemId||'Không xác định')+'</strong></div><div><span>Số lượng</span><strong>'+esc(c.qty||1)+'</strong></div><div><span>Serial</span><strong>'+esc(serials.join(', ')||'Không có')+'</strong></div><div><span>Chính sách lúc mua</span><strong>'+esc(c.policy||i?.policy||'—')+'</strong></div></div>';
 const logistics=(c.type==='return'||c.type==='warranty')?panel('Gửi / nhận lại hàng','<p>'+esc(c.logistics||'Chưa có hướng dẫn gửi hàng.')+'</p>'+(c.replacementSerial?'<p><strong>Serial thay thế:</strong> '+esc(c.replacementSerial)+'</p>':'')+(s?'<p class="shop-mini">Đơn gốc: '+esc(s.id)+' · Trạng thái giao: '+esc(s.shippingStatus)+'</p>':'')):'';
 shell(
  head(c.id,caseTypeLabel(c.type)+' · '+c.status,'<a class="btn btn--secondary" href="'+link('aftersales')+'">Danh sách hậu mãi</a><a class="btn btn--secondary" href="'+link('order',{sub:s.id})+'">Xem đơn</a>')+
  '<div class="shop-grid"><div class="stack">'+
   panel('Nội dung hồ sơ',related+'<div class="shop-case-copy"><p><strong>Lý do:</strong> '+esc(c.reason||'—')+'</p><p>'+esc(c.text||'')+'</p></div>')+
   panel('Bằng chứng',aftersalesEvidenceHTML(c))+
   panel('Tiến trình',aftersalesTimelineHTML(c))+
  '</div><div class="stack">'+
   panel('Trạng thái','<div class="shop-badge-row">'+badge(caseTypeLabel(c.type))+badge(c.status)+'</div>')+
   logistics+
   panel('Trao đổi với khách','<form data-form="case-message" data-case="'+esc(c.id)+'"><label class="field"><span>Nội dung phản hồi</span><textarea name="text" rows="4" placeholder="Nhập phản hồi của shop" required></textarea></label><button class="btn btn--secondary">Gửi phản hồi</button></form>')+
   panel('Xử lý hồ sơ',aftersalesActionsHTML(c,ctx))+
  '</div></div>',
  'Hậu mãi'
 );
}
function aftersalesPage(){
 const id=qs.get('id'),c=id?aftersalesCases().find(x=>x.id===id):null;
 if(id&&!c){shell(head('Không tìm thấy hồ sơ','Hồ sơ không thuộc BuildPro Sài Gòn hoặc không còn tồn tại.','<a class="btn btn--primary" href="'+link('aftersales')+'">Mở danh sách</a>'),'Hậu mãi');return;}
 if(c){aftersalesDetailPage(c);return;}
 const q=(qs.get('q')||'').toLowerCase(),type=qs.get('type')||'',status=qs.get('status')||'';
 const all=aftersalesCases().slice().sort((a,b)=>(b.timeline?.at(-1)?.at||0)-(a.timeline?.at(-1)?.at||0));
 const rows=all.filter(c=>{
  const ctx=caseContext(c),hay=[c.id,c.reason,c.status,c.serial,(c.serials||[]).join(' '),ctx.item?.name,buyerNameById(c.userId),c.orderId,c.subId].join(' ').toLowerCase();
  return (!q||hay.includes(q))&&(!type||c.type===type)&&(!status||(status==='open'?!caseClosed(c):status==='closed'?caseClosed(c):c.status===status));
 });
 const counts={all:all.length,return:all.filter(c=>c.type==='return').length,warranty:all.filter(c=>c.type==='warranty').length,complaint:all.filter(c=>c.type==='complaint').length,open:all.filter(c=>!caseClosed(c)).length};
 const tabs='<div class="shop-status-tabs"><a href="'+link('aftersales')+'" '+(!type?'aria-current="page"':'')+'>Tất cả <strong>'+counts.all+'</strong></a><a href="'+link('aftersales',{type:'return'})+'" '+(type==='return'?'aria-current="page"':'')+'>Đổi/trả <strong>'+counts.return+'</strong></a><a href="'+link('aftersales',{type:'warranty'})+'" '+(type==='warranty'?'aria-current="page"':'')+'>Bảo hành <strong>'+counts.warranty+'</strong></a><a href="'+link('aftersales',{type:'complaint'})+'" '+(type==='complaint'?'aria-current="page"':'')+'>Khiếu nại <strong>'+counts.complaint+'</strong></a></div>';
 const cards=rows.map(c=>{const ctx=caseContext(c),serials=(c.serials?.length?c.serials:[c.serial]).filter(Boolean).join(', ');return '<article class="shop-card shop-case-card"><div><div class="shop-badge-row">'+badge(caseTypeLabel(c.type))+badge(c.status)+'</div><h2><a href="'+link('aftersales',{id:c.id})+'">'+esc(c.id)+'</a></h2><p><strong>'+esc(ctx.item?.name||c.itemId||'Hồ sơ giao dịch')+'</strong> · '+esc(buyerNameById(c.userId))+'</p><p>'+esc(c.reason||'')+'</p><div class="shop-card__meta"><span class="shop-signal">'+esc(c.subId||c.orderId||'Không có đơn')+'</span>'+(serials?'<span class="shop-signal">Serial '+esc(serials)+'</span>':'')+'<span class="shop-signal">'+fmtDate(c.timeline?.at(-1)?.at)+'</span></div></div><div><a class="btn btn--secondary" href="'+link('aftersales',{id:c.id})+'">Xử lý</a></div></article>';}).join('');
 shell(
  head('Hậu mãi','Tiếp nhận đổi/trả, bảo hành và phản hồi khiếu nại thuộc đơn của '+shopInfo.name+'.','<a class="btn btn--secondary" href="'+link('orders')+'">Mở đơn hàng</a>')+
  '<div class="shop-kpis">'+
   '<article class="panel shop-kpi"><span class="metric-label">Hồ sơ đang mở</span><strong class="metric-value">'+counts.open+'<small> hồ sơ</small></strong><p>Cần tiếp nhận hoặc đang xử lý.</p></article>'+
   '<article class="panel shop-kpi"><span class="metric-label">Đổi/trả</span><strong class="metric-value">'+counts.return+'<small> hồ sơ</small></strong><p>Theo từng item và serial.</p></article>'+
   '<article class="panel shop-kpi"><span class="metric-label">Bảo hành</span><strong class="metric-value">'+counts.warranty+'<small> hồ sơ</small></strong><p>Sửa hoặc đổi sản phẩm.</p></article>'+
   '<article class="panel shop-kpi"><span class="metric-label">Khiếu nại</span><strong class="metric-value">'+counts.complaint+'<small> hồ sơ</small></strong><p>Shop cung cấp phản hồi cho nền tảng.</p></article>'+
  '</div>'+tabs+
  '<form class="shop-toolbar--compact shop-toolbar" data-form="case-filter"><label class="field"><span>Tìm hồ sơ</span><input name="q" value="'+esc(q)+'" placeholder="CASE, đơn, serial, khách hàng"></label><label class="field"><span>Loại</span><select name="type"><option value="">Tất cả</option><option value="return" '+(type==='return'?'selected':'')+'>Đổi/trả</option><option value="warranty" '+(type==='warranty'?'selected':'')+'>Bảo hành</option><option value="complaint" '+(type==='complaint'?'selected':'')+'>Khiếu nại</option></select></label><label class="field"><span>Trạng thái</span><select name="status"><option value="">Tất cả</option><option value="open" '+(status==='open'?'selected':'')+'>Đang mở</option><option value="closed" '+(status==='closed'?'selected':'')+'>Đã có kết quả</option></select></label><button class="btn btn--secondary">Lọc</button></form>'+
  (cards||'<div class="panel shop-empty"><h2>Chưa có hồ sơ hậu mãi</h2><p></p></div>'),
  'Hậu mãi'
 );
}

function fulfillmentPage(){
 const entry=suborders().find(x=>x.sub.id===(qs.get('sub')||suborders().find(x=>!['Chờ shop xác nhận','Đã hủy','Đã giao'].includes(x.sub.status))?.sub.id));
 if(!entry){shell(head('Chưa có đơn cần giao','Xác nhận một đơn hàng trước khi xử lý giao nhận.','<a class="btn btn--primary" href="'+link('orders')+'">Mở đơn hàng</a>'),'Giao hàng');return;}
 const {order:o,sub:s}=entry,meta=db().shopMeta.packing[s.id]||{},serialDone=serialComplete(s),stage=s.shippingStatus==='Đã giao'?4:s.shippingStatus==='Đang giao'?3:s.tracking?2:meta.packed?1:serialDone?1:0;
 const serialFields=s.items.map((i,itemIndex)=>'<div class="shop-serial-item"><div><strong>'+esc(i.name)+'</strong><small>'+esc(i.offerId)+' · Số lượng '+i.qty+'</small></div>'+Array.from({length:i.qty},(_,unitIndex)=>'<label class="field"><span>Serial '+(unitIndex+1)+'</span><input name="serial-'+itemIndex+'-'+unitIndex+'" value="'+esc(i.serials?.[unitIndex]||'')+'" placeholder="Nhập serial" required></label>').join('')+'</div>').join('');
 const shipping=s.tracking?'<p><strong>'+esc(s.tracking)+'</strong></p>'+badge(s.shippingStatus)+'<div class="stack" style="margin-top:var(--space-4)">'+(s.shippingStatus==='Chờ lấy hàng'?button('Đánh dấu đang giao','shipment-pickup',s.id,'primary'):'')+(s.shippingStatus==='Đang giao'?button('Đánh dấu đã giao','shipment-delivered',s.id,'primary'):'')+'</div>':'<form data-form="shipment" data-sub="'+esc(s.id)+'"><label class="field"><span>Dịch vụ</span><select name="service"><option value="standard">Tiêu chuẩn · 3–5 ngày</option><option value="fast">Nhanh · 2–3 ngày</option></select></label><button class="btn btn--primary">Tạo vận đơn</button></form>';
 shell(
  head('Xử lý giao hàng',s.id+' · '+esc(s.status),'<a class="btn btn--secondary" href="'+link('order',{sub:s.id})+'">Về đơn</a>')+
  '<div class="shop-flow"><div class="shop-flow__step '+(serialDone?'is-done':'is-current')+'"><strong>1. Serial</strong><small>Theo từng sản phẩm</small></div><div class="shop-flow__step '+(meta.packed?'is-done':serialDone?'is-current':'')+'"><strong>2. Đóng gói</strong><small>Khối lượng và số kiện</small></div><div class="shop-flow__step '+(s.tracking?'is-done':meta.packed?'is-current':'')+'"><strong>3. Vận đơn</strong><small>Tracking và dịch vụ</small></div><div class="shop-flow__step '+(s.shippingStatus==='Đã giao'?'is-done':s.shippingStatus==='Đang giao'?'is-current':'')+'"><strong>4. Bàn giao</strong><small>'+esc(s.shippingStatus||'Chưa bắt đầu')+'</small></div></div>'+
  '<div class="shop-grid shop-section"><div class="stack">'+panel('Serial sản phẩm','<form data-form="serials" data-sub="'+esc(s.id)+'" class="stack">'+serialFields+'<button class="btn btn--secondary">Lưu serial</button></form>')+panel('Đóng gói','<form data-form="packing" data-sub="'+esc(s.id)+'"><div class="form-grid"><label class="field"><span>Khối lượng (kg)</span><input name="weight" type="number" min="0.1" step="0.1" value="'+esc(meta.weight||'4.2')+'" required></label><label class="field"><span>Số kiện</span><input name="packages" type="number" min="1" value="'+esc(meta.packages||1)+'" required></label></div><label class="field"><span>Kích thước</span><input name="size" value="'+esc(meta.size||'50 × 40 × 30 cm')+'" required></label><button class="btn btn--secondary">Xác nhận đóng gói</button></form>')+'</div>'+panel('Vận đơn','<p>Giao đến: '+esc(o.address.detail)+' · '+esc(regions[o.address.region])+'</p>'+shipping)+'</div>',
  'Giao hàng'
 );
}

const renderers={dashboard,offers:offersPage,inventory:inventoryPage,'build-requests':buildRequestsPage,'build-request-detail':requestDetailPage,'proposal-builder':proposalBuilderPage,'proposal-list':proposalListPage,proposal:proposalDetailPage,orders:orderListPage,order:orderPage,fulfillment:fulfillmentPage,aftersales:aftersalesPage,revenue:revenuePage};
(renderers[page]||dashboard)();
function rerender(){(renderers[page]||dashboard)();}
function findProposal(id){return proposals().find(p=>p.id===id);}

function proposalFormData(form){
 return {slots:builderSelection(form),fee:Number(form.elements.fee.value||0),assembly:Number(form.elements.assembly.value||0),hours:Number(form.elements.hours.value||24),note:String(form.elements.note.value||'').trim()};
}
function validateProposal(form){
 const r=db().requests.find(x=>x.id===form.dataset.request);if(!r||r.status!=='open'||remainingMs(r)<=0)throw Error('Yêu cầu không còn nhận proposal.');
 const data=proposalFormData(form),required=['CPU','MB','RAM','GPU','SSD','PSU','CASE'];
 if(required.some(c=>!data.slots[c]))throw Error('Cần chọn đủ CPU, mainboard, RAM, GPU, SSD, PSU và case.');
 const checks=compatibility({slots:data.slots});if(checks.some(c=>c.state==='Không tương thích'))throw Error('Cấu hình còn lỗi tương thích.');
 for(const x of Object.values(data.slots)){const o=currentOffer(x.offerId);if(!o||o.shopId!==SHOP_ID||!o.active||availableFor(o.id)<1)throw Error('Có tin bán không còn đủ tồn khả dụng.');}
 if(!Number.isInteger(data.hours)||data.hours<1||data.hours>72)throw Error('Thời hạn proposal phải từ 1 đến 72 giờ.');
 return {r,...data};
}

document.addEventListener('click',e=>{
 const side=e.target.closest('[data-sidebar-toggle]');if(side){const sh=document.querySelector('.shop-shell'),open=sh.classList.toggle('is-sidebar-open');side.setAttribute('aria-expanded',String(open));return;}
 const closer=e.target.closest('[data-dialog-close]');if(closer){closeDialog(closer.closest('dialog'));return;}
 const b=e.target.closest('[data-action]');if(!b)return;const act=b.dataset.action,id=b.dataset.id;
 try{
  if(act==='offer-create-open'){
   const dlg=document.querySelector('#offer-editor'),f=dlg.querySelector('form'),first=bpOffers().find(o=>!o.active)||bpOffers()[0],m=model(first.modelId);f.reset();f.elements.offerId.value='';f.elements.modelId.disabled=false;f.elements.modelId.value=m.id;f.elements.price.value=first.price;f.elements.warranty.value=first.warranty;f.elements.stock.value=Math.max(0,first.stock);f.elements.active.value='1';dlg.querySelector('[data-dialog-title]').textContent='Tạo tin bán';dlg.showModal();return;
  }
  if(act==='offer-edit-open'){
   const o=currentOffer(id),dlg=document.querySelector('#offer-editor'),f=dlg.querySelector('form');if(!o)throw Error('Không tìm thấy tin bán.');f.elements.offerId.value=o.id;f.elements.modelId.disabled=true;f.elements.modelId.value=o.modelId;f.elements.price.value=o.price;f.elements.warranty.value=o.warranty;f.elements.stock.value=o.stock;f.elements.active.value=o.active?'1':'0';dlg.querySelector('[data-dialog-title]').textContent='Sửa tin bán';dlg.showModal();return;
  }
  if(act==='offer-toggle'){tx(s=>{const o=currentOffer(id);s.overrides[id]={...s.overrides[id],active:!o.active};});rerender();toast('Đã cập nhật trạng thái tin bán.');return;}
  if(act==='stock-adjust-open'){
   const o=currentOffer(id),dlg=document.querySelector('#stock-dialog'),f=dlg.querySelector('form'),reserved=reservedFor(id);f.elements.offerId.value=id;f.elements.stock.min=reserved;f.elements.stock.value=o.stock;dlg.querySelector('[data-stock-caption]').textContent=id+' · '+model(o.modelId).name;dlg.querySelector('[data-stock-current]').textContent=o.stock;dlg.querySelector('[data-stock-reserved]').textContent=reserved;dlg.querySelector('[data-stock-available]').textContent=availableFor(id);dlg.querySelector('[data-stock-result]').textContent=o.stock;dlg.showModal();return;
  }
  if(act==='proposal-save-draft'){
   const form=document.querySelector('[data-form=proposal-builder]'),data=proposalFormData(form),rid=form.dataset.request;tx(s=>s.shopMeta.proposalDrafts[rid]={...clone(data),from:form.dataset.from||'',at:Date.now()});toast('Đã lưu bản nháp.');return;
  }
  if(act==='proposal-preview-open'){
   const form=document.querySelector('[data-form=proposal-builder]'),data=validateProposal(form),dlg=document.querySelector('#proposal-preview-dialog');dlg.querySelector('[data-proposal-preview-dialog]').innerHTML=proposalSummaryHTML(data.slots,data.r,data.fee,data.assembly);dlg.showModal();return;
  }
  if(act==='proposal-withdraw-open'){document.querySelector('#proposal-withdraw-dialog')?.showModal();return;}
  if(act==='order-reject-open'){document.querySelector('#order-reject-dialog')?.showModal();return;}
  if(act==='case-inspect'){
   const c=aftersalesCases().find(x=>x.id===id);if(!c)throw Error('Không tìm thấy hồ sơ.');
   if(!['Đã gửi — chờ tiếp nhận','Cần bổ sung bằng chứng'].includes(c.status))throw Error('Hồ sơ đã được tiếp nhận.');
   tx(s=>{c.status=c.type==='warranty'?'Đã nhận — kiểm tra bảo hành':'Đang kiểm tra hồ sơ';c.logistics='Nơi tiếp nhận: '+shopInfo.name+'; chờ vận đơn gửi hàng demo.';c.timeline.push({at:Date.now(),text:'Shop: '+c.status});pushBuyerNotification(s,c.userId,'Shop đã tiếp nhận hồ sơ '+c.id,'cases.html?id='+encodeURIComponent(c.id));});rerender();toast('Đã tiếp nhận hồ sơ.');return;
  }
  if(act==='case-refund'){
   const c=aftersalesCases().find(x=>x.id===id);if(!c||c.type!=='return')throw Error('Không phải hồ sơ đổi/trả.');const {sub,item}=caseContext(c);if(!sub||!item)throw Error('Không tìm thấy dòng hàng gốc.');if(!['Đang kiểm tra hồ sơ','Đang gửi hàng cho shop'].includes(c.status))throw Error('Cần tiếp nhận hồ sơ trước khi duyệt hoàn.');if(refundsFor(sub).some(r=>r.caseId===c.id))throw Error('Hồ sơ đã có khoản hoàn.');
   const serials=c.serials?.length?c.serials:[c.serial],allocated=discountForSerials(sub,item,serials),amount=item.price*c.qty-allocated;
   tx(s=>{appendRefund(sub,{id:uid('RF'),caseId:c.id,amount,requested:amount,approved:amount,status:'Đang xử lý',itemId:item.id,qty:c.qty,discount:allocated,fee:0});c.status='Đã duyệt đổi/trả — chờ hoàn tiền';c.timeline.push({at:Date.now(),text:'Shop: Đã duyệt đổi/trả, tạo khoản hoàn '+money(amount)});pushBuyerNotification(s,c.userId,'Đổi/trả '+c.id+' đã được duyệt','cases.html?id='+encodeURIComponent(c.id));});rerender();toast('Đã tạo khoản hoàn.');return;
  }
  if(act==='case-repair'){
   const c=aftersalesCases().find(x=>x.id===id);if(!c||c.type!=='warranty')throw Error('Không phải hồ sơ bảo hành.');if(!['Đang gửi hàng cho shop','Đã nhận — kiểm tra bảo hành'].includes(c.status))throw Error('Cần tiếp nhận kiểm tra trước khi kết luận.');
   tx(s=>{c.status='Đã sửa — chờ gửi lại hàng';c.logistics='Vận đơn gửi lại demo: '+uid('REDELIVERY');c.timeline.push({at:Date.now(),text:'Shop: Đã sửa xong, chờ gửi lại sản phẩm'});pushBuyerNotification(s,c.userId,'Bảo hành '+c.id+': đã sửa xong','cases.html?id='+encodeURIComponent(c.id));});rerender();return;
  }
  if(act==='case-complaint-replied'){
   const c=aftersalesCases().find(x=>x.id===id);if(!c||c.type!=='complaint')throw Error('Không phải hồ sơ khiếu nại.');
   tx(s=>{c.status='Shop đã phản hồi — chờ nền tảng xem xét';c.timeline.push({at:Date.now(),text:'Shop: Đã gửi phản hồi khiếu nại; chờ nền tảng xem xét'});pushBuyerNotification(s,c.userId,'Shop đã phản hồi khiếu nại '+c.id,'cases.html?id='+encodeURIComponent(c.id));});rerender();return;
  }
  if(act==='order-confirm'){
   const entry=suborders().find(x=>x.sub.id===id);if(!entry)throw Error('Không tìm thấy đơn.');if(entry.order.payment!=='paid')throw Error('Đơn chưa thanh toán.');
   for(const i of entry.sub.items){const o=currentOffer(i.offerId);if(!o||o.stock<reservedFor(i.offerId))throw Error('Tồn kho không đủ để xác nhận đơn.');}
   tx(()=>{entry.sub.status='Chuẩn bị hàng';entry.sub.shippingStatus='Chưa tạo vận đơn';entry.sub.confirmedAt=Date.now();entry.sub.items.forEach(i=>{i.serial='';i.serials=[];});entry.sub.timeline.push({at:Date.now(),text:'Shop xác nhận đơn và bắt đầu chuẩn bị hàng'});});rerender();toast('Đã xác nhận đơn.');return;
  }
  if(act==='shipment-pickup'){
   const entry=suborders().find(x=>x.sub.id===id);if(!entry?.sub.tracking)throw Error('Chưa có vận đơn.');tx(()=>{entry.sub.status='Đang giao';entry.sub.shippingStatus='Đang giao';entry.sub.timeline.push({at:Date.now(),text:'Đơn vị vận chuyển đã nhận hàng'});});rerender();return;
  }
  if(act==='shipment-delivered'){
   const entry=suborders().find(x=>x.sub.id===id);if(entry?.sub.shippingStatus!=='Đang giao')throw Error('Đơn chưa ở trạng thái đang giao.');tx(()=>{entry.sub.status='Đã giao';entry.sub.shippingStatus='Đã giao';entry.sub.deliveredAt=Date.now();entry.sub.timeline.push({at:Date.now(),text:'Đã giao thành công'});});rerender();return;
  }
 }catch(err){toast(err.message);}
});

document.addEventListener('change',e=>{
 if(e.target.closest('[data-form=proposal-builder]'))proposalPreview();
 if(e.target.closest('[data-form=offer-editor]')&&e.target.name==='modelId'){
  const f=e.target.form,o=currentOffer(SHOP_ID+'-'+e.target.value);if(o){f.elements.price.value=o.price;f.elements.warranty.value=o.warranty;f.elements.stock.value=o.stock;f.elements.active.value=o.active?'1':'0';}
 }
 if(e.target.closest('[data-form=stock-adjust]')&&e.target.name==='stock'){document.querySelector('[data-stock-result]').textContent=e.target.value||'0';}
});
document.addEventListener('input',e=>{
 if(e.target.closest('[data-form=proposal-builder]')&&['fee','assembly'].includes(e.target.name))proposalPreview();
 if(e.target.closest('[data-form=stock-adjust]')&&e.target.name==='stock'){document.querySelector('[data-stock-result]').textContent=e.target.value||'0';}
});

document.addEventListener('submit',e=>{
 const form=e.target.closest('form[data-form]');if(!form)return;e.preventDefault();
 const name=form.dataset.form;
 if(!form.reportValidity())return;
 const d=Object.fromEntries(new FormData(form));
 try{
  if(['offer-filter','request-filter','proposal-filter','order-filter','revenue-filter','case-filter'].includes(name)){
   const p=new URLSearchParams();for(const [k,v] of Object.entries(d))if(v)p.set(k,v);location.search=p;return;
  }
  if(name==='offer-editor'){
   const modelId=d.offerId?currentOffer(d.offerId)?.modelId:d.modelId,id=d.offerId||SHOP_ID+'-'+modelId,o=currentOffer(id);if(!o)throw Error('Model này chưa có dữ liệu tin bán.');
   const price=Number(d.price),warranty=Number(d.warranty),stock=Number(d.stock),reserved=reservedFor(id);if(!Number.isInteger(price)||price<=0)throw Error('Giá bán không hợp lệ.');if(!Number.isInteger(warranty)||warranty<0)throw Error('Bảo hành không hợp lệ.');if(!Number.isInteger(stock)||stock<reserved)throw Error('Tồn mới không được thấp hơn lượng đang giữ ('+reserved+').');
   tx(s=>{const before=currentOffer(id).stock;s.overrides[id]={...s.overrides[id],price,warranty,stock,active:d.active==='1'};if(stock!==before)s.shopMeta.inventoryLog.unshift({offerId:id,before,after:stock,delta:stock-before,reason:'Cập nhật từ tin bán',at:Date.now()});});rerender();toast('Đã lưu tin bán.');return;
  }
  if(name==='stock-adjust'){
   const id=d.offerId,o=currentOffer(id),before=o.stock,reserved=reservedFor(id),stock=Number(d.stock);if(!Number.isInteger(stock)||stock<reserved)throw Error('Tồn mới không được thấp hơn lượng đang giữ ('+reserved+').');
   tx(s=>{s.overrides[id]={...s.overrides[id],stock};s.shopMeta.inventoryLog.unshift({offerId:id,before,after:stock,delta:stock-before,reason:d.reason,at:Date.now()});});rerender();toast('Đã cập nhật tồn kho.');return;
  }
  if(name==='chat'){
   const text=String(d.text||'').trim(),rid=form.dataset.request;if(!text)throw Error('Nhập nội dung tin nhắn.');tx(s=>{const r=s.requests.find(x=>x.id===rid);if(!r)throw Error('Không tìm thấy request.');r.messages||=[];r.messages.push({author:shopInfo.name,role:'shop',shopId:SHOP_ID,text,at:Date.now()});pushBuyerNotification(s,r.userId,'Shop phản hồi '+r.id,'requests.html?id='+encodeURIComponent(r.id));});rerender();toast('Đã gửi tin nhắn.');return;
  }
  if(name==='case-message'){
   const c=aftersalesCases().find(x=>x.id===form.dataset.case),text=String(d.text||'').trim();if(!c)throw Error('Không tìm thấy hồ sơ.');if(!text)throw Error('Nhập nội dung phản hồi.');
   tx(s=>{c.timeline.push({at:Date.now(),text:'Shop: '+text});pushBuyerNotification(s,c.userId,'Shop phản hồi hồ sơ '+c.id,'cases.html?id='+encodeURIComponent(c.id));});rerender();toast('Đã gửi phản hồi.');return;
  }
  if(name==='case-more'){
   const c=aftersalesCases().find(x=>x.id===form.dataset.case),text=String(d.text||'').trim();if(!c)throw Error('Không tìm thấy hồ sơ.');if(!text)throw Error('Nhập nội dung cần bổ sung.');
   tx(s=>{c.status='Cần bổ sung bằng chứng';c.timeline.push({at:Date.now(),text:'Shop yêu cầu bổ sung: '+text});pushBuyerNotification(s,c.userId,'Hồ sơ '+c.id+' cần bổ sung','cases.html?id='+encodeURIComponent(c.id));});rerender();toast('Đã gửi yêu cầu bổ sung.');return;
  }
  if(name==='case-reject'){
   const c=aftersalesCases().find(x=>x.id===form.dataset.case),reason=String(d.reason||'').trim();if(!c)throw Error('Không tìm thấy hồ sơ.');if(!reason)throw Error('Nhập lý do từ chối.');
   tx(s=>{c.status='Từ chối: '+reason;c.timeline.push({at:Date.now(),text:'Shop: '+c.status});pushBuyerNotification(s,c.userId,'Hồ sơ '+c.id+' đã được phản hồi','cases.html?id='+encodeURIComponent(c.id));});rerender();toast('Đã cập nhật kết quả hồ sơ.');return;
  }
  if(name==='case-replace'){
   const c=aftersalesCases().find(x=>x.id===form.dataset.case),serial=String(d.serial||'').trim();if(!c||c.type!=='warranty')throw Error('Không phải hồ sơ bảo hành.');if(!serial)throw Error('Nhập serial sản phẩm thay thế.');if(!['Đang gửi hàng cho shop','Đã nhận — kiểm tra bảo hành'].includes(c.status))throw Error('Cần tiếp nhận kiểm tra trước khi đổi sản phẩm.');
   tx(s=>{c.status='Đã đổi sản phẩm — chờ gửi lại hàng';c.replacementSerial=serial;c.logistics='Vận đơn gửi lại demo: '+uid('REDELIVERY');c.timeline.push({at:Date.now(),text:'Shop: Đổi sản phẩm, serial mới '+serial});pushBuyerNotification(s,c.userId,'Bảo hành '+c.id+': shop đã đổi sản phẩm','cases.html?id='+encodeURIComponent(c.id));});rerender();toast('Đã cập nhật sản phẩm thay thế.');return;
  }
  if(name==='proposal-builder'){
   const data=validateProposal(form),previous=findProposal(form.dataset.from),versions=proposals().filter(p=>p.requestId===data.r.id),version=previous?previous.version+1:Math.max(0,...versions.map(p=>p.version))+1;
   const items=Object.values(data.slots).map(x=>{const o=currentOffer(x.offerId);return {offerId:o.id,qty:1,price:o.price,warranty:o.warranty};});
   const p={id:uid('PR'),userId:data.r.userId,requestId:data.r.id,requestVersion:data.r.version,version,shopId:SHOP_ID,status:'Đã gửi',sentAt:Date.now(),expires:Date.now()+data.hours*3600000,items,fee:data.fee,assembly:data.assembly,feedback:[],note:data.note,previousId:previous?.id||undefined};
   tx(s=>{if(previous&&['Đã gửi','Cần sửa','Hết hạn'].includes(proposalState(previous)))previous.status='Đã thay thế';s.proposals.push(p);delete s.shopMeta.proposalDrafts[data.r.id];pushBuyerNotification(s,p.userId,'Có proposal mới từ '+shopInfo.name,'proposals.html?id='+encodeURIComponent(p.id));});location.href=link('proposal',{id:p.id});return;
  }
  if(name==='proposal-withdraw'){
   const p=findProposal(d.proposalId);if(!p||!['Đã gửi','Cần sửa'].includes(proposalState(p)))throw Error('Proposal không còn có thể rút.');tx(s=>{p.status='Đã rút';p.withdrawReason=d.reason;pushBuyerNotification(s,p.userId,'Proposal '+p.id+' đã được rút','requests.html?id='+encodeURIComponent(p.requestId));});location.href=link('proposal',{id:p.id});return;
  }
  if(name==='order-reject'){
   const entry=suborders().find(x=>x.sub.id===d.subId);if(!entry||entry.sub.status!=='Chờ shop xác nhận')throw Error('Đơn không còn chờ xác nhận.');const reason=d.reason+(d.note?.trim()?': '+d.note.trim():'');
   tx(()=>{entry.sub.status='Đã hủy';entry.sub.cancellation={reason,status:'Shop từ chối',requested:entry.order.payment==='paid'?entry.sub.total:0};entry.sub.timeline.push({at:Date.now(),text:'Shop từ chối đơn: '+reason});if(entry.order.payment==='paid')appendRefund(entry.sub,{id:uid('RF'),amount:entry.sub.total,requested:entry.sub.total,approved:entry.sub.total,status:'Đang xử lý'});});location.href=link('order',{sub:entry.sub.id});return;
  }
  if(name==='serials'){
   const entry=suborders().find(x=>x.sub.id===form.dataset.sub);if(!entry)throw Error('Không tìm thấy đơn.');const all=[];
   const serialMap=entry.sub.items.map((i,itemIndex)=>Array.from({length:i.qty},(_,unitIndex)=>{const value=String(d['serial-'+itemIndex+'-'+unitIndex]||'').trim();if(!value)throw Error('Nhập đủ serial cho từng sản phẩm.');all.push(value);return value;}));
   if(new Set(all).size!==all.length)throw Error('Serial không được trùng trong cùng đơn.');tx(()=>entry.sub.items.forEach((i,n)=>{i.serials=serialMap[n];i.serial=serialMap[n][0];}));rerender();toast('Đã lưu serial.');return;
  }
  if(name==='packing'){
   const id=form.dataset.sub,entry=suborders().find(x=>x.sub.id===id);if(!entry||!serialComplete(entry.sub))throw Error('Lưu đủ serial trước khi xác nhận đóng gói.');tx(s=>{s.shopMeta.packing[id]={weight:Number(d.weight),packages:Number(d.packages),size:d.size,packed:true,at:Date.now()};entry.sub.timeline.push({at:Date.now(),text:'Đã xác nhận đóng gói'});});rerender();toast('Đã xác nhận đóng gói.');return;
  }
  if(name==='shipment'){
   const entry=suborders().find(x=>x.sub.id===form.dataset.sub),meta=db().shopMeta.packing[entry.sub.id];if(!meta?.packed)throw Error('Xác nhận đóng gói trước khi tạo vận đơn.');if(!serialComplete(entry.sub))throw Error('Lưu đủ serial trước khi tạo vận đơn.');
   tx(()=>{entry.sub.deliveryService=d.service;entry.sub.tracking=uid('SHIP');entry.sub.shippingStatus='Chờ lấy hàng';entry.sub.status='Chờ lấy hàng';entry.sub.timeline.push({at:Date.now(),text:'Đã tạo vận đơn '+entry.sub.tracking});});rerender();toast('Đã tạo vận đơn.');return;
  }
 }catch(err){toast(err.message);}
});

document.addEventListener('keydown',e=>{
 if(e.key!=='Enter'||e.target?.id!=='shop-global-search')return;e.preventDefault();const q=e.target.value.trim(),u=q.toUpperCase();
 location.href=u.startsWith('BR-')||u.startsWith('REQ-')?link('build-requests',{q}):u.startsWith('PR-')?link('proposal',{id:q}):u.startsWith('CASE-')?link('aftersales',{id:q}):u.startsWith('SUB-')?link('order',{sub:q}):u.startsWith('PCM-')?link('orders',{q}):link('offers',{q});
});
