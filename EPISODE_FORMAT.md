# Episode file format

One file per episode in `episodes/`, named `YYYY-MM-DD.md` (the date it airs, South African time).

```markdown
---
title: The Southern Africa Brief: Wednesday 26 November 2026
date: 2026-11-26
type: daily
status: publish
description: Two sentences describing the episode for podcast apps.
---
## Script
**[OPEN]**
Good morning. This is The Southern Africa Brief for Wednesday, the 26th of November.

**[STORY 1]**
...

## Sources
- [Page title](https://example.gov.za/page)
```

Rules the build checks:

- `date` must match the file name.
- `title`, `description` and a `## Script` section are required.
- The spoken script must be 120 to 2,200 words.
- `type` is `daily` (Tuesday to Friday) or `monday`.
- `status: publish` goes out automatically. `status: draft` is kept back. If `auto_publish` is `false` in `podcast.json`, only `status: approved` goes out.

What is read aloud: everything under `## Script`, except lines that are only a bracketed label such as `**[STORY 1]**`. Bold marks and links are removed before the voice reads it.
