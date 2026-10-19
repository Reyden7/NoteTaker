"""Authored regression fixtures, not an annotated human reference for the debate."""
import copy
import json
import pytest
from notetaker.engines import topic_summary as engine
from notetaker.domain.summary import (PROFILES,lexicon_from_text,lexicon_text,voice_registry,
    render_template,narrative_problems,manual_narrative)
from notetaker.services.pipeline import assemble_summary,integral_transcript
from notetaker.services.evidence import DraftEvidenceError,draft_issues,propose_attribution_refresh
from notetaker.services.storage import SessionStore
from notetaker.services.session_export import export_session


@pytest.mark.parametrize('kind,discourse,text,quote,reason',[
    ('question','question','Les habitants refusent le chantier.','Les habitants refusent-ils le chantier ?', 'question_changed_to_assertion'),
    ('position','own','La mesure est approuvée.','Approuvez-vous cette mesure ?', 'question_changed_to_assertion'),
    ('position','own','Le locuteur soutient les blocages.','Vous estimez que les blocages sont indispensables.', 'reported_opinion_assigned_to_reporting_voice'),
    ('proposal','anecdote','Un transport scolaire supplémentaire est proposé.',"Quand j’étais au lycée, je prenais le bus très tôt.",'anecdote_or_description_changed_to_proposal'),
])
def test_observed_modality_and_attribution_errors_are_not_justified_by_exact_quote(kind,discourse,text,quote,reason):
    assert engine.discourse_problem(kind,discourse,text,[quote])==reason


def test_explicit_question_report_and_proposal_keep_their_modality():
    assert engine.discourse_problem('question','question','La personne demande si les habitants approuvent la mesure.',['Les habitants approuvent-ils la mesure ?']) is None
    assert engine.discourse_problem('position','reported','Le journaliste interroge la position attribuée à son invité.',['Vous estimez que les blocages sont indispensables.']) is None
    assert engine.discourse_problem('proposal','own','Une expertise préalable est demandée.',['Je demande une expertise avant les travaux.']) is None


def test_absence_of_opposition_does_not_establish_support():
    source="Je n’ai jamais été opposé à cette mesure."
    assert engine.discourse_problem('argument','own','La personne a toujours été en faveur de cette mesure.',[source])=='absence_of_opposition_changed_to_support'
    assert engine.discourse_problem('argument','own','La personne indique ne jamais avoir été opposée à cette mesure.',[source]) is None


def test_real_listening_actor_inversion_is_refused():
    quotes=["le problème avec les ministres, donc le ministre de l’Éducation nationale", "ou le ministre de l’Enseignement supérieur, c’est qu’ils ne nous écoutent pas."]
    bad='La personne souligne que les ministres de l’Éducation nationale ou de l’Enseignement supérieur ne sont pas entendus.'
    assert engine.role_problem(bad,quotes)=='listener_actor_changed_to_patient'
    assert engine.role_problem('La personne reproche aux ministres de ne pas les écouter.',quotes) is None


def test_materially_changed_direct_quote_is_never_treated_as_exact():
    claims=[{'evidence':[{'id':'s0','quote':'ils les insultent, ils les agressent à moitié'}]}]
    assert engine.quotation_problem('La personne dit : « insultés, ils les agressent à moitié ».',claims)=='narrative_quotation_not_exact'
    assert engine.quotation_problem('La personne rapporte : « ils les insultent, ils les agressent à moitié ».',claims) is None


@pytest.mark.parametrize('supported',[True,False])
def test_actor_repair_keeps_sources_and_never_accepts_an_unverified_rewrite(tmp_path,monkeypatch,supported):
    source="Le problème avec les ministres, c’est qu’ils ne nous écoutent pas."
    claim={'id':'c0','speaker':'a','kind':'argument','discourse':'own',
        'text':'Les ministres ne sont pas entendus.','evidence':[{'id':'s0','quote':source}]}
    row={'id':'s0','speaker_id':'a','text':source,'start_ms':0,'end_ms':5000}
    before=copy.deepcopy(claim)
    monkeypatch.setattr(engine,'call_json',lambda *a,**k:{'text':'La personne reproche aux ministres de ne pas les écouter.'})
    monkeypatch.setattr(engine,'verify',lambda *a,**k:{'c0':dict.fromkeys(['meaning','modality','attribution','relation'],'supported' if supported else 'not_explicit')})
    assert engine.repair_role({'workspace':str(tmp_path),'utterances':[row]},claim,{'s0':row},[row])==supported
    assert claim['evidence']==before['evidence'] and claim['speaker']==before['speaker']
    assert (claim['text']!=before['text'])==supported


