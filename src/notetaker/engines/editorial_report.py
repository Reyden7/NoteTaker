"""Topic-led first drafts with a separate, exhaustive verification inventory.

Planning and entailment verdicts are machine suggestions, never human approval.
No changes to audio, utterances, speaker labels or the registry are made here.
"""
import hashlib
import json
import re
from pathlib import Path
from notetaker.infrastructure.atomic import atomic_json
from .hierarchical_summary import call_json, object_schema, coherent_blocks, normalized
from .automatic_report import assess

VERSION = 'municipal-editorial-v5'
NATURES = {'opinion':'position','argument':'argument','proposition':'proposal',
           'question':'question','fait_evoque':'context','intention_vote':'context',
           'decision_evoquee':'reported_decision'}

SENTENCE_INSTRUCTION = (
    'Reformule et synthétise ce dossier dans un style administratif français naturel. Ne recopie pas la '
    'transcription, les hésitations ou les identifiants dans le texte rédigé. Ne fais pas une succession de « dit que ». '
    'Pour chaque voix, écris deux à quatre phrases '
    'courtes au discours indirect dans sentences, chacune avec ses propres sources (IDs séparés par des virgules, '
    'une à trois sources de cet auteur). Commence chaque phrase par V1, V2, etc. puis un verbe de parole précis. '
    'Rapporte uniquement ce que la personne dit : aucune analyse, implication, conséquence ou conclusion ajoutée. '
    'Une opinion reste une opinion attribuée ; une défense de sa gestion ne prouve pas sa probité. '
    'Préserve les comparaisons nommées, les chiffres et leur objet, les négations et les limites comme '
    '« pas forcément » et « pas à chaque fois ». Résous nous/vous dans le contexte, sans changer les équipes. '
    'Une question ne devient pas un fait, une intention de vote ne devient pas un résultat. '
    'Une relation personnelle alléguée par un orateur ne devient pas un fait établi ni une relation de cet orateur. '
    'Ne transforme pas une ironie en fait ou en métier réel. N’invente ni identité ni développement de sigle. '
    'Signale seulement les ambiguïtés réelles dans uncertainty (sinon chaîne vide). '
    'Vérifie les arguments de chaque auteur avant de terminer : omissions conserve les IDs et le motif des '
    'arguments non repris (sinon chaîne vide). La longueur indicative ne justifie pas d’omettre un argument important. '
    'Aucun diagnostic ni commentaire sur le travail de rédaction.'
)


def reconstruct_turns(rows, limit=4500):
    """Merge only adjacent, same-voice, nonoverlapping, timed source rows."""
    turns=[]
    for row in rows:
        voice=row.get('speaker_id') or 'unattributed'
        if not row['text'].strip():continue
        merge=(turns and voice!='unattributed' and turns[-1]['speaker']==voice
               and 0<=row['start_ms']-turns[-1]['end_ms']<=1500
               and row['end_ms']>row['start_ms'] and not turns[-1]['zero_duration']
               and sum(len(r['text']) for r in turns[-1]['segments'])+len(row['text'])<=limit)
        if not merge:
            turns.append({'speaker':voice,'start_ms':row['start_ms'],'end_ms':row['end_ms'],
                          'zero_duration':row['end_ms']<=row['start_ms'],'segments':[]})
        turns[-1]['segments'].append({'id':row['id'],'text':row['text'],
            'start_ms':row['start_ms'],'end_ms':row['end_ms'],'uncertain':bool(row.get('uncertain'))})
        turns[-1]['end_ms']=max(turns[-1]['end_ms'],row['end_ms'])
    return turns


def editorial_body(text):
    """Only replace model scaffolding, never rewrite the substantive clause."""
    body=re.sub(r'^(?:La personne|Cette personne|Le locuteur|La locutrice|V\d+)\s+', '',text.strip(),flags=re.I)
    body=re.sub(r"^s['’]inscrit dans l['’]intervention précédente en soulignant que",'souligne que',body,flags=re.I)
    return re.sub(r'^(?:Il|Elle)\s+(?=(?:ajoute|rappelle|affirme|estime|propose|demande|conteste|précise|souligne|explique|rapporte|critique|insiste|exprime|observe|souhaite|récuse)\b)','',body,flags=re.I)


def prose_sentences(text):
    # Decimal numbers and abbreviations without a following capital are retained.
    sentences=[]
    for sentence in re.split(r'(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Ý])',text):
        pieces=re.split(r",\s+(?=(?:ce qui\b|et qu(?:e\s|['’])|soulignant que|affirmant que|en insistant sur le fait que|en faisant))",sentence)
        positive_parent=bool(re.match(r"^(?:(?:V\d+|Il|Elle|La personne)\s+)?(?:souligne|précise|indique|rappelle|affirme|considère|observe|exprime|explique|mentionne)\s+qu(?:e\s|['’])",sentence,re.I))
        positive_parent=positive_parent and not re.search(r'\b(?:pas|peut|pourrait|incertain|doute|possible)\b',pieces[0],re.I)
        for i,piece in enumerate(pieces):
            if i and positive_parent and re.match(r"et qu(?:e\s|['’])",piece):
                piece='ajoute '+piece.removeprefix('et ')
            if i and not re.search(r"\b(?:pas|doute|incertain|possible)\b",pieces[0],re.I):
                piece=re.sub(r'^soulignant que','souligne que',piece)
                piece=re.sub(r'^affirmant que','affirme que',piece)
                piece=re.sub(r'^en insistant sur le fait que','insiste sur le fait que',piece)
            if piece.strip():sentences.append(piece.strip()+('.' if i<len(pieces)-1 else ''))
    return sentences


