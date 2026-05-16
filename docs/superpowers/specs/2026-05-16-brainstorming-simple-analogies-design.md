# Brainstorming Communication Style — Simple Analogies Design

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** During brainstorming sessions, Claude explains technical concepts using simple everyday analogies rather than jargon, matching the needs of a PM audience.

**Architecture:** Two changes in two places — a communication style section added to the brainstorming skill file (immediate effect), and a feedback memory entry (durable across plugin updates). No code changes, no tests needed.

**Tech Stack:** Plain text edits to SKILL.md and a new memory file.

---

## What Changes

### 1. Brainstorming skill file

Add a "Communication Style" section to `SKILL.md` in the brainstorming skill directory. The section instructs Claude to:

- Explain technical decisions through simple everyday analogies (cooking, building, travel, etc.)
- Avoid technical jargon in conversational text
- Describe behaviour and outcomes, not implementation details
- Target a PM with some CS/UX background — can reason about tradeoffs, does not need to evaluate code

This section goes near the top of the skill, before the process steps, so it applies throughout the entire brainstorming session.

### 2. Feedback memory entry

Create a feedback memory at the standard memory path. Same content: during brainstorming sessions, use simple everyday analogies. This survives plugin updates and carries into all future sessions automatically.

---

## What Does NOT Change

- The brainstorming process itself (checklist, flow, gates) is unchanged
- Outside of brainstorming sessions, existing communication style memory applies
- No changes to any other skill files
