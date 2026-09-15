# Athlete Meals Folder

Place your meal or food photos here (e.g. `lunch.jpg`, `dinner.png`, `breakfast.jpeg`).

### How to analyze your meals:
1. **In the Terminal Chat (Option 9 in `main.py`):**
   - Simply type `meal` (the coach will automatically analyze your newest photo in this folder).
   - Or type `meal lunch.jpg` or `meal data/meals/lunch.jpg`.
2. **Via Web API (FastAPI):**
   - Open `http://127.0.0.1:8000/docs` in your browser.
   - Go to `POST /chat/vision-meal` and upload any meal image directly!
