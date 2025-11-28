# Overview

This is a Discord bot-based service monitoring application that allows users to track the uptime and status of their web services. The system combines a Flask web dashboard for management with a Discord bot for notifications and monitoring. Users can add services to monitor, receive status updates through Discord, and manage their monitored services through a web interface with Discord OAuth authentication.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Application Structure

**Hybrid Flask + Discord Bot Architecture**: The application runs two concurrent services - a Flask web server for the dashboard interface and a Discord bot for real-time monitoring and notifications. The bot is started in a background thread during Flask application initialization.

**Rationale**: This architecture enables both web-based management (user-friendly for configuration) and Discord-native interactions (convenient for real-time alerts where users already spend time). The background threading approach allows both services to run in a single deployment.

**Trade-off**: Running both services in one process creates coupling and potential resource contention, but simplifies deployment and state sharing between components.

## Authentication & Authorization

**Discord OAuth 2.0**: Uses Discord's OAuth flow for user authentication on the web dashboard. Session-based authentication stores user information after successful OAuth callback.

**Rationale**: Since the application is Discord-centric, using Discord as the identity provider eliminates the need for separate user registration and leverages existing Discord accounts.

**Implementation**: The `require_login` decorator protects dashboard routes, redirecting unauthenticated users to the OAuth flow.

## Data Storage

**Supabase (PostgreSQL)**: Uses Supabase as the backend database with a services table structure that includes owner_id, guild_id, service name, URL, status, and timestamps.

**Schema Design**: 
- Services are linked to Discord users via `owner_id` (string representation of Discord user ID)
- Guild association via `guild_id` enables server-specific service monitoring
- Unique constraint on (owner_id, name) prevents duplicate service names per user
- Indexes on owner_id and guild_id optimize common query patterns

**Rationale**: Supabase provides a managed PostgreSQL instance with a Python client library, reducing operational overhead. The direct SQL client approach (vs ORM) keeps the codebase simple for this straightforward data model.

## Discord Bot Architecture

**discord.py with Slash Commands**: Implements Discord bot using the discord.py library with application commands (slash commands) for user interaction.

**Command Structure**:
- `/add_service` - Adds a new service to monitor
- `/list_services` - Lists monitored services
- Background task loop for periodic health checks

**Rationale**: Slash commands provide a native Discord UX with autocomplete and validation. The tasks extension enables scheduled monitoring without external cron services.

**Intents Configuration**: Enables message_content intent for potential future text-based commands while primarily using slash commands.

## Service Monitoring

**Periodic Health Check Task**: Uses discord.py's tasks extension to create a background loop (`check_services`) that periodically checks service availability.

**Rationale**: In-process scheduled tasks eliminate dependency on external schedulers. The approach is suitable for moderate monitoring frequencies (likely minute-level checks based on the architecture).

**Consideration**: This design means monitoring only occurs while the bot is running. For production use, this creates a single point of failure.

## Web Dashboard

**Flask with Jinja2 Templates**: Traditional server-side rendered web application using Flask and Jinja2 templates for the dashboard interface.

**Styling**: Custom CSS with Discord-inspired design language (dark theme, Discord color palette: #5865f2 for primary, #57f287 for success, #ed4245 for errors).

**Rationale**: Server-side rendering keeps the frontend simple without requiring a separate JavaScript framework. The Discord-themed UI creates visual consistency with the bot interface.

# External Dependencies

## Discord API

**Purpose**: User authentication (OAuth 2.0) and bot functionality (commands, notifications)

**Endpoints Used**:
- OAuth authorize: `https://discord.com/api/oauth2/authorize`
- OAuth token exchange: `https://discord.com/api/oauth2/token`
- Discord API base: `https://discord.com/api`

**Authentication**: Bot token for bot API calls, OAuth flow for user authentication

## Supabase

**Purpose**: Primary database for storing service configurations and monitoring data

**Configuration**: Requires SUPABASE_URL and SUPABASE_KEY environment variables

**Client Library**: supabase-py v2.3.4

**Database Schema**: Services table with owner tracking, guild association, and status management

## Python Libraries

**Core Framework**: Flask 3.0.0 for web server

**Discord Integration**: discord.py 2.3.2 for bot functionality

**HTTP Requests**: 
- `requests` library for synchronous HTTP (Flask routes, service health checks)
- `aiohttp` for async HTTP within Discord bot context

**Configuration Management**: python-dotenv for environment variable loading

## Environment Configuration

**Required Environment Variables**:
- `DISCORD_TOKEN` - Bot authentication token
- `DISCORD_CLIENT_ID` - OAuth application ID
- `DISCORD_CLIENT_SECRET` - OAuth application secret
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase API key
- `SECRET_KEY` - Flask session encryption key (defaults to "dev-key-change-in-prod")

**Security Note**: All sensitive credentials are externalized through environment variables, loaded via dotenv for development convenience.