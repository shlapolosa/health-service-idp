# Executive Summary

## Overview
The Wellness Gamification initiative enhances Sahatna with engagement loops that encourage sustained participation in healthy lifestyle behaviors. The initiative is designed as a community-driven program, where individuals work toward their personal wellness goals while collectively contributing to broader community outcomes.
Through challenges, points, leaderboards, and rewards, users are motivated not only by their own progress but also by the shared progress of their community or district. Individual participation and consistency contribute to aggregate community wellness scores, reinforcing a sense of collective effort and shared achievement. Rewards are positioned as recognition for both individual commitment and community-wide engagement, encouraging sustained behavior change at scale.
This initiative aligns with DoH’s preventive health strategy by promoting daily movement and strengthening community involvement in wellness.

## Context
Sahatna currently provides users with visibility into selected wellness indicators and allows users to manually set personal wellness goals. While this establishes a foundational level of awareness, the current experience is largely passive.
At present:
Users are not proactively prompted to connect external data sources such as Apple Health or Google Health; discovery of the wellness section and wearable data connection relies on user initiative, which can limit data completeness and engagement.
There are no proactive nudges to encourage users to increase, adjust, or revisit their wellness goals over time.
Changes or trends in wellness indicators (ex, improvement, decline, or stagnation) are not actively surfaced or contextualized for the user.
There are no gamification mechanisms such as challenges, awards, badges, or rewards to motivate goal achievement or sustained engagement.
The Wellness Gamification initiative addresses these gaps by introducing structured engagement mechanisms that transform wellness tracking from a passive experience into an active, motivating, and community-driven journey.

## Opportunity / Expected Outcome
The Wellness Gamification initiative introduces engagement mechanisms that enable:
Sustained participation over time, by converting individual wellness activities into time-bound challenges that encourage repeated engagement rather than one-off usage.
Community-level motivation and accountability, where individual actions contribute to shared outcomes (e.g. district/team wellness scores), reinforcing collective participation.
Positive reinforcement for consistency, through points, progression, and rewards that recognize regular effort instead of peak performance.
Improved activation of wellness features, by proactively surfacing gamification challenges rather than relying on user discovery.
As a result, the initiative is expected to drive:
Higher engagement with wellness features
Greater consistency in meeting personal physical activity goals
Improved adoption of healthy behaviors over time
Stronger uptake of community-based wellness initiatives
Actionable analytics to inform future initiatives

## Scope Summary
Sahatna will act as the user-facing platform for participation, wellness tracking, scoring, and progress visualization. At the back-end, challenges should be easily configurable as DoH will introduce future challenges with varying characteristics that are further explained below.

# Requirements
The requirements sections below highlight business requirements. For more details on the scope of the overall project, please refer to the Appendix.

## Phase 1 Scope
Objective: Launch the first challenge with multiple wellness goals to get data for the initiative including participation rates, engagement and healthy behavior outcomes. This will help refine future challenges targeting the Abu Dhabi population.
Target Audience: The population of Abu Dhabi.
Expected timeline: To be developed by Q3 2026. DoH internal testing for end-to-end features must be conducted by September 1st and the public challenge needs to go live by September 28th, 2026.
User journeys: User journeys have been visualized on this miro board: https://miro.com/app/board/uXjVP8Bds2Y=/?share_link_id=828004339568
ID
Requirement Description
Priority (H/M/L)
Additional Details
1
User should be able to enroll into an active challenge and clearly understand its duration and participation criteria.
H
Enrollment for eligible users is opt-in.
Phase 1 only has individual-based challenges.
2a
DoH should be able to set specific target goals for wellness metrics.
H
Users should not be able to edit the set goals for the duration of the challenge.
2b
DoH should be able to set segment-based goals.
M
Segment-based goals based on age, gender, or conditions.
3a
Multiple challenges can be created from back-end targeting audiences with separate goal thresholds
H
Only users within a defined target audience for a challenge will be able to see that challenge. For Phase 1, we can target by age, gender or conditions.
Users eligible for multiple challenges can participate in multiple challenges at the same time.
3b
Challenges can be created for specific whitelisted audiences
M
Only users who are whitelisted from back-end will be able to see the challenge and participate in it
4
User should be able to send in a request to DoH for a challenge via Sahatna
M
This will launch a link with a form that needs to be filled in by the user (could be a web link)
5
User should earn wellness score for completing daily targets during an active challenge.
H
Scoring is based on completion of defined thresholds for all wellness metrics available in Phase 1. (refer to ‘goals’ section for details)
6
User should receive additional recognition for consistent participation across multiple days.
H
Track number of times user met goals in a week and send weekly summary notifications.
7
User should be able to view their wellness score, daily goals progress and their weekly streak progress.
H
Show user their overall wellness score and their daily goals progress.
Show user a ‘streak builder’ component on the UI that tracks progress for the week.
8
User should be able to see their relative position among other participants in the same challenge.
M
Individual leaderboards will be limited to defined cohorts and presented in a privacy-safe manner.
9
User should be able to get additional score if they sign up for specific events on Sahatna
M
DoH should be able to mark some events separately that will reward gamification points if user signs up.
10
User should be able to get additional score if they check-in at the events they signed up for
M
This will use the existing check-in module of Sahatna
11
User should receive reminders and nudges related to challenge participation and progress.
H
Push notification depends on user consent and will address the user by name.Email will be sent to users for whom we have email addresses and consent to receiving emails.
12
User should be able to see if they won or not at the end of the challenge and what their overall score was.
H
Users should be notified if they won or not.The challenge details page can also show winners information.
13
DoH should be able to view a dashboard with challenge-level participation and engagement metrics.
H
Metrics include participation rate, consistency, challenge completion, and retention trends.
These metrics will be segmented by districts and user demographics.
14
DoH should be able to configure challenges on the back-end.
H
The configuration does not need to have a dedicated self-serve UI, but it should be easy to create new challenges without needing new code from the technical team.
15
User should earn badges for meeting pre-set criteria
M
Based on existing data and wellness metrics only.
16
User should be able to see what badges they have earned, and what they can potentially earn on a dedicated screen
M
Show progress on unattained badges
17
User should be able to share a badge they earned with other users
M
Pre-populate text for the badge and trigger native phone share function
18
User should be able to accumulate spendable points from their progress in wellness challenges
H
These points are different from the wellness score. These points are available for redeeming rewards and do not reset on conclusion of challenge.We should be able to set in back-end if a challenge will earn points for users or not.
This should be feature flagged as for the challenge in September 2026, we may not have officially launched reward points.
19
User should be able to view potential rewards within Sahatna
H
DoH should be able to add digitally redeemable rewards from the back-end.This does not need to be self-serve, but it should be easy to add, remove, edit options without needing additional development.
This should be feature flagged as for the challenge in September 2026, we may not have officially launched reward points and rewards.
20
User should be able to redeem rewards using their points
H
Rewards could be coupons, codes that can be redeemed digitally or at stores.
This should be feature flagged as for the challenge in September 2026, we may not have officially launched reward points and rewards.

