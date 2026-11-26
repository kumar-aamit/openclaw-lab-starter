"""Answer blocks: the JSON schema the model must fill, and checks on what it returned."""
from .screens import AnswerBlock


def block_schema(block: AnswerBlock) -> dict:
    if block.kind == "text":
        return {"type": "string"}
    if block.kind == "score":
        return {
            "type": "object",
            "properties": {
                "value": {"type": "integer", "minimum": 0, "maximum": 100},
                "label": {"type": "string"},
            },
            "required": ["value", "label"],
        }
    if block.kind == "table":
        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {c: {"type": "string"} for c in block.columns},
                "required": list(block.columns),
            },
        }
    if block.kind == "checklist":
        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"step": {"type": "string"}, "source": {"type": "string"}},
                "required": ["step"],
            },
        }
    raise ValueError(block.kind)


def json_schema(blocks: tuple[AnswerBlock, ...]) -> dict:
    return {
        "type": "object",
        "properties": {b.key: block_schema(b) for b in blocks},
        "required": [b.key for b in blocks],
    }


def placeholder_answer(blocks: tuple[AnswerBlock, ...]) -> dict:
    answer = {}
    for b in blocks:
        if b.kind == "text":
            answer[b.key] = f"Mock answer for {b.title}. Set LLM_MOCK=0 to ask the model."
        elif b.kind == "score":
            answer[b.key] = {"value": 50, "label": "Mock"}
        elif b.kind == "table":
            answer[b.key] = [{c: f"mock {c.lower()}" for c in b.columns}]
        elif b.kind == "checklist":
            answer[b.key] = [{"step": "Mock step one"}, {"step": "Mock step two"}]
    return answer


def answer_problems(blocks: tuple[AnswerBlock, ...], answer: dict) -> list[str]:
    problems = []
    if not isinstance(answer, dict):
        return ["the answer is not a JSON object"]
    for b in blocks:
        value = answer.get(b.key)
        if value is None:
            problems.append(f"{b.key} is missing")
        elif b.kind == "text" and not isinstance(value, str):
            problems.append(f"{b.key} must be text")
        elif b.kind == "score":
            if not isinstance(value, dict) or not isinstance(value.get("value"), int):
                problems.append(f"{b.key} needs value (0 to 100) and label")
            elif not 0 <= value["value"] <= 100:
                problems.append(f"{b.key}.value must be 0 to 100")
        elif b.kind == "table":
            if not isinstance(value, list) or not all(isinstance(r, dict) for r in value):
                problems.append(f"{b.key} must be a list of rows")
        elif b.kind == "checklist":
            if not isinstance(value, list) or not all(isinstance(r, dict) and "step" in r for r in value):
                problems.append(f"{b.key} must be a list of {{step, source}} items")
    return problems
