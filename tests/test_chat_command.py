
from click.testing import CliRunner
from lee.cli.commands.chat import chat
from unittest.mock import patch, AsyncMock
import asyncio

def test_chat_help():
    runner = CliRunner()
    result = runner.invoke(chat, ['--help'])
    assert result.exit_code == 0
    assert "Start Lee Chat" in result.output

@patch('lee.cli.commands.chat.LeeChatREPL.run_loop', new_callable=AsyncMock)
def test_chat_run(mock_loop):
    runner = CliRunner()
    result = runner.invoke(chat)
    assert result.exit_code == 0
    mock_loop.assert_called_once()
