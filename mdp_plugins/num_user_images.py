import sqlite3
import os
import time
import filetype
import re
from typing import List

import config.config as config
from marple.file_object import FileItem

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class NumberOfUserImages(MDPPlugin):
<<<<<<< HEAD
    name = "no_pictures"
    description = "Number of pictures"
=======
    name = "num_user_images"
    description = "Number of images at 'user-controlled' locations."
>>>>>>> no_pictures
    expected_results = [
        "no_pictures",
        "no_non_nsrl_files",
        "no_non_nsrl_files_incl_zero",
    ]

    image_extensions = {
        ".dwg",
        ".xcf",
        ".jpg",
        ".jpx",
        ".png",
        ".apng",
        ".gif",
        ".webp",
        ".cr2",
        ".tif",
        ".bmp",
        ".jxr",
        ".psd",
        ".ico",
        ".heic",
        ".avif",
    }

    @staticmethod
    def is_user_controlled(file: FileItem) -> bool:
        pattern = r"^P_\d+/(?:Users|Benutzer)/([^/]+)/(?:Desktop|Documents|Dokumente|Downloads|Pictures|Bilder|Music|Musik|Videos|Favorites|Favoriten|Links|Contacts|Kontakte|Saved Games|Gespeicherte Spiele|Searches|Suchen|3D Objects|3D Objekte|OneDrive)(?:/|$)"
        return re.match(pattern, file.full_path) is not None

    @classmethod
    def is_picture(cls, file: FileItem, use_signature: bool = False) -> bool:
        """
        Checks whether a file is a picture based on filetype(https://pypi.org/project/filetype/)
        """
        if config.populate_file_signatures or config.populate_file_hashes_and_signatures:
            return filetype.is_image(file.signature)
        _, extension = os.path.splitext(file.full_path)
        return extension in cls.image_extensions

    @staticmethod
    def is_sha1_in_nsrl(sha1, conn) -> bool:
        cursor = conn.cursor()
        query = """SELECT EXISTS(SELECT 1 FROM FILE WHERE sha1 = ?)"""
        cursor.execute(query, (sha1.upper(),))
        result = cursor.fetchone()[0]
        cursor.close()
        return bool(result)

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files = disk_image.files
        # Filter for files that are 'user-controlled' and 'pictures'
        user_controlled_pictures = [x for x in files if self.is_user_controlled(x) and self.is_picture(x)]
        no_pictures = len(user_controlled_pictures)
        no_non_nsrl_files = None
        no_non_nsrl_files_incl_zero = None

        hashes_populated = target_disk_image.attributes["hashes_populated"]

        if hashes_populated and config.path_to_nsrl:
            # TODO exception handling for incorrect path_to_nsrl or unexpected nsrl db
            # need sth like check whether nsrl db is valid, only go here if nsrl check method if valid

            if not os.path.exists(config.path_to_nsrl):
                print("Provided NSRL database does not exist, skipping NSRL lookups")
            else:
                print("NSRL database found...")

                # open database here once
                open_db_start = time.time()
                conn = sqlite3.connect(config.path_to_nsrl)
                open_db_end = time.time()
                print(
                    "NSRL database opened in {} seconds".format(
                        open_db_end - open_db_start
                    )
                )

                no_non_nsrl_files = 0
                no_non_nsrl_files_incl_zero = 0
                no_nsrl = 0
                no_nsrl_non_zero = 0
                file_items: List[FileItem] = user_controlled_pictures
                for each_file in file_items:
                    sha1_file_hash = each_file.sha1
                    if (
                        sha1_file_hash
                    ):  # field might not populated for larger files (above defined max for hashing)
                        sha1_in_nsrl = self.is_sha1_in_nsrl(sha1_file_hash, conn)
                        if sha1_in_nsrl:
                            no_nsrl += 1
                            if each_file.file_size > 0:
                                no_nsrl_non_zero += 1
                            else:
                                no_non_nsrl_files_incl_zero += 1
                        else:
                            no_non_nsrl_files += 1
                            no_non_nsrl_files_incl_zero += 1
                    else:
                        no_non_nsrl_files += 1
                        no_non_nsrl_files_incl_zero += 1

                # close database here
                conn.close()
        else:
            print("File hash fields not populated. Skipping NSRL RDS check.")

        result = self.create_result(target_disk_image)
        self.set_results(
            result,
            {
                "no_pictures": no_pictures,
                "no_non_nsrl_files": no_non_nsrl_files,
                "no_non_nsrl_files_incl_zero": no_non_nsrl_files_incl_zero,
            },
        )

        return result
