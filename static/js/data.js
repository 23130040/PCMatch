// Commercial values and technical checks are synthetic fixtures, never live data.
export const categories={CPU:'Bộ xử lý',MB:'Mainboard',RAM:'Bộ nhớ',GPU:'Card đồ họa',SSD:'Lưu trữ',PSU:'Bộ nguồn',CASE:'Vỏ máy',COOL:'Tản nhiệt'};
export const shops=[{id:'BP',name:'BuildPro Sài Gòn',region:'HCM',consult:true,assembly:true,active:true},{id:'TZ',name:'TechZone Hà Nội',region:'HN',consult:true,assembly:true,active:true},{id:'NV',name:'NovaPC Đà Nẵng',region:'DN',consult:false,assembly:false,active:false}];
const rows=[
['CPU-7600','CPU','AMD Ryzen 5 7600','AMD',4690000,{Socket:'AM5',RAM:'DDR5','Nhân / luồng':'6 / 12',iGPU:'Có',Tản:'Kèm box'},'Bộ xử lý cho máy làm việc và giải trí; cần mainboard cùng nền tảng.'],
['CPU-7700','CPU','AMD Ryzen 7 7700','AMD',7290000,{Socket:'AM5',RAM:'DDR5','Nhân / luồng':'8 / 16',iGPU:'Có',Tản:'Kèm box'},'Lựa chọn nhiều nhân hơn cho các tác vụ chạy đồng thời.'],
['CPU-12400','CPU','Intel Core i5-12400F','Intel',2890000,{Socket:'LGA1700',RAM:'DDR4','Nhân / luồng':'6 / 12',iGPU:'Không',Tản:'Kèm box'},'Cần card đồ họa rời để xuất hình; không dùng được với mainboard AM5.'],
['MB-B650','MB','MSI PRO B650M-A WIFI','MSI',3890000,{Socket:'AM5',RAM:'DDR5',Form:'mATX',BIOS:'Chưa có dữ liệu'},'Bo mạch AM5. Hỏi shop phiên bản BIOS của lô hàng trước khi mua.'],
['MB-B660','MB','MSI PRO B660M-A DDR4','MSI',2790000,{Socket:'LGA1700',RAM:'DDR4',Form:'mATX',BIOS:'Chưa có dữ liệu'},'Bo mạch DDR4; không nhận RAM DDR5.'],
['RAM-K32','RAM','Kingston Fury Beast 32GB (2×16GB)','Kingston',2190000,{RAM:'DDR5','Dung lượng':'32GB',Kit:'2×16GB',Profile:'XMP / EXPO cần bật'},'Bộ hai thanh RAM bán theo kit; số lượng 1 là một kit.'],
['RAM-C16','RAM','Corsair Vengeance 16GB (2×8GB)','Corsair',990000,{RAM:'DDR4','Dung lượng':'16GB',Kit:'2×8GB',Profile:'XMP cần bật'},'Bộ RAM DDR4 hai thanh cho mainboard hỗ trợ DDR4.'],
['GPU-5060','GPU','ASUS Dual RTX 5060 8GB','ASUS',8190000,{VRAM:'8GB','Chiều dài':'228mm','Nguồn đề nghị':'650W'},'Card đồ họa rời; đối chiếu không gian case và đầu cấp điện nguồn.'],
['GPU-4060','GPU','MSI RTX 4060 Ventus 8GB','MSI',6990000,{VRAM:'8GB','Chiều dài':'199mm','Nguồn đề nghị':'550W'},'Thông số demo không phải benchmark hay cam kết FPS.'],
['SSD-SN770','SSD','WD Black SN770 1TB','WD',1790000,{'Dung lượng':'1TB',Chuẩn:'NVMe PCIe 4.0',Form:'M.2 2280'},'Ổ lưu trữ NVMe. Cần khe M.2 phù hợp trên mainboard.'],
['SSD-MP44','SSD','TeamGroup MP44L 1TB','TeamGroup',1590000,{'Dung lượng':'1TB',Chuẩn:'NVMe PCIe 4.0',Form:'M.2 2280'},'Ổ SSD cho hệ điều hành, ứng dụng và dữ liệu.'],
['PSU-750','PSU','Corsair RM750e 750W','Corsair',2490000,{'Công suất':'750W',Form:'ATX','Đầu cấp':'Chưa có dữ liệu'},'Công suất danh định không thay thế kiểm tra đầu cắm.'],
['PSU-550','PSU','Cooler Master MWE 550W','Cooler Master',1190000,{'Công suất':'550W',Form:'ATX','Đầu cấp':'Chưa có dữ liệu'},'Đối chiếu yêu cầu của card đồ họa đã chọn.'],
['CASE-AIR','CASE','Montech AIR 100','Montech',1290000,{Form:'mATX','GPU tối đa':'330mm','Tản tối đa':'161mm'},'Vỏ mATX; không bao gồm linh kiện bên trong.'],
['CASE-MINI','CASE','Case Mini demo','PCMatch',790000,{Form:'mATX','GPU tối đa':'200mm','Tản tối đa':'150mm'},'Mẫu dữ liệu để thử cảnh báo card đồ họa quá dài.'],
['COOL-AK','COOL','DeepCool AK400','DeepCool',690000,{Socket:'AM5 / LGA1700','Chiều cao':'155mm'},'Tản khí rời. Kiểm tra ngàm và chiều cao cho phép của case.']
];
export const models=rows.map(([id,category,name,brand,price,specs,description])=>({id,category,name,brand,price,specs,description}));
export const offers=models.flatMap((m,i)=>shops.map((s,j)=>({id:s.id+'-'+m.id,modelId:m.id,shopId:s.id,price:m.price+(j===1?-100000:0),stock:j===2||(j===1&&m.id==='COOL-AK')?0:8+i%5,warranty:m.category==='SSD'?60:m.category==='CASE'?12:36,accessories:m.category==='CPU'?'Hộp và tản box (fixture demo)':'Phụ kiện theo hộp; xác nhận với shop',active:s.active})));
export const regions={HCM:'TP. Hồ Chí Minh',HN:'Hà Nội',DN:'Đà Nẵng',OTHER:'Ngoài vùng giao demo'};
export const model=id=>models.find(x=>x.id===id);
export const shop=id=>shops.find(x=>x.id===id);
export const offer=id=>offers.find(x=>x.id===id);
export const money=n=>new Intl.NumberFormat('vi-VN',{style:'currency',currency:'VND'}).format(n||0);
export const shipping=(shopId,region,fast=false)=>region==='OTHER'?null:(shopId==='BP'?65000:80000)+(fast?55000:0)+(shop(shopId).region===region?0:15000);
