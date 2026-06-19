---
name: amr-commit-no-claude
description: "Préférence commits — NE PAS mentionner Claude (pas de trailer Co-Authored-By, pas de 'Generated with Claude')"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 6da325ad-d900-4dba-9896-6d398a31000d
---

L'utilisateur ne veut **AUCUNE mention de Claude** dans les commits/PR de ce projet (openamr-robot) :
pas de trailer `Co-Authored-By: Claude ...`, pas de « Generated with Claude Code ».

**Why:** demande explicite (2026-06-19, « je ne veux pas que claude soit mentionné »).
**How to apply:** rédiger les messages de commit sans aucun trailer d'attribution Claude. L'auteur git
reste l'utilisateur (SHuttooo <matthieuvinet04@gmail.com>). Idem pour les descriptions de PR.

Workflow git du repo : commits **directs sur `master`** (pas de branche), puis `git push origin master`.
Cf [[amr-pi-ros-commands]].
