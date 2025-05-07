from enum import Enum


class Model(Enum):
    GPT_4_O = "gpt-4o"
    GPT_4_1 = "gpt-4.1"
    O3 = "o3"
    O4_MINI = "o4-mini"
    CLAUDE_SONNET_3_7 = "claude-3-7-sonnet-latest"
    CLAUDE_SONNET_3_5 = "claude-3-5-sonnet-latest"
    GEMINI_2_5_PRO = "gemini-2.5-pro-preview-03-25"
    GEMINI_2_5_PRO_EXP = "gemini-2.5-pro-exp-03-25"

    def is_anthropic(self):
        return self in [
            Model.CLAUDE_SONNET_3_7,
            Model.CLAUDE_SONNET_3_5,
        ]

    def is_gemini(self):
        return self in [
            Model.GEMINI_2_5_PRO,
            Model.GEMINI_2_5_PRO_EXP,
        ]
