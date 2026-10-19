"""Topic dossiers, contextual entailment checks and source-bound prose.

Every machine verdict remains provisional. Raw quotes, rejected output and
omissions stay in the private job; neither this module nor its caller approves.
"""
import json
import re
from pathlib import Path
from .hierarchical_summary import (call_json,object_schema,source_units,coherent_blocks,
    resolve_evidence,grounded_claim,verification_context,validate_grouping,VERIFY_INSTRUCTION)
from notetaker.domain.summary import PROFILES,TOKEN,validate_lexicon,anaphoric_prose
from notetaker.infrastructure.atomic import atomic_json

VERDICTS=['supported','contradicted','not_explicit','uncertain']
DISCOURSES=['own','question','reported','anecdote']
KINDS=['position','argument','proposal','context','question']


def model_aliases(request,value):
    voices=list(dict.fromkeys(u.get('speaker_id') or 'unattributed' for u in request.get('utterances',[])))
    aliases={key:f'V{i+1}' for i,key in enumerate(voices)}
    def visit(item):
        if isinstance(item,list):return [visit(v) for v in item]
        if isinstance(item,dict):
            return {key:(aliases.get(v,v) if key in {'speaker','speaker_id','implicit_speaker'} and isinstance(v,str) else
                {a:aliases.get(b,b) for a,b in v.items()} if key=='voice_bindings' else visit(v)) for key,v in item.items()}
        return item
    return visit(value)


def semantic_context(claim,utterances):
    raw=verification_context(claim,utterances,budget=1000)
    groups=[]
    for row in raw['turns']:
        if groups and row['speaker']!='unattributed' and groups[-1]['speaker']==row['speaker'] and 0<=row['start_ms']-groups[-1]['end_ms']<=1500:
            groups[-1]['text']+=' '+row['text'];groups[-1]['ids'].append(row['id']);groups[-1]['end_ms']=row['end_ms']
        else:groups.append({'ids':[row['id']],'speaker':row['speaker'],'start_ms':row['start_ms'],'end_ms':row['end_ms'],'text':row['text']})
    return {'turns':groups,'truncated':raw['truncated']}


def role_problem(text,quotes):
    source=' '.join(quotes)
    if (re.search(r'\bministres?\b',source,re.I) and re.search(r'\bils\s+ne\s+nous\s+écoutent\s+pas\b',source,re.I)
        and re.search(r'\bministres?\b(?:(?![.!?]|\b(?:étudiants|élèves|nous|jeunes|agents)\b).){0,150}?\bne\s+(?:sont|seraient)\s+pas\s+(?:entendus|écoutés)\b',text,re.I)):
        return 'listener_actor_changed_to_patient'
    return None


def discourse_problem(kind,discourse,text,quotes):
    source=' '.join(quotes)
    if (re.search(r"\b(?:jamais|pas)\s+(?:été\s+)?oppos\w*|\bpas\s+contre\b",source,re.I)
        and re.search(r"\b(?:favorable\w*|en faveur|soutien\w*|approuv\w*|adh[èé]r\w*)\b",text,re.I)):
        return 'absence_of_opposition_changed_to_support'
    if (discourse=='question' or kind=='question') and not re.search(r'\?|\b(?:interrog\w*|question\w*|demand\w*|souhaite savoir)\b',text,re.I):
        return 'question_changed_to_assertion'
    if all(q.rstrip().endswith('?') for q in quotes) and kind!='question':return 'question_changed_to_assertion'
    reported=bool(re.search(r"\b(?:vous (?:dites|pensez|estimez|affirmez)|selon (?:vous|lui|elle)|ils (?:disent|envoient)|elle affirme|il affirme)\b",source,re.I))
    if (reported or discourse=='reported') and not re.search(r'\b(?:rapport\w*|cit\w*|attribu\w*|contest\w*|critiqu\w*|évoqu\w*|interrog\w*|question\w*|demand\w*|dénonc\w*|décrit|raconte|récit|témoign\w*)\b',text,re.I):
        return 'reported_opinion_assigned_to_reporting_voice'
    if kind=='proposal' and not re.search(r"\b(?:propos\w*|demand\w*|souhait\w*|il faut|faudrait|devrait|recommand\w*|je voudrais|nous voudrions|j['’]aimerais|il conviendrait)\b",source,re.I):
        return 'anecdote_or_description_changed_to_proposal'
    return None


def check_id_set(items,expected):
    ids=[item['id'] for item in items]
    if set(ids)!=set(expected) or len(ids)!=len(set(ids)):raise ValueError('SUMMARY_INVALID_ID_SET')


def distinct_claims(claims):
    result=[];seen=set()
    for c in claims:
        key=(c['speaker'],c['kind'],tuple((e['id'],e['quote']) for e in c['evidence']), ' '.join(c['text'].split()).casefold())
        if key not in seen:result.append(c);seen.add(key)
    return result