## Phase 2 Scope
ID
Requirement Description
Priority (H/M/L)
Additional Details
1
Extend the types of goals that are set for users in challenges to other available wellness parameters in Sahatna
H
This can include Health age, sleep scores etc.
Additional segments for setting goals are possible: Whitelisted audience, accessibility flag
2
Integrate with citymoov AD app and reward extra points for users that complete quests on it
H
This is dependent on citymoov app developers and agreement to connect via APIs
3
Sahatna should be able to identify an individual’s baseline for quantified wellness metrics
H
Need to identify the logic for how the baseline is set; this also assumes we will have enough user data to set up a baseline.
4
DoH should be able to set a personalized goal for users based on their baseline
H
If enough data isn’t available for baseline, we should have a backup number for the goal based on user profile data (ex. age, gender).
5
DoH should be able to set a customized and separate type of goal for POD
H
This may not be covered by existing wellness metrics and may require manual logging.
It is possible we divide POD into further categories based on type of challenge and setup unified goals for each type of accessibility challenge.
6
DoH should be able to setup a challenge as team-based
H
A team-based challenge will allow users to participate as individuals or as teams (with cap on size)
Wellness score for teams will be an average of their individual team members wellness scores
7
User should be able to participate in challenges as a team
H
User should be able to identify the members of their team while registering
8
User should be able to invite or remove Sahatna users from their team
H
User should be able to extend an invite over push and email to team members
They should be able to modify their team members (only the creator of the team)
9
Users should be able to see the leaderboard with both individuals and teams
H
The leaderboard will show both types of participants; individuals and teams. Teams should show on UI like a group.
10
User should be able to receive a title for meeting certain pre-set criteria
H
These titles are tied to achieving milestone objectives.
11
User should be able to check other users' profiles on leaderboard and view their earned badges and their title
H
Earned badges and titles should show up for the user along with their current score in the active challenge.

## Phase 3 Scope
ID
Requirement Description
Priority (H/M/L)
Additional Details
1
Introduce a new type of challenge; district-based. This is similar to team-based, but instead users sign up to represent a district
H
A district-based challenge will only have districts competing with each other
User should be select a district to represent when signing up.
Goals may be set separately for separate districts.
2
The leaderboard will be updated for district-based challenges to show a district ranking instead; and within a district the individual rankings
H
A district wellness score will be the average of all its participants
3
DoH should be able to see a heatmap of districts based on their wellness scores and no. of people contributing to it
H
Size of circle will be no. of participants; color will denote how high their wellness score is

## Non-functional Requirements
ID
Category
Requirement Description
Priority (H/M/L)
1
Privacy
Clearly recorded user consent for participation in competition and agreement with its conditions (ex. sharing name on leaderboard)
H
2
Performance
Real-time refresh of individual score and leaderboards
H
3
Scalability
Support thousands of concurrent participants
H

## Open Questions
Question
Involved Stakeholders
Status
How will the rewards be distributed to the winners for the challenge in September 2026?
ADPHC
Open
What are the exact dashboard widgets and metrics we want to track for gamification?
ADPHC/DH
Open

# Phase 1 Milestones
There need to be milestone checkpoints scheduled throughout the development period to ensure alignment across DoH, ADHDS, TAMM, and ADPHC.
Regular demos will allow stakeholders to review progress, validate functionality, and identify critical issues early in the development cycle.
Milestone
Description
Target Completion (to be filled in by ADHDS)
Milestone 1 Demo – Complete Back-end + Enrollment Journey
Demonstration of back-end configuration, challenge listing screens and enrollment journey for users
Milestone 2 Demo – Gamification Elements
Demonstration of progress tracking, goals, streaks, leaderboard and scoring logic
Milestone 3 Demo – Reward Points + Marketplace
Demonstration of reward points accumulation, redemption within Sahatna and reward catalog
Milestone 4 Demo – Badges & Reporting Dashboards
Demonstration of dashboards reports and badge system
UAT Initiation
Readiness for end-to-end testing of the complete user journeys

# Stakeholders
Name
Role
Organization
Responsibility
Faten Naser Khamees Mohamed Albreiki
Specialist Occupational Safety and Health Regulation
ADPHC
Main POC
Emma Helen Gibson
Sr. Analyst, Strategic Planning
HLU
Delivery and Support
Vincenzo Cervadoro
Project Manager – Delivery Assurance
HLU
Delivery and Support
Russell Anas
Program Manager
DH
Technical implementation
Austin Beh
Section Head Digital Product Management
DH
Steerco
Nitin Vereesh Kenkere
Advisor, Community Health
ADPHC
Steerco

# Performance Metrics

## Dashboard (TBD)
The DoH team will need a dashboard with summary level views of live challenges as well as detailed metrics for each challenge. These metrics may include:
Adoption & Engagement Funnel
Number of Sahatna users
Number of users with connected wellness
Number of users who clicked on a challenge banner
Number of users who successfully enrolled in challenge
Number of users who tracked atleast 1 goal in the challenge
Daily and weekly active users in challenge
Current leaderboard rankings and scores
Behavioral Consistency
Number of participants with 2, 3, 4, 5 day streaks per week (week over week)
Average wellness scores
Percentage of users completing full challenge
Participants list sorted by performance on specific wellness metrics (like no. of steps, no. Of mental well being check-ins)
Community Impact
District-wise average wellness scores
Change in score over time
Participants volume over time

# Appendix

