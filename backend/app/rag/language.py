"""Answer-language support for the Regulatory Copilot.

Only the *language of the generated answer* is affected. Retrieval, grounding,
sources and safety rules are unchanged; English remains the default.
"""
import re

_LANGUAGE_NAMES = {"hi": "Hindi (Devanagari script)", "mr": "Marathi (Devanagari script)"}


def language_instruction(language: str | None) -> str:
    """Extra system-prompt text; empty string for English/unknown so prompts stay unchanged."""
    name = _LANGUAGE_NAMES.get((language or "en").lower())
    if not name:
        return ""
    return (
        f" Write the entire answer in natural, professional {name}. "
        "Do not use romanised Hindi/Marathi. Keep official names, scheme names, "
        "approval/form/document identifiers, section numbers and technical terms such as "
        "AI, API, SLA, MPCB and MIDC exactly as in the source. "
        "The answer must stay strictly grounded in the provided context; do not add facts."
    )


NO_CONTEXT_MESSAGES = {
    "hi": (
        "मुझे उपलब्ध नियमों में इसका उत्तर नहीं मिला। कृपया किसी विशिष्ट अनुमोदन के बारे में पूछें "
        "(जैसे फैक्ट्री लाइसेंस, MPCB सहमति, बॉयलर पंजीकरण या फायर NOC), या अपना प्रश्न अधिक विवरण के साथ दोबारा लिखें।"
    ),
    "mr": (
        "मला उपलब्ध नियमांमध्ये याचे उत्तर सापडले नाही. कृपया एखाद्या विशिष्ट मंजुरीबद्दल विचारा "
        "(उदा. कारखाना परवाना, MPCB संमती, बॉयलर नोंदणी किंवा फायर NOC), किंवा तुमचा प्रश्न अधिक तपशिलासह पुन्हा लिहा."
    ),
}


_DEVANAGARI = re.compile(r"[\u0900-\u097F]")


async def english_for_retrieval(question: str, language: str | None) -> str:
    """Translate a Hindi/Marathi question to English so the (English, keyword-based)
    retrieval and intent detection can work. Returns the original question if the
    text is not Devanagari, the language is English, or translation fails/looks wrong.
    The regulatory knowledge base itself is never translated.
    """
    if (language or "en") not in _LANGUAGE_NAMES or not _DEVANAGARI.search(question or ""):
        return question
    try:
        from app.ai.llm_provider import generate_with_fallback

        translated = await generate_with_fallback(
            "You are a translator. Translate the user's question into plain English. "
            "Output only the translated question, nothing else. Keep identifiers such as "
            "MPCB, MIDC, NOC and scheme names unchanged.",
            question,
            temperature=0.0,
        )
    except Exception:  # noqa: BLE001 - translation is best-effort; fall back to the original
        return question
    translated = (translated or "").strip().strip('"')
    latin = len(re.findall(r"[A-Za-z]", translated))
    if not translated or len(translated) > 500 or _DEVANAGARI.search(translated) or latin < 3:
        return question
    return translated