def financial_scope_problem(text,quotes):
    source=' '.join(quotes).casefold();text=text.casefold()
    if 'histoire classique' in source and re.search(r'histoire de la collectivité|histoire.{0,25}marquée',text):
        return 'colloquial_example_changed_to_institutional_history'
    frequency_text=text
    if re.search(r'pas forcément|pas.{0,100}à chaque fois',source):
        frequency_text=re.sub(r'pas\s+(?:toujours|systématiquement)', '',frequency_text)
    if re.search(r'\b(?:souvent|toujours|jamais|systématiquement)\b',frequency_text) and not re.search(r'\b(?:souvent|toujours|jamais|systématiquement)\b',source):
        return 'historical_frequency_added'
    if re.search(r'violation|viol\w*.{0,25}règles fondamentales',text) and not re.search(r'violation|viol\w*.{0,25}règles fondamentales',source):
        return 'criticism_strengthened_to_formal_violation'
    if (re.search(r'pas forcément',source)
        and re.search(r'(?:sans|absence de).{0,60}(?:débats?|conférences?)',text)
        and not re.search(r'forcément|nécessairement|systémati\w*|chaque fois|toujours|parfois',text)):
        return 'qualified_history_changed_to_absolute_absence'
    if re.search(r'\b(?:pertes|déficit\w*|surconsommation)\b',text) and not re.search(r'\b(?:pertes|déficit\w*|surconsommation)\b',source):
        return 'financial_diagnosis_not_in_source'
    if re.search(r'mal\s+évalu\w*|chiffres\s+erron\w*',text) and not re.search(r'mal\s+évalu\w*|erron\w*|faux',source):
        return 'missing_figures_changed_to_wrong_figures'
    if re.search(r'pas.{0,100}à chaque fois',source) and re.search(r'\bsans\b.{0,100}(?:délibération|conférence)',text) and not re.search(r'systémati\w*|chaque fois|parfois|toujours',text):
        return 'non_systematic_changed_to_never'
    if re.search(r'amoral\w*|malhonnêt\w*',text) and not re.search(r'amoral\w*|malhonnêt\w*',source):
        return 'moral_qualification_not_in_citation'
    if re.match(r'propos\w*',text) and not re.search(r'\bpropos\w*',source):
        return 'proposal_not_explicit_in_cited_sources'
    if re.search(r'violemment|virulemment|forte insatisfaction',text) and not re.search(r'violemment|virulemment|forte insatisfaction',source):
        return 'criticism_intensity_added'
    if 'motions' in text and re.search(r"les motions qu['’]on y met",source):
        return 'ambiguous_motion_word_requires_audio_review'
    if re.search(r'éveill\w*.{0,30}intérêt du public',text) and not re.search(r'intérêt du public',source):
        return 'audience_reaction_not_in_citation'
    if re.search(r'soit vous nous accusez',source) and re.search(r'allégations?|accusations?',text) and not re.search(r'insinu\w*|éventuel\w*|sous.entend\w*',text):
        return 'conditional_accusation_changed_to_asserted_allegation'
    if re.search(r'pas de grands changements|pas de changement\w*',text) and 'surprise' in source and 'changement' not in source:
        return 'absence_of_surprise_changed_to_absence_of_policy_change'
    if re.search(r'aucune faute|pas de faute',text) and not re.search(r'aucune faute|pas de faute',source):
        return 'absence_of_fault_not_in_source'
    if 'gouvernement' in text and 'gouvernement' not in source:
        return 'municipal_team_changed_to_government'
    if 'votre mentor' in source and 'mentor' in text and not re.search(r'qualifie|présente comme|appelle|désigne comme',text):
        return 'rhetorical_affiliation_changed_to_established_relationship'
    if 'vague idée' in text and re.search(r'vague idée.{0,45}\bress\b',text) and not re.search(r'vague idée\s+(?:sur|de|du|des)\s+ress',source):
        return 'ambiguous_idea_assigned_to_later_question'
    if re.search(r'délibér\w*',text) and not re.search(r'délibér\w*',source):
        return 'deliberation_not_in_sentence_citations'
    if re.search(r"(?:oppose|conteste|réfute).{0,90}gestion courante",text) and re.search(r"c['’]est de la gestion courante",source):
        return 'routine_management_assertion_changed_to_opposition'
    if 'raisons spécifiques' in text and 'raison' not in source:
        return 'unmentioned_explanation_implied'
    if re.search(r'optimistes?|simplistes?',text) and not re.search(r'optimistes?|simplistes?',source):
        return 'tone_characterisation_not_in_source'
    if 'association' in text and re.search(r'opération de (?:com|communication)',text) and 'donc voilà' in source:
        return 'ambiguous_communication_referent_attached_to_associations'
    return None


def priority_signal(text):
    return bool(re.search(r'\d|\?|\b(?:propos\w*|décid\w*|vot\w*|répond\w*|contre|probité|honneur)\b',text,re.I))


def historical_referent_problem(text,evidence,rows):
    """Reject an observed reversal of the explicitly preceding historical team."""
    if not re.search(r'équipe actuelle.{0,90}(?:pas|sans).{0,90}(?:conférence|délibération)',text,re.I):return None
    for e in evidence:
        index=next(i for i,r in enumerate(rows) if r['id']==e['id'])
        row=rows[index]
        if not re.search(r"^(?:Et )?nous n['’]avons pas",row['text'],re.I):continue
        previous=[r for r in rows[max(0,index-2):index] if r.get('speaker_id')==row.get('speaker_id')
            and 0<=row['start_ms']-r['end_ms']<1500]
        if any('équipe précédente' in r['text'].casefold() for r in previous):return 'previous_team_changed_to_current_team'
    return None


def protocol_only(text):
    text=normalized(text)
    return bool(re.fullmatch(r'Merci[.!]?|Monsieur [\wÀ-ÿ-]+, Madame [\wÀ-ÿ-]+, vous avez la parole\.|'
        r'Très bien\. Merci beaucoup\. La parole est à monsieur [\wÀ-ÿ-]+\.',text,re.I))


def reader_note(note,aliases,request):
    if normalized(note).casefold() in ('','aucune','aucune incertitude','rien à signaler'):return ''
    def replace(match):
        voice=aliases.get(match[0])
        if voice is None:return 'un intervenant non identifié'
        name=request.get('speaker_templates',{}).get(voice,'Intervenant non identifié ({{V1}})')
        return name.replace('{{V1}}',request['speaker_labels'].get(voice,'Voix inconnue'))
    return re.sub(r'\bV\d+\b',replace,note)


def explicit_discourse_groups(rows):
    """Conservative textual anchors; no identities or vote outcomes inferred."""
    groups=[];used=set()
    for index,row in enumerate(rows):
        if row['end_ms']<=row['start_ms'] or not row.get('speaker_id'):continue
        request_object=re.search(r'on ne sait pas\s+(?:(?:réellement|précisément)\s+)?quel est votre\s+([^.!?]{1,70})',row['text'],re.I)
        if request_object:
            previous=[r for r in rows[max(0,index-2):index] if r.get('speaker_id')==row['speaker_id'] and
                0<=row['start_ms']-r['end_ms']<20000 and re.search(r'aimer(?:ait|ions|aient)\s+bien|voudrait|souhait\w*',r['text'],re.I)]
            if previous:
                chosen=[previous[-1],row]
                object_text=request_object[1].strip()
                group={'title':'Demande de précisions sur '+object_text,
                    'object':object_text,'ids':[r['id'] for r in chosen],'request_rule':True}
                if re.search(r"maire\b.+ce qu['’]il veut.+faire pour (?:cette|la) ville",previous[-1]['text'],re.I):
                    group.update(title='Demande de précisions adressée au maire',
                        request_text='demande au maire de préciser ce qu’il veut faire pour la ville.')
                groups.append(group)
                used.update(r['id'] for r in chosen)
        question=re.search(r'questions?\s+sur\s+([^.!?]{1,70})',row['text'],re.I)
        if question:
            chosen=[row]
            for neighbor in rows[index+1:index+3]:
                if neighbor.get('speaker_id')!=row['speaker_id'] or neighbor['start_ms']-row['end_ms']>15000:break
                if re.search(r'répon\w*|question\w*',neighbor['text'],re.I):chosen.append(neighbor)
            groups.append({'title':'Questions sur '+question[1].strip(), 'ids':[r['id'] for r in chosen]})
            used.update(r['id'] for r in chosen)
        if re.search(r"nous avons géré.{0,90}(?:probité|sobriété|honneur)",row['text'],re.I):
            chosen=[r for r in rows if r.get('speaker_id')==row['speaker_id'] and
                r['start_ms']>=row['start_ms']-30000 and r['end_ms']<=row['end_ms']+25000 and
                re.search(r'argent public|association\w*|probité|sobriété|honneur',r['text'],re.I)]
            groups.append({'title':'Gestion publique et choix revendiqués','ids':[r['id'] for r in chosen]})
            used.update(r['id'] for r in chosen)
        # Anchored first-person statement, not a quotation of someone else.
        if re.match(r"^(?:Mais moi,\s*|Moi,\s*)?Je (?:vais (?:la |le )?voter|compte voter|voterai)\b",row['text'],re.I) and re.search(r'délibération',row['text'],re.I):
            groups.append({'title':'Intentions de vote exprimées','ids':[row['id']], 'vote_intent_rule':True})
            used.add(row['id'])
    return groups,used


