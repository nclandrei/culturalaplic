# Calendarul Hipsterului

A cultural events calendar for Bucharest - "Ce faci în weekend?"

## Stack

- **Next.js 16** with App Router
- **Tailwind CSS 4**
- **neobrutalism.dev** components (thick borders, hard shadows)
- **TypeScript**

## Getting Started

```bash
# Install dependencies
pnpm install

# Run development server
pnpm dev

# Build for production
pnpm build
```

## Design

- **Background**: Cream (`#FEF6E4`)
- **Borders/Shadows**: Black (neobrutalism style)
- **Music category**: Teal (`#0EA5E9`)
- **Theatre category**: Pink (`#EC4899`)
- **Culture category**: Mustard (`#EAB308`)

## Features

- Calendar with event indicators (blue dots)
- Today preselected on load
- Event list filtered by selected date
- Category badges
- Spotify match indicator
- Price display (or "Gratis" for free events)
- Mobile responsive layout

## Data

Currently uses sample JSON data in `src/data/sample-events.json`. 

For production, this will read from the scrapers' output in `../data/*.json`.
