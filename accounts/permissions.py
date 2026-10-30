from rest_framework.permissions import BasePermission


def _logged_in(request):
    return bool(request.user and request.user.is_authenticated)


class IsAdmin(BasePermission):
    """Only Admin (or superuser)."""
    message = "Only admins can do this."

    def has_permission(self, request, view):
        return _logged_in(request) and request.user.is_helpdesk_admin


class IsSupportStaff(BasePermission):
    """Only Support Staff."""
    message = "Only support staff can do this."

    def has_permission(self, request, view):
        return _logged_in(request) and request.user.is_support_staff


class IsAdminOrSupport(BasePermission):
    """Admin or Support Staff (the 'staff' side of the helpdesk)."""
    message = "Only admin or support staff can do this."

    def has_permission(self, request, view):
        return _logged_in(request) and (
            request.user.is_helpdesk_admin or request.user.is_support_staff
        )


class IsCustomer(BasePermission):
    """Only End User / Customer."""
    message = "Only customers can do this."

    def has_permission(self, request, view):
        return _logged_in(request) and request.user.is_customer


class IsTicketParticipant(BasePermission):
    """
    Object-level rule for a Ticket:
      - Admin: full access
      - Support Staff: only tickets assigned to them
      - Customer: only tickets they created
    """
    message = "You do not have access to this ticket."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_helpdesk_admin:
            return True
        if user.is_support_staff:
            return obj.assigned_to_id == user.id
        return obj.created_by_id == user.id
