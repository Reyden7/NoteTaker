"""Local summary options and reversible, source-bound narrative rendering."""
import copy
import json
import re

PROFILES = {
    'short': {'label':'Courte', 'words_per_topic':65, 'sentences':4},
    'standard': {'label':'Standard', 'words_per_topic':120, 'sentences':7},
    'detailed': {'label':'Détaillée', 'words_per_topic':200, 'sentences':11},
}
TOKEN = re.compile(r'\{\{(V\d+)\}\}')


def anaphoric_prose(text):
    return bool(re.match(r"^(?:(?:Il|Elle|La personne|Cette voix|Cette personne|Ce locuteur|Ce dernier|Cette dernière)\s+(?:ajoute|rappelle|affirme|estime|propose|demande|conteste|précise|souligne|explique|rapporte|critique|insiste|exprime|observe|souhaite|récuse)\b|(?:Ce|Cet|Cette)\s+(?:propos|projet|avis|point|récit|témoignage|argument|proposition|opinion|affirmation|demande)\b)",text))


def lexicon_from_text(text):
    entries=[]
    for line in text.splitlines():
        if not line.strip():continue
        parts=[p.strip() for p in line.split('|')]
        if not parts[0] or len(parts)>2:raise ValueError('Lexique : utilisez « forme retenue | variantes séparées par ; » par ligne.')
        entries.append({'canonical':parts[0], 'variants':[p.strip() for p in parts[1].split(';') if p.strip()] if len(parts)>1 else []})
    validate_lexicon(entries)
    return entries


def validate_lexicon(entries):
    if not isinstance(entries,list) or len(entries)>60:raise ValueError('Le lexique doit contenir au plus 60 entrées.')
    seen=set()
    for entry in entries:
        canonical=entry.get('canonical','')
        variants=entry.get('variants',[])
        if not isinstance(canonical,str) or not canonical.strip() or not isinstance(variants,list):raise ValueError('Une entrée du lexique est incomplète.')
        for term in [canonical,*variants]:
            if not isinstance(term,str) or not term.strip() or len(term)>120 or any(c in term for c in '\n\r{}<>'):
                raise ValueError('Chaque forme du lexique doit être un texte simple de 1 à 120 caractères.')
            if term.casefold() in seen:raise ValueError('Une forme du lexique est répétée ou ambiguë : '+term)
            seen.add(term.casefold())
    if len(json.dumps(entries,ensure_ascii=False))>5000:raise ValueError('Raccourcissez le lexique à 5 000 caractères pour cette séance.')


def lexicon_text(entries):
    return '\n'.join(e['canonical']+(' | '+' ; '.join(e.get('variants',[])) if e.get('variants') else '') for e in entries)


def voice_registry(state):
    result={}
    for row in state['utterances']:
        key=row.get('speaker_id') or 'unattributed'
        if key in result:continue
        name=state['speakers'].get(key,'')
        # Only operator-assigned labels can become a printed identity. Anonymous
        # aliases are still used in prompts, even when a name is confirmed.
        anonymous=re.fullmatch(r'(?:Intervenant|Voix)\s+(\d+)',name)
        confirmed=bool(name and not anonymous)
        alias=f'V{len(result)+1}'
        result[key]={'alias':alias, 'label':name if confirmed else ('Voix inconnue' if key=='unattributed' else 'Voix '+(anonymous[1] if anonymous else str(len(result)+1))), 'confirmed':confirmed}
    return result


def render_template(template,bindings,state):
    registry=voice_registry(state)
    def substitute(match):
        key=bindings.get(match[1])
        if key not in registry:raise ValueError('NARRATIVE_UNKNOWN_VOICE')
        return registry[key]['label']
    rendered=TOKEN.sub(substitute,template)
    if '{{' in rendered or '}}' in rendered:raise ValueError('NARRATIVE_UNKNOWN_VOICE')
    return rendered


def narrative_problems(point,state):
    if 'narrative' not in point:return []
    rows=point['narrative'];claims={c['id']:c for c in point.get('claims',[])}
    if not rows or ' '.join(r['text'] for r in rows)!=point['summary']:return ['narrative_text_changed']
    used=set();problems=[];previous_voices=set()
    for row in rows:
        ids=row.get('claim_ids',[])
        if not ids or not set(ids)<=set(claims):problems.append('narrative_missing_claim');continue
        used.update(ids)
        voices={claims[i]['speaker'] for i in ids}
        if 'template' in row:
            bindings=row.get('voice_bindings',{})
            if not set(TOKEN.findall(row['template']))<=set(bindings):problems.append('narrative_voice_changed');continue
            if not set(bindings.values())<={claims[i]['speaker'] for i in ids}:problems.append('narrative_voice_changed');continue
            if not TOKEN.findall(row['template']):
                implicit=row.get('implicit_speaker')
                if not implicit or voices!={implicit} or previous_voices!={implicit} or not anaphoric_prose(row['template']):problems.append('narrative_voice_changed')
            try:
                if render_template(row['template'],bindings,state)!=row['text']:problems.append('narrative_voice_changed')
            except ValueError:problems.append('narrative_voice_changed')
        previous_voices=voices
    if used!=set(claims):problems.append('narrative_missing_claim')
    return list(dict.fromkeys(problems))


def manual_narrative(point,text):
    """An explicit prose edit retains all links and loses its machine verdict."""
    point['summary']=text
    point['narrative']=[{'text':text,'claim_ids':[c['id'] for c in point.get('claims',[])],
        'machine_verdict':'human_edited_requires_review'}]


def refresh_narrative(point,old,state):
    if 'narrative' not in point or old['summary']!=' '.join(r['text'] for r in old['narrative']):return False
    before={c['id']:c for c in old.get('claims',[])}
    after={c['id']:c for c in point.get('claims',[])}
    changed=False
    for row in point['narrative']:
        if 'template' not in row:continue
        moves={}
        for cid in row['claim_ids']:
            if cid in before and cid in after:moves.setdefault(before[cid]['speaker'],set()).add(after[cid]['speaker'])
        bindings=copy.deepcopy(row['voice_bindings'])
        if any(len(moves.get(key,{key}))!=1 for key in bindings.values()):continue
        implicit=row.get('implicit_speaker')
        if implicit and len(moves.get(implicit,{implicit}))!=1:continue
        bindings={a:next(iter(moves.get(key,{key}))) for a,key in bindings.items()}
        try:text=render_template(row['template'],bindings,state)
        except ValueError:continue
        updated_implicit=next(iter(moves.get(implicit,{implicit}))) if implicit else None
        if text!=row['text'] or bindings!=row['voice_bindings'] or implicit!=updated_implicit:
            row.update(text=text,voice_bindings=bindings,machine_verdict='attribution_changed_human_review_required');changed=True
            if implicit:row['implicit_speaker']=updated_implicit
    if changed:point['summary']=' '.join(r['text'] for r in point['narrative'])
    return changed
