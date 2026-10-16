import {seller,getOrCreateDemoSeller,shopLogin} from './shop-store.js';
import {page,params,link,go,shell,mount,toast,dialog,operation,updateSidebarUser,shopCommon} from './shop-ui.js';
import * as auth from './shop-auth.js';
import * as dashboard from './shop-dashboard.js';
import * as products from './shop-products.js';
import * as orders from './shop-orders.js';
import * as builds from './shop-builds.js';
import * as aftersales from './shop-aftersales.js';

const AUTH_PAGES=['login','register','forgot'];
const PRIVATE_PAGES=['dashboard','offers','inventory','orders','order','fulfillment','revenue','build-requests','build-request-detail','proposal-builder','proposal-list','proposal','aftersales','questions'];

const routes={
  login:auth.loginPage,
  register:auth.registerPage,
  forgot:auth.forgotPage,
  dashboard:dashboard.dashboard,
  revenue:dashboard.revenue,
  offers:products.offers,
  inventory:products.inventory,
  orders:orders.orders,
  order:orders.order,
  fulfillment:orders.fulfillment,
  'build-requests':builds.buildRequests,
  'build-request-detail':builds.buildRequestDetail,
  'proposal-list':builds.proposalList,
  'proposal-builder':builds.buildRequestDetail,
  proposal:builds.proposal,
  aftersales:aftersales.aftersales,
  questions:aftersales.questions
};

const modules=[auth,dashboard,products,orders,builds,aftersales];

function render(){
  try{

    if(PRIVATE_PAGES.includes(page)&&!seller()){
      const sel=getOrCreateDemoSeller();
      shopLogin(sel);
    }
    if(AUTH_PAGES.includes(page)&&seller()&&page==='login'){
      go('dashboard');
      return;
    }
    (routes[page]||dashboard.dashboard)();
    updateSidebarUser();
  }catch(e){
    mount('Lỗi tải','<section class="empty"><h2>Lỗi tải trang</h2><p>'+e.message+'</p><a class="btn btn--primary" href="'+link('dashboard')+'">Về Dashboard</a></section>');
  }
}

shell();

setTimeout(()=>{
  render();
},80);

document.addEventListener('shop-render',()=>{
  updateSidebarUser();
});

document.addEventListener('click',async e=>{
  const b=e.target.closest('[data-action]');
  if(!b)return;
  try{
    const act=b.dataset.action,id=b.dataset.id||'';
    if(shopCommon(act))return;
    for(const m of modules)if(m.action?.(act,id))break;
  }catch(err){
    toast(err.message);
  }
});

document.addEventListener('submit',e=>{
  const f=e.target.closest('form[data-form]');
  if(!f)return;
  e.preventDefault();
  if(!f.reportValidity())return;
  operation(f,async()=>{
    const d=Object.fromEntries(new FormData(f));
    for(const m of modules)if(await m.submitForm?.(f.dataset.form,f,d))break;
  });
});

document.addEventListener('keydown',e=>{
  if(e.key==='Escape'){
    document.getElementById('shop-shell')?.classList.remove('is-sidebar-open');
  }
});

window.addEventListener('storage',e=>{
  if(e.key==='pcmatch-shop-v1')location.reload();
});
