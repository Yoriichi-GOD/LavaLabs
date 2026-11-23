"""Format our measured content in the supplied PDF's two-column serif style.

The reference is a layout reference only. This builder never reads its text.
"""
from pathlib import Path
import json
import re
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, CondPageBreak, Frame, FrameBreak, KeepTogether, NextPageTemplate,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'output/pdf/LavaLabs-Obscura-Research.pdf'
DEST.parent.mkdir(parents=True,exist_ok=True)
CONTENT=json.loads((ROOT/'paper_content.json').read_text(encoding='utf-8'))['blocks']
FONTROOT=Path('C:/Windows/Fonts')
for face,file in [('Paper','times.ttf'),('Paper-Bold','timesbd.ttf'),
                  ('Paper-Italic','timesi.ttf'),('Paper-BoldItalic','timesbi.ttf')]:
    pdfmetrics.registerFont(TTFont(face,str(FONTROOT/file)))
pdfmetrics.registerFontFamily('Paper',normal='Paper',bold='Paper-Bold',
                             italic='Paper-Italic',boldItalic='Paper-BoldItalic')

WIDTH,HEIGHT=letter
LEFT=49.0
RIGHT=49.0
GAP=12.0
COL=(WIDTH-LEFT-RIGHT-GAP)/2
styles={
    'body':ParagraphStyle('Body',fontName='Paper',fontSize=9.96,leading=11.96,
        alignment=TA_JUSTIFY,firstLineIndent=10,spaceAfter=0,allowWidows=0,allowOrphans=0),
    'abstract':ParagraphStyle('Abstract',fontName='Paper-Bold',fontSize=8.97,leading=9.96,
        alignment=TA_JUSTIFY,firstLineIndent=10,spaceAfter=6,allowWidows=0,allowOrphans=0),
    'title':ParagraphStyle('Title',fontName='Paper',fontSize=23.91,leading=26,
        alignment=TA_CENTER,spaceAfter=8),
    'author':ParagraphStyle('Author',fontName='Paper',fontSize=10.96,leading=13,
        alignment=TA_CENTER,spaceAfter=3),
    'event':ParagraphStyle('Event',fontName='Paper-Italic',fontSize=8.97,leading=11,
        alignment=TA_CENTER),
    'section':ParagraphStyle('Section',fontName='Paper',fontSize=9.96,leading=12,
        alignment=TA_CENTER,spaceBefore=12,spaceAfter=7,keepWithNext=False),
    'subsection':ParagraphStyle('Subsection',fontName='Paper-Italic',fontSize=9.96,
        leading=11.96,spaceBefore=7,spaceAfter=4,keepWithNext=False),
    'small':ParagraphStyle('Small',fontName='Paper',fontSize=7.97,leading=9.3,
        alignment=TA_LEFT,spaceAfter=4,wordWrap='CJK'),
    'caption':ParagraphStyle('Caption',fontName='Paper',fontSize=7.97,leading=9.3,
        alignment=TA_CENTER,spaceBefore=7,spaceAfter=4,keepWithNext=True),
    'cell':ParagraphStyle('Cell',fontName='Paper',fontSize=7.6,leading=8.7,
        alignment=TA_LEFT),
    'numeric':ParagraphStyle('NumericCell',fontName='Paper',fontSize=7.6,leading=8.7,
        alignment=TA_RIGHT),
    'ref':ParagraphStyle('Reference',fontName='Paper',fontSize=7.97,leading=9.3,
        alignment=TA_LEFT,leftIndent=12,firstLineIndent=-12,spaceAfter=3,
        splitLongWords=True,wordWrap='CJK'),
}

def smallcaps(text):
    parts=[]
    for word in text.split():
        parts.append(escape(word[:1].upper())+'<font size="8.1">'+escape(word[1:].upper())+'</font>')
    return ' '.join(parts)

headings={
    'Research question and contribution':('section','I. '+smallcaps('Introduction')),
    'Decision supported':('subsection','A. Decision Support and Scope'),
    'Data and target contract':('section','II. '+smallcaps('Data and Targets')),
    'Features and controlled changes':('section','III. '+smallcaps('Features and Validation')),
    'Validation and selection':('subsection','A. Site-Grouped Validation and Selection'),
    'Matched development results':('section','IV. '+smallcaps('Experimental Results')),
    'Negative findings':('subsection','A. Rejected Feature Extensions'),
    'Confirmation and leaderboard evidence':('subsection','B. Confirmation and Public Scoring'),
    'Reproduction and measured runtime':('section','V. '+smallcaps('Reproduction and Runtime')),
    'One fixed model follow-up':('section','VI. '+smallcaps('Fixed Model Follow-Up')),
    'Verification, provenance and limitations':('section','VI. '+smallcaps('Verification and Limitations')),
    'Attribution and AI use':('section',smallcaps('Acknowledgment and AI Disclosure')),
    'References and reviewer entry points':('section',smallcaps('References')),
}
captions=[
    ('I','OBSERVED TARGET SUPPORT'),
    ('II','CONTROLLED SPECTRAL DEVELOPMENT RESULTS'),
    ('III','DISTINCT EVALUATION POPULATIONS'),
    ('IV','LOCAL AND PUBLIC EVALUATION POPULATIONS'),
    ('V','FIXED MODEL FOLLOW-UP'),
]

