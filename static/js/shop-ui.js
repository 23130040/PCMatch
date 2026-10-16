import {pageName,pageUrl} from './routing.js';
import {seller,shopLogout} from './shop-store.js';

export const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const page=pageName;
export const params=new URLSearchParams(location.search);
export const link=(p,args={})=>pageUrl('shop',p,args);
export const go=(p,args)=>location.href=link(p,args);

export const btn=(text,action,data='',kind='secondary')=>'<button type="button" class="btn btn--'+kind+'" data-action="'+action+'" data-id="'+esc(data)+'">'+text+'</button>';
export const a=(text,p,args={},kind='secondary')=>'<a class="btn btn--'+kind+'" href="'+link(p,args)+'">'+text+'</a>';
export const field=(label,name,value='',type='text',attrs='')=>'<label class="field"><span>'+label+'</span><input name="'+name+'" type="'+type+'" value="'+esc(value)+'" '+attrs+'></label>';
export const select=(label,name,options,value='',attrs='')=>'<label class="field"><span>'+label+'</span><select name="'+name+'" '+attrs+'>'+Object.entries(options).map(([k,v])=>'<option value="'+esc(k)+'" '+(k===String(value)?'selected':'')+'>'+esc(v)+'</option>').join('')+'</select></label>';
export const textarea=(label,name,value='',attrs='required')=>'<label class="field"><span>'+label+'</span><textarea name="'+name+'" '+attrs+'>'+esc(value)+'</textarea></label>';
export const submit=text=>'<button class="btn btn--primary" type="submit">'+text+'</button>';
export const form=(id,body)=>'<form data-form="'+id+'" class="stack">'+body+'<p class="form-error" role="alert"></p></form>';
export const notice=(text,type='info')=>'<div class="message message--'+type+'">'+text+'</div>';
export const empty=(title,text,action='')=>'<section class="sa-empty"><h2>'+title+'</h2><p>'+text+'</p>'+action+'</section>';
export const panel=(title,body)=>'<section class="panel panel--padded"><h2>'+title+'</h2>'+body+'</section>';
export const head=(title,desc='',actions='')=>'<div class="sa-page-heading"><div><h1>'+esc(title)+'</h1>'+(desc?'<p>'+esc(desc)+'</p>':'')+'</div><div class="sa-page-actions">'+actions+'</div></div>';
export const badge=(text,type='default')=>'<span class="sa-badge sa-badge--'+type+'">'+esc(text)+'</span>';

const STATUS_TYPES={
  'Chờ xác nhận':'warn','Đang xử lý':'info','Đang giao':'info',
  'Đã giao':'success','Đã hủy':'error','Chờ hoàn hàng':'warn',
  'Đã hoàn hàng':'default','Chờ xử lý':'warn','Đang xử lý aftersales':'info',
  'Đã giải quyết':'success','Từ chối':'error','Mới':'info',
  'Đã gửi báo giá':'success','Đang thương lượng':'warn','Đã chốt':'success',
  'Đã hủy báo giá':'error'
};
export const statusBadge=text=>badge(text,STATUS_TYPES[text]||'default');

export function mount(title,content){
  document.title=title+' - PCMatch Kênh bán';
  document.querySelector('#shop-main').innerHTML='<div class="sa-main-inner">'+content+'</div>';
  document.dispatchEvent(new Event('shop-render'));
}

export function toast(text){
  let el=document.querySelector('#shop-toast');
  if(!el){el=document.createElement('div');el.id='shop-toast';el.setAttribute('role','status');document.body.appendChild(el);}
  el.textContent=text;el.hidden=false;el.classList.add('is-visible');
  clearTimeout(window.shopToastTimer);
  window.shopToastTimer=setTimeout(()=>{el.hidden=true;el.classList.remove('is-visible');},5500);
}

