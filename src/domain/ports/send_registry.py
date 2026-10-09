from abc import ABC, abstractmethod
from datetime import date, datetime

from src.domain.entities.campaign import Campaign


class SendRegistry(ABC):
    """Port that defines how to track the progress of an email campaign.

    A campaign is identified by a Campaign value (see its attributes): the
    same choices a user would make again when restarting an interrupted
    bulk send. Each recipient is identified by its key (see Recipient).
    Implementations persist this state locally so that resuming the same
    campaign:

    - does not re-send emails to recipients already reached,
    - continues the schedule right after the last slot already queued,
    - can warn about attempts whose outcome is unknown (possible duplicates).

    Every send attempt is recorded with mark_attempt() before calling the
    delivery service, and resolved afterwards with mark_sent() or
    discard_attempt(). Attempts left unresolved are the uncertain ones.
    """

    @abstractmethod
    def get_sent_keys(
        self, campaign: Campaign
    ) -> set[str]:
        """Return the keys of the recipients already sent an email in this campaign.

        Args:
            campaign: Campaign the progress belongs to.

        Returns:
            A set of recipient keys. Empty when the campaign has no
            recorded sends yet.
        """
        pass

    @abstractmethod
    def get_last_start_date(
        self, campaign: Campaign
    ) -> datetime | None:
        """Return the latest send slot ever attempted in this campaign.

        Args:
            campaign: Campaign the progress belongs to.

        Returns:
            The latest start_date passed to mark_attempt() or mark_sent(),
            or None when the campaign has no record.
        """
        pass

    @abstractmethod
    def get_last_start_dates_by_day(
        self, campaign: Campaign
    ) -> dict[date, datetime]:
        """Return the latest slot attempted for each send day of this campaign.

        Used in the contact date mode, where every day is resumed on its
        own right after its last slot.

        Args:
            campaign: Campaign the progress belongs to.

        Returns:
            A dict mapping each send day passed to mark_attempt() or
            mark_sent() to its latest slot. Empty when there is none.
        """
        pass

    @abstractmethod
    def get_uncertain_attempts(
        self, campaign: Campaign
    ) -> dict[str, list[datetime]]:
        """Return the attempts of this campaign whose outcome is unknown.

        Args:
            campaign: Campaign the progress belongs to.

        Returns:
            A dict mapping each recipient key to the list of send slots
            that were attempted but never resolved. Empty when there are
            none.
        """
        pass

    @abstractmethod
    def mark_attempt(
        self, campaign: Campaign,
        key: str, start_date: datetime, day: date | None = None,
    ) -> None:
        """Record that an email is about to be sent to a recipient for a given slot.

        Must be called right before calling the delivery service and be
        persisted immediately, so an abrupt close leaves the attempt on
        record as uncertain. Also advances the campaign's last start date,
        and that of the send day when one is given.

        Args:
            campaign: Campaign the progress belongs to.
            key: Key of the recipient about to be emailed.
            start_date: Send slot requested for this email.
            day: Send day of the recipient in the contact date mode, or None.
        """
        pass

    @abstractmethod
    def mark_sent(
        self, campaign: Campaign,
        key: str, start_date: datetime, day: date | None = None,
    ) -> None:
        """Record that a recipient successfully received an email in this campaign.

        Resolves the attempt for the same slot, if any, and advances the
        campaign's last start date, and that of the send day when one is
        given. Earlier unresolved attempts of the same
        recipient are kept, since they may be duplicates. Implementations
        must persist this immediately so progress survives an interruption.

        Args:
            campaign: Campaign the progress belongs to.
            key: Key of the recipient that was successfully emailed.
            start_date: Send slot the email was scheduled for.
            day: Send day of the recipient in the contact date mode, or None.
        """
        pass

    @abstractmethod
    def discard_attempt(
        self, campaign: Campaign,
        key: str, start_date: datetime,
    ) -> None:
        """Resolve an attempt known not to have scheduled any email.

        The last start date is not rolled back, so later runs still stay
        after this slot.

        Args:
            campaign: Campaign the progress belongs to.
            key: Key of the recipient whose attempt failed.
            start_date: Send slot of the failed attempt.
        """
        pass

    @abstractmethod
    def clear(self, campaign: Campaign) -> None:
        """Forget everything recorded for this campaign.

        Called once a campaign completes with no pending or errored
        recipients, so a legitimate future re-send of the same campaign is
        not blocked.

        Args:
            campaign: Campaign the progress belongs to.
        """
        pass
