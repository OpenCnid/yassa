"""Bounded declarative predicates over JSON evidence; no evaluated code or I/O."""

import math
from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from .records import canonical, parse_json
from .study import Record, Slug

ARITY = {
    "get": (2, 2),
    "eq": (2, 2),
    "ne": (2, 2),
    "lt": (2, 2),
    "le": (2, 2),
    "gt": (2, 2),
    "ge": (2, 2),
    "and": (1, 50),
    "or": (1, 50),
    "not": (1, 1),
    "add": (2, 2),
    "sub": (2, 2),
    "mul": (2, 2),
    "sum": (1, 1),
    "len": (1, 1),
    "unique": (1, 1),
    "keys": (1, 1),
    "contains": (2, 2),
    "type": (1, 1),
    "if": (3, 3),
    "map": (2, 2),
    "filter": (2, 2),
    "all": (2, 2),
    "any": (2, 2),
    "set-eq": (2, 2),
    "lower": (1, 1),
    "strip": (1, 1),
}
QUANTIFIERS = {"map", "filter", "all", "any"}


def validate_expression(node, variables=frozenset({"input", "output"}), depth=0) -> set[str]:
    if depth > 40 or type(node) is not dict:
        raise ValueError("expression must be an object within depth 40")
    if set(node) == {"literal"}:
        canonical(node["literal"])
        return set()
    if set(node) == {"var"}:
        if type(node["var"]) is not str or node["var"] not in variables:
            raise ValueError("unknown rubric variable")
        return {node["var"]}
    op, args = node.get("op"), node.get("args")
    if type(op) is not str or op not in ARITY or type(args) is not list:
        raise ValueError("unknown rubric operator or invalid args")
    lo, hi = ARITY[op]
    if not lo <= len(args) <= hi:
        raise ValueError(f"invalid arity for {op}")
    if op in QUANTIFIERS:
        name = node.get("as")
        if set(node) != {"op", "args", "as"} or type(name) is not str:
            raise ValueError("quantifier needs an explicit variable")
        if not name.isidentifier() or name in variables or len(name) > 40:
            raise ValueError("quantifier variable must be new and bounded")
        return validate_expression(args[0], variables, depth + 1) | validate_expression(
            args[1], variables | {name}, depth + 1
        )
    if set(node) != {"op", "args"}:
        raise ValueError("unexpected expression fields")
    return set().union(*(validate_expression(a, variables, depth + 1) for a in args))


class Criterion(Record):
    id: Slug
    description: Annotated[str, Field(min_length=1, max_length=2000)]
    expression: Any


class JsonRubric(Record):
    version: Literal["json-predicates-v1"]
    input_assertions: Annotated[tuple[Criterion, ...], Field(min_length=1, max_length=30)]
    assertions: Annotated[tuple[Criterion, ...], Field(min_length=1, max_length=30)]
    limitations: Annotated[str, Field(min_length=1, max_length=5000)]

    @model_validator(mode="after")
    def expressions(self):
        if len(canonical(self.model_dump(mode="json"))) > 100_000:
            raise ValueError("rubric exceeds 100 KB")
        for collection in (self.input_assertions, self.assertions):
            if len({c.id for c in collection}) != len(collection) or any(
                c.id == "json" for c in collection
            ):
                raise ValueError("criterion IDs must be distinct and not reserved json")
        for c in self.input_assertions:
            if "input" not in validate_expression(c.expression, frozenset({"input"})):
                raise ValueError("input assertions must inspect input")
        variables = set()
        for c in self.assertions:
            used = validate_expression(c.expression)
            if "output" not in used:
                raise ValueError("each score criterion must inspect output")
            variables |= used
        if "input" not in variables:
            raise ValueError("rubric must relate output to input")
        return self


def _boolean(value):
    if type(value) is not bool:
        raise ValueError("predicate requires Boolean")
    return value


def _number(value):
    if (
        type(value) not in {int, float}
        or (type(value) is float and not math.isfinite(value))
        or (type(value) is int and value.bit_length() > 256)
    ):
        raise ValueError("arithmetic requires finite bounded numbers, excluding booleans")
    return value


def _array(value):
    if type(value) is not list or len(value) > 10_000:
        raise ValueError("operator requires an array of at most 10000 items")
    return value


def _encoded(value, fuel):
    # Charge traversal before serializing, including repeated shared subtrees produced by map.
    # An operation count alone would allow one comparison to expand enormous intermediate data.
    if len(fuel) == 1:
        fuel.append(20_000_000)
    stack = [value]
    while stack:
        part = stack.pop()
        fuel[0] -= 1
        if fuel[0] < 0:
            raise ValueError("rubric operation budget exceeded")
        if type(part) is dict:
            stack.extend(part.keys())
            stack.extend(part.values())
        elif type(part) is list:
            stack.extend(part)
        elif type(part) is str:
            fuel[1] -= len(part.encode("utf-8")) * 6 + 2
        else:
            fuel[1] -= 100
        if fuel[1] < 0:
            raise ValueError("rubric comparison byte budget exceeded")
    return canonical(value)


