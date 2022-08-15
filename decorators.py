import logging
import traceback

import email_notifications

logger = logging.getLogger(__name__)
f_handler = logging.FileHandler("logs/log.txt")
f_format = logging.Formatter(
    "\n%(levelname)s:%(name)s:%(asctime)s %(message)s", datefmt="%d-%m-%Y %H:%M:%S"
)
f_handler.setFormatter(f_format)
logger.addHandler(f_handler)
logger.propagate = False


def log_errors(send_email: bool = False):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except:
                error_str = traceback.format_exc()
                error_str = error_str[: error_str.find("Stacktrace")]
                logger.error(f"\n{error_str}\n")
                if not send_email:
                    return
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

        return wrapper

    return decorator
