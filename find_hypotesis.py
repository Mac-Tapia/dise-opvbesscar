import PyPDF2
reader = PyPDF2.PdfReader('tesisvefinal.pdf')
for i,page in enumerate(reader.pages):
    text = page.extract_text() or ''
    if 'Hipótesis' in text or 'Hipótesis' in text:
        print('page', i+1)
        print(text[:400])