## Goals
A goal is a measurable target a participant must achieve within a defined time window during a challenge.
Every goal must specify:
The metric being measured
The required threshold
The time frequency (daily, weekly, one-time)
The verified data source
Goals are assigned at enrollment and remain locked for the duration of the challenge.

### Supported Goal Types
The system must support the following goal categories; however, the goal engine must allow new metric types to be added without redesigning the structure:
Category
Example Target
Should be Available By
Measurement Source
Physical Activity - Steps
8,000 steps/day
Phase 1
Phone/Wearables integration
Physical Activity - Exercise
10 mins/day
Phase 1
Phone/Wearables integration
Sleep - Hours
7 hours/night
Phase 1
Phone/Wearables integration
Sleep Score
75/100 daily
Phase 2
Wearables integration
Mental Wellbeing
1 check-in/day
Phase 1
In-app survey/assessment logging
Mental Wellbeing
Daily Mood Rating (1-5)
Phase 1
In-app survey/assessment logging
Nutrition Wellness
1 check-in/day
Phase 1
In-app survey/assessment logging
Nutrition Wellness
Caloric intake
Phase 1
In-app survey/assessment logging
Screening Metrics
Complete IFHAS screening
Phase 1
Sahatna IFHAS module
Event Participation
Check-in at event
Phase 1
Sahatna events module
External Quest
Complete Citymoov quest
Phase 2
API integration with Citymoov
Accessibility (POD)
Custom logged activity
Phase 2
Manual logging / defined logic

### Goal Frequency
Goals may be:
Daily recurring (e.g., steps per day)
Weekly recurring (e.g., check-in per week)
Weekly cumulative (e.g., 4 times a week)
One-time within challenge (e.g., complete screening once)
Time-bound event goals (valid only within event window)
Daily and Weekly goals close at a defined cutoff time in the day/week.

### Goal Assignment Models
Segment-Based Fixed Goals
A predefined threshold applied uniformly to a defined participant segment.
Threshold varies based on user profile attributes such as:
Age
Gender
Accessibility classification
District
Whitelisted audience
Segment evaluation occurs at enrollment only.
Baseline-Based Personalized Goals
The system may calculate a user-specific threshold based on historical data for quantified wellness metrics captured in Sahatna.
Baseline requirements:
Minimum historical data window
Outlier filtering
Defined uplift logic (e.g., +15% improvement)
If insufficient data exists, a fallback segment-based threshold is assigned.
Personalized thresholds are calculated once at enrollment and remain fixed.
Accessibility (POD) Goals
Accessibility goals may:
Use different thresholds
Rely on manual input instead of device data (ex. log your activity manually)

### Goal Locking
Once a user enrolls:
Goal thresholds are stored.
Users cannot edit or override goals.
Threshold logic does not recalculate mid-challenge.
Goal definitions cannot change for active participants.

### Goal Visibility (User Experience)
Users must clearly see:
The target threshold
The time window
Their real-time progress toward the goal
For multi-metric challenges, each goal is displayed independently. The system must clearly indicate whether a goal has been met for that time period.
If personalized, the UI should indicate that the goal was calculated based on past activity without exposing calculation formulas.

### Phase 1 Goals
Category
Target
Frequency
Segment
Physical Activity - Steps
7,000
Daily
All the population
Mental Wellbeing Survey Check-in
1
Daily
All the population
Sleep - Hours
>=7 hours
Daily
All the population
Nutrition Survey Check-in
1
Daily
All the population

## Scoring
Wellness Score is the numeric value assigned to a participant based on performance against challenge goals.
It:
It is calculated only within the context of an active challenge.
Calculated weekly and capped at a maximum of 100 per week.
Resets at the start of every new challenge.
Determines leaderboard ranking.
Determines challenge winners.
Is used for individual, team, and district aggregation.
There is one scoring logic across that applies uniformly to all participants in that challenge.

### Weekly Score Structure (1-100 Range)
Each challenge week has a maximum possible score of 100.
All scoring components within that week, including goal completion and any consistency bonuses, must collectively sum to 100.
The distribution of score across goals is defined per challenge, but the total weekly maximum must always equal 100.
Example distribution (illustrative only):
Physical activity goal: 40 score/week
Sleep goal: 30 score/week
Mental wellbeing goal: 20 score/week
Consistency bonus: 10 score/week
Total = 100
No participant may exceed 100 in any given week.

### Individual Weekly Score Calculation
Within a week:
Each goal contributes to a predefined portion of the 100-score structure.
Score is awarded based on the configured scoring logic (e.g., threshold met).
If multiple goals exist, their weighted contributions determine the total.
The weekly score equals the total score earned from all eligible scoring components, up to a maximum of 100.
If a participant does not meet any goals in a week, their weekly score is 0.
Weekly scores become final once the week closes.

### Final Challenge Score Calculation
For challenges spanning multiple weeks:
Final Wellness Score = Average of all completed weekly scores.
Example:
Week 1: 82
Week 2: 95
Week 3: 76
Final Score = (82 + 95 + 76) / 3 = 84.33
Each week carries equal weight in the final calculation.
If the challenge includes partial weeks, the partial week is treated as a full week and the score is extrapolated, so it is out of 100.
In case of late enrollment, averaging begins from enrollment week only.
These rules must be consistent for all participants in that challenge.

### Consistency-Based Score Allocation (Streaks)
Consistency bonuses are embedded within the 100-score weekly structure.
Scoring:
Specific score allocation for meeting goals 4,5 and 7 days out of a full week.
The bonus forms part of the 100 total.
The system must prevent total weekly score from exceeding 100.
Consistency scoring influences the weekly total but does not create additional uncapped score.

### Team Score Calculation
In team-based challenges:
Each participant has a Wellness Score (derived from weekly averages).
Team Score = Average of Wellness Scores of all team members.
Rules:
All registered team members are included in the calculation.
Score updates dynamically as individual weekly averages update.
Teams are ranked strictly by Team Score.
If a member is added or removed, the average score calculation from that point onwards is updated to reflect the change in member count.

### District Score Calculation
In district-based challenges:
Each participant contributes their Wellness Score to a district they assign themselves to when joining a challenge.
District Score = Average of Wellness cores of all participating users within that district.
Additional considerations:
Each user is associated with only one district per challenge.
District ranking is based solely on district score.
Participants cannot change their district later in the middle of the challenge.

