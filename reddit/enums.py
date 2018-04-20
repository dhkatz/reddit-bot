from enum import Enum
from typing import NamedTuple, Optional

# DO NOT REMOVE HEADER OR FOOTER
HEADER = """
**Unfortunately, we've had to remove your post.**
___

"""

FOOTER = """

___
[**Here are our subreddit rules.**](https://www.reddit.com/r/FortNiteBR/wiki/rules) - If you have any queries about this, you can contact us via [Moderator Mail](https://www.reddit.com/message/compose?to=%2Fr%2FFortNiteBR).
"""

# CUSTOM REMOVAL REASONS

flair = """
### Post Flair Guidelines

We require all users to set a post flair for their own post. There is a 30 minute grace period, and this has passed for this post. 

For more information, please read [this post](https://www.reddit.com/r/FortNiteBR/comments/8bznpy/state_of_the_subreddit_new_moderators_survey/).
"""

domain = """
### Restricted Domain

The domain you are submitting from is currently on our list of restricted domains. 

All links submitted from this domain are prohibited as long as the restriction remains.
"""

promotion = """
### Promotion Guidelines

In order keep the subreddit free of advertisement, we enforce a strict 10:1 rule which states;

**For every one promotional post you submit, 10 high-quality comments or submissions should be non-promotional.**

What counts as promotion?

- Links to videos 

- Links to community websites

- Links to community content channels- streams, youtube channels, etc.

- Links to written articles

- Links to artwork and fan literature

- Feedback on content in the form of discussions, polls, etc.

- References to the above list

- Promotional comments in general

You also may also only make one promotional post every 3-4 days and any giveaway must be approved by the moderation team ahead of time.
"""


class Rule(Enum):
    def __str__(self):
        return str(HEADER + self.value + FOOTER)

    FLAIR = flair
    DOMAIN = domain
    PROMOTION = promotion
    NONE = 'none'


Valid = NamedTuple('Valid', [('removed', bool), ('reason', Optional[Rule])])
