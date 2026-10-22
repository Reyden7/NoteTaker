import copy
import json
from pathlib import Path
import pytest
from notetaker.engines import editorial_report as engine
from notetaker.domain.minutes import validate_minutes
from notetaker.services.evidence import draft_issues


def rows():
    return [
        {'id':'a','speaker_id':'alice','text':'Les recettes sont estimées à 200 000 euros.', 'start_ms':0,'end_ms':5000,'uncertain':False},
        {'id':'b','speaker_id':'alice','text':'Je compte voter cette délibération.', 'start_ms':5100,'end_ms':8000,'uncertain':False},
        {'id':'c','speaker_id':'bob','text':'Ces ventes relèvent de la gestion courante.', 'start_ms':8200,'end_ms':13000,'uncertain':False},
        {'id':'d','speaker_id':'bob','text':'Merci.', 'start_ms':14000,'end_ms':15000,'uncertain':False}]


def run(tmp_path,monkeypatch,*,wrong_voice=False,reject=False,secondary_priority=False):
    original=rows()
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'plan' in label:
            return {'topics':[{'title':'Vente des véhicules','items':[
                {'focus':'Recettes attendues','sources':['a']},
                {'focus':'Intention de vote','sources':['b']},
                {'focus':'Gestion courante','sources':['c']}]}],
                'secondary':[{'source':'b' if secondary_priority else 'd','reason':'detail_secondaire' if secondary_priority else 'formule_de_seance'}]}
        if 'write' in label:
            items=inputs['outline']
            return {'paragraphs':[
                {'speaker':'V2' if wrong_voice else 'V1','nature':'argument',
                 'text':'La personne rappelle les recettes estimées à 200 000 euros.',
                 'sources':['a'],'items':[items[0]['id']],'uncertainty':''},
                {'speaker':'V1','nature':'intention_vote','text':'annonce son intention de voter cette délibération.',
                 'sources':['b'],'items':[items[1]['id']],'uncertainty':''},
                {'speaker':'V2','nature':'opinion','text':'considère ces ventes comme une opération de gestion courante.',
                 'sources':['c'],'items':[items[2]['id']],'uncertainty':''}]}
        return {c['id']:{'supported':not reject,'reason':'Fixture machine, jamais vérité humaine'} for c in inputs['candidates']}
    monkeypatch.setattr(engine,'call_json',call)
    request={'workspace':str(tmp_path),'utterances':original,
             'speaker_labels':{'alice':'Alice Martin','bob':'Voix 2'},
             'speaker_templates':{'alice':'{{V1}}','bob':'Intervenant non identifié ({{V1}})'}}
    result=engine.summarize(request)
    assert original==rows()
    return result,json.loads((tmp_path/'automatic-inventory.json').read_text(encoding='utf-8'))


def test_natural_topic_document_keeps_sources_names_and_intention(tmp_path,monkeypatch):
    result,inventory=run(tmp_path,monkeypatch)
    assert len(result['points'])==1
    p=result['points'][0]
    assert 'Alice Martin rappelle' in p['summary'] and 'La personne' not in p['summary']
    assert 'Intervenant non identifié (Voix 2)' in p['summary']
    assert 'intention de voter' in p['summary'] and p['vote_id'] is None
    assert p['sources']==['a','b','c'] and len(p['claims'])==3
    validate_minutes(result,set('abcd'),{})
    state={'utterances':rows(),'speakers':{'alice':'Alice Martin','bob':'Intervenant 2'}}
    assert not draft_issues(result,state)
    changed=copy.deepcopy(state);changed['speakers']['alice']='Autre personne'
    assert any(i['reason']=='narrative_voice_changed' for i in draft_issues(result,changed))
    assert inventory['coverage_counts']=={'represented':3,'secondary_proposed':1}


def test_full_quotes_and_diagnostics_are_separate_from_reader_document(tmp_path,monkeypatch):
    result,inventory=run(tmp_path,monkeypatch,reject=True)
    reader=json.dumps([result['points'],result['to_verify']],ensure_ascii=False)
    assert 'Fixture machine' not in reader and rows()[0]['text'] not in reader
    report=(tmp_path/'verification-report.md').read_text(encoding='utf-8')
    assert rows()[0]['text'] in report and '00:00.000' in report and 'Fixture machine' in report
    assert result['generation_diagnostics']['paraphrase_claims']==0
    assert len(inventory['items'])==3 and all(not c['retained'] for c in inventory['items'])


