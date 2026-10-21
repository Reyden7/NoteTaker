"""Build a local, evidence-linked report; never score incomplete human references."""
import csv
import io
import json
from pathlib import Path
from .common import ROOT,OUT,read,write,sha
from .observations import EXCERPTS,DIAGNOSTICS


def link(label,path):return f'[{label}](<{Path(path).resolve().as_posix()}>)'


def mm(seconds):return f'{int(seconds)//60:02d}:{seconds%60:06.3f}'


def measurements():
    rows=[]
    for path in sorted((OUT/'runs').glob('*/**/measurement.json')):
        m=read(path);relative=path.relative_to(OUT/'runs').parts
        cpu=m.get('cpu') or {};result_path=path.parent.parent/('asr-result.json' if relative[-2]=='asr' else 'sherpa-result.json' if relative[-2]=='sherpa' else 'result.json')
        r=read(result_path) if result_path.is_file() else {}
        output=r.get('result') or {}
        rows.append({'series':relative[0],'stage':relative[1],'component':relative[-2],
            'status':m['status'],'exit_code':m.get('exit_code'),'wall_seconds':m.get('wall_seconds'),
            'cpu_user_seconds':cpu.get('user_seconds'),'cpu_kernel_seconds':cpu.get('kernel_seconds'),
            'cpu_total_seconds':sum(cpu.get(k,0) for k in ('user_seconds','kernel_seconds')) if cpu else None,
            'peak_job_committed_bytes':m.get('peak_job_committed_bytes'),
            'peak_sampled_tree_rss_bytes':m.get('peak_sampled_tree_rss_bytes'),
            'peak_observed_windows_process_working_set_bytes':m.get('peak_observed_windows_process_working_set_bytes'),
            'gpu_active_kernel_seconds':None,'gpu_process_peak_vram_bytes':None,
            'gpu_metrics':output.get('gpu_metrics'),
            'python_network_attempts':r.get('python_network_attempts'),
            'error_type':r.get('error_type') or m.get('error_type'),
            'error':r.get('error') or m.get('error'),
            'request':str(path.parent.parent/('asr-request.json' if relative[-2]=='asr' else 'sherpa-request.json' if relative[-2]=='sherpa' else 'request.json')),
            'measurement':str(path),'result':str(result_path)})
    return rows


def model_sizes():
    request=read(OUT/'runs/A-cpu-v2/full/asr-request.json')
    files=[Path(request['model'])/'model.bin']+[Path(request[k]) for k in ('segmentation','embedding','refinement_embedding')]
    rows=[{'name':'A — poids Small + trois ONNX actuels','bytes':sum(p.stat().st_size for p in files),
           'scope':'Weight files only; see product manifests for all accompanying files','files':[str(p) for p in files]}]
    for name in ('large','community','alignment','moss'):
        proof=read(OUT/'assets'/(name+'.json'))
        rows.append({'name':name,'bytes':sum(f['size'] for f in proof['files']),
                     'scope':'All acquired files in the pinned asset proof, excluding acquisition cache','revision':proof['revision']})
    write(OUT/'model-sizes.json',rows)
    return rows


def preservation():
    m=read(OUT/'manifest.json')
    protected={p:sha(p)==h for p,h in m['protected'].items()}
    audio={k:sha(c['audio'])==c['sha256'] for k,c in m['cases'].items()}
    assets={}
    for name in ('large','community','alignment','moss'):
        proof=read(OUT/'assets'/(name+'.json'))
        assets[name]={f['name']:sha(Path(proof['path'])/f['name'])==f['sha256'] for f in proof['files']}
    source=sha(m['source_audio'])==m['source_audio_sha256']
    result={'source_audio_unchanged':source,'protected':protected,'prepared_audio':audio,'assets':assets,
            'all_checked_hashes_match':source and all(protected.values()) and all(audio.values()) and all(all(v.values()) for v in assets.values()),
            'scope':'Source Python, product model manifests, frozen references, source/clip audio and acquired candidate assets. No claim of a pre/post hash for every user database.',
            'session_store_or_database_opened_by_lab':False}
    write(OUT/'preservation.json',result)
    return result


