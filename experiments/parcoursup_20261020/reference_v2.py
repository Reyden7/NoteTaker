"""Freeze the independent human reference before reading revised model outputs."""
from .prepare import OUT, read, write_new, sha
from .import_human import V2


def main():
    reference = read(OUT/'reference-operationnalisee.json')
    reference['status'] = 'Analyst operationalization of human narrative, refined by user-supplied corrected excerpt; not Qwen judgments.'
    reference['human_correction_sha256'] = sha(V2/'correction-humaine-originale.txt')
    reference['timing_limit'] = 'Human retained original timestamp markers; word-level boundaries have not been re-aligned or independently measured.'
    for point in reference['points']:
        point['human_corrected_verbatim_available'] = True
    h03 = next(p for p in reference['points'] if p['id']=='H03')
    h03['content'] = 'Arthur Berdah conteste Manès et décrit la sélection premier arrivé/premier servi ; Bruno rappelle le tirage au sort, sans affirmer que Parcoursup est le bon système.'
    h03['refinement'] = 'The later human corrected excerpt supersedes the broad narrative attribution to Bruno for the first-come-first-served interruption.'
    h03['source_ids_proposed_by_analyst'] = ['s499-0','s500-0','s502-0','s504-0','s508-0','s509-0','s511-0']
    reference['additional_human_verbatim_points'] = [
        {'id':'V01','content':'Manès répond à Louise : la sélection repose surtout sur les notes, certaines formations utilisant les lettres de motivation.',
         'source_ids':['s560-0','s561-0','s562-0','s562-1','s563-0','s564-0','s566-0','s567-0']},
        {'id':'V02','content':'Louise interroge la moindre sélection ; Manès réagit par une question incrédule à son affirmation que la sélection serait faible. Ce n’est pas un accord.',
         'source_ids':['s551-0','s553-0','s554-0','s555-0']}
    ]
    reference['evaluation_warning'] = 'Compare the original eleven narrative points separately from the two additional verbatim points. A single analyst coding against human sources is not a blind second human rating, nor a validated aggregate quality score.'
    write_new(V2/'reference-independante-v2.json',reference)


if __name__=='__main__': main()