def test_model_aliases_change_only_speaker_metadata_never_quotes():
    key='directory-00000000-0000-0000-0000-000000000001'
    request={'utterances':[{'speaker_id':key},{'speaker_id':None}]}
    payload={'speaker':key,'sources':[{'speaker':key,'quote':key}], 'voice_bindings':{'V1':key}}
    changed=engine.model_aliases(request,payload)
    assert changed['speaker']==changed['sources'][0]['speaker']=='V1'
    assert changed['sources'][0]['quote']==key and changed['voice_bindings']=={'V1':'V1'}
    assert payload['speaker']==key


def test_compact_semantic_context_retains_original_ids_and_voice_boundaries():
    rows=[{'id':'s0','speaker_id':'a','start_ms':0,'end_ms':1000,'text':'Première phrase.'},
        {'id':'s1','speaker_id':'a','start_ms':1100,'end_ms':2000,'text':'Suite du même propos.'},
        {'id':'s2','speaker_id':'b','start_ms':2100,'end_ms':3000,'text':'Une objection.'}]
    context=engine.semantic_context({'evidence':[{'id':'s1'}]},rows)
    assert context['turns'][0]['ids']==['s0','s1'] and context['turns'][1]['ids']==['s2']
    assert context['turns'][0]['text']=='Première phrase. Suite du même propos.'


def test_distinct_arguments_with_identical_quote_are_never_silently_deduplicated(sample):
    _,claims=sample;a=copy.deepcopy(claims[0]);b=copy.deepcopy(a)
    b.update(id='another',text='Une autre information distincte issue du même passage.')
    duplicate=copy.deepcopy(a);duplicate['id']='repeat'
    assert [c['id'] for c in engine.distinct_claims([a,b,duplicate])]==[a['id'],'another']


@pytest.fixture
def sample():
    a='Je propose une expertise du bâtiment avant les travaux pour vérifier les risques sur la toiture.'
    b='Je conteste ce calendrier car la bibliothèque doit rester ouverte pendant les examens.'
    rows=[{'id':'s0','text':a,'speaker_id':'a','start_ms':0,'end_ms':10000,'uncertain':False},
        {'id':'s1','text':b,'speaker_id':'b','start_ms':600000,'end_ms':610000,'uncertain':True}]
    claims=[{'id':'c0','topic':'Travaux','kind':'proposal','discourse':'own','speaker':'a',
        'text':'Une expertise préalable du bâtiment est proposée afin de vérifier les risques.', 'evidence':[{'id':'s0','quote':a}]},
        {'id':'c1','topic':'Travaux','kind':'argument','discourse':'own','speaker':'b',
        'text':'Le maintien de l’ouverture durant les examens motive une objection au calendrier.', 'evidence':[{'id':'s1','quote':b}]}]
    return {'speakers':{'a':'Élodie Exemple','b':'Intervenant 2'},'utterances':rows},claims


def fictional_result(claims):
    return {'strategy':'contextual-topic-paragraphs-v1','claims':claims,'topics':[{'title':'Calendrier des travaux',
        'claims':['c0','c1'],'sentences':[
            {'text':'{{V1}} propose une expertise préalable du bâtiment pour en évaluer les risques.',
             'claim_ids':['c0'],'voice_bindings':{'V1':'a'},'relation':'proposal','machine_verdict':'supported_not_human_verified'},
            {'text':'De son côté, {{V2}} conteste le calendrier en invoquant le maintien de l’ouverture pendant les examens.',
             'claim_ids':['c1'],'voice_bindings':{'V2':'b'},'relation':'statement','machine_verdict':'supported_not_human_verified'}]}],
        'diagnostics':{'summary_length':'standard','omitted_claims':0,'topics_not_written':[],'rejected_claims':0}}


