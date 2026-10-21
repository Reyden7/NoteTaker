"""Compare unchanged recognized text with/without forced alignment and exclusive turns."""
import argparse
import re
from .common import ROOT,OUT,read,write
from .analyze import align_reference,describe


def standard_overlap(turns):
    result=[]
    for i,a in enumerate(turns):
        for b in turns[i+1:]:
            start,end=max(a['start'],b['start']),min(a['end'],b['end'])
            if a['speaker']!=b['speaker'] and end>start:result.append({'start':start,'end':end})
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['60s','180s','full']);p.add_argument('--device',default='cuda');a=p.parse_args()
    original=OUT/'runs'/('large-'+a.device+'-main')/a.stage
    diar_folder=OUT/'runs'/('community-'+a.device+'-main')/a.stage
    aligned_folder=OUT/'runs'/('alignment-'+a.device+'-main')/a.stage
    for folder in (original,diar_folder,aligned_folder):
        if not read(folder/'gate.json')['passed']:raise ValueError('B_COMPONENT_FAILED')
    raw=read(original/'result.json')['result'];diar=read(diar_folder/'result.json')['result']
    aligned=read(aligned_folder/'result.json')['result']
    output=OUT/'combined'/('B-'+a.device)/a.stage;output.mkdir(parents=True,exist_ok=True)
    overlap=standard_overlap(diar['turns'])
    def compact(text):return re.sub(r'\s+','',text)
    before=compact(''.join(r['text'] for r in raw['segments']))
    after=compact(''.join(r['text'] for r in aligned['segments']))
    variants={}
    for alignment_name,source in [('without-whisperx',raw),('with-whisperx',aligned)]:
        segments=[];fallback=[]
        for i,s in enumerate(source['segments']):
            words=s.get('words') or []
            incomplete=bool(s.get('text','').strip()) and (not words or any(w.get('start') is None or w.get('end') is None for w in words))
            if incomplete:fallback.append(i)
            # WhisperModel surfaces include leading spaces; WhisperX surfaces do not.
            # Adapt only separators for the unchanged reference concatenation function.
            # Raw alignment JSON remains untouched, including all original surfaces.
            if alignment_name=='with-whisperx':
                words=[{**w,'word':' '+w['word'].lstrip()} for w in words]
            segments.append({**s,'id':f's{i}','words':[] if incomplete else words})
        for diar_name,turns in [('standard',diar['turns']),('exclusive',diar['exclusive_turns'])]:
            rows,speakers=align_reference(segments,{'turns':turns,'possible_overlaps':overlap})
            normalized=[{'id':r['id'],'start':r['start_ms']/1000,'end':r['end_ms']/1000,
                'speaker':r['speaker_id'],'text':r['text'],'uncertain':r['uncertain'],'source':r['source']} for r in rows]
            fallback_ids={f's{i}' for i in fallback}
            for r in normalized:
                if r['id'] in fallback_ids:
                    r['uncertain']=True;r['source']['word_alignment_missing_or_incomplete']=True
            key=alignment_name+'-'+diar_name
            write(output/(key+'.json'),{'segments':normalized,'speaker_aliases':speakers,
                'no_names_automatically_assigned':True,'unaligned_word_fallback_segment_indices':fallback,
                'surface_adapter':'Whitespace separators added to WhisperX word surfaces for the existing reference concatenator; raw outputs unchanged.' if alignment_name=='with-whisperx' else None,
                'standard_overlaps_preserved_as_uncertainty':True})
            stats=describe(normalized,read(OUT/'manifest.json')['cases'][a.stage]['duration_seconds'],has_text=True)
            variants[key]={**stats,'uncertain_count':sum(r['uncertain'] for r in normalized),
                           'combined_text_preserved_ignoring_whitespace':compact(''.join(r['text'] for r in normalized))==before,
                           'whole_segment_fallback_count':len(fallback)}
    summary={'raw_asr':describe(raw['segments'],read(OUT/'manifest.json')['cases'][a.stage]['duration_seconds'],has_text=True),
        'standard_diarization':describe(diar['turns'],read(OUT/'manifest.json')['cases'][a.stage]['duration_seconds']),
        'exclusive_diarization':describe(diar['exclusive_turns'],read(OUT/'manifest.json')['cases'][a.stage]['duration_seconds']),
        'recognized_text_preserved_ignoring_whitespace':before==after,'original_text':before if before!=after else None,
        'aligned_text':after if before!=after else None,'variants':variants,
        'WER':None,'DER':None,'cpWER':None,'cpCER':None,'quality_validated':False}
    write(output/'statistics.json',summary)
    print('Combined B',a.stage,'recognized text preserved:',before==after)


if __name__=='__main__':main()
