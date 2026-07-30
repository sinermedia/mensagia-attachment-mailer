from abc import ABC, abstractmethod


class SendRegistry(ABC):
    """Port that defines how to track which contacts already received an email in a campaign.

    A campaign is identified by the combination of target group, template,
    attachment extra field, and subject — the same parameters a user would
    pick again when restarting an interrupted bulk send. Implementations
    persist this state locally so that resuming the same campaign does not
    re-send emails to contacts that were already reached in a previous,
    interrupted run.
    """

    @abstractmethod
    def get_sent_contact_ids(
        self, group_id: int, template_id: int, field_name: str, subject: str
    ) -> set[int]:
        """Return the IDs of contacts already sent an email in this campaign.

        Args:
            group_id: ID of the target agenda group.
            template_id: ID of the email template used.
            field_name: Name of the extra field holding the attachment URL.
            subject: Email subject line.

        Returns:
            A set of contact IDs. Empty when the campaign has no recorded
            sends yet.
        """
        pass

    @abstractmethod
    def mark_sent(
        self, group_id: int, template_id: int, field_name: str, subject: str, contact_id: int
    ) -> None:
        """Record that a contact successfully received an email in this campaign.

        Implementations must persist this immediately so progress survives
        an interruption of the send process.

        Args:
            group_id: ID of the target agenda group.
            template_id: ID of the email template used.
            field_name: Name of the extra field holding the attachment URL.
            subject: Email subject line.
            contact_id: ID of the contact that was successfully emailed.
        """
        pass

    @abstractmethod
    def clear(self, group_id: int, template_id: int, field_name: str, subject: str) -> None:
        """Forget all recorded sends for this campaign.

        Called once a campaign completes with no pending or errored
        contacts, so a legitimate future re-send to the same group,
        template and field is not blocked.

        Args:
            group_id: ID of the target agenda group.
            template_id: ID of the email template used.
            field_name: Name of the extra field holding the attachment URL.
            subject: Email subject line.
        """
        pass
