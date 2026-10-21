"""Artificial unit fixtures with known truth; not benchmark quality evidence."""
import copy
import unittest
from .core import blank_zone,approve,tokens,update_zone,QualificationError
from .scoring import evaluate,diarization_scores,edit_alignment,lexical_clock


def project():
    return {'schema':1,'id':'test','audio':{'path':'unit-fixture.wav','sha256':'unit-fixture','duration':10},'sources':{},
        'voices':[{'id':'vA','name':'Alice humaine'},{'id':'vB','name':'Bob humain'}],
        'zones':[blank_zone('z1',0,2),blank_zone('z2',4,6)]}


def dataset():
    segment={'start':0.1,'end':.9,'text':'Bonjour mairie','words':[
        {'word':' Bonjour','start':.1,'end':.4},{'word':' mairie','start':.5,'end':.9}]}
    display={**segment,'speaker':'hA','source':{'word_spans':segment['words']}}
    base={'name':'fixture','asr':[segment],'clock':[segment],
          'diarization':[{'start':.1,'end':.9,'speaker':'hA'}],'standard':[display],'exclusive':[display]}
    return {'chains':{key:copy.deepcopy(base) for key in ('small','large','whisperx')}}


def reference():
    p=project();z=p['zones'][0];z['verbatim']='Bonjour mairie'
    z['turns']=[{'start':.1,'end':.9,'speaker':'vA'}]
    p=approve(p,'z1','text','Test humain explicite',True)
    return approve(p,'z1','diarization','Test humain explicite',True)


class ScoringTests(unittest.TestCase):
    def test_edit_distance_and_french_normalization(self):
        r=edit_alignment(['a','b','c'],['a','x','c','d'])
        self.assertEqual((r['substitute'],r['delete'],r['insert']),(1,0,1))
        self.assertEqual(r['WER'],2/3)
        self.assertIsNone(edit_alignment([],['inventé'])['WER'])
        self.assertEqual(tokens("L’ école, ÉLODIE ! 12"),["l'école",'élodie','12'])
    def test_french_elisions_and_missing_words_not_dropped(self):
        s={'start':0,'end':1,'text':"l'école revient",'words':[{'word':" l'",'start':0,'end':.1},{'word':'école','start':.1,'end':.5},{'word':' revient','start':.6,'end':1}]}
        self.assertEqual([w['text'] for w in lexical_clock([s])],["l'école",'revient'])
        s['words']=[];clock=lexical_clock([s]);self.assertEqual(len(clock),2);self.assertIsNone(clock[0]['start'])
    def test_no_reference_means_no_scores(self):
        result=evaluate(project(),dataset())
        for r in result['results'].values():
            self.assertIsNone(r['transcription']['WER']);self.assertIsNone(r['diarization']['DER'])
    def test_only_reviewed_zone_and_common_large_word_clock(self):
        p=reference();d=dataset()
        for chain in d['chains'].values():
            chain['asr'].append({'start':4,'end':6,'text':'hors portée non annoté','words':[]})
            chain['diarization'].append({'start':4,'end':6,'speaker':'autre'})
        result=evaluate(p,d)
        for r in result['results'].values():
            self.assertEqual(r['transcription']['WER'],0);self.assertAlmostEqual(r['diarization']['DER'],0)
        self.assertEqual(result['coverage']['WER_eligible_zones'],1)
    def test_der_global_mapping_cannot_hide_identity_changes_between_excerpts(self):
        zones=[{'id':'a','start':0,'end':1,'turns':[{'start':0,'end':1,'speaker':'vA'}]},
               {'id':'b','start':2,'end':3,'turns':[{'start':2,'end':3,'speaker':'vB'}]}]
        hyp=[{'start':0,'end':1,'speaker':'h'},{'start':2,'end':3,'speaker':'h'},{'start':8,'end':9,'speaker':'outside'}]
        r=diarization_scores(zones,hyp)
        self.assertAlmostEqual(r['DER'],.5);self.assertEqual(r['total'],2)
        self.assertEqual(sorted(z['DER'] for z in r['zones']),[0,1])
    def test_overlap_is_included_in_der_and_not_linearly_scored_in_wer(self):
        z={'id':'overlap','start':0,'end':2,'turns':[{'start':0,'end':2,'speaker':'A'},{'start':1,'end':2,'speaker':'B'}]}
        r=diarization_scores([z],[{'start':0,'end':2,'speaker':'h'}])
        self.assertEqual(r['total'],3);self.assertAlmostEqual(r['DER'],1/3)
        p=reference();p['zones'][0]['tags']=['chevauchement']
        p['zones'][0]=update_zone(p['zones'][0],turns=p['zones'][0]['turns']+[{'start':.2,'end':.5,'speaker':'vB'}])
        p=approve(p,'z1','diarization','Test',True)
        r=evaluate(p,dataset());self.assertIsNone(r['results']['small']['transcription']['WER'])
        self.assertIsNotNone(r['results']['small']['diarization']['DER'])
    def test_silence_keeps_insertions_and_false_alarms_without_fake_zero_rate(self):
        p=project();p['zones'][0]['silence']=True
        for domain in ('text','diarization'):p=approve(p,'z1',domain,'Test',True)
        r=evaluate(p,dataset())['results']['small']
        self.assertIsNone(r['transcription']['WER']);self.assertEqual(r['transcription']['insert'],2)
        self.assertIsNone(r['diarization']['DER']);self.assertAlmostEqual(r['diarization']['false alarm'],.8)
    def test_partial_segment_without_word_times_blocks_common_wer_scope(self):
        p=reference();d=dataset();d['chains']['small']['asr']=[{'start':0,'end':3,'text':'bonjour mairie autre','words':[]}]
        r=evaluate(p,d);self.assertEqual(r['coverage']['WER_eligible_zones'],0)
    def test_tag_strata_do_not_score_unreviewed_regions(self):
        p=reference();p['zones'][0]['tags']=['nom propre'];p['zones'][1]['tags']=['nom propre','interruption']
        r=evaluate(p,dataset())['results']['small']['difficult_cases']
        self.assertEqual(r['nom propre']['WER_zones'],1);self.assertEqual(r['nom propre']['DER_zones'],1)
        self.assertIsNone(r['interruption']['WER']);self.assertIsNone(r['interruption']['DER'])
    def test_separate_word_alignment_and_final_attribution_errors(self):
        p=reference();p['zones'][0]['words']=[{'text':'Bonjour','start':.1,'end':.4,'speaker':'vA'},{'text':'mairie','start':.5,'end':.9,'speaker':'vA'}]
        p=approve(p,'z1','word_times','Test',True);d=dataset()
        for w in d['chains']['large']['clock'][0]['words']:w['start']+=.1;w['end']+=.1
        # Clock was shared with asr in this test fixture: restore identical ASR input.
        d['chains']['large']['asr']=copy.deepcopy(d['chains']['small']['asr'])
        d['chains']['whisperx']['exclusive'][0]['speaker']='unmapped'
        r=evaluate(p,d)['results']
        self.assertAlmostEqual(r['large']['alignment_and_word_attribution']['mean_start_absolute_error_seconds'],.1)
        self.assertEqual(r['whisperx']['alignment_and_word_attribution']['mean_start_absolute_error_seconds'],0)
        self.assertEqual(r['whisperx']['alignment_and_word_attribution']['conditional_attribution_error_rate'],1)
        self.assertEqual(r['large']['transcription']['WER'],r['whisperx']['transcription']['WER'])
        self.assertEqual(r['large']['diarization']['DER'],r['whisperx']['diarization']['DER'])


if __name__=='__main__':unittest.main()
