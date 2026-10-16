import {renderTemplate,page,params,link,shell,mount,toast,operation,updateSidebarUser,shopCommon,enterShop,esc,toggleSidebar} from './shop-ui.js';
import {seller,getOrCreateDemoSeller,shopLogin} from './shop-store.js';
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
  aftersales:()=>params.has('id')?aftersales.aftersaleDetail():aftersales.aftersales(),
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
      enterShop();
      return;
    }
    (routes[page]||dashboard.dashboard)();
  }catch(e){
    mount('Lỗi tải',renderTemplate("shop-app-render-1", {
      message: esc(e.message),
      dashboardUrl: link('dashboard')
    }));
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
    e.preventDefault();
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
    toggleSidebar(false);
  }
});

window.addEventListener('storage',e=>{
  if(e.key==='pcmatch-shop-v1')location.reload();
});
