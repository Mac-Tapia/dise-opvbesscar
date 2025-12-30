import PyPDF2
reader = PyPDF2.PdfReader('tesisvefinal.pdf')
print('pages', len(reader.pages))
from_index = max(len(reader.pages)-10,0)
print('extracting pages', from_index, 'to end')
refs = []
for i in range(from_index, len(reader.pages)):
    text = reader.pages[i].extract_text() or ''
    if text.strip():
        refs.append('--- PAGE %d ---' % (i+1))
        refs.append(text)
with open('extract_refs.txt','w', encoding='utf-8') as f:
    f.write('\n'.join(refs))
print('extracted to extract_refs.txt')
