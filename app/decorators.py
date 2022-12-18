import app.notifications.email as email
from app.logging import get_logger

logger = get_logger(__name__)


def log_errors(send_email: bool = False, re_raise: bool = False):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exception:
                logger.error("error catched by decorator log_errors")
                if send_email:
                    email.send_email(
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
