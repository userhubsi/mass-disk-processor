import re
import xmltodict

import Evtx.Evtx as evtx

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin
from collections import defaultdict, Counter
from statistics import mean, median
from pathlib import PurePosixPath, PureWindowsPath
from itertools import chain


def get_path_obj(path):
    """
    Get PurePath object from a string.
    """
    if "\\" in path:
        return PureWindowsPath(path)
    return PurePosixPath(path)


def get_metrics(data):
    """
    Get min, max, mean, and median from a list of paths.
    """
    if not data or len(data) == 0:
        return {"min": 0, "max": 0, "mean": 0, "median": 0}
    return {
        "min": min(data),
        "max": max(data),
        "mean": round(mean(data)),
        "median": round(median(data)),
    }

class FolderStatistics(MDPPlugin):
    """
    [x] Folder structure statistics (maybe restrict to user folders): folder depth, files per folder, folder name length (for each, e.g., max, min, mean, and median) (just get all filenames/paths and check how often prefixes appear(files per folder) and how many "/" as a max behind each prefix (folder depth), how long strings are between "/" (folder name length)) ... don't know what to do with statistics like this...
    """

    name = "folder_statistics"
    description = "Statistics about the folder structure"
    expected_results = []  # Dynamically generated

    def _get_statistics(self, paths: list):
        paths = [get_path_obj(p) for p in paths]
        file_counts = Counter(p.parent for p in paths if len(p.parts) > 1)
        unique_folders = {
            folder for p in paths for folder in p.parents if str(folder) != "."
        }
        files_per_folder = get_metrics(list(file_counts.values()))
        folder_depth = get_metrics([len(f.parts) for f in unique_folders])
        folder_name_len = get_metrics(
            [len(f.name) for f in unique_folders if f.name]
        )
        return {
            "files_per_folder": files_per_folder,
            "folder_depth": folder_depth,
            "folder_name_len": folder_name_len
        }



    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files = disk_image.files

        temp_filename = 'export.bin'

        result = self.create_result(target_disk_image)

        user_map = defaultdict(list)
        user_logon = defaultdict(int)

        pattern = (
            r"^P_[0-9]+[/\\]"
            r"(?:Users|Documents and Settings|Dokumente und Einstellungen|home)[/\\]"
            r"([^/\\]+)[/\\]"
            r"(.*)$"
        )
        user_pattern = re.compile(pattern, re.IGNORECASE)

        for each in files:
            # get all files for each user
            match = user_pattern.match(each.full_path)
            if match:
                username = match.group(1)
                relative_path = match.group(2)
                user_map[username].append(relative_path)

            # get num interactive logins per user
            if re.match('.*/winevt/Logs/Security.evtx$', each.full_path, re.IGNORECASE):
                succ_login = 0
                with open(temp_filename, 'wb') as f:
                    f.write(each.read())

                with evtx.Evtx(temp_filename) as log:
                    for record in log.records():
                        data_dict = xmltodict.parse(record.xml())
                        event_id = int(data_dict['Event']['System']['EventID']['#text'])

                        if event_id and int(event_id) == 4624:  # successful login
                            raw_data = data_dict["Event"]["EventData"]["Data"]
                            event_data = {item.get("@Name"): item.get("#text") for item in raw_data}

                            if event_data.get("LogonType") == "2":
                                target_user = event_data.get("TargetUserName")
                                if (target_user):
                                    user_logon[target_user] += 1

        # Determine main user of the system
        main_user_log_name = None
        if user_logon:
            main_user_log_name = max(user_logon, key=user_logon.get)

        # get folder statistics for the main user
        # get folder paths for main user (case insensitive)
        main_user_folder_paths = []
        if main_user_log_name:
            for folder_user in user_map.keys():
                if folder_user.lower() == main_user_log_name.lower():
                    main_user_folder_paths = user_map[folder_user]
                    break

        stats = self._get_statistics(main_user_folder_paths)
        result.results[f"Main User: files_per_folder"] = stats["files_per_folder"]
        result.results[f"Main User: folder_depth"] = stats["folder_depth"]
        result.results[f"Main User: folder_name_len"] = stats["folder_name_len"]

        # get folder statistics for all users combined
        all_paths = chain.from_iterable(user_map.values())
        stats = self._get_statistics(list(all_paths))
        result.results[f"Users Combined: files_per_folder"] = stats["files_per_folder"]
        result.results[f"Users Combined: folder_depth"] = stats["folder_depth"]
        result.results[f"Users Combined: folder_name_len"] = stats["folder_name_len"]

        return result