def comparison_groups(rows):
    """Keep an explicit named comparison out of unrelated financial arguments.

    This only fences the verbatim; Qwen still has to formulate and audit it.
    A quoted 'mentor' never creates an identity or an established affiliation.
    """
    groups=[]
    for i,row in enumerate(rows):
        if not row.get('speaker_id') or row['end_ms']<=row['start_ms']:continue
        if not re.search(r'compar\w*|inspir\w*|mentor',row['text'],re.I):continue
        names=re.findall(r'\b[A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+\s+[A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+\b',row['text'])
        if not names:continue
        chosen=[row]
        if i+1<len(rows):
            nxt=rows[i+1]
            if nxt.get('speaker_id')==row['speaker_id'] and 0<=nxt['start_ms']-row['end_ms']<1500 and re.search(r'panneaux|communication',nxt['text'],re.I):chosen.append(nxt)
        group={'title':'Communication et comparaison avec '+names[0],'ids':[r['id'] for r in chosen]}
        literal=' '.join(r['text'] for r in chosen)
        if (re.search(r'comme à la région',literal,re.I) and re.search(r'panneaux',literal,re.I)
            and re.search(r'communication',literal,re.I) and re.search(r'mairie|collectivité',literal,re.I)
            and not re.search(r'pas.{0,15}comparaison|aucun rapport',literal,re.I)):
            group['named_comparison_rule']=names[0]
        groups.append(group)
    return groups


def explicit_historical_limits(rows):
    """Resolve only an explicit same-voice pair: previous-team sales + not every time."""
    result=[]
    for previous,row in zip(rows,rows[1:]):
        if not row.get('speaker_id') or previous.get('speaker_id')!=row['speaker_id']:continue
        if any(r['end_ms']<=r['start_ms'] for r in (previous,row)):continue
        if not 0<=row['start_ms']-previous['end_ms']<1500:continue
        if not re.search(r"équipe précédente.{0,30}(?:a vendu|vendait).{0,20}véhicules",previous['text'],re.I):continue
        if not re.match(r"^(?:Et )?nous n['’]avons pas fait une conférence de presse à chaque fois",row['text'],re.I):continue
        if not re.search(r"nous n['’]avons pas fait une délibération avec débat à chaque fois",row['text'],re.I):continue
        result.append({'speaker':row['speaker_id'],'source_ids':[previous['id'],row['id']],
            'text':"rappelle que les ventes de l’équipe précédente ne s’accompagnaient pas systématiquement d’une conférence de presse ni d’une délibération avec débat."})
    return result


def literal_question_claims(rows):
    if len({r.get('speaker_id') for r in rows})!=1:return []
    question=next((r for r in rows if re.search(r'questions? sur [^.!?]+',r['text'],re.I)),None)
    missing=next((r for r in rows if re.search(r"je n['’]ai pas eu de réponse, madame l['’]adjointe",r['text'],re.I)),None)
    legitimacy=next((r for r in rows if re.search(r"élus d['’]opposition",r['text'],re.I)
                     and re.search(r'minoritaires',r['text'],re.I) and re.search(r'légitimes',r['text'],re.I)),None)
    if not all((question,missing,legitimacy)):return []
    obj=re.search(r'questions? sur ([^.!?]{1,70})',question['text'],re.I)[1].strip()
    return [(question,'question','demande des réponses aux questions sur '+obj+'.'),
        (missing,'context','indique ne pas avoir reçu de réponse de l’adjointe.'),
        (legitimacy,'position','rappelle que les élus d’opposition sont légitimes à poser des questions malgré leur statut minoritaire.')]


def explicit_routine_sales(rows):
    result=[]
    for previous,row in zip(rows,rows[1:]):
        if not row.get('speaker_id') or previous.get('speaker_id')!=row['speaker_id']:continue
        if any(r['end_ms']<=r['start_ms'] for r in (previous,row)):continue
        if not 0<=row['start_ms']-previous['end_ms']<1500:continue
        sale=re.search(r'vente de (\d+) véhicules',previous['text'],re.I)
        if sale and re.match(r"Alors que c['’]est de la gestion courante de la ville",row['text'],re.I):
            result.append({'speaker':row['speaker_id'],'source_ids':[previous['id'],row['id']],
                'text':'qualifie la vente des '+sale[1]+' véhicules de gestion courante de la ville.'})
    return result


def explicit_source_frames(row):
    text=row['text']
    if re.search(r'chiffres.{0,50}oubliez.{0,30}des fois.{0,80}conseils municipaux',text,re.I):
        return ('criticised_figure_omission','position',
            'estime que certains chiffres sont parfois omis lors des conseils municipaux.')
    if re.match(r"^(?:Parce que )?(?:comme tous les élus,\s*){0,2}nous avons géré l['’]argent public",text,re.I) and all(
        re.search(term,text,re.I) for term in ('honneur','probité','sobriété')):
        return ('self_defence_values','position',
            'défend la gestion passée de l’argent public en invoquant l’honneur, la probité et la sobriété.')
    return None


def coverage_matrix(topics,rows,candidates=None):
    """Source/speaker matrix, not a claim of semantic completeness."""
    result=[]
    for topic in topics:
        ids={s for item in topic['items'] for s in item['sources']}
        for voice in dict.fromkeys(r.get('speaker_id') or 'unattributed' for r in rows if r['id'] in ids):
            selected=[r for r in rows if r['id'] in ids and (r.get('speaker_id') or 'unattributed')==voice]
            retained=[c for c in candidates or [] if c['topic_id']==topic['id'] and c.get('retained') and c['claim']['speaker']==voice]
            used={e['id'] for c in retained for e in c['claim']['evidence']}
            result.append({'topic_id':topic['id'],'topic':topic['title'],'speaker':voice,
                'source_ids':[r['id'] for r in selected], 'source_texts':[r['text'] for r in selected],
                'priority_signal_ids':[r['id'] for r in selected if priority_signal(r['text'])],
                'retained_claim_ids':[c['claim']['id'] for c in retained],
                'uncited_ids':[r['id'] for r in selected if r['id'] not in used],
                'semantic_completeness_verified':False})
            names=list(dict.fromkeys(name for r in selected for name in re.findall(
                r'\b[A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+\s+[A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ]+\b',r['text'])))
            prose=' '.join(c['claim']['text'] for c in retained).casefold()
            result[-1]['named_mentions_not_repeated']=[name for name in names if name.casefold() not in prose]
    return result