def test_non_consecutive_interventions_become_one_topic_paragraph_with_sentence_links(sample):
    state,claims=sample
    draft=assemble_summary(state,fictional_result(claims))
    point=draft['points'][0]
    assert len(draft['points'])==1 and '\n\n' not in point['summary']
    assert 'Élodie Exemple' in point['summary'] and 'Voix 2' in point['summary']
    assert 'Intervenant 2' not in point['summary'] and 'Argument —' not in point['summary']
    assert point['narrative'][1]['claim_ids']==['c1']
    assert set(point['sources'])=={'s0','s1'} and not draft_issues(draft,state)
    transcript=integral_transcript(state)
    assert len(transcript['points'])==2 and transcript['points'][0]['summary']==state['utterances'][0]['text']
    assert any('incertaines' in warning for warning in draft['to_verify'])


def test_confirmed_directory_name_and_unknown_identity_are_rendered_without_model_invention(sample):
    state,_=sample
    state['utterances'].append({'id':'unknown','speaker_id':None,'text':'Autre voix','start_ms':620000,'end_ms':621000})
    registry=voice_registry(state)
    assert registry['a']['confirmed'] and not registry['b']['confirmed']
    assert render_template('{{V3}} interroge le calendrier.',{'V3':'unattributed'},state)=='Voix inconnue interroge le calendrier.'
    with pytest.raises(ValueError,match='UNKNOWN_VOICE'):render_template('{{V9}}',{},state)


def test_unnamed_voice_keeps_its_stored_number_even_if_turn_order_changes(sample):
    state,_=sample;state['speakers']['b']='Intervenant 7'
    assert voice_registry(state)['b']['label']=='Voix 7'
    state['utterances'].reverse()
    assert voice_registry(state)['b']['label']=='Voix 7'


def test_sentence_mapping_cannot_be_removed_or_rebound_to_a_third_voice(sample):
    state,claims=sample;point=assemble_summary(state,fictional_result(claims))['points'][0]
    point['narrative'][0]['claim_ids']=['missing']
    assert 'narrative_missing_claim' in narrative_problems(point,state)
    point=assemble_summary(state,fictional_result(claims))['points'][0]
    point['narrative'][0]['voice_bindings']={'V1':'b'}
    assert 'narrative_voice_changed' in narrative_problems(point,state)
    point=assemble_summary(state,fictional_result(claims))['points'][0];point['summary']+=' Une conclusion inventée.'
    assert 'narrative_text_changed' in narrative_problems(point,state)


def test_manual_prose_retains_links_and_does_not_keep_machine_verdict(sample):
    state,claims=sample;point=assemble_summary(state,fictional_result(claims))['points'][0]
    manual_narrative(point,'Texte corrigé explicitement par l’opérateur, toujours à relire.')
    assert point['narrative'][0]['claim_ids']==['c0','c1']
    assert point['narrative'][0]['machine_verdict']=='human_edited_requires_review'
    assert not narrative_problems(point,state)


def test_name_refresh_preserves_prose_templates_and_exact_sources(sample):
    state,claims=sample;draft=assemble_summary(state,fictional_result(claims));before=copy.deepcopy(draft)
    state['speakers']['a']='Mme Nom corrigé'
    assert any(i['reason']=='narrative_voice_changed' for i in draft_issues(draft,state))
    updated,changed=propose_attribution_refresh(draft,state)
    assert changed==[0] and 'Mme Nom corrigé' in updated['points'][0]['summary']
    assert not draft_issues(updated,state)
    assert before['points'][0]['claims']==updated['points'][0]['claims']
    assert before['points'][0]['narrative'][0]['template']==updated['points'][0]['narrative'][0]['template']


def test_changed_directory_uuid_refresh_updates_template_binding_only_when_unambiguous(sample):
    state,claims=sample;draft=assemble_summary(state,fictional_result(claims))
    state['speakers']['directory-new']='Nouveau nom confirmé';state['utterances'][0]['speaker_id']='directory-new'
    updated,_=propose_attribution_refresh(draft,state)
    assert updated['points'][0]['narrative'][0]['voice_bindings']=={'V1':'directory-new'}
    assert not draft_issues(updated,state)