def test_wrong_speaker_cannot_be_accepted_by_favorable_machine_judge(tmp_path,monkeypatch):
    result,inventory=run(tmp_path,monkeypatch,wrong_voice=True)
    bad=inventory['items'][0]
    assert not bad['retained'] and bad['reason']=='mixed_or_wrong_speaker'
    assert '200 000' not in result['points'][0]['summary']
    assert next(r for r in inventory['coverage'] if r['id']=='a')['status']=='important_to_verify'


def test_reconstruction_never_joins_interruptions_overlap_or_zero_duration():
    source=rows()+[{'id':'z','speaker_id':'bob','text':'fragment','start_ms':15000,'end_ms':15000}]
    turns=engine.reconstruct_turns(source)
    assert [s['id'] for s in turns[0]['segments']]==['a','b']
    assert turns[1]['speaker']=='bob' and turns[2]['zero_duration']
    source[1]['start_ms']=4000
    assert len(engine.reconstruct_turns(source))==4
    assert [s['id'] for t in engine.reconstruct_turns(source) for s in t['segments']]==['a','b','c','d','z']


def test_plan_failure_still_returns_unofficial_draft_and_exhaustive_inventory(tmp_path,monkeypatch):
    def fail(*args,**kwargs):raise RuntimeError('Fixture de panne Qwen')
    monkeypatch.setattr(engine,'call_json',fail)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':rows(),'speaker_labels':{}})
    assert result['points'] and 'Fixture' not in json.dumps(result['points'])
    inventory=json.loads((tmp_path/'automatic-inventory.json').read_text(encoding='utf-8'))
    assert len(inventory['coverage'])==4 and inventory['errors'][0]['phase']=='plan'
    assert all(r['status']=='unclassified_to_verify' for r in inventory['coverage'][:3])
    assert inventory['coverage'][3]['status']=='secondary_proposed'  # exact standalone "Merci."


def test_numeric_secondary_content_is_not_silently_discarded(tmp_path,monkeypatch):
    source=rows()
    def call(*args,**kwargs):
        return {'topics':[],'secondary':[{'source':'a','reason':'detail_secondaire'}]}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':source,'speaker_labels':{}})
    inventory=json.loads((tmp_path/'automatic-inventory.json').read_text(encoding='utf-8'))
    assert inventory['coverage'][0]['status']=='secondary_with_priority_signal_to_verify'
    assert any('potentiellement importantes' in t for t in result['to_verify'])


def test_zero_duration_source_is_retained_for_diagnostics_but_not_prose(tmp_path,monkeypatch):
    # A dedicated static case without modifying persisted data.
    data=rows();data[0]['end_ms']=0
    monkeypatch.setattr(__import__(__name__,fromlist=['rows']),'rows',lambda:copy.deepcopy(data))
    result,inventory=run(tmp_path,monkeypatch)
    assert inventory['items'][0]['reason']=='source_audio_interval_empty'


@pytest.mark.parametrize('bad_source',[False,True])
def test_compact_plan_and_per_voice_output_do_not_repeat_or_guess_ids(tmp_path,monkeypatch,bad_source):
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'plan' in label:
            assert 'subjects' in schema['properties']
            return {'subjects':[{'title':'Vente des véhicules','source_ids':'a,b,c,a'}]}
        if 'write' in label:
            assert set(schema['properties']['contributions']['properties'])=={'V1','V2'}
            return {'contributions':{
                'V1':{'nature':'argument','text':'rappelle les recettes estimées à 200 000 euros et annonce son intention de voter la délibération.',
                    'sources':'a,b,a' if not bad_source else 'source_inventee','uncertainty':''},
                'V2':{'nature':'opinion','text':'présente les ventes comme de la gestion courante.','sources':'c','uncertainty':''}}}
        return {c['id']:{'supported':True,'reason':'Fixture explicite'} for c in inputs['candidates']}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':rows(),'speaker_labels':{'alice':'Alice','bob':'Bob'},
        'speaker_templates':{'alice':'{{V1}}','bob':'{{V1}}'}})
    inventory=json.loads((tmp_path/'automatic-inventory.json').read_text(encoding='utf-8'))
    if bad_source:
        assert '200 000' not in result['points'][0]['summary']
        assert inventory['errors'][0]['error']=='unknown_or_missing_source'
    else:
        assert result['points'][0]['sources']==['a','b','c']
        assert len(result['points'][0]['claims'])==2
        assert result['points'][0]['summary'].startswith('Alice rappelle')
    assert inventory['coverage'][-1]['status']=='secondary_proposed'


