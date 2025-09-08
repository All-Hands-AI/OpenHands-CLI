from enum import Enum


class UserConfirmation(Enum):
    ACCEPT = "accept"
    REJECT = "reject"
    REJECT_WITH_REASON = "reject_with_reason"
    DEFER = "defer"
