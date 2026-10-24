from unittest.mock import ANY, MagicMock, patch

from agent import solve


# helpers

def make_tool_call(name, arguments, call_id="call_1"):
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = name
    tc.function.arguments = arguments
    return tc


def make_response(content=None, tool_calls=None):
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls
    response = MagicMock()
    response.choices[0].message = message
    return response


# direct answer no tool calls

def test_direct_answer_returned():
    response = make_response(content="42", tool_calls=None)
    with patch("agent.client.chat.completions.create", return_value=response):
        result = solve("What is 6 * 7?", tools=[])
    assert result == "42"

def test_direct_answer_resolves_in_one_llm_call():
    response = make_response(content="42", tool_calls=None)
    with patch("agent.client.chat.completions.create", return_value=response) as mock_create:
        solve("question", tools=[])
    assert mock_create.call_count == 1


# single tool call then answer

def test_single_tool_call_then_final_answer():
    tool_response = make_response(tool_calls=[make_tool_call("calculator", '{"expression": "6*7"}')])
    final_response = make_response(content="The answer is 42", tool_calls=None)

    with patch("agent.client.chat.completions.create", side_effect=[tool_response, final_response]):
        with patch("agent.dispatch", return_value={"result": 42}):
            result = solve("What is 6 * 7?", tools=[])

    assert result == "The answer is 42"

def test_single_tool_call_dispatched_correctly():
    tool_response = make_response(tool_calls=[make_tool_call("calculator", '{"expression": "6*7"}')])
    final_response = make_response(content="42", tool_calls=None)

    with patch("agent.client.chat.completions.create", side_effect=[tool_response, final_response]):
        with patch("agent.dispatch", return_value={"result": 42}) as mock_dispatch:
            solve("question", tools=[])

    mock_dispatch.assert_called_once_with(
        "calculator", '{"expression": "6*7"}', approver=None, reason=ANY, run_id=None
    )


# tool results appended to conversation before next LLM call

def test_tool_result_appended_before_next_call():
    tool_call = make_tool_call("calculator", '{"expression": "1+1"}', call_id="id_1")
    tool_response = make_response(tool_calls=[tool_call])
    final_response = make_response(content="2", tool_calls=None)

    captured = []

    def capture_create(**kwargs):
        captured.append(list(kwargs["messages"]))
        return tool_response if len(captured) == 1 else final_response

    with patch("agent.client.chat.completions.create", side_effect=capture_create):
        with patch("agent.dispatch", return_value={"result": 2}):
            solve("1+1", tools=[])

    second_call_messages = captured[1]
    roles = [m["role"] if isinstance(m, dict) else m.role for m in second_call_messages]
    assert "tool" in roles

def test_tool_result_matched_by_call_id():
    tool_call = make_tool_call("calculator", '{"expression": "1+1"}', call_id="abc123")
    tool_response = make_response(tool_calls=[tool_call])
    final_response = make_response(content="2", tool_calls=None)

    captured = []

    def capture_create(**kwargs):
        captured.append(list(kwargs["messages"]))
        return tool_response if len(captured) == 1 else final_response

    with patch("agent.client.chat.completions.create", side_effect=capture_create):
        with patch("agent.dispatch", return_value={"result": 2}):
            solve("1+1", tools=[])

    tool_messages = [m for m in captured[1] if isinstance(m, dict) and m.get("role") == "tool"]
    assert tool_messages[0]["tool_call_id"] == "abc123"


# iteration limit

def test_iteration_limit_returns_none():
    tool_response = make_response(tool_calls=[make_tool_call("calculator", '{"expression": "1+1"}')])

    with patch("agent.client.chat.completions.create", return_value=tool_response):
        with patch("agent.dispatch", return_value={"result": 2}):
            with patch("agent.settings.agent_max_iterations", 2):
                result = solve("question", tools=[])

    assert result is None

def test_iteration_limit_does_not_raise():
    tool_response = make_response(tool_calls=[make_tool_call("calculator", '{"expression": "1+1"}')])

    with patch("agent.client.chat.completions.create", return_value=tool_response):
        with patch("agent.dispatch", return_value={"result": 2}):
            with patch("agent.settings.agent_max_iterations", 2):
                result = solve("question", tools=[])

    assert result is None


# parallel tool calls

def test_parallel_tool_calls_both_dispatched():
    call_1 = make_tool_call("calculator", '{"expression": "1+1"}', call_id="id_1")
    call_2 = make_tool_call("get_weather", '{"location": "Tokyo"}', call_id="id_2")
    tool_response = make_response(tool_calls=[call_1, call_2])
    final_response = make_response(content="Done", tool_calls=None)

    with patch("agent.client.chat.completions.create", side_effect=[tool_response, final_response]):
        with patch("agent.dispatch", return_value={"result": "ok"}) as mock_dispatch:
            solve("question", tools=[])

    assert mock_dispatch.call_count == 2

