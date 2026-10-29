from pathlib import Path
import json,re
import pymupdf
from PIL import Image,ImageDraw
W=Path(__file__).resolve().parent
pdf=pymupdf.open(W/'bao_cao_qa.pdf')
pages=W/'final_pages_v3';pages.mkdir(exist_ok=True)
sheets=W/'contact_sheets_v3';sheets.mkdir(exist_ok=True)
audit=[];landmarks=[]
for i,page in enumerate(pdf):
 text=page.get_text()
 data=page.get_text('dict');spans=[s for b in data['blocks'] if b['type']==0 for l in b['lines'] for s in l['spans']]
 outside=[s['text'] for s in spans if s['bbox'][0]<24 or s['bbox'][2]>page.rect.width-24 or s['bbox'][1]<15 or s['bbox'][3]>page.rect.height-20]
 page.get_pixmap(matrix=pymupdf.Matrix(1.35,1.35)).save(pages/f'page-{i+1}.png')
 audit.append({'page':i+1,'chars':len(text.strip()),'outside':outside,'first':text.strip().splitlines()[:3]})
 for line in text.splitlines():
  if line.startswith(('CHƯƠNG ','MỞ ĐẦU','TÀI LIỆU THAM KHẢO','PHỤ LỤC ','Hình ','Bảng ')):
   landmarks.append({'page':i+1,'line':line})
for start in range(0,len(pdf),4):
 canvas=Image.new('RGB',(1220,1750),'#E0E0E0');draw=ImageDraw.Draw(canvas)
 for j in range(4):
  idx=start+j
  if idx>=len(pdf):break
  im=Image.open(pages/f'page-{idx+1}.png');im.thumbnail((595,842))
  x=10+(j%2)*610;y=25+(j//2)*875
  canvas.paste(im,(x,y));draw.text((x,y-16),f'PDF page {idx+1}',fill='black')
 canvas.save(sheets/f'sheet-{start//4+1:02}.png')
(W/'page_audit.json').write_text(json.dumps({'pages':len(pdf),'audit':audit,'landmarks':landmarks},ensure_ascii=False,indent=2),encoding='utf-8')
print('Pages',len(pdf),'Contact sheets',(len(pdf)+3)//4)
print('Sparse pages',[(r['page'],r['chars']) for r in audit if r['chars']<250])
print('Outside',[(r['page'],r['outside']) for r in audit if r['outside']])
print('Landmarks',landmarks[:16])
