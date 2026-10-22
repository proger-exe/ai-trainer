import os

from AtlantSDK.errors.model import ErrorInitializationModel
from AtlantSDK.type.conversation import Conversation
from AtlantSDK.type.generation_config import (
    DefaultModelConfigurationSettings,
    ModelConfigurationSettings,
)


class Model:
    "Class of neural network model operation"

    def __init__(self, settings: dict):
        """Model Initialization Function

        Args:
            settings (dict): Generation parameters and framework configuration
            upload_from_file (bool): Parameter determining whether a system instruction should be loaded from AtlantSDK.a file or whether the given parameter is already an instruction
        """
        self.name = settings.get("Name", "")
        self.system_instruction = settings.get("SystemInstruction", str())
        self.priority = settings.get("Priority")
        self.model = settings.get("Model", "gemini-2.5-flash")
        upload_from_file = settings.get("FromFile", True)

        # A generation subparameters
        generation_settings = settings.get(
            "Generation", DefaultModelConfigurationSettings.generation_config
        )
        self.generation_setting = ModelConfigurationSettings(**generation_settings)

        if not self.name or not self.system_instruction:
            raise ErrorInitializationModel(
                "Model.name or Model.system_instruction was not specified in the model configuration."
            )

        # Framework settings
        if upload_from_file:
            self.system_instruction = self._read_description_from_file(
                self.system_instruction
            )

        # Add API usage variables
        self.chat = Conversation(self)

    def _read_description_from_file(self, path: str):
        """Read description from model.file method

        Args:
            path (str): A path to file

        Raises:
            ErrorInitializationModel: if there is not file

        Returns:
            str: Return a content of file
        """
        if os.path.exists(path) and os.path.isfile(path):
            with open(path, "r+") as description:
                return description.read()
        else:
            raise ErrorInitializationModel(
                "The Model.system_instruction path does not exist (maybe you forgot to turn off upload_from_file?)"
            )
