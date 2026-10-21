"""Conservative, symmetric French scoring transforms, never reference edits.

Versioned rules are intentionally finite. No spellchecker, fuzzy names, accent
stripping, grammar repair, synonym replacement or deletion of hesitations.
"""
import re
from .core import tokens

VERSION = 'fr-conservative-v1'
RULES = {
    'base': 'Protocole strict inchangé : NFC, casse/ponctuation ignorées, accents conservés.',
    'clitics': "Séparer les élisions connues en conservant chaque composant ; j→je, n→ne, d→de, c→ce, qu→que, m→me, t→te ; s→si devant il/ils, sinon se. l reste l (le/la indécidable). Ne jamais supprimer ne, pas, plus, jamais, ni, non.",
    'accents': 'Liste fermée : selection/séléction→sélection, selectionne/séléctionne→sélectionne, evenement/évènement→événement, evenements/évènements→événements, zero→zéro. Les autres accents restent distinctifs (a/à, ou/où, sur/sûr, du/dû, élevé/élève). Pas de suppression générale des accents.',
    'ligatures': 'œ→oe et æ→ae, sans autre correction de lettres.',
    'proper_names': 'Alias explicite unique parcours sup→parcoursup. Pas de rapprochement phonétique ou de correction parcoursuc→parcoursup ; aucune identité inventée.',
    'integers': 'Entiers arabes isolés 0–9999 sans zéro initial→forme française en lettres ; signe explicite conservé sous forme moins/plus. Traits d’union déjà séparés par le protocole strict. Les nombres adjacents et décimaux ne sont pas interprétés. Aucun mot grammatical, unité ou négation supprimé.',
    'hours': 'Notation isolée Nh (0–9999)→nombre en lettres + heure/heures. Pas de conversion d’horaires composés ni d’unités implicites.',
    'numeric_plural': 'Dans un groupe numérique seulement : cents→cent et quatre vingts→quatre vingt ; aucun pluriel lexical ou accord verbal corrigé.',
    'denominator': 'WER normalisé calculé sur ses propres tokens normalisés ; N strict et N normalisé présentés séparément. Il ne mesure pas la même unité lexicale que le WER strict.',
    'limitations': 'Pas de correction des fautes humaines (acceuille, uner, fillière...), des répétitions ou des formes pour quoi/pourquoi, parceque/parce que. La ponctuation numérique est déjà perdue dans les tokens stricts : séquences numériques adjacentes conservées et signalées ; pas de normalisation décimale revendiquée.',
}
ACCENTS = {'selection':'sélection', 'séléction':'sélection', 'selectionne':'sélectionne',
           'séléctionne':'sélectionne', 'evenement':'événement', 'évènement':'événement',
           'evenements':'événements', 'évènements':'événements', 'zero':'zéro'}
UNITS = ['zéro','un','deux','trois','quatre','cinq','six','sept','huit','neuf',
         'dix','onze','douze','treize','quatorze','quinze','seize']


def integer_words(n):
    if n < 17:return [UNITS[n]]
    if n < 20:return ['dix',UNITS[n-10]]
    if n < 70:
        d,u=divmod(n,10);base=[{2:'vingt',3:'trente',4:'quarante',5:'cinquante',6:'soixante'}[d]]
        return base+(['et','un'] if u==1 else integer_words(u) if u else [])
    if n < 80:return ['soixante']+(['et','onze'] if n==71 else integer_words(n-60))
    if n < 100:return ['quatre','vingt']+(integer_words(n-80) if n>80 else [])
    if n < 1000:
        d,u=divmod(n,100);return ([UNITS[d]] if d>1 else [])+['cent']+(integer_words(u) if u else [])
    d,u=divmod(n,1000)
    return ([UNITS[d]] if d>1 else [])+['mille']+(integer_words(u) if u else [])


def numeric_prefixes(text):
    from .wer_plan import token_view
    view,spans=token_view(text);prefixes={}
    for i,(a,b) in enumerate(spans):
        if not re.fullmatch(r'[0-9]+h?',view[a:b],re.I):continue
        before=view[spans[i-1][1] if i else 0:a].strip()
        if before in ('-','−','+'):prefixes[i]='plus' if before=='+' else 'moins'
    return prefixes


def normalize(values,prefixes=None):
    """Returns tokens AND a provenance per token, tied to strict input indices."""
    result=[];changes=[];numeric_ambiguous=[]
    clitics={'j':'je','n':'ne','d':'de','c':'ce','qu':'que','m':'me','t':'te','l':'l',
             'jusqu':'jusque','lorsqu':'lorsque','puisqu':'puisque'}
    i=0
    while i<len(values):
        source=[i];word=values[i];rules=[];out=None
        if word=='parcours' and i+1<len(values) and values[i+1]=='sup':
            source.append(i+1);out=['parcoursup'];rules.append('proper_names');i+=1
        else:
            word2=word.replace('œ','oe').replace('æ','ae')
            if word2!=word:rules.append('ligatures')
            word=word2
            parts=word.split("'",1)
            if len(parts)>1 and (parts[0] in clitics or parts[0]=='s'):
                head=('si' if parts[1] in ('il','ils') else 'se') if parts[0]=='s' else clitics[parts[0]]
                out=[head,*parts[1:]];rules.append('clitics')
            if out is None:out=[word]
            fixed=[ACCENTS.get(t,t) for t in out]
            if fixed!=out:rules.append('accents');out=fixed
            numeric=re.fullmatch(r'(0|[1-9][0-9]{0,3})(h)?',word)
            if numeric:
                adjacent=any(0<=j<len(values) and re.search(r'\d',values[j]) for j in (i-1,i+1))
                if adjacent:
                    numeric_ambiguous.append(i)
                    if prefixes and i in prefixes:out=[prefixes[i],*out]
                else:
                    n=int(numeric[1]);out=([prefixes[i]] if prefixes and i in prefixes else [])+integer_words(n)
                    if numeric[2]:out+=['heure' if n==1 else 'heures']
                    rules.append('hours' if numeric[2] else 'integers')
        for token in out:result.append({'text':token,'source_indices':source,'rules':rules[:]})
        if rules:changes.append({'source_indices':source,'before':[values[j] for j in source],'after':out,'rules':rules})
        i+=1
    numeric_words=set(UNITS+['vingt','trente','quarante','cinquante','soixante','cent'])
    for i,row in enumerate(result):
        if i and ((row['text']=='cents' and result[i-1]['text'] in numeric_words) or
                  (row['text']=='vingts' and result[i-1]['text']=='quatre')):
            old=row['text'];row['text']=old[:-1];row['rules'].append('numeric_plural')
            changes.append({'source_indices':row['source_indices'],'before':[old],'after':[row['text']],'rules':['numeric_plural']})
    return {'tokens':[r['text'] for r in result],'provenance':result,'changes':changes,
            'ambiguous_numeric_source_indices':numeric_ambiguous,'version':VERSION}
