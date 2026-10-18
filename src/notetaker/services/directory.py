"""Civil municipal directory only. No voice model, recording or biometric data."""
import json
import unicodedata
import uuid
from .storage import encoded

ATTENDANCE = {'unconfirmed': 'À renseigner', 'present': 'Présent', 'absent': 'Absent',
              'excused': 'Excusé', 'represented': 'Représenté'}
PERSON_FIELDS = ('first_name', 'last_name', 'position', 'municipality')


def folded(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))


def person_name(person):
    return f"{person['first_name']} {person['last_name']}".strip()


class DirectoryService:
    def __init__(self, store):
        self.store, self.db = store, store.db

    def get_person(self, pid):
        row = self.db.execute('SELECT * FROM directory_person WHERE id=?', (pid,)).fetchone()
        if row is None:
            raise ValueError('Intervenant introuvable dans l’annuaire.')
        return dict(row)

    def list_people(self, query='', municipality='', status='active'):
        if status not in ('active', 'archived', 'all'):
            raise ValueError('Filtre d’annuaire invalide.')
        tokens = folded(query).split()
        people = [dict(r) for r in self.db.execute('SELECT * FROM directory_person')]
        return sorted((p for p in people if (status == 'all' or bool(p['archived']) == (status == 'archived'))
            and (not municipality or folded(p['municipality']) == folded(municipality))
            and all(t in folded(' '.join(p[k] for k in PERSON_FIELDS)) for t in tokens)),
            key=lambda p: (folded(p['last_name']), folded(p['first_name']), p['id']))

    def save_person(self, values, pid=None, expected_revision=None):
        values = {k: str(values.get(k, '')).strip() for k in PERSON_FIELDS}
        if not values['first_name'] or not values['last_name']:
            raise ValueError('Le prénom et le nom sont obligatoires.')
        if any(len(v) > 200 or any(ord(c) < 32 for c in v) for v in values.values()):
            raise ValueError('Chaque champ doit tenir sur une ligne de 200 caractères maximum.')
        with self.db:
            if pid:
                self.db.execute('UPDATE directory_person SET revision=revision WHERE id=?', (pid,))
                before = self.get_person(pid)
                if expected_revision is not None and before['revision'] != expected_revision:
                    raise ValueError('La fiche a été modifiée. Rouvrez-la avant de sauvegarder.')
                if all(before[k] == v for k, v in values.items()):
                    return pid
                self.db.execute("INSERT INTO directory_history(person_id,action,content_json) VALUES(?,'edit',?)", (pid, encoded(before)))
                self.db.execute('UPDATE directory_person SET first_name=?,last_name=?,position=?,municipality=?,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?', (*values.values(), pid))
            else:
                pid = str(uuid.uuid4())
                self.db.execute('INSERT INTO directory_person(id,first_name,last_name,position,municipality) VALUES(?,?,?,?,?)', (pid, *values.values()))
                self.db.execute("INSERT INTO directory_history(person_id,action,content_json) VALUES(?,'create',?)", (pid, encoded(values)))
        return pid

    def archive_person(self, pid, archived, expected_revision=None):
        with self.db:
            self.db.execute('UPDATE directory_person SET revision=revision WHERE id=?', (pid,))
            before = self.get_person(pid)
            if expected_revision is not None and before['revision'] != expected_revision:
                raise ValueError('La fiche a été modifiée. Rouvrez-la avant de poursuivre.')
            if bool(before['archived']) == bool(archived):
                return
            self.db.execute('INSERT INTO directory_history(person_id,action,content_json) VALUES(?,?,?)',
                            (pid, 'archive' if archived else 'reactivate', encoded(before)))
            self.db.execute('UPDATE directory_person SET archived=?,revision=revision+1,updated_at=CURRENT_TIMESTAMP WHERE id=?', (int(bool(archived)), pid))

    def history(self, pid):
        return [dict(r) for r in self.db.execute('SELECT * FROM directory_history WHERE person_id=? ORDER BY id DESC', (pid,))]

    def participants(self, sid):
        return [{**dict(r), 'snapshot': json.loads(r['snapshot_json'])} for r in self.db.execute(
            'SELECT * FROM session_participant WHERE session_id=? ORDER BY sort_order,person_id', (sid,))]

    def save_participants(self, sid, rows, expected=None):
        with self.db:
            self.db.execute('UPDATE session SET revision=revision WHERE id=?', (sid,))
            self.store.get(sid)  # refuse a missing session before writing
            before = self.participants(sid)
            if expected is not None and before != expected:
                raise ValueError('Les présences ont changé. Rechargez la séance avant de poursuivre.')
            previous = {p['person_id']: p for p in before}
            ids = [r['person_id'] for r in rows]
            if len(set(ids)) != len(ids):
                raise ValueError('Une personne ne peut figurer qu’une fois dans la séance.')
            normalized = []
            for index, r in enumerate(rows):
                person = self.get_person(r['person_id'])
                if person['archived'] and person['id'] not in previous:
                    raise ValueError('Réactivez cette fiche avant de l’ajouter à une nouvelle séance.')
                attendance = r.get('attendance', 'unconfirmed')
                if attendance not in ATTENDANCE:
                    raise ValueError('Présence invalide.')
                role, note = str(r.get('session_role', '')).strip(), str(r.get('proxy_note', '')).strip()
                if len(role) > 200 or len(note) > 1000:
                    raise ValueError('Rôle ou référence de procuration trop long.')
                holder = r.get('proxy_to_person_id') or None
                if attendance == 'represented':
                    target = next((p for p in rows if p['person_id'] == holder), None)
                    if holder == person['id'] or target is None or target.get('attendance') != 'present':
                        raise ValueError('Une personne représentée doit désigner un autre participant présent comme mandataire.')
                elif holder or note:
                    raise ValueError('Les informations de procuration sont réservées au statut « Représenté ».')
                snapshot = previous[person['id']]['snapshot'] if person['id'] in previous else {k: person[k] for k in PERSON_FIELDS}
                normalized.append({'session_id': sid, 'person_id': person['id'], 'snapshot_json': encoded(snapshot),
                    'attendance': attendance, 'session_role': role, 'proxy_to_person_id': holder,
                    'proxy_note': note, 'sort_order': index, 'snapshot': snapshot})
            if before == normalized:
                return
            self.db.execute("INSERT INTO edit_history(session_id,kind,content_json) VALUES(?,'participants',?)", (sid, encoded(before)))
            self.db.execute('DELETE FROM session_participant WHERE session_id=?', (sid,))
            for r in normalized:
                self.db.execute('INSERT INTO session_participant VALUES(?,?,?,?,?,?,?,?)', tuple(r[k] for k in
                    ('session_id', 'person_id', 'snapshot_json', 'attendance', 'session_role', 'proxy_to_person_id', 'proxy_note', 'sort_order')))
            self.store._changed(sid)

    def assign_person(self, sid, utterance_ids, pid):
        with self.db:
            self.db.execute('UPDATE session SET revision=revision WHERE id=?', (sid,))
            state = self.store.get(sid)
            participant = next((p for p in self.participants(sid) if p['person_id'] == pid), None)
            if participant is None:
                raise ValueError('Ajoutez d’abord cette personne aux participants de la séance.')
            selected = set(utterance_ids)
            if not selected or not selected <= {u['id'] for u in state['utterances']}:
                raise ValueError('Sélectionnez au moins une intervention existante.')
            self.db.execute("INSERT INTO edit_history(session_id,kind,content_json) VALUES(?,'directory_assignment',?)", (sid, encoded({'utterances': state['utterances'], 'speakers': state['speakers']})))
            speaker = 'directory-' + pid
            label = person_name(participant['snapshot'])
            self.db.execute('INSERT INTO speaker(id,session_id,label) VALUES(?,?,?) ON CONFLICT(id,session_id) DO UPDATE SET label=excluded.label', (speaker, sid, label))
            for u in state['utterances']:
                if u['id'] in selected:
                    source = json.loads(u['source_json'])
                    source.update({'automatic_attribution': False, 'directory_person_id': pid,
                                   'directory_snapshot': participant['snapshot']})
                    self.db.execute('UPDATE utterance SET speaker_id=?,uncertain=0,source_json=? WHERE session_id=? AND id=?',
                                    (speaker, encoded(source), sid, u['id']))
            self.store._changed(sid)


def participant_lines(rows):
    by_id = {p['person_id']: person_name(p['snapshot']) for p in rows}
    for p in rows:
        civil = p['snapshot']
        text = f"{person_name(civil)} — {ATTENDANCE[p['attendance']]}"
        if civil.get('position'):
            text += f" ; fonction : {civil['position']}"
        if p['session_role']:
            text += f" ; rôle dans la séance : {p['session_role']}"
        if p['proxy_to_person_id']:
            text += f" ; procuration à {by_id[p['proxy_to_person_id']]}"
        if p['proxy_note']:
            text += f" ({p['proxy_note']})"
        yield text
