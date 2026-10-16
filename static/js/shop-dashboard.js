import {mineSeller,revenueStats,orderStats,productStats,seller,money,sdb,stx,uid,clone} from './shop-store.js';
import {esc,params,go,link,a,btn,field,select,textarea,submit,form,notice,empty,panel,head,badge,statusBadge,mount,toast,dialog,operation,requireSeller} from './shop-ui.js';
import {models,model as getModel} from './data.js';

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
    return `<div class="dash-bar" style="--h:${h}%" title="${d.label}: ${money(d.revenue)}"><div class="dash-bar__fill"></div><small>${d.label}</small></div>`;
  }).join('');

  const recentOrders=mineSeller('shopOrders').slice().reverse().slice(0,5);
  const pendingOrders=mineSeller('shopOrders').filter(o=>['Chờ xác nhận','Đang xử lý'].includes(o.status));

  mount('Dashboard',`
    <section class="sa-page-heading">
      <div>
        <div class="sa-breadcrumbs">
          <a href="${link('dashboard')}">Kênh bán</a>
          <span>/</span>
          <span>Dashboard</span>
        </div>
        <h1>Xin chào, ${esc(s.shopName||s.name)}</h1>
        <p>Tổng quan hoạt động shop hôm nay</p>
      </div>
      <div class="sa-page-actions">
        ${a('+ Sản phẩm mới','offers',{new:'1'},'primary')}
        <button type="button" class="btn btn--secondary" data-action="shop-demo">Công cụ demo</button>
      </div>
    </section>

    <section class="sa-kpi-grid" aria-label="Chỉ số tổng quan">
      <article class="sa-kpi-card sa-kpi-card--blue">
        <h2>DOANH THU THÁNG NÀY</h2>
        <div class="sa-kpi-value"><strong>${money(rev.total)}</strong></div>
        <p>${rev.orders} đơn · Trung bình ${money(rev.avg)}/ngày</p>
      </article>
      <article class="sa-kpi-card sa-kpi-card--amber">
        <h2>ĐƠN CHỜ XỬ LÝ</h2>
        <div class="sa-kpi-value"><strong>${ord.pending+ord.processing}</strong></div>
        <p>${ord.pending} chờ xác nhận · ${ord.processing} đang xử lý</p>
      </article>
      <article class="sa-kpi-card sa-kpi-card--sky">
        <h2>SẢN PHẨM ĐANG BÁN</h2>
        <div class="sa-kpi-value"><strong>${prd.active}</strong></div>
        <p>${prd.lowStock} sắp hết hàng · ${prd.inactive} đã ẩn</p>
      </article>
      <article class="sa-kpi-card sa-kpi-card--rose">
        <h2>CẦN PHẢN HỒI</h2>
        <div class="sa-kpi-value"><strong>${pendingQs+pendingAf+pendingBr}</strong></div>
        <p>${pendingQs} câu hỏi · ${pendingAf} hậu mãi · ${pendingBr} build</p>
      </article>
    </section>

    <div style="display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:20px;margin-bottom:20px">
      <div class="sa-table-card">
        <div class="sa-table-toolbar">
          <h2 style="margin:0;font-size:15px;font-weight:700;color:#0f172a">Doanh thu 14 ngày gần nhất</h2>
          ${a('Xem báo cáo đầy đủ →','revenue','','sa-detail-btn')}
        </div>
        <div style="padding:20px 16px 16px">
          <div class="dash-bar-chart">${barChart}</div>
        </div>
      </div>
      <div class="stack">
        <div class="sa-table-card">
          <div class="sa-table-toolbar">
            <h2 style="margin:0;font-size:14px;font-weight:700;color:#0f172a">Đơn hàng cần xử lý</h2>
            ${pendingOrders.length>5?a('Xem tất cả','orders','','sa-detail-btn'):''}
          </div>
          <div style="padding:0 0 4px">
            ${pendingOrders.slice(0,5).map(o=>`
              <div class="dash-order-row" style="padding:12px 16px">
                <div><strong>${esc(o.buyerName)}</strong><p>${money(o.total)} · ${statusBadge(o.status)}</p></div>
                ${a('Xem','order',{id:o.id},'sa-detail-btn')}
              </div>
            `).join('')||'<p style="padding:16px;color:#94a3b8;margin:0;font-size:13px">Không có đơn chờ xử lý.</p>'}
          </div>
        </div>
        <div class="sa-table-card">
          <div class="sa-table-toolbar">
            <h2 style="margin:0;font-size:14px;font-weight:700;color:#0f172a">Câu hỏi chưa trả lời</h2>
            ${pendingQs>3?a('Xem tất cả','questions','','sa-detail-btn'):''}
          </div>
          <div style="padding:0 0 4px">
            ${mineSeller('shopQuestions').filter(q=>!q.answered).slice(0,3).map(q=>`
              <div class="dash-order-row" style="padding:12px 16px">
                <div><strong>${esc(q.buyerName)}</strong><p style="color:#94a3b8;font-size:12px;margin:2px 0 0">${esc(q.question.slice(0,55))}…</p></div>
                ${a('Trả lời','questions',{id:q.id},'sa-detail-btn')}
              </div>
            `).join('')||'<p style="padding:16px;color:#94a3b8;margin:0;font-size:13px">Không có câu hỏi mới.</p>'}
          </div>
        </div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px">
      <div class="sa-table-card">
        <div class="sa-table-toolbar">
          <h2 style="margin:0;font-size:14px;font-weight:700;color:#0f172a">Đơn hàng gần nhất</h2>
          ${a('Tất cả đơn','orders','','sa-detail-btn')}
        </div>
        <div style="padding:0 0 4px">
          ${recentOrders.map(o=>`
            <div class="dash-order-row" style="padding:10px 16px">
              <div>
                <strong style="font-size:12px;color:#0f172a">${esc(o.id)}</strong>
                <p style="color:#94a3b8;font-size:11px;margin:2px 0 0">${esc(o.buyerName)} · ${money(o.total)}</p>
              </div>
              ${statusBadge(o.status)}
            </div>
          `).join('')||'<p style="padding:16px;color:#94a3b8;margin:0;font-size:13px">Chưa có đơn hàng.</p>'}
        </div>
      </div>
      <div class="sa-table-card">
        <div class="sa-table-toolbar">
          <h2 style="margin:0;font-size:14px;font-weight:700;color:#0f172a">Tình trạng tồn kho</h2>
          ${a('Quản lý kho','inventory','','sa-detail-btn')}
        </div>
        <div style="padding:12px 16px;display:grid;gap:10px">
          ${(()=>{
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
            ].map(r=>`
              <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 10px;border-radius:8px;background:${r.bg}">
                <span style="font-size:13px;color:${r.color};font-weight:500">${r.label}</span>
                <strong style="font-size:16px;color:${r.color}">${r.count}</strong>
              </div>
            `).join('');
          })()}
        </div>
      </div>
      <div class="sa-table-card">
        <div class="sa-table-toolbar">
          <h2 style="margin:0;font-size:14px;font-weight:700;color:#0f172a">Trạng thái đơn hàng</h2>
          ${a('Tất cả đơn','orders','','sa-detail-btn')}
        </div>
        <div style="padding:12px 16px;display:grid;gap:10px">
          ${(()=>{
            const allOrders=mineSeller('shopOrders');
            return [
              {label:'Chờ xác nhận',count:allOrders.filter(o=>o.status==='Chờ xác nhận').length,color:'#92400e',bg:'#fef3c7'},
              {label:'Đang xử lý',count:allOrders.filter(o=>o.status==='Đang xử lý').length,color:'#1e40af',bg:'#dbeafe'},
              {label:'Đang giao',count:allOrders.filter(o=>o.status==='Đang giao').length,color:'#0891b2',bg:'#e0f2fe'},
              {label:'Đã giao',count:allOrders.filter(o=>o.status==='Đã giao').length,color:'#166534',bg:'#dcfce7'},
              {label:'Đã hủy',count:allOrders.filter(o=>o.status==='Đã hủy').length,color:'#991b1b',bg:'#fee2e2'},
            ].map(r=>`
              <div style="display:flex;justify-content:space-between;align-items:center;padding:7px 10px;border-radius:8px;background:${r.bg}">
                <span style="font-size:12px;color:${r.color};font-weight:500">${r.label}</span>
                <strong style="font-size:15px;color:${r.color}">${r.count}</strong>
              </div>
            `).join('');
          })()}
        </div>
      </div>
    </div>
  `);
}

