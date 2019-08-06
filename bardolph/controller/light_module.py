from ..lib import clock
from ..lib import log_config
from ..lib.i_lib import Settings
from ..lib.injection import provide

def configure():
    log_config.configure()
    clock.configure()

    settings = provide(Settings)
    if settings.get_value('use_fakes'):
        import tests.fake_light_set as fake_light_set
        fake_light_set.configure()
    else:
        from . import light_set
        light_set.configure()