def verify(request,label,items,narrative=False):
    """Separate machine opinions on meaning, modality, attribution and relation."""
    items=model_aliases(request,items)
    if len(json.dumps(items,ensure_ascii=False))>16000 and len(items)>1:
        result={}
        for index,item in enumerate(items):result.update(verify(request,f'{label}-{index}',[item],narrative=narrative))
        return result
    check=object_schema({field:{'type':'string','enum':VERDICTS} for field in ['meaning','modality','attribution','relation']})
    schema=object_schema({'checks':object_schema({item['id']:check for item in items})})
    response=call_json(request,label,VERIFY_INSTRUCTION+
        " Tu n'as pas accès à la vérité extérieure au débat. Vérifie le soutien de la source, pas sa véracité politique. "
        "Les preuves factuelles sont quote et source_text des seuls IDs cités. Le contexte voisin sert à détecter contradictions, "
        "modalité et auteur ; il ne justifie aucun détail supplémentaire, même provenant de la même voix. "
        "Renseigne quatre contrôles indépendants : meaning (chaque détail), modality (question, hypothèse, vécu ou fait), "
        "attribution (auteur de l'avis, personne qui le rapporte ou le critique), relation (accord, désaccord, proposition). "
        "Une question doit rester une question rapportée, même si elle contient une accusation. "
        "Citer ou critiquer l'avis d'autrui n'exprime pas cet avis en son nom. Un récit personnel ne prouve pas un fait général. "
        "Une expérience ou un constat ne devient pas une recommandation officielle. Deux opinions voisines ne prouvent pas un accord explicite. "
        "Les conclusions et titres ne doivent pas convertir une allégation en fait établi. "
        "Pour un heading nominal neutre désignant seulement l'objet évoqué, modality/attribution/relation sont supported si le titre n'ajoute aucune thèse. "
        "Le lexique corrige seulement une graphie fournie par l'opérateur, jamais l'identité d'une voix. "
        "Au moindre doute, uncertain ; aucune inférence d'intention ou d'appartenance politique. supported exige les quatre axes étayés."+
        (" Pour une phrase de paragraphe, contrôle aussi ses liaisons avec les autres phrases du paragraph_context_for_relation_only. "
         "Une reprise 'cette affirmation' doit désigner exactement la position sourcée à laquelle elle renvoie. "
         "Des propos éloignés sur des objets différents ne deviennent pas une réponse, une contestation ou un accord. "
         "Les horaires sont ceux des extraits ; une simple proximité dans le paragraphe n'est aucune preuve de dialogue. "
         "Le paragraphe donne seulement le contexte des relations, jamais une nouvelle preuve factuelle. "
         "Une relation non étayée impose not_explicit même si chaque citation prise seule existe." if narrative else ''),
        {'items':items,'lexicon':request.get('lexicon',[])},schema,tokens=1400)
    checks=response['checks']
    if set(checks)!={i['id'] for i in items}:raise ValueError('SUMMARY_INVALID_ID_SET')
    return checks


def verify_heading(request,label,title,claims,by_id,utterances):
    """A nominal heading has no speaker assertion; verify its actual risks."""
    fields=['topic_supported','no_unsupported_assertion','no_invented_identity_or_decision']
    schema=object_schema({'checks':object_schema({k:{'type':'string','enum':VERDICTS} for k in fields})})
    result=call_json(request,label,
        "Vérifie uniquement le TITRE nominal d'un sujet, contre ses citations originales. "
        "topic_supported : tous les objets, précisions, chiffres et lieux du titre sont étayés. "
        "no_unsupported_assertion : le titre désigne un objet discuté, sans transformer accusation, opinion, "
        "question ou vécu personnel en fait établi, sans ajouter de causalité ou consensus. "
        "no_invented_identity_or_decision : aucune identité, affiliation, décision ou vote n'est inventé. "
        "Un titre nominal n'attribue pas lui-même une phrase à une voix ; les phrases sont contrôlées séparément. "
        "Une proposition explicitement formulée peut être nommée proposition ; elle ne devient pas une décision. "
        "Chaque contrôle vaut supported seulement si ces exigences sont satisfaites ; sinon contradicted, "
        "not_explicit ou uncertain. Une citation exacte ne suffit jamais à justifier un titre plus général.",
        {'title':title,'source_notes':model_aliases(request,[claim_payload(c,by_id,utterances) for c in claims])},
        schema,tokens=400)
    checks=result['checks'].copy()
    checks['source_identity_guard']='not_explicit' if identity_problem(title,claims,request.get('lexicon',[])) else 'supported'
    return checks


def claim_payload(claim,by_id,utterances,context=True):
    refs=[]
    for e in claim['evidence']:
        u=by_id[e['id']]
        refs.append({'id':u['id'],'speaker':u.get('speaker_id') or 'unattributed',
            'quote':e['quote'],'source_text':u['text'][:900], 'truncated':len(u['text'])>900})
    result={'id':claim['id'],'kind':claim['kind'],'discourse':claim['discourse'],
        'speaker':claim['speaker'],'claim':claim['text'],'sources':refs}
    if context:result['nearby_context']=semantic_context(claim,utterances)
    return result


