import os
import re
import subprocess

from mdp_lib.mdp_plugin import MDPPlugin
from mdp_lib.disk_image_info import TargetDiskImage


class BlockUsage(MDPPlugin):
    name = "block_usage"
    description = (
        "Use an external program to determine disk usage by block allocation status."
    )
    expected_results = ["fs_fill_percent_c", "disk_fill_percent_c"]

    def process_disk(self, target_disk_image: TargetDiskImage):
        image_path = target_disk_image.image_path

        # relative path to external tool
        c_calc_fill_path = os.path.join(
            os.path.dirname(__file__), "..", "external_programs", "calc_fill"
        )
        c_calc_fill_path = os.path.abspath(c_calc_fill_path)

        try:
            # Run external C tool as subprocess
            proc_result = subprocess.run(
                [c_calc_fill_path, image_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )

            output = proc_result.stdout.decode("utf-8")

            # Parse output
            fs_fill_match = re.search(r"FSes fill:\s*([\d.]+)", output)
            disk_fill_match = re.search(r"Disk fill:\s*([\d.]+)", output)

            fs_fill_percent_c = float(fs_fill_match.group(1)) if fs_fill_match else None
            disk_fill_percent_c = (
                float(disk_fill_match.group(1)) if disk_fill_match else None
            )

        except subprocess.CalledProcessError as e:
            fs_fill_percent_c = disk_fill_percent_c = None
            print("Byte usage calculation failed: {}".format(e))
        except FileNotFoundError:
            fs_fill_percent_c = disk_fill_percent_c = None
            print(
                "Byte usage calculation program not found where expected. Please check if calc_fill.c was compiled "
                "(see instructions in calc_fill.c) in external_programs/ folder."
            )

        res = self.create_result(target_disk_image)
        self.set_results(
            res,
            {
                "fs_fill_percent_c": fs_fill_percent_c,
                "disk_fill_percent_c": disk_fill_percent_c,
            },
        )

        return res
