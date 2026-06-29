import pytest
from tools import calculator


# arithmetic operations

def test_addition():
    assert calculator("2 + 3")["result"] == 5

def test_subtraction():
    assert calculator("10 - 4")["result"] == 6

def test_multiplication():
    assert calculator("3 * 4")["result"] == 12

def test_division():
    assert calculator("10 / 4")["result"] == 2.5

def test_exponent():
    assert calculator("2 ** 8")["result"] == 256

def test_modulo():
    assert calculator("10 % 3")["result"] == 1


# complex expressions

def test_operator_precedence():
    assert calculator("2 + 3 * 4")["result"] == 14

def test_parentheses():
    assert calculator("(2 + 3) * 4")["result"] == 20

def test_negative_number():
    assert calculator("-5 + 10")["result"] == 5

def test_nested_parentheses():
    assert calculator("(12 * 3) / 4 + 2 ** 3")["result"] == 17.0


# return structure

def test_returns_expression_and_result():
    result = calculator("1 + 1")
    assert "expression" in result
    assert "result" in result

def test_returns_original_expression():
    result = calculator("1 + 1")
    assert result["expression"] == "1 + 1"


# division by zero

def test_division_by_zero():
    result = calculator("1 / 0")
    assert "error" in result
    assert "zero" in result["error"].lower()


# unsafe expressions

def test_blocks_import():
    result = calculator("__import__('os')")
    assert "error" in result

def test_blocks_builtin_call():
    result = calculator("print('hello')")
    assert "error" in result

def test_blocks_string_input():
    result = calculator("'hello' + 'world'")
    assert "error" in result

def test_blocks_attribute_access():
    result = calculator("(1).__class__")
    assert "error" in result


# invalid syntax

def test_invalid_syntax():
    result = calculator("2 +")
    assert "error" in result

def test_empty_expression():
    result = calculator("")
    assert "error" in result


# never raises

def test_does_not_raise_on_unsafe_input():
    result = calculator("__import__('os').system('ls')")
    assert isinstance(result, dict)
    assert "error" in result
