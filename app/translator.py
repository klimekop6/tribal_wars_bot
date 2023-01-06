import functools
import os
import random
import re
import sys
import time
import urllib.parse
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple, Union

import execjs
import lxml.etree
import requests


class Tse:
    def __init__(self):
        self.author = "Ulion.Tse"
        self.begin_time = time.time()
        self.default_session_seconds = 1.5e3
        self.transform_en_translator_pool = (
            "Itranslate",
            "Lingvanex",
        )
        self.auto_pool = (
            "auto",
            "auto-detect",
        )
        self.zh_pool = (
            "zh",
            "zh-CN",
            "zh-CHS",
            "zh-Hans",
            "zh-Hans_CN",
            "cn",
            "chi",
        )

    @staticmethod
    def time_stat(func):
        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            if_show_time_stat = kwargs.get("if_show_time_stat", False)
            show_time_stat_precision = kwargs.get("show_time_stat_precision", 4)
            sleep_seconds = kwargs.get("sleep_seconds", None)

            if if_show_time_stat and sleep_seconds is None:
                raise TranslatorError(
                    "Uncertainty of measurement! Please specify parameter [sleep_seconds]."
                )

            if if_show_time_stat and sleep_seconds >= 0:
                t1 = time.time()
                result = func(*args, **kwargs)
                t2 = time.time()
                cost_time = round((t2 - t1 - sleep_seconds), show_time_stat_precision)
                sys.stderr.write(
                    f"CostTime(function: {func.__name__[:-4]}): {cost_time}s\n"
                )
                return result
            return func(*args, **kwargs)

        return _wrapper

    @staticmethod
    def get_headers(
        host_url: str,
        if_api: bool = False,
        if_referer_for_host: bool = True,
        if_ajax_for_api: bool = True,
        if_json_for_api: bool = False,
        if_multipart_for_api: bool = False,
    ) -> dict:

        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
        url_path = urllib.parse.urlparse(host_url).path
        host_headers = {
            "Referer" if if_referer_for_host else "Host": host_url,
            "User-Agent": user_agent,
        }
        api_headers = {
            "Origin": host_url.split(url_path)[0] if url_path else host_url,
            "Referer": host_url,
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": user_agent,
        }
        if if_api and not if_ajax_for_api:
            api_headers.pop("X-Requested-With")
            api_headers.update({"Content-Type": "text/plain"})
        if if_api and if_json_for_api:
            api_headers.update({"Content-Type": "application/json"})
        if if_api and if_multipart_for_api:
            api_headers.pop("Content-Type")
        return host_headers if not if_api else api_headers

    def check_en_lang(
        self,
        from_lang: str,
        to_lang: str,
        default_translator: str = None,
        default_lang: str = "en-US",
    ):
        if default_translator in self.transform_en_translator_pool:
            from_lang = default_lang if from_lang == "en" else from_lang
            to_lang = default_lang if to_lang == "en" else to_lang
            from_lang = (
                default_lang.replace("-", "_")
                if default_translator == "Lingvanex" and from_lang[:3] == "en-"
                else from_lang
            )
            to_lang = (
                default_lang.replace("-", "_")
                if default_translator == "Lingvanex" and to_lang[:3] == "en-"
                else to_lang
            )
        return from_lang, to_lang

    def check_language(
        self,
        from_language: str,
        to_language: str,
        language_map: dict,
        output_auto: str = "auto",
        output_zh: str = "zh",
        output_en_translator: str = None,
        output_en: str = "en-US",
    ) -> Tuple[str, str]:

        if output_en_translator:
            from_language, to_language = self.check_en_lang(
                from_language, to_language, output_en_translator, output_en
            )

        from_language = (
            output_auto if from_language in self.auto_pool else from_language
        )
        from_language = output_zh if from_language in self.zh_pool else from_language
        to_language = output_zh if to_language in self.zh_pool else to_language

        if from_language != output_auto and from_language not in language_map:
            raise TranslatorError(
                "Unsupported from_language[{}] in {}.".format(
                    from_language, sorted(language_map.keys())
                )
            )
        elif to_language not in language_map:
            raise TranslatorError(
                "Unsupported to_language[{}] in {}.".format(
                    to_language, sorted(language_map.keys())
                )
            )
        elif (
            from_language != output_auto
            and to_language not in language_map[from_language]
        ):
            raise TranslatorError(
                "Unsupported translation: from [{0}] to [{1}]!".format(
                    from_language, to_language
                )
            )
        elif from_language == to_language:
            raise TranslatorError(
                f"from_language[{from_language}] and to_language[{to_language}] should not be same."
            )
        return from_language, to_language

    @staticmethod
    def debug_language_map(func):
        def make_temp_language_map(from_language: str, to_language: str) -> dict:
            if not (to_language != "auto" and from_language != to_language):
                raise TranslatorError
            lang_list = [from_language, to_language]
            auto_lang_dict = {from_language: [to_language], to_language: [to_language]}
            return (
                {}.fromkeys(lang_list, lang_list)
                if from_language != "auto"
                else auto_lang_dict
            )

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                warnings.warn(str(e))
                return make_temp_language_map(
                    kwargs.get("from_language"), kwargs.get("to_language")
                )

        return _wrapper

    @staticmethod
    def check_query(func):
        def check_query_text(
            query_text: str,
            if_ignore_empty_query: bool,
            if_ignore_limit_of_length: bool,
            limit_of_length: int,
        ) -> str:

            if not isinstance(query_text, str):
                raise TranslatorError

            query_text = query_text.strip()
            qt_length = len(query_text)
            if qt_length == 0 and not if_ignore_empty_query:
                raise TranslatorError("The `query_text` can't be empty!")
            if qt_length >= limit_of_length and not if_ignore_limit_of_length:
                raise TranslatorError("The length of `query_text` exceeds the limit.")
            else:
                if qt_length >= limit_of_length:
                    warnings.warn(f"The translation ignored the excess.")
                    warnings.warn(
                        f"The length of `query_text` is {qt_length}, above {limit_of_length}."
                    )
                    return query_text[: limit_of_length - 1]
            return query_text

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            if_ignore_empty_query = kwargs.get("if_ignore_empty_query", False)
            if_ignore_limit_of_length = kwargs.get("if_ignore_limit_of_length", False)
            limit_of_length = kwargs.get("limit_of_length", 5000)
            is_detail_result = kwargs.get("is_detail_result", False)

            query_text = list(args)[1] if len(args) >= 2 else kwargs.get("query_text")
            query_text = check_query_text(
                query_text,
                if_ignore_empty_query,
                if_ignore_limit_of_length,
                limit_of_length,
            )
            if not query_text and if_ignore_empty_query:
                return {"data": query_text} if is_detail_result else query_text

            if len(args) >= 2:
                new_args = list(args)
                new_args[1] = query_text
                return func(*tuple(new_args), **kwargs)
            return func(*args, **{**kwargs, **{"query_text": query_text}})

        return _wrapper


