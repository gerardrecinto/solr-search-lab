import random
import string


def random_tag(length: int = 12) -> str:
    """Pure lowercase letters, no digits or case changes -- WordDelimiterGraphFilter
    (the field type's tokenizer chain, see config/setup_schema.py) splits
    on digit/letter transitions and case changes. A mixed-case or
    alphanumeric tag (e.g. a uuid hex fragment) gets split into multiple
    short sub-tokens, some of which can accidentally match unrelated
    documents already in the shared test core. A pure-letter tag stays as
    a single token through analysis, so `message:{tag}` is an exact,
    isolated match."""
    return "".join(random.choices(string.ascii_lowercase, k=length))
