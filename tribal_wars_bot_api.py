import inspect
import threading

import requests

from app_logging import get_logger
from config import PYTHON_ANYWHERE_API, PYTHON_ANYWHERE_API_TOKEN

logger = get_logger(__name__)


def threaded(func):
    def wrapper(*args, **kwargs):
        signature = inspect.signature(func)

        kwargs.update(
            {
                key: value.default
                for key, value in signature.parameters.items()
                if value.default != inspect.Signature.empty and key not in kwargs
            }
        )

        def log_response_on_error(
            self: "TribalWarsBotApi", *args, **kwargs
        ) -> requests.Response | bool:
            """Run wrapped function and after that log response errors"""

            try:
                self.response: requests.Response = func(self, *args, **kwargs)
            except BaseException:
                logger.error("Connection error")
                return False
            if self.response.status_code >= 400:
                logger.error(f"{self.response.status_code} {self.response.text}")
            return self.response

        # Wait for response
        if kwargs["sync"]:
            return log_response_on_error(*args, **kwargs)
        # Skip waiting
        else:
            threading.Thread(
                target=log_response_on_error, args=args, kwargs=kwargs
            ).start()

    return wrapper


class TribalWarsBotApi:
    base_url = PYTHON_ANYWHERE_API
    headers = {
        "Content-Type": "application/json",
        "Authorization": PYTHON_ANYWHERE_API_TOKEN,
    }

    def __init__(self, endpoint: str, json: dict = {}) -> None:
        self.url = self.base_url + endpoint
        self.json = json

    @threaded
    def get(self, sync: bool = True, **kwargs) -> requests.Response:
        self.response = requests.get(self.url, headers=self.headers, **kwargs)
        return self.response

    @threaded
    def patch(self, sync: bool = True, **kwargs) -> requests.Response:
        self.response = requests.patch(
            self.url, json=self.json, headers=self.headers, **kwargs
        )
        return self.response

    @threaded
    def post(self, sync: bool = True, **kwargs) -> requests.Response:
        self.response = requests.post(
            self.url, json=self.json, headers=self.headers, **kwargs
        )
        return self.response

    @threaded
    def put(self, sync: bool = True, **kwargs) -> requests.Response:
        self.response = requests.put(
            self.url, json=self.json, headers=self.headers, **kwargs
        )
        return self.response