class GuestSeverRegion(Tse):
    def __init__(self):
        super().__init__()
        self.get_addr_url = (
            "https://geolocation.onetrust.com/cookieconsentpub/v1/geo/location"
        )
        self.get_ip_url = "https://httpbin.org/ip"
        self.ip_api_addr_url = "http://ip-api.com/json"
        self.ip_tb_add_url = "https://ip.taobao.com/outGetIpInfo"
        self.default_country = os.environ.get("translators_default_country", None)

    @property
    def get_server_region(self):
        _headers_fn = lambda url: self.get_headers(
            url, if_api=False, if_referer_for_host=True
        )
        try:
            try:
                data = eval(
                    requests.get(
                        self.get_addr_url, headers=_headers_fn(self.get_addr_url)
                    ).text[9:-2]
                )
                sys.stderr.write(
                    f'Using state {data.get("stateName")} server backend.\n'
                )
                return data.get("country")
            except requests.exceptions.Timeout:
                ip_address = requests.get(
                    self.get_ip_url, headers=_headers_fn(self.get_ip_url)
                ).json()["origin"]
                form_data = {"ip": ip_address, "accessKey": "alibaba-inc"}
                data = (
                    requests.post(
                        url=self.ip_tb_add_url,
                        data=form_data,
                        headers=_headers_fn(self.ip_tb_add_url),
                    )
                    .json()
                    .get("data")
                )
                return data.get("country_id")

        except requests.exceptions.ConnectionError:
            raise TranslatorError("Unable to connect the Internet.\n")
        except:
            warnings.warn("Unable to find server backend.\n")
            country = self.default_country or input(
                "Please input your server region need to visit:\neg: [Qatar, China, ...]\n"
            )
            sys.stderr.write(f"Using country {country} server backend.\n")
            return "CN" if country == "China" else "EN"


class TranslatorError(Exception):
    pass


