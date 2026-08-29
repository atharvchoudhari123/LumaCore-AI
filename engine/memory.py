class ConversationMemory:

    def normalize(self, messages):

        result = []

        for message in messages:

            if not isinstance(
                message,
                dict
            ):
                continue

            role = message.get(
                "role"
            )

            content = message.get(
                "content"
            )

            if not isinstance(
                role,
                str
            ):
                continue

            if not isinstance(
                content,
                str
            ):
                continue

            result.append({

                "role":
                    role,

                "content":
                    content

            })

        return result


memory = ConversationMemory()
