---
description: Task list prompt with loop
title: List title
tasks(list): List of task items
show_priority(bool): Show priority levels
---
# {title}

{#for task, index in tasks}
{index}. {task.name}{#if show_priority} [{task.priority}]{/if}
   - {task.description}
{/for}

{#if not tasks}
No tasks to display.
{/if}