class Bing(Tse):
    def __init__(self, server_region="EN"):
        super().__init__()
        self.host_url = None
        self.cn_host_url = "https://cn.bing.com/Translator"
        self.en_host_url = "https://www.bing.com/Translator"
        self.server_region = server_region
        self.api_url = None
        self.host_headers = None
        self.api_headers = None
        self.language_map = None
        self.session = None
        self.tk = None
        self.ig_iid = None
        self.query_count = 0
        self.output_auto = "auto-detect"
        self.output_zh = "zh-Hans"
        self.input_limit = 1000

    @Tse.debug_language_map
    def get_language_map(self, host_html, **kwargs):
        et = lxml.etree.HTML(host_html)
        lang_list = et.xpath('//*[@id="tta_srcsl"]/option/@value') or et.xpath(
            '//*[@id="t_srcAllLang"]/option/@value'
        )
        lang_list = sorted(list(set(lang_list)))
        return {}.fromkeys(lang_list, lang_list)

    def get_ig_iid(self, host_html):
        et = lxml.etree.HTML(host_html)
        iid = et.xpath('//*[@id="rich_tta"]/@data-iid')[0]
        ig = re.compile('IG:"(.*?)"').findall(host_html)[0]
        return {"iid": iid, "ig": ig}

    def get_tk(self, host_html):
        result_str = re.compile("var params_RichTranslateHelper = (.*?);").findall(
            host_html
        )[0]
        result = execjs.eval(result_str)
        return {"key": result[0], "token": result[1]}

    @Tse.time_stat
    @Tse.check_query
    def bing_api(
        self,
        query_text: str,
        from_language: str = "auto",
        to_language: str = "en",
        **kwargs,
    ) -> Union[str, list]:

        timeout = kwargs.get("timeout", None)
        proxies = kwargs.get("proxies", None)
        is_detail_result = kwargs.get("is_detail_result", False)
        sleep_seconds = kwargs.get("sleep_seconds", random.random())
        update_session_after_seconds = kwargs.get(
            "update_session_after_seconds", self.default_session_seconds
        )

        use_cn_condition = (
            kwargs.get("if_use_cn_host", None) or self.server_region == "CN"
        )
        self.host_url = self.cn_host_url if use_cn_condition else self.en_host_url
        self.api_url = self.host_url.replace("Translator", "ttranslatev3")
        self.host_headers = self.get_headers(self.host_url, if_api=False)
        self.api_headers = self.get_headers(self.host_url, if_api=True)

        not_update_cond_time = (
            1 if time.time() - self.begin_time < update_session_after_seconds else 0
        )
        if not (
            self.session
            and not_update_cond_time
            and self.language_map
            and self.tk
            and self.ig_iid
        ):
            self.session = requests.Session()
            host_html = self.session.get(
                self.host_url,
                headers=self.host_headers,
                timeout=timeout,
                proxies=proxies,
            ).text
            self.tk = self.get_tk(host_html)
            self.ig_iid = self.get_ig_iid(host_html)
            self.language_map = self.get_language_map(
                host_html, from_language=from_language, to_language=to_language
            )

        from_language, to_language = self.check_language(
            from_language,
            to_language,
            self.language_map,
            output_zh=self.output_zh,
            output_auto=self.output_auto,
        )

        form_data = {
            **{"text": query_text, "fromLang": from_language, "to": to_language},
            **self.tk,
        }
        api_url_param = f'?isVertical=1&&IG={self.ig_iid["ig"]}&IID={self.ig_iid["iid"]}.{self.query_count + 1}'
        api_url = "".join([self.api_url, api_url_param])
        r = self.session.post(
            api_url,
            headers=self.host_headers,
            data=form_data,
            timeout=timeout,
            proxies=proxies,
        )
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep_seconds)
        self.query_count += 1
        return data if is_detail_result else data[0]["translations"][0]["text"]


class TranslatorsServer:
    _instance = None

    def __new__(cls: "TranslatorsServer", *args, **kwargs) -> "TranslatorsServer":
        if not cls._instance:
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if hasattr(self, "server_region"):
            return
        self.server_region = GuestSeverRegion().get_server_region
        self._bing = Bing(server_region=self.server_region)
        self.bing = self._bing.bing_api
        self.translators_dict = {"bing": self.bing}
        self.translators_pool = list(self.translators_dict.keys())

    def translate_text(
        self,
        query_text: str,
        translator: str = "bing",
        from_language: str = "auto",
        to_language: str = "en",
        **kwargs,
    ) -> Union[str, dict]:

        if translator not in self.translators_pool:
            raise TranslatorError
        return self.translators_dict[translator](
            query_text=query_text,
            from_language=from_language,
            to_language=to_language,
            **kwargs,
        )

    def translate_html(
        self,
        html_text: str,
        translator: str = "bing",
        from_language: str = "auto",
        to_language: str = "en",
        n_jobs: int = -1,
        **kwargs,
    ) -> str:

        if translator not in self.translators_pool or kwargs.get(
            "is_detail_result", False
        ):
            raise TranslatorError

        if not kwargs.get("sleep_seconds", None):
            kwargs.update({"sleep_seconds": 0})

        n_jobs = os.cpu_count() if n_jobs <= 0 else n_jobs
        _ts = self.translators_dict[translator]

        pattern = re.compile(r"(?:^|(?<=>))([\s\S]*?)(?:(?=<)|$)")
        sentence_list = list(set(pattern.findall(html_text)))
        _map_translate_func = lambda sentence: (
            sentence,
            _ts(
                query_text=sentence,
                from_language=from_language,
                to_language=to_language,
                **kwargs,
            ),
        )

        with ThreadPoolExecutor(n_jobs) as executor:
            result = tuple(executor.map(_map_translate_func, sentence_list))

        result_dict = {text: ts_text for text, ts_text in result}
        _get_result_func = lambda k: result_dict.get(k.group(1), "")
        return pattern.sub(repl=_get_result_func, string=html_text)
