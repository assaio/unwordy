---
description: A commit message for a small rename, written as the text that goes to git.
max_turns: 6
allowed_tools: [Skill]
---
Write the commit message for this change, exactly as I would pass it to git and nothing else: I renamed getUser to fetchUser in user.js and updated the three call sites in api.js, because the old name suggested a synchronous lookup and it hits the network.
