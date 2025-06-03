# Static Directory

This directory is used by Streamlit's static file serving feature to provide direct URL access to files.

Files in this directory can be accessed via URLs like:
`http://localhost:8501/app/static/filename.ext`

## Contents

This directory typically contains:
- JSON result files from troubleshooting workflows
- Other static assets needed by the application

## Usage

Files in this directory are meant to be accessed via direct URLs, which allows for:
1. Sharing links to result data
2. Integration with other systems
3. Direct downloads without requiring Streamlit download buttons

## Configuration

Static file serving is enabled in `.streamlit/config.toml` with:
```
[server]
enableStaticServing = true
```
