from typing import Optional, List, Union, Any
from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from getpass import getpass


# This allows the prompt to accept up/down arrows for history navigation
# based on https://github.com/Textualize/rich/issues/262#issuecomment-2546430217
class InteractiveConsole(Console):
    def __init__(
        self, history: Optional[Union[str, List[str]]] = None, *args: Any, **kwargs: Any
    ) -> None:
        self._history = InMemoryHistory(history)
        self._session: Optional[PromptSession] = None
        super().__init__(*args, **kwargs)

    @property
    def session(self) -> PromptSession:
        """Lazy-load the PromptSession only when needed for interactive input."""
        if self._session is None:
            self._session = PromptSession(history=self._history)
        return self._session

    def input(
        self,
        prompt: str = "",
        markup: bool = True,
        emoji: bool = True,
        password: bool = False,
        stream: Optional[Any] = None,
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
