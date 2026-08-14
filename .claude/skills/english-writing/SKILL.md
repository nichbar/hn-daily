---
name: english-writing
description: English writing guide for high-quality daily digests and articles on technology, business, policy, science, and society.
---

# English Writing Guide

This guide is for generating high-quality, modern English daily digests and related articles.

Core principles: **Simple**, **Human**, **Clear**.

## 1. Voice and Tone

- **Warm and relaxed**: Write like a thoughtful person, not a press release or a model reciting bullet points.
- **Crisp and clear**: Lead with what happened and why it matters. Cut filler.
- **Helpful**: Assume a curious general reader, not a specialist.

## 1.1 Priority Rules

- **Must**: User requirements, project schemas, fixed titles, naming rules, and anything marked “must / do not / never” here.
- **Should**: Default style and structure advice. Yield if a specific task needs something else.
- **May**: Optional polish. Never trade facts or required format for flourish.

Conflict order: explicit user request > project convention > current task > this skill. `Must` always wins.

## 2. General Writing Tips

- Write the way you would explain the story to a smart friend.
- Avoid empty evaluatives (“noteworthy”, “it is important to note”, “in today’s rapidly evolving landscape”).
- One idea per sentence. Prefer short sentences. Cut “very”, “clearly”, “essentially”.
- Put the news first. Context second.
- In a daily digest, stay in third person. Do not force “you”.
- Use active voice. Name the actor.
- Avoid absolute claims (“always”, “never”, “proves”) unless the source does, and even then hedge if the evidence is thin.

## 3. Structure and Formatting

- Headings should say what the section is about. Use the project’s fixed headings when a task defines them.
- Keep paragraphs short (about 3–5 sentences).
- Bold key terms sparingly.
- Do not use emoji.

## 4. Grammar and Usage

- American English spelling, unless a proper name requires otherwise.
- Keep product, company, and project names in their official form.
- On first mention of jargon, add a short plain-English gloss in the same sentence.
- Use straight or curly quotes consistently; prefer straight quotes in Markdown source.
- Numbers: use numerals for 10 and above; write out one through nine unless they are scores, versions, or measurements.

## 5. Daily Newsletter Writing

### 5.1 Titles

If the task fixes the title format, use it exactly. For this project the English title is:

`"Hacker News Daily (YYYY-MM-DD)"`

### 5.2 Opening and closing

- Open with `# Today's Highlights`.
- Start from the highest-`points` story, then give a short tour of the day’s themes. Never print points, scores, or comment counts.
- Close with `# Closing`.
- End with a brief wrap-up and a standing sign-off such as “See you next time.”

### 5.3 Sections

Use only the topic headings that appear in the input:

- `technology` → `## Tech and Products`
- `business` → `## Business and Platforms`
- `policy` → `## Policy and Governance`
- `science` → `## Science and Research`
- `society` → `## Society and Culture`

Do not invent extra top-level sections. Do not use `# Article summaries and comment reactions`.

### 5.4 Entries

- Each story gets a `###` heading.
- 3–6 sentences of summary, then a short “Note:” paragraph for interpretation and HN reaction.
- Embed the original link as anchor text on a product, company, paper, or article name. Never add a standalone “Read more” or “Original link” line.
- If `hn_url` is present, end the entry with `Discussion: [Hacker News thread](url)`.
- Fold `why_it_matters` into the first one or two sentences.
- Keep original claims, the digest writer’s reading, and HN reactions visibly distinct.
- Attribute HN views at least once per entry, and rotate the phrasing (“top comments argued…”, “several readers pushed back…”, “the thread’s main split was…”).
- Do not treat HN comments as established fact.

### 5.5 Front matter

```yaml
---
title: "Hacker News Daily (YYYY-MM-DD)"
date: "YYYY-MM-DD"
summary: "One or two sentences on the day’s through-line."
tags: ["Company", "Topic"]
editor: "model-id"
translationKey: "YYYY-MM-DD"
---
```

- `date` must equal the target date.
- `tags` come from the content. Prefer company and project names. Drop `Hacker News`.
- `editor` is the model ID actually used (`PI_MODEL`, else the workflow default).
- `translationKey` must match the Chinese edition so Hugo can pair them.

### 5.6 Format checklist

- [ ] Title is `"Hacker News Daily (YYYY-MM-DD)"` in quotes
- [ ] Front matter includes `date`, `summary`, `tags`, `editor`, `translationKey`
- [ ] Structure is Highlights → topic sections → Closing
- [ ] No points, scores, or comment counts
- [ ] Links are inline anchor text
- [ ] Each entry attributes HN discussion at least once
- [ ] HN link, if any, is the last line of the entry
- [ ] English is written, not a sentence-by-sentence calque of the Chinese edition
- [ ] A general reader can follow the piece without a CS background