### Real-Time Updates & Finalization
During the challenge:
Weekly total score updates dynamically as goals are met.
At week close, the Wellness Score is updated with the week’s contribution.
At challenge end:
Final Wellness Scores are calculated.
Scores are locked and rankings are finalized.
Tie-breaking logic is applied.
No further updates are permitted after finalization.

### Tie-Breaking Rules
If two participants (or teams/districts) have identical Final Wellness Scores, tie-breaking rules must be followed.
Tie-breakers may include:
Greater number of weeks above a defined threshold.
Lower variance across weeks (greater consistency).
Tie-breaking logic must be predefined and consistent across the challenge.

### Score Visibility & User Experience
The scoring experience must clearly communicate two distinct values:
Weekly Score: performance for the current week
Wellness Score: overall challenge performance (average of completed weeks)
The UI must ensure users understand that these are related but different metrics.
Weekly Score Display
The Weekly Score represents progress for the current week only.
The interface must show:
Current Weekly Score (e.g., 72/100)
A clear visual progress indicator toward 100
Time remaining in the week
This score updates dynamically as goals are achieved.
Contribution Transparency
For challenges with multiple goals contributing to the weekly 100:
Users should be able to see how each goal contributes to their Weekly Score.
The UI should indicate which components are completed and which are still pending.
Week Closure & Finality
When a week ends:
The Weekly Score is reset.
The Wellness Score recalculates to reflect the updated average.
Users should ideally see some UI indication that shows their completed weekly score has contributed to their Overall Wellness Score.
When the challenge ends:
The final Wellness Score must be presented prominently.
The overall score should feel definitive and complete.

### Score Validation
The scoring engine must:
Prevent duplicate score allocation within the same time window.
Handle late device synchronization within defined limits (when a wearable might sync data later due to some issue).
Log every score update with timestamp and source reference.
Ensure team or district membership changes do not retroactively alter finalized weekly scores.
Every weekly score must be traceable to underlying goal performance data for auditability.

### Phase 1 Scoring
Phase 1 September Challenge
Outcome
Consistency
Max 100 scr
Daily steps
Balanced Day
% of goal
scr
≥100% steps
3
10-29%
1
≥7h sleep
30-49%
2
mental health check-in
50-79%
3
nutrition check-in
80-99%
4
>= 100%
5
Mental Health
Nutrition
Check-in
scr
Check-in
scr
No check in
0
No check in
0
completed
1
completed
1
Sleep
Consistent Engagement
Duration
scr
Bronze 4/7
5
<6h
0
Silver 6/7
11
6–7h
1
Gold 7/7
16
≥7h
2
Total Weekly
100

## Challenge Configuration
This section defines the parameters that must be configurable per challenge. These configurations may be managed via internal tools, scripts, or deployment workflows, but the system must not require code changes for each new challenge.

### Challenge Request Submission
Challenge ideas may originate from both internal DoH teams and Sahatna users. A structured submission process must be provided to collect and review these requests.
Internal Challenge Requests
DoH teams should be able to submit challenge proposals through an internal request form.
The form will be accessible to authorized DoH staff.
The form will capture the required information for challenge evaluation and configuration (fields defined separately in upcoming section).
Submitted requests will be reviewed by the Gamification program team before being approved for implementation.
Approved requests will be shared with ADHDS for configuration and go-live.
User-Initiated Challenge Requests
Sahatna users should be able to suggest challenge ideas through the application.
A link within the Sahatna app will allow users to open a web-based challenge request form.
The form will collect user suggestions for new challenges.
Submitted requests will be reviewed by the Sahatna program team for feasibility and alignment with program objectives.
User-submitted challenge requests are suggestions only and do not guarantee that a challenge will be created.
Review and Evaluation
All submitted challenge requests will undergo internal review to determine:
Alignment with program goals
Feasibility of implementation
Data and tracking requirements
Target audience suitability

### Challenge Structure & Lifecycle
Each challenge can be configured based on the following parameters:
Challenge type (Individual / Team-based / District-based)
Published date and time
Start date and time
End date and time
Target audience
Age, Gender or Conditions (ex. Diabetes)
Type of goals assigned to users
Description of challenge (this can include images, and partner logos)
Description of reward and redemption method
If redemption is offline, then messaging in challenge details to reflect the method
If redemption is via points/catalog, then access to the rewards catalog and messaging around points accumulation
Hybrid is possible as well where there is both offline redemption (for instance, a grand prize for top performer) + reward points for the catalog
Winning criteria
Enabled push/email notification types (details in Nudges section below)
Additionally, for team-based challenges:
Maximum team size must be configurable.
Participation mode must be configurable (team-only vs individual-or-team).
Additionally, for district-based challenges:
District affiliation method must be configurable (user-address-derived vs user-selected).
Manual district reassignment for users from back-end

### Winning Criteria & Reward Mapping
The system should support flexible configuration of winning criteria for wellness challenges and should allow us to define the rewards mapped to those criteria.
Criteria can be applied individually or in combination to determine winners across different challenge formats.
The following criteria must be supported, but should be extensible later to add other types of criteria:
Criteria
Description
Highest Challenge Score (Primary Ranking)
Winners determined based on highest challenge scores over the full challenge duration. (ex. top 1, 2, 5 rankers. Exact number to be configurable)
Most Balanced Days
Winners determined based on highest number of balanced days (achieves ALL goals) over the full challenge duration (ex. Top 1, 2, 5 rankers. Exact number to be configurable)
Wellness pillars champion
User completes a specific goal type the most number of days over the full challenge duration (ex. Top 1,2, 5 rankers. Exact number to be configurable)
Consistent Engagement Criteria
Winners determined or qualified based on consecutive-day progress in at least 1 goal (minimum of 1 progress bar needed to qualify). (ex. 30, 60, 90 days. Exact number of days to be configurable)
Wellness Score Maintenance Criteria
Winner determined on maintaining more than X challenge score (ex. 80+) by the end of the challenge. Exact score threshold to be configurable.
Criteria can be applied for specific cohorts. Ex. Pick top 5 rankers each for each gender. The possible cohorts are:
Age
Gender
PoD (when PoD flags are supported in Malaffi)
District (when district-based challenges go live)
The types of rewards possible are:
Offline rewards (ex. automobiles, electronics, goodie bags)
Reward points (ex. 10,000 points, 20,000 points)

