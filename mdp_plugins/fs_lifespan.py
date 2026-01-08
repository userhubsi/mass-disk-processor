import datetime

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin
from config.config import min_valid_timestamp, max_valid_timestamp


class FSLifespan(MDPPlugin):
    name = 'fs_lifespan'
    description = 'Difference between earliest and latest file creation time'
    expected_results = [
        'lifespan_fs_cr',
        'lifespan_fs_cr_str',
        'earliest_fs_cr',
        'latest_fs_cr'
    ]

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files = disk_image.files

        valid_timestamps = []
        for each in files:
            timestamp = each.timestamps['cr_time']
            if timestamp is not None and min_valid_timestamp < timestamp < max_valid_timestamp:
                valid_timestamps.append(timestamp)

        valid_timestamps.sort()

        if len(valid_timestamps) > 0:
            earliest = valid_timestamps[0]
            earliest_str = datetime.datetime.fromtimestamp(earliest).isoformat()
            latest = valid_timestamps[-1]
            latest_str = datetime.datetime.fromtimestamp(latest).isoformat()
            diff = latest - earliest  # in seconds
            diff_datetime = datetime.datetime.fromtimestamp(latest) - datetime.datetime.fromtimestamp(earliest)
            diff_str = str(diff_datetime)
        else:
            diff = 0
            diff_str = "No valid timestamps found"
            earliest_str = None
            latest_str = None

        result = self.create_result(target_disk_image)
        self.set_results(result, {
            'lifespan_fs_cr': diff,
            'lifespan_fs_cr_str': diff_str,
            'earliest_fs_cr': earliest_str,
            'latest_fs_cr': latest_str
        })

        return result
