"""Regressions for source coverage, scope and reversible name presentation."""
import copy
import json
import pytest
from notetaker.domain.summary import municipal_name,narrative_problems,refresh_narrative
from notetaker.engines import editorial_report as engine


def test_display_names_are_versioned_and_do_not_change_historical_bindings():
    state={'speakers':{'a':'moniseur sineux'},'utterances':[{'id':'a','speaker_id':'a'}]}
    old={'summary':'moniseur sineux rappelle les ventes.',
         'claims':[{'id':'c','speaker':'a'}],
         'narrative':[{'text':'moniseur sineux rappelle les ventes.','template':'{{V1}} rappelle les ventes.',
                       'voice_bindings':{'V1':'a'},'claim_ids':['c']}]}
    new=copy.deepcopy(old);new['narrative'][0].update(text='Monsieur Sineux rappelle les ventes.',name_style='municipal-civilities-v1')
    new['summary']=new['narrative'][0]['text']
    assert not narrative_problems(old,state) and not narrative_problems(new,state)
    assert state['speakers']['a']=='moniseur sineux'
    changed=copy.deepcopy(state);changed['speakers']['a']='Monsieur Autre'
    assert 'narrative_voice_changed' in narrative_problems(new,changed)
    refreshed=copy.deepcopy(new)
    assert refresh_narrative(refreshed,new,changed)
    assert refreshed['summary']=='Monsieur Autre rappelle les ventes.'
    bad=copy.deepcopy(new);bad['narrative'][0]['name_style']='infer-identity'
    assert 'narrative_voice_changed' in narrative_problems(bad,state)
    assert municipal_name('madame de la Tour')=='Madame de la Tour'
    assert municipal_name('Voix inconnue')=='Voix inconnue'


@pytest.mark.parametrize('text',[
    'rappelle une histoire souvent marquée par des délibérations peu débattues.',
    'affirme que les ventes ont toujours eu lieu sans conférence.',
])
def test_historical_frequency_cannot_be_inferred_from_examples(text):
    assert engine.financial_scope_problem(text,["J’ai déjà vu passer des délibérations, pas forcément en grand débat."])=='historical_frequency_added'


def test_named_comparison_is_fenced_without_affiliation_inference():
    data=[{'id':'a','speaker_id':'x','start_ms':0,'end_ms':5000,
           'text':'Votre mentor, Laurent Wauquiez, je pense que vous inspirez beaucoup de ce qu’il fait.'},
          {'id':'b','speaker_id':'x','start_ms':5100,'end_ms':9000,'text':'On voit ces panneaux de communication.'},
          {'id':'c','speaker_id':'y','start_ms':9100,'end_ms':11000,'text':'Nous défendons cette gestion.'}]
    assert engine.comparison_groups(data)==[{'title':'Communication et comparaison avec Laurent Wauquiez','ids':['a','b']}]
    assert data[0]['text'].startswith('Votre mentor')


