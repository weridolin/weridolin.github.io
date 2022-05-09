
import logging
messages = []
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# logger.addHandler(logging.StreamHandler())
# class ListenFilter(logging.Filter):

#     def filter(self, record):
#         """Determine which log records to output.Returns 0 for no, nonzero for yes.
#         """
#         if record.getMessage().startswith('i am filter'):
#             return False
#         return True
# _filter = ListenFilter()
# logger.addFilter(filter=_filter)
# logger.debug("i am filter >>>>")
# logger.debug("i am not filter >>>>")

# class RequestsHandler(logging.Handler):
#     def emit(self, record):
#         """Send the log records (created by loggers) to
#         the appropriate destination.
#         """
#         print("deal message",record.getMessage())
#         messages.append(record.getMessage())

# handler = RequestsHandler()
# logger.addHandler(handler)

# logger.info(">>> iiiiiiiiii")

# filter_ = ListenFilter()
# logger.addFilter(filter_)

# # log I want
# logger.info("logme: Howdy!")


# # log i want to skip
# logger.info("dont: I'm doing great!")

# # prints ['logme: Howdy!']
# print(messages)


from logging import LoggerAdapter

class LoggerInterceptor(LoggerAdapter):

    def process(self, msg, kwargs):
        msg = str(msg)+"i am interceptor"
        return super().process(msg, kwargs)

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)
_logger.addHandler(logging.StreamHandler())
logger = LoggerInterceptor(logger=_logger,extra={"extra_option":"Var1"})
logger.info(">>>>>>>")

