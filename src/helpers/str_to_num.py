import re
from num2words import num2words

def str_to_num(text: str) -> str:
    return re.sub(r"(\d+)", lambda m: num2words(m.group(), lang="en"), text)