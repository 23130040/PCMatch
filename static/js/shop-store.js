import {models,shops,offers,money} from './data.js';
const KEY='pcmatch-shop-v1';
export {money,shops};
export const uid=prefix=>prefix+'-'+crypto.randomUUID().slice(0,8).toUpperCase();
export const clone=x=>JSON.parse(JSON.stringify(x));

const initial=()=>({
  version:1,
  sellers:[],
  shopProducts:[],
  shopOrders:[],
  shopQuestions:[],
  shopProposals:[],
  shopBuildRequests:[],
  shopAftersales:[],
  shopRevenue:[],
  shopInventoryAlerts:[]
});

let state;
try{state=JSON.parse(localStorage.getItem(KEY))||initial();if(state.version!==1)throw Error();}
catch{state=initial();}
try{localStorage.setItem(KEY,JSON.stringify(state));}catch{}

export const sdb=()=>state;
export function ssave(){try{localStorage.setItem(KEY,JSON.stringify(state));}catch{throw Error('Không lưu được dữ liệu shop. Kiểm tra dung lượng trình duyệt rồi thử lại.');}}
export function stx(fn){const before=clone(state);try{const r=fn(state);ssave();return r;}catch(e){state=JSON.parse(JSON.stringify(before));throw e;}}

export function seller(){
  try{
    const s=JSON.parse(sessionStorage.getItem('pcmatch-shop-session'));
    return s&&s.expires>Date.now()?state.sellers.find(u=>u.id===s.sellerId&&!u.suspended):null;
  }catch{return null;}
}
export function shopLogin(s){
  sessionStorage.setItem('pcmatch-shop-session',JSON.stringify({sellerId:s.id,expires:Date.now()+3600000*8}));
}
export function shopLogout(){
  sessionStorage.removeItem('pcmatch-shop-session');
}
export async function fingerprint(text){
  const b=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text));
  return Array.from(new Uint8Array(b)).map(x=>x.toString(16).padStart(2,'0')).join('');
}
export const mineSeller=collection=>state[collection].filter(x=>x.sellerId===seller()?.id);

const STATUSES_ALL=['Chờ xác nhận','Đang xử lý','Đang giao','Đã giao','Đã hủy','Chờ hoàn hàng','Đã hoàn hàng'];

function seedShopData(sel){
  const shopId=sel.shopId;
  if(state.shopProducts.some(p=>p.sellerId===sel.id))return;

  const baseProducts=models.slice(0,8).map((m,i)=>({
    id:uid('SP'),
    sellerId:sel.id,
    shopId,
    modelId:m.id,
    name:m.name,
    category:m.category,
    brand:m.brand,
    price:m.price+(i%3===0?50000:-50000),
    stock:5+i*3,
    sold:10+i*7,
    active:i!==6,
    createdAt:Date.now()-i*86400000*15,
    images:[],
    description:m.description||'Sản phẩm chính hãng.'
  }));
  state.shopProducts.push(...baseProducts);

  const orderItems=baseProducts.slice(0,5).map((p,i)=>({
    id:uid('SI'),
    productId:p.id,
    name:p.name,
    qty:1+i%3,
    price:p.price,
    modelId:p.modelId
  }));
  const orders=[
    {id:uid('SO'),sellerId:sel.id,shopId,buyerName:'Nguyễn Văn An',buyerPhone:'0912345678',address:'45 Lê Lợi, Q.1, TP.HCM',status:'Đã giao',payment:'Đã thanh toán',total:orderItems[0].price*orderItems[0].qty+orderItems[1].price*orderItems[1].qty,items:[orderItems[0],orderItems[1]],shippingService:'Tiêu chuẩn',tracking:'SHIP-'+uid('TR'),createdAt:Date.now()-864000000*3,deliveredAt:Date.now()-86400000,timeline:[{at:Date.now()-864000000*3,text:'Tạo đơn'},{at:Date.now()-86400000*2,text:'Đang giao'},{at:Date.now()-86400000,text:'Đã giao'}]},
    {id:uid('SO'),sellerId:sel.id,shopId,buyerName:'Trần Thị Bình',buyerPhone:'0987654321',address:'12 Nguyễn Huệ, Hà Nội',status:'Chờ xác nhận',payment:'Đã thanh toán',total:orderItems[2].price*orderItems[2].qty,items:[orderItems[2]],shippingService:'Nhanh',tracking:null,createdAt:Date.now()-3600000*5,deliveredAt:null,timeline:[{at:Date.now()-3600000*5,text:'Tạo đơn'}]},
    {id:uid('SO'),sellerId:sel.id,shopId,buyerName:'Lê Minh Cường',buyerPhone:'0908765432',address:'78 Trần Phú, Đà Nẵng',status:'Đang xử lý',payment:'Đã thanh toán',total:orderItems[3].price,items:[{...orderItems[3],qty:1}],shippingService:'Tiêu chuẩn',tracking:null,createdAt:Date.now()-3600000*12,deliveredAt:null,timeline:[{at:Date.now()-3600000*12,text:'Tạo đơn'},{at:Date.now()-3600000*8,text:'Shop xác nhận'}]},
    {id:uid('SO'),sellerId:sel.id,shopId,buyerName:'Phạm Thị Dung',buyerPhone:'0901234567',address:'23 Võ Thị Sáu, TP.HCM',status:'Đang giao',payment:'Đã thanh toán',total:orderItems[4].price*2,items:[{...orderItems[4],qty:2}],shippingService:'Tiêu chuẩn',tracking:'SHIP-'+uid('TR'),createdAt:Date.now()-86400000*2,deliveredAt:null,timeline:[{at:Date.now()-86400000*2,text:'Tạo đơn'},{at:Date.now()-86400000,text:'Đang giao'}]},
    {id:uid('SO'),sellerId:sel.id,shopId,buyerName:'Hoàng Văn Em',buyerPhone:'0919876543',address:'56 Bà Triệu, Hà Nội',status:'Đã hủy',payment:'Đã hoàn tiền',total:orderItems[0].price,items:[{...orderItems[0],qty:1}],shippingService:'Tiêu chuẩn',tracking:null,createdAt:Date.now()-86400000*5,deliveredAt:null,timeline:[{at:Date.now()-86400000*5,text:'Tạo đơn'},{at:Date.now()-86400000*4,text:'Đã hủy theo yêu cầu'}]}
  ];
  state.shopOrders.push(...orders);

  const questions=[
    {id:uid('QS'),sellerId:sel.id,shopId,buyerName:'Khách ẩn danh',productName:baseProducts[0].name,question:'Sản phẩm này có tương thích với mainboard B650 không?',answer:null,answered:false,createdAt:Date.now()-3600000*4},
    {id:uid('QS'),sellerId:sel.id,shopId,buyerName:'Người mua B',productName:baseProducts[1].name,question:'Còn hàng không shop ơi? Mình cần gấp.',answer:'Còn hàng bạn nhé! Mình giao trong ngày với đơn trước 14h.',answered:true,answeredAt:Date.now()-1800000,createdAt:Date.now()-7200000},
    {id:uid('QS'),sellerId:sel.id,shopId,buyerName:'Khách C',productName:baseProducts[2].name,question:'Sản phẩm có bảo hành tại nhà không?',answer:null,answered:false,createdAt:Date.now()-86400000}
  ];
  state.shopQuestions.push(...questions);

  const buildRequests=[
    {id:uid('BR'),sellerId:sel.id,shopId,buyerName:'Anh Hùng',budget:15000000,purpose:'Gaming 1080p',notes:'Ưu tiên CPU + GPU mạnh, RAM 16GB+',status:'Mới',createdAt:Date.now()-7200000,offers:[]},
    {id:uid('BR'),sellerId:sel.id,shopId,buyerName:'Chị Mai',budget:8000000,purpose:'Văn phòng / học tập',notes:'Cần ổn định, ít tiếng ồn, có tản nhiệt rời',status:'Đã gửi báo giá',createdAt:Date.now()-86400000*2,offers:[{modelId:models[0].id,price:models[0].price,qty:1},{modelId:models[3].id,price:models[3].price,qty:1},{modelId:models[5].id,price:models[5].price,qty:1}]},
    {id:uid('BR'),sellerId:sel.id,shopId,buyerName:'Bạn Nam',budget:20000000,purpose:'Đồ họa / Render',notes:'Cần GPU mạnh nhất có thể, tản nhiệt nước',status:'Đang thương lượng',createdAt:Date.now()-86400000*3,offers:[{modelId:models[6].id,price:models[6].price,qty:1},{modelId:models[8].id,price:models[8].price,qty:1}]}
  ];
  state.shopBuildRequests.push(...buildRequests);

  const aftersales=[
    {id:uid('AF'),sellerId:sel.id,shopId,orderId:orders[0].id,buyerName:orders[0].buyerName,type:'Đổi/trả',productName:baseProducts[0].name,reason:'Sản phẩm lỗi khi nhận',status:'Chờ xử lý',createdAt:Date.now()-3600000*10,logs:[{at:Date.now()-3600000*10,text:'Khách gửi yêu cầu đổi/trả'}]},
    {id:uid('AF'),sellerId:sel.id,shopId,orderId:orders[0].id,buyerName:orders[0].buyerName,type:'Bảo hành',productName:baseProducts[1].name,reason:'CPU không nhận boot sau 2 ngày sử dụng',status:'Đang xử lý',createdAt:Date.now()-86400000*2,logs:[{at:Date.now()-86400000*2,text:'Tiếp nhận hồ sơ bảo hành'},{at:Date.now()-86400000,text:'Shop đang kiểm tra thiết bị'}]}
  ];
  state.shopAftersales.push(...aftersales);

  const now=Date.now();
  const revenueData=[];
  for(let i=29;i>=0;i--){
    const d=new Date(now-i*86400000);
    revenueData.push({
      date:d.toISOString().slice(0,10),
      revenue:Math.floor(Math.random()*15000000+2000000),
      orders:Math.floor(Math.random()*12+1),
      label:`${d.getDate()}/${d.getMonth()+1}`
    });
  }
  state.shopRevenue.push(...revenueData.map(r=>({...r,sellerId:sel.id})));

  ssave();
}

export function getOrCreateDemoSeller(){
  let sel=state.sellers.find(s=>s.email==='shop@pcmatch.local');
  if(!sel){
    const shop=shops.find(s=>s.active)||shops[0];
    sel={
      id:uid('SELLER'),
      name:'BuildPro Demo',
      email:'shop@pcmatch.local',
      password:'',
      shopId:shop.id,
      shopName:shop.name,
      phone:'0901234567',
      address:'Tầng 3, 123 Nguyễn Trãi, Q.5, TP.HCM',
      businessType:'Cá nhân kinh doanh',
      taxCode:'0312345678',
      category:'Linh kiện máy tính',
      joinedAt:Date.now()-86400000*180,
      suspended:false,
      verified:true,
      rating:4.8,
      totalProducts:0,
      totalSold:0
    };
    state.sellers.push(sel);
    seedShopData(sel);
  }
  return sel;
}

export function revenueStats(){
  const data=mineSeller('shopRevenue');
  if(!data.length)return{total:0,avg:0,orders:0,days:[]};
  const total=data.reduce((s,d)=>s+d.revenue,0);
  const orders=data.reduce((s,d)=>s+d.orders,0);
  return{total,avg:Math.round(total/data.length),orders,days:data.slice(-30)};
}

export function orderStats(){
  const orders=mineSeller('shopOrders');
  const pending=orders.filter(o=>o.status==='Chờ xác nhận').length;
  const processing=orders.filter(o=>o.status==='Đang xử lý').length;
  const delivering=orders.filter(o=>o.status==='Đang giao').length;
  const done=orders.filter(o=>o.status==='Đã giao').length;
  return{pending,processing,delivering,done,total:orders.length};
}

export function productStats(){
  const products=mineSeller('shopProducts');
  const active=products.filter(p=>p.active).length;
  const inactive=products.filter(p=>!p.active).length;
  const lowStock=products.filter(p=>p.active&&p.stock<=3).length;
  return{active,inactive,lowStock,total:products.length};
}