def license_archive():
    index=[]
    for env in 'ABC':
        inventory=read(OUT/f'environments/{env}.json')
        for p in inventory['packages']:
            for i,f in enumerate(p['license_files']):
                path=Path(f)
                target=OUT/'licenses'/env/p['name']/(str(i)+'-'+path.name)
                data=path.read_bytes();target.parent.mkdir(parents=True,exist_ok=True)
                if target.exists() and target.read_bytes()!=data:raise ValueError('LICENSE_ARCHIVE_CHANGED')
                if not target.exists():target.write_bytes(data)
                index.append({'environment':env,'package':p['name'],'version':p['version'],
                              'source':str(path),'archive':str(target),'sha256':sha(target)})
    # Trained Punkt data has a separate, unresolved redistribution status.
    nltk=ROOT/'models/audio-lab/nltk'
    files=[{'name':str(p.relative_to(nltk)),'size':p.stat().st_size,'sha256':sha(p)} for p in sorted(nltk.rglob('*')) if p.is_file()]
    write(OUT/'assets/nltk-data-local.json',{'acquisition':'Explicit build-time nltk.download(punkt_tab); no inference download',
        'index_url':'https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/tokenizers/punkt_tab.xml',
        'immutable_upstream_revision_recorded_at_acquisition':False,'files':files,
        'redistribution_approved':False,'reason':'No explicit trained-data redistribution grant found in inspected README/index. NLTK code license does not establish trained-data license.'})
    write(OUT/'licenses/index.json',index)


def review_packet():
    reference=read(OUT/'references/annotations-12-extraits-originales.json')
    sources={
        'A CPU — complet':(OUT/'runs/A-cpu-v2/full/transcript.json',0,None),
        **{f'B CUDA — {v} — complet':(OUT/f'combined/B-cuda/full/{v}.json',0,None) for v in
            ('without-whisperx-standard','without-whisperx-exclusive','with-whisperx-standard','with-whisperx-exclusive')},
        'C CUDA — 180 s seulement':(OUT/'runs/moss-cuda-main/180s/transcript.json',1051.96,1231.96),
        'C CUDA — 60 s seulement':(OUT/'runs/moss-cuda-main/60s/transcript.json',1080,1140)}
    packet=[];index=['# Douze extraits — comparaison préparée pour écoute humaine','',
        '**Aucune écoute certifiée par l’agent.** Les observations sont une confrontation textuelle à la référence fournie. '
        'Les changements de voix, interruptions et chevauchements restent à annoter précisément. Aucun WER/DER/cpWER/cpCER.','',
        'C n’a pas produit de transcription complète : ses deux clips pilotes sont affichés uniquement là où ils recouvrent l’extrait. '
        'Un groupe peut changer d’identité entre essais ; comparer les groupes uniquement dans une même sortie.','']
    for e in reference['excerpts']:
        start,end=e['start_ms']/1000,e['end_ms']/1000
        audio=ROOT/'output/direct-summary/reference-humaine'/e['audio']
        expected,observation=EXCERPTS[e['id']]
        lines=[f"# {e['id']} — {mm(start)}–{mm(end)}",'',
            f'![Écouter les 40 secondes](<{audio.resolve().as_posix()}>)','',
            '**Statut : écoute humaine et frontières non validées.** Les noms ci-dessous proviennent du document humain, pas d’une reconnaissance nominative.','',
            '## Référence humaine narrative ou corrigée','',expected,'',
            '## Écarts textuels à examiner','',observation,'',
            'Les lignes débordant de l’extrait restent entières pour préserver leur contexte. Horaires absolus dans le débat.','']
        item={**e,'human_checked':False,'review_status':'prepared_not_audio_reviewed',
              'expected_from_human_reference':expected,'text_comparison':observation,'outputs':{}}
        for title,(path,offset,stop) in sources.items():
            rows=read(path)['segments'];selected=[]
            for r in rows:
                if r['end']+offset>start and r['start']+offset<end:
                    selected.append({**r,'global_start':r['start']+offset,'global_end':r['end']+offset})
            lines += ['## '+title,'',link('Sortie complète de cet essai',path),'']
            if not selected:
                lines+=['**Non disponible sur cette portée ; aucun résultat C complet.**','']
            else:
                if stop:lines += [f'Portée limitée : {mm(offset)}–{mm(stop)}. Au-delà : non traité dans cet essai.','']
                for r in selected:
                    flags=[]
                    if r.get('uncertain'):flags.append('incertain selon rapprochement automatique')
                    if r['end']==r['start']:flags.append('durée nulle')
                    if r.get('uncertainty_status'):flags.append('confiance non calibrée')
                    lines += [f"- **{mm(r['global_start'])}–{mm(r['global_end'])} · {r.get('speaker') or 'inconnu'}**"
                        +(' · '+', '.join(flags) if flags else '')+' : '+r.get('text','')]
                lines+=['']
            item['outputs'][title]={'source':str(path),'offset_seconds':offset,'segments':selected}
        lines += ['## À remplir après écoute','',
            '- Auteur et début/fin de chaque changement de voix :','- Interruptions et paroles simultanées :',
            '- Mots réellement omis, déformés ou ajoutés :','- Date et personne ayant vérifié :','']
        target=OUT/'review'/f"{e['id']}.md";write(target,'\n'.join(lines))
        index += [f"- {link(e['id']+' '+mm(start)+'–'+mm(end),target)} : {expected}"]
        packet.append(item)
    write(OUT/'review/index.md','\n'.join(index)+'\n')
    write(OUT/'review/comparaison-a-annoter.json',{'human_reference_completed':False,
        'audio_review_by_agent':False,'metrics':{k:None for k in ('WER','DER','cpWER','cpCER')},'excerpts':packet})