def test_new_paragraph_review_export_and_reopen_keep_existing_gate(sample,tmp_path):
    state,claims=sample
    store=SessionStore(tmp_path/'data');sid=store.create('Fixture de rédaction')
    store.save_analysis(sid,state['utterances'],state['speakers'],0)
    draft=assemble_summary(state,fictional_result(claims));store.save_draft(sid,draft)
    with pytest.raises(ValueError,match='HUMAN_REVIEW'):export_session(store,sid,tmp_path/'forbidden.pdf')
    store.approve(sid,'RELECTURE AUTOMATISÉE DE FIXTURE UNIQUEMENT')
    assert export_session(store,sid,tmp_path/'fixture.pdf').is_file()
    docx=export_session(store,sid,tmp_path/'fixture.docx')
    from docx import Document
    assert draft['points'][0]['summary'] in '\n'.join(p.text for p in Document(docx).paragraphs)
    store.close();store=SessionStore(tmp_path/'data')
    try:
        assert store.reviewed_content(sid)[0]['draft']['content']==draft
        store.rename_speaker(sid,'a','Nouveau nom')
        with pytest.raises(ValueError,match='HUMAN_REVIEW'):store.reviewed_content(sid)
    finally:store.close()


def test_paragraph_links_survive_source_split_and_merge(sample,tmp_path):
    state,claims=sample;store=SessionStore(tmp_path/'data');sid=store.create('Fixture de filiation')
    try:
        store.save_analysis(sid,state['utterances'],state['speakers'],0)
        draft=assemble_summary(state,fictional_result(claims));store.save_draft(sid,draft)
        child=store.split_utterance(sid,'s0',5000,state['utterances'][0]['text'].index('avant'))
        split=store.get(sid)
        assert not draft_issues(split['draft']['content'],split)
        assert split['draft']['content']['points'][0]['narrative']==draft['points'][0]['narrative']
        store.merge_utterances(sid,['s0',child]);merged=store.get(sid)
        assert not draft_issues(merged['draft']['content'],merged)
        assert merged['draft']['content']['points'][0]['narrative']==draft['points'][0]['narrative']
    finally:store.close()


def test_exact_quote_does_not_override_contextual_verifier_rejection(monkeypatch,tmp_path,sample):
    state,claims=sample
    monkeypatch.setattr(engine,'call_json',lambda request,label,instruction,inputs,schema,tokens=0:{'checks':{
        item['id']:{'meaning':'not_explicit','modality':'supported','attribution':'supported','relation':'supported'} for item in inputs['items']}})
    checks=engine.verify({'workspace':str(tmp_path)},'fixture-verification',[{'id':'n0','sentence':'Une conclusion non étayée','sources':claims[0]['evidence']}])
    assert checks['n0']['meaning']=='not_explicit'


def test_copied_mistyped_extraction_requires_contextual_rewrite_before_verification(monkeypatch,tmp_path):
    source='Approuvez-vous une expertise du bâtiment avant le lancement des travaux ?'
    calls=[]
    def model(request,label,instruction,inputs,schema,tokens=0):
        calls.append(label)
        if label.startswith('arguments-'):
            result={'claims':[{'topic':'Préparation des travaux','speaker':'a','kind':'proposal','discourse':'own',
                'text':source,'evidence':[{'id':'u0','quote':source}]}]}
        elif label.startswith('source-classify-'):
            assert 'nearby_context' in inputs[0] and inputs[0]['sources'][0]['quote']==source
            result={'classifications':{'c0-0':{'genre':'question','origine':'question_posee_par_le_locuteur'}}}
        elif label.startswith('argument-rephrase-'):
            assert inputs[0]['kind']=='question' and inputs[0]['discourse']=='question'
            result={'notes':{'c0-0':'La personne demande si une expertise préalable du bâtiment est approuvée.'}}
        else:
            result={'checks':{item['id']:dict.fromkeys(['meaning','modality','attribution','relation'],'supported') for item in inputs['items']}}
        from jsonschema import validate
        validate(result,schema);return result
    monkeypatch.setattr(engine,'call_json',model)
    claims,rejected,_=engine.extract({'workspace':str(tmp_path),'utterances':[
        {'id':'s0','text':source,'speaker_id':'a','start_ms':0,'end_ms':10000}]})
    assert calls==['arguments-000','source-classify-000','argument-rephrase-000','argument-check-000']
    assert claims[0]['kind']=='question' and claims[0]['evidence']==[{'id':'s0','quote':source}]
    assert claims[0]['text']!=source and not rejected