@pytest.mark.parametrize('echo,expected_reason',[
    ('V1 indique que le logiciel placera le nom confirmé avant ce verbe.','instruction_echo_not_speech'),
    ('V2 rappelle les recettes estimées à 200 000 euros.','model_alias_changed')])
def test_instruction_echo_and_wrong_written_alias_never_become_reader_prose(tmp_path,monkeypatch,echo,expected_reason):
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'plan' in label:return {'subjects':[{'title':'Recettes','source_ids':'a,b,c'}]}
        if 'write' in label:return {'contributions':{'V1':{'text':echo,'sources':'a','uncertainty':''}}}
        return {c['id']:{'supported':True,'reason':'Faux avis favorable de fixture'} for c in inputs['candidates']}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':rows(),'speaker_labels':{'alice':'Alice'}})
    inventory=json.loads((tmp_path/'automatic-inventory.json').read_text(encoding='utf-8'))
    assert not inventory['items'][0]['retained'] and inventory['items'][0]['reason']==expected_reason
    assert '200 000' not in result['points'][0]['summary'] and 'logiciel placera' not in result['points'][0]['summary']


def test_one_plan_consolidation_for_overlaps_or_lost_priority_source(tmp_path,monkeypatch):
    labels=[]
    def call(request,label,instruction,inputs,schema,**kwargs):
        labels.append(label)
        if 'consolidate' in label:
            assert 'b' in {r['id'] for r in inputs['passages_prioritaires_oublies']}
            return {'subjects':[{'title':'Vente des véhicules','source_ids':'a,b,c'}]}
        if 'plan' in label:return {'subjects':[{'title':'Recettes','source_ids':'a'},{'title':'Recettes et gestion','source_ids':'a,c'}]}
        if 'write' in label:return {'contributions':{'V1':{'text':'V1 rappelle les recettes estimées à 200 000 euros.',
            'sources':'a','uncertainty':''}}}
        return {c['id']:{'supported':True,'reason':'Fixture machine'} for c in inputs['candidates']}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':rows(),'speaker_labels':{'alice':'Alice'},
        'speaker_templates':{'alice':'{{V1}}'}})
    assert len(result['points'])==1 and result['points'][0]['title']=='Vente des véhicules'
    assert len([label for label in labels if 'consolidate' in label])==1
    inventory=json.loads((tmp_path/'automatic-inventory.json').read_text(encoding='utf-8'))
    assert next(r for r in inventory['coverage'] if r['id']=='b')['status']=='important_to_verify'


def test_one_bad_sentence_does_not_drop_the_supported_neighbor(tmp_path,monkeypatch):
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'plan' in label:return {'subjects':[{'title':'Recettes','source_ids':'a,b,c'}]}
        if 'write' in label:return {'contributions':{'V1':{
            'text':'V1 rappelle les recettes estimées à 200 000 euros. Il souligne un manque de transparence.',
            'sources':'a','uncertainty':''}}}
        return {c['id']:{'supported':True,'reason':'Avis favorable fictif'} for c in inputs['candidates']}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':rows(),'speaker_labels':{'alice':'Alice'},
        'speaker_templates':{'alice':'{{V1}}'}})
    assert 'Alice rappelle' in result['points'][0]['summary'] and 'transparence' not in result['points'][0]['summary']
    inventory=json.loads((tmp_path/'automatic-inventory.json').read_text(encoding='utf-8'))
    assert len(inventory['items'])==2 and inventory['items'][0]['retained'] and not inventory['items'][1]['retained']
    assert inventory['items'][1]['reason']=='transparency_requirement_not_in_cited_source'


