import {installValidation} from './validation.js';
import * as catalog from './catalog.js';
import * as account from './account.js';
import * as commerce from './commerce.js';
import * as builds from './builds.js';
import * as support from './support.js';
import {db,user} from './store.js';
import {page,params,shell,mount,empty,a,common,operation,toast,requireUser,esc} from './ui.js';
const modules=[catalog,account,commerce,builds,support];
const privatePages=['checkout','payment','orders','order','account','addresses','builds','consultation','requests','proposals','cases','notifications'];
const routes={home:catalog.home,search:catalog.search,model:catalog.detail,shop:catalog.storefront,compare:catalog.compare,login:account.auth,account:account.account,addresses:account.addresses,notifications:account.notifications,cart:commerce.cart,checkout:commerce.checkout,payment:commerce.payment,orders:commerce.orders,order:commerce.order,builder:builds.builder,builds:builds.builds,consultation:builds.consultation,requests:builds.requests,proposals:builds.proposals,cases:support.cases,help:support.help};
function render(){try{(routes[page]||catalog.home)();restoreDraft();}catch(e){mount('Lỗi tải',empty('Không thể tải dữ liệu demo',esc(e.message),a('Về trang chủ','home')));}}
const draftOwner=user()?.id||'guest';
function draftKey(){return 'pcmatch-form:'+page+':'+params.toString()+':'+draftOwner;}
const secret=el=>['password','file','hidden'].includes(el.type)||['password','confirm','old'].includes(el.name);
function restoreDraft(){try{const draft=JSON.parse(sessionStorage.getItem(draftKey())||'{}');for(const f of document.querySelectorAll('form[data-form]')){const values=draft[f.dataset.form];if(values)for(const el of f.elements){if(values[el.name]!==undefined&&!secret(el)){if(el.type==='checkbox')el.checked=values[el.name];else if(el.type==='select-multiple'){for(const option of el.options)option.selected=[].concat(values[el.name]).includes(option.value);}else el.value=values[el.name];}}}}catch{}}
document.addEventListener('pcmatch-confirmed',()=>{if(!document.body.dataset.authRedirect)sessionStorage.removeItem(draftKey());});
installValidation();shell();setTimeout(render,90);
document.addEventListener('input',e=>{const f=e.target.closest('form[data-form]');if(!f||['login','register','password-change','password-reset','offer','cart-qty','build-slot','delivery','voucher','place-order','pay','filters','shop-filter','region'].includes(f.dataset.form))return;try{const key=draftKey(),draft=JSON.parse(sessionStorage.getItem(key)||'{}');draft[f.dataset.form]=Object.fromEntries([...f.elements].filter(x=>x.name&&!secret(x)).map(x=>[x.name,x.type==='checkbox'?x.checked:x.type==='select-multiple'?[...x.selectedOptions].map(o=>o.value):x.value]));sessionStorage.setItem(key,JSON.stringify(draft));}catch{toast('Không lưu được bản nháp vào trình duyệt.');}});
document.addEventListener('click',async e=>{const b=e.target.closest('[data-action]');if(!b)return;try{if(privatePages.includes(page)&&!user()){requireUser();return;}if(common(b.dataset.action))return;for(const m of modules)if(m.action?.(b.dataset.action,b.dataset.id))break;}catch(err){toast(err.message);}});
document.addEventListener('submit',e=>{const f=e.target.closest('form[data-form]');if(!f)return;e.preventDefault();if(!f.reportValidity())return;operation(f,async()=>{const d=Object.fromEntries(new FormData(f));for(const m of modules)if(await m.submitForm?.(f.dataset.form,f,d)){if(!document.body.dataset.authRedirect&&!document.querySelector('#confirm[open]'))sessionStorage.removeItem(draftKey());return;}});});
window.addEventListener('pageshow',e=>{if(e.persisted){if(privatePages.includes(page)&&!user()){requireUser();return;}location.reload();}});
window.addEventListener('storage',e=>{if(e.key==='pcmatch-demo-v2')location.reload();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){if(document.querySelector('#market-nav.open'))document.querySelector('[data-action=menu]')?.focus();document.querySelector('#market-nav')?.classList.remove('open');document.querySelector('[data-action=menu]')?.setAttribute('aria-expanded','false');}});

// Commit a valid quantity when edited, while keeping the explicit keyboard submit.
document.addEventListener('change',e=>{const f=e.target.closest('form[data-form=cart-qty]');if(f&&e.target.name==='qty')f.requestSubmit();});
