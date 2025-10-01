# Team Git Playbook

This guide explains how our team should use Git branches while working on the project.

---

## First Pulling (first time on a machine)

1. **Clone the repo**
   ```bash
   git clone <repo-url>
   cd betboard
   ```

2. **Set your Git identity (one-time)**
   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```

3. **Make sure you’re on `main` and up to date**
   ```bash
   git checkout main
   git pull origin main
   ```

4. **Create your personal feature branch**
   ```bash
   git checkout -b feat/<area>-<short-task>
   git push -u origin feat/<area>-<short-task>
   ```
   _Examples:_ `feat/ios-navigation`, `feat/scraper-boxscores`, `feat/ml-baseline`, `feat/functions-game-endpoints`

---

## Every Time You Do Work

1. **Sync `main`**
   ```bash
   git checkout main
   git pull origin main
   ```

2. **Switch to your branch (or create one)**
   ```bash
   git checkout feat/<your-branch>
   ```

3. **Rebase your branch on latest `main` (preferred)**
   ```bash
   git fetch origin
   git rebase origin/main
   # if conflicts: fix → git add <file> → git rebase --continue
   ```
   _Alternative (simpler, messier history):_
   ```bash
   git merge origin/main
   ```

4. **Do work → stage → commit**
   ```bash
   git add .
   git commit -m "feat(area): short message"
   ```

---

## When You’re Pushing

- **First push of a new branch**
  ```bash
  git push -u origin feat/<your-branch>
  ```

- **Regular push**
  ```bash
  git push
  ```

- **After a rebase**
  ```bash
  git push --force-with-lease
  ```

---

## When You’re Ready to Share/Merge

- **Option A: push straight to `main` (for now, allowed)**
  ```bash
  git checkout main
  git pull origin main
  git merge --no-ff feat/<your-branch>
  git push
  ```

- **Option B: open a Pull Request**
  1. Push your branch
  2. On GitHub: “Compare & pull request”
  3. Add a description, tag teammates if needed
  4. Merge when ready

- **Cleanup after merge**
  ```bash
  git branch -d feat/<your-branch>
  git push origin --delete feat/<your-branch>
  ```

---

## Other Useful Git Commands

- **See branches**
  ```bash
  git branch      # local
  git branch -r   # remote
  ```

- **Rename branch**
  ```bash
  git branch -m feat/<better-name>
  git push origin -u feat/<better-name>
  git push origin --delete <old-name>
  ```

- **Stash work in progress**
  ```bash
  git stash
  git checkout main
  # later…
  git checkout feat/<your-branch>
  git stash pop
  ```

- **Undo last commit (keep changes staged)**
  ```bash
  git reset --soft HEAD~1
  ```

- **Drop local changes**
  ```bash
  git restore path/to/file
  ```

---

## Branch Naming

- `feat/<area>-<thing>` — new work  
- `fix/<area>-<bug>` — bug fixes  
- `chore/<area>-<task>` — non-feature tasks  

_Examples:_  
- `feat/ios-auth`  
- `fix/functions-timezone`  
- `chore/ml-ci`  

---

## Golden Rules (TL;DR)

- Work on your **own branch**.  
- Keep `main` updated, and **rebase or merge before pushing**.  
- Commit small, descriptive changes.  
- Use PRs when you want visibility or feedback.  

---
