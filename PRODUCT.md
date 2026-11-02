# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two groups who are really one path. Learners and interview-preppers who practise on their own and want an honest rating of where they stand. Competitive programmers who want to prove it against someone else, live. The typical journey is practice, then a rating, then a match: the same person is a learner on Monday and a rival on Friday.

## Product Purpose

CompileX is a competitive-coding arena. A player solves problems in the browser, in Python, C++, Java, JavaScript or C, against a hidden test suite that is graded on the server. They can practise alone, take a skill assessment that sets their starting rating, create or join a lobby by code for a live multiplayer match, or enter a tournament. Success is a player who keeps coming back for the next problem and the next match.

## Positioning

Every problem is generated or drawn from a reviewed pool, so there is nothing to look up and no answer to memorise. The function signature and the input/output harness are locked: players write only the logic. Grading and the hidden tests stay on the server, so a result can be trusted. A complexity analyzer reads the player's own code and gives a time and space answer with a confidence level and an explanation. A neighbouring problem-list site could not truthfully claim all four together.

## Operating Context

Players work in a browser, mostly on a laptop or desktop, in a code editor (Monaco). Matches run on a clock. A lobby has a short code that players share. Results arrive as tests passed out of tests total. Practice and assessment are quieter, single-player sessions. Mobile is for browsing, rankings and results, not for writing code.

## Capabilities and Constraints

Pages that exist: landing, login, register, forgot and reset password, home dashboard, skill assessment, practice, lobby, game (the match), tournaments and tournament detail, profile, match history, about. A leaderboard component and a 3D background component exist. Sign-in is by password or OAuth. The stack is React, Vite, Tailwind, Monaco, and a socket connection for live matches; the redesign keeps behaviour, routes and data exactly as they are and changes presentation only.

## Brand Commitments

The name stays CompileX. The logo is to be redrawn as a new wordmark (confirmed). The footer credit to the two creators, Kabir and Sayan, already on the About page, stays.

## Evidence on Hand

No verified user counts, testimonials, ratings or press. The existing landing page claims such as "Join 10,000+ Active Coders" are placeholders and must not be carried over (confirmed). Real, showable facts: the five supported languages, the practice topics, the difficulty levels, the rating and level system of the skill assessment, and live data from the running app. Any demonstration data on a marketing surface must be labelled as sample.

## Product Principles

1. Practice leads to battle. Every screen points to the next problem or the next match.
2. In a match the editor is the stage. Chrome gets out of the way of the code, the clock and the score.
3. Show the product doing its job: real tests, real complexity analysis, real ratings. Never invent numbers or social proof.
4. Fairness is visible. Locked harness, hidden tests and server grading are features to display, not footnotes.
5. One identity from the first visit to the thousandth match, loud where a visitor decides and exact where a player works.

## Accessibility & Inclusion

No product-specific requirement has been stated. Open decision: the standard to hold the redesign to (contrast, keyboard operation, reduced motion) has not been confirmed with the user.
