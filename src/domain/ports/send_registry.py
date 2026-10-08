from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.campaign import Campaign


class SendRegistry(ABC):
    """Port that defines how to track the progress of an email campaign.

    A campaign is identified by a Campaign value (see its attributes): the
    same choices a user would make again when restarting an interrupted
    bulk send. Implementations persist this state locally so that resuming
    the same campaign:

    - does not re-send emails to contacts already reached,
    - continues the schedule right after the last slot already queued,
    - can warn about attempts whose outcome is unknown (possible duplicates).

    Every send attempt is recorded with mark_attempt() before calling the
    delivery service, and resolved afterwards with mark_sent() or
    discard_attempt(). Attempts left unresolved are the uncertain ones.
    """

    @abstractmethod
    def get_sent_contact_ids(
        self, campaign: Campaign
    ) -> set[int]:
        """Return the IDs of contacts already sent an email in this campaign.

        Args:
            campaign: Campaign the progress belongs to.

        Returns:
            A set of contact IDs. Empty when the campaign has no recorded
            sends yet.
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
    def get_uncertain_attempts(
        self, campaign: Campaign
    ) -> dict[int, list[datetime]]:
        """Return the attempts of this campaign whose outcome is unknown.

        Args:
            campaign: Campaign the progress belongs to.

        Returns:
            A dict mapping each contact ID to the list of send slots that
            were attempted but never resolved. Empty when there are none.
        """
        pass

    @abstractmethod
    def mark_attempt(
        self, campaign: Campaign,
        contact_id: int, start_date: datetime,
    ) -> None:
        """Record that an email is about to be sent to a contact for a given slot.

        Must be called right before calling the delivery service and be
        persisted immediately, so an abrupt close leaves the attempt on
        record as uncertain. Also advances the campaign's last start date.

        Args:
            campaign: Campaign the progress belongs to.
            contact_id: ID of the contact about to be emailed.
            start_date: Send slot requested for this email.
        """
        pass

    @abstractmethod
    def mark_sent(
        self, campaign: Campaign,
        contact_id: int, start_date: datetime,
    ) -> None:
        """Record that a contact successfully received an email in this campaign.

        Resolves the attempt for the same slot, if any, and advances the
        campaign's last start date. Earlier unresolved attempts of the same
        contact are kept, since they may be duplicates. Implementations
        must persist this immediately so progress survives an interruption.

        Args:
            campaign: Campaign the progress belongs to.
            contact_id: ID of the contact that was successfully emailed.
            start_date: Send slot the email was scheduled for.
        """
        pass

    @abstractmethod
    def discard_attempt(
        self, campaign: Campaign,
        contact_id: int, start_date: datetime,
    ) -> None:
        """Resolve an attempt known not to have scheduled any email.

        The last start date is not rolled back, so later runs still stay
        after this slot.

        Args:
            campaign: Campaign the progress belongs to.
            contact_id: ID of the contact whose attempt failed.
            start_date: Send slot of the failed attempt.
        """
        pass

    @abstractmethod
    def clear(self, campaign: Campaign) -> None:
        """Forget everything recorded for this campaign.

        Called once a campaign completes with no pending or errored
        contacts, so a legitimate future re-send to the same group,
        template and field is not blocked.

        Args:
            campaign: Campaign the progress belongs to.
        """
        pass
