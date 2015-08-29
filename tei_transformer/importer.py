try:
    from resources import custom_teitag
    custom_teitag = custom_teitag
except ImportError:
    custom_teitag = None
try:
	from resources import config
	config = config
except ImportError:
	try:
		from .examples import config
		config = config
	except ImportError:
		config = None