export function dialog(title,body,onConfirm){
  const d=document.querySelector('#shop-confirm');
  d.innerHTML='<form class="stack"><h2 id="sc-title">'+esc(title)+'</h2><div>'+body+'</div><p class="form-error" role="alert"></p><div class="cluster"><button type="button" class="btn btn--secondary" value="cancel">Quay lại</button><button type="submit" class="btn btn--primary" value="ok">Xác nhận</button></div></form>';
  d.setAttribute('aria-labelledby','sc-title');
  d.querySelector('[value=cancel]').onclick=()=>d.close();
  d.querySelector('form').onsubmit=e=>{e.preventDefault();operation(e.currentTarget,async()=>{await onConfirm();d.close();});};
  d.showModal();
}

export async function operation(formEl,fn){
  const b=formEl?.querySelector('[type=submit]'),err=formEl?.querySelector('.form-error');
  if(b?.disabled)return;if(err)err.textContent='';
  if(b){b.disabled=true;b.dataset.label=b.textContent;b.textContent='Đang xử lý...';}
  try{
    await new Promise(r=>setTimeout(r,200));
    await fn();
  }catch(e){
    if(err?.isConnected){err.textContent=e.message;err.tabIndex=-1;err.focus();}
    else toast(e.message);
  }finally{
    if(b){b.disabled=false;b.textContent=b.dataset.label;}
  }
}

export function requireSeller(){
  if(seller())return true;
  location.replace(link('login',{next:location.pathname+location.search}));
  return false;
}

function sidebarLink(p,label,badge=''){
  const current=page===p?'aria-current="page"':'';
  return '<a href="'+link(p)+'" '+current+'><span>'+label+'</span>'+(badge?'<span class="sa-sidebar__count">'+badge+'</span>':'')+' </a>';
}

export function shell(){
  document.body.classList.add('shop-app','sa-app');
  document.body.innerHTML=`
    <a class="skip-link" href="#shop-main">Bỏ qua điều hướng</a>

    <div class="sa-service-bar">
      PCMatch Kênh bán &bull; Quản lý sản phẩm, đơn hàng và báo giá của shop bạn
    </div>

    <header class="sa-topbar" id="shop-topbar">
      <button class="sa-menu-btn" type="button" data-action="shop-menu" aria-label="Mở menu">
        <span></span><span></span><span></span>
      </button>
      <a class="sa-logo" href="/">
        <i class="sa-logo__mark"></i>
        <span>PC Match</span>
        <em>Kênh bán</em>
      </a>
      <label class="sa-search">
        <span class="sr-only">Tìm kiếm</span>
        <input type="text" placeholder="Tìm sản phẩm, đơn hàng hoặc khách hàng...">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
      </label>
      <div class="sa-topbar__right" id="shop-topbar-right"></div>
    </header>

    <div class="sa-shell" id="shop-shell">
      <aside class="sa-sidebar" id="shop-sidebar">
        <div class="sa-sidebar__brand">
          <strong>Kênh bán</strong>
          <small>Quản lý shop của bạn</small>
        </div>
        <nav id="shop-nav">
          <p class="sa-sidebar__group">Tổng quan</p>
          ${sidebarLink('dashboard','Dashboard')}
          ${sidebarLink('revenue','Doanh thu')}

          <p class="sa-sidebar__group">Sản phẩm</p>
          ${sidebarLink('offers','Sản phẩm bán')}
          ${sidebarLink('inventory','Tồn kho')}

          <p class="sa-sidebar__group">Đơn hàng</p>
          ${sidebarLink('orders','Đơn hàng')}
          ${sidebarLink('fulfillment','Giao nhận')}

          <p class="sa-sidebar__group">Báo giá &amp; Hỗ trợ</p>
          ${sidebarLink('build-requests','Yêu cầu build')}
          ${sidebarLink('proposal-list','Báo giá đã gửi')}
          ${sidebarLink('aftersales','Hậu mãi')}
          ${sidebarLink('questions','Câu hỏi')}
        </nav>
        <div class="sa-sidebar__footer" id="shop-sidebar-footer"></div>
      </aside>
      <div class="shop-overlay" id="shop-overlay"></div>
      <main class="sa-main" id="shop-main" tabindex="-1">
        <div class="sa-main-inner"><p role="status">Đang tải giao diện...</p></div>
      </main>
    </div>

    <div id="shop-toast" role="status" hidden></div>
    <dialog id="shop-confirm" class="demo-dialog"></dialog>
    <dialog id="shop-demo-tools" class="demo-dialog">
      <h2>Công cụ Kênh bán</h2>
      <div class="stack">
        <button type="button" class="btn btn--secondary" data-action="shop-logout">Đăng xuất</button>
        <button type="button" class="btn btn--secondary" data-action="shop-reset">Reset dữ liệu demo</button>
        <button type="button" class="btn btn--secondary" data-action="shop-close-demo">Đóng</button>
      </div>
    </dialog>
  `;

  document.getElementById('shop-overlay')?.addEventListener('click',()=>{
    document.getElementById('shop-shell')?.classList.remove('is-sidebar-open');
  });
}

