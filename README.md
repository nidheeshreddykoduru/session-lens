# Session Lens

Session Lens records what real users do on your website — every click, scroll, and keystroke — and lets you watch it back like a video. You paste one script tag into any webpage, and sessions start appearing in your dashboard automatically. No third-party services, no data leaving your server, no monthly fees. You run it yourself.

---

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000`.

---

## Create an account

1. Go to `http://localhost:5000/login`
2. Click the **Create Account** tab
3. Pick a username and password — that's it

---

## Create a project

A project represents one website or app you want to track.

1. Log in and go to your dashboard
2. Type a name in the **New Project** box and press Create
3. Your project appears in the list

---

## Get your snippet

1. Open a project from the dashboard
2. Click **Get Snippet**
3. Copy the `<script>` tag shown on the page

---

## Paste the snippet into any page

Open the HTML file you want to track. Paste the script tag anywhere inside the `<body>` tag — the bottom works fine:

```html
  ...your page content...

  <script>
    (function() { /* Session Lens snippet */ })();
  </script>
</body>
```

Save the file, open it in a browser, and click around. Within 5 seconds your session appears in the dashboard.

---

## Watch a recording

1. Open your project from the dashboard
2. Click any session row
3. The replay loads — press play and watch exactly what the user did

---

## What the ⚠ badge means

A session marked with ⚠ means a JavaScript error occurred during that visit. Useful for catching crashes you didn't know about. *(Coming soon.)*

---

## Tech stack

| Piece | What it does |
|---|---|
| Python + Flask | Runs the server, handles routes, saves data |
| rrweb | Records DOM changes, clicks, and mouse movement in the browser |
| Vanilla JS | Powers the dashboard and replay UI — no frameworks |
| JSON files | Stores sessions and projects on disk — no database needed |

---

Pls star if ur using it and like it 

