"""
OAuth Service for Google, GitHub, and Apple Sign-In
"""
from typing import Optional, Dict, Any
import httpx
from fastapi import HTTPException
from app.core.config import get_settings

settings = get_settings()

# OAuth Provider Configurations
OAUTH_PROVIDERS = {
    "google": {
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "user_info_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scope": "openid email profile",
    },
    "github": {
        "client_id_env": "GITHUB_CLIENT_ID",
        "client_secret_env": "GITHUB_CLIENT_SECRET",
        "auth_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "user_info_url": "https://api.github.com/user",
        "scope": "user:email",
    },
    "apple": {
        "client_id_env": "APPLE_CLIENT_ID",
        "client_secret_env": "APPLE_CLIENT_SECRET",
        "auth_url": "https://appleid.apple.com/auth/authorize",
        "token_url": "https://appleid.apple.com/auth/token",
        "user_info_url": None,  # Apple uses ID token
        "scope": "name email",
    },
}


class OAuthService:
    """Service for handling OAuth authentication"""
    
    def is_provider_configured(self, provider: str) -> bool:
        """Check if OAuth provider is configured"""
        if provider not in OAUTH_PROVIDERS:
            return False
        
        # Use settings instead of os.getenv
        if provider == "google":
            return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
        elif provider == "github":
            return bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET)
        elif provider == "apple":
            return bool(settings.APPLE_CLIENT_ID and settings.APPLE_TEAM_ID)
        
        return False
    
    async def exchange_code_for_token(
        self, provider: str, code: str, redirect_uri: str
    ) -> Optional[str]:
        """Exchange authorization code for access token"""
        if provider not in OAUTH_PROVIDERS:
            return None
        
        cfg = OAUTH_PROVIDERS[provider]
        
        # Get credentials from settings
        if provider == "google":
            client_id = settings.GOOGLE_CLIENT_ID
            client_secret = settings.GOOGLE_CLIENT_SECRET
        elif provider == "github":
            client_id = settings.GITHUB_CLIENT_ID
            client_secret = settings.GITHUB_CLIENT_SECRET
        elif provider == "apple":
            client_id = settings.APPLE_CLIENT_ID
            client_secret = settings.APPLE_PRIVATE_KEY
        else:
            return None
        
        if not client_id or not client_secret:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                data = {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                }
                
                headers = {"Accept": "application/json"}
                
                response = await client.post(
                    cfg["token_url"],
                    data=data,
                    headers=headers
                )
                response.raise_for_status()
                token_data = response.json()
                
                return token_data.get("access_token")
        except Exception as e:
            print(f"Error exchanging code for token ({provider}): {e}")
            return None
    
    async def get_user_info(
        self, provider: str, access_token: str
    ) -> Optional[Dict[str, Any]]:
        """Get user info from OAuth provider"""
        if provider == "google":
            return await self._get_google_user_info(access_token)
        elif provider == "github":
            return await self._get_github_user_info(access_token)
        elif provider == "apple":
            return await self._get_apple_user_info(access_token)
        return None
    
    async def _get_google_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user info from Google"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://www.googleapis.com/oauth2/v2/userinfo',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    'provider_id': data['id'],
                    # an address Google has not verified proves nothing about who owns it: treat it as no email at all
                    'email': data.get('email') if data.get('verified_email') is True else None,
                    'name': data.get('name'),
                    'picture': data.get('picture'),
                }
        except Exception as e:
            print(f"Error fetching Google user info: {e}")
            return None
    
    async def _get_github_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user info from GitHub"""
        try:
            async with httpx.AsyncClient() as client:
                # Get user profile
                user_response = await client.get(
                    'https://api.github.com/user',
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Accept': 'application/vnd.github.v3+json'
                    }
                )
                user_response.raise_for_status()
                user_data = user_response.json()
                
                # Get user emails
                email_response = await client.get(
                    'https://api.github.com/user/emails',
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Accept': 'application/vnd.github.v3+json'
                    }
                )
                email_response.raise_for_status()
                emails = email_response.json()
                
                # Only the primary address, and only when GitHub has verified it. The old fallback to "the first address in the list" could
                # hand us an address the person never proved they own.
                primary_email = next(
                    (email['email'] for email in emails if email.get('primary') and email.get('verified') is True),
                    None
                )
                
                return {
                    'provider_id': str(user_data['id']),
                    'email': primary_email,
                    'name': user_data.get('name') or user_data['login'],
                    'picture': user_data.get('avatar_url'),
                }
        except Exception as e:
            print(f"Error fetching GitHub user info: {e}")
            return None
    
    async def _get_apple_user_info(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Get user info from Apple ID token"""
        try:
            import jwt
            from jwt import PyJWKClient
            
            # Get Apple's public keys
            jwks_client = PyJWKClient('https://appleid.apple.com/auth/keys')
            signing_key = jwks_client.get_signing_key_from_jwt(id_token)
            
            # Decode and verify the token
            decoded = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=['RS256'],
                audience=settings.APPLE_CLIENT_ID,
                issuer='https://appleid.apple.com'
            )
            
            return {
                'provider_id': decoded['sub'],
                'email': decoded.get('email') if decoded.get('email_verified') in (True, 'true') else None,
                'name': None,  # Apple doesn't always provide name
                'picture': None,
            }
        except Exception as e:
            print(f"Error decoding Apple ID token: {e}")
            return None


oauth_service = OAuthService()