def test_source_question_cannot_be_classified_as_a_proposal_by_the_model(monkeypatch,tmp_path):
    from jsonschema import validate,ValidationError
    source='Approuvez-vous cette expertise du bâtiment ?'
    note={'id':'c0','speaker':'a','kind':'context','discourse':'own','text':'Note provisoire',
        'evidence':[{'id':'s0','quote':source}]}
    request={'workspace':str(tmp_path),'utterances':[{'id':'s0','speaker_id':'a','start_ms':0,'end_ms':2000,'text':source}]}
    def wrong(request,label,instruction,inputs,schema,tokens=0):
        result={'classifications':{'c0':{'genre':'proposition','origine':'propos_direct_du_locuteur'}}}
        validate(result,schema);return result
    monkeypatch.setattr(engine,'call_json',wrong)
    with pytest.raises(ValidationError):engine.classify_notes(request,[note],{'s0':request['utterances'][0]},'fixture')


def test_rephrase_does_not_receive_uncited_nearby_facts(monkeypatch,tmp_path):
    source='Je propose une expertise préalable du bâtiment.'
    rows=[{'id':'s0','speaker_id':'a','start_ms':0,'end_ms':2000,'text':source},
        {'id':'s1','speaker_id':'a','start_ms':2100,'end_ms':3000,'text':'Un montant non cité de cinquante mille euros.'}]
    note={'id':'c0','speaker':'a','kind':'proposal','discourse':'own','text':'Note provisoire',
        'evidence':[{'id':'s0','quote':source}]}
    def model(request,label,instruction,inputs,schema,tokens=0):
        assert 'cinquante mille' not in json.dumps(inputs,ensure_ascii=False)
        assert inputs[0]['citations']==[source]
        return {'notes':{'c0':'Une expertise préalable est proposée pour le bâtiment.'}}
    monkeypatch.setattr(engine,'call_json',model)
    engine.rephrase_notes({'workspace':str(tmp_path),'utterances':rows},[note],{u['id']:u for u in rows},'fixture')


def test_no_consensus_from_one_voice_or_similar_opinions(sample):
    _,claims=sample;by={c['id']:c for c in claims};aliases={'V1':'a','V2':'b'}
    sentence={'text':'{{V1}} approuve le calendrier.','claim_ids':['c0'],'relation':'agreement'}
    assert engine.sentence_problem(sentence,by,aliases)=='relation_needs_distinct_voices'
    sentence={'text':'{{V1}} et {{V2}} s’accordent sur les travaux.','claim_ids':['c0','c1'],'relation':'agreement'}
    assert engine.sentence_problem(sentence,by,aliases)=='consensus_not_explicit'


@pytest.mark.parametrize('level',['short','standard','detailed'])
def test_length_profiles_reach_actual_writer_and_omissions_are_accounted(monkeypatch,tmp_path,sample,level):
    state,claims=sample;seen=[]
    def model(request,label,instruction,inputs,schema,tokens=0):
        seen.append(instruction)
        from jsonschema import validate
        validate(result := {'title':'Calendrier des travaux','sentences':[{'text':'{{V1}} propose une expertise préalable du bâtiment pour vérifier les risques.','claim_ids':['c0']}]},schema)
        return result
    monkeypatch.setattr(engine,'call_json',model)
    monkeypatch.setattr(engine,'verify_heading',lambda *a,**k:{'topic_supported':'supported'})
    monkeypatch.setattr(engine,'verify',lambda *a,**k:{'title':dict.fromkeys(['meaning','modality','attribution','relation'],'supported'),
        'n0':dict.fromkeys(['meaning','modality','attribution','relation'],'supported')})
    result=engine.write_topic({'workspace':str(tmp_path),'utterances':state['utterances'],'summary_length':level},
        {'title':'Travaux','claims':['c0','c1']},claims,0)
    assert str(PROFILES[level]['words_per_topic']) in seen[0]
    assert result['claims']==['c0'] and result['omitted'][0]['id']=='c1'


def test_failed_final_entailment_never_yields_a_supported_paragraph(monkeypatch,tmp_path,sample):
    state,claims=sample
    monkeypatch.setattr(engine,'verify_heading',lambda *a,**k:{'topic_supported':'supported'})
    monkeypatch.setattr(engine,'call_json',lambda *a,**k:{'title':'Travaux',
        'sentences':[{'text':'{{V1}} propose une expertise préalable du bâtiment pour vérifier les risques.','relation':'formule_une_proposition','claim_ids':['c0']}]})
    monkeypatch.setattr(engine,'verify',lambda *a,**k:{'n0':{'meaning':'contradicted','modality':'supported','attribution':'supported','relation':'supported'}})
    result=engine.write_topic({'workspace':str(tmp_path),'utterances':state['utterances']},{'title':'Travaux','claims':['c0','c1']},claims,0)
    assert not result['sentences'] and len(result['rejected_attempts'])==2


