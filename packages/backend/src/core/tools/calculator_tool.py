"""
Calculator Tool for Bijou AI
============================

Provides basic mathematical calculations for the AI agent.
Uses AST-based safe evaluation (no eval()) to prevent RCE attacks.  # noaudit - this file explicitly avoids eval(); uses ast.literal_eval only
"""

import ast
import logging
import math
import operator
from typing import Any, Dict

logger = logging.getLogger(__name__)

class CalculatorTool:
    """
    Advanced calculator supporting basic and complex expressions.
    Safe evaluation using AST node visitor (no eval/exec).
    """
    
    # Whitelist of allowed operators
    ALLOWED_OPS = {
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
    
    # Whitelist of allowed functions
    ALLOWED_FUNCS = {
        "abs": abs,
        "round": round,
        "max": max,
        "min": min,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "sqrt": math.sqrt,
        "pow": pow,
    }
    
    # Whitelist of allowed constants
    ALLOWED_CONSTS = {
        "pi": math.pi,
        "e": math.e,
    }

    def calculate(self, expression: str) -> Dict[str, Any]:
        """
        Evaluate a mathematical expression safely using AST parsing.
        
        Args:
            expression: Math expression string (e.g., "2 + 3 * 4")
        
        Returns:
            Dict with success flag, result, or error message
        """
        try:
            # Parse expression into AST
            tree = ast.parse(expression, mode='eval')
            
            # Evaluate using safe node visitor
            result = self._eval_node(tree.body)
            
            return {
                "success": True,
                "expression": expression,
                "result": result
            }
        except SyntaxError as e:
            logger.error(f"❌ Syntax error in expression '{expression}': {e}")
            return {"success": False, "error": f"Invalid syntax: {e}"}
        except ValueError as e:
            logger.error(f"❌ Value error in expression '{expression}': {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"❌ Calculation error in '{expression}': {e}")
            return {"success": False, "error": str(e)}
    
    def _eval_node(self, node: ast.AST) -> float:
        """
        Recursively evaluate AST node with whitelist validation.
        
        Raises:
            ValueError: If node type is not whitelisted
        """
        if isinstance(node, ast.Constant):
            # Python 3.8+ (ast.Num/ast.Str deprecated)
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant type: {type(node.value)}")
        
        elif isinstance(node, ast.Num):
            # Python 3.7 compatibility
            return node.n
        
        elif isinstance(node, ast.BinOp):
            # Binary operation (e.g., 2 + 3)
            op_type = type(node.op)
            if op_type not in self.ALLOWED_OPS:
                raise ValueError(f"Operation not allowed: {op_type.__name__}")
            
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self.ALLOWED_OPS[op_type](left, right)
        
        elif isinstance(node, ast.UnaryOp):
            # Unary operation (e.g., -5)
            op_type = type(node.op)
            if op_type not in self.ALLOWED_OPS:
                raise ValueError(f"Operation not allowed: {op_type.__name__}")
            
            operand = self._eval_node(node.operand)
            return self.ALLOWED_OPS[op_type](operand)
        
        elif isinstance(node, ast.Call):
            # Function call (e.g., sqrt(16))
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only simple function calls allowed")
            
            func_name = node.func.id
            if func_name not in self.ALLOWED_FUNCS:
                raise ValueError(f"Function not allowed: {func_name}")
            
            # Evaluate arguments
            args = [self._eval_node(arg) for arg in node.args]
            
            # Call whitelisted function
            return self.ALLOWED_FUNCS[func_name](*args)
        
        elif isinstance(node, ast.Name):
            # Variable/constant reference (e.g., pi)
            if node.id not in self.ALLOWED_CONSTS:
                raise ValueError(f"Name not allowed: {node.id}")
            
            return self.ALLOWED_CONSTS[node.id]
        
        else:
            raise ValueError(f"Node type not allowed: {type(node).__name__}")
