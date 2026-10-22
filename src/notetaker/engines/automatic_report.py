"""Direct, source-bound first draft. Never creates approvals or vote objects."""
import uuid
import re
import json
from notetaker.infrastructure.atomic import atomic_json
from .hierarchical_summary import coherent_blocks, call_json, object_schema, grounded_claim, normalized, source_units, resolve_evidence

def contextual_risk(text,quotes):
    """Specific context distortions observed locally; not a fidelity proof."""
    source=' '.join(quotes).casefold();text=text.casefold()
    if 'sans délibération' in text and re.search(r'pas.{0,50}délibération\s+avec\s+débat',source):
        return 'absence_of_debate_changed_to_absence_of_deliberation'
    if re.search(r'transparen\w*',text) and not re.search(r'transparen\w*|clarté|\bclair\w*|\bexpli\w*|\bprécis\w*',source):
        return 'transparency_requirement_not_in_cited_source'
    if re.search(r'publicitair\w*',text) and not re.search(r'publicitair\w*|publicité',source):
        return 'advertising_qualification_not_in_source'
    if 'projet politique' in text and 'projet politique' not in source:
        return 'political_project_requires_its_own_source'
    if (re.search(r'vague\s+idée\s+(?:sur|de)\s+ress',text) and
        not re.search(r'vague\s+idée\s+(?:sur|de)\s+ress',source)):
        return 'unspecified_idea_assigned_to_a_specific_topic'
    if ("critique l'absence" in text and re.search(r"nous n['’]avons pas.{0,80}à chaque fois",source)):
        return 'historical_practice_changed_to_objection'
    if ('une accusation' in text and re.search(r'soit\s+vous\s+nous\s+accusez',source) and
        re.search(r'laissez entendre|petite musique',source) and not re.search(r'insinu\w*|éventuel\w*',text)):
        return 'insinuation_changed_to_formal_accusation'
    if (re.search(r'nous\s+avons\s+géré',source) and re.search(r'probité|honneur|sobriété',source)
        and re.search(r'ne\s+reflèt\w*\s+pas.{0,70}gestion|gestion\s+(?:irresponsable|non\s+responsable)',text)):
        return 'defence_of_management_changed_to_accusation'
    return None


def assess(claim,rows,lexicon=()):
    from .topic_summary import identity_problem,discourse_problem
    valid,reason=grounded_claim(claim,rows)
    quotes=[e['quote'] for e in claim['evidence']]
    problem=identity_problem(claim['text'],[claim],lexicon) or discourse_problem(claim['kind'],'own',claim['text'],quotes)
    problem=problem or contextual_risk(claim['text'],quotes)
    numbers=lambda text:set(re.findall(r'\d+(?:[.,]\d+)?',re.sub(r'(?<=\d)[\s\u00a0]+(?=\d)','',text)))
    if not numbers(claim['text'])<=numbers(' '.join(quotes)):problem='number_not_in_citation'
    return (False,problem) if problem else (valid,reason)