def header(canvas,doc):
    canvas.saveState()
    canvas.setFont('Paper',6.97)
    canvas.setFillColor(colors.black)
    canvas.drawRightString(WIDTH-RIGHT,HEIGHT-31,str(doc.page))
    canvas.restoreState()

def frame(x,y,w,h,name):
    return Frame(x,y,w,h,id=name,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)

doc=BaseDocTemplate(str(DEST),pagesize=letter,
    title='LavaLabs Atmospheric Lab: Site-Aware Spectral Prediction in OBSCURA',
    author='Saishreek Singh',subject='Measured OBSCURA research; two-column serif presentation',
    leftMargin=LEFT,rightMargin=RIGHT,topMargin=40,bottomMargin=42,
    allowSplitting=1,pageCompression=1)
first=[frame(LEFT,650,WIDTH-LEFT-RIGHT,100,'title'),
       frame(LEFT,42,COL,598,'left-first'),frame(LEFT+COL+GAP,42,COL,598,'right-first')]
regular=[frame(LEFT,42,COL,710,'left'),frame(LEFT+COL+GAP,42,COL,710,'right')]
doc.addPageTemplates([PageTemplate(id='First',frames=first,onPage=header),
                      PageTemplate(id='Body',frames=regular,onPage=header)])
story=[NextPageTemplate('Body'),
       Paragraph('LavaLabs Atmospheric Lab: Site-Aware Spectral Prediction in OBSCURA',styles['title']),
       Paragraph('Saishreek Singh',styles['author']),
       Paragraph('Solo student entry, OBSCURA Satellite AI Research Challenge, 23 November 2026',styles['event']),
       FrameBreak()]

in_abstract=False
in_references=False
table_number=0
reference_number=0
body_capture=[]
for index,block in enumerate(CONTENT):
    # Title/author are represented by the spanning paper header above.
    if index<3:continue
    if block['kind']=='heading':
        if block['text']=='Abstract':
            in_abstract=True
            continue
        in_references=block['text']=='References and reviewer entry points'
        kind,text=headings[block['text']]
        story.append(CondPageBreak(54 if kind=='section' else 43))
        story.append(Paragraph(text,styles[kind]))
        continue
    if block['kind']=='table':
        roman,caption=captions[table_number]
        table_number+=1
        caption=Paragraph(f'TABLE {roman}<br/>{caption}',styles['caption'])
        widths=[w/sum(block['widths'])*COL for w in block['widths']]
        rows=[]
        for ri,row in enumerate(block['rows']):
            cells=[]
            for ci,value in enumerate(row):
                text=escape(str(value))
                if ri==0:text='<b>'+text+'</b>'
                style=styles['numeric'] if ri>0 and ci>0 and re.fullmatch(r'[0-9.,]+',str(value)) else styles['cell']
                cells.append(Paragraph(text,style))
            rows.append(cells)
        table=Table(rows,colWidths=widths,repeatRows=1,hAlign='CENTER')
        table.setStyle(TableStyle([
            ('LINEABOVE',(0,0),(-1,0),.6,colors.black),
            ('LINEBELOW',(0,0),(-1,0),.35,colors.black),
            ('LINEBELOW',(0,-1),(-1,-1),.6,colors.black),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),3),('RIGHTPADDING',(0,0),(-1,-1),3),
            ('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),2),
        ]))
        story.extend([KeepTogether([caption,table]),Spacer(1,5)])
        continue
    text=block['text']
    body_capture.append(text)
    if in_abstract:
        story.append(Paragraph('<i>Abstract</i> - '+text,styles['abstract']))
        story.append(Paragraph('<i>Index Terms</i> - Earth observation, atmospheric regression, site-grouped validation, cloud-quality ablation, reproducibility.',styles['abstract']))
        in_abstract=False
    elif in_references and text.startswith('<link'):
        reference_number+=1
        match=re.fullmatch(r'<link href="([^"]+)">(.+)</link>',text)
        link,label=match.groups()
        readable=link.replace('https://','').replace('www.','')
        story.append(Paragraph(f'[{reference_number}] {label}. [Online]. Available: <link href="{link}">{escape(readable)}</link>.',styles['ref']))
    else:
        # The original measured prose is preserved verbatim, including limitations.
        style=styles['small'] if block['style']=='SmallLava' else styles['body']
        story.append(Paragraph(text,style))

doc.build(story)
print(DEST)
print(f'Embedded Times New Roman; {table_number} tables; {reference_number} references; two columns of {COL:.1f} pt.')
