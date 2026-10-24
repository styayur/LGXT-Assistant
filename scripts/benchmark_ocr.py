"""Self-authored input corpus + MOCK output regression, never an OCR accuracy claim."""
import io
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageFilter
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from mobile.src.question_documents import parse_recognition


def main():
    target=ROOT/'docs/research/ocr-fixtures';target.mkdir(parents=True,exist_ok=True)
    formulas=[r'x^2+y^2=z^2',r'a_{n+1}=a_n+\alpha',r'\frac{1}{\sqrt{2\pi\sigma^2}}',
              r'\int_0^1 x^2\,dx=\frac13',r'\begin{pmatrix}1&2\\3&4\end{pmatrix}',
              r'\frac{d}{dx}\sin x=\cos x',r'F=ma',r'\nabla\cdot\mathbf{E}=\frac{\rho}{\varepsilon_0}']
    cases=[{'id':f'math-{i+1:02}','latex':formula,'variant':'clean'} for i,formula in enumerate(formulas)]
    cases += [{'id':'low-resolution','latex':formulas[2],'variant':'low-resolution'},
              {'id':'blur','latex':formulas[3],'variant':'blur'},
              {'id':'crop','latex':formulas[4],'variant':'crop'},
              {'id':'background','latex':formulas[7],'variant':'background'}]
    results=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':800,'height':300},device_scale_factor=1)
        page.set_content('<!DOCTYPE html><html><body><div id="formula" style="display:inline-block;padding:32px;background:white;font-size:28px"></div></body></html>')
        page.add_style_tag(path=str(ROOT/'frontend/node_modules/katex/dist/katex.min.css'))
        page.add_script_tag(path=str(ROOT/'frontend/node_modules/katex/dist/katex.min.js'))
        for i,case in enumerate(cases):
            # The benchmark checks formula rendering independently of parsing.
            page.evaluate("tex => katex.render(tex, document.getElementById('formula'), {displayMode:true,throwOnError:true,trust:false,maxExpand:1000,maxSize:20})",case['latex'])
            raw=page.locator('#formula').screenshot()
            with Image.open(io.BytesIO(raw)) as source:
                image=source.convert('RGB')
                if case['variant']=='low-resolution':image=image.resize((max(1,image.width//4),max(1,image.height//4)))
                elif case['variant']=='blur':image=image.filter(ImageFilter.GaussianBlur(2))
                elif case['variant']=='crop':image=image.crop((image.width//5,0,image.width,image.height))
                elif case['variant']=='background':
                    from PIL import ImageDraw
                    draw=ImageDraw.Draw(image)
                    for y in range(0,image.height,12):draw.line((0,y,image.width,y),fill='#b0c9df',width=1)
                image.save(target/(case['id']+'.png'));image.close()
            response=json.dumps({'text':'synthetic formula','latex':case['latex']})
            if i in (8,9):response=json.dumps({'text':'intentional recognition error','latex':'x^3'})
            elif i==10:response='not JSON: intentional malformed fixture'
            elif i==11:response=json.dumps({'text':'untrusted model fixture','latex':r'\input{private.tex}'})
            parsed=exact=rendered=False
            try:
                value=parse_recognition(response);parsed=True
                exact=re.sub(r'\s+','',value['latex'])==re.sub(r'\s+','',case['latex'])
                rendered=page.evaluate("tex => {try {katex.renderToString(tex,{throwOnError:true,trust:false,maxExpand:1000,maxSize:20});return true;}catch(e){return false;}}",value['latex'])
            except ValueError:pass
            results.append(case|{'mockResponse':response,'parseSuccess':parsed,'normalizedExactMatch':exact,
                                 'renderSuccess':rendered,'manualCorrectionNeeded':not exact})
        browser.close()
    summary={'mode':'MOCK responses, not measured OCR accuracy','samples':len(cases),
             'parseSuccess':sum(c['parseSuccess'] for c in results),'exactMatch':sum(c['normalizedExactMatch'] for c in results),
             'renderSuccess':sum(c['renderSuccess'] for c in results),'manualCorrectionNeeded':sum(c['manualCorrectionNeeded'] for c in results),
             'diagramUnderstanding':'not measured','realModelRequests':0,'cases':results}
    (target/'results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    sys.stdout.write(json.dumps({k:v for k,v in summary.items() if k!='cases'},ensure_ascii=False)+'\n')


if __name__=='__main__':main()
