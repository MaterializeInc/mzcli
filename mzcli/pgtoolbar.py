from pkg_resources import packaging

import prompt_toolkit
from prompt_toolkit.key_binding.vi_state import InputMode
from prompt_toolkit.application import get_app

parse_version = packaging.version.parse

vi_modes = {
    InputMode.INSERT: "I",
    InputMode.NAVIGATION: "N",
    InputMode.REPLACE: "R",
    InputMode.INSERT_MULTIPLE: "M",
}
if parse_version(prompt_toolkit.__version__) >= parse_version("3.0.6"):
    vi_modes[InputMode.REPLACE_SINGLE] = "R"


def _get_vi_mode():
    return vi_modes[get_app().vi_state.input_mode]


def create_toolbar_tokens_func(mzcli):
    """Return a function that generates the toolbar tokens."""

    def get_toolbar_tokens():
        result = []
        result.append(("class:bottom-toolbar", " "))

        if mzcli.completer.smart_completion:
            result.append(("class:bottom-toolbar.on", "[F2] Smart Completion: ON  "))
        else:
            result.append(("class:bottom-toolbar.off", "[F2] Smart Completion: OFF  "))

        if mzcli.multi_line:
            result.append(("class:bottom-toolbar.on", "[F3] Multiline: ON  "))
        else:
            result.append(("class:bottom-toolbar.off", "[F3] Multiline: OFF  "))

        if mzcli.multi_line:
            if mzcli.multiline_mode == "safe":
                result.append(("class:bottom-toolbar", " ([Esc] [Enter] to execute]) "))
            else:
                result.append(
                    ("class:bottom-toolbar", " (Semi-colon [;] will end the line) ")
                )

        if mzcli.vi_mode:
            result.append(
                ("class:bottom-toolbar", "[F4] Mode: Vi (" + _get_vi_mode() + ")")
            )
        else:
            result.append(("class:bottom-toolbar", "[F4] Mode: Emacs"))

        if mzcli.pgexecute.failed_transaction():
            result.append(
                ("class:bottom-toolbar.transaction.failed", "     Failed transaction")
            )

        if mzcli.pgexecute.valid_transaction():
            result.append(
                ("class:bottom-toolbar.transaction.valid", "     Transaction")
            )

        if mzcli.completion_refresher.is_refreshing():
            result.append(("class:bottom-toolbar", "     Refreshing completions..."))

        return result

    return get_toolbar_tokens
