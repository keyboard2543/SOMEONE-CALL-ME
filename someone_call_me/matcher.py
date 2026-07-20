"""Fuzzy + phonetic name matching for distant / similar-sounding calls."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz

try:
    import jellyfish
except ImportError:  # pragma: no cover
    jellyfish = None  # type: ignore


_CALL_PREFIXES = (
    "คุณ",
    "พี่",
    "น้อง",
    "เฮ้",
    "เฮ้ย",
    "เฮ้ยย",
    "โอ้ย",
    "อ้าว",
    "เอ้ย",
    "เว้ย",
    "hey",
    "hi",
    "hello",
    "yo",
    "oi",
    "oy",
    "excuse me",
    "mister",
    "miss",
    "mr",
    "ms",
    "khun",
    "phi",
    "nong",
)

_CALL_SUFFIXES = (
    "ครับ",
    "ค่ะ",
    "คะ",
    "จ้า",
    "จ๊ะ",
    "นะ",
    "น่ะ",
    "สิ",
    "หน่อย",
    "please",
    "bro",
    "dude",
)


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    score: float
    best_target: str
    heard_text: str
    reason: str


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s\u0e00-\u0e7f]", " ", text, flags=re.UNICODE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _strip_call_affixes(text: str) -> str:
    compact = text.strip()
    # ตัดซ้ำได้หลายชั้น (เช่น "เฮ้ คุณสมชาย ครับ")
    changed = True
    while changed:
        changed = False
        for p in _CALL_PREFIXES:
            # latin word-ish
            if re.match(rf"^{re.escape(p)}\b\s*", compact, flags=re.IGNORECASE):
                compact = re.sub(rf"^{re.escape(p)}\b\s*", "", compact, flags=re.IGNORECASE)
                changed = True
            elif compact.startswith(p) and len(compact) > len(p):
                # thai / no boundary
                rest = compact[len(p) :]
                if rest[:1].isspace() or not _is_latin(p):
                    compact = rest.lstrip()
                    changed = True
        for s in _CALL_SUFFIXES:
            if re.search(rf"\b{re.escape(s)}$", compact, flags=re.IGNORECASE):
                compact = re.sub(rf"\s*\b{re.escape(s)}$", "", compact, flags=re.IGNORECASE)
                changed = True
            elif compact.endswith(s) and len(compact) > len(s):
                compact = compact[: -len(s)].rstrip()
                changed = True
    return re.sub(r"\s+", " ", compact).strip()


def _thai_loose(text: str) -> str:
    """ทำให้ตัวสะกดไทยที่มักออกเสียงคล้ายกันใกล้กันมากขึ้น."""
    text = re.sub(r"[\u0e31\u0e34-\u0e3a\u0e47-\u0e4e]", "", text)
    replacements = (
        ("ใ", "ไ"),
        ("ฤ", "ริ"),
        ("ฦ", "ลุ"),
        ("ฆ", "ค"),
        ("ฌ", "ช"),
        ("ญ", "ย"),
        ("ฎ", "ด"),
        ("ฏ", "ต"),
        ("ฐ", "ถ"),
        ("ฑ", "ท"),
        ("ฒ", "ท"),
        ("ณ", "น"),
        ("ศ", "ส"),
        ("ษ", "ส"),
        ("ฬ", "ล"),
        ("ฮ", "ห"),
        ("ๆ", ""),
        ("ฯ", ""),
    )
    for a, b in replacements:
        text = text.replace(a, b)
    return text


def _is_latin(text: str) -> bool:
    return bool(re.search(r"[a-zA-Z]", text)) and not bool(
        re.search(r"[\u0e00-\u0e7f]", text)
    )


def _generate_variants(name: str) -> set[str]:
    n = _normalize(name)
    variants: set[str] = {n}
    loose = _thai_loose(n)
    if loose:
        variants.add(loose)

    if len(n) >= 2:
        variants.add(n + n[-1] * 2)
        variants.add(n + n[-1] * 4)

    if _is_latin(n):
        collapsed = re.sub(r"(.)\1+", r"\1", n)
        if len(collapsed) >= 3:
            variants.add(collapsed)
        if n.endswith("y") and len(n) > 2:
            variants.add(n[:-1] + "ie")
            variants.add(n[:-1] + "i")
        if n.endswith("ie") and len(n) > 3:
            variants.add(n[:-2] + "y")
        if n.endswith("ey") and len(n) > 3:
            variants.add(n[:-2] + "y")
        if n.endswith("n") and len(n) >= 4:
            # john ↔ jon
            variants.add(n[:-1])

    return {v for v in variants if v}


def _word_tokens(text: str) -> set[str]:
    tokens = set(text.split())
    # ไทยมักติดกัน — ถ้ามีช่องว่างใช้อันนั้น, ไม่งั้นทั้งก้อน
    if not tokens:
        return set()
    return {t for t in tokens if len(t) >= 2}


def _windows_around_name_length(text: str, name_len: int) -> set[str]:
    compact = text.replace(" ", "")
    if not compact:
        return set()
    # หน้าต่างใกล้ความยาวชื่อเท่านั้น
    L = max(3, name_len - 1)
    R = name_len + 2
    out: set[str] = set()
    if L <= len(compact) <= R:
        out.add(compact)
    for i in range(0, len(compact) - L + 1):
        for w in range(L, min(R, len(compact) - i) + 1):
            out.add(compact[i : i + w])
    return out


class NameMatcher:
    def __init__(self, targets: list[str], sensitivity: float = 68.0) -> None:
        self.sensitivity = max(0.0, min(100.0, float(sensitivity)))
        self.threshold = self.sensitivity
        self.targets = [_normalize(t) for t in targets if t and t.strip()]
        self.variants: dict[str, set[str]] = {
            t: _generate_variants(t) for t in self.targets
        }
        self.metaphones: dict[str, str] = {}
        if jellyfish is not None:
            for t in self.targets:
                if _is_latin(t):
                    try:
                        self.metaphones[t] = (jellyfish.metaphone(t) or "").lower()
                    except Exception:
                        pass

    def _score_candidate(
        self, target: str, variant: str, candidate: str, *, embedded: bool
    ) -> float:
        """
        embedded=True: candidate คือประโยคเต็ม (อนุญาต partial)
        embedded=False: candidate คือ token/window ควรเทียบแบบเต็ม ๆ
        """
        if not candidate or not variant:
            return 0.0

        v = variant
        c = candidate
        vl, cl = len(v), len(c)

        # exact / loose contains
        if v == c or _thai_loose(v) == _thai_loose(c):
            return 100.0
        if embedded and (v in c or _thai_loose(v) in _thai_loose(c)):
            return 100.0

        ratio = float(fuzz.ratio(v, c))
        partial = float(fuzz.partial_ratio(v, c))

        # partial_ratio ใช้ได้เมื่อ candidate ยาวกว่า/เท่า variant เท่านั้น
        # (หาชื่อฝังในประโยค) — ห้ามใช้เมื่อ candidate สั้นกว่า ไม่งั้น "hin"~"john" จะสูงผิด
        if cl < max(3, int(vl * 0.65)):
            return 0.0

        if cl >= vl:
            score = max(ratio, partial if (embedded or cl <= vl + 4) else ratio)
        else:
            # candidate สั้นกว่าชื่อเล็กน้อย (jon/john) — ใช้ ratio อย่างเดียว
            score = ratio
            if cl >= vl - 1 and vl >= 3:
                # อนุญาต soft boost เล็กน้อยเมื่อขาดแค่ 1 ตัว
                score = max(score, ratio)

        # phonetic (อังกฤษ) — เฉพาะความยาวใกล้กัน
        if (
            jellyfish is not None
            and _is_latin(v)
            and _is_latin(c)
            and abs(cl - vl) <= 2
            and cl >= 3
        ):
            try:
                meta_t = self.metaphones.get(target) or (
                    jellyfish.metaphone(target) or ""
                ).lower()
                meta_c = (jellyfish.metaphone(c) or "").lower()
                if meta_t and meta_t == meta_c:
                    score = max(score, 91.0)
                elif jellyfish.soundex(v) == jellyfish.soundex(c):
                    score = max(score, 87.0)
            except Exception:
                pass

        return float(score)

    def score_text(self, heard: str) -> MatchResult:
        raw = heard or ""
        text = _normalize(raw)
        if not text:
            return MatchResult(False, 0.0, "", raw, "empty")

        cleaned = _strip_call_affixes(text)
        full_forms = {
            text,
            cleaned,
            _thai_loose(text),
            _thai_loose(cleaned),
        }
        full_forms = {f for f in full_forms if f}

        best_score = 0.0
        best_target = ""
        best_reason = "no_match"

        for target in self.targets:
            variants = self.variants.get(target, {target})

            # 1) ประโยคเต็ม
            for form in full_forms:
                for v in variants:
                    s = self._score_candidate(target, v, form, embedded=True)
                    if s > best_score:
                        best_score, best_target, best_reason = s, target, f"full:{v}~{form}"

            # 2) คำที่แยกด้วยช่องว่าง
            tokens: set[str] = set()
            for form in full_forms:
                tokens |= _word_tokens(form)
                tokens |= {_thai_loose(t) for t in _word_tokens(form)}

            for tok in tokens:
                for v in variants:
                    s = self._score_candidate(target, v, tok, embedded=False)
                    if s > best_score:
                        best_score, best_target, best_reason = s, target, f"tok:{v}~{tok}"

            # 3) หน้าต่างความยาวใกล้ชื่อ (ไทยติดกัน)
            windows: set[str] = set()
            for form in full_forms:
                windows |= _windows_around_name_length(form, len(target))
                windows |= {
                    _thai_loose(w)
                    for w in _windows_around_name_length(form, len(target))
                }

            for win in windows:
                for v in variants:
                    s = self._score_candidate(target, v, win, embedded=False)
                    if s > best_score:
                        best_score, best_target, best_reason = s, target, f"win:{v}~{win}"

        matched = best_score >= self.threshold
        return MatchResult(
            matched=matched,
            score=best_score,
            best_target=best_target,
            heard_text=raw,
            reason=best_reason,
        )
