"""Artificial fixtures only: workflow safety, never measured engine quality."""
import copy
import tempfile
import unittest
import wave
from pathlib import Path
from .core import digest,read,sha,QualificationError,review_valid
from .test_scoring import reference,dataset
from .test_wer_plan import overlapped
from .wer_plan import prepare,approve_block,approved,load_saved_plan,PlanStore
from .corrections import add_reviewed_gap,carry_unchanged_plan,TaskLog,read_task_log,operator_summary
from .municipal import register_source,select_excerpts,run_benchmark,write_new
from .sampling import proposals,select


class CorrectionWorkflowTests(unittest.TestCase):
    def test_gap_is_explicit_and_preserves_exact_text_and_existing_turns(self):
        p=reference();before=digest(p);old=copy.deepcopy(p['zones'][0]);turn={'start':.9,'end':1.6,'speaker':'vB'}
        with self.assertRaises(QualificationError):add_reviewed_gap(p,'z1',.9,2,[turn],'Test',False)
        new=add_reviewed_gap(p,'z1',.9,2,[turn],'Test',True)
        self.assertEqual(digest(p),before);z=new['zones'][0]
        self.assertEqual(z['verbatim'],old['verbatim']);self.assertEqual(z['reviews']['text'],old['reviews']['text'])
        self.assertIn(old['turns'][0],z['turns']);self.assertTrue(review_valid(z,'diarization',new['audio']['sha256']))
        self.assertEqual(z['reviews']['diarization']['incremental_review']['base_review'],old['reviews']['diarization'])
    def test_cannot_overwrite_existing_activity_or_invent_identity(self):
        p=reference()
        with self.assertRaises(QualificationError):add_reviewed_gap(p,'z1',.5,1,[{'start':.5,'end':1,'speaker':'vB'}],'Test',True)
        with self.assertRaises(QualificationError):add_reviewed_gap(p,'z1',.9,2,[{'start':1,'end':2,'speaker':'inventée'}],'Test',True)
    def test_unchanged_plan_only_carried_after_operator_confirmation(self):
        p,d=overlapped();plan=prepare(p,d);b=next(b for b in plan['blocks'] if b['start']==.1);b.update(first_token=0,last_token=1)
        plan=approve_block(p,plan,b['id'],'Premier annotateur',True);old=digest(plan)
        new=add_reviewed_gap(p,'z1',0,.1,[{'start':.01,'end':.08,'speaker':'vB'}],'Correction',True)
        with self.assertRaises(QualificationError):carry_unchanged_plan(p,new,plan,'Test',False)
        carried,invalid=carry_unchanged_plan(p,new,plan,'Correction',True)
        self.assertFalse(invalid);self.assertEqual(digest(plan),old)
        approved_block=next(b for b in carried['blocks'] if approved(b))
        self.assertEqual(approved_block['approval']['carried_forward']['original_approval']['reviewer'],'Premier annotateur')
        self.assertEqual(approved_block['approval']['carried_forward']['by'],'Correction')
    def test_new_real_overlap_does_not_receive_an_old_wer_approval(self):
        p,d=overlapped();plan=prepare(p,d);b=next(b for b in plan['blocks'] if b['kind']=='uncovered' and b['start']==0);b.update(first_token=0,last_token=1)
        plan=approve_block(p,plan,b['id'],'Test',True)
        new=add_reviewed_gap(p,'z1',0,.1,[{'start':.01,'end':.09,'speaker':'vA'},{'start':.02,'end':.08,'speaker':'vB'}],'Test',True)
        carried,invalid=carry_unchanged_plan(p,new,plan,'Test',True)
        self.assertEqual(len(invalid),1);self.assertFalse(any(approved(b) for b in carried['blocks']))
    def test_plans_are_isolated_by_project_workspace(self):
        p,d=overlapped()
        with tempfile.TemporaryDirectory() as tmp:
            a=copy.deepcopy(p);b=copy.deepcopy(p);a['lab_workspace']=str(Path(tmp)/'a');b['lab_workspace']=str(Path(tmp)/'b')
            store=PlanStore(Path(a['lab_workspace'])/'decoupages-wer.sqlite');rid=store.save(a,prepare(a,d),None)
            self.assertEqual(load_saved_plan(a)[0],rid);self.assertEqual(load_saved_plan(b),(None,None))
    def test_workload_counts_protocol_tasks_once_and_separates_important_reports(self):
        p=reference();task={'id':'task','zone':'z1','start':0,'end':2}
        with tempfile.TemporaryDirectory() as tmp:
            log=TaskLog(Path(tmp)/'tasks.sqlite');log.append(p,task,'Test','deferred',2)
            log.append(p,task,'Test','corrected',3);log.append(p,task,'Test','important_attribution',4,'Proposition attribuée à une autre voix',['small'])
            summary=operator_summary(read_task_log(p,log.path))
            self.assertEqual(summary['protocol_tasks_corrected'],1);self.assertEqual(summary['protocol_tasks_deferred'],0)
            self.assertEqual(summary['important_attribution_reports']['small'],1);self.assertEqual(summary['important_attribution_reports']['large'],0)
            self.assertEqual(summary['operator_elapsed_seconds'],9)