@pytest.mark.parametrize('uncertain',[False,True])
def test_sentence_sources_and_prewrite_speaker_coverage(tmp_path,monkeypatch,uncertain):
    data=[{'id':'a','speaker_id':'x','start_ms':0,'end_ms':5000,'text':'Les recettes sont estimées à 200 000 euros.'},
          {'id':'b','speaker_id':'x','start_ms':5100,'end_ms':9000,'text':'Certains véhicules sont amortis.'},
          {'id':'c','speaker_id':'y','start_ms':9100,'end_ms':11000,'text':'Ces ventes sont une gestion courante.'}]
    data[0]['uncertain']=uncertain
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'plan' in label:return {'subjects':[{'title':'Véhicules','source_ids':'a,b,c'}]}
        if 'write' in label:
            assert 'topic' not in inputs  # A machine heading cannot become evidence.
            pre=json.loads((tmp_path/'coverage-before-writing.json').read_text(encoding='utf-8'))
            assert [r['source_ids'] for r in pre['matrix']]==[['a','b'],['c']]
            assert 'sentences' in schema['properties']['contributions']['properties']['V1']['properties']
            return {'contributions':{
                'V1':{'sentences':[{'text':'V1 rappelle les recettes estimées à 200 000 euros.','sources':'a','uncertainty':''}],
                      'omissions':'b : amortissement non repris'},
                'V2':{'sentences':[{'text':'V2 considère les ventes comme de la gestion courante.','sources':'c','uncertainty':''}],
                      'omissions':'aucune'}}}
        return {c['id']:{'supported':True,'reason':'Fixture non humaine'} for c in inputs['candidates']}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':data,'sentence_evidence':True,'sentence_output_experiment':True,
        'speaker_labels':{'x':'madame maximi','y':'moniseur sineux'},
        'speaker_templates':{'x':'{{V1}}','y':'{{V1}}'}})
    assert [c['evidence'][0]['id'] for c in result['points'][0]['claims']]==['a','c']
    from notetaker.domain.minutes import validate_minutes
    validate_minutes(result,set('abc'),{})
    assert 'Madame Maximi' in result['points'][0]['summary'] and 'Monsieur Sineux' in result['points'][0]['summary']
    assert not narrative_problems(result['points'][0],{'utterances':data,'speakers':{'x':'madame maximi','y':'moniseur sineux'}})
    inv=json.loads((tmp_path/'automatic-inventory.json').read_text(encoding='utf-8'))
    assert inv['coverage_by_topic_and_speaker'][0]['uncited_ids']==['b']
    assert not inv['coverage_by_topic_and_speaker'][0]['semantic_completeness_verified']
    assert 'amortissement non repris' in (tmp_path/'verification-report.md').read_text(encoding='utf-8')
    assert 'Fixture' not in json.dumps(result['to_verify']) and len(result['to_verify'])==1+uncertain
    assert inv['coverage'][0]['uncertain']==uncertain
    if uncertain:assert 'signalées incertaines' in (tmp_path/'verification-report.md').read_text(encoding='utf-8')


def test_named_omission_not_hidden_by_a_shared_citation():
    rows=[{'id':'a','speaker_id':'x','text':'Je compare avec Laurent Wauquiez.'}]
    topics=[{'id':'t','title':'Communication','items':[{'sources':['a']}]}]
    matrix=engine.coverage_matrix(topics,rows,[{'topic_id':'t','retained':True,
        'claim':{'id':'c','speaker':'x','text':'critique la communication.','evidence':[{'id':'a'}]}}])
    assert matrix[0]['uncited_ids']==[]
    assert matrix[0]['named_mentions_not_repeated']==['Laurent Wauquiez']
    assert not matrix[0]['semantic_completeness_verified']


def test_inferred_consequence_is_separate_from_supported_statement():
    assert engine.prose_sentences('V1 indique que les véhicules sont amortis, ce qui soulève une question sur le coût.')==[
        'V1 indique que les véhicules sont amortis.','ce qui soulève une question sur le coût.']
    assert engine.financial_scope_problem('rappelle des délibérations sans grand débat.',
        ['J’ai déjà vu des délibérations, pas forcément en grand débat.'])=='qualified_history_changed_to_absolute_absence'


def test_historical_first_person_cannot_be_transferred_to_current_team():
    rows=[{'id':'a','speaker_id':'x','text':"L’équipe précédente a vendu des véhicules.",'start_ms':0,'end_ms':4000},
          {'id':'b','speaker_id':'x','text':"Et nous n'avons pas fait une conférence de presse à chaque fois.",'start_ms':4100,'end_ms':9000}]
    # Straight versus curly apostrophes in l’équipe do not affect the referent.
    assert engine.historical_referent_problem("souligne que l'équipe actuelle n'a pas tenu de conférence à chaque vente.",
        [{'id':'b'}],rows)=='previous_team_changed_to_current_team'
    assert engine.historical_referent_problem("rappelle que son équipe n'a pas tenu une conférence à chaque vente.",
        [{'id':'b'}],rows) is None


