import json
import requests
from flask import current_app
from flask_babel import _


def translate(text, source_language, target_language):
    if 'API_KEY' not in current_app.config or \
            not current_app.config['API_KEY']:
        return _('Error: служба перевода не настроена.')

    folder_id = 'b1gi66bmhvppkpaqqcrf'
    body = {
        "sourceLanguageCode": source_language,
        "targetLanguageCode": target_language,
        "texts": text,
        "folderId": folder_id,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {current_app.config['API_KEY']}"
    }

    r = requests.post('https://translate.api.cloud.yandex.net/translate/v2/translate',
                      json=body,
                      headers=headers)

    if r.status_code != 200:
        return _(f'Error: ошибка службы перевода {r.status_code}')
    return r.json()['translations'][0]['text']

