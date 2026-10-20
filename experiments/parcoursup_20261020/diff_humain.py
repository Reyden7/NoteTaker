"""Describe every human revision without inferring an acoustic correction."""
from collections import Counter
from .prepare import read, write_new
from .import_human import V2


def main():
    a=read(V2/'inputs/A-original.json')['passages']
    b=read(V2/'inputs/B-corrigee-humaine.json')['passages']
    by_id={r['id']:r for r in b}
    changes=[]
    for row in a:
        corrected=by_id.get(row['id'])
        if corrected is None:
            changes.append({'id':row['id'],'kind':'absent_from_human_revision','original':row})
        else:
            fields={k:{'before':row[k],'after':corrected[k]} for k in ('speaker_label','text') if row[k]!=corrected[k]}
            if fields: changes.append({'id':row['id'],'kind':'human_supplied_change','start_ms':row['start_ms'],
                                       'end_ms':row['end_ms'],'fields':fields})
    counts=Counter(k for c in changes for k in c.get('fields',{}))
    write_new(V2/'diff-correction-humaine.json',{'counts':dict(counts),'missing_row_count':len(a)-len(b),
        'original_rows':len(a),'human_rows':len(b),'time_boundaries_changed':False,
        'agent_audio_listening':False,'changes':changes})
    print(dict(counts))


if __name__=='__main__': main()
