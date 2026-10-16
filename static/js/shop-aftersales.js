import {mineSeller,sdb,stx,seller,uid} from './shop-store.js';
import {esc,params,go,link,a,btn,field,select,textarea,submit,form,notice,empty,panel,head,badge,statusBadge,mount,toast,dialog,requireSeller} from './shop-ui.js';

export function aftersales(){
  if(!requireSeller())return;
  const statusFilter=params.get('status')||'';
  let list=mineSeller('shopAftersales');
  if(statusFilter)list=list.filter(af=>af.status===statusFilter);
  list=list.slice().reverse();

  const counts={
    'Chờ xử lý':mineSeller('shopAftersales').filter(a=>a.status==='Chờ xử lý').length,
    'Đang xử lý':mineSeller('shopAftersales').filter(a=>a.status==='Đang xử lý').length,
    'Đã giải quyết':mineSeller('shopAftersales').filter(a=>a.status==='Đã giải quyết').length,
    'Từ chối':mineSeller('shopAftersales').filter(a=>a.status==='Từ chối').length
  };
  const totalAll=mineSeller('shopAftersales').length;

  mount('Hậu mãi',`
    <section class="sa-page-heading">
      <div>
        <div class="sa-breadcrumbs">
          <a href="${link('dashboard')}">Kênh bán</a>
          <span>/</span>
          <span>Hậu mãi</span>
        </div>
        <h1>Quản lý hậu mãi</h1>
        <p>Xử lý các yêu cầu đổi trả và bảo hành từ khách hàng</p>
      </div>
    </section>

    <div class="sa-table-card">
      <div class="sa-filter-tabs">
        <button class="sa-tab ${!statusFilter?'is-active':''}" data-action="aftersale-tab" data-status="">Tất cả <span>${totalAll}</span></button>
        ${Object.entries(counts).map(([s,c])=>`<button class="sa-tab ${statusFilter===s?'is-active':''}" data-action="aftersale-tab" data-status="${esc(s)}">${esc(s)} <span>${c}</span></button>`).join('')}
      </div>

      ${list.length?`
        <div style="padding:16px;display:grid;gap:12px">
          ${list.map(af=>`
            <div class="shop-card">
              <div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px">${statusBadge(af.status)} ${badge(af.type,'default')} <span style="color:#94a3b8;font-size:11px">${new Date(af.createdAt).toLocaleString('vi-VN')}</span></div>
                <strong style="font-size:14px">${esc(af.buyerName)}</strong>
                <p style="margin:4px 0;color:#475569;font-size:13px">Sản phẩm: <strong>${esc(af.productName)}</strong></p>
                <p style="margin:4px 0;color:#475569;font-size:13px">Lý do: ${esc(af.reason)}</p>
                ${af.logs.slice(-1).map(l=>`<p style="margin:4px 0;color:#94a3b8;font-size:12px">${esc(l.text)}</p>`).join('')}
              </div>
              <div class="stack">
                ${a('Xử lý','aftersales',{id:af.id},'primary')}
              </div>
            </div>
          `).join('')}
        </div>
      `:`<div class="sa-empty-table">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48"><path d="M9 12h6m-3-3v6m-7 4h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
          <h3>Không có hồ sơ hậu mãi</h3>
          <p>Khách hàng chưa gửi yêu cầu đổi trả hoặc bảo hành.${statusFilter?' Thử bỏ bộ lọc.':''}</p>
        </div>`}
    </div>
  `);

  document.querySelectorAll('[data-action="aftersale-tab"]').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const s=btn.dataset.status;
      const newParams=new URLSearchParams(location.search);
      if(s)newParams.set('status',s);else newParams.delete('status');
      location.href=link('aftersales',Object.fromEntries(newParams));
    });
  });
}

