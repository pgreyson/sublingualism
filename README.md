# Sublingualism

Art website project. Agent assists with development, curation, and promotion.

## Quick Context
- **What**: Personal art website exploring "sublingualism" (art beneath language, absorbed like medicine under tongue)
- **Who**: AI agent helping build/deploy/market
- **Where**: GitHub repo → AWS hosting
- **Security**: Encrypted credentials (see SECURITY.md)

## Agent Tasks
1. Build website
2. Curate content  
3. Advise on promotion channels
4. Manage social media accounts (Instagram, etc.)
5. Manage deployments

## Project Status
- [x] Set up credentials (.env)
- [x] Configure GitHub repository
- [x] Connect AWS account (Route 53, Amplify)
- [x] Deploy website to sublingualism.com
- [x] Create video segmentation tools
- [ ] Develop promotion strategy
- [ ] Set up social media accounts (post-strategy)

## Repository Structure
- `/website/` - Website files (deployed to sublingualism.com)
  - `index.html` - Homepage with artist statement
  - `works.html` - Video gallery (20 works)
- `/video-processing/` - Video analysis and segmentation tools
  - `/tools/` - Python scripts for processing
  - Generated EDLs, playlists, and segment data
- `/setup/` - AWS configuration files
- `/andc/` - Additional project files

## For Returning Agents
1. Read this file first
2. Check SECURITY.md for credential access
3. Review SESSION_LOG.md for recent work
4. Continue from Project Status above

## Key Files
- `ARTIST_STATEMENT.md` - Sublingualism concept
- `SECURITY.md` - Credential management
- `SESSION_LOG.md` - Work history