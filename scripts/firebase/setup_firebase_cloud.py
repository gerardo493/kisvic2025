# -*- coding: utf-8 -*-
"""Habilita Firestore y genera credenciales usando la sesión de Firebase CLI."""
import base64
import json
import os
import time
import urllib.request
import urllib.error

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT = 'kisvic-facturacion'
CONFIGSTORE = os.path.join(
    os.environ.get('APPDATA', os.path.expanduser('~')),
    '..', '.config', 'configstore', 'firebase-tools.json'
)
CONFIGSTORE = os.path.normpath(CONFIGSTORE)
CRED_OUT = os.path.join(BASE, 'firebase_credentials.json')
CONFIG_OUT = os.path.join(BASE, 'firebase_config.json')


def _token_desde_firebase_cli():
    path = CONFIGSTORE
    if not os.path.exists(path):
        alt = os.path.expanduser('~/.config/configstore/firebase-tools.json')
        path = alt if os.path.exists(alt) else path
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    tokens = data.get('tokens', {})
    if tokens.get('expires_at', 0) < int(time.time() * 1000) + 60000:
        return _refresh_token(tokens.get('refresh_token'))
    return tokens['access_token']


def _refresh_token(refresh_token):
    body = json.dumps({
        'client_id': '563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com',
        'client_secret': 'j9iVZfS8kkCEFUPaAeJV0sAi',
        'refresh_token': refresh_token,
        'grant_type': 'refresh_token',
    }).encode()
    req = urllib.request.Request(
        'https://oauth2.googleapis.com/token',
        data=body,
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)['access_token']


def _api(method, url, token, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f'{e.code} {url}: {body[:500]}') from e


def habilitar_api(token, servicio):
    url = (
        f'https://serviceusage.googleapis.com/v1/projects/{PROJECT}'
        f'/services/{servicio}:enable'
    )
    try:
        _api('POST', url, token)
        print(f'  API habilitada: {servicio}')
    except RuntimeError as e:
        if 'ALREADY_ENABLED' in str(e) or '409' in str(e):
            print(f'  API ya activa: {servicio}')
        else:
            raise


def crear_firestore(token):
    url = f'https://firestore.googleapis.com/v1/projects/{PROJECT}/databases?databaseId=(default)'
    payload = {'type': 'FIRESTORE_NATIVE', 'locationId': 'nam5'}
    try:
        _api('POST', url, token, payload)
        print('  Base Firestore creada (nam5)')
    except RuntimeError as e:
        if 'ALREADY_EXISTS' in str(e) or '409' in str(e):
            print('  Firestore ya existe')
        else:
            raise


def crear_cuenta_servicio_y_clave(token):
    sa_id = 'firebase-kisvic-admin'
    email = f'{sa_id}@{PROJECT}.iam.gserviceaccount.com'
    create_url = f'https://iam.googleapis.com/v1/projects/{PROJECT}/serviceAccounts'
    try:
        _api('POST', create_url, token, {
            'accountId': sa_id,
            'serviceAccount': {'displayName': 'Kisvic Firebase Admin'},
        })
        print(f'  Cuenta de servicio creada: {email}')
    except RuntimeError as e:
        if 'already exists' in str(e).lower() or '409' in str(e):
            print(f'  Cuenta de servicio existente: {email}')
        else:
            raise

    key_url = f'https://iam.googleapis.com/v1/projects/{PROJECT}/serviceAccounts/{email}/keys'
    key_data = _api('POST', key_url, token, {
        'privateKeyType': 'TYPE_GOOGLE_CREDENTIALS_FILE',
        'keyAlgorithm': 'KEY_ALG_RSA_2048',
    })
    private = json.loads(base64.b64decode(key_data['privateKeyData']))
    with open(CRED_OUT, 'w', encoding='utf-8') as f:
        json.dump(private, f, indent=2)
    print(f'  Credenciales guardadas en firebase_credentials.json')

    # Rol de datos Firestore para la cuenta de servicio
    role_url = (
        f'https://cloudresourcemanager.googleapis.com/v1/projects/{PROJECT}'
        f':getIamPolicy'
    )
    try:
        policy = _api('POST', role_url, token, {})
        member = f'serviceAccount:{email}'
        roles = ('roles/datastore.user', 'roles/editor')
        for role in roles:
            found = False
            for b in policy.get('bindings', []):
                if b.get('role') == role:
                    if member not in b.get('members', []):
                        b['members'].append(member)
                    found = True
                    break
            if not found:
                policy.setdefault('bindings', []).append({
                    'role': role,
                    'members': [member],
                })
        set_url = (
            f'https://cloudresourcemanager.googleapis.com/v1/projects/{PROJECT}'
            f':setIamPolicy'
        )
        _api('POST', set_url, token, {'policy': policy})
        print('  Permisos IAM asignados')
    except Exception as e:
        print(f'  Aviso IAM (puede ignorarse si Firestore ya funciona): {e}')


def main():
    print(f'Configurando proyecto Firebase: {PROJECT}')
    token = _token_desde_firebase_cli()
    for api in (
        'cloudresourcemanager.googleapis.com',
        'iam.googleapis.com',
        'serviceusage.googleapis.com',
        'firestore.googleapis.com',
    ):
        habilitar_api(token, api)
    time.sleep(5)
    crear_firestore(token)
    crear_cuenta_servicio_y_clave(token)
    with open(CONFIG_OUT, 'w', encoding='utf-8') as f:
        json.dump({
            'use_firebase': True,
            'project_id': PROJECT,
            'credentials_path': 'firebase_credentials.json',
        }, f, indent=2)
    print('  firebase_config.json actualizado')
    os.environ['KISVIC_USE_FIREBASE'] = '1'
    from almacenamiento import migrar_todo_a_firebase, usar_firebase
    if usar_firebase():
        print('Migrando datos locales a Firestore...')
        res = migrar_todo_a_firebase()
        ok = sum(1 for v in res.values() if v)
        print(f'Migración completada: {ok}/{len(res)} archivos')
        with open(os.path.join(BASE, '.firebase_migrado'), 'w') as f:
            f.write('ok')
    print('Listo. Ejecuta: python app.py')


if __name__ == '__main__':
    main()