def classify_notes(request,notes,by_id,label):
    """Classify original speech separately from the indirect prose we will write."""
    genres={'position':'position','argument':'argument','proposition':'proposal','description':'context','question':'question'}
    origins={'propos_direct_du_locuteur':'own','question_posee_par_le_locuteur':'question',
        'avis_d_autrui_cite_ou_critique':'reported','recit_personnel_du_locuteur':'anecdote'}
    def item(claim):
        quote=' '.join(e['quote'] for e in claim['evidence']).strip()
        question=quote.endswith('?') or bool(re.match(r"(?:pourquoi|comment|est[- ]ce|qu['’]est[- ]ce)\b",quote,re.I))
        proposal=bool(re.search(r"\b(?:propos\w*|demand\w*|souhait\w*|il faut|faudrait|devrait|recommand\w*|je voudrais|nous voudrions|j['’]aimerais|il conviendrait)\b",quote,re.I))
        allowed=['question'] if question else [k for k in genres if k!='proposition' or proposal]
        if not question and re.match(r'^(?:je suis|nous sommes)\s+(?:opposé|opposés|favorable|favorables)',quote,re.I):allowed.remove('question')
        return object_schema({'genre':{'type':'string','enum':allowed},'origine':{'type':'string','enum':['question_posee_par_le_locuteur'] if question else list(origins)}})
    result=call_json(request,label,
        "Classe UNIQUEMENT les PROPOS ORIGINAUX cités. Ne rédige pas le compte rendu. "
        "Le futur style indirect du résumé ne change JAMAIS l'origine du propos. "
        "propos_direct_du_locuteur = il exprime lui-même description, position, argument ou recommandation ; "
        "question_posee_par_le_locuteur = il pose une interrogation ; "
        "avis_d_autrui_cite_ou_critique = il rapporte ou critique explicitement l'avis d'une autre personne ; "
        "recit_personnel_du_locuteur = il raconte son expérience passée, sans généraliser. "
        "Le genre question exige une interrogation réelle, pas une objection. Le genre proposition exige une action future recommandée. "
        "Exemples : 'Je suis opposé à ce calendrier car la salle doit rester ouverte' = argument/propos_direct_du_locuteur. "
        "'Je propose de reporter les travaux' = proposition/propos_direct_du_locuteur. "
        "'Vous dites que les travaux sont nécessaires, pourquoi ?' = question/question_posee_par_le_locuteur. "
        "'Quand j’étais élève, je prenais ce bus' = description/recit_personnel_du_locuteur. "
        "Ne confonds pas un VOUS générique ('quand vous êtes étudiant') avec une citation de l'avis d'autrui. "
        "Aucune étiquette n'autorise un fait absent des sources. Chaque clé est obligatoire.",
        model_aliases(request,[{'id':c['id'],'speaker':c['speaker'],
            'sources':claim_payload(c,by_id,request['utterances'],context=False)['sources'],
            'nearby_context':semantic_context(c,request['utterances'])} for c in notes]),
        object_schema({'classifications':object_schema({c['id']:item(c) for c in notes})}),tokens=900)
    if set(result['classifications'])!={c['id'] for c in notes}:raise ValueError('SUMMARY_INVALID_ID_SET')
    return {key:{'kind':genres[v['genre']],'discourse':origins[v['origine']]} for key,v in result['classifications'].items()}


def rephrase_notes(request,notes,by_id,label):
    schema=object_schema({'notes':object_schema({c['id']:{'type':'string','minLength':10,'maxLength':350} for c in notes})})
    result=call_json(request,label,
        "Rédige une note française indirecte de 15 à 35 mots par clé, depuis les seules citations jointes et la nature du propos fournie. "
        "La nature du propos original est fournie ; le style indirect ne signifie pas que l'avis venait d'autrui. "
        "question = 'La personne demande si/pourquoi…', sans affirmer le présupposé de la question. "
        "reported = 'La personne rapporte/interroge/critique l'avis…', sans lui attribuer l'avis cité. "
        "anecdote = 'Un témoignage personnel décrit…', sans fait général ni recommandation ajoutée. "
        "own = description, avis ou argument explicitement avancé par le locuteur ; le situer comme tel. "
        "Reformule avec tes propres mots, aucun je/nous/vous, aucune longue copie. "
        "Le contexte a servi à classifier le propos. Ici les extraits joints sont les seules preuves : aucun détail d'un contexte absent, ni fait emprunté à une autre voix. "
        "Une phrase comme 'Vous venez de ce milieu' évoque l'interlocuteur, pas l'origine personnelle du locuteur. N'invente pas son identité. "
        "Garde négations, hypothèses, portée des chiffres et réserves. Aucun détail, cause, affiliation politique, décision ou résultat de vote ajouté. "
        "Un budget global ne devient pas celui d'une partie des travaux. Ne complète pas une phrase mal transcrite. "
        "Chaque clé est obligatoire ; ne fusionne pas les auteurs.",
        model_aliases(request,[{'id':c['id'],'speaker':c['speaker'],'kind':c['kind'],'discourse':c['discourse'],
            'citations':[e['quote'] for e in c['evidence']]} for c in notes]),schema,tokens=1600)
    if set(result['notes'])!={c['id'] for c in notes}:raise ValueError('SUMMARY_INVALID_ID_SET')
    return result['notes']