def test_consolidation_never_sends_native_word_metadata_to_qwen(tmp_path,monkeypatch):
    source=rows();source[1]['source_json']='NATIVE_WORD_METADATA'*10000
    def call(request,label,instruction,inputs,schema,**kwargs):
        assert 'NATIVE_WORD_METADATA' not in json.dumps(inputs)
        if 'consolidate' in label:return {'subjects':[{'title':'Vente','source_ids':'a,b,c'}]}
        if 'plan' in label:return {'subjects':[{'title':'Vente','source_ids':'a,c'}]}
        if 'write' in label:return {'contributions':{'V1':{'text':'V1 annonce son intention de voter cette délibération.',
            'sources':'b','uncertainty':''}}}
        return {c['id']:{'supported':True,'reason':'Fixture'} for c in inputs['candidates']}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':source,'speaker_labels':{'alice':'Alice'}})
    assert result['generation_diagnostics']['paraphrase_claims']==1


@pytest.mark.parametrize('text,quote,reason',[
    ('La gestion semble caractérisée par des pertes.','Les dépenses sont supérieures aux économies annoncées.','financial_diagnosis_not_in_source'),
    ('Les chiffres sont mal évalués.','Vous oubliez de parler de ces chiffres.','missing_figures_changed_to_wrong_figures'),
    ('Des ventes ont eu lieu sans conférence ni délibération avec débat.',"Nous n'avons pas fait une conférence de presse à chaque fois.",'non_systematic_changed_to_never'),
    ('La pratique est une forme d’amoralité.','Des véhicules ont été vendus en 2022.','moral_qualification_not_in_citation'),
    ('Propose de nommer un commissaire priseur.',"On va peut-être vous avoir comme commissaire priseur.",'proposal_not_explicit_in_cited_sources')])
def test_scope_strengthening_in_actual_writing_failures_is_rejected(text,quote,reason):
    assert engine.financial_scope_problem(text,[quote])==reason


@pytest.mark.parametrize('text,quote,reason',[
    ('Critique violemment les déclarations.','Vous parlez du courage nécessaire.','criticism_intensity_added'),
    ('Demande que les motions soient bien pensées.',"Il faut faire attention avec les motions qu'on y met.",'ambiguous_motion_word_requires_audio_review'),
    ("Les panneaux ne parviennent pas à éveiller l'intérêt du public.",'On voit apparaître ces petits panneaux.','audience_reaction_not_in_citation')])
def test_intensity_ambiguity_and_audience_inventions(text,quote,reason):
    assert engine.financial_scope_problem(text,[quote])==reason


def test_literal_context_source_can_be_cited_without_guessing_or_losing_it(tmp_path,monkeypatch):
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'plan' in label:return {'subjects':[{'title':'Vente','source_ids':'a,c'}]}
        if 'consolidate' in label:raise RuntimeError('Fixture de reprise indisponible')
        if 'write' in label:
            assert 'b' in {r['id'] for r in inputs['context_only']}
            return {'contributions':{'V1':{'text':'V1 annonce son intention de voter cette délibération.',
                'sources':'b','uncertainty':''}}}
        return {c['id']:{'supported':True,'reason':'Fixture machine'} for c in inputs['candidates']}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':rows(),'speaker_labels':{'alice':'Alice'},
        'speaker_templates':{'alice':'{{V1}}'},'recover_editorial_omissions':False})
    assert result['points'][0]['claims'][0]['evidence']==[{'id':'b','quote':rows()[1]['text']}]


def test_interpretive_tail_remains_a_separate_review_item():
    text='V1 cite 200 000 euros, ce qui suggère un déficit. Il rappelle un coût de 300 000 euros.'
    parts=engine.prose_sentences(text)
    assert parts==['V1 cite 200 000 euros.','ce qui suggère un déficit.','Il rappelle un coût de 300 000 euros.']


def test_reader_notes_use_bound_names_instead_of_model_aliases():
    request={'speaker_labels':{'alice':'Alice Martin'},'speaker_templates':{'alice':'{{V1}}'}}
    assert engine.reader_note('Référence citée par V2 à vérifier.',{'V2':'alice'},request)=='Référence citée par Alice Martin à vérifier.'
    assert engine.reader_note('aucune',{},request)==''
    assert engine.reader_note('V8 reste incertain.',{},request)=='un intervenant non identifié reste incertain.'