def test_unspecified_idea_cannot_be_assigned_to_following_acronym():
    assert engine.financial_scope_problem('souligne une vague idée sur le projet de RESS.',
        ['On a une vague idée, mais nous voulons des réponses aux questions sur RESS.'])=='ambiguous_idea_assigned_to_later_question'


def test_quoted_mentor_is_never_the_speakers_established_mentor():
    assert engine.financial_scope_problem('estime que Laurent Wauquiez, son mentor, inspire les initiatives.',
        ['Votre mentor, Laurent Wauquiez, je pense que vous inspirez beaucoup de ce qu’il fait.'])=='rhetorical_affiliation_changed_to_established_relationship'


def test_non_systematic_history_can_be_rephrased_without_false_rejection():
    assert engine.financial_scope_problem('précise que les ventes ne donnaient pas systématiquement lieu à une conférence.',
        ["Nous n'avons pas fait une conférence de presse à chaque fois."]) is None


def test_criticism_is_not_a_formal_violation_and_unrelated_citation_is_rejected():
    assert engine.financial_scope_problem('affirme une violation des règles fondamentales de la démocratie.',
        ["Il faut une délibération, ce n'est pas rien en termes de respect de la démocratie."])=='criticism_strengthened_to_formal_violation'
    assert engine.financial_scope_problem('rappelle des délibérations peu débattues.',
        ['Les recettes sont estimées à 200 000 euros.'])=='deliberation_not_in_sentence_citations'


def test_source_identifiers_cannot_escape_into_reader_prose(tmp_path,monkeypatch):
    data=[{'id':'src-01','speaker_id':'x','start_ms':0,'end_ms':4000,'text':'Les recettes sont estimées à 200 000 euros.'}]
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'plan' in label:return {'subjects':[{'title':'Recettes','source_ids':'src-01'}]}
        if 'write' in label:return {'contributions':{'V1':{'text':'V1 rappelle les recettes de 200 000 euros src-01.',
            'sources':'src-01','uncertainty':''}}}
        return {c['id']:{'supported':True,'reason':'Avis faux favorable'} for c in inputs['candidates']}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':data,'speaker_labels':{'x':'Alice'},'sentence_evidence':True})
    assert 'src-01' not in json.dumps([result['points'][0]['summary'],result['to_verify']])
    inventory=json.loads((tmp_path/'automatic-inventory.json').read_text(encoding='utf-8'))
    assert inventory['items'][0]['reason']=='technical_source_identifier_in_prose'


def test_colloquial_resale_example_is_not_a_history_of_the_institution():
    assert engine.financial_scope_problem("rappelle que l'histoire de la collectivité est celle d'une opposition de douze ans.",
        ["C'est l'histoire classique d'une collectivité qui revend... J'ai déjà vu passer des délibérations."])=='colloquial_example_changed_to_institutional_history'


def test_literal_comparison_is_sourced_without_personal_relationship(tmp_path,monkeypatch):
    data=[{'id':'a','speaker_id':'x','start_ms':0,'end_ms':5000,
           'text':'Votre mentor, Laurent Wauquiez, je pense que vous inspirez de ce qu’il fait. À la mairie, on voit, comme à la région, ces petits panneaux.'},
          {'id':'b','speaker_id':'x','start_ms':5100,'end_ms':9000,'text':'Tout ce que fait de bien votre collectivité. Beaucoup de communication.'}]
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'plan' in label:return {'subjects':[{'title':'Communication','source_ids':'a,b'}]}
        assert 'write' not in label
        return {c['id']:{'supported':True,'reason':'Fixture de contrôle, pas validation humaine'} for c in inputs['candidates']}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':data,'speaker_labels':{'x':'madame maximi'},
        'speaker_templates':{'x':'{{V1}}'},'sentence_evidence':True,'discourse_anchors':True})
    text=result['points'][0]['summary']
    assert 'Madame Maximi évoque Laurent Wauquiez' in text and 'mentor' not in text
    assert result['points'][0]['claims'][0]['evidence']==[{'id':r['id'],'quote':r['text']} for r in data]
    data[1]['speaker_id']='other'
    assert not engine.comparison_groups(data)[0].get('named_comparison_rule')