def extract(request):
    utterances=request['utterances'];units=source_units(utterances)
    by_unit={u['id']:u for u in units};by_id={u['id']:u for u in utterances}
    # Four-minute context preserves complete exchanges while bounding CPU calls;
    # the independent 8,000-character limit still bounds the model prompt.
    claims=[];rejected=[];blocks=list(coherent_blocks(units,max_seconds=240))
    for index,block in enumerate(blocks):
        atomic_json(Path(request['workspace'])/'summary-progress.json',{'phase':'topic_arguments','completed':index,'total':len(blocks)})
        ids=list(dict.fromkeys(u['id'] for u in block))
        item=object_schema({'topic':{'type':'string','minLength':3,'maxLength':80},
            'speaker':{'type':'string','enum':sorted({u['speaker'] for u in block})},
            'kind':{'type':'string','enum':KINDS},'discourse':{'type':'string','enum':DISCOURSES},
            'text':{'type':'string','minLength':10,'maxLength':350},
            'evidence':{'type':'array','minItems':1,'maxItems':3,'items':object_schema({
                'id':{'type':'string','enum':ids},'quote':{'type':'string','minLength':10,'maxLength':350}})}})
        response=call_json(request,f'arguments-{index:03d}',
            "Repère les sujets et arguments substantiels de toutes les voix dans ce bloc. Au plus six notes distinctes, "
            "sans remplir un quota. Une note reste attachée à UNE voix et à ses citations exactes. "
            "Conserve motif, objection, réserve, négation et portée des chiffres. Garde les interventions du début ET de la fin. "
            "text est une reformulation française indirecte de la note, pas une longue copie de la transcription ; les extraits exacts restent uniquement dans evidence.quote. "
            "Identifie discourse : own (avis exprimé), question (interrogation), reported (avis cité/rapporté/critiqué), "
            "anecdote (expérience personnelle, pas fait général). Dans text, rapporte explicitement les questions, avis cités et anecdotes. "
            "Une question accusatrice ne prouve pas l'accusation ; un journaliste ne reprend pas à son compte ce qu'il reformule. "
            "Une anecdote n'est jamais une proposition de politique publique. proposal exige une recommandation explicite. "
            "Les accusations, descriptions contestées et positions politiques restent des propos attribués, jamais des faits établis. "
            "topic est un groupe nominal neutre décrivant l'objet, pas la thèse d'une personne. "
            "Les citations reprennent mot pour mot des extraits continus de 10 à 35 mots : pas de citation abrégée ni de guillemets ajoutés. "
            "Ne crée aucun résultat de scrutin, décision ou identité. Écarte salutations et répétitions.",
            {'segments':block},object_schema({'claims':{'type':'array','maxItems':6,'items':item}}),tokens=2600)
        preliminary=[]
        for candidate in response['claims']:
            resolved=resolve_evidence(candidate,[by_unit[i] for i in ids])
            if resolved is None:rejected.append({'claim':candidate,'reason':'no_unique_exact_quote_for_speaker'});continue
            good,reason=grounded_claim(resolved,utterances,require_paraphrase=False)
            if not good:rejected.append({'claim':resolved,'reason':reason});continue
            resolved['id']=f'c{index}-{len(preliminary)}';preliminary.append(resolved)
        if not preliminary:continue
        # Classifying original speech is a separate task from writing indirect prose.
        atomic_json(Path(request['workspace'])/'summary-progress.json',{'phase':'source_classification','completed':index,'total':len(blocks)})
        classified=classify_notes(request,preliminary,by_id,f'source-classify-{index:03d}')
        for resolved in preliminary:resolved.update(classified[resolved['id']])
        atomic_json(Path(request['workspace'])/'summary-progress.json',{'phase':'source_rewrite','completed':index,'total':len(blocks)})
        rewritten=rephrase_notes(request,preliminary,by_id,f'argument-rephrase-{index:03d}')
        for resolved in preliminary:
            resolved['text']=rewritten[resolved['id']]
            good,reason=grounded_claim(resolved,utterances)
            reason=discourse_problem(resolved['kind'],resolved['discourse'],resolved['text'],[e['quote'] for e in resolved['evidence']]) or (None if good else reason)
            if reason:rejected.append({'claim':resolved,'reason':reason});continue
            # IDs can be sparse after rejection; never reuse an already accepted ID.
            claims.append(resolved)
        atomic_json(Path(request['workspace'])/'argument-audit.json',{'claims':claims,'rejected':rejected,'completed_blocks':index+1})
    supported=[]
    for offset in range(0,len(claims),4):
        atomic_json(Path(request['workspace'])/'summary-progress.json',{'phase':'argument_entailment','completed':offset,'total':len(claims)})
        batch=claims[offset:offset+4]
        checks=verify(request,f'argument-check-{offset:03d}',[claim_payload(c,by_id,utterances) for c in batch])
        for c in batch:
            guard=(financial_clause_problem(c['text'],[c]) or absence_problem(c['text'],[c]) or
                identity_problem(c['text'],[c],request.get('lexicon',[])))
            if guard:rejected.append({'claim':c,'reason':guard,'checks':checks[c['id']]})
            elif all(v=='supported' for v in checks[c['id']].values()):
                c['machine_verdict']='supported_not_human_verified';supported.append(c)
            else:rejected.append({'claim':c,'reason':'contextual_entailment_rejected','checks':checks[c['id']]})
        atomic_json(Path(request['workspace'])/'argument-audit.json',{'claims':claims,'supported':supported,'rejected':rejected})
    unique=distinct_claims(supported)
    if not unique:raise ValueError('NO_SUPPORTED_SUMMARY_CLAIMS')
    return unique,rejected,len(blocks)


