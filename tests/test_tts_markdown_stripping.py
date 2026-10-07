import pytest
from app.services.tts_processor import tts_processor, strip_markdown_for_tts
from app.services.tts_service import tts_service

def test_bold_and_italic_markdown_stripping():
    """
    Test Case 1:
    Input: **Soil moisture is low.**
    Expected TTS text: 'Soil moisture is low.'
    NOT: 'asterisk asterisk Soil moisture is low...'
    """
    inp = "**Soil moisture is low.**"
    cleaned = strip_markdown_for_tts(inp)
    assert cleaned == "Soil moisture is low."
    assert "*" not in cleaned
    assert "_" not in cleaned

def test_bullet_list_and_temperature_unit_conversion():
    """
    Test Case 2:
    Input:
    - Soil moisture: **34%**
    - Temperature: **28°C**
    Expected TTS text:
    'Soil moisture: 34%.\n\nTemperature: 28 degrees Celsius.'
    NOT: 'dash Soil moisture...'
    """
    inp = "- Soil moisture: **34%**\n- Temperature: **28°C**"
    cleaned = strip_markdown_for_tts(inp, language="en")
    assert "Soil moisture: 34%." in cleaned
    assert "Temperature: 28 degrees Celsius." in cleaned
    assert not cleaned.startswith("-")
    assert "*" not in cleaned

def test_heading_and_percent_expansion():
    """
    Test Case 3:
    Input:
    ## Farm Condition

    **Current soil moisture:** 34%

    Expected:
    'Farm Condition.\n\nCurrent soil moisture: 34 percent.'
    NOT: 'hash hash Farm Condition...'
    """
    inp = "## Farm Condition\n\n**Current soil moisture:** 34%"
    cleaned = strip_markdown_for_tts(inp, language="en", expand_percent=True)
    assert "Farm Condition." in cleaned
    assert "Current soil moisture: 34 percent." in cleaned
    assert "#" not in cleaned
    assert "*" not in cleaned

def test_comprehensive_agricultural_advisor_text():
    """
    Test Section 3 Example:
    Input:
    **Your current soil moisture is 34.0%.**

    According to **TNAU - Tamil Nadu Agricultural University**:

    - Optimal range: **45%–65%**
    - Current condition: **LOW**

    **Prompt irrigation is recommended.**
    """
    inp = """**Your current soil moisture is 34.0%.**

According to **TNAU - Tamil Nadu Agricultural University**:

- Optimal range: **45%–65%**
- Current condition: **LOW**

**Prompt irrigation is recommended.**"""

    expected = """Your current soil moisture is 34.0%.

According to TNAU - Tamil Nadu Agricultural University:

Optimal range: 45%–65%.

Current condition: LOW.

Prompt irrigation is recommended."""

    cleaned = strip_markdown_for_tts(inp, language="en")
    assert cleaned == expected

def test_links_and_code_blocks_stripping():
    """
    Verifies that:
    1. Links [text](url) -> text (URL stripped)
    2. Inline code `code` -> code (backticks stripped)
    3. Fenced code blocks ```...``` are completely omitted from speech
    """
    link_inp = "Refer to [TNAU Agriculture Guide](https://agritech.tnau.ac.in) for details."
    cleaned_link = strip_markdown_for_tts(link_inp)
    assert "Refer to TNAU Agriculture Guide for details." in cleaned_link
    assert "http" not in cleaned_link

    code_inp = "Telemetry status: `ONLINE`.\n```python\nirrigate_field(duration=15)\n```\nPlease proceed."
    cleaned_code = strip_markdown_for_tts(code_inp)
    assert "Telemetry status: ONLINE." in cleaned_code
    assert "irrigate_field" not in cleaned_code
    assert "`" not in cleaned_code

def test_multilingual_tamil_and_malayalam_cleaning():
    """
    Verifies that Markdown is cleanly stripped from Tamil and Malayalam responses.
    """
    ta_inp = "**தற்போது உங்கள் மண் ஈரப்பதம் 36.4% ஆக உள்ளது.**"
    ta_cleaned = strip_markdown_for_tts(ta_inp, language="ta")
    assert ta_cleaned == "தற்போது உங்கள் மண் ஈரப்பதம் 36.4% ஆக உள்ளது."
    assert "*" not in ta_cleaned

    ml_inp = "**നിങ്ങളുടെ മണ്ണിലെ ഈർപ്പം 36.4% ആണ്.**"
    ml_cleaned = strip_markdown_for_tts(ml_inp, language="ml")
    assert ml_cleaned == "നിങ്ങളുടെ മണ്ണിലെ ഈർപ്പം 36.4% ആണ്."
    assert "*" not in ml_cleaned

@pytest.mark.asyncio
async def test_tts_service_integration_with_markdown():
    """
    Verifies that passing Markdown text to tts_service.generate_speech
    synthesizes cleanly without error for en, ta, and ml.
    """
    # English with Markdown
    res_en = await tts_service.generate_speech("**Soil moisture is optimal.**", language="en")
    assert res_en["audio_url"] is not None
    assert res_en["language"] == "en"

    # Tamil with Markdown
    res_ta = await tts_service.generate_speech("**மண் ஈரப்பதம் சீராக உள்ளது.**", language="ta")
    assert res_ta["audio_url"] is not None
    assert res_ta["language"] == "ta"

    # Malayalam with Markdown
    res_ml = await tts_service.generate_speech("**മണ്ണിലെ ഈർപ്പം അനുയോജ്യമാണ്.**", language="ml")
    assert res_ml["audio_url"] is not None
    assert res_ml["language"] == "ml"
