import re
import locale
import os

from Registry import Registry

from mdp_lib.disk_image_info import TargetDiskImage
from mdp_lib.mdp_plugin import MDPPlugin


class WindowsSystemLang(MDPPlugin):
    name = "win_system_lang"
    description = "Gets information about Windows language settings"
    expected_results = [
        "win_install_language",
        "win_default_locale",
        "win_keyboard_layout",
    ]

    def process_disk(self, target_disk_image: TargetDiskImage):
        disk_image = target_disk_image.accessor
        files = disk_image.files

        temp_filename = "export.bin"
        install_lang = None
        system_locale = None
        keyboard_layout = None

        # Work on Windows SYSTEM Hive
        for each_file in files:
            if (
                re.search(
                    "Windows/System32/config/SYSTEM$",
                    each_file.full_path,
                    re.IGNORECASE,
                )
                is not None
            ):
                # Store hive in temporary file
                f = open(temp_filename, "wb")
                f.write(each_file.read())
                f.close()

                reg = Registry.Registry(temp_filename)

                current_cs_number = 1

                try:
                    select_key = reg.open("Select")
                    current_cs_number = select_key.value("Current").value()
                except (
                    Registry.RegistryValueNotFoundException,
                    Registry.RegistryKeyNotFoundException,
                ):
                    pass

                control_set = f"ControlSet{current_cs_number:03d}"

                # Extract language info
                nls_lang_path = f"{control_set}\\Control\\Nls\\Language"
                try:
                    lang_key = reg.open(nls_lang_path)
                    raw_install = lang_key.value("InstallLanguage").value()
                    if raw_install:
                        install_lang = locale.windows_locale.get(int(raw_install, 16))

                    raw_default = lang_key.value("Default").value()
                    if raw_default:
                        system_locale = locale.windows_locale.get(int(raw_default, 16))
                except Registry.RegistryKeyNotFoundException:
                    pass

                # Extract keyboard layout
                locale_path = f"{control_set}\\Control\\Nls\\Locale"
                try:
                    locale_key = reg.open(locale_path)

                    raw_kb = None
                    for v in locale_key.values():
                        if v.name() == "(Default)" or v.name() == "":
                            raw_kb = v.value()
                            break

                    if raw_kb:
                        keyboard_layout = locale.windows_locale.get(
                            int(raw_kb.upper(), 16)
                        )
                except Registry.RegistryKeyNotFoundException:
                    pass
                os.remove(temp_filename)

        result = self.create_result(target_disk_image)
        self.set_results(
            result,
            {
                "win_install_language": install_lang,
                "win_default_locale": system_locale,
                "win_keyboard_layout": keyboard_layout,
            },
        )

        return result
