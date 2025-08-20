#!/usr/bin/env python3
"""
Token Hash Generator for Unix Socket Bridge Server

This utility helps generate secure SHA-256 hashed tokens for authentication.
Use this to create secure tokens that can be stored in environment variables.

Usage:
    python3 generate-token-hash.py [token]
    python3 generate-token-hash.py --random
    python3 generate-token-hash.py --interactive

Examples:
    # Generate hash for specific token
    python3 generate-token-hash.py "my-secret-token"
    
    # Generate a secure random token and its hash
    python3 generate-token-hash.py --random
    
    # Interactive mode (token won't be shown in shell history)
    python3 generate-token-hash.py --interactive
"""

import argparse
import hashlib
import secrets
import sys
import getpass
from typing import Tuple

def generate_random_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token"""
    return secrets.token_urlsafe(length)

def hash_token(token: str) -> str:
    """Generate SHA-256 hash of a token"""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def interactive_token_input() -> str:
    """Securely get token from user input without echoing to terminal"""
    try:
        token = getpass.getpass("Enter your secret token (hidden): ")
        if not token.strip():
            print("Error: Token cannot be empty", file=sys.stderr)
            sys.exit(1)
        return token.strip()
    except KeyboardInterrupt:
        print("\nCancelled by user", file=sys.stderr)
        sys.exit(1)

def generate_token_and_hash(token: str = None) -> Tuple[str, str]:
    """Generate or use provided token and return token and its hash"""
    if token is None:
        token = generate_random_token()
    
    token_hash = hash_token(token)
    return token, token_hash

def print_usage_instructions(token: str, token_hash: str):
    """Print usage instructions for the generated token"""
    print("\n" + "="*60)
    print("🔐 SECURE TOKEN GENERATED")
    print("="*60)
    print(f"Token:      {token}")
    print(f"SHA-256:    {token_hash}")
    print("\n📋 SETUP INSTRUCTIONS:")
    print("-"*60)
    print("1. Server Environment Variable:")
    print(f'   export AUTH_TOKEN_HASH="{token_hash}"')
    print("\n2. n8n Credential Configuration:")
    print(f'   - Use token: {token}')
    print("   - Configure 'HTTP Header Auth' credential in n8n")
    print("   - Set 'Value' field to the token above")
    print("   - ✅ Tokens are hashed before transmission (secure)")
    print("\n3. Security Features:")
    print("   - Plain text tokens never sent over socket")
    print("   - SHA-256 hashing prevents token interception")
    print("   - Only credential-based authentication supported")
    print("\n🛡️  SECURITY NOTES:")
    print("-"*60)
    print("• Store the TOKEN securely (password manager, secrets vault)")
    print("• Use AUTH_TOKEN_HASH environment variable on server")
    print("• Never commit tokens to version control")
    print("• Regenerate tokens periodically")
    print("• The server only stores the hash, never the plain token")
    print("="*60)

def main():
    parser = argparse.ArgumentParser(
        description="Generate secure hashed tokens for Unix Socket Bridge authentication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        'token', 
        nargs='?', 
        help='Token to hash (if not provided, will generate random token)'
    )
    group.add_argument(
        '--random', 
        action='store_true',
        help='Generate a cryptographically secure random token'
    )
    group.add_argument(
        '--interactive', 
        action='store_true',
        help='Interactively input token (hidden from terminal)'
    )
    
    parser.add_argument(
        '--hash-only',
        action='store_true',
        help='Only output the hash (useful for scripting)'
    )
    
    parser.add_argument(
        '--validate',
        metavar='HASH',
        help='Validate a token against an existing hash'
    )

    args = parser.parse_args()
    
    # Validation mode
    if args.validate:
        if args.interactive:
            token = interactive_token_input()
        elif args.token:
            token = args.token
        else:
            print("Error: Token required for validation", file=sys.stderr)
            sys.exit(1)
        
        computed_hash = hash_token(token)
        if computed_hash == args.validate:
            print("✅ Token is valid for the provided hash")
            sys.exit(0)
        else:
            print("❌ Token does not match the provided hash")
            sys.exit(1)
    
    # Generation mode
    if args.interactive:
        token = interactive_token_input()
    elif args.random or args.token is None:
        token = None  # Will generate random
    else:
        token = args.token

    token, token_hash = generate_token_and_hash(token)
    
    if args.hash_only:
        print(token_hash)
    else:
        print_usage_instructions(token, token_hash)

if __name__ == "__main__":
    main()