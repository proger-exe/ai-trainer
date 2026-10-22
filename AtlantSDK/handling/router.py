import logging
import inspect

from AtlantSDK.type.conversation import Conversation
from AtlantSDK.type.model import Model
from AtlantSDK.misc.cas import CustomAssembly
from AtlantSDK.misc.filter import check_handlers


class Router:
    def __init__(self, model: Model, cas: CustomAssembly, dp) -> None:
        """A Routing of model-chat class.

        Args:
            model (atlant.types.Model): The model to which the router will be bound

        """
        self.model: Model = model
        self.chat: Conversation = model.chat
        self.cas: CustomAssembly = cas
        self.logger = logging.getLogger(f"AtlantSDK.router.{model.name}")
        self.handlers = {}
        self.dp = dp

    def send_command(self, text: str, *parameters):
        if parameters:
            text = self.cas.generate_command(text, parameters)

        self.logger.info(f"TO\t=>\t{text}")
        answer = self.chat.send_command(text)

        self.logger.info(f"FROM\t=>\t{answer}")

        return answer

    def register_a_handler(self, function):
        def wrapper(*args, **kwargs):
            sig = inspect.signature(function)
            bound_args = sig.bind_partial()

            for param_name in sig.parameters:
                if param_name == "chat":
                    bound_args.arguments[param_name] = self.chat
                elif param_name == "model":
                    bound_args.arguments[param_name] = self.model
                elif param_name == "cas":
                    bound_args.arguments[param_name] = self.cas

            for kw in kwargs:
                bound_args.arguments[kw] = kwargs[kw]

            res = function(*bound_args.args, **bound_args.kwargs)
            self.logger.info(f"FROM\t=>\t{res}")

            self.dp.proccess_update(res)

        return wrapper

    def handle_update(self, command: tuple):
        self.logger.info(f"TO\t=>\t{command}")
        self.logger.info(f"Available handlers: {list(self.handlers.keys())}")

        for handler in self.handlers:
            correct = check_handlers(dict(handler), dict(command))
            self.logger.debug(f"Handler {handler}: check_handlers result = {correct}")
            if correct:
                func = self.handlers.get(handler)

                if func:
                    cmd = command[0][1]
                    cmd_args = command[1][1]
                    cmd = f"{cmd} {cmd_args}"
                    self.logger.info(f"Calling handler with cmd: {cmd}")
                    func(cmd=cmd)
                else:
                    self.logger.warning(f"Handler {handler} found but func is None")
            else:
                self.logger.debug(f"Handler {handler} did not match")

    def sync(self, handlers: dict):
        for handler in handlers:
            self.handlers[handler] = self.register_a_handler(handlers[handler])


class AbstactRouter:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.handlers = {}

    def handler(self, **filters):
        def register_a_handler(func):
            params = tuple(filters.items())
            self.handlers.update({params: func})

            def wrapper(*args, **kwargs):
                return func

            return wrapper

        return register_a_handler
