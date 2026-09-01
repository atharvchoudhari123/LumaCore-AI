from __future__ import annotations

import ast
import operator

from datetime import datetime
from zoneinfo import ZoneInfo


class PluginError(Exception):
    pass


# =========================================================
# SAFE CALCULATOR
# =========================================================

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _calculate(expression: str):
    expression = expression.strip()

    if not expression:
        raise PluginError("Expression is empty.")

    if len(expression) > 200:
        raise PluginError("Expression is too long.")

    try:
        tree = ast.parse(
            expression,
            mode="eval"
        )
    except SyntaxError as exc:
        raise PluginError("Invalid expression.") from exc

    def evaluate(node):

        if isinstance(node, ast.Expression):
            return evaluate(node.body)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value

            raise PluginError(
                "Only numeric values are allowed."
            )

        if isinstance(node, ast.UnaryOp):
            operation = _ALLOWED_OPERATORS.get(
                type(node.op)
            )

            if operation is None:
                raise PluginError(
                    "Unsupported operator."
                )

            return operation(
                evaluate(node.operand)
            )

        if isinstance(node, ast.BinOp):
            operation = _ALLOWED_OPERATORS.get(
                type(node.op)
            )

            if operation is None:
                raise PluginError(
                    "Unsupported operator."
                )

            left = evaluate(node.left)
            right = evaluate(node.right)

            if isinstance(node.op, ast.Pow):
                if abs(right) > 20:
                    raise PluginError(
                        "Exponent is too large."
                    )

            try:
                return operation(
                    left,
                    right
                )
            except ZeroDivisionError as exc:
                raise PluginError(
                    "Division by zero."
                ) from exc

        raise PluginError(
            "Unsupported expression."
        )

    return evaluate(tree)


# =========================================================
# PLUGIN REGISTRY
# =========================================================

PLUGINS = {
    "calculator": {
        "id": "calculator",
        "name": "Calculator",
        "description": (
            "Safely evaluates basic arithmetic expressions."
        )
    },

    "clock": {
        "id": "clock",
        "name": "Clock",
        "description": (
            "Returns the current time for a timezone."
        )
    }
}


def list_plugins():
    return list(
        PLUGINS.values()
    )


def get_plugin(
    plugin_id: str
):
    return PLUGINS.get(
        plugin_id
    )


def run_plugin(
    plugin_id: str,
    arguments: dict
):

    if plugin_id == "calculator":

        expression = str(
            arguments.get(
                "expression",
                ""
            )
        )

        result = _calculate(
            expression
        )

        return {
            "plugin": "calculator",
            "result": result
        }


    if plugin_id == "clock":

        timezone = str(
            arguments.get(
                "timezone",
                "UTC"
            )
        )

        try:

            zone = ZoneInfo(
                timezone
            )

        except Exception as exc:

            raise PluginError(
                f"Unknown timezone: {timezone}"
            ) from exc

        now = datetime.now(
            zone
        )

        return {
            "plugin": "clock",
            "timezone": timezone,
            "iso": now.isoformat(),
            "display": now.strftime(
                "%A, %B %d, %Y at %I:%M:%S %p %Z"
            )
        }


    raise PluginError(
        f"Unknown plugin: {plugin_id}"
    )
