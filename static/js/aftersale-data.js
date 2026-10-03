// Read legacy order snapshots as well as the new per-unit serial/refund records.
export const serialsFor=item=>item.serials||Array.from({length:item.qty},(_,n)=>n?item.serial+'-'+(n+1):item.serial);
export const refundsFor=sub=>sub.refunds?.length?sub.refunds:sub.refund?[sub.refund]:[];
export function appendRefund(sub,refund){
 const existing=refundsFor(sub);if(existing.reduce((sum,r)=>sum+r.amount,0)+refund.amount>sub.total)throw Error('Tổng hoàn vượt số đã thu của đơn con.');
 sub.refunds=[...existing,refund];sub.refund=refund;
}
export function discountForSerials(sub,item,serials){
 const index=sub.items.findIndex(x=>x.id===item.id);
 const allocated=index===sub.items.length-1?sub.discount-sub.items.slice(0,-1).reduce((sum,i)=>sum+Math.floor(sub.discount*i.price*i.qty/sub.subtotal),0):Math.floor(sub.discount*item.price*item.qty/sub.subtotal);
 const each=Math.floor(allocated/item.qty),units=serialsFor(item);
 return serials.reduce((sum,serial)=>sum+each+(units.indexOf(serial)===units.length-1?allocated-each*item.qty:0),0);
}