def test_unsupported_heading_refuses_the_entire_topic(monkeypatch,tmp_path,sample):
    state,claims=sample
    monkeypatch.setattr(engine,'call_json',lambda *a,**k:{'title':'Les travaux ont été votés',
        'sentences':[{'text':'{{V1}} propose une expertise préalable du bâtiment.','claim_ids':['c0']}]})
    monkeypatch.setattr(engine,'verify_heading',lambda *a,**k:{'no_invented_identity_or_decision':'not_explicit'})
    monkeypatch.setattr(engine,'verify',lambda *a,**k:pytest.fail('Un titre refusé ne doit pas livrer son paragraphe'))
    result=engine.write_topic({'workspace':str(tmp_path),'utterances':state['utterances']},{'title':'Travaux','claims':['c0']},claims,0)
    assert not result['sentences'] and len(result['rejected_attempts'])==2


def test_shared_theme_plan_excludes_preliminary_note_titles_and_routes_every_note(monkeypatch,tmp_path,sample):
    state,claims=sample
    claims[0]['topic']='Coût';claims[1]['topic']='Calendrier'
    def model(request,label,instruction,inputs,schema,tokens=0):
        from jsonschema import validate
        assert all('topic' not in note for note in (inputs if isinstance(inputs,list) else inputs['notes']))
        result=({'themes':[{'title':'Travaux de la bibliothèque'}]} if label=='theme-catalogue' else
            {'assignments':{'c0':'t0','c1':'t0'}})
        validate(result,schema);return result
    monkeypatch.setattr(engine,'call_json',model)
    topics,repaired=engine.group_topics({'workspace':str(tmp_path),'utterances':state['utterances']},claims)
    assert topics==[{'title':'Travaux de la bibliothèque','claims':['c0','c1']}] and not repaired


def test_same_voice_anaphora_requires_a_prior_attributed_sentence(sample):
    _,claims=sample;by={c['id']:c for c in claims};aliases={'V1':'a','V2':'b'}
    continuation={'text':'Cette proposition vise à vérifier les risques du bâtiment.','claim_ids':['c0']}
    assert engine.sentence_problem(continuation,by,aliases,{'a'}) is None
    assert engine.sentence_problem(continuation,by,aliases,set())=='unattributed_narrative_assertion'
    assert engine.sentence_problem(continuation,by,aliases,{'b'})=='unattributed_narrative_assertion'
    fact={'text':'Les travaux seront approuvés demain.','claim_ids':['c0']}
    assert engine.sentence_problem(fact,by,aliases,{'a'})=='unattributed_narrative_assertion'


def test_implicit_voice_binding_is_checked_after_source_attribution_changes(sample):
    state,claims=sample
    result=fictional_result(claims)
    result['topics'][0]['sentences'][1]={'text':'Cette proposition porte sur les risques du bâtiment.',
        'claim_ids':['c0'],'implicit_speaker':'a','voice_bindings':{},'relation':'statement',
        'machine_verdict':'supported_not_human_verified'}
    result['topics'][0]['claims']=['c0']
    point=assemble_summary(state,result)['points'][0]
    assert not narrative_problems(point,state)
    point['narrative'][1]['implicit_speaker']='b'
    assert 'narrative_voice_changed' in narrative_problems(point,state)


def test_textual_consensus_is_checked_without_a_model_relation_tag(sample):
    _,claims=sample
    sentence={'text':'{{V1}} et {{V2}} s’accordent sur le calendrier.','claim_ids':['c0','c1']}
    assert engine.sentence_problem(sentence,{c['id']:c for c in claims},{'V1':'a','V2':'b'})=='consensus_not_explicit'


def test_instruction_word_leaking_into_prose_is_refused(sample):
    _,claims=sample
    assert engine.sentence_problem({'text':'EXACT {{V1}} propose une expertise du bâtiment.','claim_ids':['c0']},
        {c['id']:c for c in claims},{'V1':'a','V2':'b'})=='narrative_instruction_artifact'


