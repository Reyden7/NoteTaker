"""Read-only boundary diagnostics and an explicit, partial DER evaluation mask."""
from .core import tokens,review_valid
from .normalization import normalize,numeric_prefixes
from .wer_plan import merge,subtract,overlaps,approved,token_view


def qualified_activity(project,plan=None):
    """Only reviewed named activity and explicitly heard silence. No gap filling."""
    h=project['audio']['sha256'];zones=[];excluded=[];basis=[]
    for z in project['zones']:
        if not review_valid(z,'diarization',h) or z['unintelligible']:continue
        ranges=[(t['start'],t['end']) for t in z['turns']]
        if z['silence']:
            ranges.append((z['start'],z['end']));basis.append({'zone':z['id'],'kind':'whole_zone_explicit_silence'})
        for b in (plan or {}).get('blocks',[]):
            if b['zone']==z['id'] and approved(b) and b['classification']=='silence':
                ranges.append((b['start'],b['end']));basis.append({'zone':z['id'],'portion':b['id'],'kind':'explicit_heard_silence','approval':b['approval']})
        covered=merge(ranges)
        for i,(a,b) in enumerate(covered):
            turns=[{**t,'start':max(a,t['start']),'end':min(b,t['end'])} for t in z['turns'] if min(b,t['end'])>max(a,t['start'])]
            zones.append({'id':z['id']+f'-Q{i+1:02d}','source_zone':z['id'],'start':a,'end':b,'turns':turns})
        for a,b in subtract([(z['start'],z['end'])],covered):
            excluded.append({'zone':z['id'],'start':a,'end':b,'seconds':b-a,'reason':'Activité ou identités non annotées ; aucune absence de voix supposée.'})
    return zones,excluded,basis


def summarize_wer(rows):
    keys=('reference_words','hypothesis_words','equal','substitute','delete','insert')
    result={k:sum(row[k] for row in rows) for k in keys}
    result['errors']=result['substitute']+result['delete']+result['insert']
    result['WER']=result['errors']/result['reference_words'] if result['reference_words'] else None
    return result


def aggregate_by_zone(rows):
    return [{'id':zone,**summarize_wer([r for r in rows if r['source_zone']==zone])}
            for zone in sorted({r['source_zone'] for r in rows})]


def selected_raw(project,part):
    z=next(z for z in project['zones'] if z['id']==part['source_zone'])
    a,b=part['reference_token_range'];view,spans=token_view(z['verbatim'])
    if a==b:return ''
    start=spans[a][0];previous=spans[a-1][1] if a else 0
    if view[previous:start].strip() in ('-','−','+'):start=previous
    return view[start:spans[b-1][1]]


def compare_baseline(report,baseline):
    """Never describe a change in annotation selection as a change in accuracy."""
    same_reference=report['reference_sha256']==baseline['reference_sha256']
    same_audio=report['audio_sha256']==baseline['audio_sha256']
    old={b['id']:b for b in (baseline.get('wer_plan') or {}).get('blocks',[])}
    new={b['id']:b for b in (report.get('wer_plan') or {}).get('blocks',[])}
    changes=[]
    for identifier in sorted(set(old)|set(new)):
        a,b=old.get(identifier,{}),new.get(identifier,{})
        fields={k:{'before':a.get(k),'after':b.get(k)} for k in ('start','end','first_token','last_token','classification') if a.get(k)!=b.get(k)}
        if fields:changes.append({'id':identifier,'fields':fields})
    return {'same_reference':same_reference,'same_audio':same_audio,'portion_changes':changes,
        'same_scoring_selection':same_reference and same_audio and not changes,
        'historical_rates':{k:{'WER':r['transcription']['WER'],'N':r['transcription']['reference_words'],'DER':r['diarization']['DER']} for k,r in baseline['results'].items()},
        'strict_historical_reproduced':{k:report['results'][k]['transcription']['WER']==r['transcription']['WER'] for k,r in baseline['results'].items()},
        'historical_DER_reproduced':{k:report['results'][k]['diarization']['DER']==r['diarization']['DER'] for k,r in baseline['results'].items()}}


