"""Shared UI localization for all 1.0 editing windows."""
import json
from pathlib import Path
from functools import lru_cache

LANGUAGES = dict(zip(
    ['简体中文','繁體中文','English','Français','Deutsch','Polski','Русский','Español (España)','Italiano','日本語','Português (Brasil)','Magyar','한국어','Українська','Български','Türkçe','Slovenčina','Čeština'],
    ['zh-CN','zh-TW','en','fr','de','pl','ru','es','it','ja','pt-BR','hu','ko','uk','bg','tr','sk','cs']))

@lru_cache(maxsize=18)
def catalogue(language):
    code=LANGUAGES.get(language,'en')
    return json.loads((Path(__file__).parent/'locales'/(code+'.json')).read_text(encoding='utf8'))

def translate(language,english):
    return catalogue(language).get(english,english)

def translator(language):
    return lambda zh,en:translate(language,en)

def error(language,exc):
    # System paths, library diagnostics and other variable details stay verbatim.
    return translate(language,'Error details:')+'\n'+translate(language,str(exc))