def test_explicit_discourse_anchors_separate_questions_management_and_vote():
    data=[
        {'id':'q','speaker_id':'a','start_ms':0,'end_ms':4000,'text':'Nous voulons des réponses aux questions sur RESS.'},
        {'id':'r','speaker_id':'a','start_ms':4100,'end_ms':7000,'text':'Nous demandons une réponse à ces questions.'},
        {'id':'v','speaker_id':'a','start_ms':8000,'end_ms':10000,'text':'Mais moi, je vais la voter, votre délibération.'},
        {'id':'d','speaker_id':'b','start_ms':12000,'end_ms':16000,'text':"Nous avons géré l'argent public avec honneur et probité."},
        {'id':'x','speaker_id':'b','start_ms':16100,'end_ms':20000,'text':'Nous assumons nos choix sur les associations.'}]
    groups,protected=engine.explicit_discourse_groups(data)
    assert groups[0]['title']=='Questions sur RESS' and groups[0]['ids']==['q','r']
    assert next(g for g in groups if g.get('vote_intent_rule'))['ids']==['v']
    assert next(g for g in groups if g['title']=='Gestion publique et choix revendiqués')['ids']==['d','x']
    assert protected==set('qrvdx')
    data[2]['text']='Il a dit : je vais la voter, votre délibération.'
    assert not any(g.get('vote_intent_rule') for g in engine.explicit_discourse_groups(data)[0])
    data[2]['text']='Je ne vais pas voter cette délibération.'
    assert not any(g.get('vote_intent_rule') for g in engine.explicit_discourse_groups(data)[0])


def test_explicit_intention_recovery_never_creates_a_vote_result(tmp_path,monkeypatch):
    source=[{'id':'v','speaker_id':'a','text':'Mais moi, je vais la voter, votre délibération.',
        'start_ms':0,'end_ms':4000,'uncertain':False}]
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'plan' in label:return {'subjects':[{'title':'Délibération','source_ids':'v'}]}
        assert 'write' not in label
        return {c['id']:{'supported':True,'reason':'Avis de fixture'} for c in inputs['candidates']}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':source,'speaker_labels':{'a':'Alice'},
        'speaker_templates':{'a':'{{V1}}'},'discourse_anchors':True})
    assert result['points'][0]['title']=='Intentions de vote exprimées'
    assert 'Alice évoque son intention' in result['points'][0]['summary']
    assert result['points'][0]['vote_id'] is None
    assert not any(w in result['points'][0]['summary'] for w in ('adoptée','favorable','pour','contre'))
    assert result['points'][0]['claims'][0]['kind']=='context'


def test_overlapping_recovery_keeps_new_sources_without_duplicate_assignments(tmp_path,monkeypatch):
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'consolidate' in label:return {'subjects':[{'title':'Recettes','source_ids':'a'}]}
        if 'recover' in label:return {'subjects':[{'title':'Intention','source_ids':'b'},{'title':'Gestion courante','source_ids':'b,c'}]}
        if 'plan' in label:return {'subjects':[{'title':'Recettes','source_ids':'a'}]}
        if 'write' in label:
            source=inputs['sources'][0]['id']
            alias='V2' if source=='c' else 'V1'
            text={'a':'rappelle les recettes estimées à 200 000 euros.',
                  'b':'annonce son intention de voter cette délibération.',
                  'c':'présente les ventes comme de la gestion courante.'}[source]
            return {'contributions':{alias:{'text':text,'sources':source,'uncertainty':''}}}
        return {c['id']:{'supported':True,'reason':'Fixture'} for c in inputs['candidates']}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':rows(),
        'speaker_labels':{'alice':'Alice','bob':'Bob'},'speaker_templates':{'alice':'{{V1}}','bob':'{{V1}}'}})
    inventory=json.loads((tmp_path/'automatic-inventory.json').read_text(encoding='utf-8'))
    assert inventory['coverage_counts']=={'represented':3,'secondary_proposed':1}
    assert inventory['errors']==[] and len(result['points'])==3


