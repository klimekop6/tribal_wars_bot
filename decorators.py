import logging

import email_notifications
from app_logging import CustomLogFormatter

logger = logging.getLogger(__name__)
f_handler = logging.FileHandler("logs/log.txt")
f_format = CustomLogFormatter(
    "%(levelname)s | %(name)s | %(asctime)s %(message)s", datefmt="%d-%m-%Y %H:%M:%S"
)
f_handler.setFormatter(f_format)
logger.addHandler(f_handler)
logger.propagate = False


def log_errors(send_email: bool = False, re_raise: bool = False):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BaseException as exception:
                logger.error("error catched by decorator log_errors")
                if send_email:
                    email_notifications.send_email(
                        email_recepients=kwargs["settings"]["notifications"][
                            "email_address"
                        ],
                        email_subject="TribalWars Error",
                        email_body=f"Aplikacja została zatrzymana w wyniku krytycznego błędu.\n\n"
                        f"Możliwe szybkie rozwiązania:\n"
                        f"- uruchom ponownie aplikację\n\n"
                        f"Jeżeli problem nadal występuję poinformuj mnie na k.spec@tuta.io",
                    )
                if re_raise:
                    raise exception

        return wrapper

    return decorator
