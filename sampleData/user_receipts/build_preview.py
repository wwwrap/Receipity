"""Build a standalone HTML annotation viewer without changing source photos."""

import html
import json
from pathlib import Path


def build():
    root = Path(__file__).resolve().parent
    dataset = json.loads((root / 'annotations.json').read_text(encoding='utf-8'))
    cards = []
    for receipt in dataset['receipts']:
        boxes, rows = [], []
        for name, field in receipt['fields'].items():
            value = 'Unknown — review' if field['value'] is None else str(field['value'])
            if name == 'amount':
                value = f"PHP {field['value']:,.2f}"
            rows.append(f'<tr><th>{name.title()}</th><td>{html.escape(value)}'
                        f'<small>{html.escape(field["status"])}: {html.escape(field["evidence"])}</small></td></tr>')
            if field['bbox']:
                left, top, right, bottom = field['bbox']
                boxes.append(f'<div class="box {name}" style="left:{left*100}%;top:{top*100}%;'
                             f'width:{(right-left)*100}%;height:{(bottom-top)*100}%">'
                             f'<span>{name.title()}</span></div>')
        notes = ''.join(f'<li>{html.escape(note)}</li>' for note in receipt['notes'])
        cards.append(f'<article><h2>{html.escape(receipt["id"])}</h2><div class="columns">'
                     f'<a class="photo" href="{receipt["image"]}" title="Open original photo">'
                     f'<img src="{receipt["image"]}" alt="Receipt {receipt["id"]}">{"".join(boxes)}</a>'
                     f'<div><table>{"".join(rows)}</table><ul>{notes}</ul>'
                     f'<a href="{receipt["transcription"]}">View manual text fixture</a></div></div></article>')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Receipity — annotated receipt samples</title>
<style>
body{font:16px/1.6 system-ui,sans-serif;margin:0;background:#f3f5f8;color:#17263c}
main{max-width:1150px;margin:auto;padding:32px}h1{line-height:1.2}h2{font-size:21px}
article{background:white;padding:24px;margin:24px 0;border-radius:16px;border:1px solid #dbe2ec}
.columns{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:28px;align-items:start}
.photo{position:relative;display:block;line-height:0}.photo img{width:100%;height:auto}
.box{position:absolute;border:3px solid;box-sizing:border-box;pointer-events:none}
.box span{position:absolute;bottom:100%;left:-3px;padding:2px 6px;color:white;font:600 12px/1.4 system-ui;white-space:nowrap}
.merchant{border-color:#854dce}.merchant span{background:#854dce}
.date{border-color:#087ec0}.date span{background:#087ec0}
.amount{border-color:#007f60}.amount span{background:#007f60}
th,td{text-align:left;padding:12px 8px;vertical-align:top;border-bottom:1px solid #dbe2ec}
small{display:block;color:#516078;margin-top:6px}a{color:#005a9b}table{border-collapse:collapse;width:100%}
label{display:inline-block;padding:8px 0}body.hide-boxes .box{display:none}
@media(max-width:750px){.columns{grid-template-columns:1fr}main{padding:16px}article{padding:16px}}
</style><main><h1>Annotated receipt samples</h1>
<p>Four supplied photos with manual field labels. Blue: date · Green: total · Purple: merchant evidence.
Boxes are approximate. Missing fields stay unknown. Transcriptions are selected human-readable text, not OCR output.</p>
<label><input type="checkbox" checked onchange="document.body.classList.toggle('hide-boxes', !this.checked)"> Show field boxes</label>
<p><a href="annotations.json">Download annotation JSON</a> · Click a photo to inspect its original.</p>
'''+''.join(cards)+'</main></html>'
    (root / 'index.html').write_text(page, encoding='utf-8')


if __name__ == '__main__':
    build()