def test_ambiguous_accusation_and_deictic_tail_are_not_promoted():
    assert engine.financial_scope_problem('Estime que des allégations ont été formulées.',
        ['Soit vous nous accusez concrètement, soit vous laissez entendre une petite musique.'])=='conditional_accusation_changed_to_asserted_allegation'
    parts=engine.prose_sentences('Il exprime sa fierté des associations, et que cette action est une opération de communication.')
    assert parts==['Il exprime sa fierté des associations.','et que cette action est une opération de communication.']
    assert engine.financial_scope_problem('La politique ne présente pas de grands changements.',
        ["On n'avait pas trop de surprises en politique, c'est décevant."])=='absence_of_surprise_changed_to_absence_of_policy_change'
    assert engine.financial_scope_problem('Ajoute qu’aucune faute n’a été commise.',
        ['Nous avons géré avec honneur et probité.'])=='absence_of_fault_not_in_source'
    assert engine.financial_scope_problem('Critique le gouvernement.',
        ["Votre équipe met en avant ces ventes."])=='municipal_team_changed_to_government'
    assert engine.prose_sentences('Il précise que les associations sont une fierté, et qu’ils en assument le soutien.')==[
        'Il précise que les associations sont une fierté.','ajoute qu’ils en assument le soutien.']
    assert engine.prose_sentences('Il doute que la mesure soit possible, et que le coût soit connu.')==[
        'Il doute que la mesure soit possible.','et que le coût soit connu.']


def test_new_editorial_exports_use_compact_layout_without_affecting_legacy(tmp_path):
    from notetaker.services.export import _pdf,_docx
    from pypdf import PdfReader
    from docx import Document
    content={'points':[{'title':'Vente des véhicules','summary':'Alice demande un examen des recettes.',
        'sources':['s'],'vote_id':None}],'to_verify':[],
        'generation_diagnostics':{'strategy':engine.VERSION}}
    details={'title':'Séance de recette','preview':True,'working_draft':True}
    _pdf(content,'BROUILLON',tmp_path/'new.pdf',[],[],details)
    assert len(PdfReader(tmp_path/'new.pdf').pages)==1
    _docx(content,'BROUILLON',tmp_path/'new.docx',[],[],details)
    xml=Document(tmp_path/'new.docx').element.xml
    assert 'w:type="page"' not in xml
    content.pop('generation_diagnostics')
    _pdf(content,'BROUILLON',tmp_path/'old.pdf',[],[],details)
    assert len(PdfReader(tmp_path/'old.pdf').pages)==2


def test_literal_information_request_recovery_is_generic_and_speaker_bound(tmp_path,monkeypatch):
    data=[{'id':'a','speaker_id':'x','start_ms':0,'end_ms':4000,'text':'Nous aimerions bien connaître vos intentions.'},
          {'id':'b','speaker_id':'x','start_ms':4100,'end_ms':8000,'text':'On ne sait pas réellement quel est votre plan SNCF.'}]
    groups,ids=engine.explicit_discourse_groups(data)
    assert groups==[{'title':'Demande de précisions sur plan SNCF','object':'plan SNCF','ids':['a','b'],'request_rule':True}]
    assert ids=={'a','b'}
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'plan' in label:return {'subjects':[{'title':'Projet','source_ids':'a,b'}]}
        assert 'write' not in label
        return {c['id']:{'supported':True,'reason':'Fixture'} for c in inputs['candidates']}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':data,'speaker_labels':{'x':'Alice'},
        'speaker_templates':{'x':'{{V1}}'},'discourse_anchors':True})
    assert result['points'][0]['title']=='Demande de précisions sur plan SNCF'
    assert result['points'][0]['summary']=='Alice demande des précisions sur le contenu du « plan SNCF ».'
    data[0]['speaker_id']='other'
    assert not engine.explicit_discourse_groups(data)[0]


def test_ui_report_opens_latest_completed_generation_after_failed_retry(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication,QDialog,QTextEdit
    from notetaker.ui.window import MainWindow
    from notetaker.infrastructure.paths import session_directory
    app=QApplication.instance() or QApplication([])
    window=MainWindow(tmp_path/'ui');sid=window.store.create('Séance fictive')
    window.sid=sid
    for label in ('ANCIEN RAPPORT','RAPPORT COURANT'):
        jid=window.store.start_job(sid,'automatic-report')
        path=session_directory(window.store.root,sid)/'jobs'/jid;path.mkdir(parents=True)
        (path/'verification-report.md').write_text(label,encoding='utf-8')
        window.store.finish_job(jid,True)
    jid=window.store.start_job(sid,'automatic-report');window.store.finish_job(jid,False,'fixture')
    seen=[]
    def show(dialog):seen.extend(w.toPlainText() for w in dialog.findChildren(QTextEdit));return 0
    monkeypatch.setattr(QDialog,'exec',show)
    window.show_automatic_diagnostics()
    assert seen==['RAPPORT COURANT']
    window.sid=None;window.close();app.processEvents()