def test_historical_limit_requires_both_negations_and_same_explicit_team():
    data=[{'id':'a','speaker_id':'x','start_ms':0,'end_ms':4000,'text':"L’équipe précédente a vendu des véhicules le 29 juin 2022."},
          {'id':'b','speaker_id':'x','start_ms':4100,'end_ms':8000,
           'text':"Et nous n'avons pas fait une conférence de presse à chaque fois. Et nous n'avons pas fait une délibération avec débat à chaque fois."}]
    result=engine.explicit_historical_limits(data)
    assert len(result)==1 and 'pas systématiquement' in result[0]['text'] and 'avec débat' in result[0]['text']
    assert not engine.financial_scope_problem(result[0]['text'],[r['text'] for r in data])
    for change in ('different_voice','missing_negation','zero_duration','reported_quotation'):
        altered=copy.deepcopy(data)
        if change=='different_voice':altered[1]['speaker_id']='y'
        if change=='missing_negation':altered[1]['text']=altered[1]['text'].split('. Et')[0]+'.'
        if change=='zero_duration':altered[1]['end_ms']=altered[1]['start_ms']
        if change=='reported_quotation':altered[1]['text']='Il dit : '+altered[1]['text']
        assert not engine.explicit_historical_limits(altered),change


def test_historical_qualification_is_not_lost_when_qwen_only_keeps_dates(tmp_path,monkeypatch):
    data=[{'id':'a','speaker_id':'x','start_ms':0,'end_ms':4000,'text':"L’équipe précédente a vendu des véhicules le 29 juin 2022."},
          {'id':'b','speaker_id':'x','start_ms':4100,'end_ms':8000,
           'text':"Et nous n'avons pas fait une conférence de presse à chaque fois. Et nous n'avons pas fait une délibération avec débat à chaque fois."}]
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'plan' in label:return {'subjects':[{'title':'Ventes de véhicules','source_ids':'a,b'}]}
        if 'write' in label:return {'contributions':{'V1':{'text':'rappelle la vente de véhicules le 29 juin 2022.',
            'sources':'a','uncertainty':''}}}
        return {c['id']:{'supported':True,'reason':'Fixture machine'} for c in inputs['candidates']}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':data,'speaker_labels':{'x':'monsieur exemple'},
        'speaker_templates':{'x':'{{V1}}'},'sentence_evidence':True})
    assert 'pas systématiquement' in result['points'][0]['summary']
    assert 'délibération avec débat' in result['points'][0]['summary']
    assert result['points'][0]['claims'][-1]['evidence']==[{'id':r['id'],'quote':r['text']} for r in data]


def test_question_sources_keep_missing_answer_and_legitimacy_separate():
    data=[{'id':'q','speaker_id':'x','text':'On a une vague idée, mais nous voulons des réponses aux questions sur RESS.'},
          {'id':'m','speaker_id':'x','text':"Je n'ai pas eu de réponse, madame l'adjointe."},
          {'id':'l','speaker_id':'x','text':"Les élus d'opposition, certes minoritaires, sont légitimes pour vous interroger."}]
    result=engine.literal_question_claims(data)
    assert [r['id'] for r,kind,text in result]==['q','m','l']
    assert 'vague idée' not in result[0][2] and 'RESS' in result[0][2]
    assert 'ne pas avoir reçu' in result[1][2] and 'pertinentes' not in result[2][2]
    data[1]['speaker_id']='different'
    assert engine.literal_question_claims(data)==[]


def test_detaching_adjuncts_does_not_promote_a_doubted_statement():
    assert engine.prose_sentences('V1 évoque des véhicules amortis, soulignant que leur état est connu.')==[
        'V1 évoque des véhicules amortis.','souligne que leur état est connu.']
    assert engine.prose_sentences('Il doute du constat, affirmant que les chiffres sont connus.')==[
        'Il doute du constat.','affirmant que les chiffres sont connus.']
    assert engine.financial_scope_problem("s'oppose à l'idée que la vente relève d'une gestion courante.",
        ["C'est de la gestion courante de la ville."])=='routine_management_assertion_changed_to_opposition'


