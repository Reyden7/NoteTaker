"""WER, DER and word-clock diagnostics, ONLY over explicitly reviewed zones.

DER uses the installed pyannote.metrics in the isolated benchmark environment.
No model is loaded. No output of an engine is ever promoted to a human reference.
"""
import argparse
import json
import math
import os
from pathlib import Path
from .core import (tokens,review_valid,validate_project,load_dataset,read,digest,utc,DOMAINS)


def edit_alignment(reference,hypothesis):
    """Unit-cost Levenshtein; returns auditable substitutions/deletions/insertions."""
    n,m=len(reference),len(hypothesis)
    dp=[[0]*(m+1) for _ in range(n+1)]
    for i in range(n+1):dp[i][0]=i
    for j in range(m+1):dp[0][j]=j
    for i in range(1,n+1):
        for j in range(1,m+1):
            dp[i][j]=min(dp[i-1][j-1]+(reference[i-1]!=hypothesis[j-1]),dp[i-1][j]+1,dp[i][j-1]+1)
    operations=[];i,j=n,m
    while i or j:
        if i and j and dp[i][j]==dp[i-1][j-1]+(reference[i-1]!=hypothesis[j-1]):
            operations.append(('equal' if reference[i-1]==hypothesis[j-1] else 'substitute',i-1,j-1));i-=1;j-=1
        elif i and dp[i][j]==dp[i-1][j]+1:operations.append(('delete',i-1,None));i-=1
        else:operations.append(('insert',None,j-1));j-=1
    operations.reverse()
    counts={name:sum(o[0]==name for o in operations) for name in ('equal','substitute','delete','insert')}
    return {'reference_words':n,'hypothesis_words':m,**counts,'operations':operations,
            'WER':(counts['substitute']+counts['delete']+counts['insert'])/n if n else None}


def lexical_clock(segments,*,combined=False):
    """Preserve every lexical token; missing/ambiguous timings stay None."""
    output=[]
    for segment in segments:
        pieces=segment.get('source',{}).get('word_spans',[]) if combined else segment.get('words',[])
        merged=[]
        for piece in pieces or []:
            text=piece['word'].strip()
            if merged and (merged[-1]['word'].rstrip().endswith(("'",'’')) or text.startswith(("'",'’'))):
                previous=merged[-1];previous['word']+=text
                previous['end']=piece.get('end') if previous.get('start') is not None else None
            else:merged.append(dict(piece,word=text))
        candidate=[]
        for p in merged:
            for word in tokens(p['word']):
                start,end=p.get('start'),p.get('end')
                valid=all(isinstance(x,(int,float)) and math.isfinite(x) for x in (start,end)) and end>=start
                candidate.append({'text':word,'start':start if valid else None,'end':end if valid else None})
        expected=tokens(segment['text'])
        if [w['text'] for w in candidate]!=expected:
            candidate=[{'text':word,'start':None,'end':None} for word in expected]
        from .normalization import numeric_prefixes
        prefixes=numeric_prefixes(segment['text'])
        for index,word in enumerate(candidate):
            output.append({**word,'segment_start':segment['start'],'segment_end':segment['end'],
                           'speaker':segment.get('speaker'),'numeric_prefix':prefixes.get(index)})
    return output


def words_in_zone(words,zone):
    selected=[];missing_boundary=False
    for word in words:
        if word['segment_end']<=zone['start'] or word['segment_start']>=zone['end']:continue
        if word['start'] is None:
            if word['segment_start']>=zone['start'] and word['segment_end']<=zone['end']:selected.append(word)
            else:missing_boundary=True
        elif zone['start']<=(word['start']+word['end'])/2<zone['end']:selected.append(word)
    return selected,missing_boundary


def has_overlap(zone):
    from .wer_plan import overlaps
    return bool(overlaps(zone))


