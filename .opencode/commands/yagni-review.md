---
description: Review the current diff specifically for overengineering and unnecessary code.
agent: router-local-plan
---

Load the `yagni` skill and review the current Git diff only for unnecessary complexity.

Flag:

- code that can be deleted
- existing functionality that could be reused
- standard/native capability that replaces custom code
- speculative abstractions
- future requirements implemented prematurely
- unnecessarily large changes

Do not perform a correctness or security review in this command.
