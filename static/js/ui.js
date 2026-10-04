import {db,user,logout,reset} from './store.js';
import {pageName,pageUrl,indexUrl,buyerDestination} from './routing.js';
export const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const params=new URLSearchParams(location.search);
export const page=pageName;
export const link=(p,args={})=>pageUrl('buyer',p,args);
export const go=(p,args)=>location.href=link(p,args);
export const button=(text,action,data='',kind='secondary')=>'<button type="button" class="btn btn--'+kind+'" data-action="'+action+'" data-id="'+esc(data)+'">'+text+'</button>';
export const a=(text,p,args={},kind='secondary')=>'<a class="btn btn--'+kind+'" href="'+link(p,args)+'">'+text+'</a>';
export const field=(label,name,value='',type='text',attrs='')=>'<label class="field"><span>'+label+'</span><input name="'+name+'" type="'+type+'" value="'+esc(value)+'" '+attrs+'></label>';
export const select=(label,name,options,value='',attrs='')=>'<label class="field"><span>'+label+'</span><select name="'+name+'" '+attrs+'>'+Object.entries(options).map(([k,v])=>'<option value="'+esc(k)+'" '+(k===String(value)?'selected':'')+'>'+esc(v)+'</option>').join('')+'</select></label>';
export const textarea=(label,name,value='',attrs='required')=>'<label class="field"><span>'+label+'</span><textarea name="'+name+'" '+attrs+'>'+esc(value)+'</textarea></label>';
export const check=(label,name,attrs='')=>'<label class="check"><input type="checkbox" name="'+name+'" '+attrs+'> <span>'+label+'</span></label>';
export const submit=text=>'<button class="btn btn--primary" type="submit">'+text+'</button>';
export const form=(id,body)=>'<form data-form="'+id+'" class="stack">'+body+'<p class="form-error" role="alert"></p></form>';
export const notice=(text,type='info')=>'<div class="message message--'+type+'">'+text+'</div>';
export const empty=(title,text,action=a('Xem linh kiện','search'))=>'<section class="empty"><h2>'+title+'</h2><p>'+text+'</p>'+action+'</section>';
export const panel=(title,body)=>'<section class="panel panel--padded"><h2>'+title+'</h2>'+body+'</section>';
export const head=(title,desc='',actions='')=>'<div class="page-head"><div><h1>'+esc(title)+'</h1><p>'+esc(desc)+'</p></div><div class="cluster">'+actions+'</div></div>';
export function mount(title,content){const count=document.querySelector('#cart-count');if(count)count.textContent=db().cart.reduce((s,c)=>s+c.qty,0);document.title=title+' — PCMatch';document.querySelector('#main').innerHTML='<div class="container stack">'+content+'</div>';document.dispatchEvent(new Event('pcmatch-render'));}
export function toast(text){const el=document.querySelector('#feedback');el.textContent=text;el.hidden=false;clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>el.hidden=true,6000);}
export function requireUser(){if(user())return true;document.body.dataset.authRedirect='1';location.replace(pageUrl('auth','login',{next:location.pathname+location.search}));return false;}
export function safeNext(){return buyerDestination(params.get('next'));}
export function dialog(title,body,onConfirm){
 const d=document.querySelector('#confirm'),owner=user()?.id;
 d.innerHTML='<form class="stack"><h2 id="confirm-title">'+esc(title)+'</h2><div>'+body+'</div><p class="form-error" role="alert"></p><div class="cluster"><button type="button" class="btn btn--secondary" value="cancel">Quay lại</button><button type="submit" class="btn btn--primary" value="ok">Xác nhận</button></div></form>';
 d.setAttribute('aria-labelledby','confirm-title');d.onclose=null;
 d.querySelector('[value=cancel]').onclick=()=>d.close();
 d.querySelector('form').onsubmit=e=>{e.preventDefault();operation(e.currentTarget,async()=>{
  if(owner&&user()?.id!==owner){requireUser();return;}
  await onConfirm();document.dispatchEvent(new Event('pcmatch-confirmed'));d.close();
 });};d.showModal();
}
export async function operation(formEl,fn){const b=formEl?.querySelector('[type=submit]'),err=formEl?.querySelector('.form-error');if(b?.disabled)return;if(err)err.textContent='';if(b){b.disabled=true;b.dataset.label=b.textContent;b.textContent='Đang xử lý…';}try{await new Promise(r=>setTimeout(r,220));if(sessionStorage.getItem('pcmatch-fail')==='1'){sessionStorage.removeItem('pcmatch-fail');throw Error('Lỗi thao tác mô phỏng. Nội dung được giữ; hãy thử lại.');}await fn();}catch(e){if(err?.isConnected){err.textContent=e.message;err.tabIndex=-1;err.focus();}else toast(e.message);}finally{if(b){b.disabled=false;b.textContent=b.dataset.label;}}}
export function shell(){document.body.classList.add('buyer-app');document.body.innerHTML='<a class="skip-link" href="#main">Bỏ qua điều hướng</a><div class="prototype-note">Bản demo · Giá, tồn, giao nhận và thanh toán đều mô phỏng</div><header class="market-header"></header><main id="main" tabindex="-1"><div class="container"><p role="status">Đang tải giao diện…</p></div></main><footer class="container market-footer"><div><strong>PCMatch</strong><p>Sàn linh kiện máy tính đa cửa hàng.</p></div><div class="cluster">'+a('Trợ giúp','help')+'<a href="'+indexUrl+'">Sitemap prototype</a>'+button('Công cụ demo','demo')+'</div></footer><div id="feedback" role="status" hidden></div><dialog id="confirm" class="demo-dialog"></dialog><dialog id="demo-tools" class="demo-dialog"><h2>Công cụ demo</h2><p>Chỉ tác động dữ liệu trong trình duyệt này.</p><div class="stack">'+button('Lỗi ở thao tác kế tiếp','fail')+button('Hết hạn phiên đăng nhập','expire-session')+button('Reset toàn bộ demo','reset')+button('Đóng','close-demo')+'</div></dialog>';}
export function common(action){if(action==='menu'){document.dispatchEvent(new Event('pcmatch-menu'));return true;}if(action==='demo'){document.querySelector('#demo-tools').showModal();return true;}if(action==='close-demo'){document.querySelector('#demo-tools').close();return true;}if(action==='fail'){sessionStorage.setItem('pcmatch-fail','1');document.querySelector('#demo-tools').close();toast('Thao tác gửi kế tiếp sẽ lỗi một lần để thử lại.');return true;}if(action==='expire-session'){logout();location.reload();return true;}if(action==='reset'){document.querySelector('#demo-tools').close();dialog('Reset demo?','Giỏ, tài khoản và toàn bộ dữ liệu demo sẽ bị xóa khỏi trình duyệt này.',()=>{reset();go('home');});return true;}return false;}