def annotation(rows,uri):
    from pyannote.core import Annotation,Segment
    value=Annotation(uri=uri)
    for i,row in enumerate(rows):
        if row.get('speaker') is not None and row['end']>row['start']:
            value[Segment(row['start'],row['end']),str(i)]=str(row['speaker'])
    return value.support()


def diarization_scores(zones,rows):
    from pyannote.core import Segment,Timeline
    from pyannote.metrics.diarization import DiarizationErrorRate
    from pyannote.metrics.identification import IdentificationErrorRate
    if not zones:return {'DER':None,'reason':'Aucune zone avec activité et identités vocales revues humainement.','zones':[],'mapping':{}}
    reference=annotation([t for z in zones for t in z['turns']],'human')
    hypothesis=annotation(rows,'candidate')
    uem=Timeline([Segment(z['start'],z['end']) for z in zones])
    metric=DiarizationErrorRate(collar=0.0,skip_overlap=False)
    details=metric(reference,hypothesis,uem=uem,detailed=True)
    mapping=metric.optimal_mapping(reference,hypothesis,uem=uem)
    total=float(details['total'])
    parts={k:float(details[k]) for k in ('total','confusion','missed detection','false alarm','correct')}
    # Same optimal mapping across ALL reviewed portions of this recording.
    # Never independently permute labels per 40-second excerpt.
    mapped=hypothesis.rename_labels(mapping={k:mapping.get(k,'unmapped::'+k) for k in hypothesis.labels()})
    per_zone=[]
    for z in zones:
        d=IdentificationErrorRate(collar=0,skip_overlap=False)(reference,mapped,uem=Timeline([Segment(z['start'],z['end'])]),detailed=True)
        p={k:float(d[k]) for k in ('total','confusion','missed detection','false alarm','correct')}
        per_zone.append({'id':z['id'],**p,'DER':(p['confusion']+p['missed detection']+p['false alarm'])/p['total'] if p['total'] else None})
    return {'DER':(parts['confusion']+parts['missed detection']+parts['false alarm'])/total if total else None,
            **parts,'uem':[[z['start'],z['end']] for z in zones],'zones':per_zone,
            'mapping':{str(k):str(v) for k,v in mapping.items()},'collar_seconds':0.0,'include_overlap':True,
            'mapping_scope':'one global Hungarian mapping on all DER-reviewed zones of this recording',
            'total_unit':'human speaker-seconds; overlapping voices count separately'}


def mean(values):return sum(values)/len(values) if values else None


def clock_scores(zones,chain,mapping,display_mode):
    clocks=lexical_clock(chain['clock']);assigned=lexical_clock(chain[display_mode],combined=True)
    starts=[];ends=[];timely100=timely250=reference_count=correct_tokens=timed=0
    attr_total=attr_wrong=unassigned=0;examples=[]
    for z in zones:
        if has_overlap(z):continue
        reference=z['words'];reference_count+=len(reference)
        clock,_=words_in_zone(clocks,z);labels,_=words_in_zone(assigned,z)
        align=edit_alignment([tokens(w['text'])[0] for w in reference],[w['text'] for w in clock])
        for op,i,j in align['operations']:
            if op!='equal':continue
            correct_tokens+=1;r,h=reference[i],clock[j]
            if h['start'] is None:continue
            timed+=1;ds=abs(h['start']-r['start']);de=abs(h['end']-r['end']);starts.append(ds);ends.append(de)
            timely100+=ds<=0.1+1e-9 and de<=0.1+1e-9;timely250+=ds<=0.25+1e-9 and de<=0.25+1e-9
            examples.append({'zone':z['id'],'word':r['text'],'human_start':r['start'],'human_end':r['end'],
                             'hypothesis_start':h['start'],'hypothesis_end':h['end'],'start_absolute_error':ds,'end_absolute_error':de})
        # Conditional attribution error for lexically correct words. No identity inference.
        alignment=edit_alignment([tokens(w['text'])[0] for w in reference],[w['text'] for w in labels])
        for op,i,j in alignment['operations']:
            if op!='equal':continue
            attr_total+=1;speaker=labels[j]['speaker'];mapped=mapping.get(speaker)
            if speaker is None or mapped is None:unassigned+=1
            if mapped!=reference[i]['speaker']:attr_wrong+=1
    return {'reference_words':reference_count,'lexically_correct_words':correct_tokens,'matched_words_with_times':timed,
        'mean_start_absolute_error_seconds':mean(starts),'mean_end_absolute_error_seconds':mean(ends),
        'both_boundaries_within_100ms_fraction_of_reference':timely100/reference_count if reference_count else None,
        'both_boundaries_within_250ms_fraction_of_reference':timely250/reference_count if reference_count else None,
        'conditional_attribution_errors':attr_wrong,'conditional_attribution_words':attr_total,
        'conditional_attribution_error_rate':attr_wrong/attr_total if attr_total else None,
        'unassigned_or_unmapped_correct_words':unassigned,'examples':examples,
        'scope':'Only human-reviewed individual words in non-overlap zones; lexical substitutions/deletions reported separately by WER.',
        'missing_hypothesis_timings_are_not_fabricated':True,'display_assignment_variant':display_mode}


