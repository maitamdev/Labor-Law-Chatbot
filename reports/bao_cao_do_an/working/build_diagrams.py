from pathlib import Path
from html import escape
import math, csv
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
import pymupdf

OUT=Path(__file__).resolve().parents[1]/'so_do';OUT.mkdir(exist_ok=True)
pdfmetrics.registerFont(TTFont('VN',r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('VNB',r'C:\Windows\Fonts\arialbd.ttf'))

class Diagram:
 def __init__(self,name,w=1000,h=720):
  self.name=name;self.w=w;self.h=h
  self.c=canvas.Canvas(str(OUT/(name+'.pdf')),pagesize=(w,h))
  self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/>']
 def text(self,x,y,s,size=24,bold=False,color='#172B40',align='center'):
  self.c.setFillColor(HexColor(color));self.c.setFont('VNB' if bold else 'VN',size)
  if align=='center':self.c.drawCentredString(x,self.h-y,s)
  else:self.c.drawString(x,self.h-y,s)
  self.svg.append(f'<text x="{x}" y="{y}" text-anchor="{"middle" if align=="center" else "start"}" font-family="Arial, sans-serif" font-size="{size}" font-weight="{"bold" if bold else "normal"}" fill="{color}">{escape(s)}</text>')
 def box(self,x,y,w,h,lines,fill='#F0F4F8',dashed=False,size=24):
  self.c.setStrokeColor(HexColor('#697D90'));self.c.setFillColor(HexColor(fill));self.c.setLineWidth(2)
  self.c.setDash(6,4) if dashed else self.c.setDash()
  self.c.roundRect(x,self.h-y-h,w,h,10,stroke=1,fill=1);self.c.setDash()
  self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="#697D90" stroke-width="2" {"stroke-dasharray=\"6 4\"" if dashed else ""}/>')
  lines=lines.split('\n');top=y+h/2-(len(lines)-1)*size*0.62+size*0.32
  for i,line in enumerate(lines):self.text(x+w/2,top+i*size*1.24,line,size=size,bold=i==0)
 def line(self,x1,y1,x2,y2,arrow=True,dashed=False):
  self.c.setStrokeColor(HexColor('#435A70'));self.c.setFillColor(HexColor('#435A70'));self.c.setLineWidth(2)
  self.c.setDash(6,5) if dashed else self.c.setDash();self.c.line(x1,self.h-y1,x2,self.h-y2);self.c.setDash()
  self.svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#435A70" stroke-width="2" {"stroke-dasharray=\"6 5\"" if dashed else ""}/>')
  if arrow:
   a=math.atan2(y2-y1,x2-x1);pts=[(x2,y2),(x2-12*math.cos(a-.42),y2-12*math.sin(a-.42)),(x2-12*math.cos(a+.42),y2-12*math.sin(a+.42))]
   p=self.c.beginPath();p.moveTo(pts[0][0],self.h-pts[0][1]);p.lineTo(pts[1][0],self.h-pts[1][1]);p.lineTo(pts[2][0],self.h-pts[2][1]);p.close();self.c.drawPath(p,fill=1,stroke=0)
   self.svg.append('<polygon fill="#435A70" points="'+' '.join(f'{x},{y}' for x,y in pts)+'"/>')
 def save(self,mmd):
  self.c.save();(OUT/(self.name+'.svg')).write_text('\n'.join(self.svg+['</svg>']),encoding='utf-8')
  (OUT/(self.name+'.mmd')).write_text(mmd,encoding='utf-8')
  pdf=pymupdf.open(OUT/(self.name+'.pdf'));pdf[0].get_pixmap(matrix=pymupdf.Matrix(2,2)).save(OUT/(self.name+'.png'))

d=Diagram('01_use_cases',1000,760)
d.text(500,38,'CA SỬ DỤNG CỦA HỆ THỐNG',28,True)
d.box(20,245,190,105,'Người dùng\ntra cứu')
for y,s in [(90,'Hỏi đáp và xem căn cứ'),(210,'Hỏi nối tiếp hoặc làm rõ'),(330,'Đọc tài liệu đính kèm'),(450,'Xem đồ thị và phản hồi')]:
 d.box(280,y,435,85,s);d.line(210,295,280,y+42)
d.box(775,245,205,105,'Người vận hành\nqua script',size=22)
d.box(280,600,435,90,'Chuẩn bị dữ liệu, chỉ mục\nvà nạp Neo4j')
d.line(775,300,740,300,False);d.line(740,300,740,645,False);d.line(740,645,715,645)
d.text(500,735,'Vai trò vận hành chưa là tài khoản quản trị trên giao diện',21)
d.save('flowchart LR\n U[Người dùng] --> Q[Hỏi đáp và căn cứ]\n U --> H[Hội thoại và làm rõ]\n U --> D[Đọc tài liệu]\n U --> G[Xem đồ thị và phản hồi]\n O[Người vận hành qua script] --> I[Chuẩn bị corpus và chỉ mục]\n O --> N[Nạp Neo4j]\n')

d=Diagram('02_architecture',1000,790)
d.text(500,38,'KIẾN TRÚC TỔNG THỂ',28,True)
d.box(280,75,440,80,'Giao diện Streamlit')
d.box(280,195,440,85,'ChatService và cache câu trả lời')
d.line(500,155,500,195)
d.box(175,325,650,100,'VietLaborRAGChain\nPhân tích, truy xuất, chứng cứ, kiểm định')
d.line(500,280,500,325)
for x,s in [(25,'Corpus JSONL\nBM25 và Chroma'),(365,'Neo4j tùy chọn\nQuan hệ điều luật'),(705,'Ollama\nQwen2.5')]:
 d.box(x,505,270,100,s,size=23);d.line(500,425,x+135,505)
d.box(280,665,440,75,'Lịch sử hội thoại và feedback')
d.line(720,237,950,237,False);d.line(950,237,950,705,False);d.line(950,705,720,705)
d.text(500,775,'Cache trong tiến trình; Neo4j mặc định tắt khi chạy trực tiếp',21)
d.save('flowchart TB\n UI[Streamlit] --> S[ChatService và answer cache]\n S --> R[VietLaborRAGChain]\n R --> C[Corpus BM25 Chroma]\n R -. tùy chọn .-> G[Neo4j]\n R --> L[LocalLLMManager và Ollama]\n S --> H[Lịch sử và feedback]\n')

d=Diagram('03_pipeline',1000,800)
d.text(500,38,'LUỒNG HỎI ĐÁP THEO MÃ THỰC THI',28,True)
steps=[(65,'Chuẩn hóa và giải quyết câu hỏi nối tiếp'),(145,'Router, phân tích và phân rã vấn đề'),(225,'MaterialPremiseGate trước truy xuất'),(305,'BM25 + dense, hợp nhất RRF'),(385,'Mở rộng Neo4j nếu khả dụng'),(465,'Selector, constraints và completeness gate'),(545,'ContextBuilder và các mã E1, E2'),(625,'LLM hoặc nhánh quy tắc chuyên biệt'),(705,'Ánh xạ nguồn và OutputValidator')]
for i,(y,s) in enumerate(steps):
 d.box(145,y,710,55,s,size=24)
 if i:d.line(500,steps[i-1][0]+55,500,y)
d.text(500,788,'Có nhánh trả sớm: xã giao, ngoài phạm vi, cần làm rõ, thiếu chứng cứ',21)
d.save('flowchart TB\n Q[Câu hỏi và hội thoại] --> N[Chuẩn hóa và giải quyết nối tiếp]\n N --> R[Router và phân rã vấn đề]\n R --> P[MaterialPremiseGate]\n P -->|đủ tiền đề| H[BM25 + dense + RRF]\n P -->|thiếu tiền đề| C[Hỏi làm rõ]\n H --> G[Mở rộng graph tùy chọn]\n G --> S[Selector constraints completeness]\n S --> B[ContextBuilder]\n B --> L[LLM hoặc quy tắc chuyên biệt]\n L --> V[EvidenceMapper và OutputValidator]\n V --> A[Câu trả lời và căn cứ]\n')

d=Diagram('04_graph_schema',1000,710)
d.text(500,38,'LƯỢC ĐỒ ĐƯỢC BUILDER NẠP',28,True)
d.box(305,80,390,95,'LegalDocument\nKhóa doc_id')
d.box(305,245,390,115,'Article\nKhóa chunk_id\nnumber, clause_number, point',size=23)
d.line(500,175,500,245);d.text(660,220,'HAS_ARTICLE',22)
d.box(20,440,300,95,'Article hướng dẫn\nhoặc xử phạt',size=23)
d.box(680,440,300,95,'Article được\nviện dẫn',size=23)
d.line(170,440,360,360);d.text(170,395,'GUIDES / PENALIZES',21)
d.line(670,360,830,440);d.text(830,395,'REFERENCES',22)
d.box(115,595,770,65,'Chapter, Clause, Point chưa nạp thành nút riêng',dashed=True,size=23)
d.text(500,695,'8 mục cầu dẫn cấu hình; số cạnh thực tế cần truy vấn Neo4j',21)
d.save('flowchart TB\n D[LegalDocument khóa doc_id] -->|HAS_ARTICLE| A[Article khóa chunk_id]\n S[Article hướng dẫn hoặc xử phạt] -->|GUIDES hoặc PENALIZES| A\n A -->|REFERENCES| T[Article được viện dẫn]\n P[Chapter Clause Point chỉ có trong ontology]\n')

d=Diagram('05_sequence',1000,770)
d.text(500,38,'TRÌNH TỰ MỘT LƯỢT HỎI ĐÁP',28,True)
xs=[95,295,510,720,920];labels=['UI','ChatService','RAG chain','Retriever','Ollama']
for x,label in zip(xs,labels):d.box(x-72,75,144,60,label,size=22);d.line(x,135,x,735,False,True)
for y,a,b,lab in [(190,0,1,'Câu hỏi và history'),(270,1,2,'Cache miss hoặc nối tiếp'),(350,2,3,'Truy xuất chứng cứ'),(425,3,2,'Ứng viên và metadata'),(510,2,4,'Prompt với mã chứng cứ'),(585,4,2,'JSON hoặc findings'),(665,2,1,'Kết quả đã kiểm định'),(720,1,0,'Câu trả lời và căn cứ')]:
 d.line(xs[a],y,xs[b],y);d.text((xs[a]+xs[b])/2,y-12,lab,20)
d.save('sequenceDiagram\n participant U as UI\n participant S as ChatService\n participant R as RAG chain\n participant T as Retriever\n participant L as Ollama\n U->>S: Câu hỏi và history\n S->>R: Cache miss hoặc nối tiếp\n R->>T: Truy xuất\n T-->>R: Chứng cứ\n R->>L: Prompt với mã E\n L-->>R: JSON hoặc findings\n Note over R: Kiểm định và ánh xạ nguồn\n R-->>S: Kết quả\n S-->>U: Câu trả lời và căn cứ\n')

d=Diagram('06_deployment',1000,790)
d.text(500,38,'TRIỂN KHAI CỤC BỘ',28,True)
d.box(250,75,500,75,'Trình duyệt trên máy người dùng')
d.box(100,210,800,100,'Ứng dụng Python hoặc container app\nCổng host 127.0.0.1:8501',size=24);d.line(500,150,500,210)
d.box(35,390,430,105,'Ollama hoặc container ollama\n127.0.0.1:11434',size=23)
d.box(535,390,430,105,'Neo4j hoặc container neo4j\n127.0.0.1:7474 và 7687',size=23)
d.line(300,310,250,390);d.line(700,310,750,390)
d.box(20,600,290,105,'Volume\nmodel Ollama',size=23)
d.box(355,600,290,105,'Corpus, storage\nvà HF cache',size=23)
d.box(690,600,290,105,'Volume\ndữ liệu Neo4j',size=23)
d.line(250,495,165,600);d.line(500,310,500,600);d.line(750,495,835,600)
d.text(500,755,'Compose có thêm ollama-pull; cần chuẩn bị corpus và chỉ mục',21)
d.save('flowchart TB\n B[Trình duyệt] -->|127.0.0.1 8501| A[Ứng dụng app]\n A -->|11434| O[Ollama]\n A -->|7687| N[Neo4j]\n O --> M[Volume model]\n A --> C[Corpus read only]\n A --> S[Storage chỉ mục lịch sử feedback]\n A --> H[HF cache read only]\n P[ollama pull] --> O\n')

d=Diagram('07_ingestion',1000,770)
d.text(500,38,'XỬ LÝ DỮ LIỆU VÀ LẬP CHỈ MỤC',28,True)
for i,(y,s) in enumerate([(80,'Nguồn PDF DOC DOCX và manifest'),(210,'Đọc chữ hoặc OCR và chuẩn hóa'),(340,'Parser và LegalChunk có nguồn'),(470,'Production corpus JSONL')]):
 d.box(200,y,600,80,s)
 if i:d.line(500,y-50,500,y)
for x,s in [(20,'Chỉ mục BM25'),(355,'Chroma vector'),(690,'Neo4j tùy chọn')]:
 d.box(x,650,290,80,s,size=24);d.line(500,550,x+145,650)
d.save('flowchart TB\n R[Raw và manifest] --> X[Đọc chữ hoặc OCR]\n X --> P[Chuẩn hóa và parser]\n P --> C[LegalChunk JSONL có nguồn]\n C --> B[BM25]\n C --> V[Chroma]\n C --> G[Neo4j tùy chọn]\n')

d=Diagram('08_retrieval_chart',1000,650)
d.text(500,38,'ABLATION TRUY XUẤT ĐÃ LƯU',28,True)
rows=list(csv.DictReader((OUT.parent.parent/'ablation_retrieval.csv').open()))
left=150;right=950;top=115;bottom=500
for val in [.8,.85,.9,.95,1.0]:
 y=bottom-(val-.75)/.25*(bottom-top);d.line(left,y,right,y,False);d.text(105,y+8,f'{val:.2f}',22)
for i,r in enumerate(rows):
 x=225+i*145
 for dx,key,col in [(-32,'hit@10','#2B587D'),(14,'recall@10','#8EADB9')]:
  v=float(r[key]);h=(v-.75)/.25*(bottom-top)
  d.c.setFillColor(HexColor(col));d.c.rect(x+dx,d.h-bottom,38,h,fill=1,stroke=0)
  d.svg.append(f'<rect x="{x+dx}" y="{bottom-h}" width="38" height="{h}" fill="{col}"/>')
 label={'hybrid_graph':'hybrid graph','hybrid_norm':'hybrid norm'}.get(r['config'],r['config'])
 for j,l in enumerate(label.split()):d.text(x+10,540+j*27,l,22)
d.text(330,600,'Đậm Hit@10',23);d.text(650,600,'Nhạt Recall@10',23)
d.text(500,638,'n = 145; graph offline nên kết quả bằng hybrid; trục bắt đầu 0,75',20)
d.save('%% Biểu đồ tạo từ reports/ablation_retrieval.csv\n%% Có thể sửa vector trong SVG; không dùng Mermaid cho số liệu.\n')

d=Diagram('09_latency_chart',1000,650)
d.text(500,38,'ĐỘ TRỄ CỦA 11 CÂU HỎI ĐÃ LƯU',28,True)
vals=[42.6,25.3,23.5,19.7,19.1,13.8,20.9,11.7,17.4,7.8,11.1]
for val in [0,10,20,30,40,50]:
 y=500-val*7.2;d.line(105,y,970,y,False);d.text(65,y+7,str(val),22)
for i,v in enumerate(vals):
 x=130+i*75;h=v*7.2
 d.c.setFillColor(HexColor('#2B587D'));d.c.rect(x,d.h-500,45,h,fill=1,stroke=0)
 d.svg.append(f'<rect x="{x}" y="{500-h}" width="45" height="{h}" fill="#2B587D"/>')
 d.text(x+23,500-h-10,f'{v:.1f}',20);d.text(x+23,540,f'Q{i}',22)
d.text(500,595,'Đơn vị giây; trung bình 19,35; trung vị 19,10',23)
d.text(500,635,'Nguồn benchmark_11_gold_results.md; không phải lần đo mới',21)
d.save('%% Biểu đồ độ trễ kế thừa từ reports/benchmark_11_gold_results.md\n%% Dữ liệu: 42.6,25.3,23.5,19.7,19.1,13.8,20.9,11.7,17.4,7.8,11.1\n')

print('Created 7 technical diagrams and 2 data charts in',OUT)