export function aftersaleDetail(){
  if(!requireSeller())return;
  const af=mineSeller('shopAftersales').find(x=>x.id===params.get('id'));
  if(!af){mount('Hậu mãi',`<div class="sa-empty-table"><h3>Không tìm thấy hồ sơ</h3><p>Hồ sơ không tồn tại.</p>${a('Quay lại','aftersales')}</div>`);return;}

  const canProcess=!['Đã giải quyết','Từ chối'].includes(af.status);

  mount('Hồ sơ '+af.id,`
    <section class="sa-page-heading">
      <div>
        <div class="sa-breadcrumbs">
          <a href="${link('dashboard')}">Kênh bán</a>
          <span>/</span>
          <a href="${link('aftersales')}">Hậu mãi</a>
          <span>/</span>
          <span>${esc(af.id)}</span>
        </div>
        <h1>${esc(af.id)}</h1>
        <p>${af.type} · ${esc(af.buyerName)}</p>
      </div>
      <div class="sa-page-actions">
        ${a('← Danh sách hậu mãi','aftersales')}
      </div>
    </section>

    <div class="shop-grid">
      <div class="stack">
        ${panel('Thông tin hồ sơ',`
          <dl class="info-dl">
            <dt>Khách hàng</dt><dd>${esc(af.buyerName)}</dd>
            <dt>Loại yêu cầu</dt><dd>${badge(af.type,'default')}</dd>
            <dt>Sản phẩm</dt><dd>${esc(af.productName)}</dd>
            <dt>Lý do</dt><dd>${esc(af.reason)}</dd>
            <dt>Trạng thái</dt><dd>${statusBadge(af.status)}</dd>
            <dt>Ngày gửi</dt><dd>${new Date(af.createdAt).toLocaleString('vi-VN')}</dd>
          </dl>
        `)}

        ${panel('Lịch sử xử lý',`
          <ul class="shop-timeline">
            ${af.logs.map(l=>`<li><strong>${new Date(l.at).toLocaleString('vi-VN')}</strong><span>${esc(l.text)}</span></li>`).join('')}
          </ul>
        `)}

        ${canProcess?`
          <div class="shop-aftersales-actions">
            <section class="shop-action-form">
              <h3>Tiếp nhận & trả lời khách</h3>
              ${form('aftersale-reply',`
                <input type="hidden" name="id" value="${esc(af.id)}">
                ${textarea('Phản hồi cho khách hàng','reply','','required maxlength="500" placeholder="Hướng dẫn gửi hàng, địa chỉ tiếp nhận, thời gian xử lý dự kiến..."')}
                <div class="cluster">
                  ${submit('Gửi phản hồi')}
                  ${btn('Tiếp nhận kiểm tra','case-inspect',af.id,'secondary')}
                </div>
              `)}
            </section>
            <section class="shop-action-form">
              <h3>Kết quả xử lý</h3>
              <div class="cluster">
                ${btn('Duyệt đổi/trả','case-approve',af.id,'primary')}
                ${btn('Sửa & gửi lại (bảo hành)','case-repair',af.id)}
                ${btn('Từ chối','case-reject',af.id,'danger')}
              </div>
            </section>
          </div>
        `:`<div class="shop-case-result">
          <span>${statusBadge(af.status)}</span>
          <p>Hồ sơ đã được xử lý xong.</p>
        </div>`}
      </div>

      <div>
        ${panel('Hướng dẫn xử lý',`
          <div class="shop-aftersales-resolution">
            <p><strong>Đổi/trả:</strong> Xác nhận lý do hợp lệ → Hướng dẫn gửi hàng → Duyệt hoàn tiền hoặc gửi hàng mới.</p>
            <p><strong>Bảo hành:</strong> Tiếp nhận kiểm tra → Sửa chữa hoặc thay thế → Gửi lại cho khách.</p>
            <p class="muted">Thời gian xử lý mô phỏng, không ràng buộc nghĩa vụ thương mại.</p>
          </div>
        `)}
      </div>
    </div>
  `);
}

