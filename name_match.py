"""Rough JP<->KR product-name similarity: romanize katakana and hangul, normalize Uniqlo terms."""
import re
from difflib import SequenceMatcher

# Shared Uniqlo vocabulary -> canonical tokens (applied before romanization).
GLOSSARY = [
    (r"超極暖|울트라웜", "ULTRAWARM"), (r"極暖|엑스트라웜", "EXTRAWARM"),
    (r"ヒートテック|히트텍", "HEATTECH"), (r"エアリズム|에어리즘|AIRism", "AIRISM"),
    (r"感動|감탄", "KANDO"), (r"長袖|긴팔", "LS"), (r"半袖|반팔", "SS"), (r"ノースリーブ|슬리브리스|민소매", "NSL"),
    (r"(\d)枚組|(\d)P", r"\1\2P"), (r"(\d)足組", r"\1P"), (r"Tシャツ|T셔츠", "T"), (r"UVカット|UV PROTECTION|UV ?컷", "UV"),
    (r"ボタンダウン|버튼다운|BD", "BD"), (r"ジーンズ|진", "JEANS"), (r"ジャケット|재킷", "JACKET"),
    (r"パーカ|파카|후디", "PARKA"), (r"セーター|스웨터", "SWEATER"), (r"カーディガン|가디건", "CARDIGAN"),
    (r"レギンス|레깅스", "LEGGINGS"), (r"タイツ|타이츠|타이즈", "TIGHTS"), (r"ソックス|삭스|양말", "SOCKS"),
    (r"ショーツ|쇼츠|쇼트팬츠", "SHORTS"), (r"パンツ|팬츠", "PANTS"), (r"シャツ|셔츠", "SHIRT"),
    (r"ワンピース|원피스", "DRESS"), (r"スカート|스커트", "SKIRT"), (r"ブラ|브라", "BRA"),
    (r"マタニティ|마터니티|임부", "MATERNITY"), (r"ステテコ|스테테코", "STETECO"),
    (r"KIDS|BOYS|GIRLS|GIRS|BABY|キッズ|ベビー|키즈|베이비|WOMEN|MEN", ""),
]
KANA = dict(zip(
    "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンガギグゲゴザジズゼゾダヂヅデドバビブベボパピプペポヴ",
    "a i u e o ka ki ku ke ko sa shi su se so ta chi tsu te to na ni nu ne no ha hi fu he ho ma mi mu me mo ya yu yo ra ri ru re ro wa o n ga gi gu ge go za ji zu ze zo da ji zu de do ba bi bu be bo pa pi pu pe po vu".split()))
SMALL = {"ャ": "ya", "ュ": "yu", "ョ": "yo", "ァ": "a", "ィ": "i", "ゥ": "u", "ェ": "e", "ォ": "o"}
HI = "g kk n d tt r m b pp s ss  j jj ch k t p h".split(" ")
HM = "a ae ya yae eo e yeo ye o wa wae oe yo u wo we wi yu eu ui i".split()
HF = ["", "k", "k", "k", "n", "n", "n", "t", "l", "k", "m", "l", "l", "l", "p", "l", "m", "p", "p", "t", "t", "ng", "t", "t", "k", "t", "p", "t"]


def roman_kana(s):
    out = []
    for ch in s:
        if ch in SMALL and out:  # キャ -> kya, ファ -> fa
            prev = out.pop()
            out.append((prev[:-1] if prev[-1] in "iu" else prev) + SMALL[ch])
        elif ch in KANA:
            out.append(KANA[ch])
        elif ch not in "ッー・":
            out.append(ch)
    return "".join(out)


def roman_hangul(s):
    out = []
    for ch in s:
        c = ord(ch) - 0xAC00
        if 0 <= c < 11172:
            out.append(HI[c // 588] + HM[(c % 588) // 28] + HF[c % 28])
        else:
            out.append(ch)
    return "".join(out)


def vowel_fold(s):
    # collapse spelling differences between the two romanizations
    s = s.lower()
    for a, b in [("eo", "o"), ("eu", "u"), ("ae", "e"), ("shi", "si"), ("chi", "ci"), ("tsu", "su"), ("ji", "ci"),
                 ("ch", "c"), ("j", "c"), ("f", "p"), ("h", "p"), ("l", "r"), ("ng", "n"), ("kk", "k"), ("tt", "t"),
                 ("pp", "p"), ("ss", "s"), ("g", "k"), ("d", "t"), ("b", "p"), ("z", "c"), ("v", "p"), ("w", ""), ("y", "")]:
        s = s.replace(a, b)
    return re.sub(r"[aeiou]+", lambda m: m.group(0)[0], s)


def norm(name, roman):
    s = name
    for pat, rep in GLOSSARY:
        s = re.sub(pat, rep, s)
    tokens = re.findall(r"[A-Z0-9]{2,}|[^\sA-Z0-9/()（）・·&,.\-]+", s)
    canon = sorted(t for t in tokens if t.isupper() or t.isdigit())
    rest = "".join(t for t in tokens if not (t.isupper() or t.isdigit()))
    rest = re.sub(r"[一-龥]+", "", rest)  # leftover kanji (丈長め 等) is dropped
    return canon, vowel_fold(roman(rest))


def similarity(jp_name, kr_name):
    jc, jr = norm(jp_name, roman_kana)
    kc, kr = norm(kr_name, roman_hangul)
    text = SequenceMatcher(None, jr, kr).ratio() if jr and kr else 0.0
    union = set(jc) | set(kc)
    canon = len(set(jc) & set(kc)) / len(union) if union else 1.0
    return round(0.7 * text + 0.3 * canon, 3)


if __name__ == "__main__":
    tests = [("ライトダウンボリュームジャケット", "라이트다운볼륨재킷", True),
             ("スマートアンクルマタニティパンツ", "히트텍타이즈", False),
             ("BOYS エアリズムボクサーブリーフ/3枚組/前閉じ", "BOYS AIRism복서브리프3P", True)]
    for j, k, same in tests:
        s = similarity(j, k)
        print(f"{s:.3f} {'OK ' if (s >= 0.6) == same else 'BAD'} {j} | {k}")
        assert (s >= 0.6) == same
