from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from getpass import getpass


# This allows the prompt to accept up/down arrows for history navigation
# based on https://github.com/Textualize/rich/issues/262#issuecomment-2546430217
class InteractiveConsole(Console):
    def __init__(self, history=None, *args, **kwargs):
        self.history = InMemoryHistory(history)
        self.session = PromptSession(history=self.history)
        return super().__init__(*args, **kwargs)

    def input(
        self, prompt="", markup=True, emoji=True, password=False, stream=None
    ) -> str:
        if prompt:
            self.print(prompt, markup=markup, emoji=emoji, end="")
        if password:
            result = getpass("", stream=stream)
        else:
            if stream:
                result = stream.readline()
            else:
                result = self.session.prompt("")
        return result
