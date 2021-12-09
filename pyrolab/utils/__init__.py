import secrets
import pkg_resources


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def generate_random_name(count=3) -> str:
    """
    Reads ``count`` random words and returns them as a hyphenated string.

    Wordlist is located in pyrolab/data/wordlist.txt.

    Parameters
    ----------
    count : int, optional
        How many words to use in the hyphenated string.

    Returns
    -------
    str
        A hyphenated string of ``count`` random words.
    """
    import random
    from pathlib import Path

    path = Path(pkg_resources.resource_filename('pyrolab', "data/wordlist.txt"))
    with open(path, 'r') as f:
        wordlist = f.read().splitlines()

    # random.shuffle(wordlist)
    # return '-'.join(wordlist[:count])
    return '-'.join([secrets.choice(wordlist) for _ in range(count)])
