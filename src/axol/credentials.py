# credentials for search providers that require tokens
# meant to be overridden in the private config
# TODO perhaps this should all be under axol.config subpackage? and that's the one to be overridden


# TODO maybe this should be inside the corresponding user config under axol.modules.reddit.credentials? dunno
def reddit_praw() -> dict[str, str]:
    raise NotImplementedError


def github_token() -> str:
    raise NotImplementedError
