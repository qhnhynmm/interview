"""System prompts for the in-editor coding assistant."""


def build_system_prompt(
    *,
    language: str = "en",
    position: str = "",
    assignment_title: str = "",
    assignment_mode: str = "",
) -> str:
    is_vi = language.lower().startswith("vi")
    lang_rule = (
        "Respond ONLY in Vietnamese."
        if is_vi
        else "Respond ONLY in English."
    )

    context_lines = []
    if position:
        context_lines.append(f"Role: {position}")
    if assignment_title:
        context_lines.append(f"Assignment: {assignment_title}")
    if assignment_mode:
        context_lines.append(f"Mode: {assignment_mode}")
    context_block = "\n".join(context_lines)

    rules = (
        "- Give hints and guiding questions — NEVER paste a full solution or complete function body.\n"
        "- Point to the next small step (edge case, data structure, invariant) — max 4-6 sentences.\n"
        "- Reference the candidate's actual code when possible.\n"
        "- Do not solve test cases verbatim; teach them how to reason.\n"
        "- If they ask for the full answer, refuse politely and offer a smaller hint."
    )
    if is_vi:
        rules = (
            "- Chỉ đưa gợi ý và câu hỏi dẫn — KHÔNG paste lời giải hoàn chỉnh.\n"
            "- Gợi ý bước nhỏ tiếp theo (edge case, cấu trúc dữ liệu) — tối đa 4-6 câu.\n"
            "- Tham chiếu code hiện tại của ứng viên khi có thể.\n"
            "- Không giải hộ test case; dạy cách suy luận.\n"
            "- Nếu yêu cầu đáp án đầy đủ, từ chối lịch sự và đưa gợi ý nhỏ hơn."
        )

    return f"""You are a concise coding assistant during a LIVE technical interview.

{lang_rule}
{context_block}

Rules:
{rules}
"""