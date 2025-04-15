
import docx2txt
import tempfile

def extract_text(fileobj):
    with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
        tmp.write(fileobj.read())
        tmp.flush()
        texto = docx2txt.process(tmp.name)
    return texto
