import json
import re

from config.config import path_to_browser_categories_json
from mdp_lib.browser_history import BrowserHistory, SearchEngine
from mdp_lib.disk_image_info import TargetDiskImage


class BrowserHistoryCategories(BrowserHistory):
    name = "browser_history_categories"
    description = "Information about the categories in histories of Google Chrome (including chromium on Linux), Microsoft Edge and Mozilla Firefox."
    include_in_data_table = True
    # NOTE: This doesnt work for MacOS atm
    expected_results = []  # dynamically generated based on given categories

    # fmt: off
    # --- Regex patterns ---
    # Chrome / Chromium
    _CHROME_PATTERN_WINDOWS = r"/(Users|Documents and Settings|Dokumente und Einstellungen)/[^/]+/(AppData/Local|Local Settings/Application Data|Lokale Einstellungen/Anwendungsdaten)/Google/Chrome/User Data/[^/]+"
    _CHROME_PATTERN_LINUX = r"/home/[^/]+/(snap/chromium/common/|\.config/)(chromium|google-chrome)/[^/]+"
    _CHROME_HISTORY_PATTERN = r"P_[0-9]+((" + _CHROME_PATTERN_WINDOWS + r")|(" + _CHROME_PATTERN_LINUX + r"))/History$"

    # Edge
    _EDGE_PATTERN_WINDOWS = r"/Users/[^/]+/AppData/Local/Microsoft/Edge/User Data/[^/]+/History$"
    _EDGE_HISTORY_PATTERN = r"P_[0-9]+(" + _EDGE_PATTERN_WINDOWS + r")"

    # Firefox
    _FIREFOX_PATTERN_WINDOWS = r"/(Users|Documents and Settings|Dokumente und Einstellungen)/[^/]+/(AppData/Roaming|Application Data|Anwendungsdaten)/Mozilla/Firefox/Profiles/[^/]+\.default[^/]*"
    _FIREFOX_PATTERN_LINUX = r"/home/[^/]+/(snap/firefox/common/)?\.mozilla/firefox/[^/]+\.default[^/]*"
    _FIREFOX_PLACES_PATTERN = r"P_[0-9]+((" + _FIREFOX_PATTERN_WINDOWS + r")|(" + _FIREFOX_PATTERN_LINUX + r"))/places\.sqlite$"

    # --- SQL queries ---
    _CHROME_EDGE_QUERY = """
        SELECT urls.url,
               urls.visit_count
        FROM urls
    """
    _FIREFOX_QUERY = """
        SELECT moz_places.url,
               moz_places.visit_count
        FROM moz_places
    """

    # --- Browser Configurations ---
    BROWSER_CONFIGS = [
        {
            "pattern": _CHROME_HISTORY_PATTERN,
            "query": _CHROME_EDGE_QUERY
        },
        {
            "pattern": _EDGE_HISTORY_PATTERN,
            "query": _CHROME_EDGE_QUERY
        },
        {
            "pattern": _FIREFOX_PLACES_PATTERN,
            "query": _FIREFOX_QUERY
        }
    ]
    # fmt: on

    def process_disk(self, target_disk_image: TargetDiskImage):
        # {"category": {"site": visited_count}}
        result_dict: dict[str, int] = {}
        try:
            with open(path_to_browser_categories_json) as json_file:
                categories = json.load(json_file)
        except (FileNotFoundError, json.JSONDecodeError) as error:
            print(f"Error loading browser categories: {error}")
            result = self.create_result(target_disk_image)
            result.results = result_dict
            return result

        for category, domains in categories.items():
            # create "SearchEngine" for each domain
            search_engines = [
                SearchEngine(
                    domain,
                    rf"(?i)\bhttps?:\/\/(?:[A-Za-z0-9-]+\.)*{re.escape(domain)}\b",
                )
                for domain in domains
            ]

            browser_results = []
            for config in self.BROWSER_CONFIGS:
                browser_result: dict[str, int | None] = super().analyze_history_file(
                    category,
                    target_disk_image,
                    config["pattern"],
                    config["query"],
                    search_engines,
                )
                browser_results.append(browser_result)

            category_result: dict[str, int] = {}
            for browser_result in browser_results:
                for domain, visit_count in browser_result.items():
                    if visit_count:
                        category_result[f"{category}_{domain}"] += visit_count
            result_dict.update(category_result)

        result = self.create_result(target_disk_image)
        result.results = result_dict
        return result
