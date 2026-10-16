const assert = require('node:assert/strict');
const {chromium} = require('playwright');
const base = 'http://127.0.0.1:8767';

(async () => {
  const browser = await chromium.launch({headless:true, channel:'chrome'});
  const context = await browser.newContext({viewport:{width:1440,height:1000}});
  const page = await context.newPage();
  const errors=[];
  page.on('pageerror', e=>errors.push(e.message));
  page.on('response', r=>{if(r.url().startsWith(base)&&r.status()>=400&&!r.url().endsWith('/favicon.ico'))errors.push(`${r.status()} ${r.url()}`);});
  const open=async(path)=>{
    await page.goto(base+path);
    await page.locator('#shop-main h1').waitFor();
    assert.equal(await page.getByText('Lỗi tải trang',{exact:true}).count(),0,path);
  };
  const data=()=>page.evaluate(()=>JSON.parse(localStorage.getItem('pcmatch-shop-v1')));
  const confirm=async()=>{
    await page.locator('#shop-confirm').getByRole('button',{name:'Xác nhận',exact:true}).click();
    await page.locator('#shop-confirm').waitFor({state:'hidden'});
  };
  try {
    await open('/shop/login/');
    // The prefilled credentials must work on a fresh browser, without first using demo auto-login.
    await page.locator('[data-form="shop-login"]').getByRole('button',{name:'Đăng nhập',exact:true}).click();
    await page.waitForURL(url=>url.pathname==='/auth/login/'&&url.searchParams.has('next'));
    await page.locator('input[name=email]').fill('shopbrowser@example.test');
    await page.locator('input[name=password]').fill('ShopBrowser!9472');
    await page.getByRole('button',{name:'Đăng nhập',exact:true}).click();
    await page.waitForURL('**/shop/dashboard/');
    await page.locator('#shop-main h1').waitFor();
    const initial=await data();
    assert.equal(initial.shopProducts.length,8);
    assert.equal(initial.shopOrders.length,5);

    for(const name of ['dashboard','offers','inventory','orders','order','fulfillment','revenue',
      'build-requests','build-request-detail','proposal-builder','proposal-list','proposal','aftersales','questions']){
      let query='';
      if(name==='order')query='?id='+initial.shopOrders[0].id;
      if(['build-request-detail','proposal-builder','proposal'].includes(name))query='?id='+initial.shopBuildRequests[0].id;
      await open(`/shop/${name}/${query}`);
    }

    await open('/shop/offers/?new=1');
    const form=page.locator('[data-form="product-form"]');
    await form.locator('[name=name]').fill('Sản phẩm kiểm thử');
    await form.locator('[name=brand]').fill('Test brand');
    await form.locator('[name=price]').fill('1500000');
    await form.locator('[name=stock]').fill('10');
    await form.locator('[name=description]').fill('Mô tả kiểm thử demo');
    await form.getByRole('button',{name:'Thêm sản phẩm',exact:true}).click();
    await page.waitForURL('**/shop/offers/');
    await page.getByText('Sản phẩm kiểm thử',{exact:true}).waitFor();
    let product=(await data()).shopProducts.find(p=>p.name==='Sản phẩm kiểm thử');
    assert(product);
    await open('/shop/offers/?edit='+product.id);
    await page.locator('[name=price]').fill('1800000');
    await page.getByRole('button',{name:'Lưu thay đổi',exact:true}).click();
    await page.waitForURL('**/shop/offers/');
    await page.locator('#shop-main h1').waitFor();
    assert.equal((await data()).shopProducts.find(p=>p.id===product.id).price,1800000);
    await page.locator(`[data-action="toggle-product"][data-id="${product.id}"]`).click();
    await confirm();
    assert.equal((await data()).shopProducts.find(p=>p.id===product.id).active,false);
    await page.locator(`[data-action="toggle-product"][data-id="${product.id}"]`).click();await confirm();
    await open('/shop/inventory/');
    const stock=page.locator('form[data-form="update-stock"]').filter({has:page.locator(`[name=id][value="${product.id}"]`)});
    await stock.locator('[name=qty]').fill('2');
    await stock.getByRole('button',{name:'Cập nhật',exact:true}).click();
    await page.waitForFunction(id=>JSON.parse(localStorage.getItem('pcmatch-shop-v1')).shopProducts.find(p=>p.id===id).stock===2,product.id);

    await open('/shop/orders/');
    const order=initial.shopOrders.find(o=>o.status==='Chờ xác nhận');
    await open('/shop/order/?id='+order.id);
    await page.locator(`[data-action="order-confirm"][data-id="${order.id}"]`).click();await confirm();
    assert.equal((await data()).shopOrders.find(o=>o.id===order.id).status,'Đang xử lý');
    assert.equal(await page.locator('#shop-main h1').textContent(),order.id);
    await open('/shop/fulfillment/');
    await page.locator(`[data-action="order-ship"][data-id="${order.id}"]`).click();await confirm();
    assert.equal((await data()).shopOrders.find(o=>o.id===order.id).status,'Đang giao');
    assert.equal(await page.locator('#shop-main h1').textContent(),'Quản lý giao nhận');
    await page.locator(`[data-action="order-deliver"][data-id="${order.id}"]`).click();await confirm();
    assert.equal((await data()).shopOrders.find(o=>o.id===order.id).status,'Đã giao');

    await open('/shop/questions/');
    const question=initial.shopQuestions.find(q=>!q.answered);
    const answer=page.locator('[data-form="answer-question"]').filter({has:page.locator(`[name=id][value="${question.id}"]`)});
    await answer.locator('[name=answer]').fill('Câu trả lời kiểm thử');
    await answer.getByRole('button',{name:'Gửi trả lời',exact:true}).click();
    await page.waitForFunction(id=>JSON.parse(localStorage.getItem('pcmatch-shop-v1')).shopQuestions.find(q=>q.id===id).answered,question.id);
    await open('/shop/questions/?answered=1');
    await page.locator(`[data-action="edit-answer"][data-id="${question.id}"]`).click();
    await page.locator('textarea[name=answer]').fill('Câu trả lời đã sửa');
    await page.getByRole('button',{name:'Cập nhật câu trả lời',exact:true}).click();
    await page.locator('.sa-q-answered').filter({hasText:'Câu trả lời đã sửa'}).waitFor();

    await open('/shop/build-request-detail/?id='+initial.shopBuildRequests[0].id);
    await page.locator('[data-action="add-proposal-slot"]').click();
    await page.locator('[data-action="add-proposal-slot"]').click();
    await page.locator('[data-action="remove-proposal-slot"][data-id="1"]').click();
    for(const i of [0,2]){
      await page.locator(`[name=model_${i}]`).selectOption(i===0?'CPU-7600':'MB-B650');
      await page.locator(`[name=price_${i}]`).fill('3000000');
    }
    await page.getByRole('button',{name:'Gửi báo giá cho khách',exact:true}).click();
    await page.getByRole('heading',{name:'Báo giá hiện tại',exact:true}).waitFor();
    assert.equal((await data()).shopBuildRequests[0].offers.length,2);

    await open('/shop/aftersales/?id='+initial.shopAftersales[0].id);
    await page.locator('[data-action="case-inspect"]').click();
    assert.equal((await data()).shopAftersales[0].status,'Đang xử lý');
    await page.locator('[name=reply]').fill('Shop đã tiếp nhận kiểm thử');
    await page.locator('[data-form="aftersale-reply"] button[type=submit]').click();
    await page.getByText('Shop phản hồi: Shop đã tiếp nhận kiểm thử',{exact:true}).waitFor();

    await open('/shop/offers/');
    await page.locator(`[data-action="delete-product"][data-id="${product.id}"]`).click();await confirm();
    assert.equal((await data()).shopProducts.some(p=>p.id===product.id),false);
    await open('/shop/dashboard/');
    await page.screenshot({path:'artifacts/screenshots/shop-dashboard-desktop.png',fullPage:true,animations:'disabled'});
    for(const name of ['dashboard','offers','orders','questions','revenue']){
      await page.setViewportSize({width:390,height:844});
      await open(`/shop/${name}/`);
      const dims=await page.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth}));
      console.log('Mobile',name,dims);
      assert.equal(dims.scroll,dims.width,'Mobile overflow: '+name);
      await page.screenshot({path:`artifacts/screenshots/shop-${name}-mobile.png`,fullPage:true,animations:'disabled'});
    }
    await page.locator('[data-action="shop-menu"]').click();
    assert.match(await page.locator('#shop-shell').getAttribute('class'),/is-sidebar-open/);
    await page.keyboard.press('Escape');
    assert.doesNotMatch(await page.locator('#shop-shell').getAttribute('class'),/is-sidebar-open/);
    await page.locator('#shop-user-btn').click();
    await page.locator('[data-action="shop-logout"]').first().click();
    await page.waitForURL('**/auth/login/');
    await page.goto(base+'/shop/dashboard/');
    await page.waitForURL(url=>url.pathname==='/auth/login/'&&url.searchParams.has('next'));

    await page.setViewportSize({width:1440,height:1000});
    await open('/shop/register/');
    await page.locator('[name=name]').fill('Người bán kiểm thử');
    await page.locator('[name=email]').fill('demoregister@example.test');
    await page.locator('[name=password]').fill('DemoPass!123');
    await page.locator('[name=confirm]').fill('DemoPass!123');
    await page.locator('[name=phone]').fill('0901234567');
    await page.getByRole('button',{name:'Tiếp theo',exact:true}).click();
    await page.waitForURL('**/shop/register/?step=2');
    await page.locator('[name=shopName]').fill('Shop kiểm thử');
    await page.locator('[name=address]').fill('123 Nguyễn Trãi, TP.HCM');
    await page.getByRole('button',{name:'Tiếp theo',exact:true}).click();
    await page.getByRole('heading',{name:'Đăng ký thành công!',exact:true}).waitFor();
    assert((await data()).sellers.some(s=>s.email==='demoregister@example.test'));
    await open('/shop/forgot/');
    await page.locator('[name=email]').fill('demoregister@example.test');
    await page.getByRole('button',{name:'Gửi liên kết khôi phục',exact:true}).click();
    await page.getByRole('status').getByText('Demo chưa hỗ trợ khôi phục mật khẩu hoặc gửi email.',{exact:true}).waitFor();
    await open('/shop/login/');
    await page.locator('[name=email]').fill('demoregister@example.test');
    await page.locator('[name=password]').fill('DemoPass!123');
    await page.locator('[data-form="shop-login"] button[type=submit]').click();
    await page.waitForURL(url=>url.pathname==='/auth/login/'&&url.searchParams.has('next'));
    assert.deepEqual(errors,[]);
    console.log('PASS: 17 Shop routes, products, inventory, orders, questions, build proposals, aftersales, mobile menu, demo registration/sign-in and Django logout');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