def group_topics(request,claims):
    # Preliminary note titles are deliberately absent: otherwise the field model
    # copied one title per note instead of finding shared objects of discussion.
    compact=[{k:c[k] for k in ['id','kind','speaker','text']} for c in claims]
    if len(json.dumps(compact,ensure_ascii=False))>20000:raise ValueError('SUMMARY_CONTEXT_BUDGET_EXCEEDED')
    catalogue=call_json(request,'theme-catalogue',
        "Définis seulement le plan thématique d'un compte rendu, sans rédiger les paragraphes ni classer les IDs. "
        "Trouve les objets communs du débat. Les coûts, le calendrier, les objections et les mesures d'accompagnement "
        "d'un même projet sont des facettes d'un même sujet, pas quatre sujets. "
        "Un argument, une anecdote ou une voix n'est pas à lui seul un nouveau thème. "
        "Regroupe les passages éloignés qui discutent le même objet, en gardant les vraies différences de sujet. "
        "Peu de sujets cohérents, sans en créer pour remplir un quota. Les titres sont des groupes nominaux neutres "
        "tirés exclusivement des notes, sans transformer une accusation en fait, sans consensus ni décision déduite.",
        model_aliases(request,compact),object_schema({'themes':{'type':'array','minItems':1,'maxItems':8,
            'items':object_schema({'title':{'type':'string','minLength':3,'maxLength':100}})}}),tokens=700)
    themes=catalogue['themes']
    routing=call_json(request,'theme-routing',
        "Affecte chaque note à UN sujet du plan. Toutes les clés sont obligatoires. Rassemble dans le même sujet "
        "les arguments, réserves et propositions sur le même objet, même s'ils viennent de voix différentes "
        "ou de moments éloignés. Le classement thématique n'affirme aucun accord entre les voix. "
        "Aucun ajout de fait, aucune réécriture des notes ou des titres.",
        {'themes':[{'id':f't{i}','title':t['title']} for i,t in enumerate(themes)],'notes':model_aliases(request,compact)},
        object_schema({'assignments':object_schema({c['id']:{'type':'string','enum':[f't{i}' for i in range(len(themes))]} for c in claims})}),tokens=1500)
    grouped=[{'title':t['title'],'claims':[c['id'] for c in claims if routing['assignments'][c['id']]==f't{i}']} for i,t in enumerate(themes)]
    grouped=[t for t in grouped if t['claims']]
    validate_grouping({'topics':grouped},[c['id'] for c in claims])
    atomic_json(Path(request['workspace'])/'theme-plan-audit.json',{'catalogue':catalogue,'routing':routing,'topics':grouped})
    return grouped,False


def identity_problem(text,claims,lexicon=()):
    source=' '.join(e['quote'] for c in claims for e in c['evidence']).casefold()
    words=lambda s:set(re.findall(r'[\wÀ-ÿ-]+',s.casefold()))
    allowed=words(source)
    for entry in lexicon:
        if any(variant.casefold() in source for variant in [entry['canonical'],*entry.get('variants',[])]):allowed.update(words(entry['canonical']))
    plain=TOKEN.sub('la personne',text)
    for match in re.finditer(r'\b(?:[A-ZÀ-ÖØ-Ý][a-zà-öø-ÿ-]{2,}|[A-Z]{2,})\b',plain):
        if match.start()>0 and match[0].casefold() not in allowed:return 'unsupported_proper_name'
    for match in re.finditer(r'\bparti\s+(?:politique\s+)?([\wÀ-ÿ-]+)',plain,re.I):
        if match[1].casefold() not in allowed:return 'unsupported_political_identity'
    return None


def absence_problem(text,claims):
    source=' '.join(e['quote'] for c in claims for e in c['evidence']).casefold()
    for stem in ['affirm','évalu','précis','détaill','expliqu','chiffr','évoqu']:
        if re.search(r'\bsans\s+'+stem+r'\w*',text,re.I) and stem not in source:return 'unsupported_absence_added'
    return None


def unresolved_referent(claim):
    quotes=[e['quote'].strip() for e in claim['evidence']]
    return (any(re.search(r'\bcette prétention[.!?]?$',q,re.I) for q in quotes)
        and sum(len(q.split()) for q in quotes)<20
        and all(len(q.split())<=8 for q in quotes))


def financial_clause_problem(text,claims):
    """Conservative guard after a real Qwen false positive on budget scope.

    A financial amount must be a literal source clause in guillemets. This is
    additional to semantic verification, not a claim that a quote proves prose.
    """
    money=re.compile(r'€|\b(?:euros?|EUR)\b',re.I)
    if not money.search(text):return None
    normalize=lambda s:' '.join(s.strip().strip('.!?').split()).casefold()
    clauses=[]
    for claim in claims:
        for evidence in claim['evidence']:
            clauses.extend(normalize(c) for c in re.split(r'(?<=[.!?])\s+',evidence['quote']) if money.search(c))
    quoted=re.findall(r'«([^»]+)»',text)
    if money.search(re.sub(r'«[^»]+»','',text)) or not quoted:return 'financial_scope_requires_literal_source'
    if any(money.search(q) and normalize(q) not in clauses for q in quoted):return 'financial_scope_requires_literal_source'
    return None


def quotation_problem(text,claims):
    normalize=lambda s:' '.join(s.split()).casefold()
    # A reformulation may be indirect prose, never a fabricated direct quote.
    quotes=[e['quote'] for c in claims for e in c['evidence']]
    source=normalize(' '.join(quotes))
    if any(normalize(q) not in source for q in re.findall(r'«([^»]+)»',text)):
        return 'narrative_quotation_not_exact'
    return None


