"""Technical comparison artifact, separate from the reviewed-session export path."""
import argparse
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,KeepTogether
from pypdf import PdfReader
from notetaker.services.export import pdf_fonts,validate_glyphs
from notetaker.services.evidence import require_valid_evidence
from notetaker.infrastructure.atomic import atomic_json,sha256_file

p=argparse.ArgumentParser()
p.add_argument('--work',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
args=p.parse_args();work=args.work.resolve(strict=True)
read=lambda name:json.loads((work/name).read_text(encoding='utf-8'))
old,new,state,report=read('baseline.json'),read('draft.json'),read('state.json'),read('comparison.json')
assert report['status']=='passed' and not report['human_review_created'] and not report['production_export_performed']
require_valid_evidence(new,state)
pdf_fonts()
by_id={u['id']:u for u in state['utterances']}
body=ParagraphStyle('ComparisonBody',fontName='NoteTakerNoto',fontSize=10,leading=15,spaceAfter=10,textColor=colors.HexColor('#202b35'))
heading=ParagraphStyle('ComparisonHeading',parent=body,fontName='NoteTakerNotoBold',fontSize=14,leading=19,spaceBefore=16,spaceAfter=10,keepWithNext=True)
title=ParagraphStyle('ComparisonTitle',parent=heading,fontSize=25,leading=32,spaceAfter=20)
small=ParagraphStyle('ComparisonSmall',parent=body,fontSize=8.5,leading=12,spaceAfter=7)
flow=[];texts=[]
def add(text,style=body):
    texts.append(text);flow.append(Paragraph(escape(text).replace('\n','<br/>'),style))
def stamp(ms):
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d}'

add('NOTETAKER',small);add('Comparaison de synthèse par sujet',title)
add('Comparaison technique non validée',heading)
add('Même transcription du dernier test français. Aucun nouveau document de séance n’a été approuvé ou exporté par la procédure de production.')
add(f"Périmètre : {report['transcription_rows']} passages, jusqu’à {stamp(report['last_transcription_ms'])}. L’audio référencé dure environ 20 min 40 s : le test dit « 20 minutes » n’est pas une coupe artificielle à 20 min 00 s.")
add('La version A reprend le brouillon enregistré du test 0.2.2. La version B est une génération Qwen3 CPU organisée par sujet, avec un lien de chaque phrase vers ses notes et citations exactes.')
add(f"Structure observée : A, {report['old_topics']} sujets et {report['old_characters']} caractères ; B, {report['new_topics']} sujets, {report['new_sourced_sentences']} phrases sourcées et {report['new_characters']} caractères. Ces nombres ne mesurent pas la fidélité.")
add('Les contrôles automatiques examinent sens, modalité, attribution et relation entre positions. Le même modèle peut se tromper à plusieurs étapes. Aucune référence humaine annotée ne permet de chiffrer ici un gain de qualité, un taux d’invention ou une couverture des thèmes.')
add('Limites constatées pendant le développement : Qwen a parfois accepté un budget rattaché au mauvais objet, une absence d’évaluation inventée ou une affiliation absente de la source. Des règles supplémentaires refusent ces formes connues. Elles peuvent écarter des informations et ne garantissent pas les autres reformulations. La référence audio doit soutenir le sens réel de chaque phrase.')
add('Les chiffres entre crochets de la version B renvoient à l’annexe des sources. Relire et écouter les passages avant toute utilisation. Les voix inconnues restent anonymes ; les noms imprimés proviennent des corrections opérateur existantes.')
flow.append(PageBreak());add('A  Brouillon du test 0.2.2',title)
add('Contenu enregistré reproduit pour comparaison. Sa présence dans ce rapport n’en certifie pas la fidélité.',small)
for point in old['points']:
    add(point['title'],heading)
    for paragraph in point['summary'].split('\n\n'):add(paragraph)
flow.append(PageBreak());add('B  Rédaction thématique proposée',title)
add('Niveau standard. Les propositions de rédaction ci-dessous n’ont reçu aucune nouvelle relecture humaine.',small)
trace=[]
for pi,point in enumerate(new['points']):
    add(point['title'],heading)
    clauses=[];by_claim={c['id']:c for c in point['claims']}
    for si,sentence in enumerate(point['narrative']):
        key=f'{pi+1}.{si+1}';clauses.append(sentence['text']+f' [{key}]')
        refs=[];seen=set()
        for cid in sentence['claim_ids']:
            for e in by_claim[cid]['evidence']:
                if (e['id'],e['quote']) in seen:continue
                seen.add((e['id'],e['quote']));u=by_id[e['id']]
                refs.append({**e,'start_ms':u['start_ms'],'end_ms':u['end_ms'],'speaker_id':u['speaker_id']})
        trace.append({'key':key,'topic':point['title'],'sentence':sentence['text'],'claim_ids':sentence['claim_ids'],'sources':refs})
    add(' '.join(clauses))
add('Éléments à vérifier',heading)
for warning in new['to_verify']:add(warning,small)
flow.append(PageBreak());add('Sources de la rédaction proposée',title)
add('Les horodatages sont ceux de l’audio préparé de la séance. Chaque extrait est conservé tel qu’il apparaît dans la transcription ; il peut encore contenir une erreur de reconnaissance ou d’attribution. Consulter aussi son contexte et la transcription complète.',small)
for item in trace:
    add(f"[{item['key']}] {item['topic']}",heading)
    add(item['sentence'],small)
    for e in item['sources']:
        add(f"{stamp(e['start_ms'])}–{stamp(e['end_ms'])} : « {e['quote']} »",small)
atomic_json(args.output.with_suffix('.sources.json'),{'scope':'technical traceability only; no human validation','sentences':trace,
    'snapshot_sha256':report['snapshot_sha256']})
validate_glyphs(texts)
def page(canvas,doc):
    canvas.saveState();canvas.setFont('NoteTakerNoto',8)
    canvas.setFillColor(colors.HexColor('#42505b'))
    canvas.drawString(48,28,'COMPARAISON TECHNIQUE NON VALIDÉE')
    canvas.drawRightString(A4[0]-48,28,f'Page {doc.page}')
    canvas.restoreState()
args.output.parent.mkdir(parents=True,exist_ok=True)
SimpleDocTemplate(str(args.output),pagesize=A4,rightMargin=48,leftMargin=48,topMargin=48,bottomMargin=48,
    title='NoteTaker Comparaison de synthèse par sujet',author='NoteTaker').build(flow,onFirstPage=page,onLaterPages=page)
reader=PdfReader(args.output)
qa={'scope':'technical comparison artifact only; not a production session export','pdf':str(args.output.resolve()),
    'sha256':sha256_file(args.output),'pages':len(reader.pages),'human_review_created':False,
    'replacement_characters':sum(page.extract_text().count('\ufffd') for page in reader.pages),
    'rendered_pages_visually_inspected':False}
atomic_json(ROOT/'docs/evidence/topic-comparison-pdf.json',qa)
print(json.dumps(qa,ensure_ascii=True,indent=2))
