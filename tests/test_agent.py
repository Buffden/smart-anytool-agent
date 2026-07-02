from unittest.mock import MagicMock, patch

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

    mock_dispatch.assert_called_once_with("calculator", '{"expression": "6*7"}')


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

def test_iteration_limit_returns_fallback():
    tool_response = make_response(tool_calls=[make_tool_call("calculator", '{"expression": "1+1"}')])

    with patch("agent.client.chat.completions.create", return_value=tool_response):
        with patch("agent.dispatch", return_value={"result": 2}):
            with patch("agent.settings.agent_max_iterations", 2):
                result = solve("question", tools=[])

    assert "unable" in result.lower()

def test_iteration_limit_does_not_raise():
    tool_response = make_response(tool_calls=[make_tool_call("calculator", '{"expression": "1+1"}')])

    with patch("agent.client.chat.completions.create", return_value=tool_response):
        with patch("agent.dispatch", return_value={"result": 2}):
            with patch("agent.settings.agent_max_iterations", 2):
                result = solve("question", tools=[])

    assert isinstance(result, str)