def test_real_native_false_positive_global_budget_reassigned_to_roof_is_refused():
    source='Les travaux de la bibliothèque sont estimés à vingt mille euros. Je propose de commencer par réparer la toiture.'
    claims=[{'evidence':[{'id':'s0','quote':source}]}]
    bad='La personne propose les travaux de réparation de la toiture de la bibliothèque, estimés à vingt mille euros.'
    assert engine.financial_clause_problem(bad,claims)=='financial_scope_requires_literal_source'
    good='La personne indique : « Les travaux de la bibliothèque sont estimés à vingt mille euros. » et propose de commencer par la toiture.'
    assert engine.financial_clause_problem(good,claims) is None
    altered='La personne indique : « La toiture est estimée à vingt mille euros. »'
    assert engine.financial_clause_problem(altered,claims)=='financial_scope_requires_literal_source'


def test_invented_political_identity_requires_words_in_source_not_just_a_model_verdict():
    claims=[{'evidence':[{'id':'s0','quote':'Je propose de réparer la bibliothèque.'}]}]
    assert engine.identity_problem('Proposition du parti Exemple pour la bibliothèque',claims)=='unsupported_proper_name'
    assert engine.identity_problem('Proposition du parti exemple pour la bibliothèque',claims)=='unsupported_political_identity'
    assert engine.identity_problem('Travaux de la bibliothèque',claims) is None


def test_lexicon_only_authorizes_a_name_when_a_variant_is_present_in_sources():
    claims=[{'evidence':[{'id':'s0','quote':'La médiathèque Simone Veille reste ouverte.'}]}]
    lexicon=[{'canonical':'Simone Veil','variants':['Simone Veille']}]
    assert engine.identity_problem('Médiathèque Simone Veil',claims,lexicon) is None
    assert engine.identity_problem('Médiathèque Simone Veil',[{'evidence':[{'quote':'La bibliothèque reste ouverte.'}]}],lexicon)=='unsupported_proper_name'


def test_absence_of_evaluation_cannot_be_invented_from_an_excerpt():
    claims=[{'evidence':[{'id':'s0','quote':'Ce sont des blocus qui peuvent durer plusieurs semaines.'}]}]
    assert engine.absence_problem('La personne décrit des blocus sans évaluer leur impact.',claims)=='unsupported_absence_added'
    assert engine.absence_problem('La personne décrit la durée des blocus.',claims) is None


def test_real_unresolved_denial_is_not_used_as_a_standalone_position():
    assert engine.unresolved_referent({'evidence':[{'quote':'Mais vous non plus.'},{'quote':"Je n’ai jamais eu cette prétention."}]})
    assert not engine.unresolved_referent({'evidence':[{'quote':"Je propose de reporter les travaux aux vacances."}]})


def test_contesting_a_previous_assertion_requires_both_source_voices(sample):
    _,claims=sample
    text='{{V2}} conteste cette affirmation en proposant de modifier le calendrier.'
    assert engine.sentence_problem({'text':text,'claim_ids':['c1']},{c['id']:c for c in claims},{'V1':'a','V2':'b'})=='relation_needs_distinct_voices'


def test_common_speaker_anaphora_keeps_the_same_explicit_voice_binding(sample):
    _,claims=sample
    sentence={'text':'Ce locuteur exprime une demande d’expertise du bâtiment.','claim_ids':['c0']}
    assert engine.sentence_problem(sentence,{c['id']:c for c in claims},{'V1':'a'},previous_voices={'a'}) is None


def test_reported_question_cannot_be_followed_by_an_assertion_of_the_same_voice(sample):
    _,claims=sample;c=copy.deepcopy(claims[0]);c.update(kind='question',discourse='question')
    text='{{V1}} pose la question des principes, affirmant qu’ils ne sont pas respectés.'
    assert engine.sentence_problem({'text':text,'claim_ids':['c0']},{'c0':c},{'V1':'a'})=='question_changed_to_assertion'


def test_local_lexicon_roundtrip_and_ambiguous_graphies_refused():
    text='Médiathèque Simone Veil | médiathèque Simone Veille\nConseil municipal'
    assert lexicon_text(lexicon_from_text(text))==text
    with pytest.raises(ValueError,match='ambiguë'):lexicon_from_text('Veil | Veille\nVeille')
    with pytest.raises(ValueError):lexicon_from_text('{{V1}} | Jeanne')


