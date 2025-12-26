import PyPDF2
reader = PyPDF2.PdfReader('tesisvefinal.pdf')
for i,page in enumerate(reader.pages):
    text = (page.extract_text() or '')
    if '3.1' in text:
        print('page', i+1)