def transcript_views():
    sources=[('A CPU complet',OUT/'runs/A-cpu-v2/full/transcript.json',0),
             ('C CUDA 180 s',OUT/'runs/moss-cuda-main/180s/transcript.json',1051.96),
             ('C CUDA 60 s',OUT/'runs/moss-cuda-main/60s/transcript.json',1080),
             ('C CPU 60 s',OUT/'runs/moss-cpu-main/60s/transcript.json',1080)]
    for device in ('cuda','cpu'):
        for stage in ('60s','180s','full'):
            folder=OUT/f'combined/B-{device}/{stage}'
            if not folder.is_dir():continue
            offset=read(OUT/'manifest.json')['cases'][stage]['start_in_original_seconds']
            for path in sorted(folder.glob('*.json')):
                if path.name=='statistics.json':continue
                sources.append((f'B {device} {stage} {path.stem}',path,offset))
    inventory=[]
    index=['# Transcriptions du laboratoire','',
           'Sorties non corrigées ; identifiants anonymes propres à chaque essai. '
           'Aucun nom automatiquement reconnu. Les vues B ajoutent seulement des espaces aux surfaces lexicales WhisperX, '
           'sans changer les JSON bruts des moteurs. Horaires absolus dans le débat.','']
    for name,path,offset in sources:
        rows=read(path)['segments'];flagged=[]
        for i,r in enumerate(rows):
            reasons=[];source=r.get('source') or {}
            if r.get('uncertain'):reasons.append('signal_automatique_du_rapprochement')
            if r.get('speaker') is None:reasons.append('groupe_inconnu')
            if 0<=r['end']-r['start']<1:reasons.append('passage_moins_une_seconde')
            if source.get('word_alignment_missing_or_incomplete'):reasons.append('alignement_mots_incomplet')
            if source.get('possible_overlap'):reasons.append('chevauchement_possible_amont')
            if any(j!=i and r.get('speaker')!=s.get('speaker') and min(r['end'],s['end'])>max(r['start'],s['start']) for j,s in enumerate(rows)):
                reasons.append('plages_de_groupes_distincts_se_chevauchent')
            if reasons:flagged.append({'id':r.get('id',str(i)),'start':r['start']+offset,'end':r['end']+offset,
                'speaker':r.get('speaker'),'text':r['text'],'reasons':reasons})
        inventory.append({'name':name,'source':str(path),'all_attributions_require_human_check':True,
            'heuristics_are_not_accuracy_or_calibrated_confidence':True,'flagged':flagged})
        target=path.with_suffix('.md')
        # Keep A/C's earlier engine-specific Markdown untouched; create a separate view.
        if name.startswith(('A ','C ')):target=path.with_name('transcript-global-view.md')
        lines=['# '+name,'',link('JSON source de cette vue',path),'',
            'Horaires absolus. Absence de signal automatique ≠ attribution confirmée.','']
        flagged_ids={f['id'] for f in flagged}
        for i,r in enumerate(rows):
            label=' · À vérifier' if r.get('id',str(i)) in flagged_ids else ''
            lines += [f"- **{mm(r['start']+offset)}–{mm(r['end']+offset)} · {r.get('speaker') or 'inconnu'}**{label} : {r['text']}"]
        write(target,'\n'.join(lines)+'\n')
        index += ['- '+link(name,target)]
    write(OUT/'uncertitudes.json',{'status':'heuristic_review_inventory_not_ground_truth','outputs':inventory})
    write(OUT/'transcriptions.md','\n'.join(index)+'\n')


