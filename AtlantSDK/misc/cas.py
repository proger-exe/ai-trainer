from typing import Callable, Dict, List, Optional
from AtlantSDK.errors import MakingExecutableFunctionException


class CustomAssembly:
    "CustomAssembly class"

    def __init__(self) -> None:
        """
        CustomAssembly Inteprier init function

        Returns:
            CustomAssebly: instance of class
        """
        self.syntax = {}

    def __format__(self, __format_spec: str) -> Optional[str]:
        if __format_spec.startswith("s:"):
            cmd = __format_spec.split(":")[1]
            return f"{self.syntax[cmd]}"

        elif __format_spec.startswith("c:"):
            array = __format_spec.split(":")
            cmd = array[1]
            syntax = self.syntax[cmd]
            res = ""
            for key, arg in zip(syntax.keys(), array[2:]):
                res += f"{key}: {arg};"

            return res

    def add_command_to_syntax(self, name: str, args: Dict[str, str]):
        """Method of adding a command to CAS

        Args:
            name (str): Name of command
            args (Dict[str, str]): Arguments of command
        """
        self.syntax.update({name: ("simple", args)})

    def add_executable_command(self, name: str, func: Callable, args: Dict[str, str]):
        """Method of adding the called command to CAS

        Args:
            name (str): Name of command
            func (Callable): A Callable python-function (DO NOT ADD TO SYNTAX FILE!!!)
            args (Dict[str, str]): Command arguments - repeated into a function.
        """
        self.syntax.update({name: ("executable", func, args)})

    def generate_command(self, name: str, args: tuple):
        """_summary_

        Args:
            name (str): _description_
            args (tuple): _description_

        Raises:
            MakingExecutableFunctionException: _description_

        Returns:
            _type_: _description_
        """

        command = self.syntax.get(name)
        if len(command) >= 3:  # type: ignore
            raise MakingExecutableFunctionException("Cannot make an executable command")

        keys = command[1].keys()
        res = ""
        for key, value in zip(keys, args):
            res += f"{key}={value}"

        completed_command = f"{name} {res}"
        return completed_command

    def make_an_update(self, raw_str: str):
        command, where = raw_str.split("=>")
        command = command.strip()
        command_params_list = command.split()

        command_params = " ".join(command_params_list[1:])

        if not command_params_list[1:]:
            return ((("command", command_params_list[0]),), where)

        return ((("command", command_params_list[0]), ("args", command_params)), where)

    def get_args(self, command: str):
        command = command.strip()
        command_params = tuple(command.split())

        return command_params