export function revenue(){
  if(!requireSeller())return;
  const rev=revenueStats();
  const period=params.get('period')||'30';
  const days=parseInt(period);
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
  const periodOrders=allOrders.slice(-totalOrders);
  const deliveredCount=allOrders.filter(o=>o.status==='Đã giao').length;
  const cancelledCount=allOrders.filter(o=>o.status==='Đã hủy').length;
  const returnCount=allOrders.filter(o=>o.status==='Đã hoàn hàng').length;
  const successRate=allOrders.length>0?Math.round(deliveredCount/allOrders.length*100):0;

  const products=mineSeller('shopProducts');
  const topProducts=products.slice().sort((a,b)=>(b.sold||0)-(a.sold||0)).slice(0,5);

  mount('Doanh thu',`
    <section class="sa-page-heading">
      <div>
        <div class="sa-breadcrumbs">
          <a href="${link('dashboard')}">Kênh bán</a>
          <span>/</span>
          <span>Báo cáo doanh thu</span>
        </div>
        <h1>Báo cáo doanh thu</h1>
        <p>Thống kê doanh số và đơn hàng của shop</p>
      </div>
      <div class="sa-page-actions">
        ${form('rev-filter',`<div style="display:flex;gap:8px;align-items:center">${select('','period',{'7':'7 ngày','14':'14 ngày','30':'30 ngày'},period,'class="sa-filter-select"')}${submit('Áp dụng')}</div>`)}
      </div>
    </section>

    <section class="sa-kpi-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:20px">
      <article class="sa-kpi-card sa-kpi-card--blue">
        <h2>TỔNG DOANH THU</h2>
        <div class="sa-kpi-value"><strong>${money(totalRevenue)}</strong></div>
        <p>${days} ngày vừa qua</p>
      </article>
      <article class="sa-kpi-card sa-kpi-card--sky">
        <h2>TỔNG ĐƠN HÀNG</h2>
        <div class="sa-kpi-value"><strong>${totalOrders}</strong><span>đơn</span></div>
        <p>Đã hoàn thành trong kỳ</p>
      </article>
      <article class="sa-kpi-card sa-kpi-card--amber">
        <h2>GIÁ TRỊ TB/ĐƠN</h2>
        <div class="sa-kpi-value"><strong>${money(avgOrder)}</strong></div>
        <p>Trung bình mỗi đơn</p>
      </article>
      <article class="sa-kpi-card sa-kpi-card--rose">
        <h2>TỶ LỆ GIAO THÀNH CÔNG</h2>
        <div class="sa-kpi-value"><strong>${successRate}%</strong></div>
        <p>${deliveredCount} đã giao / ${allOrders.length} tổng đơn</p>
      </article>
    </section>

    <div style="display:grid;grid-template-columns:minmax(0,2fr) minmax(0,1fr);gap:20px;margin-bottom:20px">
      <div class="sa-table-card">
        <div class="sa-table-toolbar">
          <h2 style="margin:0;font-size:15px;font-weight:700;color:#0f172a">Doanh thu theo ngày</h2>
          <span style="font-size:12px;color:#64748b">Đơn vị: VNĐ</span>
        </div>
        <div style="padding:16px">
          <div class="shop-revenue-bars" style="--days:${data.length}">
            ${data.map(d=>{
              const h=Math.round(d.revenue/maxRev*100);
              return `<div class="shop-revenue-bar">
                <div class="shop-revenue-bar__value">${money(d.revenue).replace('₫','').trim()}</div>
                <div class="shop-revenue-bar__track"><i style="--bar:${h}%"></i></div>
                <small>${d.label}</small>
              </div>`;
            }).join('')}
          </div>
        </div>
      </div>
      <div class="sa-table-card">
        <div class="sa-table-toolbar">
          <h2 style="margin:0;font-size:15px;font-weight:700;color:#0f172a">Cơ cấu theo ngành</h2>
        </div>
        <div style="padding:16px">
          <div class="shop-revenue-pie" style="grid-template-columns:1fr">
            <div class="shop-revenue-donut" style="--donut:${donutGrad};width:160px;height:160px;margin:0 auto 16px">
              <div><strong style="font-size:14px">${money(totalRevenue).replace('₫','').trim()}</strong><span>tổng</span></div>
            </div>
            <div class="shop-revenue-legend">
              ${categories.map(c=>`<div><i style="background:${c.color}"></i><span>${esc(c.label)}</span><strong>${c.pct}%</strong><small>${money(Math.round(totalRevenue*c.pct/100))}</small></div>`).join('')}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div style="display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:20px">
      <div class="sa-table-card">
        <div class="sa-table-toolbar">
          <h2 style="margin:0;font-size:14px;font-weight:700;color:#0f172a">Sản phẩm bán chạy nhất</h2>
          ${a('Xem tất cả sản phẩm','offers','','sa-detail-btn')}
        </div>
        <div class="table-scroll">
          <table style="min-width:0">
            <thead><tr>
              <th>#</th><th>SẢN PHẨM</th><th class="center">ĐÃ BÁN</th><th>GIÁ</th><th class="center">TỒN</th>
            </tr></thead>
            <tbody>
              ${topProducts.length?topProducts.map((p,i)=>`<tr>
                <td><strong style="color:#94a3b8;font-size:13px">${i+1}</strong></td>
                <td><strong>${esc(p.name)}</strong><small>${esc(p.brand||'')}</small></td>
                <td class="center"><strong>${p.sold||0}</strong></td>
                <td>${money(p.price)}</td>
                <td class="center"><span style="color:${p.stock===0?'#dc2626':p.stock<=3?'#d97706':'#166534'}">${p.stock}</span></td>
              </tr>`).join(''):`<tr><td colspan="5" style="text-align:center;color:#94a3b8;padding:32px">Chưa có dữ liệu bán hàng</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
      <div class="sa-table-card">
        <div class="sa-table-toolbar">
          <h2 style="margin:0;font-size:14px;font-weight:700;color:#0f172a">Tổng kết đơn hàng</h2>
        </div>
        <div style="padding:16px;display:grid;gap:12px">
          ${[
            {label:'Tổng đơn phát sinh',count:allOrders.length,color:'#0f172a',bg:'#f8fafc'},
            {label:'Đã giao thành công',count:deliveredCount,color:'#166534',bg:'#dcfce7'},
            {label:'Đã hủy',count:cancelledCount,color:'#991b1b',bg:'#fee2e2'},
            {label:'Hoàn hàng',count:returnCount,color:'#92400e',bg:'#fef3c7'},
            {label:'Đang xử lý / giao',count:allOrders.filter(o=>['Đang xử lý','Đang giao'].includes(o.status)).length,color:'#1e40af',bg:'#dbeafe'},
          ].map(r=>`
            <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 12px;border-radius:8px;background:${r.bg}">
              <span style="font-size:13px;color:${r.color};font-weight:500">${r.label}</span>
              <strong style="font-size:18px;color:${r.color};font-variant-numeric:tabular-nums">${r.count}</strong>
            </div>
          `).join('')}
          <div style="padding:10px 12px;border-radius:8px;background:#eff6ff;border:1px solid #dbeafe">
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-size:13px;color:#1e40af;font-weight:600">Tỷ lệ giao thành công</span>
              <strong style="font-size:20px;color:#1e40af">${successRate}%</strong>
            </div>
            <div style="margin-top:8px;height:6px;border-radius:99px;background:#dbeafe;overflow:hidden">
              <div style="height:100%;width:${successRate}%;background:#2563eb;border-radius:99px;transition:width .4s"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `);
}

export function action(act,id){
  return false;
}

export async function submitForm(name,f,d){
  if(name==='rev-filter'){go('revenue',{period:d.period});return true;}
  return false;
}
