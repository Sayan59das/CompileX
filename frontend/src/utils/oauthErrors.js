// What to tell the player when "Sign in with Google / GitHub / Apple" comes back with an error code from the server.
const MESSAGES = {
  no_code: 'Authorization code not received',
  token_exchange_failed: 'Failed to exchange authorization code',
  no_email: 'Your account has no verified email address, so we cannot sign you in with it. Verify the email with the provider, or sign up with a username and password.',
  email_in_use: 'An account with this email already exists. Sign in with your username and password instead.',
  invalid_state: 'That sign-in attempt expired or did not start on this browser. Please try again.',
  google_not_configured: 'Google Sign-In is not available at the moment. Please use username/password to login.',
  github_not_configured: 'GitHub Sign-In is not available at the moment. Please use username/password to login.',
  apple_not_configured: 'Apple Sign-In is not available at the moment. Please use username/password to login.',
}

export function oauthErrorMessage(code) {
  return MESSAGES[code] || `OAuth error: ${code}`
}
