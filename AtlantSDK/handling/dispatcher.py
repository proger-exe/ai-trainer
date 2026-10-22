import logging
from typing import Dict
import google.generativeai as gemini


from AtlantSDK.handling.router import Router
from AtlantSDK.utils.model_parser import ModelParser
from AtlantSDK.utils.syntax_parser import SyntaxParser
from AtlantSDK.misc import CustomAssembly


class Dispatcher:
    def __init__(
        self,
        token: str,
        models_path: str = "models.json",
        syntax_path: str = "syntax.json",
    ):
        self.models_path = models_path
        self.syntax_path = syntax_path
        self.routers: Dict[str, Router] = {}
        self.cas = CustomAssembly()
        self.logger = logging.getLogger("AtlantSDK.dispatcher")

        gemini.configure(api_key=token)

    def __getattr__(self, model: str):
        return self.routers[model]

    def init_routers(self):
        """Initialization a Routers to Models"""
        parser = ModelParser()

        models = parser.get_models_from_file(self.models_path)
        for model_id in models:
            model = models[model_id]
            router = Router(model=model, cas=self.cas, dp=self)
            # Ищем абстрактный роутер по имени модели, а не по model_id
            # (model_id может быть "CORE" для Priority=0, но model.name - это реальное имя)
            abs_router = self.routers.get(model.name)
            if abs_router:
                self.logger.info(
                    f"Syncing handlers for model {model.name} from abstract router"
                )
                router.sync(abs_router.handlers)
            else:
                self.logger.warning(
                    f"No abstract router found for model {model.name} (model_id: {model_id})"
                )
            self.routers.update({model.name: router})

    def load_syntax(self, functions: dict = {}):
        parser = SyntaxParser(self.cas)
        parser.register_syntax_from_file(self.syntax_path, functions)

    def proccess_update(self, update: str):
        # Uses format CMD => WHO
        if not update:
            print("no update.")
            return

        command, to = self.cas.make_an_update(update)
        command, to = command, to.strip()

        self.routers[to].handle_update(command)

    def include_routers(self, routers: list):
        for router in routers:
            self.routers.update({router.model_name: router})

    def start_polling(self, start_command: str = "START", to_model: str = "CORE"):
        """Method Start of polling

        Args:
            start_command (str, optional): The command that will be sent to start working with CORE model. Defaults to "START".
        """
        self.init_routers()

        self.logger.info("Running...")

        start_cmd = f"{start_command} => {to_model}"
        self.proccess_update(start_cmd)
