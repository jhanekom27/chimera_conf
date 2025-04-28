# from chimera_conf.chimera_conf import logger
import logging

logger = logging.getLogger(__name__)


class ChimeraForm:
    """
    ChimeraForm defines the active form your configurations will take.

    By setting the form, you determine which overlays (e.g., dev, prod, local)
    are applied on top of your base configuration files.

    Each form manifests a different configuration 'creature' by layering
    additional sources onto the base config.

    Example:
        ChimeraForm.set_form("prod")
        config = MyConfig.load_config()

    If no form is explicitly set, 'local' is assumed by default.
    """

    chimera_form: str = "local"

    @classmethod
    def set_form(cls, chimera_form: str) -> None:
        logger.info("Setting chimera form to %s", chimera_form)
        cls.chimera_form = chimera_form
