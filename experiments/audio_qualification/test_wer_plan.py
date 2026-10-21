"""Regression checks: artificial truth fixtures, plus frozen E11/E12 diagnostics."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from .core import approve,update_zone,digest,QualificationError,WORK
from .test_scoring import project,dataset,reference
from .scoring import evaluate
from .wer_plan import prepare,coverage,overlaps,approve_block,approved,PlanStore,validate_plan,selection_tokens


def overlapped():
    p=reference();p['zones'][0]['end']=3
    p['zones'][0]['reviews']={d:None for d in p['zones'][0]['reviews']}
    p['zones'][0]['verbatim']='Bonjour mairie oui'
    p['zones'][0]['turns']=[{'start':.1,'end':2,'speaker':'vA'},{'start':1,'end':2.8,'speaker':'vB'}]
    for d in ('text','diarization'):p=approve(p,'z1',d,'Fixture humaine',True)
    data=dataset()
    for c in data['chains'].values():
        c['asr']=[{'start':.1,'end':2.7,'text':'Bonjour mairie oui','words':[
            {'word':' Bonjour','start':.1,'end':.4},{'word':' mairie','start':1.2,'end':1.5},{'word':' oui','start':2.2,'end':2.7}]}]
    return p,data


class WERPlanTests(unittest.TestCase):
    def test_two_reviews_are_sufficient_without_human_word_times(self):
        p=reference();self.assertEqual(p['zones'][0]['words'],[])
        result=evaluate(p,dataset());self.assertEqual(result['results']['small']['transcription']['WER'],0)
        self.assertEqual(result['coverage']['word_timing_zones'],0)
    def test_global_tag_does_not_exclude_a_sequential_reviewed_zone(self):
        p=reference();p['zones'][0]['tags']=['chevauchement']
        self.assertEqual(overlaps(p['zones'][0]),[])
        self.assertEqual(evaluate(p,dataset())['results']['small']['transcription']['WER'],0)
    def test_overlaps_are_local_and_proposals_not_scored_without_consent(self):
        p,d=overlapped();before=digest(p);plan=prepare(p,d)
        self.assertEqual(plan['coverage'][0]['real_human_overlaps'],[[1,2]])
        self.assertTrue(any(b['start']==.1 and b['end']==1 for b in plan['blocks']))
        self.assertTrue(all(b['approval'] is None for b in plan['blocks']))
        self.assertIsNone(evaluate(p,d,wer_plan=plan)['results']['small']['transcription']['WER'])
        self.assertEqual(digest(p),before)
    def test_approved_sequential_portion_scores_without_word_annotation(self):
        p,d=overlapped();plan=prepare(p,d);b=next(b for b in plan['blocks'] if b['start']==.1)
        b.update(first_token=0,last_token=1)
        with self.assertRaises(QualificationError):approve_block(p,plan,b['id'],'Test',False)
        plan=approve_block(p,plan,b['id'],'Test',True)
        r=evaluate(p,d,wer_plan=plan)
        self.assertEqual(r['results']['small']['transcription']['WER'],0)
        self.assertEqual(r['results']['small']['transcription']['reference_words'],1)
        self.assertEqual(r['coverage']['WER_eligible_portions'],1)
        self.assertGreater(r['coverage']['WER_pending_portions'],0)
        self.assertEqual(p['zones'][0]['words'],[])
    def test_real_overlap_cannot_be_validated_as_sequential(self):
        p,d=overlapped();plan=prepare(p,d);b=next(b for b in plan['blocks'] if b['start']==.1)
        b['end']=1.1
        with self.assertRaises(QualificationError):approve_block(p,plan,b['id'],'Test',True)
    def test_duplicate_reference_words_cannot_be_counted_twice(self):
        p,d=overlapped();plan=prepare(p,d);b=next(b for b in plan['blocks'] if b['start']==.1);b.update(first_token=0,last_token=1)
        plan=approve_block(p,plan,b['id'],'Test',True);other=next(b for b in plan['blocks'] if b['start']==2)
        other.update(first_token=0,last_token=1)
        with self.assertRaises(QualificationError):approve_block(p,plan,other['id'],'Test',True)
    def test_plan_becomes_stale_after_any_reference_revision(self):
        p,d=overlapped();plan=prepare(p,d);p['zones'][0]['notes'].append({'text':'nouvelle revue'})
        with self.assertRaises(QualificationError):validate_plan(p,plan)
    def test_approval_cannot_be_copied_to_a_different_reference(self):
        p,d=overlapped();plan=prepare(p,d);b=next(b for b in plan['blocks'] if b['start']==.1);b.update(first_token=0,last_token=1)
        plan=approve_block(p,plan,b['id'],'Test',True)
        p['zones'][0]['notes'].append({'text':'nouvelle révision'});plan['reference_sha256']=digest(p)
        with self.assertRaises(QualificationError):validate_plan(p,plan)
    def test_sidecar_history_never_overwrites_an_earlier_plan(self):
        p,d=overlapped();plan=prepare(p,d)
        with tempfile.TemporaryDirectory(dir=WORK) as temporary:
            self.assertTrue(Path(temporary).resolve().is_relative_to(WORK.resolve()))
            store=PlanStore(Path(temporary)/'plan.sqlite');rid=store.save(p,plan,None)
            b=next(b for b in plan['blocks'] if b['start']==.1);b.update(first_token=0,last_token=1)
            newer=approve_block(p,plan,b['id'],'Test',True);rid2=store.save(p,newer,rid)
            self.assertNotEqual(rid,rid2);self.assertEqual(store.load(p),(rid2,newer))
            with self.assertRaises(QualificationError):store.save(p,newer,rid)
    def test_human_selection_maps_to_whole_words_without_engine_text(self):
        self.assertEqual(selection_tokens("Bonjour à l’école.",11,18),(2,3))
    def test_frozen_E12_tail_is_reported_and_original_reference_not_modified(self):
        pointer=WORK/'wer-correction/current-audit.txt'
        if not pointer.is_file():self.skipTest('Frozen local human reference unavailable')
        folder=Path(pointer.read_text(encoding='utf-8'));p=json.loads((folder/'reference-originale.json').read_text(encoding='utf-8'))
        from .core import load_dataset
        before=digest(p);info=coverage(p,load_dataset(p));e12=next(d for d in info if d['zone']=='E12')
        tail=e12['uncovered'][-1]
        self.assertAlmostEqual(tail['start'],1225.251);self.assertAlmostEqual(tail['end'],1237.58)
        self.assertAlmostEqual(tail['duration'],12.329);self.assertTrue(tail['speech_detected_by'])
        self.assertEqual(digest(p),before)


if __name__=='__main__':unittest.main()
