# BodySync design guide (2026 direction)

Rules for how screens are built. The aim: it feels like a current app, not a pile of boxes and not a 2016 template.

## Sources and limits
Trend sources are roundup articles, which are opinion, not studies. Where I found nothing, the point is marked "my judgment".
- 2026 direction: [Muzli mobile trends](https://muz.li/blog/whats-changing-in-mobile-app-design-ui-patterns-that-matter-in-2026/), [daisyUI 18 trends](https://trends.daisyui.com/ui-design-trends-2026/), [Mockflow](https://mockflow.com/blog/ui-design-trends), [Svitla](https://svitla.com/blog/mobile-uiux-approaches-and-trends/), [Tubik](https://blog.tubikstudio.com/ui-design-trends-2026).
  Themes there: Liquid Glass (translucent, blurred layers), purposeful motion, accessibility first, adaptive layouts, expressive type and physical depth, rounded corners, and giving people a way to stop or reduce motion.
- Grouping with spacing and separators instead of extra containers; lists when rows are compared: [Cognite Aura](https://docs.cognite.com/aura-design-system/primitives/card), [UX Planet](https://uxplanet.org/simple-design-tips-for-crafting-better-ui-cards-19c1ac31a44e).
- A border and shadow signal "one clickable thing" ([Nielsen Norman](https://www.nngroup.com/articles/cards-component/)).
- Bottom sheets and bottom nav for one-handed use ([Intuit](https://medium.com/intuit-engineering/native-mobile-app-design-overall-principles-and-common-patterns-26edee8ced10)).

## Principles
1. **Soft, not bold.** No hard edges between areas: halves blend with a gradient, sections separate with space or a hairline. Colors are pastel (pink, lilac, blue) over a calm base; saturated color is kept for the one main action and for achievements.
2. **Depth through light, not borders.** Layers are told apart by blur, translucency and gentle gradients. Heavy drop shadows and outlined boxes are out.
3. **A box only for something you open or act on as one unit.** Everything else is a row, a rule line, a big number, or spacing.
4. **Type does the work.** One typeface (Inter), large and confident headings, a clear size step between title, body and caption. Numbers (weights, reps, PRs) are the largest thing on a data screen.
5. **Motion with purpose and a way out.** One fade per screen, short feedback on every tap, 2 seconds for a level-up, `prefers-reduced-motion` respected, and sound has a visible mute.
6. **Accessible first.** 44 px targets, contrast checked in light and dark, nothing important only in color, nothing hidden in popovers.
7. **Adaptive.** Bottom-reach actions on a phone, sidebar on desktop, same content and order.

## Pattern catalog (pick a different one per screen)
| Pattern | Use for | Not for |
|---|---|---|
| Hairline list row (photo, title, detail, action) | exercises, lifts, routines, history | a single item |
| Full-bleed hero band with gradient scrim | today's workout, a skill, rest day | lists |
| Big number + small label (no container) | PR weight, sets done, weekly total | more than 3 in a row |
| Step ladder / timeline on a line | skill steps, onboarding progress, plan order | unrelated items |
| Pill row | goals, muscles, filters | more than ~8 options |
| Segmented switch | lb/kg, 4W/3M/All | navigation |
| Floating translucent action bar (glass) | Done with set, Continue, Start | pages with no main action |
| Gradient split page | sign-in, welcome, empty states | data screens |
| Inline edit (tap the number) | weight, reps, goal days | long forms |
| Single curve with one label | progress per lift | tables of numbers |
| Dialog (one question, two buttons) | delete, discard, "just today or new level?" | forms |
| Paragraph with a bold lead-in | explanations, "why we ask" | repeated data |

## Per screen
- **Sign-in / onboarding:** gradient split page, one question per screen, no box. Left plain, blending into an animated right side.
- **Home:** hero band for today's plan, hairline rows for its exercises, one primary button, week flames as a plain row. Rest day: hero plus 3 rows.
- **Session:** exercise demo large, big weight and reps numbers, floating Done bar, plain plan list. No boxes around sets.
- **My lifts:** rows with a small trend line; opening one shows big numbers (best, last, next).
- **Progress:** big numbers and one curve per lift; patterns noticed as sentences.
- **Skills:** a step ladder per skill with the current step enlarged.
- **Library:** pill filters, then rows.
- **Profile:** plain labeled fields with a line of "why" under each.

## Visuals
- Photos and animations are for exercises and backgrounds only. No stock photos of people on other screens.
- Animated characters come only from files whose license allows app use, credited in Profile > About. Canva elements are not used (see README note on licenses).
- One icon family. No emoji in the UI.

## Rules by page type
Each kind of page has its own rules. A global style is not enough.

### Sign-in
- Evidence: guides recommend a lean page, one clear social button, at most 3 options, and one consistent word ("Sign in") ([UX Planet](https://uxplanet.org/12-best-practies-for-sign-up-and-login-page-design-69d6cd045cf), [web.dev](https://web.dev/articles/sign-in-form-best-practices)). I found no source on where a privacy link should go (my judgment: one small line under the button).
- Rules: logo, one headline, one sentence, one button, one line "Private to you" with the privacy link. No storage details, no feature list, no form.
- Clear split: a curved white panel on the left, an animated scene on the right. The scene shows a person working out (an animated character, not a photo) so the app's purpose is clear at a glance.
- Phone: the scene is a band at the top, the white panel rises over it.

### Onboarding
- Evidence (vendor blogs, directional only): long onboarding lowers completion, most drop-off is on the first screen, ask profile questions progressively, and get to a first completed workout fast ([RevenueCat](https://revenuecat.com/blog/growth/why-your-onboarding-experience-might-be-too-short), [Adapty](https://adapty.io/state-of-onboarding/report/), [Glance](https://thisisglance.com/learning-centre/how-do-you-design-onboarding-that-enables-smart-personalisation)).
- Rules: one question per screen, thin step bar, big heading, one line of "what this changes", sticky Continue, quiet Skip, Back keeps answers. Max 5 questions. Everything else is asked later, in context. Ends on a first workout, not a settings summary.

### Home (daily)
- Answers "what do I do today?" first. Hero plus rows. One primary action. Rest day and welcome-back are different states of the same page.

### Workout session
- The least decoration. Large numbers, one next action, rest timer, the demo always visible. No navigation chrome competing with logging.

### Progress
- A calm page. One curve, big numbers, sentences that notice patterns. Never punish absence: lifetime totals do not reset.

### Library / lists
- Pills then rows. Dense and quick to scan. No decoration.

### Profile / settings
- Plain labeled fields, each with a "why" line. No gradients or hero.

## Sign-in and onboarding, laptop and phone (Nov 2026 revision)
What the research says, and where it came from. Sources are vendor blogs and editorial write-ups, so treat them as direction, not proof. I could read text descriptions of these apps' screens but not see the screenshots themselves.
- **Split sign-in on wide screens, picture panel hidden or moved on phones.** Split layouts with the sign-in action on one side and the value on the other are common ([Eleken](https://www.eleken.co/blog-posts/login-page-examples)); on small screens the visual panel can be hidden or adapted ([Adobe](https://www.adobe.com/be_fr/products/xd/learn/design/layout/design-login-page-ui.html)). One page, one main action ([HubSpot](https://blog.hubspot.com/website/login-screen)).
- **Google button colours** follow Google's branding guide for light (white, #747775 border) and dark (#131314, #8E918F border).
- **Workout apps known for design.** Gentler Streak (Apple Design Award 2024, Social Impact): colourful, friendly, compares you only with your own history, respects rest ([Apple](https://developer.apple.com/news/?id=3m0ht22s)). Fitbod: opens onboarding with purpose, not demographics, then shows what the plan will do ([ScreensDesign](https://screensdesign.com/showcase/fitbod-gym-fitness-planner)). Trackers (Strong, JEFIT, Planfit): large tap targets, a big rest timer with +/-15 s, one clear "start" action ([ScreensDesign](https://screensdesign.com/articles/workout-tracker-app-design-examples/)). Setup ends on one large "start first workout" button (10K Runner, [ScreensDesign](https://screensdesign.com/articles/fitness-app-onboarding-examples/)).
- **Progress that shows position and what is left** ([ScreensDesign](https://screensdesign.com/articles/onboarding-progress-indicator-examples/)), and "Step n of N" so a questionnaire never feels open-ended (Intercom, [Supademo](https://supademo.com/content/plg-onboarding-gallery/intercom)).

What BodySync does with it (my synthesis, not a copy of any one app):
- Phone: one question per screen, a segmented bar plus "Step n of 5", full-width option rows with an icon on the left and a round tick on the right, Continue pinned to the bottom, Back and Skip always at the top.
- Laptop (900 px and up): a rounded tinted panel on the left lists the five steps on a line, ticked as you go with your answer under each, above a picture; the question sits on the right at a reading width (620 px). Sign-in uses the same panel family: words and the Google button on the left, three rotating pictures on the right.
- Colours for both themes come from `ui.split_vars()`, read from `st.context.theme.type`. Limit: if the device switches theme while the page is open, the new palette applies on the next tap or reload.

## Buttons, exits and moments (Nov 2026)

Every screen answers three questions without the person having to ask: *how do I go back*, *what is happening*,
*how do I finish*.

| Kind | Looks like | Where | Used for |
|---|---|---|---|
| **Main action** | Full-width purple pill, 56 px tall, max 480 px wide | Pinned to the bottom (`st.container(key="bs-donebar")`), or right under the card on Home (`bs-homestart`) | The one thing this screen is for: Start, Next, Create playlist, Save my week, Done with set, Resume |
| **Second choice** | Outlined button, same width as its neighbour | In a pair under the main content | Edit / Save as playlist, Skip / Next, Clear / Show N |
| **Small option** | Text button with an icon | Next to what it changes | Back, Cancel, Change workout, Not feeling it today, Create your own exercise |
| **Icon button** | Icon only, with a tooltip | In list rows and the workout top bar | Move up / down (stacked on the left), swap, remove, pause |

Rules:
- **Back** is top left on every screen that isn't a tab. A multi-step flow also has **Cancel** top right, which always
  leaves without saving. Back means the previous step, never a loop.
- **A main action is never greyed out without saying why**, right next to it ("Add at least one exercise", "Pick a
  number to continue").
- **A finished action gets a moment, not a line of text.** Making something (a playlist, your week) opens a pop-up:
  the pictures stack in, a tick, the name, then one big next step and a quiet "Done" (`ui.created`, `_made_dialog`,
  `_week_dialog`). Small saves use a toast.
- **The same job looks and works the same everywhere.** Lists of exercises use the same row (picture, name, muscle
  and equipment) and the same controls (reorder, swap, remove, sets and reps or seconds, add with the shared picker,
  including your own exercises) on the ready page, Change today's plan, the playlist editor, Edit workout and a
  planned day.
- **Fun is light and optional.** An encouragement line during rest and at the finish; with a GIPHY key, a G-rated
  GIF (switch off in You > Fun GIFs).
