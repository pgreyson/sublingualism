# Security & Credentials

## Overview
All credentials stored encrypted with single master password (SSO).

## Required Credentials
- GitHub account access
- AWS account access  
- Social media accounts (Instagram, etc.) - *pending strategy*
- Vimeo account access - *for video management*

## Setup Process
1. Agent requests master password from user
2. Initialize encrypted keystore
3. Add credentials as provided
4. Never commit credentials or master password

## Access Protocol
1. Read this file for credential list
2. Request master password once per session
3. Access specific credentials as needed
4. Log credential usage in SESSION_LOG.md

## Security Rules
- NEVER log passwords or keys
- NEVER commit credentials to git
- ALWAYS use environment variables in code
- ALWAYS confirm before using production credentials