### Eligibility & Audience Targeting
The challenge engine must support configurable eligibility rules per challenge, including:
Age range
Gender
Conditions
District (when district-based challenges are live)
Accessibility classification (when PoD flags are supported in Malaffi)
Whitelisted audience
Challenge visibility is based on user profile data matching the eligibility criteria of a challenge. (ex. If a challenge is targeting females only, only females should be able to see the challenge and be able to enroll into it)
Profile changes during an active challenge must not retroactively alter eligibility.
The system must support running multiple challenges concurrently, each with distinct eligibility criteria.
A user should be able to join multiple challenges and have respective goals setup for each of those challenges.

### Goal Assignment Mode
Each challenge must specify:
Which goal categories are included
The goal assignment strategy (segment-based / baseline-personalized)
Whether a goal will contribute to the weekly score or will only reward points
Whether accessibility-specific goals apply

### Additional Goal Types (Quests, Events & Screenings)
These goal types will not contribute to weekly scores but will reward points (reward points discussed in detail in a dedicated section later below).
The system must support configurable flags for these additional goals per challenge.
Citymoov Quest Integration
If enabled, we must define:
Maximum number of Citymoov quests that will reward points
Number of rewarded points for successful completion of every instance of this goal.
Whether specific quest categories are eligible (if provided by Citymoov API).
Event Participation (Within Sahatna)
If enabled, we must define:
Which events within Sahatna are eligible for the challenge.
Whether eligibility applies to:
Event sign-up
Event check-in
Both
How many points each eligible event will reward for:
Sign-up
Check-in
Event eligibility must be defined at challenge creation and must not automatically include new events unless explicitly configured.
If an event is canceled or removed later from Sahatna, its points contribution should be preserved.
Screening (IFHAS)
If enabled, we must define:
How many instances of the screening will reward points
How many points to reward for each instance
Only IFHAS screenings done during the course of the specific challenge will reward the points.

### Communication Enablement
Per challenge, the system must support enabling or disabling:
Push notification support
Email notification support
Per challenge, the system must allow configuration of nudge types (exact nudge types are defined in dedicated Nudges section).
Nudges must respect individual user consent settings.

### Governance & Operational Controls
The system must support:
Early termination with score freeze
Manual participant removal
Manual participant district update
Archival of completed challenges
All structural changes must be logged with timestamp and actor reference.

## Enrollment, Conclusion & Disenrollment
This section outlines how users discover, enroll in, and exit wellness challenges within Sahatna.

### Challenge Discovery
Currently enrolled and new challenges must be visible:
As a banner or featured section on the main Sahatna dashboard.
Within the Wellness module.
Completed challenges must move to a historical section.
Each challenge card must display:
Challenge type (Individual / Team / District)
Challenge description
Goals being tracked
Duration
Rewards description and redemption method
Enrollment status
Users must be able to view full details by tapping into a card before enrolling.

### General Enrollment Flow
Enrollment is strictly opt-in.
Before confirming enrollment, the user must:
Review duration and participation structure.
View a summary of goals.
Review leaderboard visibility rules.
Provide consent for either displaying their name or only their initials.
Validate their contact info and email address
Connect their wellness data if they haven’t yet to Sahatna.
Upon confirmation:
The user is assigned to the challenge.
Eligibility and configuration parameters are snapshotted.
A user may participate in multiple challenges at a time.

### Team-Based Enrollment
When enrolling in a team-based challenge, the flow adapts.
The system must support the following enrollment paths:
Create a Team
A user may:
Create a new team.
Assign a team name.
Become the team creator (team owner).
The team creator:
Can invite other users via push/email.
This will send a unique link that the potential team member can click to open Sahatna and be taken to the challenge enrollment page with pre-populated team joining details
The push/email will also contain a unique code that they can enter when enrolling into a challenge and electing to join a team
Can remove team members.
Must adhere to team size cap.
The team becomes active as soon as it has at least 1 member (including the creator) actively enrolled in the challenge.
Join an Existing Team
A user can join an existing team that they have been invited to:
The user can search for a pending team invite via a code
The system must prevent joining teams that have reached the maximum size.
Participate Individually
If the challenge allows both team and individual participation:
The user must explicitly select their participation mode during enrollment.
Once the challenge begins, switching between individual and team participation must not be allowed.
Team Enrollment Constraints
A user cannot belong to more than one team within the same challenge.
Leaving a team mid-challenge must follow defined score handling rules from the Scoring section (ex. freeze prior contribution).
The enrollment flow must clearly explain:
That team score is derived from all the members’ performance.
That team performance impacts leaderboard ranking.

### District-Based Enrollment
For district-based challenges, enrollment must assign the user to represent a district.
The system must support:
District Derived from Profile
If district location data exists in the user address book:
The district must be displayed during enrollment.
The user must confirm district representation.
The user can select another district if the derived district is incorrect.
District Selection During Enrollment
If user selection is required:
The system must display a list of eligible districts.
The user must explicitly select one district before confirming enrollment.
Selection must be confirmed and locked.
District Enrollment Constraints
A user may represent only one district per challenge.
Switching districts mid-challenge must not be allowed.
If the user leaves the challenge, their district contribution must freeze.
The enrollment screen must clearly communicate:
That districts compete against each other.
That district ranking is based on aggregated participant performance.

