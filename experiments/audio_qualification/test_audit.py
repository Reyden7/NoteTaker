"""Known artificial truths for the audit; not engine accuracy measurements."""
import copy
import tempfile
import unittest
from pathlib import Path
from .core import tokens,approve,digest,QualificationError,update_zone
from .normalization import normalize,numeric_prefixes
from .audit_metrics import qualified_activity,audit_boundaries,compare_baseline
from .scoring import evaluate,lexical_clock,words_in_zone
from .test_scoring import reference,dataset
from .wer_plan import prepare,approve_block,validate_plan


class FrenchNormalizationTests(unittest.TestCase):
    def normalized(self,text):return normalize(tokens(text),numeric_prefixes(text))['tokens']
    def test_names_ligatures_and_conventional_accents_only(self):
        self.assertEqual(self.normalized('Parcours sup, voeux, selection, évènement'),self.normalized('Parcoursup vœux sélection événement'))
        self.assertNotEqual(self.normalized('parcoursuc'),self.normalized('parcoursup'))
        for a,b in [('a','à'),('ou','où'),('sur','sûr'),('du','dû'),('élevé','élève'),('pour quoi','pourquoi'),('acceuille','accueille'),('uner','une')]:
            self.assertNotEqual(self.normalized(a),self.normalized(b),(a,b))
    def test_negations_and_repetitions_are_not_erased(self):
        for word in ('pas','plus','jamais','non','ni'):
            self.assertNotEqual(self.normalized('je ne dis '+word),self.normalized('je ne dis'))
        self.assertEqual(self.normalized("n'est pas"),['ne','est','pas'])
        self.assertNotEqual(self.normalized("n'est pas vrai"),self.normalized("n'est vrai"))
        self.assertNotEqual(self.normalized('je je'),self.normalized('je'))
    def test_apostrophes_keep_all_components(self):
        self.assertEqual(self.normalized('qu’avant'),self.normalized('que avant'))
        self.assertEqual(self.normalized("s'il"),self.normalized('si il'))
        self.assertEqual(self.normalized("d'aujourd'hui"),self.normalized("de aujourd'hui"))
        self.assertNotEqual(self.normalized("l'école"),self.normalized('la école'))
    def test_numbers_signs_units_and_ambiguity(self):
        for a,b in [('21','vingt-et-un'),('71','soixante et onze'),('80','quatre vingts'),('200','deux cents'),('2026','deux mille vingt six'),('5h','cinq heures')]:
            self.assertEqual(self.normalized(a),self.normalized(b),(a,b))
        self.assertEqual(self.normalized('-5'),self.normalized('moins cinq'))
        self.assertNotEqual(self.normalized('-5'),self.normalized('5'))
        self.assertEqual(self.normalized('12,5'),['12','5'])
        self.assertEqual(self.normalized('007'),['007'])
        self.assertEqual(self.normalized('10000'),['10000'])
        self.assertEqual(self.normalized('recettes'),['recettes'])
    def test_transformations_have_strict_source_indices(self):
        n=normalize(tokens('parcours sup 21'))
        self.assertEqual(n['provenance'][0]['source_indices'],[0,1])
        self.assertTrue(all(r['source_indices']==[2] for r in n['provenance'][1:]))


