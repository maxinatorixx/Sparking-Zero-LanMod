"""Recovered own card/proficiency updates; neither is a match result."""
import unicodedata

RANK_ROUTE='/user/update_player_rank.php'
PROFICIENCY_ROUTE='/user/update_proficiency_rank.php'
PROFILE_ROUTES=(RANK_ROUTE,PROFICIENCY_ROUTE)

def validate_profile_update(path,body):
    if type(body) is not dict or path not in PROFILE_ROUTES:
        raise ValueError('unsupported native profile update')
    expected={'player_rank'} if path==RANK_ROUTE else {'character_id','character_proficiency_rank'}
    if set(body)!=expected:
        raise ValueError('invalid native profile fields')
    field='player_rank' if path==RANK_ROUTE else 'character_proficiency_rank'
    if type(body[field]) is not int or not -128<=body[field]<=127:
        raise ValueError('invalid native profile rank')
    if path==PROFICIENCY_ROUTE:
        char=body['character_id']
        if (type(char) is not str or not char or len(char.encode('utf-8'))>128
                or any(unicodedata.category(c)=='Cc' for c in char)):
            raise ValueError('invalid native character id')
    return dict(body)