### Challenge Conclusion
If a user remains enrolled in a challenge until its scheduled conclusion:
The challenge should transition to a Completed state.
There should be an indication that challenge data is being reviewed, and winners will be announced shortly.
Following challenge completion:
The DoH team should review the challenge reporting dashboard to retrieve the list of winners based on the winning criteria configured for the challenge.
DoH team will have an option to ‘confirm’ the winners list on the dashboard.
If the list is not approved and requires tweaks, DoH shall share the required updates with ADHDS and the winner list should be adjusted prior to confirmation.
Once winners are confirmed:
The challenge details page should be updated with challenge conclusion information including:
Overall challenge statistics
Summary of participation outcomes
Next steps or upcoming challenges teaser
(Optional) The list of winners including winner names and associated rewards.
Participants should receive a challenge completion notification:
Notification content should vary depending on whether the user won a reward or not.
Users should be able to tap the notification to view the challenge conclusion announcement and winners list.
Reward Distribution
For users identified as winners:
Winners should receive communication regarding reward collection via push and email.
The challenge details page should be updated with winner information.
Reward fulfillment will follow the following approach:
If reward redemption method for the challenge involves offline reward:
The DoH gamification team retrieves the user’s email or phone number from reporting dashboard and contacts the user with reward redemption instructions.
The challenge conclusion information should mention winners will be contacted by DoH team.
If reward redemption method for the challenge involves points:
The reward points are credited on a weekly basis based on the user performance
If there are reward points allocated to a winning criteria for the challenge, then those reward points to be added to the wallet of winners

### Disenrollment (Leaving a Challenge)
Users must be able to leave a challenge subject to defined rules:
The user must confirm exit.
The user must be removed from active ranking.
Historical participation must remain archived.
For team challenges:
If a user leaves, their removal must update team composition.
Score handling must follow integrity rules (defined in Scoring).
For district challenges:
Leaving must remove the user from district aggregation moving forward.
Historical score contribution handling must remain consistent.
Upon leaving:
The user should not be allowed to re-join a challenge they have left.

### User Experience
Users must always understand:
Whether they are participating individually, as part of a team, or representing a district.
That they may have multiple challenges active at a time and be able to navigate across them
That they may have multiple goals, scoring, leaderboard due to multiple challenges
When a challenge has concluded and where to view the final results and winners list.

## Streaks
The Streak feature represents the number of days within a week that a user successfully meets their defined daily goal criteria.
The streak resets at the beginning of every new week.
Streak performance contributes additional points toward the Weekly Score (as defined in the Scoring section).

### Daily Success Condition
A “successful day” is defined as a day where the participant meets one of the configured daily goal criteria for that challenge.
This means:
Meeting a minimum threshold of 1 type of goal for the day
The definition of a successful day must be consistent across all participants in the challenge.
Daily success must only be evaluated after the day closes.

### Weekly Streak Counter
Within each week:
The system tracks the number of successful days.
The counter increments by 1 for each successful day.
The maximum value is capped at the number of days in the week (typically 7).
The streak counter resets to 0 at the start of each new week.
There is no carryover across weeks.

### End-of-Week Evaluation
At week closure:
The total number of successful days is finalized.
The corresponding streak bonus is calculated.
Weekly Score is finalized (handled in Scoring).

### Edge Cases
The system must handle:
Mid-week enrollment (streak tracking begins from enrollment day and shows previous days empty for that week).
Late data submissions (cannot retroactively increase streak after weekly closure).

### Streak Builder User Experience
This feature should feel like a weekly momentum builder, not a pressure mechanic.
Users should immediately see:
How many days they have completed successfully.
How many days remain in the week.
What tier they are progressing toward.
At the start of a new week:
The streak tracker resets visually.
The user is clearly shown that a new weekly streak cycle has begun.
Relationship to Score
The UI must clearly differentiate:
Weekly Score (numeric total out of 100)
Streak Progress (number of successful days that contribute to the weekly score)
The streak is a contributor to Weekly Score, not a separate permanent metric.

## Leaderboard
The leaderboard presents comparative performance within an active challenge. Rankings are based on Final Wellness Score (as defined in Scoring) and reflect the participation structure of the challenge: Individual, Team-based, Hybrid (Individual + Teams), or District-based.

### Core Ranking Logic
All leaderboard positions must be determined using the Wellness Score.
During an active challenge:
Rankings update based on current Wellness Score.
As Wellness Scores get updated weekly based on the week’s performance, the leaderboard also shows updated rankings on a weekly basis.
At challenge completion:
Positions become final.
Tie-breaking rules (defined in Scoring) are applied.

### Individual Leaderboard
Applicable when the challenge type is Individual-only.
The leaderboard must display:
Rank
Participant name or initials
Wellness Score
Highlighted row for current user
Top 3 ranking individuals separately indicated

### Team-Based Leaderboard (Team-Only)
Applicable when the challenge is configured as Team-only.
The leaderboard must display:
Rank
Team name
Team Score (average of member Wellness Scores)
Number of team members
Top 3 ranking teams separately indicated
Users must be able to tap a team to view:
Team members (creator and members)
Each member’s Wellness Score

### Hybrid Leaderboard (Individuals + Teams in One List)
Applicable when the challenge allows users to choose participation as either:
Individual participant
Team participant
In this structure, there is a single unified leaderboard.
The leaderboard must display:
Rank
Entity name (individual name/initials or team name)
Wellness Score (individual score or team score)
A clear label identifying whether the row represents:
An Individual
A Team
Ranking must treat individuals and teams equally; both are ranked based on their respective Wellness Score.
Users participating as part of a team must not appear separately as individuals.
Hybrid Leaderboard User Experience
To avoid confusion:
Each row representing a team must have a visible label or badge such as “Team”.
Team rows may use a visual distinction (e.g., icon, group symbol).
Individual rows should not display the team badge.
The design must ensure users can quickly distinguish between:
A single participant
A group competing collectively
The current user’s row must always be highlighted regardless of whether they are competing individually or as part of a team.
This mirrors best practices seen in community fitness challenges, where groups and individuals coexist but are clearly marked.

### District-Based Leaderboard
District challenges operate differently and require a two-level structure.
District Ranking (Leaderboard)
The leaderboard ranks districts only.
Each row must display:
Rank
District name
District Score (average of participant Wellness Scores)
Number of active participants in the district
Top 3 districts separately indicated
This represents district vs district competition.
Individuals are not displayed at the top level.
District Detail View (Internal Participant List)
When a district is selected:
A ranked list of participants within that district must be shown.
Each participant must display:
Rank within district
Participant name
Wellness Score
This internal list is a simple ranking view and does not mix participants across districts.
Users must clearly understand that:
The outer leaderboard compares districts.
The inner view lists individuals only within that district.

## Badges
Badges represent milestone achievements tied to wellness behaviors, challenge participation, and performance outcomes. They persist across challenges and should be setup in the back-end in a way that it is easy to add additional badges later by the technical team.
The system must support:
Trigger-based awarding
Tiered badges
In-progress tracking
Social sharing

