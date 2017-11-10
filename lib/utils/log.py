
import logging

logger = logging.Logger('craftr')
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('[%(levelname)s]: %(message)s'))
logger.addHandler(handler)

module.exports = logger