def test_associations_cannot_be_the_unresolved_communication_operation(tmp_path,monkeypatch):
    data=[{'id':'a','speaker_id':'x','start_ms':0,'end_ms':5000,
           'text':"Sur les associations, c'était une fierté de construire le vivre-ensemble. Oui, oui, on assume ça. Donc voilà, c'est une opération de com', elle est bien menée."}]
    def call(request,label,instruction,inputs,schema,**kwargs):
        if 'plan' in label:return {'subjects':[{'title':'Choix associatifs','source_ids':'a'}]}
        if 'write' in label:return {'contributions':{'V1':{'text':"V1 indique que les associations sont une opération de communication.",
            'sources':'a','uncertainty':''}}}
        return {c['id']:{'supported':True,'reason':'Avis machine de fixture'} for c in inputs['candidates']}
    monkeypatch.setattr(engine,'call_json',call)
    result=engine.summarize({'workspace':str(tmp_path),'utterances':data,'speaker_labels':{'x':'monsieur exemple'},
        'speaker_templates':{'x':'{{V1}}'},'sentence_evidence':True})
    assert 'assume les choix concernant les associations' in result['points'][0]['summary']
    assert 'opération de communication' not in result['points'][0]['summary']


def test_missing_political_program_is_a_request_not_an_invented_topic():
    data=[{'id':'a','speaker_id':'x','start_ms':0,'end_ms':4000,
           'text':"Nous aimerions bien que le maire nous dise ce qu'il veut réellement faire pour cette ville."},
          {'id':'b','speaker_id':'x','start_ms':4100,'end_ms':8000,
           'text':"On ne sait pas réellement quel est votre projet politique."}]
    groups,_=engine.explicit_discourse_groups(data)
    assert groups[0]['title']=='Demande de précisions adressée au maire'
    assert groups[0]['request_text']=='demande au maire de préciser ce qu’il veut faire pour la ville.'


def test_literal_routine_classification_uses_adjacent_same_voice_sale():
    data=[{'id':'a','speaker_id':'x','start_ms':0,'end_ms':4000,'text':'Vous êtes saisi par la vente de 22 véhicules.'},
          {'id':'b','speaker_id':'x','start_ms':4500,'end_ms':8000,'text':"Alors que c'est de la gestion courante de la ville."}]
    result=engine.explicit_routine_sales(data)
    assert result[0]['text']=='qualifie la vente des 22 véhicules de gestion courante de la ville.'
    data[1]['speaker_id']='y'
    assert not engine.explicit_routine_sales(data)


def test_figure_omissions_are_oral_not_omissions_from_legal_decisions():
    row={'text':'Les chiffres que vous oubliez, des fois, de parler dans les conseils municipaux.'}
    frame=engine.explicit_source_frames(row)
    assert frame[0]=='criticised_figure_omission' and 'parfois' in frame[2]
    assert 'délibération' not in frame[2]


def test_probity_is_explicitly_framed_as_a_defence_not_certified_conduct():
    row={'text':"Parce que comme tous les élus, comme tous les élus, nous avons géré l'argent public avec honneur, avec probité, avec sobriété."}
    frame=engine.explicit_source_frames(row)
    assert frame[1]=='position' and frame[2].startswith('défend la gestion passée')
    assert 'tous les élus' not in frame[2] and 'a géré' not in frame[2]
    assert engine.explicit_source_frames({'text':"Il dit que nous avons géré l'argent public avec honneur, probité, sobriété."}) is None


def test_reordered_document_does_not_retain_undefined_previous_intervention():
    assert engine.editorial_body("s'inscrit dans l'intervention précédente en soulignant que les ventes sont courantes.")=="souligne que les ventes sont courantes."