### Initial Badge Set (TBD)
Badge Name
Category
Trigger Type
Tiered
Step Starter
Activity (Steps)
Meet daily step goal once
No
Step Master
Activity (Steps)
Meet step goal 4/5/7 days in a week
Yes
Marathon Week Champion
Activity (Steps)
Meet step goal all 7 days in a week
No
Milestone Achiever
Activity (Steps)
Accumulate 50k, 100k, 150k, 200k steps
Yes
Exercise Starter
Activity (Exercise Minutes)
Meet daily exercise minutes goal once
No
Exercise Master
Activity (Exercise Minutes)
Meet exercise minutes goal 4/5/7 days in a week
Yes
Sleep Starter
Sleep
Meet sleep goal once
No
Sleep Master
Sleep
Meet sleep goal 4/5/7 days in a week
Yes
Rest Champion
Sleep
Perfect sleep completion for 2 full weeks
No
Mindful Starter
Mental Wellbeing
Complete first mental check-in
No
Mindful Master
Mental Wellbeing
Complete 1 check-in every week for 4 weeks
No
Nutrition Starter
Nutrition
Complete first nutrition check-in
No
Nutrition Master
Nutrition
Complete nutrition check-in 4/5/7 days in a week
Yes
Healthy Habits Builder
Multi-Metric
Meet all daily goals 7 days in a week
No
Consistency Champion
Streak
Meet all daily goals every day of a month
Yes
Challenge Participant
Participation
Enroll and complete a challenge
No
Challenge Finisher
Participation
Complete all weeks in a challenge
No
Team Player
Participation
Participate in a team-based challenge
No
District Ambassador
Participation
Participate and compete a district-based challenge
No
Top 10 Finisher
Performance
Rank Top 10 in a challenge
No
Challenge Champion
Performance
Rank #1 in challenge
No
Team Champion
Performance
Member of #1 ranked team
No
District Champion
Performance
Member of #1 ranked district
No

### Badge User Experience
Inspired by Apple Fitness Awards and Strava:
Dedicated Badge Screen
Users must be able to:
View earned badges.
View locked badges.
See progress toward next tier.
Filter by category.
Moment of Achievement
When a badge is earned:
Trigger celebratory visual.
Show badge icon and description.
Explain why it was awarded.
Visual Hierarchy
Higher-tier and performance badges should:
Be visually distinct.
Feel more prestigious.
Be clearly differentiated from entry-level achievements.

## Titles
Titles represent a user’s long-term wellness progression across challenges. They are persistent, cumulative, and reflect sustained participation over time. Only the highest unlocked title is displayed.

### Level Structure
The system must support a configurable level ladder (initially 7 levels), where each level maps to a user-facing title:
Wellness Starter
Wellness Explorer
Wellness Builder
Wellness Achiever
Wellness Champion
Wellness Elite
Wellness Legend

### Progression Criteria Model
Level progression must be based on cumulative lifetime totals:
Total Completed Weeks across all challenges
Total Perfect Weeks across all challenges
The system must track these counters independently and persistently.
Completed Week (for Level Progression)
A Completed Week is counted when all the following conditions are true:
The user is enrolled in an active challenge for that week.
The user receives a finalized Weekly Score for that week (1–100).
A Completed Week is counted as long as the Weekly Score is not 0.
A week is not counted as completed if:
The user disenrolls before the week is finalized, or
The challenge is terminated before week finalization, and no weekly record is produced for that user.
Perfect Week
A Perfect Week is a Completed Week where the user achieves:
A weekly streak outcome of 7 successful days out of 7 (as defined in the Streaks section), within that finalized week.
Perfect Week is strictly based on the streak success-day count, not on Weekly Score.
If the challenge includes multiple daily goals, the daily “success” condition is evaluated based on the configured daily success rule for that challenge (already defined under Streaks).

### Proposed Advancement Thresholds
The system must support thresholds such as:
Wellness Starter: Complete 1 challenge
Wellness Explorer: 4 Completed Weeks
Wellness Builder: 8 Completed Weeks
Wellness Achiever: 12 Completed Weeks + 2 Perfect Weeks
Wellness Champion: 20 Completed Weeks + 5 Perfect Weeks
Wellness Elite: 35 Completed Weeks + 10 Perfect Weeks
Wellness Legend: 50+ Completed Weeks + 20 Perfect Weeks
Notes:
“Complete 1 challenge” means the user remained enrolled through challenge completion and has a finalized challenge outcome record.
All thresholds must be configurable in the back-end (for ex. we should be able to modify Wellness Legend criteria to make it easier or more difficult if needed without needing extensive coding)

### Display Rules
The user’s active title must appear below their display name wherever the name appears in competitive contexts (ex. leaderboard, district participant list) and in the user profile.
Only one title is displayed at a time: the highest level achieved.
Users cannot manually select or downgrade titles.
Users should be able to get more information on the available titles and what needs to be done to achieve them.

### Edge Handling
If a user joins mid-week and remains enrolled through that week’s finalization, that week counts as a Completed Week.
If a user leaves mid-week, that week does not count as completed.
Once a week is finalized, the Completed Week / Perfect Week counters must not change retroactively.

## Nudges (TBD)
Type of Nudge Push/SMS/Email
Messages
Target
Frequency
When
What Clicking/Tapping Does
Push Notfication Sample Content
Challenge initiation
Push/Email
Anouncment of Challenge
All of TAMM users
1
Beginning of challenge
Challenge registration page
A new health and wellness challenge just went live in the Sahatna space! Join today and start earning rewards as you progress.
Push/Email
End of Challenge
All participants of the challenge
1
End of Challenge
Challenge conclusion page
Thank you for participating in the Healthy Living Challenge. Final results are being reviewed and winners will be announced once confirmed.
Push/Email
Anouncement of winners
All participants of the challenge
1
End of Challenge
Challenge winners page
Winners have been finalized for the Health Living Challenge. Tap to view if you won.
Challenge progress
Push
Plan for the week
All Participants
Weekly
Beginning of the week
Personal goals tracking page
Hey Russell, new week starts today for the Health Living challenge. Tap here to view your goals.
Push
Reminders to complete targets
All Participants with any missing goal any day of the week
Weekly
3 days into the week
Personal goals tracking page
Hey Russell, you can improve your score by meeting your daily goals. Tap here to view your progress.
Push
Reminder to uphold performance
All Participants meeting all goals all days of the week
Weekly
3 days into the week
Personal goals tracking page
Hey Russell, great job! Keep meeting your daily goals to maximize your weekly score and reward points.
Push
Review the overall week progress
All Participants
Weekly
End of the week
Week conclusion page
Hey Russell, week 'x' of the Healthy Living Challenge is complete. Tap to view your score and reward points.
Challenge reminder
Push/Email
Reminder of challenge and rewards
All of TAMM users
1
Middle of challenge
Challenge registration page
The Healthy Living challenge in the Sahatna space is in full swing. Join today and start earning rewards as you progress.