def summarize(request):
    from pathlib import Path
    workspace = Path(request['workspace'])
    model_request={**request,'workspace':request.get('cache_workspace',str(workspace))}
    rows = request['utterances']
    by_id = {u['id']: u for u in rows}
    points, alerts, inventory = [], [], []
    blocks = list(coherent_blocks(rows, max_characters=14000, max_seconds=600, overlap=1))
    units=source_units(rows)
    seen = set()
    for index, block in enumerate(blocks):
        atomic_json(workspace/'summary-progress.json', {'phase':'automatic_report', 'completed':index, 'total':len(blocks)})
        ids = sorted({u['id'] for u in block})
        voices = sorted({u['speaker'] for u in block})
        aliases={f'V{i+1}':voice for i,voice in enumerate(voices)}
        reverse={voice:alias for alias,voice in aliases.items()}
        model_block=[{**u,'speaker':reverse[u['speaker']]} for u in block]
        # Let Qwen write prose and choose source IDs; the application supplies
        # exact quotations. Asking the small model to repeat every quotation
        # doubled output and made it copy the transcript instead of summarizing.
        compact_schema=object_schema({'paragraphs':{'type':'array','maxItems':12,'items':object_schema({
            'topic':{'type':'string','minLength':1,'maxLength':160},
            'speaker':{'type':'string','enum':list(aliases)},
            'nature':{'type':'string','enum':['opinion','argument','proposition','question','decision_evoquee','intention_vote','contexte']},
            'text':{'type':'string','minLength':1,'maxLength':700},
            'sources':{'type':'array','minItems':1,'uniqueItems':True,'items':{'type':'string','enum':ids}},
            'uncertainty':{'type':'string','maxLength':180}})}})
        compact_instruction=(
            'Écris un compte rendu SYNTHÉTIQUE de ces échanges : trois à six paragraphes courts, au discours INDIRECT. '
            'Regroupe les critiques et arguments d’une même voix et d’un même sujet. '
            'Un paragraphe appartient à une seule voix. text reformule en une à trois phrases ; NE RECOPIE PAS le dialogue. '
            'Exemples de style : « La personne critique la portée des économies annoncées. » ; '
            '« La personne demande une réponse à sa question. » Ne copie pas ces exemples comme des faits. '
            'Renseigne les ID des sources précises sans recopier leurs citations : le logiciel les fournira. '
            'Rapporte les opinions comme opinions, les questions comme questions, les intentions comme intentions. '
            'Une critique n’est ni un engagement ni une décision. Aucun résultat de vote ou adoption inventé. '
            'Respecte négations, chiffres, dates, noms cités et portée des montants. '
            'uncertainty est vide si les propos sont compréhensibles ; le défaut de justification d’une opinion '
            'n’empêche pas de la rapporter comme opinion. Ne devine aucune identité de voix.')
        generated=call_json(model_request,f'automatic-{index:04d}',compact_instruction,
            {'agenda':request.get('agenda',[]),'lexicon':request.get('lexicon',[]),'turns':model_block},compact_schema,tokens=1800)
        if 'paragraphs' in generated:
            result={'subjects':[]}
            kinds={'opinion':'position','argument':'argument','proposition':'proposal','question':'question',
                'decision_evoquee':'reported_decision','intention_vote':'context','contexte':'context'}
            for paragraph in generated['paragraphs']:
                # Each quote is copied from the unchanged source, never generated.
                result['subjects'].append({'title':paragraph['topic'],'interventions':[{
                    'speaker':aliases[paragraph['speaker']],'kind':kinds[paragraph['nature']],
                    'text':paragraph['text'],'uncertainty':paragraph['uncertainty'],
                    'evidence':[{'id':sid,'quote':part['text']} for sid in paragraph['sources'] for part in block
                        if part['id']==sid]}]})
        else:
            result=generated  # Previously structured in-memory results remain readable.
        candidates=[{'id':f'c{i}','subject':subject['title'],**item} for i,(subject,item) in enumerate(
            ( (subject,item) for subject in result['subjects'] for item in subject['interventions']))]
        checks={}
        if candidates:
            check_instruction=('Contrôle chaque formulation, son type, son sujet et son auteur contre ses citations et le contexte. '
                'supported exige que tous les détails soient explicites : négations, chiffres, modalités, question, opinion '
                'rapportée ou critiquée, intention et proposition. Ne transforme pas un récit en recommandation ni une '
                'proposition en décision. Un titre ne doit pas ajouter une thèse. Refuse tout résultat de vote. '
                'Ce contrôle est un avis machine, pas une vérité humaine.')
            inputs={'candidates':candidates,'context':block}
            groups=[(candidates,block)]
            if len(json.dumps(inputs,ensure_ascii=False))>23500:
                from .hierarchical_summary import verification_context
                groups=[];batch=[];size=0
                for candidate in candidates:
                    amount=len(json.dumps(candidate,ensure_ascii=False))
                    if batch and size+amount>10000:
                        context=verification_context({'evidence':[e for c in batch for e in c['evidence']]},rows,budget=6000)
                        groups.append((batch,context));batch=[];size=0
                    batch.append(candidate);size+=amount
                if batch:
                    groups.append((batch,verification_context({'evidence':[e for c in batch for e in c['evidence']]},rows,budget=6000)))
            for gi,(batch,context) in enumerate(groups):
                label=f'automatic-check-{index:04d}'+(f'-{gi}' if len(groups)>1 else '')
                checks.update(call_json(model_request,label,check_instruction,
                    {'candidates':batch,'context':context},object_schema({c['id']:object_schema({
                        'supported':{'type':'boolean'},'reason':{'type':'string','maxLength':300}}) for c in batch}),tokens=1800))
        repairs={};repair_reasons={}
        if request.get('repair_rejected'):
            selected=[];used=0
            for candidate in candidates:
                valid,reason=assess(candidate,rows,request.get('lexicon',[]))
                if valid and checks[candidate['id']]['supported']:continue
                # Never ask a repair to invent a source or change its author.
                exact=all(e['id'] in by_id and normalized(e['quote']) in normalized(by_id[e['id']]['text']) and
                    (by_id[e['id']].get('speaker_id') or 'unattributed')==candidate['speaker'] for e in candidate['evidence'])
                if not exact:continue
                payload={'id':candidate['id'],'topic':candidate['subject'],'text':candidate['text'],
                    'kind':candidate['kind'],'quotes':[e['quote'] for e in candidate['evidence']],
                    'reason':reason if not valid else checks[candidate['id']]['reason']}
                size=len(json.dumps(payload,ensure_ascii=False))
                if used+size>16000:continue  # remaining items still enter the source fallback/inventory
                selected.append(payload);used+=size;repair_reasons[candidate['id']]=payload['reason']
            if selected:
                revision_schema=object_schema({'revisions':object_schema({c['id']:object_schema({
                    'topic':{'type':'string','minLength':1,'maxLength':160},
                    'text':{'type':'string','minLength':1,'maxLength':700},
                    'kind':{'type':'string','enum':['position','argument','proposal','question','context','reported_decision','reported_action']},
                    'uncertainty':{'type':'string','maxLength':180}}) for c in selected})})
                try:
                    # Do not show the rejected prose again: the small model tended
                    # to copy it. Rebuild only from the unchanged source excerpts.
                    repaired=call_json(model_request,f'automatic-repair-{index:04d}',
                        'À partir des seules citations, écris UNE phrase de compte rendu au discours indirect par entrée. '
                        'Exemple de style : citation « Nous avons organisé trois ateliers » devient '
                        '« La personne indique avoir organisé trois ateliers ». Ne copie pas cet exemple comme un fait. '
                        'Conserve exactement négations et modalités. Ne pas faire une délibération AVEC DÉBAT à chaque fois '
                        'ne veut pas dire ne pas faire de délibération. Une défense de sa probité ne devient pas une accusation. '
                        'N’ajoute ni exigence de transparence, ni projet politique, ni qualification publicitaire absents. '
                        'Évite toute généralisation et toute conséquence non exprimée. Nomme un sujet neutre, sans ajouter une thèse. '
                        'Aucun nom de voix ni résultat de vote. Les IDs, les sources et les voix sont fixes.',
                        {'items':[{'id':c['id'],'quotes':c['quotes'],'reason':c['reason']} for c in selected]},revision_schema,tokens=1200)
                    repairs=repaired['revisions']
                    review_items=[{'id':c['id'],'subject':repairs[c['id']]['topic'],'text':repairs[c['id']]['text'],
                        'kind':c['kind'],'quotes':c['quotes']} for c in selected]
                    recheck=call_json(model_request,f'automatic-repair-check-{index:04d}',
                        'Vérifie chaque reformulation corrigée contre ses seules citations. supported exige tous les détails explicites, '
                        'une modalité et une négation fidèles. Aucun ajout de conclusion, identité, décision ou résultat de vote. '
                        'Une source proche ne suffit pas à soutenir un détail absent. Ce verdict reste un avis machine.',
                        {'items':review_items},object_schema({c['id']:object_schema({
                            'supported':{'type':'boolean'},'reason':{'type':'string','maxLength':200}}) for c in selected}),tokens=1000)
                    checks.update(recheck)
                except Exception as error:
                    from notetaker.infrastructure.process import JobCancelled
                    if isinstance(error,JobCancelled):raise
                    repairs={}
                    atomic_json(workspace/f'automatic-repair-error-{index:04d}.json',
                        {'error_type':type(error).__name__,'message':str(error),'sources_preserved':True})
                    alerts.append('La réécriture ciblée n’a pas abouti. Les citations restent proposées à vérifier ; aucun ancien brouillon ni source n’est supprimé.')
        candidate_index=0
        for subject in result['subjects']:
            for item in subject['interventions']:
                cid=f'c{candidate_index}';original_text=item['text'];topic=subject['title']
                if cid in repairs:
                    # A rewrite changes prose, never the established author,
                    # source IDs or nature. Ignore its legacy kind field.
                    topic=repairs[cid]['topic'];item={**item,**{k:repairs[cid][k] for k in ('text','uncertainty')}}
                check=checks.get(cid,{'supported':False,'reason':'Contrôle absent'})
                candidate_index+=1
                claim = {k:item[k] for k in ('speaker','kind','text','evidence')}
                claim['id'] = 'A'+uuid.uuid4().hex[:20]
                # Only uniquely resolvable, literal quotations of this same voice
                # can be split back across consecutive saved source spans.
                resolved=resolve_evidence(claim,units)
                if resolved:claim=resolved
                signature = (claim['speaker'], normalized(claim['text']), tuple((e['id'],e['quote']) for e in claim['evidence']))
                if signature in seen:
                    continue
                seen.add(signature)
                valid, reason = assess(claim,rows,request.get('lexicon',[]))
                valid=valid and check['supported']
                if not check['supported']: reason=check['reason']
                # Source integrity is independent of a machine judgement of prose.
                exact = all(e['id'] in by_id and normalized(e['quote']) and
                    normalized(e['quote']) in normalized(by_id[e['id']]['text']) and
                    (by_id[e['id']].get('speaker_id') or 'unattributed') == claim['speaker'] for e in claim['evidence'])
                record = {'subject':topic, **item,'original_text':original_text,'repair_attempted':cid in repair_reasons,
                    'repair_reason':repair_reasons.get(cid),'resolved_evidence':claim['evidence'],'source_integrity':bool(exact),
                    'checks_passed':valid,'reason':reason,'id':claim['id']}
                inventory.append(record)
                if not exact:
                    alerts.append('Une formulation sans citation exacte a été écartée de la prose ; elle reste dans le dossier de génération.')
                    continue
                label=request['speaker_labels'].get(claim['speaker'],'Voix inconnue')
                voice_template=request.get('speaker_templates',{}).get(claim['speaker'],'Intervenant non identifié ({{V1}})')
                name=voice_template.replace('{{V1}}',label)
                if valid:
                    labels = {'position':'Opinion','argument':'Argument','proposal':'Proposition','question':'Question',
                        'context':'Échange','reported_decision':'Décision évoquée à confirmer','reported_action':'Engagement évoqué à confirmer'}
                    template=f"{labels[claim['kind']]} — {voice_template} : {claim['text']}"
                    if item['uncertainty']:
                        template='À vérifier — '+template
                        alerts.append(f"Source {claim['evidence'][0]['id']} : {item['uncertainty']}")
                    if any(by_id[e['id']].get('uncertain',False) for e in claim['evidence']):
                        template='Attribution à vérifier — '+template
                    text = template.replace('{{V1}}',label)
                    point = {'title':topic,'summary':text,'sources':list(dict.fromkeys(e['id'] for e in claim['evidence'])),
                        'vote_id':None,'claims':[claim],'narrative':[{'text':text,'template':template,
                            'voice_bindings':{'V1':claim['speaker']},'claim_ids':[claim['id']],
                            'machine_verdict':'machine_supported_requires_human_review'}]}
                else:
                    # Preserve the usable quotation, never promote a rejected paraphrase.
                    quote = ' […] '.join(e['quote'] for e in claim['evidence'])
                    if len(quote)>8500:
                        quote=quote[:8300].rsplit(' ',1)[0]+' […]'
                        alerts.append('Une citation affichée est abrégée ; ses passages complets et horaires restent disponibles dans les sources.')
                    text = f'À vérifier — {name} : « {quote} »'
                    at=by_id[claim['evidence'][0]['id']].get('start_ms',0)
                    point = {'title':f'Passage à vérifier — {at//60000:02d}:{at//1000%60:02d}','summary':text[:9000],
                        'sources':list(dict.fromkeys(e['id'] for e in claim['evidence'])),'vote_id':None}
                    alerts.append(f"Source {claim['evidence'][0]['id']} : {item['uncertainty'] or 'reformulation non retenue, citation conservée'}. Diagnostic : {reason}.")
                points.append(point)
    grouped=[]
    for point in points:
        previous=next((p for p in grouped if p['title']==point['title'] and 'narrative' in p and 'narrative' in point and
            len(p['summary'])+len(point['summary'])<9000),None)
        if previous:
            previous['summary']+=' '+point['summary'];previous['narrative']+=point['narrative'];previous['claims']+=point['claims']
            previous['sources']=list(dict.fromkeys(previous['sources']+point['sources']))
        else: grouped.append(point)
    points=grouped
    used = {sid for p in points for sid in p['sources']}
    uncovered = [u['id'] for u in rows if u['id'] not in used and u['text'].strip()]
    # A valid first draft remains possible even if the model produces nothing usable.
    # This fallback is labelled as source excerpts, never as a successful AI synthesis.
    if not points:
        for u in rows:
            if not u['text'].strip(): continue
            for offset in range(0,len(u['text']),6000):
                points.append({'title':'Passage source à vérifier — synthèse indisponible',
                    'summary':request['speaker_labels'].get(u.get('speaker_id'),'Intervenant non identifié')+' — « '+u['text'][offset:offset+6000]+' »',
                    'sources':[u['id']], 'vote_id':None})
        alerts.append('Qwen n’a pas fourni de reformulation exploitable. Ce document contient des extraits à examiner, pas une synthèse validée.')
    warnings = ['BROUILLON NON RELU — aucune validation officielle. Contrôler le sens, les auteurs, les chiffres et les sources audio.',
        'Les résultats de vote et décisions officiels doivent être confirmés et saisis séparément.']
    if uncovered:
        warnings.append(f'{len(uncovered)} passage(s) sans reprise dans la synthèse. Inventaire et transcription intégrale conservés dans le dossier de génération.')
    if any(u.get('uncertain') for u in rows):
        warnings.append('Des voix ou chevauchements restent incertains. Une attribution automatique ne vaut pas confirmation humaine.')
    paraphrases=sum(len(p.get('claims',[])) for p in points)
    fallback_points=sum(not p.get('claims') for p in points)
    if not paraphrases:
        warnings.append('Aucune reformulation n’a passé les contrôles : ce brouillon contient des citations sources à examiner, pas une synthèse fiable.')
    atomic_json(workspace/'automatic-inventory.json', {'items':inventory,'unrepresented_source_ids':uncovered,
        'all_input_ids':list(by_id),'human_fidelity_measured':False})
    atomic_json(workspace/'summary-progress.json', {'phase':'automatic_report','completed':len(blocks),'total':len(blocks)})
    return {'document_mode':'summary','points':points,'to_verify':list(dict.fromkeys(warnings+alerts)),
            'generation_diagnostics':{'strategy':'automatic-first-draft-v3','blocks':len(blocks),'input_segments':len(rows),
            'paraphrase_claims':paraphrases,'quoted_fallback_points':fallback_points,
            'unrepresented_sources':uncovered,'inventory':'automatic-inventory.json','human_fidelity_measured':False}}
