---
description: Greeting prompt with conditional formality
formal(bool): Use formal greeting style
name: User's name
title: User's title (for formal greetings)
---
Hello{#if formal}, {title}{/if} {name}!

{#if formal}
We hope this message finds you well. Thank you for your continued support.
{#else}
How's it going? Hope you're having a great day!
{/if}
