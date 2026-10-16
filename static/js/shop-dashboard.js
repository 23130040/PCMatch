import {renderTemplate,esc,params,go,link,a,select,submit,form,statusBadge,mount,requireSeller} from './shop-ui.js';
import {mineSeller,revenueStats,orderStats,productStats,seller,money} from './shop-store.js';

export function dashboard(){
  if(!requireSeller())return;
  const s=seller();
  const rev=revenueStats();
  const ord=orderStats();
  const prd=productStats();
  const pendingQs=mineSeller('shopQuestions').filter(q=>!q.answered).length;
  const pendingAf=mineSeller('shopAftersales').filter(a=>a.status==='Chờ xử lý').length;
  const pendingBr=mineSeller('shopBuildRequests').filter(b=>b.status==='Mới').length;

  const maxRev=Math.max(...rev.days.map(d=>d.revenue),1);
  const barChart=rev.days.slice(-14).map(d=>{
    const h=Math.round(d.revenue/maxRev*100);
    return renderTemplate("shop-dashboard-barChart-1", {
      h: h,
      label: d.label,
      revenueMoney: money(d.revenue),
      label2: d.label
    });
  }).join('');

  const recentOrders=mineSeller('shopOrders').slice().reverse().slice(0,5);
  const pendingOrders=mineSeller('shopOrders').filter(o=>['Chờ xác nhận','Đang xử lý'].includes(o.status));

  mount('Dashboard',renderTemplate("shop-dashboard-dashboard-7", {
    dashboardUrl: link('dashboard'),
    shopName: esc(s.shopName||s.name),
    offersLink: a('+ Sản phẩm mới','offers',{new:'1'},'primary'),
    totalMoney: money(rev.total),
    orders: rev.orders,
    avgMoney: money(rev.avg),
    pending: ord.pending+ord.processing,
    pending2: ord.pending,
    processing: ord.processing,
    active: prd.active,
    lowStock: prd.lowStock,
    inactive: prd.inactive,
    pendingQs: pendingQs+pendingAf+pendingBr,
    pendingQs2: pendingQs,
    pendingAf: pendingAf,
    pendingBr: pendingBr,
    revenueLink: a('Xem báo cáo đầy đủ →','revenue','','sa-detail-btn'),
    barChart: barChart,
    lengthContent: pendingOrders.length>5?a('Xem tất cả','orders','','sa-detail-btn'):'',
    sliceRows: pendingOrders.slice(0,5).map(o=>renderTemplate("shop-dashboard-dashboard-1", {
      buyerName: esc(o.buyerName),
      totalMoney: money(o.total),
      statusBadge: statusBadge(o.status),
      orderLink: a('Xem','order',{id:o.id},'sa-detail-btn')
    })).join('')||renderTemplate("shop-dashboard-dashboard-2"),
    pendingQsContent: pendingQs>3?a('Xem tất cả','questions','','sa-detail-btn'):'',
    sliceRows2: mineSeller('shopQuestions').filter(q=>!q.answered).slice(0,3).map(q=>renderTemplate("shop-dashboard-dashboard-3", {
      buyerName: esc(q.buyerName),
      slice: esc(q.question.slice(0,55)),
      questionsLink: a('Trả lời','questions',{id:q.id},'sa-detail-btn')
    })).join('')||renderTemplate("shop-dashboard-dashboard-4"),
    ordersLink: a('Tất cả đơn','orders','','sa-detail-btn'),
    recentOrdersRows: recentOrders.map(o=>renderTemplate("shop-dashboard-dashboard-5", {
      id: esc(o.id),
      buyerName: esc(o.buyerName),
      totalMoney: money(o.total),
      statusBadge: statusBadge(o.status)
    })).join('')||renderTemplate("shop-dashboard-dashboard-6"),
    inventoryLink: a('Quản lý kho','inventory','','sa-detail-btn'),
    content: (()=>{
            const prods=mineSeller('shopProducts');
            const ok=prods.filter(p=>p.active&&p.stock>3).length;
            const low=prods.filter(p=>p.active&&p.stock>0&&p.stock<=3).length;
            const out=prods.filter(p=>p.active&&p.stock===0).length;
            const hidden=prods.filter(p=>!p.active).length;
            return [
              {label:'Còn hàng tốt',count:ok,color:'#166534',bg:'#dcfce7'},
              {label:'Sắp hết (≤3)',count:low,color:'#92400e',bg:'#fef3c7'},
              {label:'Hết hàng',count:out,color:'#991b1b',bg:'#fee2e2'},
              {label:'Đang ẩn',count:hidden,color:'#475569',bg:'#f1f5f9'},
            ].map(r=>renderTemplate("shop-dashboard-dashboard-8", {
      bg: r.bg,
      color: r.color,
      label: r.label,
      color2: r.color,
      count: r.count
    })).join('');
          })(),
    ordersLink2: a('Tất cả đơn','orders','','sa-detail-btn'),
    content2: (()=>{
            const allOrders=mineSeller('shopOrders');
            return [
              {label:'Chờ xác nhận',count:allOrders.filter(o=>o.status==='Chờ xác nhận').length,color:'#92400e',bg:'#fef3c7'},
              {label:'Đang xử lý',count:allOrders.filter(o=>o.status==='Đang xử lý').length,color:'#1e40af',bg:'#dbeafe'},
              {label:'Đang giao',count:allOrders.filter(o=>o.status==='Đang giao').length,color:'#0891b2',bg:'#e0f2fe'},
              {label:'Đã giao',count:allOrders.filter(o=>o.status==='Đã giao').length,color:'#166534',bg:'#dcfce7'},
              {label:'Đã hủy',count:allOrders.filter(o=>o.status==='Đã hủy').length,color:'#991b1b',bg:'#fee2e2'},
            ].map(r=>renderTemplate("shop-dashboard-dashboard-9", {
      bg: r.bg,
      color: r.color,
      label: r.label,
      color2: r.color,
      count: r.count
    })).join('');
          })()
  }));
}

export function revenue(){
  if(!requireSeller())return;
  const rev=revenueStats();
  const period=params.get('period')||'30';
  const days=['7','14','30'].includes(period)?Number(period):30;
  const data=rev.days.slice(-days);
  const maxRev=Math.max(...data.map(d=>d.revenue),1);
  const totalRevenue=data.reduce((s,d)=>s+d.revenue,0);
  const totalOrders=data.reduce((s,d)=>s+d.orders,0);
  const avgOrder=totalOrders?Math.round(totalRevenue/totalOrders):0;

  const categories=[
    {label:'CPU & Mainboard',pct:32,color:'#1e40af'},
    {label:'RAM & SSD',pct:24,color:'#0891b2'},
    {label:'GPU & Card đồ họa',pct:21,color:'#059669'},
    {label:'Vỏ máy & PSU',pct:14,color:'#d97706'},
    {label:'Tản nhiệt & Phụ kiện',pct:9,color:'#7c3aed'}
  ];
  let pctAccum=0;
  const donutGrad=categories.map(c=>{
    const from=pctAccum;pctAccum+=c.pct;
    return `${c.color} ${from}% ${pctAccum}%`;
  }).join(', ');

  const allOrders=mineSeller('shopOrders');
  const deliveredCount=allOrders.filter(o=>o.status==='Đã giao').length;
  const cancelledCount=allOrders.filter(o=>o.status==='Đã hủy').length;
  const returnCount=allOrders.filter(o=>o.status==='Đã hoàn hàng').length;
  const successRate=allOrders.length>0?Math.round(deliveredCount/allOrders.length*100):0;

  const products=mineSeller('shopProducts');
  const topProducts=products.slice().sort((a,b)=>(b.sold||0)-(a.sold||0)).slice(0,5);

  mount('Doanh thu',renderTemplate("shop-dashboard-revenue-3", {
    dashboardUrl: link('dashboard'),
    revFilterForm: form('rev-filter',renderTemplate("shop-dashboard-revenue-4", {
      periodField: select('','period',{'7':'7 ngày','14':'14 ngày','30':'30 ngày'},period,'class="sa-filter-select"'),
      content: submit('Áp dụng')
    })),
    totalRevenueMoney: money(totalRevenue),
    days: days,
    totalOrders: totalOrders,
    avgOrderMoney: money(avgOrder),
    successRate: successRate,
    deliveredCount: deliveredCount,
    length: allOrders.length,
    length2: data.length,
    dataRows: data.map(d=>{
              const h=Math.round(d.revenue/maxRev*100);
              return renderTemplate("shop-dashboard-revenue-1", {
      trim: money(d.revenue).replace('₫','').trim(),
      h: h,
      label: d.label
    });
            }).join(''),
    donutGrad: donutGrad,
    trim: money(totalRevenue).replace('₫','').trim(),
    categoriesRows: categories.map(c=>renderTemplate("shop-dashboard-revenue-2", {
      color: c.color,
      label: esc(c.label),
      pct: c.pct,
      roundMoney: money(Math.round(totalRevenue*c.pct/100))
    })).join(''),
    offersLink: a('Xem tất cả sản phẩm','offers','','sa-detail-btn'),
    lengthContent: topProducts.length?topProducts.map((p,i)=>renderTemplate("shop-dashboard-revenue-5", {
      i: i+1,
      name: esc(p.name),
      brand: esc(p.brand||''),
      sold: p.sold||0,
      priceMoney: money(p.price),
      stockContent: p.stock===0?'#dc2626':p.stock<=3?'#d97706':'#166534',
      stock: p.stock
    })).join(''):renderTemplate("shop-dashboard-revenue-6"),
    contentRows: [
            {label:'Tổng đơn phát sinh',count:allOrders.length,color:'#0f172a',bg:'#f8fafc'},
            {label:'Đã giao thành công',count:deliveredCount,color:'#166534',bg:'#dcfce7'},
            {label:'Đã hủy',count:cancelledCount,color:'#991b1b',bg:'#fee2e2'},
            {label:'Hoàn hàng',count:returnCount,color:'#92400e',bg:'#fef3c7'},
            {label:'Đang xử lý / giao',count:allOrders.filter(o=>['Đang xử lý','Đang giao'].includes(o.status)).length,color:'#1e40af',bg:'#dbeafe'},
          ].map(r=>renderTemplate("shop-dashboard-revenue-7", {
      bg: r.bg,
      color: r.color,
      label: r.label,
      color2: r.color,
      count: r.count
    })).join(''),
    successRate2: successRate,
    successRate3: successRate
  }));
}

export function action(act,id){
  return false;
}

export async function submitForm(name,f,d){
  if(name==='rev-filter'){go('revenue',{period:d.period});return true;}
  return false;
}
