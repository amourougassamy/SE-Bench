import argparse
import json
import sys

from .demo import run_demo
from .evaluator import grade
from .model import ContractError, canonical
from .runtime import Session, write_json
from .task import load_task
from .tools import TOOLS


def emit(value):
    print(canonical(value), flush=True)


def request(session, raw):
    try:
        obj = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"Invalid number {value}")))
        if not isinstance(obj, dict) or set(obj) != {"tool", "arguments"}:
            raise ValueError("Request requires exactly tool and arguments fields")
        if not isinstance(obj["tool"], str) or not isinstance(obj["arguments"], dict):
            raise ValueError("tool must be a string and arguments an object")
        if obj["tool"] == "tools.list" and obj["arguments"] == {}:
            return {"ok": True, "data": {"tools": TOOLS}}
        return session.call(obj["tool"], obj["arguments"])
    except (ValueError, TypeError) as exc:
        return session.call("protocol.invalid", {"message": str(exc)})


def main(argv=None):
    parser = argparse.ArgumentParser(description="SE-Bench structural workflow development runner")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List available task fixtures")
    sub.add_parser("tools", help="Print provider-neutral tool schemas")
    for name in ("init", "call", "serve", "demo", "grade"):
        command = sub.add_parser(name)
        command.add_argument("--workspace", required=True)
        if name == "init":
            command.add_argument("--agent-id", default="unspecified")
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            task = load_task()[0]
            emit([{key: task[key] for key in ("id", "version", "title", "status")}])
        elif args.command == "tools":
            emit(TOOLS)
        elif args.command == "init":
            session = Session.create(args.workspace, args.agent_id)
            emit({"workspace": str(session.root), "task_id": session.task["id"], "phase": "baseline"})
        elif args.command == "demo":
            session = run_demo(args.workspace)
            result = grade(session.root)
            write_json(session.control / "grade.json", result)
            emit(result)
            return 0 if result["automated_success"] else 1
        elif args.command == "grade":
            result = grade(args.workspace)
            emit(result)
            return 0 if result["automated_success"] else 1
        else:
            session = Session(args.workspace)
            if args.command == "call":
                raw = sys.stdin.read(1_000_001)
                if len(raw) > 1_000_000:
                    raise ContractError("Request exceeds one million characters")
                response = request(session, raw)
                emit(response)
                return 0 if response["ok"] else 1
            for raw in sys.stdin:
                if len(raw) > 1_000_000:
                    emit({"ok": False, "error": {"type": "ProtocolError", "message": "Request too large"}})
                    return 1
                emit(request(session, raw))
        return 0
    except (ContractError, OSError, ValueError, KeyError, TypeError) as exc:
        emit({"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}})
        return 1