def repair_role(request,claim,by_id,utterances):
    """One independently checked repair of an observed actor/patient inversion.

    This late dossier check preserves the existing topic plan and source IDs.
    Rejected original machine prose remains in the private audit, never silently
    promoted into the point's claims. A failed repair omits the note.
    """
    old=claim['text'];quotes=[e['quote'] for e in claim['evidence']]
    problem=role_problem(old,quotes)
    if not problem:return True
    label='argument-role-repair-'+claim['id']
    result=call_json(request,label,
        "Corrige uniquement la reformulation à partir des citations originales. Style indirect français, "
        "sans guillemets et sans ajout de fait. Respecte qui accomplit et qui subit chaque action. "
        "Ne pas écouter quelqu'un ne signifie pas ne pas être écouté. Conserve l'accusation comme propos "
        "attribué au locuteur ; n'en fais pas une vérité établie. Aucun nom ou résultat de vote ajouté.",
        model_aliases(request,{'rejected_rewrite':old,'problem':problem,'speaker':claim['speaker'],'citations':quotes}),
        object_schema({'text':{'type':'string','minLength':15,'maxLength':350}}),tokens=500)
    candidate={**claim,'text':result['text']}
    guard=(role_problem(candidate['text'],quotes) or discourse_problem(candidate['kind'],candidate['discourse'],candidate['text'],quotes)
        or financial_clause_problem(candidate['text'],[candidate]) or absence_problem(candidate['text'],[candidate])
        or quotation_problem(candidate['text'],[candidate]) or identity_problem(candidate['text'],[candidate],request.get('lexicon',[])))
    checks={} if guard else verify(request,label+'-check',[claim_payload(candidate,by_id,utterances)])
    accepted=not guard and all(v=='supported' for v in checks[claim['id']].values())
    atomic_json(Path(request['workspace'])/(label+'-audit.json'),{'original':old,'candidate':candidate['text'],
        'problem':problem,'guard':guard,'checks':checks,'accepted':accepted,'evidence':claim['evidence']})
    if accepted:claim['text']=candidate['text']
    return accepted


def sentence_problem(sentence,claims,aliases,previous_voices=None,lexicon=()):
    selected=[claims[cid] for cid in sentence['claim_ids']]
    if len(sentence['claim_ids'])!=len(set(sentence['claim_ids'])):return 'duplicated_narrative_claim'
    voices={c['speaker'] for c in selected}
    mentioned=set(TOKEN.findall(sentence['text']))
    if re.search(r'\bEXACT\b|<\|',sentence['text']):return 'narrative_instruction_artifact'
    financial=financial_clause_problem(sentence['text'],selected)
    if financial:return financial
    absence=absence_problem(sentence['text'],selected)
    if absence:return absence
    quotation=quotation_problem(sentence['text'],selected)
    if quotation:return quotation
    role=role_problem(sentence['text'],[e['quote'] for c in selected for e in c['evidence']])
    if role:return role
    identity=identity_problem(sentence['text'],selected,lexicon)
    if identity:return identity
    if len(voices)==1 and all(c['kind']=='question' for c in selected) and re.search(r'\b(?:affirmant|assurant|soutenant|et\s+(?:affirme|assure|soutient))\b',sentence['text'],re.I):return 'question_changed_to_assertion'
    if '{{' in TOKEN.sub('',sentence['text']) or '}}' in TOKEN.sub('',sentence['text']):return 'unknown_voice_placeholder'
    if not mentioned<=set(aliases) or not {aliases[v] for v in mentioned}<=voices:return 'unsupported_narrative_identity'
    # Every assertion is explicitly attributed; no allégation becomes a narrator fact.
    if not mentioned and not (len(voices)==1 and voices==previous_voices and anaphoric_prose(sentence['text'])):return 'unattributed_narrative_assertion'
    agreement=sentence.get('relation')=='agreement' or bool(re.search(r"\b(?:consensus|s['’]accordent|accord entre|position commune)\b",sentence['text'],re.I))
    disagreement=sentence.get('relation')=='disagreement' or bool(re.search(r"\b(?:désaccord entre|divergence entre|s['’]opposent)\b",sentence['text'],re.I))
    disagreement=disagreement or bool(re.search(r"\b(?:conteste|réfute|rejette|contredit|critique)\s+(?:cette|cet|ces|ce)\s+(?:affirmation|propos|position|argument|idée|avis)",sentence['text'],re.I))
    if (agreement or disagreement) and len(voices)<2:return 'relation_needs_distinct_voices'
    if agreement and not any(re.search(r"\b(?:d'accord|je partage|nous partageons|même avis|je vous rejoins)\b",e['quote'],re.I) for c in selected for e in c['evidence']):return 'consensus_not_explicit'
    for c in selected:
        reason=discourse_problem(c['kind'],c['discourse'],sentence['text'],[e['quote'] for e in c['evidence']])
        if reason:return reason
    if re.search(r'\b(?:adopté|approuvé|unanimité|décision prise)\b',sentence['text'],re.I):return 'vote_or_decision_in_narrative'
    return None