class MunicipalProtocolTests(unittest.TestCase):
    def test_import_is_an_immutable_copy_and_never_reuses_an_existing_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            original=Path(tmp)/'recording.wav'
            with wave.open(str(original),'wb') as w:w.setparams((1,2,16000,0,'NONE','not compressed'));w.writeframes(bytes(32000))
            h=sha(original);folder=Path(tmp)/'new'
            result=register_source(original,folder,'technical_test','Fixture technique')
            self.assertEqual(sha(result['source']['path']),h);self.assertEqual(sha(original),h)
            with self.assertRaises(QualificationError):register_source(original,folder,'real','autre')
    def test_six_blank_samples_do_not_invent_words_speakers_or_votes(self):
        z=select_excerpts(720)
        self.assertEqual(len(z),6);self.assertTrue(all(not t['verbatim'] and not t['turns'] and not any(t['reviews'].values()) for t in z))
        self.assertTrue(all(a['end']<=b['start'] for a,b in zip(z,z[1:])))
    def test_failed_first_engine_blocks_later_stages_and_keeps_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);audio=folder/'audio.wav'
            with wave.open(str(audio),'wb') as w:w.setparams((1,2,16000,0,'NONE','not compressed'));w.writeframes(bytes(32000))
            write_new(folder/'audio.json',{'path':str(audio),'sha256':sha(audio),'duration':1})
            write_new(folder/'source.json',{'protected':{}});calls=[]
            def failure(*args,**kwargs):calls.append(args);return {'status':'failed'}
            with self.assertRaises(QualificationError):run_benchmark(folder,'cuda',failure)
            self.assertEqual(len(calls),1);self.assertFalse(list(folder.glob('runs/*/ready.json')));self.assertTrue(audio.exists())
    def test_sampling_keywords_are_hypotheses_and_cannot_replace_validated_text(self):
        p=reference();d=dataset();d['chains']['large']['asr'][0]['text']='nous proposons de voter'
        hints=proposals(p,d)
        self.assertTrue(any('ASR' in h['origin'] for h in hints))
        with self.assertRaises(QualificationError):select(p,hints[:1])
        empty=copy.deepcopy(p)
        for z in empty['zones']:z.update(verbatim='',turns=[],words=[],reviews={k:None for k in z['reviews']})
        candidate=next(h for h in hints if 'ASR' in h['origin'])
        new=select(empty,[candidate]);self.assertTrue(new['zones'][0]['hypotheses_seen'])
        self.assertFalse(any(new['zones'][0]['reviews'].values()));self.assertEqual(new['zones'][0]['verbatim'],'')


if __name__=='__main__':unittest.main()
