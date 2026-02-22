import re
import diff_match_patch as dmp_module


def compute_diff(old_text: str, new_text: str) -> list[dict]:
    """
    Compute a word-level diff between two text strings.

    Each word/whitespace token is treated as atomic, so identical words
    are always marked '=' even if surrounding layout or line structure
    differs between the two PDFs.

    Returns a list of operations:
        {"op": "=", "text": "..."} - unchanged
        {"op": "+", "text": "..."} - added in new
        {"op": "-", "text": "..."} - deleted from old
    """
    dmp = dmp_module.diff_match_patch()

    # Build a shared vocabulary: map each unique token to a Unicode char.
    # Tokens are alternating word-runs and whitespace-runs so every
    # character of the original text is preserved exactly.
    token_list = ['']   # index 0 reserved (diff_match_patch convention)
    token_map: dict[str, int] = {}

    def encode(text: str) -> str:
        chars = []
        for tok in re.findall(r'\S+|\s+', text):
            if tok not in token_map:
                token_list.append(tok)
                token_map[tok] = len(token_list) - 1
            chars.append(chr(token_map[tok]))
        return ''.join(chars)

    enc_old = encode(old_text)
    enc_new = encode(new_text)

    # Diff the token-encoded strings, then decode back to text
    diffs = dmp.diff_main(enc_old, enc_new, False)
    dmp.diff_charsToLines(diffs, token_list)   # reuse decoder (works for any token list)
    dmp.diff_cleanupSemantic(diffs)

    op_map = {-1: "-", 0: "=", 1: "+"}
    return [{"op": op_map[op], "text": text} for op, text in diffs]