export function questions(){
  if(!requireSeller())return;
  const showAnswered=params.get('answered')==='1';
  let list=mineSeller('shopQuestions');
  if(!showAnswered)list=list.filter(q=>!q.answered);
  else list=list.filter(q=>q.answered);
  list=list.slice().reverse();

  const unanswered=mineSeller('shopQuestions').filter(q=>!q.answered).length;
  const answered=mineSeller('shopQuestions').filter(q=>q.answered).length;

  mount('Câu hỏi',`
    <section class="sa-page-heading">
      <div>
        <div class="sa-breadcrumbs">
          <a href="${link('dashboard')}">Kênh bán</a>
          <span>/</span>
          <span>Câu hỏi</span>
        </div>
        <h1>Câu hỏi từ khách hàng</h1>
        <p>Trả lời câu hỏi để tăng tỷ lệ chuyển đổi</p>
      </div>
    </section>

    <div class="sa-table-card">
      <div class="sa-filter-tabs">
        <button class="sa-tab ${!showAnswered?'is-active':''}" data-action="question-tab" data-answered="">Chưa trả lời <span>${unanswered}</span></button>
        <button class="sa-tab ${showAnswered?'is-active':''}" data-action="question-tab" data-answered="1">Đã trả lời <span>${answered}</span></button>
      </div>

      ${list.length?`
        <div class="table-scroll"><table>
          <thead><tr>
            <th>KHÁCH / SẢN PHẨM</th>
            <th>CÂU Hỏi</th>
            <th>THỜI GIAN</th>
            <th>${showAnswered?'CÂU TRẢ LỜI':'GỪI CÂU TRẢ LỜI'}</th>
          </tr></thead>
          <tbody>
            ${list.map(q=>`<tr>
              <td>
                <div class="sa-product-cell">
                  <div class="sa-product-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                  </div>
                  <div>
                    <strong>${esc(q.buyerName)}</strong>
                    <small>${esc(q.productName)}</small>
                  </div>
                </div>
              </td>
              <td class="sa-q-text">${esc(q.question)}</td>
              <td class="sa-q-time">${new Date(q.createdAt).toLocaleString('vi-VN',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}</td>
              <td>
                ${q.answered
                  ?`<div class="sa-q-answered">${esc(q.answer)}<br><button type="button" class="sa-detail-btn" style="margin-top:6px" data-action="edit-answer" data-id="${esc(q.id)}">Sửa</button></div>`
                  :`<form data-form="answer-question" class="sa-q-reply-form"><input type="hidden" name="id" value="${esc(q.id)}"><input type="text" name="answer" required maxlength="500" placeholder="Nhập câu trả lời ngắn gọn, rõ ràng..."><button type="submit" class="inv-update-btn">Gửi trả lời</button></form>`
                }
              </td>
            </tr>`).join('')}
          </tbody>
        </table></div>
      `:`<div class="sa-empty-table">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48"><path d="M8 10h8M8 14h4m-7 5h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
          <h3>${showAnswered?'Chưa có câu hỏi nào được trả lời':'Không có câu hỏi mới'}</h3>
          <p>${showAnswered?'Các câu hỏi đã trả lời sẽ xuất hiện ở đây.':'Tuyệt vời! Không có câu hỏi mới cần trả lời.'}</p>
        </div>`}
    </div>
  `);

  document.querySelectorAll('[data-action="question-tab"]').forEach(btn=>{
    btn.addEventListener('click',()=>{
      const answered=btn.dataset.answered;
      const newParams=new URLSearchParams(location.search);
      if(answered)newParams.set('answered',answered);else newParams.delete('answered');
      location.href=link('questions',Object.fromEntries(newParams));
    });
  });
}