class AuditTests(unittest.TestCase):
    def test_baseline_change_is_not_claimed_as_engine_improvement(self):
        r=evaluate(reference(),dataset());old=copy.deepcopy(r)
        old['wer_plan']={'blocks':[{'id':'z1-P01','start':0,'end':2,'first_token':0,'last_token':1,'classification':'sequential'}]}
        r['wer_plan']=copy.deepcopy(old['wer_plan']);r['wer_plan']['blocks'][0]['last_token']=2
        c=compare_baseline(r,old)
        self.assertFalse(c['same_scoring_selection'])
        self.assertEqual(c['portion_changes'][0]['fields']['last_token'],{'before':1,'after':2})
    def test_unknown_gaps_excluded_without_becoming_silence(self):
        p=reference();data=dataset()
        # Actual word/voice at .1-.9, but prediction extends into unknown activity.
        for c in data['chains'].values():c['diarization']=[{'start':0,'end':2,'speaker':'hA'}]
        before=digest(p);r=evaluate(p,data)['results']['small']
        self.assertAlmostEqual(r['diarization']['false alarm'],1.2)
        self.assertAlmostEqual(r['diarization_qualified']['false alarm'],0)
        self.assertAlmostEqual(r['diarization_qualified']['DER'],0)
        self.assertAlmostEqual(r['diarization_qualified']['total'],.8)
        self.assertEqual(digest(p),before)
        self.assertEqual(r['diarization_qualified']['excluded_unknown_activity'][0]['start'],0)
    def test_explicit_whole_silence_counts_false_alarms(self):
        p=reference();p['zones'][1]['silence']=True
        p=approve(p,'z2','diarization','Test',True);data=dataset()
        for c in data['chains'].values():c['diarization'].append({'start':4,'end':5,'speaker':'hA'})
        r=evaluate(p,data)['results']['small']['diarization_qualified']
        self.assertAlmostEqual(r['false alarm'],1)
    def test_qualified_der_keeps_overlap_and_global_mapping(self):
        p=reference();p['zones'][0]=update_zone(p['zones'][0],turns=[{'start':0,'end':2,'speaker':'vA'},{'start':1,'end':2,'speaker':'vB'}])
        p=approve(p,'z1','diarization','Test',True)
        data=dataset()
        for c in data['chains'].values():c['diarization']=[{'start':0,'end':2,'speaker':'hA'}]
        r=evaluate(p,data)['results']['small']['diarization_qualified']
        self.assertAlmostEqual(r['total'],3);self.assertAlmostEqual(r['DER'],1/3)
        self.assertEqual(r['collar_seconds'],0)
    def test_wer_gap_speech_does_not_supply_an_identity(self):
        from .test_wer_plan import overlapped
        p,data=overlapped();plan=prepare(p,data)
        gap=next(b for b in plan['blocks'] if b['kind']=='uncovered')
        gap.update(first_token=0,last_token=1)
        plan=approve_block(p,plan,gap['id'],'Test',True)
        masks,excluded,basis=qualified_activity(p,plan)
        self.assertTrue(any(e['start']==gap['start'] and e['end']==gap['end'] for e in excluded))
        self.assertFalse(basis)
    def test_explicit_portion_silence_can_extend_activity_mask(self):
        from .test_wer_plan import overlapped
        p,data=overlapped();plan=prepare(p,data);b=next(b for b in plan['blocks'] if b['kind']=='uncovered')
        b.update(first_token=0,last_token=0,classification='silence');plan=approve_block(p,plan,b['id'],'Test',True)
        masks,excluded,basis=qualified_activity(p,plan)
        self.assertTrue(basis)
        self.assertFalse(any(e['start']==b['start'] and e['end']==b['end'] for e in excluded))
    def test_sixty_selected_vs_ninety_one_hypothesis_is_a_selection_alert(self):
        p=reference();p['zones'][0]=update_zone(p['zones'][0],end=100,verbatim=' '.join('mot'+str(i) for i in range(99)),turns=[{'start':0,'end':100,'speaker':'vA'}])
        p['audio']['duration']=100;p['zones']=p['zones'][:1]
        for domain in ('text','diarization'):p=approve(p,'z1',domain,'Test',True)
        data=dataset();words=[{'word':'mot'+str(i),'start':i,'end':i+.4} for i in range(91)]
        for c in data['chains'].values():c['asr']=[{'start':0,'end':91,'text':' '.join(w['word'] for w in words),'words':words}]
        unit={**p['zones'][0],'id':'E11-P01','source_zone':'z1','start':0,'end':91,'reference_token_range':[0,60]}
        before=digest(p);audit=audit_boundaries(p,data,[unit]);a=audit['portions'][0]
        self.assertEqual(a['reference_words'],60);self.assertEqual(a['engines']['large']['hypothesis_words'],91)
        self.assertEqual(len(a['engines']['large']['matching_unselected_human_tokens_inside']),31)
        self.assertEqual(audit['unselected_reference_runs'][0]['words'],39)
        self.assertEqual(digest(p),before)
    def test_midpoint_crossing_is_visible_without_changing_selection(self):
        p=reference();d=dataset();u={**p['zones'][0],'source_zone':'z1','reference_token_range':[0,2],'end':.8}
        before=digest(p);a=audit_boundaries(p,d,[u])['portions'][0]
        self.assertEqual(a['engines']['large']['words_crossing_boundaries'][0]['word'],'mairie')
        self.assertEqual(a['engines']['large']['hypothesis_words'],2)
        self.assertEqual(digest(p),before)
    def test_strict_score_unchanged_and_normalized_separate(self):
        p=reference();p['zones'][0]=update_zone(p['zones'][0],verbatim='parcours sup');p=approve(p,'z1','text','Test',True)
        data=dataset()
        for c in data['chains'].values():c['asr']=[{'start':.1,'end':.9,'text':'Parcoursup','words':[{'word':'Parcoursup','start':.1,'end':.9}]}]
        r=evaluate(p,data)['results']['small']
        self.assertEqual(r['transcription']['WER'],1)
        self.assertEqual(r['transcription_normalized']['WER'],0)
        self.assertEqual(r['transcription']['reference_words'],2)
        self.assertEqual(r['transcription_normalized']['reference_words'],1)
    def test_sign_on_first_selected_token_is_not_lost(self):
        p=reference();p['zones'][0]=update_zone(p['zones'][0],verbatim='-5');p=approve(p,'z1','text','Test',True)
        data=dataset()
        for c in data['chains'].values():c['asr']=[{'start':.1,'end':.9,'text':'5','words':[{'word':'5','start':.1,'end':.9}]}]
        r=evaluate(p,data)['results']['small']
        self.assertEqual(r['transcription']['WER'],0)  # historical punctuation policy
        self.assertGreater(r['transcription_normalized']['WER'],0)


if __name__=='__main__':unittest.main()
