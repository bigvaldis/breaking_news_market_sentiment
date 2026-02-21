# Deploy to GitHub

The project is built and ready. Follow these steps to push it to your GitHub.

## 1. Authenticate with GitHub (one-time)

```bash
gh auth login
```

Choose:
- **GitHub.com**
- **HTTPS** (or SSH if you prefer)
- **Login with a web browser** (easiest)

## 2. Create repo and push

From the project directory:

```bash
cd "/Users/shaonbiswas/Documents/Python Projects/Breaking News and Sentiment Analysis"

# Create a new public repo and push (replace REPO_NAME if desired)
gh repo create breaking-news-sentiment-analysis --public --source=. --remote=origin --push
```

Or, if you prefer to create the repo manually on GitHub first:

```bash
# Add your repo as remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/breaking-news-sentiment-analysis.git

# Push
git push -u origin main
```

## 3. Verify

Visit `https://github.com/YOUR_USERNAME/breaking-news-sentiment-analysis` to see your deployed project.
