import re

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin
from collections import defaultdict, Counter
from statistics import mean, median
from pathlib import PurePosixPath, PureWindowsPath


def get_path_obj(path):
    if "\\" in path:
        return PureWindowsPath(path)
    return PurePosixPath(path)


def get_metrics(data):
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

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files = disk_image.files

        user_path_exists = False

        result = self.create_result(target_disk_image)

        for each in files:
            if (
                re.match(r"P_[0-9]+/Users/", each.full_path, re.IGNORECASE)
                or re.match(
                    "P_[0-9]+/Documents and Settings/", each.full_path, re.IGNORECASE
                )
                or re.match(
                    "P_[0-9]+/Dokumente und Einstellungen/",
                    each.full_path,
                    re.IGNORECASE,
                )
                or re.match("P_[0-9]+/home/", each.full_path)
            ):
                user_path_exists = True
                break

        if user_path_exists:
            user_map = defaultdict(list)
            pattern = (
                r"^P_[0-9]+[/\\]"
                r"(?:Users|Documents and Settings|Dokumente und Einstellungen|home)[/\\]"
                r"([^/\\]+)[/\\]"
                r"(.*)$"
            )
            user_pattern = re.compile(pattern, re.IGNORECASE)

            # get all files for each user
            for each in files:
                match = user_pattern.match(each.full_path)

                if match:
                    username = match.group(1)
                    relative_path = match.group(2)

                    user_map[username].append(relative_path)

            # get per user statistics
            for user, relative_paths in user_map.items():
                paths = [get_path_obj(p) for p in relative_paths]
                file_counts = Counter(p.parent for p in paths if len(p.parts) > 1)
                unique_folders = {
                    folder for p in paths for folder in p.parents if str(folder) != "."
                }

                files_per_folder = get_metrics(list(file_counts.values()))
                folder_depth = get_metrics([len(f.parts) for f in unique_folders])
                folder_name_len = get_metrics(
                    [len(f.name) for f in unique_folders if f.name]
                )
                result.results[f"{user}_files_per_folder"] = files_per_folder
                result.results[f"{user}_folder_depth"] = folder_depth
                result.results[f"{user}_folder_name_len"] = folder_name_len
        return result
