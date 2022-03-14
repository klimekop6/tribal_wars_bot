import logging
import time
import traceback

import email_notifications

logging.basicConfig(filename="log.txt", level=logging.WARNING)


def log_missed_erros(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except:
            error_str = traceback.format_exc()
            error_str = error_str[: error_str.find("Stacktrace")]
            logging.error(
                f'{time.strftime("%d.%m.%Y %H:%M:%S", time.localtime())}\n'
                f"{error_str}\n"
            )
            email_notifications.send_email(
                email_recepients=kwargs["settings"]["notifications"]["email_address"],
                email_subject="TribalWars Error",
                email_body=f"Aplikacja została zatrzymana w wyniku krytycznego błędu.\n\n"
                f"Możliwe szybkie rozwiązania:\n"
                f"- uruchom ponownie aplikację\n\n"
                f"Jeżeli problem nadal występuję poinformuj mnie na k.spec@tuta.io",
            )

    return wrapper
