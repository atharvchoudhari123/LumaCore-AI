import torch

from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM
)


class ModelRuntime:

    def __init__(self):
        self.cache = {}


    def get_device(self):

        if torch.cuda.is_available():
            return "cuda"

        if (
            hasattr(torch.backends, "mps")
            and torch.backends.mps.is_available()
        ):
            return "mps"

        return "cpu"


    def load_model(self, checkpoint):

        if checkpoint in self.cache:
            return self.cache[checkpoint]

        device = self.get_device()

        print(
            f"Loading Lumen model on {device}: {checkpoint}"
        )

        tokenizer = AutoTokenizer.from_pretrained(
            checkpoint,
            trust_remote_code=True
        )

        model = AutoModelForCausalLM.from_pretrained(
            checkpoint,
            trust_remote_code=True,
            torch_dtype=(
                torch.float16
                if device != "cpu"
                else torch.float32
            )
        )

        model.to(device)
        model.eval()

        self.cache[checkpoint] = (
            tokenizer,
            model,
            device
        )

        return self.cache[checkpoint]


    def make_prompt(
        self,
        tokenizer,
        messages
    ):

        if hasattr(
            tokenizer,
            "apply_chat_template"
        ):

            try:
                return tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )

            except Exception:
                pass


        parts = []

        for message in messages:

            role = message.get(
                "role",
                "user"
            )

            content = message.get(
                "content",
                ""
            )

            parts.append(
                f"{role.upper()}: {content}"
            )

        parts.append(
            "ASSISTANT:"
        )

        return "\n\n".join(parts)


    def generate(
        self,
        checkpoint,
        messages,
        max_new_tokens=512,
        temperature=0.7
    ):

        tokenizer, model, device = (
            self.load_model(
                checkpoint
            )
        )


        prompt = self.make_prompt(
            tokenizer,
            messages
        )


        inputs = tokenizer(
            prompt,
            return_tensors="pt"
        )


        inputs = {
            key: value.to(device)
            for key, value in inputs.items()
        }


        generation_kwargs = {
            "max_new_tokens": max_new_tokens,
            "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
            "eos_token_id": tokenizer.eos_token_id,
            "repetition_penalty": 1.05,
            "top_p": 0.8,
            "top_k": 20,
        }


        if temperature > 0:

            generation_kwargs.update({

                "temperature":
                    temperature,

                "do_sample":
                    True

            })

        else:

            generation_kwargs.update({

                "do_sample":
                    False

            })


        with torch.no_grad():

            output = model.generate(
                **inputs,
                **generation_kwargs
            )


        new_tokens = output[0][
            inputs["input_ids"].shape[1]:
        ]


        text = tokenizer.decode(
            new_tokens,
            skip_special_tokens=True
        )


        return text.strip()


runtime = ModelRuntime()