def evaluate(project,dataset,display_mode='exclusive',wer_plan=None):
    validate_project(project)
    audio_hash=project['audio']['sha256'];results={};scope=[]
    text_zones=[z for z in project['zones'] if review_valid(z,'text',audio_hash) and not z['unintelligible']]
    diar_zones=[z for z in project['zones'] if review_valid(z,'diarization',audio_hash) and not z['unintelligible']]
    word_zones=[z for z in project['zones'] if all(review_valid(z,d,audio_hash) for d in ('text','diarization','word_times'))]
    from .wer_plan import wer_units
    wer_eligible,scope,coverage_diagnostics,proposals=wer_units(project,dataset,wer_plan)
    from .normalization import normalize,numeric_prefixes,VERSION,RULES
    from .audit_metrics import qualified_activity,summarize_wer,aggregate_by_zone,selected_raw,audit_boundaries
    qualified_zones,unknown_activity,activity_basis=qualified_activity(project,wer_plan)
    # Only the SAME explicitly reviewed sequential portions for all candidates.
    # ASR word clocks are reused, never human word-by-word timings.
    asr_clocks={key:lexical_clock(chain['asr']) for key,chain in dataset['chains'].items()}
    for key,chain in dataset['chains'].items():
        counts={k:0 for k in ('reference_words','hypothesis_words','equal','substitute','delete','insert')};per_zone=[];normalized_rows=[]
        for z in wer_eligible:
            words,_=words_in_zone(asr_clocks[key],z);ref=tokens(z['verbatim']);hyp=[w['text'] for w in words]
            detail=edit_alignment(ref,hyp)
            for field in counts:counts[field]+=detail[field]
            per_zone.append({'id':z['id'],'source_zone':z['source_zone'],'start':z['start'],'end':z['end'],**detail,'reference':ref,'hypothesis':hyp,
                             'reference_token_range':z['reference_token_range'],'portion_review':z['portion_review'],
                             'tags':z['tags'],'hypotheses_seen_before_review':z['reviews']['text']['hypotheses_seen_before_review']})
            nr=normalize(ref,numeric_prefixes(selected_raw(project,z)))
            nh=normalize(hyp,{i:w['numeric_prefix'] for i,w in enumerate(words) if w.get('numeric_prefix')})
            normalized_rows.append({'id':z['id'],'source_zone':z['source_zone'],'start':z['start'],'end':z['end'],
                **edit_alignment(nr['tokens'],nh['tokens']),'reference':nr['tokens'],'hypothesis':nh['tokens'],
                'reference_normalization':nr,'hypothesis_normalization':nh})
        der=diarization_scores(diar_zones,chain['diarization'])
        qualified_der=diarization_scores(qualified_zones,chain['diarization'])
        qualified_der.update(scope='partial_explicit_human_activity_only',excluded_unknown_activity=unknown_activity,
                             explicit_silence_basis=activity_basis,unknown_intervals_never_treated_as_silence=True)
        der['coverage_status']='incomplete_reference_activity' if any(hole['speech_detected_by'] for d in coverage_diagnostics for hole in d['uncovered']) else 'no_detected_uncovered_speech'
        strata={}
        for tag in ('interruption','chevauchement','passage court','nom propre'):
            tagged={z['id'] for z in project['zones'] if tag in z['tags']}
            wz=[row for row in per_zone if row['source_zone'] in tagged];dz=[row for row in der['zones'] if row['id'] in tagged]
            n=sum(row['reference_words'] for row in wz);errors=sum(row['substitute']+row['delete']+row['insert'] for row in wz)
            seconds=sum(row['total'] for row in dz);derr=sum(row['confusion']+row['missed detection']+row['false alarm'] for row in dz)
            strata[tag]={'WER':errors/n if n else None,'human_words':n,'WER_zones':len(wz),
                'DER':derr/seconds if seconds else None,'human_speaker_seconds':seconds,'DER_zones':len(dz),
                'same_global_mapping_as_overall_DER':True}
        results[key]={'name':chain['name'],'transcription':{**counts,
            'WER':(counts['substitute']+counts['delete']+counts['insert'])/counts['reference_words'] if counts['reference_words'] else None,
            'errors':counts['substitute']+counts['delete']+counts['insert'],
            'zones':per_zone,'by_source_zone':aggregate_by_zone(per_zone),'evaluated_audio_seconds':sum(z['end']-z['start'] for z in wer_eligible)},
            'transcription_normalized':{**summarize_wer(normalized_rows),'zones':normalized_rows,'by_source_zone':aggregate_by_zone(normalized_rows),'normalization_version':VERSION},
            'diarization':der,'diarization_qualified':qualified_der,'alignment_and_word_attribution':clock_scores(word_zones,chain,der['mapping'],display_mode),
            'difficult_cases':strata}
    for z in project['zones']:
        if not any(review_valid(z,d,audio_hash) for d in DOMAINS):scope.append({'zone':z['id'],'reason':'Non annotée ou non validée humainement ; exclue de tous les scores.'})
    return {'schema':3,'evaluation_protocol_version':'audited-sequential-v3','generated_utc':utc(),'reference_sha256':digest(project),'audio_sha256':audio_hash,
        'boundary_audit':audit_boundaries(project,dataset,wer_eligible,wer_plan),
        'normalization':{'version':VERSION,'rules':RULES},
        'wer_plan':wer_plan,'wer_plan_sha256':digest(wer_plan) if wer_plan else None,
        'wer_proposals':proposals,'coverage_diagnostics':coverage_diagnostics,
        'results':results,'scope':scope,'protocol':{
            'WER':'Unicode NFC, casse et ponctuation ignorées, apostrophes/accents/chiffres conservés ; somme S+D+I divisée par les mots humains des zones exploitables.',
            'WER_boundaries':'Portions séquentielles : bornes audio et sélection du verbatim validées humainement si découpage nécessaire. Aucun horaire de mot humain requis. Milieu du mot hypothèse dans [début,fin), horloge lexicale Large-v3 identique avec/sans WhisperX.',
            'DER':'pyannote.metrics, collerette 0 s, chevauchements inclus, UEM explicite, appariement global optimal par enregistrement ; diarisation brute.',
            'DER_qualified':'Union des tours humains revus et silences explicitement confirmés ; trous inconnus exclus indépendamment des moteurs. Permutation optimale globale recalculée sur ce seul masque commun. DER conditionnel, couverture partielle : ne mesure pas la détection sur les trous exclus.',
            'WER_normalized':f'Règles symétriques {VERSION}, table complète et provenance des transformations dans le JSON. Aucun mot du verbatim enregistré n’est modifié.',
            'WhisperX':'Texte reconnu et tours Community-1 identiques : mêmes WER/DER bruts que Large-v3. Horaires et attributions des mots finaux évalués séparément.',
            'reference_origin':'Annotations manuelles revues à l’audio, jamais préremplies depuis les moteurs. Exposition aux hypothèses conservée pour chaque relecture.',
            'cpWER':None,'cpCER':None},
        'coverage':{'text_reviewed_zones':len(text_zones),'DER_zones':len(diar_zones),'word_timing_zones':len(word_zones),
            'WER_eligible_zones':len({z['source_zone'] for z in wer_eligible}),'WER_eligible_portions':len(wer_eligible),
            'WER_audio_seconds':sum(z['end']-z['start'] for z in wer_eligible),
            'WER_pending_portions':sum('portion' in item for item in scope),'DER_audio_seconds':sum(z['end']-z['start'] for z in diar_zones),
            'total_audio_seconds':project['audio']['duration'],
            'DER_qualified_audio_seconds':sum(z['end']-z['start'] for z in qualified_zones),
            'DER_unknown_audio_seconds':sum(z['seconds'] for z in unknown_activity),
            'human_reviewed_reference_words':sum(len(tokens(z['verbatim'])) for z in text_zones),
            'text_reviewed_before_hypotheses_seen':sum(not z['reviews']['text']['hypotheses_seen_before_review'] for z in text_zones)},
        'performance':dataset.get('performance',{}),
        'recommendation_status':'Pending human-scored coverage and representativeness review; no automatic engine selection.'}