export function updateSidebarUser(){
  const s=seller();
  const footer=document.getElementById('shop-sidebar-footer');
  const topbarRight=document.getElementById('shop-topbar-right');
  if(footer){
    if(s){
      footer.innerHTML='<div class="sa-sidebar__seller"><div><strong>'+esc(s.shopName||s.name)+'</strong><small>'+esc(s.email)+'</small></div></div>';
    }else{
      footer.innerHTML='';
    }
  }
  if(topbarRight){
    if(s){
      const name=esc(s.shopName||s.name);
      const email=esc(s.email);
      topbarRight.innerHTML=`
        <a class="sa-topbar-help" href="/">Trợ giúp</a>
        <div class="sa-user-dropdown" id="shop-user-dropdown">
          <button class="sa-user-btn" type="button" id="shop-user-btn" aria-haspopup="true" aria-expanded="false">
            ${name}
            <svg viewBox="0 0 20 20" fill="currentColor" width="14" height="14" aria-hidden="true"><path fill-rule="evenodd" d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z" clip-rule="evenodd"/></svg>
          </button>
          <div class="sa-user-menu" id="shop-user-menu" hidden>
            <div class="sa-udm-header">
              <div class="sa-udm-name">${name}</div>
              <div class="sa-udm-email">${email}</div>
              <span class="sa-udm-badge">Kênh bán</span>
            </div>
            <div class="sa-udm-links">
              <a href="#">&#128100; Thông tin shop</a>
              <a href="#">&#128274; Đổi mật khẩu</a>
              <hr/>
              <a href="#" class="sa-udm-logout" data-action="shop-logout">&#x2192; Đăng xuất</a>
            </div>
          </div>
        </div>
      `;
      // toggle dropdown
      document.getElementById('shop-user-btn')?.addEventListener('click',(e)=>{
        e.stopPropagation();
        const menu=document.getElementById('shop-user-menu');
        const btn=document.getElementById('shop-user-btn');
        const open=!menu.hidden;
        menu.hidden=open;
        btn.setAttribute('aria-expanded',String(!open));
        document.getElementById('shop-user-dropdown')?.classList.toggle('is-open',!open);
      });
      document.addEventListener('click',()=>{
        const menu=document.getElementById('shop-user-menu');
        const btn=document.getElementById('shop-user-btn');
        if(menu&&!menu.hidden){menu.hidden=true;btn?.setAttribute('aria-expanded','false');document.getElementById('shop-user-dropdown')?.classList.remove('is-open');}
      },{once:false});
    }else{
      topbarRight.innerHTML='';
    }
  }
}

export function toggleSidebar(){
  document.getElementById('shop-shell')?.classList.toggle('is-sidebar-open');
}

export const shopCommon=(action)=>{
  if(action==='shop-menu'){toggleSidebar();return true;}
  if(action==='shop-demo'){document.querySelector('#shop-demo-tools').showModal();return true;}
  if(action==='shop-close-demo'){document.querySelector('#shop-demo-tools').close();return true;}
  if(action==='shop-logout'||action==='shop-logout-btn'){shopLogout();go('login');return true;}
  if(action==='shop-reset'){
    dialog('Reset dữ liệu shop demo?','Toàn bộ sản phẩm, đơn hàng, câu hỏi và dữ liệu demo shop sẽ bị xóa.',()=>{
      localStorage.removeItem('pcmatch-shop-v1');
      sessionStorage.removeItem('pcmatch-shop-session');
      go('login');
    });
    return true;
  }
  return false;
};