// Synthetic catalogue-added dates and sold quantities; never live marketplace statistics.
export const merchandising={
 'CPU-7600':{createdAt:'2026-08-12',soldCount:428,image:'amd-ryzen-5-7600.jpg'},
 'CPU-7700':{createdAt:'2026-09-18',soldCount:176,image:'amd-ryzen-7-7700.jpg'},
 'CPU-12400':{createdAt:'2026-07-10',soldCount:154},
 'MB-B650':{createdAt:'2026-08-14',soldCount:208,image:'msi-pro-b650m-a-wifi.png'},
 'MB-B660':{createdAt:'2026-07-12',soldCount:95},
 'RAM-K32':{createdAt:'2026-08-20',soldCount:367,image:'kingston-fury-beast-ddr5.png'},
 'RAM-C16':{createdAt:'2026-07-15',soldCount:140},
 'GPU-5060':{createdAt:'2026-09-23',soldCount:312,image:'asus-dual-rtx-5060.png'},
 'GPU-4060':{createdAt:'2026-08-01',soldCount:192},
 'SSD-SN770':{createdAt:'2026-09-03',soldCount:395,image:'wd-black-sn770.png'},
 'SSD-MP44':{createdAt:'2026-09-08',soldCount:119},
 'PSU-750':{createdAt:'2026-08-22',soldCount:185},
 'PSU-550':{createdAt:'2026-07-19',soldCount:74},
 'CASE-AIR':{createdAt:'2026-09-10',soldCount:161},
 'CASE-MINI':{createdAt:'2026-08-05',soldCount:42},
 'COOL-AK':{createdAt:'2026-09-15',soldCount:98}
};
export const homeBanners=[
 {id:'parts',title:'Chọn linh kiện. Chọn shop phù hợp.',description:'Khám phá sản phẩm và đối chiếu giá, bảo hành từ từng cửa hàng.',cta:'Khám phá sản phẩm',route:'search',query:{},modelId:'MB-B650'},
 {id:'graphics',title:'Tìm card đồ họa cho PC của bạn',description:'Đối chiếu VRAM, kích thước và nguồn đề nghị.',cta:'Khám phá card đồ họa',route:'search',query:{category:'GPU'},modelId:'GPU-5060'}
];
export const newestModels=(items,limit=4)=>items.filter(m=>m.id&&m.name&&Number.isFinite(Date.parse(m.createdAt))).slice().sort((a,b)=>Date.parse(b.createdAt)-Date.parse(a.createdAt)||a.id.localeCompare(b.id)).slice(0,limit);
export const latestModel=items=>newestModels(items,1)[0]||null;
export const bySold=(a,b)=>(Number(b.soldCount)||0)-(Number(a.soldCount)||0)||a.id.localeCompare(b.id);