def evaluate(node, context, fuel=None):
    """Interpret a previously validated tree, with one shared operation budget."""
    fuel = [100_000] if fuel is None else fuel
    fuel[0] -= 1
    if fuel[0] < 0:
        raise ValueError("rubric operation budget exceeded")
    if "literal" in node:
        return node["literal"]
    if "var" in node:
        return context[node["var"]]
    op, args = node["op"], node["args"]

    def ev(expr, ctx=None):
        return evaluate(expr, context if ctx is None else ctx, fuel)

    if op == "if":
        return ev(args[1] if _boolean(ev(args[0])) else args[2])
    if op == "and":
        return all(_boolean(ev(a)) for a in args)
    if op == "or":
        return any(_boolean(ev(a)) for a in args)
    if op in QUANTIFIERS:
        values = _array(ev(args[0]))
        results = (ev(args[1], {**context, node["as"]: value}) for value in values)
        if op == "all":
            return all(_boolean(v) for v in results)
        if op == "any":
            return any(_boolean(v) for v in results)
        if op == "filter":
            return [v for v, keep in zip(values, results, strict=True) if _boolean(keep)]
        return list(results)
    values = [ev(a) for a in args]
    a = values[0]
    b = values[1] if len(values) > 1 else None
    if op == "get":
        if type(a) is dict and type(b) is str:
            return a[b]
        if type(a) is list and type(b) is int and 0 <= b < len(a):
            return a[b]
        raise ValueError("get needs an existing object key or nonnegative array index")
    if op in {"eq", "ne"}:
        same = _encoded(a, fuel) == _encoded(b, fuel)
        return same if op == "eq" else not same
    if op in {"lt", "le", "gt", "ge", "add", "sub", "mul"}:
        a, b = _number(a), _number(b)
        if op == "lt":
            return a < b
        if op == "le":
            return a <= b
        if op == "gt":
            return a > b
        if op == "ge":
            return a >= b
        return _number({"add": lambda: a + b, "sub": lambda: a - b, "mul": lambda: a * b}[op]())
    if op == "not":
        return not _boolean(a)
    if op == "type":
        return {
            dict: "object",
            list: "array",
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            type(None): "null",
        }[type(a)]
    if op == "len":
        if type(a) not in {dict, list, str}:
            raise ValueError("len requires object, array or string")
        return len(a)
    if op == "keys":
        if type(a) is not dict:
            raise ValueError("keys requires object")
        return list(a)
    if op == "sum":
        total = 0
        for v in _array(a):
            total = _number(total + _number(v))
        return total
    if op == "unique":
        encoded = [_encoded(v, fuel) for v in _array(a)]
        return len(set(encoded)) == len(encoded)
    if op == "set-eq":
        return {_encoded(v, fuel) for v in _array(a)} == {_encoded(v, fuel) for v in _array(b)}
    if op == "contains":
        if type(a) is str and type(b) is str:
            _encoded(a, fuel)
            _encoded(b, fuel)
            return b in a
        return _encoded(b, fuel) in {_encoded(v, fuel) for v in _array(a)}
    if op in {"lower", "strip"}:
        if type(a) is not str:
            raise ValueError("text operator requires a string")
        _encoded(a, fuel)
        return a.lower() if op == "lower" else a.strip()
    raise ValueError(f"unsupported operator: {op}")


ERRORS = (ValueError, KeyError, TypeError, IndexError, UnicodeError, RecursionError, OverflowError)


def parsed_inputs(files: dict[str, str], paths: tuple[str, ...]) -> dict:
    """Every declared rubric input is JSON; names remain explicit in the environment."""
    result = {path: parse_json(files[path]) for path in paths}
    canonical(result)  # Reject overflowing JSON numbers such as 1e999.
    return result


def validate_inputs(rubric: JsonRubric, inputs: dict) -> None:
    fuel = [100_000]
    for c in rubric.input_assertions:
        try:
            if not _boolean(evaluate(c.expression, {"input": inputs}, fuel)):
                raise ValueError("predicate is false")
        except ERRORS as error:
            raise ValueError(f"invalid case input ({c.id}): {error}") from error


def check_rubric(rubric: JsonRubric, work: bytes, inputs: dict) -> dict:
    validate_inputs(rubric, inputs)  # Protected evidence errors are never subject failures.
    try:
        if len(work) > 5_000_000:
            raise ValueError("output exceeds 5 MB")
        actual = parse_json(work)
        canonical(actual)
    except ERRORS as error:
        return {"value": 0, "components": {"json": False}, "reason": str(error)}
    components, errors, fuel = {"json": True}, {}, [100_000]
    for c in rubric.assertions:
        try:
            components[c.id] = _boolean(
                evaluate(c.expression, {"input": inputs, "output": actual}, fuel)
            )
        except ERRORS as error:
            components[c.id] = False
            errors[c.id] = str(error)
    failed = [name for name, passed in components.items() if not passed]
    return {
        "value": int(not failed),
        "components": components,
        "reason": "failed: " + ", ".join(failed) if failed else "all required checks passed",
        "diagnostics": errors,
    }
