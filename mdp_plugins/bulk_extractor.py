import os.path
import subprocess
import shutil

import config.config as config
from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class BulkExtractor(MDPPlugin):
    name = "bulk_extractor"
    description = "Run bulk_extractor against disk"
    include_in_data_table = True
    expected_results = []  # dynamically generated

    def process_disk(self, target_disk_image: TargetDiskImage):
        result = self.create_result(target_disk_image)

        evidence_path, image_name = os.path.split(target_disk_image.image_path)
        case_path = os.path.dirname(evidence_path)

        bulk_extractor_folder = os.path.join(
            case_path, f"bulk_extractor-output/{image_name}"
        )

        # check if bulk_extractor-output folder exists
        if os.path.exists(bulk_extractor_folder):
            print(
                f"[!] {bulk_extractor_folder} already exists! Overwriting with new one ..."
            )
            shutil.rmtree(bulk_extractor_folder)
        os.makedirs(bulk_extractor_folder)

        cmd = [
            config.bulk_extractor,
            *config.bulk_extractor_options,
            "-o",
            bulk_extractor_folder,
            target_disk_image.image_path,
        ]

        # --- Run bulk_extractor ---
        try:
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        except Exception as e:
            print(f"Something went wrong while executing {cmd}:\n {e}")
            return result

        # Add bulk_extractor results
        be_result_files = os.listdir(bulk_extractor_folder)
        for be_result_file in be_result_files:
            filename, extension = os.path.splitext(be_result_file)
            # we are only interested in the txt files containing the results
            if filename.endswith("_histogram") or extension != ".txt":
                continue

            be_result_file_path = os.path.join(bulk_extractor_folder, be_result_file)

            print(f"opening {be_result_file_path}")
            with open(be_result_file_path, "r") as f:
                print(f"opened {be_result_file_path}")
                count = 0
                for line in f:
                    # usually the feature files are structured in three columns separated by tabs
                    # <offset> \t <feature> \t <context>
                    # -> Skip any line that starts as a comment (# ...) or does not contain 3 columns or has empty columns
                    cols = line.split("\t")
                    if line.startswith("#") or len(cols) != 3 or "" in cols:
                        continue
                    count += 1
                # Only log interesting results
                if count:
                    result.results[f"bulk_extractor_{filename}_count"] = count
                    print(f"bulk_extractor_{filename}_count", count)

        return result
