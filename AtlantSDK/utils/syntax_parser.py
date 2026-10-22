import json

from AtlantSDK.misc.cas import CustomAssembly


class SyntaxParser:
    "CAS syntax parsing class"

    def __init__(self, cas: CustomAssembly):
        self.syntax = []
        self.cas = CustomAssembly()

    def register_syntax_from_file(self, file_path: str, functions: dict = {}):
        """A register CAS syntax from *.json file

        Args:
            file_path (str): Path to file
            functions (dict): Optional. A dict in format {COMMAND_NAME: CALLABLE} to dispatcher.
        """

        with open(file_path, "r+") as raw_commands_data_content:
            raw_commands_data = raw_commands_data_content.read()

        commands_data = json.loads(raw_commands_data)
        for command in commands_data:
            command_type, command_args = command.get(command)
            if command_type == "executable" and functions:
                self.cas.add_executable_command(
                    command, functions[command], command_args
                )

            else:
                self.cas.add_command_to_syntax(command, command_args)
