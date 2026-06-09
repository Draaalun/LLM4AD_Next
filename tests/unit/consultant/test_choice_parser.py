"""Unit tests for the choice parser in the consultant advisor."""

from llm4ad.consultant.advisor import parse_choices


class TestParseChoices:
    """Tests for parse_choices() function."""

    def test_standard_three_choices(self):
        """Parse a standard 3-choice block."""
        response = (
            "Which provider type would you like to use?\n\n"
            "  1) openai — Best for most users\n"
            "  2) anthropic — Strong reasoning\n"
            "  3) Enter your own value\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert len(choices) == 3
        assert choices[0].number == 1
        assert choices[0].label == "openai"
        assert choices[0].description == "Best for most users"
        assert choices[1].label == "anthropic"
        assert choices[2].is_custom is True

    def test_two_choices(self):
        """Parse a 2-choice block (minimum)."""
        response = (
            "Enable worktree isolation?\n\n"
            "  1) Yes — recommended\n"
            "  2) No\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert len(choices) == 2
        assert choices[0].label == "Yes"
        assert choices[1].label == "No"
        assert choices[1].description == ""

    def test_recommended_marker(self):
        """Parse choices with (recommended) marker."""
        response = (
            "  1) gpt-4o (recommended) — balanced\n"
            "  2) gpt-4o-mini — cheaper\n"
            "  3) Custom input\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert choices[0].is_recommended is True
        assert choices[0].label == "gpt-4o"
        assert choices[1].is_recommended is False

    def test_recommended_with_extra_text(self):
        """Parse (recommended for testing) variant."""
        response = (
            "  1) Small: 2 islands (recommended for testing) — quick\n"
            "  2) Medium: 5 islands — balanced\n"
            "  3) Custom\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert choices[0].is_recommended is True
        assert choices[0].label == "Small: 2 islands"

    def test_chinese_text(self):
        """Parse choices with Chinese text."""
        response = (
            "请选择评估器类型:\n\n"
            "  1) custom — Python 自定义评估器\n"
            "  2) executable — 编译后的可执行程序\n"
            "  3) 自行填写\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert len(choices) == 3
        assert choices[0].label == "custom"
        assert choices[2].is_custom is True

    def test_custom_input_variants(self):
        """Various phrasings for the custom input option are detected."""
        templates = [
            "  1) a — desc\n  2) Enter your own value\n",
            "  1) a — desc\n  2) Type a custom value\n",
            "  1) a — desc\n  2) 手动输入\n",
            "  1) a — desc\n  2) 其他\n",
            "  1) a — desc\n  2) Provide your own\n",
            "  1) a — desc\n  2) Other — specify a custom value\n",
        ]
        for text in templates:
            choices = parse_choices(text)
            assert choices is not None, f"Failed to parse: {text!r}"
            assert choices[-1].is_custom is True, f"Custom not detected: {text!r}"

    def test_non_custom_last_option(self):
        """Last option without custom keywords is not marked custom."""
        response = (
            "  1) island_ga — recommended\n"
            "  2) dyca — for diverse instances\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert choices[-1].is_custom is False

    def test_multi_block_takes_last(self):
        """When response has multiple choice blocks, take the last one."""
        response = (
            "Great, you chose openai. Now for the model:\n\n"
            "  1) option_a — old question\n"
            "  2) option_b — old question\n\n"
            "Actually, which model would you like?\n\n"
            "  1) gpt-4o — fast and capable\n"
            "  2) gpt-4o-mini — cheaper\n"
            "  3) Enter model name\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert len(choices) == 3
        assert choices[0].label == "gpt-4o"

    def test_no_choices_returns_none(self):
        """Returns None when no choices are found."""
        response = "Please tell me about your project background."
        assert parse_choices(response) is None

    def test_single_choice_returns_none(self):
        """Returns None when only 1 choice found (need >= 2)."""
        response = "  1) only_one — not enough\n"
        assert parse_choices(response) is None

    def test_malformed_numbering_returns_none(self):
        """Returns None when numbering doesn't start from 1."""
        response = (
            "  3) something — desc\n"
            "  4) another — desc\n"
        )
        assert parse_choices(response) is None

    def test_bullet_points_not_matched(self):
        """Bullet point lists are not parsed as choices."""
        response = (
            "Here are some tips:\n"
            "  - Use env vars for API keys\n"
            "  - Keep timeout reasonable\n"
        )
        assert parse_choices(response) is None

    def test_full_text_preserved(self):
        """full_text contains the original text after the number."""
        response = (
            "  1) gpt-4o (recommended) — fast and capable\n"
            "  2) Enter your own\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert choices[0].full_text == "gpt-4o (recommended) — fast and capable"

    def test_hyphen_separator(self):
        """Choices with spaced-hyphen separator are parsed."""
        response = (
            "  1) openai - standard API\n"
            "  2) anthropic - Claude models\n"
            "  3) Other\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert choices[0].label == "openai"
        assert choices[0].description == "standard API"

    def test_stage_complete_marker_ignored(self):
        """Choice parsing works even when [STAGE_COMPLETE] is in the response."""
        response = (
            "  1) Yes — looks good\n"
            "  2) No — let me change something\n"
            "[STAGE_COMPLETE]"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert len(choices) == 2

    def test_four_choices(self):
        """Parse a 4-choice block."""
        response = (
            "  1) weighted (recommended) — default\n"
            "  2) tournament — competitive selection\n"
            "  3) roulette — probability based\n"
            "  4) Enter your own\n"
        )
        choices = parse_choices(response)
        assert choices is not None
        assert len(choices) == 4
        assert choices[0].is_recommended is True
        assert choices[3].is_custom is True
