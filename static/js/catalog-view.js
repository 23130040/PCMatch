import {mount,page} from './ui.js';
// Capture native HTML templates before the shared shell is mounted.
const templates=new Map([...document.querySelectorAll('template[data-page]')].map(t=>[t.dataset.page,t.innerHTML]));
export function renderPage(title,sections){
 const template=templates.get(page);
 if(!template)throw Error('Thiếu template HTML cho trang '+page);
 document.body.classList.add('catalog-page');
 mount(title,template);
 for(const [name,html] of Object.entries(sections)){
  const node=document.querySelector('[data-content="'+name+'"]');
  if(node)node.innerHTML=html;
 }
 document.querySelectorAll('img[data-product-image]').forEach(img=>{
  const fail=()=>{img.hidden=true;img.parentElement.querySelector('.image-fallback').hidden=false;};
  img.addEventListener('error',fail,{once:true});
  if(img.complete&&!img.naturalWidth)fail();
 });
}
export function installDrawer(){
 const drawer=document.querySelector('#filter-drawer'),home=document.querySelector('#filter-home'),opener=document.querySelector('[data-action=filters-open]');
 if(!drawer||!home)return;
 drawer.addEventListener('close',()=>{const f=drawer.querySelector('form');if(f)home.append(f);opener.setAttribute('aria-expanded','false');opener.focus();});
 const media=matchMedia('(min-width:768px)');media.addEventListener('change',()=>{if(media.matches&&drawer.open)drawer.close();});
}
export function openFilters(){const d=document.querySelector('#filter-drawer');d.querySelector('[data-drawer-body]').append(document.querySelector('#filter-home form'));document.querySelector('[data-action=filters-open]').setAttribute('aria-expanded','true');d.showModal();}
