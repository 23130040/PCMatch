import {seller,shopLogout} from './shop-store.js';

const pageName=document.documentElement.dataset.page;
function pageUrl(section,page,args={}){
  const path=config.urls[section]?.[page];
  if(!path)throw Error('Unknown page: '+section+'/'+page);
  const query=new URLSearchParams(args).toString();
  return path+(query?'?'+query:'');
}

export const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const page=pageName;
export const params=new URLSearchParams(location.search);
const config=JSON.parse(document.getElementById('pcmatch-config').textContent);
const templates=Object.assign({},...Array.from(
  document.querySelectorAll('script[id^="shop-templates-"]'),
  element=>JSON.parse(element.textContent),
));

// Layout lives in HTML files. Substitution never evaluates executable code.
export function renderTemplate(name,values={}){
  const source=templates[name];
  if(source===undefined)throw Error('Không tìm thấy mẫu giao diện: '+name);
  return source.replace(/\[\[(\w+)\]\]/g,(_,index)=>String(values[index]??''));
}
export const link=(p,args={})=>pageUrl('shop',p,args);
export const go=(p,args)=>location.href=link(p,args);

// The demo session does not replace the Django session protecting Shop routes.
export function enterShop(){
  const target=new URL(params.get('next')||link('dashboard'),location.origin);
  const destination=target.origin===location.origin&&Object.values(config.urls.shop).includes(target.pathname)
    && !['login','register','forgot'].some(p=>target.pathname===link(p))
    ?target.pathname+target.search+target.hash:link('dashboard');
  location.href=config.sessionUser?destination:pageUrl('auth','login',{next:destination});
}

export const btn=(text,action,data='',kind='secondary')=>renderTemplate("shop-ui-btn-1", {
  kind: kind,
  action: action,
  data: esc(data),
  text: text
});
export const a=(text,p,args={},kind='secondary')=>renderTemplate("shop-ui-a-1", {
  kind: kind,
  pUrl: link(p,args),
  text: text
});
export const field=(label,name,value='',type='text',attrs='')=>renderTemplate("shop-ui-field-1", {
  label: label,
  name: name,
  type: type,
  value: esc(value),
  attrs: attrs
});
export const select=(label,name,options,value='',attrs='')=>renderTemplate("shop-ui-select-2", {
  label: label,
  name: name,
  attrs: attrs,
  entriesRows: Object.entries(options).map(([k,v])=>renderTemplate("shop-ui-select-1", {
    k: esc(k),
    kContent: k===String(value)?'selected':'',
    v: esc(v)
  })).join('')
});
export const textarea=(label,name,value='',attrs='required')=>renderTemplate("shop-ui-textarea-1", {
  label: label,
  name: name,
  attrs: attrs,
  value: esc(value)
});
export const submit=text=>renderTemplate("shop-ui-submit-1", {
  text: text
});
export const form=(id,body)=>renderTemplate("shop-ui-form-1", {
  id: id,
  body: body
});
export const notice=(text,type='info')=>renderTemplate("shop-ui-notice-1", {
  type: type,
  text: text
});

export const panel=(title,body)=>renderTemplate("shop-ui-panel-1", {
  title: title,
  body: body
});

export const badge=(text,type='default')=>renderTemplate("shop-ui-badge-1", {
  type: type,
  text: esc(text)
});

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
  document.querySelector('#shop-main .sa-main-inner').innerHTML=content;
  document.dispatchEvent(new Event('shop-render'));
}

export function toast(text){
  let el=document.querySelector('#shop-toast');
  el.textContent=text;el.hidden=false;el.classList.add('is-visible');
  clearTimeout(window.shopToastTimer);
  window.shopToastTimer=setTimeout(()=>{el.hidden=true;el.classList.remove('is-visible');},5500);
}

export function dialog(title,body,onConfirm){
  const d=document.querySelector('#shop-confirm');
  d.querySelector('#sc-title').textContent=title;
  d.querySelector('[data-confirm-message]').innerHTML=body;
  d.querySelector('.form-error').textContent='';
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

export function shell(){
  document.getElementById('shop-overlay')?.addEventListener('click',()=>toggleSidebar(false));
  document.getElementById('shop-user-btn')?.addEventListener('click',event=>{
    event.stopPropagation();
    const menu=document.getElementById('shop-user-menu');
    const open=menu.hidden;
    menu.hidden=!open;
    event.currentTarget.setAttribute('aria-expanded',String(open));
    document.getElementById('shop-user-dropdown').classList.toggle('is-open',open);
  });
}

export function updateSidebarUser(){
  const account=seller();
  for(const id of ['shop-sidebar-footer','shop-topbar-right'])document.getElementById(id).hidden=!account;
  document.querySelectorAll('[data-shop-user-name]').forEach(node=>node.textContent=account?.shopName||account?.name||'');
  document.querySelectorAll('[data-shop-user-email]').forEach(node=>node.textContent=account?.email||'');
}

document.addEventListener('click',()=>{
  const menu=document.getElementById('shop-user-menu');
  if(menu&&!menu.hidden){
    menu.hidden=true;
    document.getElementById('shop-user-btn')?.setAttribute('aria-expanded','false');
    document.getElementById('shop-user-dropdown')?.classList.remove('is-open');
  }
});

export function toggleSidebar(force){
  const shell=document.getElementById('shop-shell');
  if(!shell)return;
  const open=typeof force==='boolean'?force:!shell.classList.contains('is-sidebar-open');
  shell.classList.toggle('is-sidebar-open',open);
  document.querySelector('[data-action="shop-menu"]')?.setAttribute('aria-expanded',String(open));
}

export const shopCommon=(action)=>{
  if(action==='shop-menu'){toggleSidebar();return true;}
  if(action==='shop-demo'){document.querySelector('#shop-demo-tools').showModal();return true;}
  if(action==='shop-close-demo'){document.querySelector('#shop-demo-tools').close();return true;}
  if(action==='shop-logout'||action==='shop-logout-btn'){
    shopLogout();
    if(!config.sessionUser){go('login');return true;}
    document.getElementById('shop-logout-form').submit();return true;
  }
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
