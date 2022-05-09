from FileLineRotating import FileLineRotatingHandler
import logging
logger = logging.getLogger(__file__)
# Add the log message handler to the logger
handler = FileLineRotatingHandler("test.log.0", maxline = 10,backupCount=2)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

for i in range(60):
    logger.info(f">>>> {i}")
