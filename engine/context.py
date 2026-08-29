def build_system_prompt(
    model_name,
    mode="chat"
):
    prompt = (
        f"You are {model_name}, an AI model created by Lumen. "
        "Answer the user's actual question accurately, clearly, "
        "and helpfully."
    )

    if mode == "code":
        prompt += (
            " You are operating in the Lumen Coding Playground. "
            "Write complete, working code and prefer practical implementations."
        )

    return prompt


def attach_files(
    messages,
    files
):
    if not files:
        return messages

    sections = []

    for file in files:
        name = file.get(
            "name",
            "unnamed"
        )

        text = file.get(
            "text"
        )

        if not isinstance(text, str):
            continue

        sections.append(
            f"FILE: {name}\n{text}"
        )

    if not sections:
        return messages

    context = (
        "Relevant uploaded files:\n\n"
        + "\n\n---\n\n".join(sections)
    )

    return [
        *messages,
        {
            "role": "user",
            "content": context
        }
    ]
