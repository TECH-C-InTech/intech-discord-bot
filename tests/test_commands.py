from unittest.mock import MagicMock

from discord import app_commands

from src.commands import setup_all_commands


def registered_command_names() -> set[str]:
    client = MagicMock()
    client._connection = MagicMock()
    client._connection._command_tree = None
    tree = app_commands.CommandTree(client)
    setup_all_commands(tree)
    return {command.name for command in tree.get_commands()}


def test_channel_commands_are_unified_across_kinds() -> None:
    names = registered_command_names()

    assert {
        "create_channel",
        "archive_channel",
        "restore_channel",
        "add_role_members",
        "remove_role_members",
    } <= names
    assert not {name for name in names if name.endswith(("_channel_role_member", "_role_member"))}
    assert (
        not {
            f"{verb}_{kind}_channel"
            for verb in ("create", "archive", "restore")
            for kind in ("club", "event", "project")
        }
        & names
    )


def test_panel_commands_are_registered() -> None:
    assert {"intech", "setup_panel"} <= registered_command_names()
