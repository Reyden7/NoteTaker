"""Small sample proposals, never gold events or automatically approved text."""
from .core import blank_zone,review_valid,QualificationError
import copy


def proposals(project,dataset):
    result=[{'id':z['id'],'start':z['start'],'end':z['end'],'title':z['title'],'origin':'temporal_blind','tags':[]} for z in project['zones']]
    duration=project['audio']['duration'];patterns={
        'proposition':('proposons','propose','proposition'),
        'délibération':('délibération','délibérer','délibere'),
        'vote':('vote','abstention','contre','adopté','adopte','unanimité')}
    for label,terms in patterns.items():
        found=None
        for chain in ('small','large'):
            for s in dataset['chains'][chain]['asr']:
                if any(term in s.get('text','').casefold() for term in terms):
                    found=s;break
            if found:break
        if found:
            a=max(0,found['start']-5);b=min(duration,max(a+25,found['end']+5))
            result.append({'id':'S-'+label,'start':a,'end':b,'title':label+' possible · indice ASR à écouter',
                'origin':'ASR_keyword_not_human_truth','tags':[]})
    turns=dataset['chains']['large']['diarization']
    for before,after in zip(turns,turns[1:]):
        if before['speaker']!=after['speaker']:
            center=after['start'];a=max(0,center-8);b=min(duration,center+17)
            result.append({'id':'S-changement','start':a,'end':b,'title':'changement de voix possible · indice moteur',
                           'origin':'model_turn_change_not_identity_truth','tags':[]});break
    return result


def select(project,selected):
    if any(z['verbatim'].strip() or z['turns'] or z['words'] or any(z['reviews'].values()) for z in project['zones']):
        raise QualificationError('Des annotations existent déjà : elles ne seront pas remplacées. Utilisez « Ajouter une zone » pour une vérification complémentaire.')
    if not 1<=len(selected)<=6:raise QualificationError('Choisir un à six extraits pour limiter le travail humain.')
    new=copy.deepcopy(project);new['zones']=[]
    for i,p in enumerate(selected):
        z=blank_zone(f'M{i+1:02d}',p['start'],p['end'],f"M{i+1:02d} · {p['title']}")
        z['tags']=p.get('tags',[]);z['hypotheses_seen']=p['origin']!='temporal_blind';z['selection_origin']=copy.deepcopy(p)
        new['zones'].append(z)
    from .core import validate_project
    validate_project(new);return new
