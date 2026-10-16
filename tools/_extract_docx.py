# -*- coding: utf-8 -*-
"""Extract text (paragraphs + tables) from docx teaching plans."""
import zipfile, re, sys, io
import xml.etree.ElementTree as ET

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def q(tag):
    return '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}' + tag

def para_text(p):
    texts = []
    for t in p.iter(q('t')):
        texts.append(t.text or '')
    return ''.join(texts)

def cell_text(tc):
    texts = []
    for p in tc.iter(q('p')):
        s = para_text(p).strip()
        if s:
            texts.append(s)
    return ' / '.join(texts)

def extract(path):
    out = []
    with zipfile.ZipFile(path) as z:
        xml = z.read('word/document.xml').decode('utf-8')
    root = ET.fromstring(xml)
    body = root.find(q('body'))
    for child in body:
        tag = child.tag
        if tag == q('p'):
            txt = para_text(child).strip()
            if txt:
                out.append(txt)
        elif tag == q('tbl'):
            rows = []
            for tr in child.findall(q('tr')):
                cells = [cell_text(tc) for tc in tr.findall(q('tc'))]
                rows.append(cells)
            out.append('__TABLE__:' + repr(rows))
        elif tag == q('sectPr'):
            pass
    return '\n'.join(out)

if __name__ == '__main__':
    src = sys.argv[1]
    dst = sys.argv[2]
    text = extract(src)
    with io.open(dst, 'w', encoding='utf-8') as f:
        f.write(text)
    print('OK', len(text), 'chars ->', dst)
