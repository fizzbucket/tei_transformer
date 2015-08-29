try:
    from resources import custom_teitag
    custom_teitag = custom_teitag
except ImportError:
    custom_teitag = None
try:
	from resources import config
except ImportError:
	from .examples import config

config = config