def write_topic(request,topic,claims,index):
    utterances=request['utterances'];by_id={u['id']:u for u in utterances}
    original={c['id']:c for c in claims if c['id'] in topic['claims']}
    forced_omissions=[{'id':cid,'reason':'unresolved_source_referent'} for cid,c in original.items() if unresolved_referent(c)]
    selected={cid:c for cid,c in original.items() if not unresolved_referent(c)}
    failed=[cid for cid,c in selected.items() if not repair_role(request,c,by_id,utterances)]
    forced_omissions.extend({'id':cid,'reason':'actor_patient_inversion_unrepaired'} for cid in failed)
    selected={cid:c for cid,c in selected.items() if cid not in failed}
    if not selected:return {'title':topic['title'],'claims':[],'sentences':[],'omitted':forced_omissions,'rejected_attempts':[]}
    voices={c['speaker'] for c in selected.values()}
    all_voices=list(dict.fromkeys(u.get('speaker_id') or 'unattributed' for u in utterances))
    aliases={f'V{all_voices.index(v)+1}':v for v in all_voices if v in voices}
    reverse={v:a for a,v in aliases.items()}
    profile=PROFILES[request.get('summary_length','standard')]
    dossier=[]
    for c in selected.values():
        row=claim_payload(c,by_id,utterances,context=False)
        row['voice_alias']='{{'+reverse[c['speaker']]+'}}'
        dossier.append(row)
    views=[{'voice_alias':'{{'+alias+'}}','notes':[c for c in dossier if c['speaker']==speaker]} for alias,speaker in aliases.items()]
    schema=object_schema({'title':{'type':'string','minLength':3,'maxLength':100},'sentences':{'type':'array','minItems':1,'maxItems':min(profile['sentences'],len(selected)),
        'items':object_schema({'text':{'type':'string','minLength':15,'maxLength':1000},
            'claim_ids':{'type':'array','minItems':1,'maxItems':3,'items':{'type':'string','enum':list(selected)}}})}})
    rejected=[]
    for attempt in range(2):
        result=call_json(request,f'topic-{index:02d}-write-{attempt}',
            "Rédige UN paragraphe français cohérent de compte rendu sur le sujet, en phrases qui s'enchaînent. "
            "title est un intitulé nominal neutre, sans transformer une accusation ou une opinion en fait établi. "
            "Ne produis ni liste d'étiquettes Argument/Position, ni tour de table, ni succession de mini-résumés. "
            "Présente l'objet de l'échange à travers les voix, puis articule leurs raisons, objections et propositions sans inventer de liaison causale. "
            "Signale un désaccord seulement si les sources le soutiennent ; ne déduis aucun accord de positions voisines. "
            "La première phrase nomme sa voix par l'alias fourni, écrit {{V1}}, {{V2}}, etc. "
            "Une phrase suivante peut reprendre cette MÊME voix par un verbe de parole ou une anaphore claire ('Cette proposition…'), "
            "si ses notes renvoient à cette seule voix. Tout changement de voix exige son alias. "
            "Ne remplace jamais ces alias par un nom, une fonction, un parti ou une identité supposée. "
            "Les questions restent interrogations rapportées. Une opinion citée ou critiquée n'est pas l'avis du locuteur qui la rapporte. "
            "Les anecdotes restent récits personnels attribués. Une accusation n'est jamais présentée comme un fait établi. "
            "Les propositions sont des recommandations explicites, pas des décisions, votes ou intentions déduites. "
            "Chaque phrase référence les notes qui la soutiennent ; cite uniquement les notes effectivement exprimées par cette phrase. "
            "Réunis les notes complémentaires d'une voix dans une formulation articulée au lieu de répéter son nom pour chaque note. "
            "La présence d'une citation ne suffit pas : chaque détail, attribution et relation doivent découler des sources. "
            "Conserve l'objet des quantités et dates : un ensemble ne devient pas une partie, un nombre de personnes ne devient pas un nombre d'établissements. "
            "Ne complète pas un fragment mal transcrit. N'utilise pas une note trop douteuse. "
            f"Au plus environ {profile['words_per_topic']} mots pour ce paragraphe. S'il y a peu d'informations, écris moins. Ne remplis jamais un quota. "
            "Sélectionne les éléments essentiels sans effacer systématiquement une voix ni un désaccord. "
            "Les notes non utilisées seront comptabilisées automatiquement ; ne crée pas de champ d'omissions. "
            "Le lexique autorise seulement les graphies fournies, jamais une nouvelle identité. Aucun fait nouveau dans les transitions.",
            {'topic':topic['title'],'views':model_aliases(request,views),'lexicon':request.get('lexicon',[]),'previous_rejection':rejected[-1:],
             **({'explicit_relations':request['registry_relations']} if 'registry_relations' in request else {})},
            schema,tokens=2500)
        if 'registry_relations' in request:
            # A reviewed registry subject is not silently renamed by the prose stage.
            result['title']=topic['title']
        if '{{' in result['title'] or '}}' in result['title']:
            rejected.append({'reason':'heading_contains_voice_placeholder',
                'corrective_action':'Rédiger un intitulé nominal du sujet, sans alias de voix ni nom de personne.'});continue
        for sentence in result['sentences']:
            refs=[selected[cid] for cid in sentence['claim_ids']]
            kinds={c['kind'] for c in refs};discourses={c['discourse'] for c in refs}
            sentence['relation']=(next(iter(discourses)) if len(discourses)==1 and next(iter(discourses)) in {'question','reported','anecdote'} else
                next(iter(kinds)) if len(kinds)==1 else 'source_bound_prose')
        used={cid for s in result['sentences'] for cid in s['claim_ids']}
        if not used<=set(selected):raise ValueError('SUMMARY_INVALID_ID_SET')
        omitted=forced_omissions+[{'id':cid,'reason':'not_selected_in_paragraph'} for cid in selected if cid not in used]
        problems=[];previous=set()
        for s in result['sentences']:
            voices={selected[cid]['speaker'] for cid in s['claim_ids']}
            reason=sentence_problem(s,selected,aliases,previous,request.get('lexicon',[]))
            if reason:
                problem={'sentence':s,'reason':reason}
                if reason=='financial_scope_requires_literal_source':
                    problem['corrective_action']='Retirer le montant, ou reprendre entre guillemets français la phrase financière exacte de la citation, sans la rattacher à un autre objet. Les autres détails restent à vérifier.'
                if reason=='narrative_quotation_not_exact':
                    problem['corrective_action']='Une citation entre guillemets doit reprendre exactement la source. Retirer les guillemets pour une reformulation fidèle, ou recopier un extrait exact ; ne modifier ni les rôles ni la modalité.'
                if reason=='listener_actor_changed_to_patient':
                    problem['corrective_action']='La source reproche aux ministres de ne pas écouter les personnes ; elle ne dit pas que les ministres ne sont pas écoutés. Respecter qui accomplit et qui subit l’action.'
                problems.append(problem)
            elif not TOKEN.findall(s['text']):s['implicit_speaker']=next(iter(voices))
            previous=voices
        if problems:rejected.append({'reason':'narrative_guard','problems':problems});continue
        heading_checks=verify_heading(request,f'topic-{index:02d}-heading-{attempt}',result['title'],list(selected.values()),by_id,utterances)
        if any(v!='supported' for v in heading_checks.values()):
            rejected.append({'reason':'heading_entailment_rejected','checks':heading_checks});continue
        items=[]
        for j,s in enumerate(result['sentences']):
            refs=[selected[cid] for cid in s['claim_ids']]
            sources=[claim_payload(c,by_id,utterances) for c in refs]
            for note in sources:
                for e in note['sources']:e.update(start_ms=by_id[e['id']]['start_ms'],end_ms=by_id[e['id']]['end_ms'])
            items.append({'id':f'n{j}','sentence':s['text'],'relation':s['relation'],'voice_bindings':aliases,
                'paragraph_context_for_relation_only':[{'text':row['text'],'claim_ids':row['claim_ids']} for row in result['sentences']],
                'implicit_speaker':s.get('implicit_speaker'),
                'previous_sentence_for_anaphora_only':result['sentences'][j-1]['text'] if j and s.get('implicit_speaker') else None,
                'source_notes':sources})
        checks=verify(request,f'topic-{index:02d}-check-{attempt}',items,narrative=True)
        bad={key:value for key,value in checks.items() if any(v!='supported' for v in value.values())}
        if bad:rejected.append({'reason':'narrative_entailment_rejected','checks':bad});continue
        return {'title':result['title'],'claims':[cid for cid in selected if cid in used],
            'sentences':[{**s,'voice_bindings':{a:v for a,v in aliases.items() if a in TOKEN.findall(s['text'])},
                'machine_verdict':'supported_not_human_verified'} for s in result['sentences']],
            'omitted':omitted,'rejected_attempts':rejected}
    return {'title':topic['title'],'claims':[],'sentences':[],'omitted':forced_omissions+[{'id':cid,'reason':'not_reliable_enough'} for cid in selected],
        'rejected_attempts':rejected}