def main():
    measurements_rows=measurements()
    write(OUT/'mesures.json',measurements_rows)
    stream=io.StringIO(newline='');fields=[k for k in measurements_rows[0] if k!='gpu_metrics']
    writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(measurements_rows)
    write(OUT/'mesures.csv',stream.getvalue())
    write(OUT/'diagnostic.json',{'reference':'Documents humains conservés ; comparaison textuelle, sans écoute acoustique par agent',
        'quality_validated':False,'observations':DIAGNOSTICS,'excerpts':EXCERPTS})
    review_packet();transcript_views();license_archive();preserved=preservation();sizes=model_sizes()
    lines=['# Benchmark audio NoteTaker — 20 octobre 2026','',
        '**Laboratoire indépendant ; aucun remplacement du moteur applicatif, aucune recompilation.**','',
        '## Conclusion','',
        'Large-v3 + Community-1 avec WhisperX est la candidate à approfondir sur ce poste équipé NVIDIA : '
        'elle termine le fichier complet, conserve le texte reconnu et évite les interventions de durée nulle dans cet essai. '
        '**Sa précision n’est pas validée** : des fusions de voix et des attributions erronées restent visibles face à la référence humaine. '
        'Conserver A en production. MOSS ne peut pas être retenu pour la portée longue dans cette configuration : échec mémoire GPU, '
        'malgré des pilotes courts réussis. Ne pas transformer cette préférence technique en décision de migration.','',
        '## Corpus et protocole','',
        'Même WAV PCM mono 16 kHz : **1 240,0168125 s, soit 20 min 40,017 s**, '
        'SHA-256 `95da1f0787fd22ad313acfd367fda3012b47587660cb9b1a2d6e6001bf0e708a`. '
        'Le fichier a la portée historique des 670 passages corrigés ; les nombres de nouvelles interventions ne sont pas contraints à 670. '
        'Copies exactes : 60 s à 18:00, 180 s à 17:31,960, puis totalité. Aucun nombre de voix imposé. '
        'Aucune autre réunion naturelle française n’a été fournie.','',
        'A réutilise les fonctions actuelles de transcription/diarisation, puis uniquement les fonctions pures de rapprochement. '
        'B sépare reconnaissance, Community-1 standard/exclusive et alignement WhisperX du même texte. '
        'C utilise le prompt et le parseur officiels OpenMOSS, sans noms ni transcription de référence en entrée. '
        'Chaque composant réussi à 60 s puis 180 s a pu passer au fichier complet.','',
        link('Transcriptions horodatées lisibles et JSON sources',OUT/'transcriptions.md')+' · '+
        link('Inventaire des passages à contrôler',OUT/'uncertitudes.json'),'',
        '## Matériel, isolement et limites de mesure','',
        '- Intel Core i5-14600KF : 14 cœurs / 20 processeurs logiques ; RAM 31,79 GiB ; Windows 10.0.26300 x64.',
        '- NVIDIA RTX 5070 : 12 227 MiB ; pilote 616.92 ; compute capability 12.0. '
          'PyTorch 2.8.0+cu128 contient sm_120 et a réellement exécuté un calcul CUDA.',
        '- Processus neufs, environnements A/B/C distincts, quatre threads de calcul demandés, '
          'Job Windows limité à 12 GiB engagés avant démarrage ; annulation par fichier `CANCEL` dans le dossier de résultats.',
        '- Les étapes GPU du fichier complet et les contrôles CPU suivants sont séquentiels. '
          'A complet a chevauché des pilotes GPU courts : sa durée peut subir de la contention. '
          'Pas de quotient de vitesse CPU/GPU présenté comme une comparaison à matériel égal.',
        '- Une seule exécution par portée/configuration. Processus froids mais caches disque, CUDA/JIT et OS non purgés. '
          'Les pilotes 60 s incluent des coûts initiaux différents ; pas de performance « à froid » certifiée.',
        '- CPU = temps utilisateur + noyau du Job et descendants ; mémoire engagée du Job conservée par le noyau. '
          'RSS = maximum échantillonné à 250 ms, pas une garantie de capture de chaque pointe.',
        '- Temps actif des kernels GPU et maximum VRAM de tous les moteurs : **non mesurés**. '
          'MOSS fournit un intervalle CUDA de génération incluant les attentes et des pics d’allocateur Torch ; '
          'ils ne comptent pas tout le contexte CUDA ni les allocations CTranslate2.',
        '- Inférence locale : fichiers épinglés, options offline, téléchargements et télémétrie désactivés, '
          'sockets Python bloquées ; le nombre de tentatives Python est enregistré. '
          'PC de développement connecté : pas encore une recette réseau physiquement coupé sur Windows vierge.','',
        '## Mesures réellement exécutées','',
        '| Série | Audio | Étape | État | Écoulé s | CPU cumulé s | Pic engagé GiB | Pic RSS observé GiB |',
        '|---|---|---|---|---:|---:|---:|---:|']
    for r in measurements_rows:
        fmt=lambda x:'—' if x is None else f'{x:.2f}'
        lines += [f"| {r['series']} | {r['stage']} | {r['component']} | {r['status']} | {fmt(r['wall_seconds'])} | {fmt(r['cpu_total_seconds'])} | {fmt(r['peak_job_committed_bytes']/1024**3 if r['peak_job_committed_bytes'] is not None else None)} | {fmt(r['peak_sampled_tree_rss_bytes']/1024**3 if r['peak_sampled_tree_rss_bytes'] is not None else None)} |"]
    totals={}
    for title,series in [('A complet CPU',['A-cpu-v2']),('B complet CUDA, sans WhisperX',['large-cuda-main','community-cuda-main']),
                         ('B complet CUDA, avec WhisperX',['large-cuda-main','community-cuda-main','alignment-cuda-main'])]:
        selected=[r for r in measurements_rows if r['stage']=='full' and r['series'] in series and r['status']=='completed']
        totals[title]={'wall_seconds':sum(r['wall_seconds'] for r in selected),
                       'cpu_total_seconds':sum(r['cpu_total_seconds'] for r in selected)}
    write(OUT/'chain-totals.json',totals)
    lines += ['','Sommes des étapes séparées (chargements inclus, rapprochement Python hors chronométrage) :']
    for title,t in totals.items():lines += [f"- {title} : **{t['wall_seconds']:.2f} s écoulées**, {t['cpu_total_seconds']:.2f} s CPU cumulées."]
    lines += ['',link('Mesures détaillées JSON',OUT/'mesures.json')+' · '+link('Table CSV',OUT/'mesures.csv'),'',
        'Les contrôles CPU B/C portent uniquement sur 60 s. Une réussite courte ne qualifie pas leur repli CPU sur 20 minutes. '
        'L’erreur initiale `CREATE_SUSPENDED` est un défaut du contrôleur de laboratoire, conservé ; corrigé avant A-cpu-v2. '
        'L’échec MOSS complet est une véritable erreur d’inférence CUDA, pas un simple dépassement de délai.','',
        '## Segmentation et groupes : descriptions, pas scores de qualité','',
        '| Portée / sortie | Lignes | Groupes | Durée nulle | <0,5 s | <1 s | <2 s | Incertains |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for stage in ('60s','180s','full'):
        a=read(OUT/f'runs/A-cpu-v2/{stage}/statistics.json')
        b=read(OUT/f'combined/B-cuda/{stage}/statistics.json')
        tables=[('A ASR',a['asr'],None),('A tours',a['diarization'],None),('A rapproché',a['combined'],a['uncertain_combined_count']),
                ('B ASR',b['raw_asr'],None),('B tours standard',b['standard_diarization'],None),('B tours exclusifs',b['exclusive_diarization'],None)]
        tables += [('B '+v,s,s['uncertain_count']) for v,s in b['variants'].items()]
        moss_path=OUT/f'runs/moss-cuda-main/{stage}/statistics.json'
        if moss_path.is_file():tables.append(('C brut',read(moss_path)['segments'],'non calibré'))
        for name,s,u in tables:
            lines += [f"| {stage} / {name} | {s['count']} | {s['speaker_groups'] if s['speaker_groups'] is not None else '—'} | {s['zero_duration']} | {s['less_than_0_5s']} | {s['less_than_1s']} | {s['less_than_2s']} | {u if u is not None else '—'} |"]
    lines += ['',
        'Pas de durées négatives, de plages hors audio ou de texte vide dans les sorties complètes A/B. '
        'Les durées nulles d’A et de B sans WhisperX apparaissent au rapprochement ; elles ne sont ni supprimées ni comptées comme qualité acoustique. '
        'Les unités ne sont pas identiques : mots/fragments rapprochés pour A/B, interventions générées pour C. '
        'Le nombre de groupes n’est jamais un score de précision.','',
        '## Apport et limites de WhisperX','',
        'Les quatre variantes B conservent l’intégralité du texte reconnu à espaces près, y compris les répétitions. '
        'L’adaptateur du laboratoire ajoute les séparateurs absents des mots WhisperX pour le concaténateur historique ; '
        'les JSON bruts restent inchangés. Les premiers fichiers dérivés avec mots accolés sont archivés dans les dossiers `*-spacing-pilot`. '
        'Sur le fichier complet, dix segments sans mots complètement alignés gardent leur texte et leur plage entière, '
        'avec alerte explicite. Standard et exclusif sont tous deux disponibles ; les chevauchements standard restent signalés dans les vues exclusives. '
        'Aucune amélioration des frontières ou des attributions n’est quantifiée sans annotation acoustique humaine.','',
        '## Comparaison qualitative aux références humaines','',
        '**Ce tableau n’est pas une écoute de l’audio par l’agent.** Il relève des cohérences et contradictions textuelles '
        'avec le récit fourni et la correction humaine Parcoursup. Les noms ne sont jamais injectés dans les hypothèses des moteurs.','',
        '| Extrait | Attendu humain | Observations textuelles |','|---|---|---|']
    for key,(expected,observation) in EXCERPTS.items():
        lines += [f'| {link(key,OUT/f"review/{key}.md")} | {expected} | {observation} |']
    lines += ['',link('Douze vues avec audio, quatre variantes B et pilotes C disponibles',OUT/'review/index.md'),'',
        'WER, DER, cpWER, cpCER : **non mesurés**. Les douze formulaires initiaux ne sont pas remplis ; '
        'la correction humaine conserve des horaires hérités de l’ASR et n’est pas un verbatim exhaustif réannoté. '
        'Les assertions sur le résultat du mouvement, les opinions citées et les accusations restent des propos attribués, '
        'pas une vérification factuelle par le laboratoire. Les parties du récit après 20:40 ne sont pas des omissions du moteur sur ce corpus.','',
        '## Incertitudes et erreurs techniques','']
    for d in DIAGNOSTICS:lines += [f"- **{d['id']} — {d['scope']}** : {d['finding']}"]
    for r in measurements_rows:
        if r['status'] not in ('completed','running'):
            lines += [f"- **{r['series']} / {r['stage']}** : {r['error_type'] or r['status']} ; "+link('trace et mesures',r['measurement'])+'.']
    lines += ['',
        'TorchCodec 0.7.0 ne charge pas son décodeur natif sur ce Windows (DLL FFmpeg manquantes). '
        'Community-1 fonctionne réellement avec un tenseur audio préchargé, entrée documentée par l’amont. '
        'La lecture directe de fichiers par ce décodeur reste non validée ; le laboratoire lit le PCM WAV avec la bibliothèque standard. '
        'WhisperX reçoit également le WAV en mémoire. Aucun correctif n’est injecté dans NoteTaker.','',
        '## Dépendances et redistribution','',
        '| Environnement | Python | Taille logique des paquets |','|---|---|---:|']
    for env in 'ABC':
        e=read(OUT/f'environments/{env}.json')
        lines += [f"| {env} | {e['python']} | {e['logical_dependency_bytes']/1024**3:.3f} GiB |"]
    lines += ['','| Actif de modèle | Taille locale |','|---|---:|']
    for s in sizes:lines += [f"| {s['name']} | {s['bytes']/1024**3:.3f} GiB |"]
    lines += ['',
        'Tailles installées logiques des distributions Python, hors modèles, interpréteurs, cache et compression installateur. '
        'Les liens physiques uv peuvent partager les blocs disque. Inventaires complets et versions dans `environments`, '
        'preuves des poids dans `assets`, licences Python archivées dans `licenses`. '
        'A utilise CTranslate2 4.6.0, B 4.8.3 ; les dépendances ne sont donc pas toutes identiques. '
        'B utilise Transformers 4.57.6 et C 5.20.2 dans deux environnements incompatibles séparés.','',
        link('Audit des licences et réserves de redistribution',ROOT/'docs/audio-benchmark-20261020-licenses.md'),'',
        'Les licences des modèles permettent un usage commercial sous leurs conditions : '
        '[Large-v3 converti MIT](https://huggingface.co/Systran/faster-whisper-large-v3), '
        '[Community-1 CC BY 4.0](https://huggingface.co/pyannote/speaker-diarization-community-1), '
        '[MOSS Apache 2.0](https://huggingface.co/OpenMOSS-Team/MOSS-Transcribe-Diarize). '
        'Cela ne qualifie pas la redistribution du lot Windows : notices, DLL NVIDIA/FFmpeg, données Punkt et autres obligations restent à instruire.','',
        '## Tests, conservation et suite','',
        'Les tests automatiques du laboratoire couvrent les Jobs Windows, la limite mémoire effective, l’annulation, '
        'la conservation PCM/hashes, les textes avec/sans alignement et le refus de produire des scores injustifiés. '
        'Le dernier rapport JUnit est lié dans docs/progress.md ; aucune suite applicative ni recette installateur n’est revendiquée ici.','',
        f"Vérification finale des hashes préenregistrés et des actifs acquis : **{'tous identiques' if preserved['all_checked_hashes_match'] else 'ÉCHEC — consulter preservation.json'}**. "
        'Le laboratoire n’importe pas SessionStore et n’ouvre pas la base utilisateur. '
        'Le MP3 d’origine et les corrections fournies ne sont jamais remplacés.','',
        'Suite recommandée : annoter en aveugle les frontières et chevauchements des douze extraits, '
        'en priorité E01/E04/E09/E10/E12 ; inclure une vraie réunion municipale avec microphone ambiant. '
        'Mesurer alors WER/DER et la charge de correction. Profiler/répéter les essais CPU longs et les durées GPU '
        'avec mémoire vidéo avant toute décision produit. Pour MOSS, étudier un backend attention réellement économe '
        'compatible Windows ou une machine plus adaptée, en conservant cet échec comme point de comparaison ; '
        'aucun découpage avec réconciliation de voix n’a été évalué.','']
    write(OUT/'rapport-comparatif.md','\n'.join(lines))
    print('Report, measurements, 12 comparison views, license archive and preservation report written.')


if __name__=='__main__':main()
