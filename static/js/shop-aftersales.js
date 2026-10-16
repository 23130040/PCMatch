import {renderTemplate,esc,params,link,a,btn,textarea,submit,form,panel,badge,statusBadge,mount,toast,dialog,requireSeller} from './shop-ui.js';
import {mineSeller,stx} from './shop-store.js';

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

  mount('Hậu mãi',renderTemplate("shop-aftersales-aftersales-4", {
    dashboardUrl: link('dashboard'),
    contentContent: !statusFilter?'is-active':'',
    totalAll: totalAll,
    entriesRows: Object.entries(counts).map(([s,c])=>renderTemplate("shop-aftersales-aftersales-5", {
      statusFilterContent: statusFilter===s?'is-active':'',
      s: esc(s),
      s2: esc(s),
      c: c
    })).join(''),
    lengthContent: list.length?renderTemplate("shop-aftersales-aftersales-6", {
      listRows: list.map(af=>renderTemplate("shop-aftersales-aftersales-2", {
        statusBadge: statusBadge(af.status),
        content: badge(af.type,'default'),
        toLocaleString: new Date(af.createdAt).toLocaleString('vi-VN'),
        buyerName: esc(af.buyerName),
        productName: esc(af.productName),
        reason: esc(af.reason),
        sliceRows: af.logs.slice(-1).map(l=>renderTemplate("shop-aftersales-aftersales-1", {
          text: esc(l.text)
        })).join(''),
        aftersalesLink: a('Xử lý','aftersales',{id:af.id},'primary')
      })).join('')
    }):renderTemplate("shop-aftersales-aftersales-3", {
      statusFilterContent: statusFilter?' Thử bỏ bộ lọc.':''
    })
  }));

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
  if(!af){mount('Hậu mãi',renderTemplate("shop-aftersales-aftersaleDetail-1", {
    aftersalesLink: a('Quay lại','aftersales')
  }));return;}

  const canProcess=!['Đã giải quyết','Từ chối'].includes(af.status);

  mount('Hồ sơ '+af.id,renderTemplate("shop-aftersales-aftersaleDetail-4", {
    dashboardUrl: link('dashboard'),
    aftersalesUrl: link('aftersales'),
    id: esc(af.id),
    id2: esc(af.id),
    type: af.type,
    buyerName: esc(af.buyerName),
    aftersalesLink: a('← Danh sách hậu mãi','aftersales'),
    ThongTinHoSoPanel: panel('Thông tin hồ sơ',renderTemplate("shop-aftersales-aftersaleDetail-5", {
      buyerName: esc(af.buyerName),
      content: badge(af.type,'default'),
      productName: esc(af.productName),
      reason: esc(af.reason),
      statusBadge: statusBadge(af.status),
      toLocaleString: new Date(af.createdAt).toLocaleString('vi-VN')
    })),
    LichSuXuLyPanel: panel('Lịch sử xử lý',renderTemplate("shop-aftersales-aftersaleDetail-7", {
      logsRows: af.logs.map(l=>renderTemplate("shop-aftersales-aftersaleDetail-6", {
        toLocaleString: new Date(l.at).toLocaleString('vi-VN'),
        text: esc(l.text)
      })).join('')
    })),
    canProcessContent: canProcess?renderTemplate("shop-aftersales-aftersaleDetail-9", {
      aftersaleReplyForm: form('aftersale-reply',renderTemplate("shop-aftersales-aftersaleDetail-8", {
        id: esc(af.id),
        replyField: textarea('Phản hồi cho khách hàng','reply','','required maxlength="500" placeholder="Hướng dẫn gửi hàng, địa chỉ tiếp nhận, thời gian xử lý dự kiến..."'),
        content: submit('Gửi phản hồi'),
        caseInspectButton: btn('Tiếp nhận kiểm tra','case-inspect',af.id,'secondary')
      })),
      caseApproveButton: btn('Duyệt đổi/trả','case-approve',af.id,'primary'),
      caseRepairButton: btn('Sửa & gửi lại (bảo hành)','case-repair',af.id),
      caseRejectButton: btn('Từ chối','case-reject',af.id,'danger')
    }):renderTemplate("shop-aftersales-aftersaleDetail-2", {
      statusBadge: statusBadge(af.status)
    }),
    HuongDanXuLyPanel: panel('Hướng dẫn xử lý',renderTemplate("shop-aftersales-aftersaleDetail-3"))
  }));
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

  mount('Câu hỏi',renderTemplate("shop-aftersales-questions-2", {
    dashboardUrl: link('dashboard'),
    contentContent: !showAnswered?'is-active':'',
    unanswered: unanswered,
    showAnsweredContent: showAnswered?'is-active':'',
    answered: answered,
    lengthContent: list.length?renderTemplate("shop-aftersales-questions-6", {
      showAnsweredContent: showAnswered?'CÂU TRẢ LỜI':'GỪI CÂU TRẢ LỜI',
      listRows: list.map(q=>renderTemplate("shop-aftersales-questions-5", {
        buyerName: esc(q.buyerName),
        productName: esc(q.productName),
        question: esc(q.question),
        toLocaleString: new Date(q.createdAt).toLocaleString('vi-VN',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}),
        answeredContent: q.answered
                  ?renderTemplate("shop-aftersales-questions-3", {
          answer: esc(q.answer),
          id: esc(q.id)
        })
                  :renderTemplate("shop-aftersales-questions-4", {
          id: esc(q.id)
        })
      })).join('')
    }):renderTemplate("shop-aftersales-questions-1", {
      showAnsweredContent: showAnswered?'Chưa có câu hỏi nào được trả lời':'Không có câu hỏi mới',
      showAnsweredContent2: showAnswered?'Các câu hỏi đã trả lời sẽ xuất hiện ở đây.':'Tuyệt vời! Không có câu hỏi mới cần trả lời.'
    })
  }));

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
    const el=document.querySelector(`[data-action="edit-answer"][data-id="${id}"]`)?.closest('.sa-q-answered');
    if(el){
      const old=el.querySelector('[data-action="edit-answer"]');
      old.insertAdjacentHTML('afterend',`${form('answer-question',renderTemplate("shop-aftersales-action-1", {
        id: esc(q.id),
        answer: esc(q.answer||''),
        content: submit('Cập nhật câu trả lời')
      }))}`);
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
