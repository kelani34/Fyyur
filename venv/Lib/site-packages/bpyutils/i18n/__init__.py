from bpyutils.i18n.util import get_locale

def _(string):
    locale = get_locale()
    
    return string

def register(module):
    pass