export function action(act,id){
  if(!requireSeller())return true;
  if(act==='case-inspect'){
    const af=mineSeller('shopAftersales').find(x=>x.id===id);
    if(!af)throw Error('Không tìm thấy hồ sơ.');
    stx(()=>{af.status='Đang xử lý';af.logs.push({at:Date.now(),text:'Shop đang tiếp nhận kiểm tra sản phẩm'});});
    aftersaleDetail();toast('Đã cập nhật trạng thái: Đang xử lý.');return true;
  }
  if(act==='case-approve'){
    const af=mineSeller('shopAftersales').find(x=>x.id===id);
    if(!af)throw Error('Không tìm thấy hồ sơ.');
    dialog('Duyệt đổi/trả?','Xác nhận yêu cầu hợp lệ và bắt đầu tiến hành đổi/trả cho khách?',()=>{
      stx(()=>{af.status='Đã giải quyết';af.logs.push({at:Date.now(),text:'Shop duyệt đổi/trả — tiến hành hoàn tiền hoặc gửi hàng mới'});});
      aftersaleDetail();toast('Đã duyệt yêu cầu đổi/trả.');
    });return true;
  }
  if(act==='case-repair'){
    const af=mineSeller('shopAftersales').find(x=>x.id===id);
    if(!af)throw Error('Không tìm thấy hồ sơ.');
    stx(()=>{af.status='Đã giải quyết';af.logs.push({at:Date.now(),text:'Shop đã sửa xong — đang gửi lại sản phẩm cho khách'});});
    aftersaleDetail();toast('Đã cập nhật: đang gửi lại sản phẩm.');return true;
  }
  if(act==='case-reject'){
    const af=mineSeller('shopAftersales').find(x=>x.id===id);
    if(!af)throw Error('Không tìm thấy hồ sơ.');
    dialog('Từ chối yêu cầu?','Từ chối yêu cầu này sẽ đóng hồ sơ. Cần có lý do rõ ràng.',()=>{
      stx(()=>{af.status='Từ chối';af.logs.push({at:Date.now(),text:'Shop từ chối: bằng chứng chưa đủ hoặc ngoài điều kiện bảo hành demo'});});
      aftersaleDetail();toast('Đã từ chối yêu cầu.');
    });return true;
  }
  if(act==='edit-answer'){
    const q=mineSeller('shopQuestions').find(x=>x.id===id);
    if(!q)throw Error('Không tìm thấy câu hỏi.');
    const el=document.querySelector(`[data-id="${id}"]`)?.closest('.shop-card');
    if(el){
      const old=el.querySelector('.btn');
      old.insertAdjacentHTML('afterend',`${form('answer-question','<input type="hidden" name="id" value="'+esc(q.id)+'">'+`<label class="field"><span>Câu trả lời</span><textarea name="answer" required maxlength="500">${esc(q.answer||'')}</textarea></label>`+submit('Cập nhật câu trả lời'))}`);
      old.remove();
    }
    return true;
  }
  return false;
}

export async function submitForm(name,f,d){
  if(!requireSeller())return true;
  if(name==='aftersale-reply'){
    const af=mineSeller('shopAftersales').find(x=>x.id===d.id);
    if(!af)throw Error('Không tìm thấy hồ sơ.');
    if(!d.reply.trim())throw Error('Nhập nội dung phản hồi.');
    stx(()=>{af.logs.push({at:Date.now(),text:'Shop phản hồi: '+d.reply.trim()});if(af.status==='Chờ xử lý')af.status='Đang xử lý';});
    aftersaleDetail();toast('Đã gửi phản hồi cho khách hàng.');return true;
  }
  if(name==='answer-question'){
    const q=mineSeller('shopQuestions').find(x=>x.id===d.id);
    if(!q)throw Error('Không tìm thấy câu hỏi.');
    if(!d.answer.trim())throw Error('Nhập câu trả lời.');
    stx(()=>{q.answer=d.answer.trim();q.answered=true;q.answeredAt=Date.now();});
    questions();toast('Đã gửi câu trả lời.');return true;
  }
  return false;
}
