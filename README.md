# Automated Social Media Content Pipeline & Engine

An end-to-end Python automation pipeline that dynamically ingests digital news feeds (RSS), utilizes Google Gemini AI & Imagen models for content framing and visual generation, automatically stitches media assets (Reels & Carousels), and publishes them directly to Instagram via the Meta Graph API.

## Architecture Overview

```
+------------------+     +--------------------+     +------------------------+
|   hunter.py      | --> |    database.py     | --> |       editor.py        |
| (RSS Feed Ingest)|     | (SQLite Buffer DB) |     |  (Gemini + Imagen AI)  |
+------------------+     +--------------------+     +------------------------+
                                                                |
                                                                v
+------------------+     +--------------------+     +------------------------+
|  Instagram Feed  | <-- |    publisher.py    | <-- |    GitHub Repository   |
|   / Reels (IG)   |     | (Meta Graph API)   |     |  (Asset Hosting Sync)  |
+------------------+     +--------------------+     +------------------------+

```

## Key Features

* **Automated Content Ingestion (`hunter.py`)**: Continuously monitors designated RSS feeds for relevant news articles and filters content according to keyword parameters.

* **AI-Powered Editorial Processing (`editor.py`)**:

  * **Text Analysis & Structuring**: Leverages Google Gemini models (`gemini-3.6-flash`) to analyze long-form content and convert it into structured JSON slide outlines.

  * **Dynamic Visual Creation**: Uses Imagen 3 (`imagen-3.0-generate-002`) to generate 9:16 background artwork tailored to content mood and theme.

  * **Hybrid Format Generation**:

    * **Carousel Mode**: Custom Pillow canvas rendering with brand styling, typography wrapping, and multi-slide overlay effects.

    * **Reels Mode**: Downloads relevant audio segments (e.g., Al-Qur'an recitations) and compiles images into animated dynamic short videos using `moviepy`.

* **Cloud Asset Staging**: Automatically commits and hosts generated visual assets via GitHub API, generating public raw CDN endpoints for distribution.

* **Autonomous Publishing (`publisher.py`)**:

  * Direct integration with Instagram Graph API v19.0.

  * Handles single video Reels containers and multi-item Carousel containers.

  * Asynchronous background polling to verify media processing completion before final publish execution.

## Tech Stack & Dependencies

* **Language**: Python 3.10+

* **AI Services**: Google GenAI SDK (`google-genai`), Gemini 3.6 Flash, Imagen 3

* **Media Processing**: Pillow (PIL), MoviePy, Requests

* **Database**: SQLite3

* **API Integrations**: Meta Graph API v19.0, GitHub REST API, EveryAyah Audio API

## Project Structure

```
├── main.py            # Main application runner and periodic scheduler loop
├── hunter.py          # News search & ingestion engine
├── editor.py          # AI analysis, image composition & video assembly
├── publisher.py       # Meta Graph API deployment client
├── database.py       # SQLite database operations & status tracking
├── config.py          # Configuration variables and API key management
└── README.md          # System documentation

```

## Configuration & Environment Setup

### 1. Prerequisites

Ensure Python 3.10 or higher is installed along with `ffmpeg` (required for `moviepy` video rendering).

### 2. Environment Variables

Create a `config.py` file or setup environment variables containing the following keys:

```
# API Keys & Auth
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GITHUB_TOKEN = "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN"
GITHUB_REPO = "username/repository-name"

# Meta Graph API Settings
IG_USER_ID = "YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID"
ACCESS_TOKEN = "YOUR_META_LONG_LIVED_ACCESS_TOKEN"

# Design & Canvas Config
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920

```

### 3. Installation

Install the necessary Python packages:

```
pip install requests pillow moviepy google-genai feedparser

```

## Usage

To launch the automated social media agent pipeline manually or on a server (e.g., VPS, AWS EC2):

```
python main.py

```

The system runs continuously, executing a full intake-editor-publish cycle every 2 hours with automatic error recovery and execution logging.

## License & Usage

This system is built as a portfolio project showcasing backend Python automation, media processing, and AI integrations. Feel free to adapt for custom automated social media workflows.