def summarize(request):
    if request.get('summary_length','standard') not in PROFILES:raise ValueError('INVALID_SUMMARY_LENGTH')
    validate_lexicon(request.get('lexicon',[]))
    if not request['utterances']:raise ValueError('TRANSCRIPT_REQUIRED')
    if any('\ufffd' in u['text'] for u in request['utterances']):raise ValueError('DAMAGED_TRANSCRIPT_RETRANSCRIBE_ORIGINAL')
    claims,rejected,blocks=extract(request)
    topics,repaired=group_topics(request,claims)
    written=[]
    for index,topic in enumerate(topics):
        atomic_json(Path(request['workspace'])/'summary-progress.json',{'phase':'topic_prose','completed':index,'total':len(topics)})
        written.append(write_topic(request,topic,claims,index))
        atomic_json(Path(request['workspace'])/'topic-writing-audit.json',written)
    accepted=[t for t in written if t['sentences']]
    atomic_json(Path(request['workspace'])/'summary-audit.json',{'claims':claims,'rejected':rejected,'topics':written})
    if not accepted:raise ValueError('NO_SUPPORTED_TOPIC_PARAGRAPHS')
    # Expose actual time coordinates for review, not just a count of refusals.
    units={u['id']:u for u in source_units(request['utterances'])}
    by_id={u['id']:u for u in request['utterances']}
    flagged={}
    for rejection in rejected:
        for e in rejection.get('claim',{}).get('evidence',[]):
            ids=[e['id']] if e['id'] in by_id else [s['id'] for s in units.get(e['id'],{}).get('source_spans',[])]
            for sid in ids:flagged.setdefault(sid,set()).add('information_rejected')
    by_claim={c['id']:c for c in claims}
    for topic in written:
        for omission in topic['omitted']:
            reason='note_not_selected' if omission['reason']=='not_selected_in_paragraph' else 'information_rejected'
            for e in by_claim[omission['id']]['evidence']:flagged.setdefault(e['id'],set()).add(reason)
    for u in request['utterances']:
        if u.get('uncertain',True):flagged.setdefault(u['id'],set()).add('voice_or_timing_uncertain')
    unreliable=[{'source_id':sid,'start_ms':by_id[sid]['start_ms'],'end_ms':by_id[sid]['end_ms'],
        'reasons':sorted(reasons)} for sid,reasons in flagged.items()]
    unreliable.sort(key=lambda u:(u['start_ms'],u['source_id']))
    return {'strategy':'contextual-topic-paragraphs-v1','topics':accepted,'claims':claims,'device':'cpu',
        'diagnostics':{'blocks':blocks,'supported_claims':len(claims),'rejected_claims':len(rejected),
            'topic_assignment_repair':repaired,'topics_not_written':[t['title'] for t in written if not t['sentences']],
            'omitted_claims':sum(len(t['omitted']) for t in written),
            'unreliable_passages':unreliable,
            'summary_length':request.get('summary_length','standard'),
            'human_factual_validation':'required_not_performed','machine_verification':'meaning_modality_attribution_relation_not_a_human_reference'}}