## Reward Points
Reward Points are a persistent currency earned through participation in wellness challenges. Unlike Wellness Score, which resets per challenge and determines ranking, Reward Points accumulate over time and can be redeemed in the marketplace.
Reward Points are directly tied to weekly performance.

### Earning Logic
There are three ways reward points can be earned:
Weekly
Reward Points must be awarded automatically based on a finalized Weekly Score.
For each completed week:
Reward Points Earned = Finalized Weekly Score (0–100) * 10
Example:
Week 1 Weekly Score = 100 → 1000 Reward Points earned
Week 2 Weekly Score = 50 → 500 Reward Points earned
Total Reward Points earned from that challenge = 1500; sum of all weekly scores.
This applies across all challenges the user participates in.
Reward Points must be credited only after the week is finalized.
Winner Allocation
A challenge may have a certain amount of reward points allocated to winners based on the winning criteria configured for the challenge.
Examples:
Highest challenge score earns 10,000 points
Highest number of balance days winner earns 50,000 points
Additional Avenues
Bonus points may be earned separately from completing specific types of goals (they do not contribute to weekly scores). We should be able to define which goals reward only points; for now these are the finalized ones (more may be added later):
Screenings (ex. IFHAS)
Event Signup/Checkin
Citymoov Quests
Per challenge, if one of the above goal has been configured, it will reward points as per the configuration.
Examples:
Complete IFHAS screening to get bonus 500 points
Check-in at FOH for bonus 1000 points

### Accumulation Rules
Reward Points:
Accumulate across multiple weeks.
Accumulate across multiple challenges.
Do not reset at challenge end.
Are independent of leaderboard ranking.
Total Reward Point balance must equal: Sum of all finalized Weekly Scores across challenges minus redeemed points

### Wallet Structure
Each user must have a persistent Reward Point wallet.
The wallet must:
Display current balance.
Display total lifetime earned points.
Display total redeemed points.
Show transaction history.
Each weekly reward entry must record:
Week identifier
Challenge identifier
Points credited
Timestamp
The wallet balance must update immediately upon weekly finalization.

### Earning Constraints
Since Reward Points mirror Accumulated Weekly Score:
Users cannot earn more than 100 Reward Points per week per active challenge.

### Redemption Logic
Reward Points may be redeemed in the marketplace.
Redemption must:
Deduct points immediately from wallet.
Prevent redemption if balance is insufficient.
Generate a redemption record.
Issue reward artifact (coupon, code, digital voucher).

### Integrity & Audit
The system must ensure:
Reward Points are credited only once per finalized week.
Retroactive changes to Weekly Score after finalization do not alter Reward Points.
All transactions are logged with traceability.
Manual adjustments (if done manually from back-end) are traced and auditable.

### Reward Points Experience
Users must clearly understand:
“Your weekly performance becomes reward points.” for challenges that reward points
See if challenge is configured to reward additional points to winners
Weekly Score and Reward Points relationship.
Current wallet balance.
Reward Point balance should be visible:
In the Gamification screens within the Wellness Module
In the Rewards Marketplace

## Marketplace
The Marketplace is the in-app redemption platform where users can exchange accumulated Reward Points for available rewards.

### Marketplace Structure
The Marketplace must support:
A browsable catalog of rewards
Clear display of Reward Point cost per item
Reward availability status
Redemption confirmation workflow

### Reward Types Supported
The system must support multiple reward formats.
Digital Voucher / Coupon Code
Unique code
Redeemable online or in-store
Delivered instantly upon redemption
Availability caps
QR-Based Reward
Generated QR code
Scannable at physical location
The system must allow reward items to be added while adhering to the above types without needing additional development.

### Reward Catalog Configuration
Each reward must define:
Reward name
Description
Reward image
Reward Point cost
Validity period
Redemption limit per user
Total inventory limit (if applicable)
Expiry rules (post-redemption validity)

### Inventory Management
The Marketplace must support:
Limited inventory rewards (ex., 500 available)
Unlimited inventory rewards
Real-time inventory decrement on redemption
If inventory reaches zero:
Reward must show “Out of Stock”
Redemption must be disabled

### Redemption Flow
Redemption must follow a clear, multi-step confirmation process:
User selects reward.
System displays reward information
User confirms redemption.
Points are deducted immediately.
Reward is generated and stored.

### Post-Redemption Behavior
After successful redemption:
User receives confirmation screen.
Reward information (code / QR / confirmation number) is displayed.
Reward is stored in a “My Rewards” section.
User can revisit reward details anytime until expiry.

### Redemption Constraints
The system must support:
Maximum redemptions per user per reward.
Maximum redemptions per user per time period.
These constraints must be configurable per reward.

### Reward Expiry Handling
If rewards have post-redemption validity:
Expiry date must be clearly shown.
Expired rewards must be visually marked.
Expired rewards must not be usable.

### Marketplace User Experience
Clear Value Exchange
Users must clearly understand:
“You have 1,250 points.”
“This reward costs 800 points.”
The value exchange must feel simple and direct.
Visual Motivation
The Marketplace should:
Highlight popular rewards.
Show “Points needed” for locked rewards.
This creates forward motivation.
Reward Transparency
Before redemption:
Show reward details clearly.
Show validity.
Avoid hidden conditions.
After redemption:
Immediate access to reward.
Clear confirmation message.
If inventory-limited:
Show the remaining quantity.
Show countdown timers or expiry (if applicable).