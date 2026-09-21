import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

DEFAULT_ROW_LIMIT = 100

# A UNION/INTERSECT/EXCEPT of two SELECTs is a read-only query, but sqlglot's
# top-level node for it is exp.Union/Intersect/Except, not exp.Select -- a
# check for exp.Select alone would wrongly reject a perfectly safe query.
READ_ONLY_TOP_LEVEL_TYPES = (exp.Select, exp.Union, exp.Intersect, exp.Except)

# Blocked anywhere in the parsed tree, not just at the top level -- Postgres
# allows data-modifying statements inside a CTE (e.g. `WITH x AS (DELETE ...
# RETURNING *) SELECT * FROM x`), which is still a top-level SELECT as far as
# a type check on the outer statement is concerned. exp.Command is included
# as a catch-all for any statement/clause sqlglot doesn't have a specific
# node for -- treat "unrecognized" as unsafe rather than assuming it's inert.
FORBIDDEN_NODE_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.TruncateTable,
    exp.Merge,
    exp.Grant,
    exp.Create,
    exp.Copy,
    exp.Command,
)


def validate_select(sql: str) -> str:
    try:
        statements = sqlglot.parse(sql, read="postgres")
    except ParseError as e:
        raise ValueError(f"could not parse SQL: {e}")

    if len(statements) != 1:
        raise ValueError("exactly one statement is allowed")

    stmt = statements[0]
    if not isinstance(stmt, READ_ONLY_TOP_LEVEL_TYPES):
        raise ValueError(f"only SELECT is allowed, got {type(stmt).__name__}")

    nested = next(stmt.find_all(FORBIDDEN_NODE_TYPES), None)
    if nested is not None:
        raise ValueError(
            f"only SELECT is allowed, found nested {type(nested).__name__} "
            "(e.g. inside a CTE)"
        )

    if not stmt.args.get("limit"):
        stmt = stmt.limit(DEFAULT_ROW_LIMIT)

    return stmt.sql(dialect="postgres")
