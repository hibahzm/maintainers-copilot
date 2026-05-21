from fastapi import status

from app.infra.exceptions import DomainError, NotFoundError, PermissionDenied, ToolFailure
from app.main import _domain_error_code, _domain_status_code


def test_domain_error_status_mapping():
    assert _domain_status_code(NotFoundError("missing")) == status.HTTP_404_NOT_FOUND
    assert _domain_status_code(PermissionDenied("blocked")) == status.HTTP_403_FORBIDDEN
    assert _domain_status_code(ToolFailure("down")) == status.HTTP_503_SERVICE_UNAVAILABLE
    assert _domain_status_code(DomainError("bad")) == status.HTTP_400_BAD_REQUEST


def test_domain_error_code_mapping():
    assert _domain_error_code(NotFoundError("missing")) == "not_found"
    assert _domain_error_code(PermissionDenied("blocked")) == "permission_denied"
    assert _domain_error_code(ToolFailure("down")) == "tool_failure"
    assert _domain_error_code(DomainError("bad")) == "domain_error"
