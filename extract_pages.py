import PyPDF2
reader = PyPDF2.PdfReader('tesisvefinal.pdf')
for page in range(98, 102):
    text = reader.pages[page].extract_text()
    print('--- PAGE', page+1, '---')
    print(text)