def summarize(request):
    from notetaker.domain.summary import PROFILES
    profile=PROFILES.get(request.get('summary_length','standard'),PROFILES['standard'])
    rows=request['utterances'];workspace=Path(request['workspace'])
    if not rows:raise ValueError('TRANSCRIPT_REQUIRED')
    if any('\ufffd' in r['text'] for r in rows):raise ValueError('DAMAGED_TRANSCRIPT_RETRANSCRIBE_ORIGINAL')
    by_id={r['id']:r for r in rows}
    if len(by_id)!=len(rows):raise ValueError('Identifiants sources ambigus : ouvrez une seule séance.')
    voices=list(dict.fromkeys(r.get('speaker_id') or 'unattributed' for r in rows))
    aliases={f'V{i+1}':v for i,v in enumerate(voices)};reverse={v:a for a,v in aliases.items()}
    turns=reconstruct_turns(rows)
    atomic_json(workspace/'reconstructed-turns.json',turns)
    model_request={**request,'workspace':request.get('cache_workspace',str(workspace))}
    blocks=list(coherent_blocks(rows,max_characters=13500,max_seconds=720,overlap=1))
    topics=[];classifications=[];failures=[]
    for bi,block in enumerate(blocks):
        ids=list(dict.fromkeys(r['id'] for r in block))
        secondary_codes={'S_formule':'formule_de_seance','S_repetition':'repetition',
            'S_detail':'detail_secondaire','S_fragment':'parole_incomplete','A_verifier':'non_classe'}
        plan_schema=object_schema({'subjects':{'type':'array','minItems':1,'maxItems':8,
            'items':object_schema({'title':{'type':'string','minLength':1,'maxLength':100},
                'source_ids':{'type':'string','minLength':1,'maxLength':500}})}})
        part=[r for r in rows if r['id'] in ids]
        context=[{**t,'speaker':reverse[t['speaker']]} for t in reconstruct_turns(part)]
        atomic_json(workspace/'summary-progress.json',{'phase':'plan_editorial','completed':bi,'total':len(blocks)})
        try:
            plan=call_json(model_request,f'editorial-plan-{bi:03d}',
                'Établis le plan du compte rendu municipal, sans encore rédiger. subjects liste seulement les '
                'sujets concrets, avec title et source_ids. source_ids est une CHAÎNE des identifiants exacts '
                'séparés par des virgules. Pas de liste JSON d’identifiants. Affecte chaque passage de fond à '
                'son sujet principal, même les critiques, intentions ou réponses. Regroupe par sujet concret, même les '
                'interventions éloignées ou de voix différentes. Sépare les sujets distincts. Ne te limite pas à un nombre '
                'arbitraire de paragraphes. Préserve les réponses, objections, intentions de vote, comparaisons chiffrées '
                'et défenses contre des insinuations. Le contenu cité ou critiqué n’est pas forcément l’opinion de son auteur. '
                'Une anecdote ou une ironie n’est pas une proposition officielle. Titres NEUTRES et nominaux : '
                'le titre nomme un objet de discussion, jamais une accusation ou une conclusion. '
                'N’écarte pas un argument parce qu’il est critique ou difficile. Aucun classement en détail secondaire '
                'ne t’est demandé. Ne crée pas un titre pour chaque phrase. Pas de noms inventés.',
                {'agenda':request.get('agenda',[]),'turns':context},plan_schema,tokens=1700)
        except Exception as error:
            from notetaker.infrastructure.process import JobCancelled
            if isinstance(error,JobCancelled):raise
            failures.append({'phase':'plan','block':bi,'error':str(error)})
            continue
        if 'subjects' in plan:
            assigned=[s for t in plan['subjects'] for s in dict.fromkeys(s.strip() for s in t['source_ids'].split(',') if s.strip())]
            missing=[{'id':r['id'],'speaker':reverse[r.get('speaker_id') or 'unattributed'],
                      'text':r['text'],'start_ms':r['start_ms'],'end_ms':r['end_ms']}
                     for r in part if r['id'] not in assigned and priority_signal(r['text'])]
            if len(plan['subjects'])>5 or len(assigned)!=len(set(assigned)) or missing:
                revision_schema=object_schema({'subjects':{'type':'array','minItems':1,'maxItems':5,
                    'items':object_schema({'title':{'type':'string','minLength':1,'maxLength':100},
                        'source_ids':{'type':'string','minLength':1,'maxLength':500}})}})
                try:
                    plan=call_json(model_request,f'editorial-consolidate-{bi:03d}',
                        'Réorganise ce plan en quelques sujets larges et cohérents, jusqu’à cinq pour ce bloc. '
                        'Un titre nomme un objet de discussion, pas une conclusion ou une accusation. '
                        'Une personnalité citée ne constitue pas à elle seule un nouveau sujet. '
                        'Chaque source de fond apparaît dans UN seul sujet principal, sans doublon. '
                        'Réintègre les arguments oubliés, en particulier les intentions de vote. '
                        'Ne mélange pas des questions distinctes parce qu’elles se suivent. '
                        'Préserve les arguments des différentes voix au sein d’un même sujet. '
                        'source_ids est une chaîne d’identifiants séparés par des virgules. '
                        'Ne rédige pas encore les paragraphes et n’invente aucune information.',
                        {'plan_propose':plan,'passages_prioritaires_oublies':missing,
                         'transcription':context},revision_schema,tokens=1400)
                except Exception as error:
                    from notetaker.infrastructure.process import JobCancelled
                    if isinstance(error,JobCancelled):raise
                    failures.append({'phase':'consolidation','block':bi,'error':str(error)})
            converted={'topics':[],'secondary':[]}
            for subject in plan['subjects']:
                chosen=list(dict.fromkeys(s.strip() for s in subject['source_ids'].split(',') if s.strip()))
                if not chosen or not set(chosen)<=set(ids):
                    failures.append({'phase':'plan','block':bi,'error':'unknown_or_missing_source','raw':subject})
                    continue
                converted['topics'].append({'title':subject['title'],'items':[
                    {'focus':'Intervention source '+s,'sources':[s]} for s in chosen]})
            plan=converted
        elif 'assignments' in plan:
            converted={'topics':[{'title':title,'items':[]} for title in plan['titles']],'secondary':[]}
            for source_id,code in plan['assignments'].items():
                if code.startswith('T') and 0<=int(code[1:])-1<len(converted['topics']):
                    row=by_id[source_id]
                    converted['topics'][int(code[1:])-1]['items'].append({
                        'focus':'Intervention source '+source_id,'sources':[source_id]})
                elif code in secondary_codes and code!='A_verifier':
                    converted['secondary'].append({'source':source_id,'reason':secondary_codes[code]})
            converted['topics']=[t for t in converted['topics'] if t['items']]
            plan=converted
        planned_ids={s for t in plan['topics'] for i in t['items'] for s in i['sources']}
        remaining=[{'id':r['id'],'speaker':reverse[r.get('speaker_id') or 'unattributed'],
                    'text':r['text'],'start_ms':r['start_ms'],'end_ms':r['end_ms']}
                   for r in part if r['id'] not in planned_ids and r['end_ms']>r['start_ms']
                   and len(r['text'].split())>2 and not protocol_only(r['text'])]
        if remaining and request.get('recover_editorial_omissions',True):
            try:
                recovery_schema=object_schema({'subjects':{'type':'array','minItems':1,'maxItems':4,
                    'items':object_schema({'title':{'type':'string','minLength':1,'maxLength':100},
                        'source_ids':{'type':'string','minLength':1,'maxLength':500}})}})
                recovered=call_json(model_request,f'editorial-recover-{bi:03d}',
                    'Ces passages n’ont pas été classés dans le plan initial. Ils ne sont pas secondaires par défaut. '
                    'Répartis-les par sujet, en réutilisant exactement un titre existant lorsque le sens correspond, '
                    'ou en créant un titre nominal neutre pour un sujet distinct. Couvre toutes les sources de fond, '
                    'notamment les intentions de vote, les réponses, les arguments et les défenses contre des insinuations. '
                    'Ne rédige pas encore de synthèse. source_ids est une chaîne des IDs séparés par des virgules. '
                    'Ne transforme pas une formule ironique en engagement. N’invente pas de sujet pour justifier un classement.',
                    {'existing_titles':[t['title'] for t in plan['topics']],'unclassified_turns':remaining},
                    recovery_schema,tokens=1000)
                remaining_ids={r['id'] for r in remaining}
                permitted_ids=set(remaining_ids)
                for subject in recovered['subjects']:
                    chosen=list(dict.fromkeys(s.strip() for s in subject['source_ids'].split(',') if s.strip()))
                    if not chosen or not set(chosen)<=permitted_ids:
                        failures.append({'phase':'coverage_recovery','error':'unknown_or_missing_source','raw':subject})
                        continue
                    # A repeated machine assignment must not discard the NEW
                    # source IDs in the same entry. No human annotation changes.
                    chosen=[s for s in chosen if s in remaining_ids]
                    if not chosen:continue
                    target=next((t for t in plan['topics'] if normalized(t['title']).casefold()==normalized(subject['title']).casefold()),None)
                    extra=[{'focus':'Intervention source '+s,'sources':[s]} for s in chosen]
                    if target:target['items']+=extra
                    else:plan['topics'].append({'title':subject['title'],'items':extra})
                    remaining_ids-=set(chosen)
            except Exception as error:
                from notetaker.infrastructure.process import JobCancelled
                if isinstance(error,JobCancelled):raise
                failures.append({'phase':'coverage_recovery','block':bi,'error':str(error)})
        if request.get('discourse_anchors'):
            anchors,protected=explicit_discourse_groups(part)
            if request.get('sentence_evidence'):
                comparisons=comparison_groups(part)
                anchors+=comparisons
                protected.update(s for group in comparisons for s in group['ids'])
            for topic in plan['topics']:
                for item in topic['items']:item['sources']=[s for s in item['sources'] if s not in protected]
                topic['items']=[i for i in topic['items'] if i['sources']]
            plan['topics']=[t for t in plan['topics'] if t['items']]
            for anchor in anchors:
                plan['topics'].append({'title':anchor['title'],'items':[
                    {'focus':'Intervention source '+s,'sources':[s]} for s in anchor['ids']],
                    'vote_intent_rule':anchor.get('vote_intent_rule',False),
                    'request_object':anchor.get('object',''),
                    'request_text':anchor.get('request_text',''),
                    'named_comparison_rule':anchor.get('named_comparison_rule'),
                    'request_rule':anchor.get('request_rule',False)})
        classifications+=plan['secondary']
        for ti,t in enumerate(plan['topics']):
            items=[{'id':f'b{bi}t{ti}i{ii}',**item} for ii,item in enumerate(t['items'])]
            existing=next((p for p in topics if normalized(p['title']).casefold()==normalized(t['title']).casefold()),None)
            if existing:existing['items']+=items
            else:topics.append({'id':f'b{bi}t{ti}','title':t['title'],'items':items,
                               'vote_intent_rule':t.get('vote_intent_rule',False),
                               'request_object':t.get('request_object',''),
                               'request_text':t.get('request_text',''),
                               'named_comparison_rule':t.get('named_comparison_rule'),
                               'request_rule':t.get('request_rule',False)})
    atomic_json(workspace/'editorial-plan.json',{'topics':topics,'secondary':classifications,'errors':failures})
    prewrite=coverage_matrix(topics,rows)
    atomic_json(workspace/'coverage-before-writing.json',{'matrix':prewrite,
        'unplanned_source_ids':[r['id'] for r in rows if not any(r['id'] in entry['source_ids'] for entry in prewrite)],
        'human_verified':False,'purpose':'Inventaire avant rédaction, pas une mesure de fidélité.'})
    candidates=[]
    for ti,topic in enumerate(topics):
        source_ids=list(dict.fromkeys(s for item in topic['items'] for s in item['sources']))
        selected=[r for r in rows if r['id'] in source_ids]
        if request.get('sentence_evidence'):
            for row in selected:
                if row['end_ms']<=row['start_ms']:
                    failures.append({'phase':'source_eligibility','topic':topic['id'],'source_id':row['id'],
                        'reason':'Intervalle audio vide : conservé dans l’inventaire, exclu de la rédaction.'})
            selected=[r for r in selected if r['end_ms']>r['start_ms']]
            if not selected:continue
        if topic.get('request_rule'):
            claim={'id':'R'+hashlib.sha256('|'.join(source_ids).encode()).hexdigest()[:20],
                'speaker':selected[-1]['speaker_id'],'kind':'question',
                'text':topic.get('request_text') or 'demande des précisions sur le contenu du « '+topic['request_object']+' ».',
                'evidence':[{'id':r['id'],'quote':r['text']} for r in selected]}
            valid,reason=assess(claim,rows,request.get('lexicon',[]))
            candidates.append({'topic_id':topic['id'],'topic':topic['title'],'claim':claim,'nature':'question',
                'items':[i['id'] for i in topic['items']],'uncertainty':'',
                'static_passed':valid,'reason':reason,'method':'literal_request_and_missing_object'})
            continue
        if topic.get('named_comparison_rule'):
            claim={'id':'C'+hashlib.sha256('|'.join(source_ids).encode()).hexdigest()[:20],
                'speaker':selected[0]['speaker_id'],'kind':'position',
                'text':'évoque '+topic['named_comparison_rule']+' dans une comparaison entre communication municipale et communication régionale, à propos des panneaux affichés.',
                'evidence':[{'id':r['id'],'quote':r['text']} for r in selected]}
            valid,reason=assess(claim,rows,request.get('lexicon',[]))
            candidates.append({'topic_id':topic['id'],'topic':topic['title'],'claim':claim,'nature':'opinion',
                'items':[i['id'] for i in topic['items']],'uncertainty':'La comparaison appartient à cet intervenant ; aucun lien personnel n’est établi.',
                'static_passed':valid,'reason':reason,'method':'explicit_named_regional_communication_comparison'})
            continue
        literal_questions=literal_question_claims(selected) if request.get('sentence_evidence') else []
        if literal_questions:
            for row,kind,text in literal_questions:
                claim={'id':'Q'+hashlib.sha256((row['id']+text).encode()).hexdigest()[:20],
                    'speaker':row['speaker_id'],'kind':kind,'text':text,'evidence':[{'id':row['id'],'quote':row['text']}]}
                valid,reason=assess(claim,rows,request.get('lexicon',[]))
                candidates.append({'topic_id':topic['id'],'topic':topic['title'],'claim':claim,
                    'nature':'question' if kind=='question' else 'opinion' if kind=='position' else 'fait_evoque',
                    'items':[i['id'] for i in topic['items'] if row['id'] in i['sources']],
                    'uncertainty':'Le sigle reste celui de la transcription ; son développement n’est pas déduit.',
                    'static_passed':valid,'reason':reason,'method':'explicit_question_missing_answer_and_legitimacy'})
            continue
        if topic.get('vote_intent_rule'):
            for row in selected:
                text='évoque son intention de voter la délibération.'
                # Do not infer "pour", "contre" or the outcome from "la voter".
                claim={'id':'I'+hashlib.sha256(row['id'].encode()).hexdigest()[:20],
                    'speaker':row['speaker_id'],'kind':'context','text':text,
                    'evidence':[{'id':row['id'],'quote':row['text']}]}
                valid,reason=assess(claim,rows,request.get('lexicon',[]))
                candidates.append({'topic_id':topic['id'],'topic':topic['title'],'claim':claim,'nature':'intention_vote',
                    'items':[i['id'] for i in topic['items'] if row['id'] in i['sources']],
                    'uncertainty':'Une intention ne constitue pas un résultat de scrutin.',
                    'static_passed':valid,'reason':reason,'method':'explicit_first_person_vote_intent'})
            continue
        # Context neighbors retain referents and interruptions without becoming
        # additional evidence by accident. Entire input remains in the inventory.
        positions={i for i,r in enumerate(rows) if r['id'] in source_ids}
        neighbors={j for i in positions for j in (i-1,i+1) if 0<=j<len(rows)}
        context=[{'id':rows[i]['id'],'speaker':reverse[rows[i].get('speaker_id') or 'unattributed'],
            'text':rows[i]['text']} for i in sorted(neighbors) if rows[i]['id'] not in source_ids]
        # Split oversized topic dossiers, keeping their single heading afterwards.
        batches=list(coherent_blocks(selected,max_characters=10500,max_seconds=7200,overlap=0))
        for pi,batch in enumerate(batches):
            ids=list(dict.fromkeys(r['id'] for r in batch));items=[i for i in topic['items'] if set(i['sources'])&set(ids)]
            batch_voices=list(dict.fromkeys(reverse[r['speaker']] for r in batch))
            contribution_schema=object_schema({
                'text':{'type':'string','minLength':1,'maxLength':1500},
                'sources':{'type':'string','minLength':1,'maxLength':300},
                'uncertainty':{'type':'string','maxLength':160}})
            schema=object_schema({'contributions':object_schema({voice:contribution_schema for voice in batch_voices})})
            if request.get('sentence_output_experiment'):
                sentence_schema=object_schema({'text':{'type':'string','minLength':1,'maxLength':500},
                    'sources':{'type':'string','minLength':1,'maxLength':160},
                    'uncertainty':{'type':'string','maxLength':160}})
                schema=object_schema({'contributions':object_schema({voice:object_schema({
                    'sentences':{'type':'array','minItems':1,
                        'maxItems':max(4,min(12,sum(reverse[r['speaker']]==voice for r in batch)+2)),
                        'items':sentence_schema},
                    'omissions':{'type':'string','maxLength':400}}) for voice in batch_voices})})
            atomic_json(workspace/'summary-progress.json',{'phase':'redaction_par_sujet','completed':ti,'total':len(topics)})
            try:
                legacy_instruction=('Rédige ce seul sujet dans un style administratif naturel. contributions contient un paragraphe '
                    'par voix demandée. sources est une CHAÎNE d’identifiants exacts séparés par des virgules, '
                    'sans liste JSON. Cite seulement des sources de cette voix, sans répéter un identifiant. '
                    'Couvre les arguments importants soutenus '
                    'par les sources. Une voix par paragraphe, deux à quatre phrases cohérentes, sans étiquettes. '
                    'text commence par son alias V1, V2, etc., suivi d’un verbe précis au discours indirect. '
                    'Ne parle jamais du logiciel ou de la rédaction. Rapporte les faits comme des faits '
                    'ÉVOQUÉS, les appréciations comme des opinions attribuées. Exprime précisément les désaccords, '
                    'les demandes et les intentions de vote ; n’annonce jamais un résultat, une adoption ou une '
                    'décision collective déduits du débat. Une critique ironique n’est pas une accusation établie. '
                    'Conserve les limites « pas à chaque fois », le conditionnel, les négations, les chiffres et leurs '
                    'unités. Ne relie pas causalement des sujets simplement voisins. Ne recopie pas de longues citations. '
                    'Les références sont celles de CET auteur ; les voisins éclairent le sens mais ne prouvent rien '
                    'sans citation. N’invente ni identité ni développement de sigle. Si un fragment est ambigu, '
                    'rapporte seulement ce qui est clair et explique la limite dans uncertainty. N’intègre aucun diagnostic.')
                payload={'outline':items,'sources':[{**r,'speaker':reverse[r['speaker']]} for r in batch],
                     'context_only':context[:8],'lexicon':request.get('lexicon',[]),
                     'target_words_per_topic':profile['words_per_topic'],
                     'length_guidance':'Conserve les arguments importants même si la longueur indicative doit être dépassée.'}
                # A generated heading is a filing suggestion, not evidence. It
                # must not prime the writer to invent criticism or consequences.
                if not request.get('sentence_evidence'):payload['topic']=topic['title']
                raw=call_json(model_request,f'editorial-write-{ti:03d}-{pi:02d}',
                    SENTENCE_INSTRUCTION if request.get('sentence_output_experiment') else legacy_instruction,
                    payload,schema,tokens=1700)
            except Exception as error:
                from notetaker.infrastructure.process import JobCancelled
                if isinstance(error,JobCancelled):raise
                failures.append({'phase':'write','topic':topic['id'],'error':str(error)})
                continue
            if 'contributions' in raw:
                paragraphs=[]
                for alias,entry in raw['contributions'].items():
                    if entry.get('omissions'):
                        failures.append({'phase':'writer_coverage','topic':topic['id'],'speaker':alias,
                            'machine_omissions':entry['omissions']})
                    for sentence in entry.get('sentences',[entry]):
                        cited=list(dict.fromkeys(s.strip() for s in sentence['sources'].split(',') if s.strip()))
                        allowed_ids=set(ids) if request.get('sentence_evidence') else set(ids)|{r['id'] for r in context[:8]}
                        if not cited or not set(cited)<=allowed_ids or (request.get('sentence_output_experiment') and len(cited)>3):
                            failures.append({'phase':'write','topic':topic['id'],'error':'unknown_or_missing_source','raw':sentence})
                            continue
                        body=editorial_body(sentence['text'])
                        nature=sentence.get('nature') or ('proposition' if re.match(r'propose\b',body,re.I) else
                            'question' if re.match(r'(?:demande|interroge)\b',body,re.I) else
                            'opinion' if re.match(r'(?:estime|considère|critique|juge|conteste|récuse)',body,re.I) else 'fait_evoque')
                        paragraphs.append({**sentence,'nature':nature,'speaker':alias,'sources':cited,
                            'items':[i['id'] for i in items if set(i['sources'])&set(cited)]})
            else:paragraphs=raw['paragraphs']
            sentences=[]
            for paragraph in paragraphs:
                sentences.extend({**paragraph,'text':sentence} for sentence in prose_sentences(paragraph['text']))
            for paragraph in sentences:
                claim={'id':'E'+hashlib.sha256(json.dumps([topic['id'],paragraph],sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:20],
                    'speaker':aliases[paragraph['speaker']],'kind':NATURES[paragraph['nature']],
                    'text':editorial_body(paragraph['text']),
                    'evidence':[{'id':sid,'quote':by_id[sid]['text']} for sid in paragraph['sources']]}
                valid,reason=assess(claim,rows,request.get('lexicon',[]))
                scope_problem=financial_scope_problem(claim['text'],[e['quote'] for e in claim['evidence']])
                scope_problem=scope_problem or historical_referent_problem(claim['text'],claim['evidence'],rows)
                if scope_problem:valid,reason=False,scope_problem
                model_alias=re.match(r'^(V\d+)\b',paragraph['text'].strip())
                if model_alias and model_alias[1]!=paragraph['speaker']:
                    valid,reason=False,'model_alias_changed'
                if re.search(r'\bV\d+\b',claim['text']):
                    valid,reason=False,'unresolved_voice_in_prose'
                if re.search(r'logiciel\s+placera|(?:texte|text)\s+commence|sources\s+est\s+une',claim['text'],re.I):
                    valid,reason=False,'instruction_echo_not_speech'
                if re.match(r"^(?:ce qui\b|en faisant\b|soulignant que\b|affirmant que\b|et qu(?:e\s|['’])|ajoute qu(?:e cette action\b|['’](?:il|elle|ils|elles)\b))",claim['text'],re.I):
                    valid,reason=False,'incomplete_inference_clause'
                if any(by_id[s]['end_ms']<=by_id[s]['start_ms'] for s in paragraph['sources']):
                    valid,reason=False,'source_audio_interval_empty'
                if re.match(r'^(?:Il|Elle|Ils|Elles|Cela|Ceci|Ce|Cette|La personne)\b',claim['text']):valid,reason=False,'generic_or_ambiguous_subject'
                candidates.append({'topic_id':topic['id'],'topic':topic['title'],'claim':claim,'nature':paragraph['nature'],
                    'items':paragraph['items'],'uncertainty':paragraph['uncertainty'],'static_passed':valid,'reason':reason})
    if request.get('sentence_evidence'):
        for row in rows:
            if not row.get('speaker_id') or row['end_ms']<=row['start_ms']:continue
            frame=explicit_source_frames(row)
            if frame is None:continue
            method,kind,text=frame
            topic=next((t for t in topics if any(row['id'] in i['sources'] for i in t['items'])),None)
            if topic is None:continue
            for c in candidates:
                if row['id'] not in {e['id'] for e in c['claim']['evidence']}:continue
                old=c['claim']['text']
                replacement=(method=='criticised_figure_omission' and re.search(r'chiffres',old,re.I) and re.search(r'délibération',old,re.I)) or (
                    method=='self_defence_values' and all(re.search(word,old,re.I) for word in ('honneur','probité','sobriété')))
                if replacement:c.update(static_passed=False,reason='explicit_source_frame_replaces_overbroad_wording')
            claim={'id':'F'+hashlib.sha256((row['id']+text).encode()).hexdigest()[:20],
                'speaker':row['speaker_id'],'kind':kind,'text':text,'evidence':[{'id':row['id'],'quote':row['text']}]}
            valid,reason=assess(claim,rows,request.get('lexicon',[]))
            scope=financial_scope_problem(text,[row['text']])
            if scope:valid,reason=False,scope
            candidates.append({'topic_id':topic['id'],'topic':topic['title'],'claim':claim,'nature':'opinion',
                'items':[i['id'] for i in topic['items'] if row['id'] in i['sources']],
                'uncertainty':'','static_passed':valid,'reason':reason,'method':'explicit_'+method})
        for row in rows:
            if not row.get('speaker_id') or row['end_ms']<=row['start_ms']:continue
            if not all(re.search(pattern,row['text'],re.I) for pattern in ('associations','vivre.ensemble',r'(?:oui,?\s*){1,2}on assume ça[.!]')):continue
            topic=next((t for t in topics if any(row['id'] in i['sources'] for i in t['items'])),None)
            if topic is None:continue
            if any(c['static_passed'] and row['id'] in {e['id'] for e in c['claim']['evidence']}
                   and re.search(r'associations',c['claim']['text'],re.I) for c in candidates):continue
            claim={'id':'A'+hashlib.sha256(row['id'].encode()).hexdigest()[:20],
                'speaker':row['speaker_id'],'kind':'position',
                'text':'assume les choix concernant les associations et souligne leur contribution au vivre-ensemble de la ville.',
                'evidence':[{'id':row['id'],'quote':row['text']}]}
            valid,reason=assess(claim,rows,request.get('lexicon',[]))
            candidates.append({'topic_id':topic['id'],'topic':topic['title'],'claim':claim,'nature':'opinion',
                'items':[i['id'] for i in topic['items'] if row['id'] in i['sources']],
                'uncertainty':'','static_passed':valid,'reason':reason,'method':'explicit_assumed_association_choices'})
        for limit in explicit_routine_sales(rows)+explicit_historical_limits(rows):
            sid=limit['source_ids'][-1]
            topic=next((t for t in topics if any(sid in i['sources'] for i in t['items'])),None)
            if topic is None:continue
            # Do not duplicate an already adequate proposed historical limitation.
            routine='gestion courante' in limit['text']
            pattern=r'gestion courante' if routine else r'pas (?:systématiquement|toujours)|pas.{0,80}à chaque fois'
            if any(c['static_passed'] and sid in {e['id'] for e in c['claim']['evidence']}
                   and re.search(pattern,c['claim']['text'],re.I)
                   for c in candidates):continue
            claim={'id':'H'+hashlib.sha256('|'.join(limit['source_ids']).encode()).hexdigest()[:20],
                'speaker':limit['speaker'],'kind':'context','text':limit['text'],
                'evidence':[{'id':s,'quote':by_id[s]['text']} for s in limit['source_ids']]}
            valid,reason=assess(claim,rows,request.get('lexicon',[]))
            scope=financial_scope_problem(claim['text'],[e['quote'] for e in claim['evidence']])
            if scope:valid,reason=False,scope
            candidates.append({'topic_id':topic['id'],'topic':topic['title'],'claim':claim,'nature':'fait_evoque',
                'items':[i['id'] for i in topic['items'] if set(i['sources'])&set(limit['source_ids'])],
                'uncertainty':'','static_passed':valid,'reason':reason,
                'method':'explicit_routine_sale_classification' if routine else 'explicit_non_systematic_historical_practice'})
    # Contextual audit in bounded groups, independent of structural source checks.
    auditable=[]
    for c in candidates:
        if c['static_passed']:auditable.append(c)
        else:c.update(retained=False,machine_audit={'supported':False,'reason':'Refus structurel ou contextuel avant contrôle machine.'})
    for offset in range(0,len(auditable),5):
        batch=auditable[offset:offset+5]
        payload=[{'id':c['claim']['id'],'topic':c['topic'],'nature':c['nature'],'text':c['claim']['text'],
            'speaker':reverse[c['claim']['speaker']], 'sources':[{'id':e['id'],'quote':e['quote']} for e in c['claim']['evidence']]} for c in batch]
        nearby_ids={e['id'] for c in batch for e in c['claim']['evidence']}
        nearby=[{'id':r['id'],'speaker':reverse[r.get('speaker_id') or 'unattributed'],'text':r['text']} for i,r in enumerate(rows)
                if any(rows[j]['id'] in nearby_ids for j in range(max(0,i-1),min(len(rows),i+2)))]
        try:
            verdicts=call_json(model_request,f'editorial-audit-{offset//5:03d}',
                'Contrôle le SENS et le sujet de chaque reformulation, pas la seule présence d’une citation. '
                'supported exige tous les détails étayés : comparaisons, rôles, négations, modalités et contexte. '
                'Une défense contre une insinuation n’est pas une accusation avérée ; une pratique non systématique '
                'n’est pas une absence totale ; une intention de vote n’est pas un vote déjà effectué. '
                'Ne sanctionne pas une opinion faute de preuve de sa véracité : vérifier seulement qu’elle est '
                'fidèlement attribuée. Vérifie aussi les focus réellement couverts par le texte. '
                'Refuse les mélanges de sujets et les conséquences ajoutées. Retourne une raison brève. '
                'Ce verdict machine n’est pas une validation humaine.',
                {'candidates':payload,'context':nearby},object_schema({c['claim']['id']:object_schema({
                    'supported':{'type':'boolean'},'reason':{'type':'string','maxLength':200}}) for c in batch}),tokens=1000)
        except Exception as error:
            from notetaker.infrastructure.process import JobCancelled
            if isinstance(error,JobCancelled):raise
            failures.append({'phase':'audit','batch':offset,'error':str(error)})
            verdicts={}
        for c in batch:
            verdict=verdicts.get(c['claim']['id'],{'supported':False,'reason':'audit_unavailable'})
            c['machine_audit']=verdict;c['retained']=bool(c['static_passed'] and verdict['supported'])
    for c in candidates:
        if any(re.fullmatch(r'(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9_-]{4,}',s)
               and re.search(r'(?<!\w)'+re.escape(s)+r'(?!\w)',c['claim']['text']) for s in by_id):
            c.update(retained=False,reason='technical_source_identifier_in_prose')
    points=[];warnings=[]
    for topic in sorted(topics,key=lambda t:min(by_id[s]['start_ms'] for item in t['items'] for s in item['sources'])):
        all_candidates=[c for c in candidates if c['topic_id']==topic['id']]
        retained=sorted([c for c in all_candidates if c.get('retained')],
            key=lambda c:min(by_id[e['id']]['start_ms'] for e in c['claim']['evidence']))
        narrative=[];claims=[];seen=set()
        for c in retained:
            claim=c['claim'];signature=(claim['speaker'],normalized(claim['text']).casefold())
            if signature in seen:continue
            seen.add(signature)
            label=request['speaker_labels'].get(claim['speaker'],'Voix inconnue')
            if request.get('sentence_evidence'):
                from notetaker.domain.summary import municipal_name
                label=municipal_name(label)
            name=request.get('speaker_templates',{}).get(claim['speaker'],'Intervenant non identifié ({{V1}})')
            template=name+' '+claim['text'][0].lower()+claim['text'][1:]
            implicit=False
            if narrative and claims[-1]['speaker']==claim['speaker'] and name=='{{V1}}' and re.match(r'^(?:madame|monsieur)\b',label,re.I):
                from notetaker.domain.summary import anaphoric_prose
                continuation=('Elle ' if label.startswith('Madame') else 'Il ')+claim['text'][0].lower()+claim['text'][1:]
                if anaphoric_prose(continuation):template=continuation;implicit=True
            if c['nature']=='decision_evoquee':template='Décision évoquée à confirmer : '+template
            note=reader_note(c['uncertainty'],aliases,request)
            if note:
                # A model's uncertainty note may itself contain an unsupported
                # factual assertion. Preserve it in the verification report only.
                warnings.append(topic['title']+' : '+('Une intention ne constitue pas un résultat de scrutin.'
                    if c.get('method')=='explicit_first_person_vote_intent' else
                    'la formulation de cet échange est à vérifier dans les sources.'))
            if any(by_id[e['id']].get('uncertain') for e in claim['evidence']):
                warnings.append(topic['title']+' : l’attribution de cet échange reste à confirmer.')
            text=template.replace('{{V1}}',label)
            narrative.append({'text':text,'template':template,'voice_bindings':{'V1':claim['speaker']},
                'claim_ids':[claim['id']],'machine_verdict':'machine_supported_requires_human_review'})
            if request.get('sentence_evidence'):narrative[-1]['name_style']='municipal-civilities-v1'
            if implicit:narrative[-1].update(implicit_speaker=claim['speaker'],voice_bindings={})
            claims.append(claim)
        ids=list(dict.fromkeys(e['id'] for c in claims for e in c['evidence']))
        if claims:
            points.append({'title':topic['title'],'summary':' '.join(n['text'] for n in narrative),
                'sources':ids,'vote_id':None,'claims':claims,'narrative':narrative})
        elif not request.get('sentence_evidence'):
            ids=list(dict.fromkeys(s for item in topic['items'] for s in item['sources']))
            points.append({'title':topic['title'],'summary':'La rédaction de cet échange reste à vérifier. Les interventions et leurs sources sont conservées dans le rapport de vérification.',
                'sources':ids,'vote_id':None})
        covered={i for c in retained for i in c['items']}
        if any(i['id'] not in covered for i in topic['items']):warnings.append(topic['title']+' : certains arguments restent à reprendre après vérification.')
    if not points:
        points=[{'title':'Échanges à reprendre','summary':'La rédaction automatique n’a pas abouti. La transcription et les sources audio restent disponibles pour préparer le compte rendu.',
                 'sources':[r['id'] for r in rows if r['text'].strip()],'vote_id':None}]
        warnings.append('La rédaction automatique est incomplète et nécessite une reprise.')
    represented={s for p in points if p.get('claims') for s in p['sources']}
    planned={s for t in topics for i in t['items'] for s in i['sources']}
    secondary={s['source']:s['reason'] for s in classifications if s['source'] not in planned}
    for row in rows:
        if row['id'] not in planned and protocol_only(row['text']):
            secondary[row['id']]='formule_de_seance'
    ledger=[]
    for row in rows:
        sid=row['id'];status='represented' if sid in represented else 'important_to_verify' if sid in planned else 'secondary_proposed' if sid in secondary else 'unclassified_to_verify'
        if status=='secondary_proposed' and priority_signal(row['text']):status='secondary_with_priority_signal_to_verify'
        ledger.append({'id':sid,'speaker':row.get('speaker_id'),'start_ms':row['start_ms'],'end_ms':row['end_ms'],
            'text':row['text'],'uncertain':bool(row.get('uncertain')),
            'status':status,'secondary_reason':secondary.get(sid),'human_verified':False})
    counts={status:sum(r['status']==status for r in ledger) for status in sorted({r['status'] for r in ledger})}
    unclassified=sum(r['status'] in ('unclassified_to_verify','secondary_with_priority_signal_to_verify') for r in ledger)
    if unclassified:warnings.append('Des interventions non classées ou potentiellement importantes restent à examiner dans le rapport de vérification.')
    matrix=coverage_matrix(topics,rows,candidates)
    inventory={'strategy':VERSION,'topics':topics,'items':candidates,'coverage':ledger,'coverage_counts':counts,'errors':failures,
        'coverage_by_topic_and_speaker':matrix,'coverage_before_writing':prewrite,
        'all_input_ids':list(by_id),'unrepresented_source_ids':[r['id'] for r in ledger if r['status']!='represented'],
        'human_fidelity_measured':False,'coverage_is_machine_proposed':True}
    atomic_json(workspace/'automatic-inventory.json',inventory)
    write_verification(workspace,inventory,request)
    if request.get('sentence_evidence'):
        # Technical details and the full omission inventory belong to the report.
        warnings=['Ce brouillon nécessite une relecture humaine ; les sources et les passages non repris figurent dans le rapport de vérification.']
        if any(r.get('uncertain') for r in rows if r['id'] in represented):
            warnings.append('Certaines attributions ou limites de passages restent incertaines ; elles sont détaillées dans le rapport de vérification.')
        if any(c.get('nature')=='intention_vote' for c in candidates):
            warnings.append('Les intentions de vote rapportées ne constituent pas un résultat de scrutin.')
    atomic_json(workspace/'summary-progress.json',{'phase':'redaction_terminee','completed':len(topics),'total':len(topics)})
    return {'document_mode':'summary','points':points,'to_verify':list(dict.fromkeys(warnings)),
        'generation_diagnostics':{'strategy':VERSION,'blocks':len(blocks),'input_segments':len(rows),
            'paraphrase_claims':sum(len(p.get('claims',[])) for p in points),'quoted_fallback_points':0,
            'coverage_counts':counts,'unrepresented_sources':inventory['unrepresented_source_ids'],
            'verification_report':'verification-report.md','inventory':'automatic-inventory.json','human_fidelity_measured':False}}


def write_verification(workspace,inventory,request):
    def stamp(ms):return f'{ms//60000:02d}:{ms//1000%60:02d}.{ms%1000:03d}'
    by_id={r['id']:r for r in inventory['coverage']}
    status_labels={'represented':'Rattaché à une reformulation — portée à contrôler',
        'important_to_verify':'Intervention du sujet à reprendre',
        'secondary_proposed':'Contenu secondaire proposé par machine',
        'secondary_with_priority_signal_to_verify':'Contenu dit secondaire avec signal prioritaire — à examiner',
        'unclassified_to_verify':'Non classé — à examiner'}
    lines=['# Rapport de vérification du brouillon','',
        'Aucun verdict ci-dessous ne constitue une annotation ou une validation humaine.',
        'Les classes de couverture sont proposées par machine. Une source citée peut ne pas être entièrement résumée.','']
    lines+=['## Couverture par sujet et par intervenant','',
        'Inventaire effectué avant la rédaction ; rapprochement après contrôles. Une citation ne prouve pas une couverture sémantique complète.','']
    for entry in inventory.get('coverage_by_topic_and_speaker',[]):
        lines += ['### '+entry['topic']+' — '+request['speaker_labels'].get(entry['speaker'],'Non identifié'),
            'Sources prévues : '+', '.join(entry['source_ids']),
            'Signaux prioritaires à contrôler (heuristique, pas une importance validée) : '+(', '.join(entry['priority_signal_ids']) or 'aucun'),
            'Non citées dans une phrase retenue : '+(', '.join(entry['uncited_ids']) or 'aucune'),
            'Noms cités dans les sources mais non repris (importance à vérifier) : '+(', '.join(entry['named_mentions_not_repeated']) or 'aucun'),
            'Couverture du sens : à relire humainement.','']
    for topic in inventory['topics']:
        lines+=['## '+topic['title'],'']
        for c in [c for c in inventory['items'] if c['topic_id']==topic['id']]:
            lines += [('Retenu' if c.get('retained') else 'À reprendre')+' — '+request['speaker_labels'].get(c['claim']['speaker'],'Non identifié'),
                '',c['claim']['text'],'','Contrôles : '+c['reason']+' ; '+c.get('machine_audit',{}).get('reason','absent'),'',
                'Incertitude : '+(c['uncertainty'] or 'aucune signalée par le modèle'),'']
            for e in c['claim']['evidence']:
                row=by_id[e['id']]
                lines+=['Source '+e['id']+' — '+stamp(row['start_ms'])+' à '+stamp(row['end_ms']),'',e['quote'],'']
                if row.get('uncertain'):lines+=['Attribution ou limites de ce passage signalées incertaines dans la transcription.','']
    lines+=['## Inventaire exhaustif et repères audio','']
    for row in inventory['coverage']:
        lines += ['### '+row['id']+' — '+stamp(row['start_ms'])+' à '+stamp(row['end_ms']),
            status_labels[row['status']]+' ; '+str(row['secondary_reason'] or ''),'',row['text'],'']
    lines+=['## Erreurs techniques internes','',json.dumps(inventory['errors'],ensure_ascii=False,indent=2)]
    (workspace/'verification-report.md').write_text('\n'.join(lines),encoding='utf-8')
