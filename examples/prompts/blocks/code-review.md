---
description: Code review prompt with conditional checklist
language: Programming language
code: Code to review
include_checklist(bool): Include review checklist
checklist(list): List of review items
tone: Review tone (friendly, strict, neutral)
---
Please review the following {language} code:

```{language}
{code}
```

{#if tone == "friendly"}
Feel free to provide constructive feedback in a supportive manner.
{#else}
{#if tone == "strict"}
Please be thorough and point out all potential issues.
{#else}
Provide balanced and objective feedback.
{/if}
{/if}

{#if include_checklist}
## Review Checklist

{#for item in checklist}
- [ ] **{item.category}**: {item.description}
{/for}
{/if}

Please provide your feedback below:
