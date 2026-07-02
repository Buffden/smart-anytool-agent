import logging
from unittest.mock import patch

import main


# helpers

def smart_no_tool(answer="Paris", reason="stable fact"):
    return {"needs_tool": False, "answer": answer, "reason": reason}

def smart_needs_tool(reason="real-time data"):
    return {"needs_tool": True, "answer": None, "reason": reason}


# configure_logging

def test_verbose_calls_basicConfig():
    with patch("logging.basicConfig") as mock_cfg:
        main.configure_logging(True)
    mock_cfg.assert_called_once()
    _, kwargs = mock_cfg.call_args
    assert kwargs.get("level") == logging.INFO

def test_non_verbose_disables_logging():
    main.configure_logging(False)
    assert logging.root.manager.disable >= logging.CRITICAL

def test_verbose_basicConfig_streams_to_stdout():
    import sys
    with patch("logging.basicConfig") as mock_cfg:
        main.configure_logging(True)
    _, kwargs = mock_cfg.call_args
    assert kwargs.get("stream") is sys.stdout


# exit on "exit" / "quit"

def test_exit_command_stops_loop(capsys):
    with patch("builtins.input", return_value="exit"):
        main.run_cli(verbose=False)
    captured = capsys.readouterr()
    assert "Goodbye" in captured.out

def test_quit_command_stops_loop(capsys):
    with patch("builtins.input", return_value="quit"):
        main.run_cli(verbose=False)
    captured = capsys.readouterr()
    assert "Goodbye" in captured.out

def test_eof_stops_loop(capsys):
    with patch("builtins.input", side_effect=EOFError):
        main.run_cli(verbose=False)
    captured = capsys.readouterr()
    assert "Goodbye" in captured.out

def test_keyboard_interrupt_stops_loop(capsys):
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        main.run_cli(verbose=False)
    captured = capsys.readouterr()
    assert "Goodbye" in captured.out


# empty input is skipped

def test_empty_input_does_not_call_smart():
    inputs = iter(["", "exit"])
    with patch("builtins.input", side_effect=inputs):
        with patch("main.self_awareness_check") as mock_smart:
            main.run_cli(verbose=False)
    mock_smart.assert_not_called()


# no tool needed direct answer

def test_direct_answer_is_printed(capsys):
    inputs = iter(["What is the capital of France?", "exit"])
    with patch("builtins.input", side_effect=inputs):
        with patch("main.self_awareness_check", return_value=smart_no_tool("Paris")):
            main.run_cli(verbose=False)
    captured = capsys.readouterr()
    assert "Paris" in captured.out

def test_direct_answer_does_not_call_retriever():
    inputs = iter(["What is the capital of France?", "exit"])
    with patch("builtins.input", side_effect=inputs):
        with patch("main.self_awareness_check", return_value=smart_no_tool("Paris")):
            with patch("main.retriever.run") as mock_retriever:
                main.run_cli(verbose=False)
    mock_retriever.assert_not_called()

def test_direct_answer_with_none_uses_fallback(capsys):
    inputs = iter(["some question", "exit"])
    with patch("builtins.input", side_effect=inputs):
        with patch("main.self_awareness_check", return_value=smart_no_tool(answer=None)):
            main.run_cli(verbose=False)
    captured = capsys.readouterr()
    assert "Agent:" in captured.out


# tool needed routes to retriever

def test_tool_path_calls_retriever():
    inputs = iter(["What is the weather in Tokyo?", "exit"])
    with patch("builtins.input", side_effect=inputs):
        with patch("main.self_awareness_check", return_value=smart_needs_tool()):
            with patch("main.retriever.run", return_value="Tokyo is 27C") as mock_retriever:
                main.run_cli(verbose=False)
    mock_retriever.assert_called_once_with("What is the weather in Tokyo?")

def test_retriever_answer_is_printed(capsys):
    inputs = iter(["What is the weather in Tokyo?", "exit"])
    with patch("builtins.input", side_effect=inputs):
        with patch("main.self_awareness_check", return_value=smart_needs_tool()):
            with patch("main.retriever.run", return_value="Tokyo is 27C"):
                main.run_cli(verbose=False)
    captured = capsys.readouterr()
    assert "Tokyo is 27C" in captured.out


# error handling no stack trace

def test_smart_exception_is_caught(capsys):
    inputs = iter(["some question", "exit"])
    with patch("builtins.input", side_effect=inputs):
        with patch("main.self_awareness_check", side_effect=Exception("boom")):
            main.run_cli(verbose=False)
    captured = capsys.readouterr()
    assert "sorry" in captured.out.lower() or "went wrong" in captured.out.lower()

def test_retriever_exception_is_caught(capsys):
    inputs = iter(["What is the weather?", "exit"])
    with patch("builtins.input", side_effect=inputs):
        with patch("main.self_awareness_check", return_value=smart_needs_tool()):
            with patch("main.retriever.run", side_effect=Exception("timeout")):
                main.run_cli(verbose=False)
    captured = capsys.readouterr()
    assert "Agent:" in captured.out

def test_exception_does_not_crash_loop(capsys):
    inputs = iter(["bad question", "What is 1+1?", "exit"])
    with patch("builtins.input", side_effect=inputs):
        with patch("main.self_awareness_check", side_effect=[
            Exception("first fails"),
            smart_no_tool("2"),
        ]):
            main.run_cli(verbose=False)
    captured = capsys.readouterr()
    assert "2" in captured.out


# verbose mode

def test_verbose_prints_smart_direct_label(capsys):
    inputs = iter(["What is the capital of France?", "exit"])
    with patch("builtins.input", side_effect=inputs):
        with patch("main.self_awareness_check", return_value=smart_no_tool("Paris")):
            main.run_cli(verbose=True)
    captured = capsys.readouterr()
    assert "[SMART]" in captured.out

def test_verbose_prints_smart_tool_label(capsys):
    inputs = iter(["What is the weather in Tokyo?", "exit"])
    with patch("builtins.input", side_effect=inputs):
        with patch("main.self_awareness_check", return_value=smart_needs_tool()):
            with patch("main.retriever.run", return_value="27C"):
                main.run_cli(verbose=True)
    captured = capsys.readouterr()
    assert "[SMART]" in captured.out

def test_non_verbose_hides_smart_label(capsys):
    inputs = iter(["What is the capital of France?", "exit"])
    with patch("builtins.input", side_effect=inputs):
        with patch("main.self_awareness_check", return_value=smart_no_tool("Paris")):
            main.run_cli(verbose=False)
    captured = capsys.readouterr()
    assert "[SMART]" not in captured.out


# main() argument parsing

def test_main_calls_run_cli_with_verbose_false():
    with patch("sys.argv", ["main.py"]):
        with patch("main.configure_logging"):
            with patch("main.run_cli") as mock_cli:
                main.main()
    mock_cli.assert_called_once_with(False)

def test_main_calls_run_cli_with_verbose_true():
    with patch("sys.argv", ["main.py", "--verbose"]):
        with patch("main.configure_logging"):
            with patch("main.run_cli") as mock_cli:
                main.main()
    mock_cli.assert_called_once_with(True)

def test_main_short_flag_enables_verbose():
    with patch("sys.argv", ["main.py", "-v"]):
        with patch("main.configure_logging"):
            with patch("main.run_cli") as mock_cli:
                main.main()
    mock_cli.assert_called_once_with(True)

def test_main_calls_configure_logging():
    with patch("sys.argv", ["main.py"]):
        with patch("main.configure_logging") as mock_log:
            with patch("main.run_cli"):
                main.main()
    mock_log.assert_called_once_with(False)
