import pytest

from db_validation import validate_select


def test_clean_select_passes_through_unchanged_shape():
    result = validate_select("SELECT name FROM departments LIMIT 5")
    assert "SELECT" in result
    assert "LIMIT 5" in result


def test_missing_limit_gets_one_added():
    result = validate_select("SELECT * FROM employees")
    assert "LIMIT 100" in result


def test_existing_limit_is_not_overridden():
    result = validate_select("SELECT * FROM employees LIMIT 3")
    assert "LIMIT 3" in result
    assert "LIMIT 100" not in result


def test_stacked_statements_rejected():
    with pytest.raises(ValueError):
        validate_select("SELECT 1; DROP TABLE employees;")


def test_update_rejected():
    with pytest.raises(ValueError):
        validate_select("UPDATE employees SET salary = 0")


def test_delete_rejected():
    with pytest.raises(ValueError):
        validate_select("DELETE FROM employees WHERE id = 1")


def test_drop_rejected():
    with pytest.raises(ValueError):
        validate_select("DROP TABLE employees")


def test_insert_rejected():
    with pytest.raises(ValueError):
        validate_select("INSERT INTO employees (name) VALUES ('x')")


def test_unparseable_sql_rejected():
    with pytest.raises(ValueError):
        validate_select("SELECT FROM WHERE ???")


# data-modifying statements smuggled inside a CTE -- the outer statement is
# still a SELECT, so a top-level-type-only check would miss these entirely

def test_delete_inside_cte_rejected():
    with pytest.raises(ValueError):
        validate_select(
            "WITH deleted AS (DELETE FROM employees WHERE id = 1 RETURNING *) "
            "SELECT * FROM deleted"
        )


def test_update_inside_cte_rejected():
    with pytest.raises(ValueError):
        validate_select(
            "WITH updated AS (UPDATE employees SET salary = 0 RETURNING *) "
            "SELECT * FROM updated"
        )


def test_insert_inside_cte_rejected():
    with pytest.raises(ValueError):
        validate_select(
            "WITH inserted AS (INSERT INTO employees (name) VALUES ('x') RETURNING *) "
            "SELECT * FROM inserted"
        )


# legitimate read-only queries using the same shapes must still pass

def test_read_only_cte_still_allowed():
    result = validate_select(
        "WITH ranked AS (SELECT name, salary FROM employees) "
        "SELECT * FROM ranked ORDER BY salary DESC"
    )
    assert "WITH ranked AS" in result


def test_subquery_still_allowed():
    result = validate_select("SELECT * FROM (SELECT * FROM employees) sub")
    assert "SELECT" in result


# UNION/INTERSECT/EXCEPT are read-only but sqlglot's top-level node for them
# isn't exp.Select -- must not be rejected as "not a SELECT"

def test_union_of_selects_is_allowed():
    result = validate_select(
        "SELECT name FROM departments UNION SELECT name FROM employees"
    )
    assert "UNION" in result
    assert "LIMIT 100" in result


def test_union_existing_limit_is_not_overridden():
    result = validate_select(
        "SELECT name FROM departments UNION SELECT name FROM employees LIMIT 2"
    )
    assert "LIMIT 2" in result
    assert "LIMIT 100" not in result


def test_delete_inside_cte_rejected_even_under_union():
    with pytest.raises(ValueError):
        validate_select(
            "WITH deleted AS (DELETE FROM employees RETURNING name) "
            "SELECT name FROM departments UNION SELECT name FROM deleted"
        )


def test_dml_in_non_first_cte_still_rejected():
    with pytest.raises(ValueError):
        validate_select(
            "WITH a AS (SELECT * FROM departments), "
            "b AS (DELETE FROM employees RETURNING *) "
            "SELECT * FROM a"
        )


def test_recursive_cte_still_allowed():
    result = validate_select(
        "WITH RECURSIVE chain AS ("
        "SELECT id, manager_id FROM employees WHERE manager_id IS NULL "
        "UNION ALL "
        "SELECT e.id, e.manager_id FROM employees e JOIN chain c ON e.manager_id = c.id"
        ") SELECT * FROM chain"
    )
    assert "RECURSIVE" in result
