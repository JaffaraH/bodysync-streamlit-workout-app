# BodySync research and audit

The working reference for "does this make sense?" Read it before changing a flow. Every claim the app shows a
person must also be in `research.json`, with a status: verified, secondary or unverified (never shown as fact).

Last walkthrough: 23 November 2026, on phone (375 px), tablet (768 px) and laptop (1280 px), light and dark,
as a new person (Sam), a regular person ("me") and an on-and-off person ("away", 18 days gone).

---

## 1. What the owner wants (the bar every page is held to)

- Functionality first: it tracks what you did, and it actually helps you get stronger.
- Never lost: Back and a way out on every screen, no hidden controls, navigation always visible.
- Open the app, see what's planned, tap Start. No timer pressure on sets; a rest timer that dings and can be skipped.
- Every page should feel like you did something: clear feedback, a congratulation at the end, a clear "what next".
- Works for everyone: brand new, consistent, or coming back after a break. Never a blank or random page.
- Evidence-based, and honest when evidence is thin.

---

## 2. Design research

| Topic | What the guidance says | What BodySync does |
|---|---|---|
| Body text size | 16 px body on mobile web is the common baseline; iOS body is 17 pt, Material 3 Body Large is 16 sp ([Smashing](https://www.smashingmagazine.com/2018/06/reference-guide-typography-mobile-web-design/), [a11y project](https://www.a11yproject.com/posts/text-resizing-in-ios-and-android)) | Streamlit's 16 px body; inputs are 16 px+ so iOS does not zoom on focus |
| Line height | About 1.4 to 1.6 for body copy; WCAG 1.4.12 tests 1.5 | 1.5 on long text (notes, captions) |
| Typeface | One clean UI face, real weights (not browser-faked bold) | Inter 400/500/600/700 loaded from jsDelivr (checked: all four are loaded) |
| Touch targets | 44 px minimum ([Digital.gov](https://digital.gov/guides/mobile-principles/tap-targets)) | Buttons 46 to 64 px; the live-workout inputs are 64 px tall |
| Response time | Under 0.1 s feels instant; up to 1 s keeps flow; 2 to 10 s needs a looping indicator ([NN/g](https://www.nngroup.com/articles/progress-indicators/)) | Saving is instant, so no fake "saving..." wait. A short pop-in marks the moment instead (see below) |
| Confirmation | A success message confirms an action the person started, appears only after it really finished, and offers undo for reversible actions ([Intuit content design](https://contentdesign.intuit.com/product-and-ui/confirmations/)) | `ui.saved()`: the items' pictures pop in, then a green tick, then "Saved to My routines" and a link to it. Shown where the person is looking, not as a corner toast |
| Navigation | Visible navigation is found more often than a hidden menu (NN/g) | Bottom tab bar on phones and tablets (under 1024 px); sidebar on laptops. Tablets used to hide the menu behind ">>": fixed |
| Illustrations | Should belong to the page, not look like a framed gallery | Sign-in on phones: logo, headline, picture, choices, in one column; no panel, border, mat or shadow. In light mode the art blends into the page |
| Credits | Freepik (Magnific) asks free users to credit on the app's credits page, easy to find ([Freepik FAQ](https://www.freepik.es/ai/faq/apps-and-games)) | A small "Credits" link on sign-in (opens the credits) and a Credits/About section on the You page. No credit lines under pictures |

### Feedback moments ("does it feel like I did something?")

| Moment | Feedback now |
|---|---|
| Tap Done on a set | Set ticks off in the table, rest timer starts, PR toast if it beat a record |
| Rest ends | Soft two-note chime (made in the browser, no sound file) and a short buzz on Android; set screen returns by itself. Switch: You > Sounds |
| Skip rest | Straight back to the next set |
| Save a curated workout or a finished workout as a routine | Pictures pop in, green tick, "Saved to My routines", link to My lifts |
| Finish a workout | Purple flame (Noto fire, recoloured), headline, PR cards, three stats, what to do next |
| First ever workout | "Today's numbers are your baseline. Next time, you're aiming to beat them." |
| Skill practice | Result dialog with the same purple flame, step progress, what's next |
| Weekly progress | Home flames fill in for each day trained; "X of Y days this week" |

Rules for the finish screen: always three stats, never a zero. A stat that doesn't apply gives way to one that
does (Lifted becomes Reps on a bodyweight day). Bodyweight records read "12 reps", never "0 lb × 12".

---

## 3. Training research (how BodySync helps people get stronger)

### The progression rule (verified)

**ACSM 2009 position stand** ([PubMed 19204579](https://pubmed.ncbi.nlm.nih.gov/19204579/), primary text read):
"a 2–10% increase in load be applied when the individual can perform the current workload for one to two
repetitions over the desired number on two consecutive training sessions." It also says novices should
"train the entire body 2–3 d·wk⁻¹".

**Plotkin et al. 2022** ([PubMed 36199287](https://pubmed.ncbi.nlm.nih.gov/36199287/)): adding reps at the
same weight and adding weight gave similar muscle and strength gains over 8 weeks. So "one more rep" is real
progress, not a consolation prize.

What the app does (`training.suggest`):

1. **First time, no baseline:** "pick a weight you could lift about 10 times" (weights), or "as many reps as you
   can with good form" (bodyweight). That first log becomes the baseline.
2. **First time, with a known best:** starts at 75% of the estimated max (Epley), eased after a break.
3. **Inside the rep range:** same weight, aim for one more rep each set.
4. **Top of the range once:** "Do it once more and the weight goes up next time." (Visible next level.)
5. **Top of the range twice in a row** (or once and it felt easy): add weight.
6. **Size of the jump:** the usual step (5 lb upper, 10 lb lower; 2.5 / 5 kg), or half of it when the
   weight is light, so it stays near the 2–10% guidance. (Before: 5 lb on a 20 lb dumbbell, +25%.)
7. **Bodyweight moves:** never "add 5 lb". At the top of the range: try a harder version or slow the lowering.
8. **Two tough sessions in a row:** drop 10% and build back. **Said it hurt:** 80% and a form check.
9. **After a break:** 90% (2–4 weeks), 75%, 60%, 50% (16+ weeks). Records are never reset.

Rest times: 60 s bodyweight, 90 s lighter weights, 2.5 min heavy barbell lifts (`rest-hypertrophy`,
`rest-strength`, both verified).

### Base weight: how a person sets it and sees it

- Set it: My lifts > Add lifts (optional best weight), or just log the first workout.
- See it: Progress shows the best set, estimated strength, and "+N lb since you started" for each lift; the
  set screen shows "Previous" for every set; Home lists recent records.

---

## 4. Walkthrough by person

### New person (Sam)

| Step | Before | Now |
|---|---|---|
| Sign-in (phone) | Picture panel on top, framed, credits under it | Logo, headline, picture, choices; Credits link at the bottom |
| Onboarding | Fine | Fine; welcome says "Your first workout is ready on Home" |
| Home after onboarding | No workout at all, only the skill | "Your first workout: Full body, no equipment" (beginner-friendly, needs nothing), Start or See other workouts |
| Workout tab | Blocked by "Set up my lifts" | Curated workouts first, "Track your own lifts" below |
| First set screen | "Pick a weight you could lift 10 times" on a squat with no weights | "Do as many reps as you can with good form" |
| Finish | Orange emoji, "0 lb lifted", "No PR today", "Next time: lower body" | Purple flame, "your baseline", Sets / Reps / Minutes, "Full body, no equipment again in 2 or 3 days" |
| Home after one workout | "Lower body · 1 exercise · not trained yet" | Same workout again ("Up next" / "Trained today") until 3+ lifts are tracked |

### Regular person ("me")

Home shows this week's flames, then one thing to do (Up next, Continue workout, or a rest-day suggestion), then
records and skills. Workout tab: From your lifts (Upper / Lower / Full / Custom), then curated workouts.
My lifts: routines (Start), recent workouts (Repeat), all lifts. Progress: totals, a lift chart, plain-language
notes, history.

### On-and-off person ("away", 18 days)

Home: "Welcome back. Your records are safe, and today's weights start a little lighter." Weights are eased by
the break rule; nothing resets; the weekly goal costs nothing when missed.

---

## 5. Functionality fixes from this walkthrough

| Problem | Fix |
|---|---|
| A workout in progress lived only in memory: a sleeping phone, reload or restart lost every set (while the screen said sets were saved) | Saved after every tapped set (`live_session` preference); restored on return; cleared on finish or discard. Tested with a server restart mid-workout |
| Sign out existed only in the sidebar, which phones never show | Account section with Sign out on the You page |
| Tablets hid navigation behind ">>" | Tab bar up to 1023 px |
| Bodyweight lifts were told to add 5 lb | Reps, then a harder version |
| Weight went up after one session, by a fixed 5 or 10 lb | Two sessions in a row (ACSM), jump scaled for light weights |
| New people had no workout to start | Starter workout on Home; curated list open to everyone |
| One tracked lift produced a "Lower body, 1 exercise" plan | Plans from your lifts need 3+ lifts; until then, the ready-made workout |
| No sound when rest ended | Chime plus buzz, with an off switch |

Tests: `for t in training skills drive db_contract research plan; do .venv/bin/python tests/test_$t.py; done`
(all pass; new tests cover the two-session rule, light-weight jumps and bodyweight progression).

---

## 6. Answers to common questions

- **How do people sign in?** With Google, once the app is deployed with an `[auth]` section in its secrets
  (DEPLOY.md). "Who's training?" only appears on a test computer with `BODYSYNC_PROFILES=1`; real visitors
  never see it.
- **Is my data remembered?** Yes. With Google sign-in, everything (lifts, routines, skills, custom pictures,
  the workout in progress) is saved in a private app folder in the person's own Google Drive. Locally it is a
  file on the computer.
- **Is a routine (playlist) remembered?** Yes, it's saved immediately and listed in My lifts > My routines.

---

## 7. Still to do (in order)

1. ~~Plan my week~~: done (see section 8).
2. **Skills and workouts in one library.** Let a skill's drills (or a whole skill practice) be added to a
   routine, so one saved routine can hold lifts and skill work. Data model change: routine items with a
   `kind` (lift, hold, reps).
3. **Rest day stretches startable** (today they're a list with "Train anyway").
4. **Swap an exercise** for one that trains the same muscle (5 options), from the lineup and the set screen.
5. Verify photo upload in the custom-skill editor on a real phone.
6. Remaining popovers and expanders in `workouts.py` and `nutrition.py`.
7. README and DEPLOY updates, then Google setup and deploy with the owner.
8. `gifs.py` is no longer used by the celebration (the flame is fixed); remove it if GIPHY isn't wanted.

---

## 8. Plan my week (built 23 November 2026)

The owner's main ask: open the app, today's workout is already there, tap Start.

- **Where:** Workout tab, "Your week" at the top (Plan my week / Edit my week). Home shows a quiet "Plan your
  week" row until a plan exists.
- **The planner:** seven rows, one dropdown each: Rest, your routines, Upper/Lower/Full from your lifts (once 3+
  lifts are tracked), the curated workouts, or a skill practice. "Fill in a suggested week" uses the weekly goal:
  whole-body sessions spread a day apart (Mon/Wed/Fri for 3; ACSM novice guidance), upper and lower alternating
  for 4+ days with enough lifts (each trained twice: frequency-2x), and a light skill practice on a free day.
  Routines are never guessed into the suggestion. Save shows the pictures-and-tick confirmation.
- **Home with a plan:** "Today: <workout>" with its exercises and Start. Trained today: "Done for today. Next:
  ...". Planned rest day: "Rest day. Next: <workout>, tomorrow" with "Do it today instead". Below: "This week",
  each planned day with a tick when you trained that day. Days that passed untrained are just dimmed; nothing
  says "missed" (weekly-not-daily).
- **Flexible by design:** training on any day counts toward the weekly flames; the plan is a guide.
- **Stored:** `week_plan` in the person's settings (same JSON blob, no schema change); removed routines or skills
  drop out of the plan automatically.
- Code: `plan.py` (options, suggest, describe, start), `today.plan_view`, `home.planned_today`. Tests:
  `tests/test_plan.py`.

---

## 9. Plan my week, version 2 (built 23 November 2026)

Four short steps with a progress bar and Back on each: **how many days** (1 to 7, with a sentence on what that
number means), **which days** (pre-spread so there's a day between), **your main goal**, then **your week** to
review and change. Each goal fills the week differently, with "Why this plan" citing research.json:

| Goal | Week | Evidence |
|---|---|---|
| Get stronger | Whole body on each day (upper/lower alternating at 4+ days with 3+ tracked lifts) | novice-total-body, progression-top-of-range |
| Build muscle | Same split, more days when you have them | volume-hypertrophy, frequency-2x |
| Lose weight | Up to 3 strength days spaced apart, brisk walks on the rest; shows weekly walking minutes and says food matters most | weight-loss-activity (ACSM 2009), strength-keeps-muscle (2025 meta-analysis) |
| Learn a skill | Half skill practice, half strength | stretch-weekly, novice-total-body |
| Stay healthy | Two strength days, walks on the rest; compares minutes with 150-300 | who-activity (WHO 2020) |

Walks are a new plan item (brisk, or the 12-3-30 incline walk shown with its honest caveat: one 16-person
single-session study, no weight-loss data). A walk has its own screen (start/pause clock, or just enter minutes),
is logged as `cardio` (kept out of strength stats) and ends with the purple flame.

Bug fixed while testing: Streamlit drops a control's value once its step is off screen, so the days and goal
vanished by step 4 (every day became Rest). Answers are now copied on Continue.

---

## 10. Owner feedback still to build (23 November 2026), with the proposed design

Ordered by how much it improves the first week of use.

1. **Continue-workout bar on every tab.** If a workout is in progress and you open another tab, a slim bar sits
   above the tab bar: the current exercise's moving picture, "Bodyweight Squat · set 2 of 3", and Continue. Same
   idea as a music app's mini player. Nothing is hidden; one tap back.
2. **Onboarding fixes.**
   - Skills list: plain names ("Push-up", "Pull-up", "Pistol squat", "Handstand", "Touch your toes",
     "Front splits"), drop "Push-up variations", add "Create your own".
   - Fitness level: concrete descriptions (Beginner: new to training or back after a long break. Intermediate:
     training regularly for 6+ months and know the main lifts. Advanced: years of structured training).
   - Go easy on: add wrist, hip, ankle, neck, plus "Something else" (free text, used only to show a reminder).
     Needs research on which moves to swap for each.
   - Welcome screen asks "What do you want to do first?" with 3 choices (a full-body starter, a skill practice,
     plan my week) instead of deciding for you.
3. **Skills page redesign.** Segmented pills at the top: **Explore** (all ladders plus Create your own),
   **In progress** (every skill you're on, each a compact row with its step and Practise), **Done** (finished
   skills with the date). Fix "Change step" on phones (it's cut off), and let a person add, remove and reorder
   steps on built-in ladders too.
4. **Two ways to unlock a step.** A step can have alternatives (wall push-up OR band knee push-up) and "bridge"
   drills that research supports for getting to the next level: plank holds and slow negatives (eccentric) for
   push-ups and pull-ups. Needs a short research pass on eccentric training, then a data change (a step holds a
   list of options; doing any one counts).
5. **Workout tab as an explore page.** Rows by category (Full body, Upper, Lower, No equipment, Stretch and
   mobility, Core, Quick 15 minutes), each a horizontal row of workout tiles with a picture, like a streaming app.
   Search on top. More content: the Free Exercise DB already includes stretching, plyometrics and cardio moves
   (the rest-day stretches use them), so stretch, mobility and core workouts can be built from it with no new
   download. Other free sources (for example wger, CC BY-SA) would need the owner's OK before downloading.
6. **Exercise library with filters**, modelled on the reference app the owner shared (not copied): search,
   Equipment and Muscle filters as full sheets with pictures, sort. Used when adding to a routine or a custom
   workout.
7. **Training calendar** ("memories"): a month grid where trained days show the body areas worked. Fits on
   Progress.
8. **Follow along with a video (idea, needs care).** My understanding of YouTube's terms is that
   downloading or processing videos isn't allowed, but embedding with the official player is, and the player can
   start and stop at set times. So the workable version: paste a link, the app embeds it, and the person marks
   each exercise's start and end ("Squats 0:30 to 1:15"). The app then plays one segment at a time, with rest
   and logging between, at the person's own pace, and several videos can be combined. Automatic breakdown of the
   video is not possible without processing it, so it's not offered. Guardrails: only youtube.com links, YouTube's
   own embed restrictions and age gates apply, and a report/remove control. Check YouTube's current API terms
   before building.

### Built from section 10 (23 November 2026)

- **Continue bar** (item 1): on every tab except Home and Workout (which show a big Continue), a light bar
  with the current exercise's moving picture, "Continue workout", progress, and a round play button. Also for an
  unfinished skill practice.
- **Onboarding** (item 2): plain skill names (Push-up, Pull-up; "Push-up variations" is now "Harder push-ups"
  and only in Skills > Explore), "Create my own"; concrete fitness levels; go-easy-on areas now Knee, Shoulder,
  Lower back, Wrist, Hip, Ankle, Neck. The old promise of "gentler swaps" was not implemented anywhere, so it was
  replaced by what the app really does: a reminder on the set screen when an exercise loads a flagged area
  (`today.easy_on`, matched to the library's muscles and plyometrics). The welcome screen now asks "What do you
  want to do first?" (preview a first workout, make your own skill, plan my week, or look around).
- **Preview and edit any ready-made workout**: change sets, remove or add exercises from the library, reset,
  then start it or save "my version" to routines. Reached from the Workout list, Home and the welcome screen.
- **Skills page** (item 3): Explore / In progress / Done pills; each skill a compact row (Practise, Open); a
  detail screen with all steps; Change step as a full screen (the pop-up was cut off on phones); "Make my own
  version" copies a built-in ladder into the editor at the same step, so any ladder's steps can be added,
  removed or edited.
- Fixed: people who finished onboarding but logged nothing yet saw an old chooser saying "No sign-up quiz";
  they now get the normal Home.

Still open from section 10: items 4 (two ways to unlock a step), 5 (explore-style Workout tab and more
content), 6 (exercise library filters), 7 (calendar), 8 (video follow-along), and more "go easy on" research
(which moves to suggest instead).

### Explore workouts and the new welcome (23 November 2026)

- **Workout tab is an explore page**: search (by workout, exercise or words like legs, arms, stretch), then
  rows of picture tiles that scroll sideways: Start here, Full body, Upper, Lower, Stretch and mobility, Core,
  No equipment, 20 minutes or less. The whole tile is the button. Explore sits above "From your lifts".
- **Five new workouts, all built from the existing Free Exercise DB** (no downloads): Full body stretch,
  Hips and hamstrings, Morning mobility, Core basics, Quick full body. A script checked that every exercise in
  every ready-made workout has a demo picture (rule: no exercise without a visual).
- **Timed holds** in the live workout: an exercise marked "hold" shows "aim for a 30 second hold", a
  Seconds held box and a Sec column. Holds are logged but never become tracked lifts or records; stretch
  sessions are their own type and stay out of strength stats; stretches rest 15 seconds, not 60.
  Time estimates count holds as hold time plus a change-over.
- **Walks have pictures** (library walking demos) on Home, in the plan and on the walk screen.
- **Welcome after onboarding** is now visual: four picture tiles (your first workout, plan your week, your
  skill, see your progress), each opening that part of the app, and one Go to Home button. The summary list and
  extra sentences are gone.

Next ideas: a countdown timer for holds (the skill practice already has one), more stretch and cardio workouts,
and the Workout tab on dark mode.

### Live set screen redesign (23 November 2026)

Modelled on the owner's reference shots (not copied): the move is the screen.
- Top: End, a running **workout time** clock, and sets done ("1/14").
- The animated demo, large and centered, never cropped (contain, up to 46% of the screen height).
- The exercise name centered and big, "Set 1 of 2 · 30 second hold" under it.
- **Holds**: a big countdown with a round play/pause button; it chimes at zero ("Held. Tap Done.") and logs
  the seconds itself, so there's no extra box. **Reps**: the big weight and reps boxes.
- "How to do it" and "Options" sit in the corners; Options holds Add a set, Do it later and Change lineup.
- One pinned Done. Coaching notes and the sets table are below the fold.
- Stretches: the rest screen says "A short pause to change position" (no muscle-growth research), and the
  "How did it feel?" question is skipped (it only steers weights).
Checked on a phone (stretch hold, countdown to zero, chime) and a laptop (weighted lift).

### Structure, editing that sticks, units (23 November 2026)

- **Workouts tab = explore only**, the same for everyone: title, search icon top right (opens the search
  field), rows of workouts. No plan, no resume banner, nothing personal.
- **Resume lives in the bottom bar** on every tab except Home (which has its big Continue card). Opening the
  Workouts tab from the tab bar shows Workouts even mid-workout; the bar (or Home) takes you back in.
- **Library tab** (was "My lifts"; Spotify-style "your library"): pills This week (your plan, or a suggested
  week from your goal with "Use this week" / "Change it"), Playlists (your saved workouts; make one with any
  name and any exercises), Lifts (train from your lifts, your lifts and records, add a lift), History.
  "Routines" are called playlists everywhere, and playlists can be put on any day of the plan.
- **Planner**: "Start over" is now "Clear" (every day to Rest); "Make a playlist" link; suggested weeks add a
  light practice for a skill you're working on.
- **Edit mid-workout and it sticks**: Options holds Sets and Hold (seconds) or Reps to aim for, with
  "Remember for next time" (on by default). Saved per exercise (`ex_prefs`); every later workout with that
  exercise starts with your sets and hold time. (Reps targets for lifts still follow the progression rule.)
- **Rest**: a ring that empties as the break counts down, with -15 / +15 / Skip; theme colours for light/dark.
- **Units everywhere** (`training.amount`, `training.kind_of`): holds in seconds ("New best on Child's
  Pose: 55 seconds", number highlighted), walks in minutes, bodyweight in reps, lifts as weight × reps in lb
  or kg. Used by the live toasts, finish cards, Home records, Progress and Library. Holds get a "longest hold"
  record only when they beat a previous hold. Tests cover every unit.
- Dark mode: the play buttons and "Today" marks were dark purple on dark; they now use theme colours
  (`--bs-accent-ink`, `--bs-accent-soft`).

### Two ways to unlock a step (23 November 2026)

- A step can list **other ways to clear it** (`options` in progressions.json, or "Add another way to clear this
  step" in the editor). Before the first set, the practice asks "Today's way"; hitting that way's own target counts
  toward the 2-in-a-row rule. Shown on the skill card ("Also counts"), the step list ("or ...") and placement.
- Built in: Wall push-up or slow-lowering wall push-up; Knee push-up or slow-lowering knee push-up or low incline
  push-up; Slow-lowering push-up or a long plank hold; Slow-lowering pull-up or a flexed-arm hang; Band-assisted
  pull-up or 5 slow-lowering pull-ups.
- Evidence: `eccentric-strength` (2025 meta-analysis: lowering-only and lifting-only training gave similar gains in
  lifting strength; lab machines, not push-ups, said in the app) and `knee-vs-toe` (secondary: similar muscle
  ratios, toes harder).
- Tests: any way clears a step by its own target; every alternative is well formed.

Next, from the owner: **workouts that mix lifts and skill work** (e.g. upper body plus a splits block: 3 drills,
then a 60-second split hold), saved as a playlist and plannable; and "what's next" after finishing a skill.

### Owner review fixes (24 November 2026)

- **Workouts tiles**: full-bleed cover photo (chosen per workout, `cover` in curated_workouts.json), a tinted
  gradient, a category chip, title and time on the picture. Rows need 3+ workouts (Upper and lower combined;
  stretch, mobility and core combined). The same cover is used on the preview, Home and the plan.
- **Swap a move**: `training.alternatives` finds up to 3 picture-backed exercises for the same main muscles
  (same push/pull/hold pattern, similar equipment, same level or easier; no jumps for squats; no-equipment stays
  no-equipment; holds swap for holds). In a workout: Options > Swap (sets done stay logged). Before starting: the
  swap icon in the editor.
- **Mixed workouts**: a playlist can hold a skill block (`Skill: <id>`): it expands into the skill's drills and
  current step when it starts, each with its demo; finishing the step counts as a practice (2-in-a-row rule) and
  is logged as skill practice, never as a lift.
- **Home**: "Same workout. Aim for one more rep."; "Do it again"; "moves" instead of "exercises".
- **Preview**: Edit and Save as playlist side by side; save asks for a name; the editor shows each move's picture,
  swap and remove icons, Sets and Reps or Seconds.
- **Library**: tap rows everywhere (`ui.tap_row`). This week: picture rows, Start for today, "Do today" to swap a
  day's workout to today, tap to preview. Playlists: New playlist button; rows "7 moves · 15 min"; tap opens the
  playlist page (cover, list, Edit, Remove, pinned Start); editor for new or existing playlists with name, moves
  and skill blocks. Lifts: your lifts only (the hidden starter lifts added during onboarding are gone), Add a lift,
  tap to open. History: tap a workout to see every set in its unit and Do it again.
- **Skills**: Explore > tap a skill > its page (goal, steps with pictures, why) > Add to my skills > "Where are you
  now?" picture rows > Start at step N > the skill's page with a pinned Start practice. In progress rows have
  Start. Change step works full screen. 19 steps gained library demos; steps with no true match show the skill's
  picture. Headers without a photo get a purple gradient so text stays readable.
- Paused at the owner's request: the You tab.

### Warm-ups, cool-downs and rest-day stretching (24 November 2026)

- **Warm-up** (offered before the first set of any strength workout, Add or Skip): about 5 minutes of moving
  exercises for the day's area (upper: arm and shoulder circles, dynamic chest stretch, inchworm; lower: hip
  circles, front and side leg raises, bodyweight squat; full: a mix), plus a tip to do 1 or 2 light sets of the
  first lift. Evidence: `warmup-stretch` (short static holds trivial, long holds reduce strength; dynamic preferred,
  Chaabene/Behm 2019) and `specific-warmup` (lighter sets of the same lift helped in several studies, mixed;
  Ribeiro 2021).
- **Cool-down** (offered when every set is done, Add or Finish now): four 30-second holds for the worked area.
  Honest note shown: it did little for soreness or next-day performance (`cooldown`, Van Hooren and Peake 2018).
- Warm-up and cool-down moves are logged as stretching (never lifts or records). Every move has a demo picture.
- **Rest days**: Home's rest card and a planned rest day both offer "5-minute stretch", a guided session with hold
  clocks. Home's "This week" now uses the same picture rows as Library (with Do today).

### Dark mode pass (24 November 2026)

Checked in dark on a phone: Home (in progress, planned rest day), Workouts tiles, workout preview and editor,
swap window, Library (This week, playlist page), Skills (In progress, skill page), the warm-up card in a workout.
Fixes from the pass:
- Two-button rows (Edit / Save, Edit / Remove, warm-up Add / Skip, Change step) and the editor's Sets / Reps boxes
  were squeezed by the picture-row rule; a more specific rule now makes them share the row equally.
- Home's "This week" used plain text while a workout was in progress; it now uses the picture rows everywhere.
- The Workouts tab reopened an old preview or planner when tapped from the tab bar. Deliberate jumps now go through
  `ui.to_workout(pages)`; the tab bar always lands on the Workouts page (the bottom bar returns to a live workout).
- The plan list showed "3 × 6 @ 0 lb" before a weight is chosen; it now shows the weight only once there is one.

---

## 11. Full check-up (24 November 2026)

Ratings are 1 to 5 for how it feels to use on a phone today (5 = polished, nothing confusing).

| Area | Rating | What works | What still feels off |
|---|---|---|---|
| Sign-in / Who's training | 4 | Clean order, one picture, Credits link | Real Google sign-in never tested (needs setup) |
| Onboarding | 4 | Short, clear steps, visual welcome tiles | Welcome tiles could preview a real first week |
| Home | 4 | Today's workout, picture week rows, flames with states | Two big buttons on rest days; In progress card is tall |
| Workouts (explore) | 4 | Full-bleed tiles, home / gym rows, 23 workouts with demos | No yoga or pilates (no demos in the library); search only by text |
| Workout preview + editor | 4 | Edit / Save side by side, swap, sets and reps | Rep range collapses to one number when edited |
| Live workout | 4 | Big demo, clock, hold timer with chime, rest ring, Options with swap | Weight starts empty for new lifts (by design); long plan list under the set |
| Warm-up / cool-down | 4 | Offered at the right moments, honest research | Only one warm-up per area; no "always add" setting yet |
| Library | 4 | Week, playlists, lifts, history all tappable with pictures | Playlist editor uses one sets/reps value for every move |
| Skills | 3.5 | Clear add > place > practise flow, two ways to unlock | 18 steps borrow a similar demo (labelled); custom photo upload untested on a real phone |
| Progress | 3.5 | Records, chart, notes, history | Not reworked in this round; needs the same tap-row style |
| You (Profile, Nutrition, FitBuddy) | 3 (paused) | Focus, goal, sounds, account, credits | Nutrition and FitBuddy need their own review; FitBuddy needs a free Gemini key per person |
| Dark mode | 4 | Checked on every new screen | Progress and You not rechecked |

### What changed in this round, and is it better?
- Smoother demos (clear holds, quick switch, no ghosting) and moving pictures in tiles, headers and rows: better.
- Week flames with four states (done, today, coming up, missed): better feedback, missed stays quiet on purpose.
- More workouts, home and gym rows, push / pull / legs, arms, shoulders, glutes, quick sweat: better variety.
- Borrowed demos are labelled "Demo shows a similar move": more honest. The real fix is better demos (below).

### Open questions for the owner
1. A second exercise source for calisthenics demos (push-up variations, handstand, pistol, splits). Options:
   wger (open data, CC-BY-SA, licence per exercise, mostly still images) or a paid API such as ExerciseDB
   (animations, licence terms restrict reuse). Downloading needs the owner's OK; wger is the safe free choice.
2. Should warm-ups be offered every time, or remembered as "always" / "never"?

### Still to do (in order)
1. Progress page in the new style; You tab review (Nutrition, FitBuddy) when the owner un-pauses it.
2. Setup with the owner: Google sign-in and Drive (DEPLOY.md), then hosting. DEPLOY.md mentions GIPHY and Noto
   celebrations that no longer exist and needs an update.
3. Security review (see 12).
4. Code readability (see 13).

## 12. Security notes (first pass; full review is last on the list)
- SQL injection: every database query passes values as parameters (`?` / `%s`), never by pasting text into SQL.
  The only formatted SQL uses fixed table names from the code. So typing SQL into a name field does nothing.
- Whose data: in Google mode each person's data lives in their own Google Drive app folder and is keyed by their
  Google email; the app owner cannot see it. The "Who's training?" picker is a test mode with no passwords and
  must stay off on a public site (it only turns on with BODYSYNC_PROFILES=1 and no Google setup).
- Secrets: `.streamlit/secrets.toml` and `.env` are git-ignored; each person's Gemini key is pasted per session
  and never saved.
- To check in the full review: HTML that shows user-typed names (escaped everywhere?), uploaded photos (size
  limit 10 MB, resized), and the Drive token handling.

## 13. Code readability (first pass)
- 8,700 lines of Python. Most files open with a docstring saying what they do; functions have short docstrings.
- `today.py` is 1,700 lines and does too much (explore, preview, planner, live workout, finish screen). Split it
  into workouts_explore.py, workout_preview.py, live_workout.py and finish.py.
- README needs updating for the new structure, and a short "how the app is organised" map for new developers.

## 14. Results, demos you can copy, and protein (23 November 2026)

**Demos show where a move starts and finishes.** Every big demo (set screen, How to do it, Library detail) now
holds each position with a purple "1 Start" / "2 Finish" label, then switches quickly. How to do it adds:
"Start at 1, move to 2, then come back to 1. That's one rep. For a hold or stretch, stay at 2." Small thumbnails
and banners keep the clean version (a label that small can't be read). Animations rebuild automatically (v3).

**New open-licensed demo (wger.de).** Pike Push-Up, a drawing by wger.de contributors, CC-BY-SA 4.0, split into its
two positions and animated (`extra_exercises.json`, `static/wger/`). Credited in Credits and You > About. The Pike
hold skill step had no demo before; it now uses this one with "Demo shows a similar move". Checked and not used:
wger's 4 pistol squat files are one identical photo of a weighted pistol (can't animate, wrong variant); Hip Flexor
and Runners Lunge are single photos (would be static). No usable demo exists there for a dead hang, knee push-up,
forward fold or full split.

**Built for a result (Workouts, first row).** Each program shows a Goal card: what it is for, how often to show up,
what to honestly expect, and its sources.
| Program | Goal | How often | Key evidence |
|---|---|---|---|
| Flat stomach, the honest way | Fat loss around the middle | Any 3 days + 8,000-10,000 steps daily | Ab training alone did not cut belly fat (RCT 2011); steps meta-analysis (2022) |
| Strong knees | Less pain, better function | Any 3 days, 8 weeks | Cochrane: exercise helps knee osteoarthritis (2015/2024) |
| Your first pistol squat | Pistol on each leg | Any 3 days + Skills ladder | Frequency 2x/week; progression |
| Your first handstand | Wall, then freestanding | Any 3 days + Skills ladder | Same |
| Pilates-style mat core | Stronger core, easier back | 2-3 days, 8 weeks | Cochrane: Pilates for low back pain (2015) |
Every card says: "Missed a day? Pick the next free one. Showing up 3 times a week is what counts, not which days"
(habit study: missing one day did not undo progress, 2010). The Pilates program uses only Pilates-style mat moves
that have demos; classic moves such as the Hundred have none, so it doesn't claim to be a full class.
Also fixed: "Push at home" said no equipment but ended on a dumbbell move; it now ends on Pike Push-Up.

**Nutrition, rebuilt around protein (no outside service needed).**
- Protein today: body weight gives a target of 1.6 g/kg a day and about 0.4 g/kg per meal (sources in app).
- Pick the foods you have, enter servings eaten or planned; a bar shows e.g. "77 g of 109 g", and top-ups come
  only from your own foods (biggest first, never a whole shake for the last 7 g). Values are rounded USDA
  FoodData Central numbers and can be edited to match your labels. Everything is remembered; the tally resets daily.
- Meal idea from what I have (Gemini, optional): one meal from your foods aimed at your protein per meal.
- Weekly meal plan (Gemini) now uses your daily protein target and ends with a grocery list.
- Edamam recipe search only appears if keys are set: its Recipe Search page is marked "Version Retired" and free
  terms are unclear, so it is no longer something new users see first.

**Ideas for later (not built):** a protein streak on Home; FitBuddy reading your real logs ("you added 10 lb to
squat this month, try 5 more"); a PR banner that sets the new baseline and says so; photo-based meal logging.
**Seen during testing, not caused by this work:** the seeded test workout's clock shows 5 hours (started this
morning); a first-time barbell weight field starts at "0".

## 15. New playlist flow, one exercise picker, and the home-equipment idea (23 November 2026)

**New playlist is now a 3-step flow** (`playlist_builder.py`), also used for Edit:
1. Name it and "What do you want to work on?" (Upper, Lower, Full body, Core, Push, Pull, Legs, Glutes, Arms,
   Shoulders), or Skip. The choice only pre-fills the Muscle filter.
2. Add exercises: search on top, Filters (Muscle, Equipment, Type, Level, Saved only), A to Z list with letter
   headers, picture, name, main muscle and equipment. Tap a row to add (tick) or remove; "Next · 9 selected"
   stays pinned. Skills in progress can be added too.
3. Your list: body map (main muscles dark, also-worked light, named in a legend), each move with picture, name,
   its own Sets and Reps (Seconds for holds), an X to remove, Add more exercises (back to step 2 with your picks
   kept), Create playlist. Then the pictures slide in and stack, a tick pops, and the name shows.

**One exercise picker everywhere you pick** (`exercise_picker.py`): the Exercise library and New playlist share
the same search and filters. Exercise library "Save" keeps a favourite (Saved tab, and Filters > Saved only);
the new "Add to playlist" puts it in a real Library playlist or starts a new one. Its old "My routines" and
"Build a routine" sections were removed (they were a second, older copy of Library > Playlists).
Not unified yet: the swap and add pickers inside a live workout and Library > Lifts still use a plain search box.

**Fixed along the way:** tap rows only responded on a 26 px strip at their left edge (the invisible button did
not stretch), so taps missed or hit a neighbour. They now cover the whole row, everywhere in the app. The
Continue workout bar no longer covers a screen's own pinned button (it hid "Start this workout" too).

**Idea checked, not built: "use the equipment you already own" (Total Gym, treadmill, walking pad, TikTok boards).**
Possible, and can be done without legal trouble, if built this way:
- Videos: only through YouTube's own embedded player (the video stays on YouTube, the creator keeps the views
  and ads, and a creator who turns embedding off simply isn't playable). Never download or re-host, never hide
  the player's controls or ads (YouTube API Services Developer Policies).
- Brand names: saying "for a Total Gym" to describe the equipment is fine; no logos, no "official" wording.
- AI: the person photographs the equipment (and its manual if they have it); Gemini names it and drafts a few
  moves with steps and muscles; the person checks and edits them. Wording must say AI can be wrong and to
  follow the manual's safety limits.
- Demos: the app asks for two photos, start and finish, and builds the same labelled moving demo as every other
  exercise (their own photos, so no rights questions).
- Where it shows: an Equipment filter value "My equipment" in the picker, and a "With your equipment" row in
  Workouts.

## 16. Workout flow, Progress, safety and docs (23 November 2026)

**Fixed after testing on a phone:**
- Tiles and list rows only responded to taps on a 26 px strip at their left edge (Streamlit sets a fixed width on
  the button's wrapper inline). They now respond anywhere on the card, across the whole app.
- Moving demos on the workout screen showed one still frame: `st.image` re-encodes animated WebP. They are drawn as
  `<img>` now (`ui.demo`), everywhere a demo appears.
- The rest ring disappeared: CSS containing `<number>` was dropped by Streamlit's HTML cleaner. Written with CSS
  escapes now, and the ring drains smoothly.
- The − and + buttons on the set screen sat below the number; the box is now the same height as the input.
- A new step of a flow opened half-way down the page (Streamlit keeps the scroll position). It now starts at the top.
- "Press Enter to apply" is hidden: numbers save as you change them.

**Workout flow.** Starting any workout (curated, playlist, Home, This week, history) opens a ready page: name, moves,
time, muscles worked, the warm-up offer, and the plan you can still change (sets, reps or seconds, weight, move up or
down with stacked arrows, remove, add with the shared picker). The clock starts only on Start workout. "Change
today's plan" during a workout opens the same editor instead of starting over. If a workout is already going,
Resume is the main button and "Start a new one" is secondary. The "How did it feel?" question is only asked for main
lifts, not warm-ups, holds or skill drills.

**Accuracy.**
- Workout summary: "Reps" now counts every rep-based set, matching "Sets", and "Lifted" reads "Total lifted".
- Progress totals are computed from the logged sets each time, so they can't drift.
- The core-stability source link pointed to the wrong record; corrected to Smith 2014 (PMID 25488399), and the claim
  now states only the finding.

**Progress.** Weeks in a row against your own weekly goal (purple flame); lifetime totals (workouts, days, records,
sets, reps, total lifted); favourite workouts and exercises; "Room to grow" (the body area with the least work in 4
weeks, with one workout for it); one chart (all exercises by default, sets per week, or any one exercise with its
first time, best set and change); history where any workout can be done again, added to a day of your week (asks
before replacing what's there), or removed (hidden, with Undo).

**Two-photo limit, verified.** In the Free Exercise DB, 873 of 876 exercises have exactly two photos and 3 have none.
Moves with circles, flutters, scissors or kicks say so and show their written steps under the demo. "Flutter Kicks"
there is a face-down bench version, which explains the confusion.

**Security.** No secrets in any file or in the 7 commits of history. `gifs.py` (unused) and its key were removed. A
copy deployed without Google sign-in no longer opens on a public address, because every visitor would share one
account. User-typed names are escaped in the few HTML spots that didn't escape them.

**Docs.** README rewritten for three readers (users, learners, forkers) with screenshots; `docs/ARCHITECTURE.md`
follows one workout through the code, function by function.

## 17. Exits, planning fully, your own exercises, fun (23 November 2026)

**Found by using the app, now fixed:**
- New playlist could trap you: step 2's Back went to step 3 and step 3's Back to step 2. Every step now has Back
  (previous step) and Cancel (always leaves). Create never waits on a name (it suggests one) and says why when it
  can't save.
- Sunday wasn't tappable in Plan my week: the see-through pinned bar caught taps meant for what was under it. It now
  lets taps through, everywhere.
- "Go to Home" after saving the week didn't work (the button vanished on the next run). It's now a pop-up with Go to
  Home and Keep editing.
- Progress, Exercise library, Nutrition and FitBuddy had no way back; they now have a "You" back button and the You
  tab stays highlighted. The page title "Profile" now matches its tab, "You".
- Finishing a workout started from Library or Progress now returns there (it always went Home).
- A lift suggesting 85 after 95: that's the "back after 2+ weeks" rule (90%). The reason now sits right under the
  number, not in small grey text.

**New:** pause and resume during a workout (paused time isn't counted); "Change workout" and "Not feeling it today"
(same workout, about half the sets, a little lighter) right under every Home card, with a big centred Start;
Plan my week takes several goals, opens any day in the playlist editor to plan it fully, adds a skill practice to a
workout day (runs as one session), and writes its research as what to do ("work up to about 10 hard sets per
muscle a week"); create your own exercise (name, muscle, equipment, reps or seconds, steps, two photos for a moving
demo) from any picker, plus a "Yours" tab; three hour-long gym sessions and an "About an hour at the gym" row;
Full body stretch rebuilt head to toe; the core program is now mostly core; one shared editor and swap everywhere;
pop-ups for "Playlist created" and "Your week is planned"; encouragement lines and optional G-rated GIPHY GIFs.

**Checked:** the 10-sets figure. The volume meta-analysis (Schoenfeld 2017) only covered up to about 10 weekly sets
per muscle, so the advice says "work up to about 10", not more. GIPHY's free key allows 100 searches an hour and needs
"Powered by GIPHY"; results are cached for 6 hours and limited to G-rated.

## 18. Pause screen, new-user test, FitBuddy AI (23 November 2026)

**Pause screen:** a live "paused for" timer, a big round Resume button, what's next (picture, exercise, set), and Edit
plan / End workout. Home's card says "Paused" (or "Ready to start") instead of "In progress".

**New-user test** (fresh data folder): onboarding crashed on step 2. An earlier edit to the goals list had deleted five
definitions (`AREAS`, `ONBOARD_HIDE`, `CREATE_OWN`, `LEVELS`, `LEVEL_NOTE`); they were restored from earlier versions.
`python -m pyflakes *.py` now finds no undefined names anywhere, and the README tells developers to run it.
Onboarding now offers the same 8 goals as Plan my week, and the planner starts from them.

**How apps handle AI keys:** they don't ask people for keys. The app owner's key stays on the server and each person
gets an allowance. BodySync now does the same: one `GEMINI_API_KEY` in the secrets, `AI_DAILY_LIMIT` requests per
person per day (default 20, shown as "X of 20 left today"), and pasting your own key stays optional. Gemini's free
tier limits aren't published as a fixed table any more (they're shown in AI Studio), and on the free tier Google may
use prompts to improve its products, which the app now says where AI is used.
**Model check:** Google's deprecations page lists no shutdown date for `gemini-2.5-flash-lite` (the default), and
lists `gemini-3.5-flash-lite` as a stable newer model; the app falls back to it if a model ever returns "not found".

**FitBuddy:** the plan tool now asks for JSON, may only use exercises from the library that match your equipment,
shows each day with demos, and saves a day (or all days) as real playlists. Anything not in the library is left out
and counted. The machine tool returns name, muscle, setup, steps and a common mistake, and can save it as one of
your own exercises with your photo. Not tested against the live Gemini API (no key on this machine);
`tests/test_ai.py` checks the answer cleaning, the equipment filter and the model fallback.

## 19. FitBuddy after a live test (23 November 2026)

From the owner's live test with a Gemini key: plans and machine answers worked. Fixed after it:
- Saving one day, then "Save all", made duplicates ("Day 3 2"). Each day now shows "saved as ..." once saved, and
  "Save the rest" only saves days not saved yet.
- An AI plan couldn't be changed without asking the AI again. Each day now has Edit (the playlist editor: rename,
  reorder, swap, sets and reps; saving comes back to FitBuddy) and Save as is.
- Saved days connect to the app: "Put these days on my week" spreads them across the week (a day off between where
  possible) and, if the walking habit was picked, fills the other days with a brisk walk.
- Equipment choices are the exercise library's own list. "Anything else" is now focus picks (body areas), a walking
  habit switch, and a notes box with examples.
- The two tools are equal halves. The machine tool says plainly when a photo isn't gym equipment and offers no save.
  With no AI set up, the buttons say "Turn on AI above to use this."
- Your own exercises can be edited (Exercise library > Yours, tap one). Adding one photo to an exercise that has one
  makes it the finish position, so its demo moves.
Not re-tested live after these changes: the pasted key was cleared by the server restart.

## 20. Sign-in and welcome, walking habit, research for cardio and nutrition (23 November 2026)

**Sign-in pictures:** the dots are now real controls (hidden radio buttons inside labels, chosen with CSS
`:has(:checked)`, no JavaScript). Tapping one shows that picture and stops the 6-second timer. Checked at laptop width.
**Welcome screen (phone):** picture lower, "Build your own" with a shining purple word that changes (strength, routine,
pace, skills, plan), the text centred, and Get started at the bottom with a soft glow every few seconds. All of the
motion stops for people who ask their phone for reduced motion.
**FitBuddy walking habit:** choose steps a day (off, 5,000 to 12,000) and walking days a week; the hint gives the
range where studies saw most of the benefit (steps-mortality). "Put these days on my week" adds that many walks.
**Pasting a key:** the box now says to use only a free-tier key you can delete, and that everything else works
without AI, so someone who doesn't trust it can simply leave it.

**Researched, not built:**
- *Treadmill intervals on a phone:* the Screen Wake Lock API (which keeps the screen on) works in Safari from iOS
  16.4, fully from 18.4, but is unreliable in home-screen web apps, and it can't keep a timer running once the phone
  is locked. A web page also can't promise countdown sounds with the screen off, and a sound can briefly duck music.
  An interval guide is possible while the screen stays on; a locked-phone coach is a job for a native app.
- *Nutrition:* reviews link food self-monitoring with weight loss, but the evidence is low quality (Burke 2011;
  Raber 2021), and a 2026 app study found more frequent tracking went with more loss (observational). The leading
  apps compete on database accuracy (Cronometer), adaptive targets (MacroFactor), and fast logging (barcode, photo).

## 21. Walking habit, nutrition kept simple, pop-up navigation (23 November 2026)

**Walking habit:** set in Plan my week (steps a day and which days) or from FitBuddy. It sits on top of whatever the
day holds, so a day can be a workout, a skill practice and a walk; the week shows "Upper body + Push-up practice +
10k walk", walk-only days get their own row, and Home shows today's walk to tick off. A logged walk counts toward the
week's flames but doesn't tick off that day's workout. Treadmill intervals and walking games are paused, as agreed.
**Nutrition, simple on purpose:** protein only, no calorie counting (calories can be a sensitive subject, and accurate
calorie tracking needs a large food database). New: save today's foods as a meal and log it in one tap; the AI meal
idea comes back as name, ingredients, steps and estimated protein, and can be logged for today or saved to your meals.
Every number says it's an estimate.
**Fixed:** buttons inside pop-ups that change page (Go to Home, Start it now, Done, Do this again now) didn't navigate,
because `st.switch_page` doesn't take effect inside `st.dialog`. `ui.go()` now asks homepage.py to switch at the start
of the next full run, and `ui.to_workout` uses it.

## 22. Pre-commit checks: fresh copy, Google sign-in wiring, security, privacy wording (23 November 2026)

**Fresh copy, as a developer would get it:** only the files git would commit, copied to an empty folder (no `.env`,
no secrets file, no database). All tests pass there; the app starts with no settings, opens the welcome screen with no
sign-in, and every page (Home, Workouts, Library, Skills, You, Progress, Exercise library, Nutrition, FitBuddy) opens
with no errors. (The test reused the existing Python environment and exercise list, so `pip install` and the first
exercise download weren't re-run.) One warning found and fixed: two controls on You were given a default while the
app also restored their value.

**Google sign-in wiring:** with test keys in the copy only, the app switches to Google mode on its own, shows Continue
with Google, and sends the browser to accounts.google.com with the app's client ID; Google rejected the fake ID, as
expected. A real sign-in and saving to Drive still need the owner's real Google setup (DEPLOY.md).

**Privacy wording:** "saved in a private app folder in your own Google Drive" sounded like a file anyone with a link
could open. It now says the workouts stay in a hidden space in your own Google account that only BodySync can open,
with no link and nothing to share. "How your data is kept" opens PRIVACY.md inside the app (it used to link to the
teammates' GitHub, which a fork wouldn't match). PRIVACY.md now covers saved meals, custom exercise photos, and what
the AI features send to Google.

**Security pass:**
- Secrets: none in any file or in git history; `.env`, `.streamlit/secrets.toml` and `data/` are git-ignored.
- Forks and public copies: a fork gets code only; a public copy without Google sign-in refuses to open.
- Private data: each signed-in person's data is a private app-data file in their own Google account.
- Names people type are escaped before they go into HTML, and `st.html` strips scripts as a second layer.
- SQL passes values as parameters; uploads are limited to 10 MB and photos are shrunk before saving.
- JavaScript runs in only two fixed places (the rest chime and scroll-to-top) and never includes user text.
- New: AI answers are shown without Markdown images or hidden links (`ui.no_media`), so an odd AI answer can't make
  the browser load something from another site.
- Checked and left as is: a meal or exercise name someone writes for themselves is only shown to them.
- Not done: an automated scan of the Python packages for known vulnerabilities (`pip-audit`); it would mean
  installing a new tool, so it's left for the owner to approve.
- DEPLOY.md no longer states as fact how Google classifies the Drive app-data scope (unconfirmed); it says to check
  the Data Access page, to start in Testing with family as test users, and to link the fork's own PRIVACY.md.

**Wording, revised again:** "a hidden space only BodySync can open" read as if the people behind BodySync could open it. The sign-in note now speaks from the person's side, the way apps usually do: "Your workouts are saved to your own Google account. Only you can see them, when you're signed in. Not us, and not anyone with a link. You can delete them any time."

## 23. "What this works and why": goal clarity (24 November 2026)

**The owner's question:** "If I want abs, is my ab workout actually giving me abs, or am I doing random moves?" Same
for slim triceps, hip flexibility, and feeling stuck after a few weeks. Until now a workout cited research facts in
"Why it works", but no move said what it trains or why it belongs in the workout.

### Research first (all abstracts read on 24 November 2026 through Europe PMC or the journal's own page)

| Question | What the evidence says | Entry in `research.json` |
|---|---|---|
| Can ab moves burn belly fat? | No. Six weeks of ab exercises alone did not change belly fat or waist size (Vispute 2011). A meta-analysis of 13 studies, 1,158 people, found training one area did not reduce fat there (pooled effect -0.03, 95% CI -0.10 to 0.05; Ramirez-Campillo 2021). | `no-spot-reduction`, `spot-reduction-meta` |
| Which moves work which core muscle? | A review of 67 EMG studies (1,247 adults): free-weight lifts such as squats and deadlifts drew the most activity from the six-pack muscle (rectus abdominis), outer obliques and lower-back muscles; core-stability moves such as planks drew the most from the inner obliques. The deepest layer (transverse abdominis) has been little studied, and EMG methods differ between studies, so this is muscle activity, not proof of growth. | `core-emg-review` |
| "Toning" vs size | Light and heavy weights grew muscle similarly when sets went close to failure; heavy loads gave more maximal strength (21 studies, Schoenfeld 2017). So "toning" is building muscle plus losing fat overall; there is no separate toning rep range. | `load-spectrum` |
| Triceps | In 21 untrained adults, overhead cable extensions grew the triceps about 1.4 times more than arms-down extensions over 12 weeks (whole triceps +19.9% vs +13.9%; long head +28.5% vs +19.6%), with lighter loads. Cable only, untrained people. | `triceps-overhead` |
| Biceps heads | No primary source checked for head-by-head claims. The app only says which muscle a curl works (from the exercise database), not which head. | none (left out on purpose) |
| Glutes | Hip thrusts and back squats grew the glutes similarly over 9 weeks (34 untrained adults, MRI); squats also grew the thighs more. Higher glute EMG in the hip thrust did not predict more growth. | `glutes-thrust-squat` |
| Hip mobility | Total weekly stretching time matters (at least about 5 min per muscle a week) and holds of 10 to 30 s (already in the file). Full-range strength training improved range of motion as much as stretching in 11 trials, 452 people, with very mixed study designs. | `stretch-weekly`, `stretch-hold`, `strength-rom` |
| How long before change? | Strength rises first: neural factors contribute most early on, but growth starts from the beginning too (Folland 2007). Muscle size was measurable by scan after 3 weeks (quadriceps +3.5 to 5.2%), +6.5 to 7.4% by 5 weeks (7 people, Seynnes 2007): real, but too small to see in a mirror. The growth studies above ran 9 to 12 weeks. The app says "strength in the first weeks, give size 9 to 12 weeks", which is what these studies support. The common "6 to 12 weeks" line had no single source, so it isn't used. | `strength-early`, `size-timeline` |
| Feeling stuck: sleep | A systematic review (17 studies, quality moderate to weak): several nights of short sleep reduced strength on multi-joint lifts, not single-joint ones; one night without sleep did little. | `sleep-strength` |
| Feeling stuck: what else to check | Training each muscle twice a week (`frequency-2x`), enough weekly sets (`volume-hypertrophy`), adding weight or reps over time (`progression-top-of-range`, `reps-or-load`), protein up to about 1.6 g per kg a day (`protein-1-6`), and habits that survive missed days (`habit-consistency`). | existing entries |

Not used: claims that oblique work "thickens the waist", that a given curl targets one biceps head, and that some
moves "tone" while others "bulk". No primary source was checked for any of them.

### Design

1. **Every move says what it works and its job.** New file `move_targets.json` maps each of the 84 moves used in
   curated workouts to an `area` (the muscle group, from the Free Exercise DB's primary muscles, in plain words) and
   a `job` (what the move does, for example Dead Bug: "Deep core. Keeps your lower back down while your arms and
   legs move (anti-extension)."). A move whose job rests on a study names it (`research`), for example overhead
   triceps work cites `triceps-overhead`. One file, not one copy per workout, so a move reads the same everywhere,
   and the set screen works for any workout that uses a known move (playlists too).
2. **Shown where people look, nothing hidden.** Workout preview: each row gets a third line, "Works: deep core.
   Keeps your lower back down...". Set screen: one line under the set count, "Works: deep core", and the job as a
   caption below the inputs. No expanders or popovers.
3. **"For your goal" on every curated workout.** Each workout names a `for_goal` (abs, core, arms, glutes, hips,
   muscle, strength, knees, skill, fitness). The note says what the workout can and can't do, in plain words, with
   the research links, and when to expect change. Abs, for example: core moves build strength; whether abs show
   depends on the fat over them, which comes from moving more and eating a bit less, so pair it with walking and
   protein. A workout can add its own `goal_tip` when it's missing something, for example Biceps and triceps (gym)
   has no overhead triceps move, so the tip says to swap one in.
4. **"Feeling stuck?" on Progress.** Shown when someone has logged for at least 28 days, trained in the last 28
   days, and set no personal record in those 28 days. It never blames: it says plateaus are normal, then shows their
   own numbers next to what to check (days a week in the last 4 weeks vs 2 a week per muscle; whether the top
   lift moved; sleep; protein, with a link to Nutrition). Each line links its source.
5. **Rules stay plain:** `targets.py` has no Streamlit, so tests can check that every curated move has a target,
   every cited id is verified, every workout's goal note exists, and the stuck check fires only when it should.

### Built and checked (24 November 2026)

Built as designed: `move_targets.json` (84 moves, 12 goal notes), `targets.py`, `for_goal` on all 31 curated
workouts (`goal_tip` on Biceps and triceps), the preview's "Works:" lines and "For your goal" section (its sources
join "Why it works"), "Works:" plus "Why this move" on the set screen, and "Feeling stuck?" on Progress with a
button to Nutrition. Checked on a 375 px phone with a test profile (seeded with 6 weeks of flat curls and push-ups):
preview and goal note in light mode, set screen in dark mode, Feeling stuck? with real numbers. Wording fixed after
that look: removed "that happens to almost everyone" (no source) and "before blaming the plan" (the helper never
blames); the most-done move now breaks ties by sets, so a weighted lift wins over push-ups. Not checked: tablet and
laptop widths, and Progress in dark mode.
