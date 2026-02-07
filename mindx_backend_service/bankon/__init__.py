# bankon: "I do not understand" — fallback/help when the system or user is confused.
# Exposes routes and static content for clarification and next steps.

from mindx_backend_service.bankon.routes import router as bankon_router

__all__ = ["bankon_router"]
