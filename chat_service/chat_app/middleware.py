from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async


class AnonymousUser:
    """Simple anonymous user for WebSocket authentication"""
    def __init__(self):
        self.id = None
        self.username = 'Anonymous'
        self.is_authenticated = False
        self.is_anonymous = True


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware for JWT authentication in WebSocket connections.
    Extracts token from Authorization header and validates it using existing check_user function.
    """

    async def __call__(self, scope, receive, send):
        # Only process WebSocket connections
        if scope["type"] == "websocket":
            # Extract token from Authorization header
            headers = dict(scope["headers"])
            print(f"DEBUG: Available headers: {headers}")

            auth_header = headers.get(b"authorization", b"").decode()
            print(f"DEBUG: Auth header: {auth_header}")

            token = None
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                print(f"DEBUG: Extracted token with Bearer: {token[:20]}...")
            elif auth_header and not auth_header.startswith("Bearer"):
                # Handle direct token without "Bearer " prefix
                token = auth_header
                print(f"DEBUG: Extracted direct token: {token[:20]}...")

            if token:
                # Validate token using existing check_user function
                user_data = await self.authenticate_token(token)
                print(f"DEBUG: User data from auth: {user_data}")
                if user_data:
                    # Create a simple user object with the data we need
                    scope["user"] = SimpleUser(user_data)
                    scope["user_data"] = user_data
                else:
                    scope["user"] = AnonymousUser()
            else:
                print("DEBUG: No token found, setting anonymous user")
                scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def authenticate_token(self, token):
        """
        Authenticate token using the existing check_user function from views
        """
        from .views import check_user
        return check_user(token)


class SimpleUser:
    """
    Simple user class to hold user data for WebSocket authentication
    """
    def __init__(self, user_data):
        self.id = user_data.get('id')
        self.username = user_data.get('username')
        self.email = user_data.get('email')
        self.is_authenticated = True
        self.is_anonymous = False

    def __str__(self):
        return f"User({self.username})"