def test_ui_length_modes_and_local_lexicon_persist_without_any_review(tmp_path,monkeypatch):
    from PySide6.QtWidgets import QApplication,QMessageBox,QTextEdit,QDialogButtonBox
    from PySide6.QtCore import QTimer
    from notetaker.ui.window import MainWindow
    app=QApplication.instance() or QApplication([])
    win=MainWindow(tmp_path/'ui')
    sid=win.store.create('Séance de fixture');win.sid=sid;win.load_session()
    try:
        win.summary_length.setCurrentIndex(win.summary_length.findData('detailed'))
        win.save_details();win.load_session()
        assert win.summary_length.currentData()=='detailed'
        win.document_mode.setCurrentIndex(win.document_mode.findData('transcript'))
        assert not win.summary_length.isEnabled()
        win.document_mode.setCurrentIndex(win.document_mode.findData('summary'))
        assert win.summary_length.isEnabled()
        def fill_lexicon():
            dialog=app.activeModalWidget()
            dialog.findChild(QTextEdit).setPlainText('Médiathèque Simone Veil | Simone Veille')
            dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.Save).click()
        QTimer.singleShot(0,fill_lexicon);win.edit_lexicon()
        assert win.store.get(sid)['metadata']['lexicon'][0]['canonical']=='Médiathèque Simone Veil'
        assert win.store.get(sid)['draft'] is None
    finally:win.close();app.processEvents()


def test_ui_manual_paragraph_edit_keeps_sources_and_invalidates_review(tmp_path,sample):
    from PySide6.QtWidgets import QApplication
    from notetaker.ui.window import MainWindow
    app=QApplication.instance() or QApplication([])
    state,claims=sample;win=MainWindow(tmp_path/'ui')
    sid=win.store.create('Fixture de modification')
    win.store.save_analysis(sid,state['utterances'],state['speakers'],0)
    draft=assemble_summary(state,fictional_result(claims));win.store.save_draft(sid,draft)
    win.store.approve(sid,'RELECTURE DE FIXTURE UNIQUEMENT')
    win.sid=sid;win.load_session()
    try:
        win.point_text.setPlainText('L’opérateur a corrigé ce paragraphe en conservant ses sources.')
        win.save_draft();stored=win.store.get(sid)['draft']
        assert stored['review'] is None
        assert stored['content']['points'][0]['narrative'][0]['claim_ids']==['c0','c1']
        assert stored['content']['points'][0]['narrative'][0]['machine_verdict']=='human_edited_requires_review'
        assert not draft_issues(stored['content'],win.store.get(sid))
    finally:win.close();app.processEvents()


def test_sentence_source_browser_plays_the_matching_nonconsecutive_passage(sample):
    from PySide6.QtWidgets import QApplication
    from notetaker.ui.evidence import NarrativeSources
    app=QApplication.instance() or QApplication([])
    state,claims=sample;played=[]
    point=assemble_summary(state,fictional_result(claims))['points'][0]
    dialog=NarrativeSources(point,state,played.append)
    dialog.sentences.setCurrentRow(1);app.processEvents();dialog.listen()
    assert played==['s1'] and dialog.context.toPlainText()==state['utterances'][1]['text']
    assert '00:10:00' in dialog.sources.item(0,0).text()
    dialog.close()


def test_ui_flagged_passage_is_findable_and_playable_without_review(tmp_path,sample,monkeypatch):
    from PySide6.QtWidgets import QApplication,QPushButton,QTableWidget
    from PySide6.QtCore import QTimer
    from notetaker.ui.window import MainWindow
    app=QApplication.instance() or QApplication([])
    state,claims=sample;win=MainWindow(tmp_path/'ui');sid=win.store.create('Passages à vérifier')
    win.store.save_analysis(sid,state['utterances'],state['speakers'],0)
    draft=assemble_summary(state,fictional_result(claims));draft['generation_diagnostics']['unreliable_passages']=[
        {'source_id':'s1','start_ms':600000,'end_ms':610000,'reasons':['information_rejected','voice_or_timing_uncertain']}]
    win.store.save_draft(sid,draft);win.sid=sid;win.load_session();played=[]
    monkeypatch.setattr(win,'play_source',played.append)
    def inspect():
        dialog=app.activeModalWidget()
        assert dialog.findChild(QTableWidget).item(0,0).text()=='10:00'
        next(b for b in dialog.findChildren(QPushButton) if b.text()=='Écouter ce passage').click()
        dialog.close()
    try:
        QTimer.singleShot(0,inspect);win.show_unreliable_sources()
        assert played==['s1'] and win.store.get(sid)['draft']['review'] is None
    finally:win.close();app.processEvents()
