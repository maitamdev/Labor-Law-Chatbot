from docx import Document
import sys
sys.stdout.reconfigure(encoding='utf-8')
d=Document(r'C:\Users\Asus\Desktop\Bao_cao_Do_an_co_so_POS_Quan_ly_kho_Canh_bao_ton_kho_thap_FINAL.docx')
for i,e in enumerate(d._element.body):
 texts=e.xpath('.//w:t/text()')
 print(i,e.tag.rsplit('}',1)[-1], ' '.join(texts)[:145], 'breaks',len(e.xpath('.//w:br')), 'sects',len(e.xpath('.//w:sectPr')))
print(d.sections[0]._sectPr.xml)