def test_parallel_results_both_appended_before_next_call():
    call_1 = make_tool_call("calculator", '{"expression": "1+1"}', call_id="id_1")
    call_2 = make_tool_call("get_weather", '{"location": "Tokyo"}', call_id="id_2")
    tool_response = make_response(tool_calls=[call_1, call_2])
    final_response = make_response(content="Done", tool_calls=None)

    captured = []

    def capture_create(**kwargs):
        captured.append(list(kwargs["messages"]))
        return tool_response if len(captured) == 1 else final_response

    with patch("agent.client.chat.completions.create", side_effect=capture_create):
        with patch("agent.dispatch", return_value={"result": "ok"}):
            solve("question", tools=[])

    tool_messages = [m for m in captured[1] if isinstance(m, dict) and m.get("role") == "tool"]
    assert len(tool_messages) == 2

def test_partial_failure_still_appends_all_results_and_continues():
    call_1 = make_tool_call("calculator", '{"expression": "1+1"}', call_id="id_1")
    call_2 = make_tool_call("get_weather", '{"location": "Tokyo"}', call_id="id_2")
    tool_response = make_response(tool_calls=[call_1, call_2])
    final_response = make_response(content="Done", tool_calls=None)

    captured = []

    def capture_create(**kwargs):
        captured.append(list(kwargs["messages"]))
        return tool_response if len(captured) == 1 else final_response

    with patch("agent.client.chat.completions.create", side_effect=capture_create):
        with patch("agent.dispatch", side_effect=[{"result": 2}, {"error": "not found"}]):
            result = solve("question", tools=[])

    assert result == "Done"
    tool_messages = [m for m in captured[1] if isinstance(m, dict) and m.get("role") == "tool"]
    assert len(tool_messages) == 2



# a denial is final for the rest of the turn

from approval import ScriptedApprover


def test_denial_blocks_a_different_write_in_the_same_turn():
    first = make_response(tool_calls=[make_tool_call(
        "send_email", '{"recipient": "a@b.co", "subject": "s", "body": "b"}', call_id="c1")])
    second = make_response(tool_calls=[make_tool_call(
        "send_chat_message", '{"message": "b"}', call_id="c2")])
    final = make_response(content="The email was declined.", tool_calls=None)
    approver = ScriptedApprover([False, True])

    with patch("agent.client.chat.completions.create", side_effect=[first, second, final]):
        with patch("tools.send_chat_message") as mock_chat:
            result = solve("email a@b.co", tools=[], approver=approver)

    mock_chat.assert_not_called()
    assert len(approver.requests) == 1
    assert result == "The email was declined."


def test_denial_blocks_a_retry_of_the_same_write():
    call = '{"recipient": "a@b.co", "subject": "s", "body": "b"}'
    first = make_response(tool_calls=[make_tool_call("send_email", call, call_id="c1")])
    retry = make_response(tool_calls=[make_tool_call("send_email", call, call_id="c2")])
    final = make_response(content="declined", tool_calls=None)
    approver = ScriptedApprover([False, True])

    with patch("agent.client.chat.completions.create", side_effect=[first, retry, final]):
        solve("email a@b.co", tools=[], approver=approver)

    assert len(approver.requests) == 1


def test_reads_still_run_after_a_denial():
    first = make_response(tool_calls=[make_tool_call(
        "send_email", '{"recipient": "a@b.co", "subject": "s", "body": "b"}', call_id="c1")])
    read = make_response(tool_calls=[make_tool_call("calculator", '{"expression": "1+1"}', call_id="c2")])
    final = make_response(content="2", tool_calls=None)

    with patch("agent.client.chat.completions.create", side_effect=[first, read, final]):
        with patch("tools.calculator", return_value={"result": 2}) as mock_calc:
            solve("q", tools=[], approver=ScriptedApprover([False]))

    mock_calc.assert_called_once()


def test_denial_result_tells_the_model_it_is_final():
    first = make_response(tool_calls=[make_tool_call(
        "send_email", '{"recipient": "a@b.co", "subject": "s", "body": "b"}', call_id="c1")])
    final = make_response(content="declined", tool_calls=None)
    captured = []

    def capture(**kwargs):
        captured.append([m for m in kwargs["messages"] if isinstance(m, dict) and m.get("role") == "tool"])
        return [first, final][len(captured) - 1]

    with patch("agent.client.chat.completions.create", side_effect=capture):
        solve("q", tools=[], approver=ScriptedApprover([False]))

    [tool_message] = captured[1]
    assert '"kind": "denied"' in tool_message["content"]
    assert "final" in tool_message["content"]