def audit_boundaries(project,dataset,units,plan=None):
    from .scoring import lexical_clock,words_in_zone,edit_alignment
    zones={z['id']:z for z in project['zones']};clocks={k:lexical_clock(c['asr']) for k,c in dataset['chains'].items()}
    # Contextual lexical alignments are model-derived clues, never new annotations.
    mappings={}
    for zid in {u['source_zone'] for u in units}:
        z=zones[zid];refnorm=normalize(tokens(z['verbatim']),numeric_prefixes(z['verbatim']))
        for k,clock in clocks.items():
            context,missing=words_in_zone(clock,z);hn=normalize([w['text'] for w in context],{i:w['numeric_prefix'] for i,w in enumerate(context) if w.get('numeric_prefix')});pairs=[]
            for op,i,j in edit_alignment(refnorm['tokens'],hn['tokens'])['operations']:
                if op!='equal':continue
                for ri in refnorm['provenance'][i]['source_indices']:
                    for hi in hn['provenance'][j]['source_indices']:
                        w=context[hi]
                        if w['start'] is not None:pairs.append((ri,w))
            mappings[zid,k]=pairs
    audits=[]
    for u in units:
        z=zones[u['source_zone']];first,last=u['reference_token_range'];ref=tokens(z['verbatim']);engines={}
        for k,clock in clocks.items():
            selected,_=words_in_zone(clock,u)
            inside_not_selected={};selected_outside={}
            for i,w in mappings[z['id'],k]:
                midpoint=(w['start']+w['end'])/2;inside=u['start']<=midpoint<u['end']
                if inside and not first<=i<last:inside_not_selected.setdefault(i,[]).append(w)
                if not inside and first<=i<last:selected_outside.setdefault(i,[]).append(w)
            crossing=[]
            for w in clock:
                if w['start'] is None:continue
                for side,t in (('start',u['start']),('end',u['end'])):
                    if w['start']<t<w['end']:
                        crossing.append({'side':side,'boundary':t,'word':w['text'],'start':w['start'],'end':w['end'],
                                         'midpoint_in_portion':u['start']<=(w['start']+w['end'])/2<u['end']})
            engines[k]={'hypothesis_words':len(selected),'words':[dict(w) for w in selected],
                'matching_unselected_human_tokens_inside':[{'index':i,'text':ref[i],'engine_times':ws} for i,ws in sorted(inside_not_selected.items())],
                'matching_selected_human_tokens_outside':[{'index':i,'text':ref[i],'engine_times':ws} for i,ws in sorted(selected_outside.items())],
                'words_crossing_boundaries':crossing}
        alerts=[]
        independent=[k for k in ('small','large') if k in engines]
        if any(engines[k]['matching_unselected_human_tokens_inside'] for k in independent):alerts.append('mots_humains_non_selectionnes_dans_bornes_selon_alignement_assiste')
        if any(engines[k]['matching_selected_human_tokens_outside'] for k in independent):alerts.append('mots_selectionnes_localises_hors_bornes_selon_alignement_assiste')
        if any(engines[k]['words_crossing_boundaries'] for k in independent):alerts.append('mot_moteur_traversant_frontiere')
        overlap=sum(b-a for a,b in merge((max(u['start'],a),min(u['end'],b)) for a,b in overlaps(z)))
        audits.append({'id':u['id'],'zone':z['id'],'start':u['start'],'end':u['end'],'reference_token_range':[first,last],
            'reference_words':last-first,'reference_text':selected_raw(project,u),'alerts':alerts,'engines':engines,
            'real_overlap_seconds_in_portion':overlap,
            'diagnostic_status':'indices textuels à vérifier à l’écoute ; aucun rattachement modifié ni approuvé'})
    gaps=[]
    for zid in sorted({u['source_zone'] for u in units}):
        ref=tokens(zones[zid]['verbatim']);selected={i for u in units if u['source_zone']==zid for i in range(*u['reference_token_range'])}
        start=None
        for i in range(len(ref)+1):
            if i<len(ref) and i not in selected:
                if start is None:start=i
            elif start is not None:
                gaps.append({'zone':zid,'first_token':start,'last_token':i,'words':i-start,'text':' '.join(ref[start:i]),
                    'reason':'Non retenu dans les portions WER ; peut appartenir à un chevauchement ou révéler une omission de sélection.'});start=None
    return {'portions':audits,'unselected_reference_runs':gaps,
        'method':'Alignement lexical contextuel déterministe avec provenance, sur sorties existantes. Small et Large sont deux indices ; WhisperX réutilise Large et ne constitue pas une troisième confirmation.',
        'no_acoustic_human_verification_by_agent':True,'no_automatic_reference_change':True}
