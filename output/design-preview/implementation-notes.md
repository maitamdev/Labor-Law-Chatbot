# VietLaborAI implementation

The approved raster is 1643 x 957. Desktop dimensions are scaled against that reference. The logo, decorative desktop hero and article photographs reuse the approved artwork through CSS sprites; the question form, navigation, document list, quick actions and conversation UI are interactive HTML controls. Mobile switches to a readable single-column layout.

## Changed surfaces

- ui/components/approved_layout.py: markup, escaped messages, safe citation links and Streamlit v2 component registration.
- ui/frontend/approved.css: reference layout, crimson/gold/cream styling and mobile breakpoints.
- ui/frontend/approved.js: submission, navigation, dialogs, draft preservation, copy actions and document filtering.
- ui/streamlit_app.py: connects the new surface to the existing session-local chat service, streamed inference, feedback and conversation persistence.
- ui/styles/app.css: resets the Streamlit host shell.
- .streamlit/config.toml: matching colors and local static image serving.
- requirements.txt: Streamlit >= 1.51 for components v2 and markdown-it-py.

## Verification

- Eight targeted tests passed: escaped user/model/history HTML, safe official citation URLs, deduplication, incomplete-evidence notices, busy state, responsive breakpoint validity and existing session persistence/formatting.
- Browser checked at 1643 x 957 and 390 x 844.
- Verified Enter submission and an actual conversational reply, new conversation creation, history dialog, navigation and Vietnamese accent-insensitive document filtering.
- Browser console had no application JavaScript errors during these checks.
- Final desktop region measurements at 1643 x 957: header ends at y=80; hero ends at y=416; composer at x=308.984, y=416, width=895.016, height=131; news at x=284.984, y=699.188, width=943.016; documents at x=1239, y=96, width=392, height=400; utilities at x=1239, y=512, width=392, height=373; footer at y=893, height=64.
- Browser screenshots: implemented-desktop.jpg and implemented-mobile.jpg in this directory.

This is a visual reconstruction from a generated reference, not a certified pixel-identical match. Browser font rendering and UI icon geometry can differ from the raster reference. Login and attachment processing did not have backend implementations in the existing app; the corresponding controls explain this rather than claiming to perform those operations. No national coat of arms is used by the new surface.

## Assets

- Approved artwork: ui/static/approved-homepage.png and ui/static/approved-logo.png.
- UI icons: vendored Tabler icons from the official repository, with LICENSE in ui/static/icons.
- Running local application: http://127.0.0.1:8501.