def main():
    p=argparse.ArgumentParser();p.add_argument('reference',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--variant',choices=['standard','exclusive'],default='exclusive');p.add_argument('--plan',type=Path)
    p.add_argument('--baseline-report',type=Path);p.add_argument('--operator-events',type=Path);args=p.parse_args()
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYANNOTE_METRICS_ENABLED='0',HF_HUB_DISABLE_TELEMETRY='1')
    attempts=[]
    import sys
    def audit(event,parameters):
        if event in ('socket.connect','socket.getaddrinfo','socket.sendto'):
            attempts.append(event);raise PermissionError('Aucun réseau autorisé pendant le calcul des scores.')
    sys.addaudithook(audit)
    project=read(args.reference);dataset=load_dataset(project)
    from .wer_plan import load_saved_plan
    plan=read(args.plan) if args.plan else load_saved_plan(project)[1]
    report=evaluate(project,dataset,args.variant,plan);report['python_network_attempts']=len(attempts)
    from .corrections import operator_summary,tasks
    events=read(args.operator_events) if args.operator_events else []
    events=[e for e in events if e['audio_sha256']==project['audio']['sha256']]
    report['operator_review']=operator_summary(events)
    latest={e['task']['id']:e for e in events if e['outcome']!='important_attribution'}
    report['operator_review']['tasks_remaining']=[t for t in tasks(project,dataset,plan) if not (
        (e:=latest.get(t['id'])) and e['outcome'] in ('corrected','verified_unchanged') and e['task'].get('context_sha256')==t.get('context_sha256'))]
    if args.baseline_report:
        from .audit_metrics import compare_baseline
        from .core import sha
        report['baseline_comparison']={**compare_baseline(report,read(args.baseline_report)),
            'report_path':str(args.baseline_report),'report_sha256':sha(args.baseline_report)}
    # New directory per report, never overwrite the human reference or benchmark.
    args.output.mkdir(parents=True,exist_ok=False)
    from .audit_export import listening_pack
    listening_pack(project,report,args.output)
    (args.output/'scores.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    from .export import write_report
    write_report(project,report,args.output)
    print('Calcul local terminé ; seuls les domaines annotés et validés sont notés.',flush=True)


if __name__=='__main__':main()
