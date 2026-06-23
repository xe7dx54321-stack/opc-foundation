# Document Extraction Foundation

## Overview

The Document Extraction Foundation provides a **universal public document extraction** infrastructure.

## Supported Document Types

| Type | Extension | Description |
|------|-----------|-------------|
| PDF | .pdf | Portable Document Format |
| HTML | .html, .htm | HyperText Markup Language |
| Text | .txt | Plain text files |
| Markdown | .md, .markdown | Markdown documents |

## Key Features

1. **Local Document Processing**
   - Reads local files only
   - No remote downloads

2. **Text Extraction**
   - Extracts text content
   - Computes statistics

3. **Quality Assessment**
   - High: >5000 chars
   - Medium: 1000-5000 chars
   - Low: <1000 chars

## Architecture

```
┌─────────────────┐
│ DocumentArchiver │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Extractors │
    ├──────────┤
    │ PDF      │
    │ HTML     │
    │ Text     │
    │ Markdown │
    └──────────┘
```

## Disclaimer

> This module provides infrastructure only.
> Business logic remains with the consuming system.
