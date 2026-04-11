import copy
import json
from pathlib import Path


OUTPUT_PATH = Path("/Users/jw246/Desktop/NTU/NLP/PlanFit/training_plan_samples.json")


DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def entry(day, focus, details, duration, intensity, reason):
    return {
        "day": day,
        "focus": focus,
        "details": details,
        "duration": duration,
        "intensity": intensity,
        "reason": reason,
    }


def render_summary(summary_bullets):
    lines = ["[1] Goal and Constraint Summary"]
    for bullet in summary_bullets:
        lines.append(f"- {bullet}")
    return "\n".join(lines)


def render_week_plan(weeks, include_revision_status=False):
    lines = ["[2] 4-Week Training Plan" if not include_revision_status else "[2] Revised 4-Week Plan"]
    for week_index, week in enumerate(weeks, start=1):
        lines.append(f"Week {week_index}")
        for day in week:
            lines.append(f"- Week: {week_index}")
            lines.append(f"- Day: {day['day']}")
            lines.append(f"- Main focus: {day['focus']}")
            lines.append(f"- Session details: {day['details']}")
            lines.append(f"- Estimated duration (minutes): {day['duration']}")
            lines.append(f"- Intensity / effort note: {day['intensity']}")
            lines.append(f"- Short reason: {day['reason']}")
            if include_revision_status:
                lines.append(f"- Revision status: {day['revision_status']}")
        if week_index != len(weeks):
            lines.append("")
    return "\n".join(lines)


def render_tradeoff(tradeoff_text):
    return "\n".join(["[3] Trade-off Explanation", tradeoff_text])


def render_safety(safety_notes):
    lines = ["[4] Safety Notes"]
    for note in safety_notes:
        lines.append(f"- {note}")
    return "\n".join(lines)


def render_progression(progress_text):
    return "\n".join(["[5] Progression Logic", progress_text])


def render_condition_a(persona, plan_data):
    return "\n\n".join(
        [
            render_summary(plan_data["summary"]),
            render_week_plan(plan_data["weeks"]),
            render_tradeoff(plan_data["tradeoff"]),
            render_safety(plan_data["safety"]),
            render_progression(plan_data["progression"]),
        ]
    )


def render_condition_b(persona, plan_data):
    lines = ["Step 1. Extract the user profile"]
    lines.append(f"- Primary goal: {persona['primary_goal']}")
    lines.append(f"- Secondary goal: {persona['secondary_goal']}")
    lines.append(f"- Experience level: {persona['training_background']}")
    lines.append(f"- Schedule constraints: {persona['schedule_constraint']}")
    lines.append(f"- Injury / physical limitations: {persona['injury_or_limitation']}")
    lines.append(f"- Preferences: {persona['preferences']}")
    lines.append(f"- Likely trade-offs or conflicts: {plan_data['tradeoff_extract']}")
    lines.append("")
    lines.append("Step 2. Planning strategy")
    for bullet in plan_data["strategy"]:
        lines.append(f"- {bullet}")
    lines.append("")
    lines.append("Step 3. Final 4-week plan")
    for week_index, week in enumerate(plan_data["weeks"], start=1):
        lines.append(f"Week {week_index}")
        for day in week:
            lines.append(f"- Week: {week_index}")
            lines.append(f"- Day: {day['day']}")
            lines.append(f"- Main focus: {day['focus']}")
            lines.append(f"- Session details: {day['details']}")
            lines.append(f"- Estimated duration (minutes): {day['duration']}")
            lines.append(f"- Intensity / effort note: {day['intensity']}")
            lines.append(f"- Short reason: {day['reason']}")
        if week_index != len(plan_data["weeks"]):
            lines.append("")
    lines.append("")
    lines.append("Step 4. Final self-check")
    for bullet in plan_data["self_check"]:
        lines.append(f"- {bullet}")
    return "\n".join(lines)


def render_condition_c(review):
    parts = []
    parts.append("[1] Main Problems in the Original Plan")
    for problem in review["problems"]:
        parts.append(f"- {problem}")
    parts.append("")
    parts.append(render_week_plan(review["weeks"], include_revision_status=True))
    parts.append("")
    parts.append("[3] What Was Changed")
    for item in review["changes"]:
        parts.append(f"- {item}")
    parts.append("")
    parts.append("[4] Why the Revised Plan Is Better")
    parts.append(review["why_better"])
    return "\n".join(parts)


def annotate_revision_status(original_weeks, revised_weeks):
    annotated = []
    for original_week, revised_week in zip(original_weeks, revised_weeks):
        week_entries = []
        for original_day, revised_day in zip(original_week, revised_week):
            item = copy.deepcopy(revised_day)
            item["revision_status"] = (
                "unchanged" if original_day == revised_day else "modified"
            )
            week_entries.append(item)
        annotated.append(week_entries)
    return annotated


def p1_plan():
    summary = [
        "Primary goal is hypertrophy, so lifting volume and quality are the main priority.",
        "Running is kept at two maintenance-focused sessions per week instead of a performance-building block.",
        "The plan uses four lifting days and two running days inside the six-day cap and 90-minute session limit.",
        "Lower-body lifting is preserved because the user explicitly does not want to give it up.",
        "Running sessions are separated from hard lower-body sessions to reduce interference and leg-fatigue spillover.",
    ]
    weeks = [
        [
            entry("Monday", "Upper hypertrophy A", "Bench press, incline dumbbell press, chest-supported row, lat pulldown, lateral raise, and arm accessories; mostly 3 working sets per exercise.", 80, "RPE 7 to 8, leave 1 to 3 reps in reserve.", "Opens the week with a high-quality hypertrophy session while the user is fresh."),
            entry("Tuesday", "Easy aerobic run", "35 minutes easy running plus 4 x 20-second relaxed strides, then 10 minutes of calf, hip, and ankle mobility.", 45, "Comfortable Zone 2 effort.", "Keeps running economy without creating heavy leg fatigue before the main lower day."),
            entry("Wednesday", "Lower hypertrophy A", "Back squat or hack squat, Romanian deadlift, leg press, leg curl, calf raise, and trunk work; 3 working sets on major lifts.", 85, "RPE 7 to 8, controlled tempo.", "Preserves lower-body muscle stimulus as part of the primary goal."),
            entry("Thursday", "Upper hypertrophy B", "Pull-up or pulldown, flat dumbbell press, cable row, machine shoulder press, rear-delt work, and arms; moderate volume.", 75, "RPE 7 to 8.", "Adds a second upper session for weekly hypertrophy volume without stressing the legs."),
            entry("Friday", "Steady maintenance run", "40 minutes steady but sub-threshold running, followed by 8 minutes easy mobility.", 50, "Mostly Zone 2 to low Zone 3, never race-like.", "Maintains running feel while still leaving room for Saturday lifting."),
            entry("Saturday", "Lower hypertrophy B", "Front squat or leg press, hip thrust, split squat, seated leg curl, calf raise, and optional adductor work; moderate volume.", 80, "RPE 7, do not grind reps.", "A second lower day keeps weekly hypertrophy volume high without turning into a power-focused day."),
            entry("Sunday", "Rest and recovery", "Full rest or an easy 20-minute walk and light mobility only.", 20, "Very easy.", "Creates a clear recovery point before repeating the training week."),
        ],
        [
            entry("Monday", "Upper hypertrophy A", "Repeat Week 1 exercise selection; add a fourth set to bench press and chest-supported row if recovery is good.", 85, "RPE 7 to 8.", "Increases upper-body volume gradually to support hypertrophy."),
            entry("Tuesday", "Easy aerobic run", "38 minutes easy running plus 4 x 20-second relaxed strides, then mobility.", 48, "Comfortable Zone 2.", "Adds only a small running progression so lifting remains dominant."),
            entry("Wednesday", "Lower hypertrophy A", "Repeat Week 1 lower pattern; add one set to the first squat pattern or leg press only.", 88, "RPE 7 to 8.", "Progresses lower-body volume modestly without overshooting recovery."),
            entry("Thursday", "Upper hypertrophy B", "Same template as Week 1 with one extra set on the primary pull or press movement.", 78, "RPE 7 to 8.", "Builds weekly hypertrophy volume while fatigue is still manageable."),
            entry("Friday", "Steady maintenance run", "42 minutes steady running with the last 8 minutes slightly faster but still controlled.", 52, "Zone 2 to low Zone 3.", "Keeps running performance from drifting while staying secondary."),
            entry("Saturday", "Lower hypertrophy B", "Same movement pattern as Week 1, but add reps before adding load on split squats and curls.", 82, "RPE 7.", "Extends lower-body work without colliding with the running goal."),
            entry("Sunday", "Rest and recovery", "Rest day with optional walk and soft-tissue work.", 20, "Very easy.", "Protects recovery heading into Week 3."),
        ],
        [
            entry("Monday", "Upper hypertrophy A", "Keep Week 2 volume and try to progress load or reps slightly on the first two compound lifts.", 85, "RPE 8 on top sets, still controlled.", "Week 3 is the highest-quality overload week for the primary goal."),
            entry("Tuesday", "Easy aerobic run", "40 minutes easy running plus 4 x 20-second relaxed strides.", 50, "Comfortable Zone 2.", "Maintains run frequency without turning Tuesday into a hard session."),
            entry("Wednesday", "Lower hypertrophy A", "Keep the same exercise list and aim for small rep or load progressions on squat and Romanian deadlift.", 88, "RPE 8 on main lifts, no failed reps.", "Provides the strongest lower-body hypertrophy stimulus of the block."),
            entry("Thursday", "Upper hypertrophy B", "Same template as prior weeks; push one accessory movement slightly harder if recovery is solid.", 80, "RPE 7 to 8.", "Supports total hypertrophy volume without creating excessive systemic fatigue."),
            entry("Friday", "Steady maintenance run", "40 minutes steady running, fully sub-threshold and conversational for most of the session.", 50, "Upper Zone 2 only.", "Keeps running maintenance in place while protecting Saturday leg work."),
            entry("Saturday", "Lower hypertrophy B", "Use the same movement pattern with controlled volume; avoid adding extra sets beyond the plan.", 80, "RPE 7 to 8.", "Maintains frequency while preventing interference from accumulated fatigue."),
            entry("Sunday", "Rest and recovery", "Full rest or an easy walk.", 20, "Very easy.", "Sets up a smoother transition into the deload week."),
        ],
        [
            entry("Monday", "Upper hypertrophy A", "Keep the same exercises but remove roughly one set from each main movement and stay crisp technically.", 70, "RPE 6 to 7.", "Deloads fatigue while preserving movement quality and muscle stimulus."),
            entry("Tuesday", "Easy aerobic run", "30 to 32 minutes easy running with no strides.", 35, "Easy Zone 2.", "Reduces total stress while keeping the running routine intact."),
            entry("Wednesday", "Lower hypertrophy A", "Same lower template with roughly 25 to 30 percent less volume than Week 3.", 72, "RPE 6 to 7.", "Allows leg recovery so the block ends feeling fresh instead of depleted."),
            entry("Thursday", "Upper hypertrophy B", "Shortened upper session with moderate loads and fewer accessories.", 65, "RPE 6 to 7.", "Retains practice and blood flow without chasing overload."),
            entry("Friday", "Easy maintenance run", "32 to 35 minutes easy running only.", 35, "Easy Zone 2.", "Keeps the secondary goal present while clearly prioritizing recovery."),
            entry("Saturday", "Lower hypertrophy B", "Short lower session with reduced sets on all lifts and no grinders.", 70, "RPE 6 to 7.", "Finishes the block with enough stimulus but much less fatigue."),
            entry("Sunday", "Rest and recovery", "Full rest.", 0, "Rest.", "Ends the four-week block with a clear recovery day."),
        ],
    ]
    return {
        "summary": summary,
        "weeks": weeks,
        "tradeoff": "The plan gives hypertrophy the first claim on recovery by using four lifting sessions and only two running sessions. Running is kept mostly easy or steady, not interval-heavy, so it supports maintenance without undermining lower-body growth. Lower-body training stays in the program twice per week because removing it would conflict with the user's preference and the primary physique goal.",
        "safety": [
            "Do not turn the Friday run into a hard tempo or race-pace effort, especially before Saturday lower-body lifting.",
            "Keep at least one to three reps in reserve on most hypertrophy work to avoid unnecessary fatigue accumulation.",
            "If leg soreness remains unusually high after Wednesday, keep Saturday lower work moderate rather than adding volume.",
            "Running shoe choice and easy surfaces can help reduce lower-leg stress, but the plan still assumes normal healthy tolerance rather than medical management.",
        ],
        "progression": "Week 1 establishes the rhythm and baseline volume. Week 2 adds a small amount of lifting volume and a small amount of running time. Week 3 is the highest overload week, but running intensity is intentionally capped so the primary goal still wins. Week 4 reduces volume across both modalities so the user keeps momentum while shedding fatigue.",
        "tradeoff_extract": "The main conflict is that too much running volume or intensity would reduce recovery for hypertrophy, especially around lower-body days.",
        "strategy": [
            "Prioritize lifting quality and weekly hypertrophy volume over running progression.",
            "Limit running to maintenance-focused sessions rather than intervals or long-distance build-up.",
            "Protect the lower-body sessions by avoiding hard runs after heavy leg days.",
            "Use Week 4 as a fatigue-management week so both lifting and running stay sustainable.",
        ],
        "self_check": [
            "Does the plan respect the primary goal? Yes, hypertrophy receives the highest weekly volume and best recovery slots.",
            "Does the plan stay within schedule constraints? Yes, it uses six days or fewer and keeps sessions at or below 90 minutes.",
            "Does the plan address physical limitations? Yes, there is no reported injury, but fatigue management is still built in.",
            "Does the plan avoid obvious running-lifting conflicts? Yes, hard lower-body days are not followed by interval or long-distance running.",
        ],
    }


def p2_plan():
    summary = [
        "Primary goal is beginner-friendly strength and muscle gain, so the plan stays gym-centered.",
        "Running is minimized because the user prefers gym training and does not enjoy running-focused plans.",
        "Low flexibility is handled by adding warm-up and mobility time instead of pushing high-skill lifts too early.",
        "The schedule fits three main training days with one optional easy conditioning day inside the 3 to 4 day limit.",
        "Progression is simple and repeatable so recovery and technique can improve together.",
    ]
    weeks = [
        [
            entry("Monday", "Full-body gym A", "Leg press, dumbbell bench press, chest-supported row, Romanian deadlift with light dumbbells, cable pulldown, and plank work; 2 to 3 working sets each after 8 minutes of mobility.", 60, "RPE 6 to 7.", "Introduces basic movement patterns without overwhelming a beginner."),
            entry("Tuesday", "Rest", "Full rest or an easy 15-minute walk.", 15, "Very easy.", "Creates recovery space after the first gym day."),
            entry("Wednesday", "Full-body gym B", "Goblet squat to a comfortable depth, machine chest press, seated row, split squat holding support, hamstring curl, and dead-bug core work.", 60, "RPE 6 to 7.", "Builds general strength with stable, accessible exercises."),
            entry("Thursday", "Rest", "Rest and light stretching for hips, ankles, and thoracic spine.", 15, "Very easy.", "Keeps flexibility work in the routine without adding fatigue."),
            entry("Friday", "Full-body gym A", "Repeat Monday with slightly more confidence in movement execution but no need to push heavy.", 60, "RPE 6 to 7.", "Repetition helps a beginner learn technique faster."),
            entry("Saturday", "Optional easy conditioning", "20 minutes incline treadmill walk or easy bike plus 10 minutes mobility.", 30, "Easy conversational effort.", "Improves general fitness without turning the plan into a running program."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Keeps the week sustainable."),
        ],
        [
            entry("Monday", "Full-body gym A", "Same exercise menu; add one set to leg press and row if technique stayed clean in Week 1.", 60, "RPE 6 to 7.", "Gradual progression supports strength and muscle without rushing."),
            entry("Tuesday", "Rest", "Full rest or an easy walk.", 15, "Very easy.", "Keeps fatigue low for the next gym session."),
            entry("Wednesday", "Full-body gym B", "Repeat Week 1 with slightly more range of motion where comfortable and controlled.", 60, "RPE 6 to 7.", "Uses practice and slightly better movement quality as progression."),
            entry("Thursday", "Rest", "Light mobility and recovery.", 15, "Very easy.", "Supports flexibility and consistency."),
            entry("Friday", "Full-body gym A", "Repeat Monday and add a few reps before adding much load.", 60, "RPE 6 to 7.", "Beginner adaptation usually responds well to small rep increases."),
            entry("Saturday", "Optional easy conditioning", "20 to 25 minutes easy bike or treadmill walk plus mobility.", 35, "Easy.", "Adds a little general fitness work without overemphasizing running."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Preserves recovery."),
        ],
        [
            entry("Monday", "Full-body gym A", "Keep the same pattern and use slightly heavier but still controlled loads on the first two lifts.", 60, "RPE 7.", "Week 3 is the clearest loading week of the block."),
            entry("Tuesday", "Rest", "Full rest or easy walk.", 15, "Very easy.", "Avoids stacking too much fatigue on a beginner."),
            entry("Wednesday", "Full-body gym B", "Repeat Week 2 and keep mobility work before squats and split squats.", 60, "RPE 7.", "Maintains progression while respecting flexibility limits."),
            entry("Thursday", "Rest", "Light stretching and recovery.", 15, "Very easy.", "Encourages habit without adding strain."),
            entry("Friday", "Full-body gym A", "Same movement pattern with stable technique and only modest load increases.", 60, "RPE 7.", "Reinforces the primary goal through repetition and consistency."),
            entry("Saturday", "Optional easy conditioning", "25 minutes easy bike or treadmill walk only if recovery feels good.", 25, "Easy.", "Keeps conditioning secondary and optional."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Allows recovery before the final week."),
        ],
        [
            entry("Monday", "Full-body gym A", "Reduce total sets slightly but keep the same movements and good form.", 50, "RPE 6.", "Deloads fatigue while preserving the routine."),
            entry("Tuesday", "Rest", "Full rest.", 0, "Rest.", "Maintains recovery."),
            entry("Wednesday", "Full-body gym B", "Shorter session with the same exercise family and no pushing near failure.", 50, "RPE 6.", "Lets technique stay sharp without excess stress."),
            entry("Thursday", "Rest", "Easy mobility only.", 15, "Very easy.", "Supports long-term adherence."),
            entry("Friday", "Full-body gym A", "Repeat the shortened pattern from Monday.", 50, "RPE 6.", "Finishes the block with a manageable workload."),
            entry("Saturday", "Optional easy conditioning", "15 to 20 minutes easy bike or treadmill walk.", 20, "Easy.", "Keeps fitness work low stress."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Ends the block recovered."),
        ],
    ]
    return {
        "summary": summary,
        "weeks": weeks,
        "tradeoff": "The plan keeps nearly all training stress in gym-based strength and hypertrophy work because that matches the user's preference and beginner needs. Conditioning is optional and easy so it improves general fitness without competing with recovery, flexibility work, or skill acquisition in the gym.",
        "safety": [
            "Warm up the hips, ankles, shoulders, and thoracic spine before every gym session because low flexibility is a meaningful limiter.",
            "Use stable exercise variations and comfortable ranges of motion instead of forcing deep positions.",
            "Avoid high-skill barbell lifts until the user has a more consistent technical base.",
            "Do not add running-focused work just to fill time, because it does not support the primary goal or preference set.",
        ],
        "progression": "Week 1 teaches the pattern. Week 2 adds a small amount of volume. Week 3 uses the same structure with slightly stronger loading if technique remains stable. Week 4 trims volume to keep the beginner adapting rather than burning out.",
        "tradeoff_extract": "The main conflict is between wanting general fitness and not enjoying or needing a running-heavy plan, so conditioning must stay secondary.",
        "strategy": [
            "Prioritize simple full-body gym sessions that build strength and muscle for a beginner.",
            "Limit conditioning to optional easy work so it supports fitness rather than replacing strength progress.",
            "Use mobility and warm-up structure to account for low flexibility.",
            "Progress through better movement quality, slightly more reps, and small load increases rather than aggressive complexity.",
        ],
        "self_check": [
            "Does the plan respect the primary goal? Yes, gym-based strength and muscle work is the core of the week.",
            "Does the plan stay within schedule constraints? Yes, it uses three main days plus one optional short day, all around 60 minutes.",
            "Does the plan address physical limitations? Yes, it explicitly includes mobility and avoids forcing advanced movement demands.",
            "Does the plan avoid obvious running-lifting conflicts? Yes, running is kept minimal and optional.",
        ],
    }


def p3_plan():
    summary = [
        "Primary goal is fat loss while maintaining muscle, so resistance training remains the anchor of the week.",
        "Running is treated as conditioning support rather than a performance goal, which matches the user's preference.",
        "Frequent calf issues mean impact volume must stay conservative and replaceable with low-impact options.",
        "The weekly structure uses four lifting sessions and one conditioning-focused day inside the five-day limit.",
        "The plan avoids high aerobic volume that could undermine muscle retention or aggravate the calf.",
    ]
    weeks = [
        [
            entry("Monday", "Upper body strength-hypertrophy", "Bench press or machine press, row, pulldown, incline dumbbell press, lateral raise, and arms; 3 working sets each.", 75, "RPE 7 to 8.", "Keeps upper-body muscle stimulus high for maintenance during fat loss."),
            entry("Tuesday", "Lower body strength-hypertrophy", "Leg press or squat variation, Romanian deadlift, split squat, hamstring curl, calf raise with conservative volume, and trunk work.", 80, "RPE 7.", "Supports lower-body muscle retention without turning the day into a running conflict."),
            entry("Wednesday", "Low-impact conditioning", "25 minutes incline walk, bike, or elliptical plus 15 minutes mobility and core work.", 45, "Easy to moderate, mostly conversational.", "Adds caloric expenditure with lower calf risk than performance running."),
            entry("Thursday", "Upper hypertrophy", "Machine press, cable row, pulldown, chest fly, rear-delt work, and arms; moderate volume.", 70, "RPE 7 to 8.", "Maintains weekly upper-body volume for muscle retention."),
            entry("Friday", "Rest", "Full rest or easy walk only.", 20, "Very easy.", "Protects recovery before the second lower session."),
            entry("Saturday", "Lower hypertrophy and conditioning finisher", "Leg press, hip hinge, glute bridge, leg curl, and optional 8 to 10 minutes easy sled push or bike if the calf feels calm.", 80, "RPE 7, no grinding.", "Keeps the lower-body stimulus strong while using conditioning as a small add-on."),
            entry("Sunday", "Easy run or run-walk", "20 to 25 minutes easy run-walk if the calf feels good; otherwise replace with incline walk.", 30, "Easy conversational effort only.", "Preserves a bit of running routine without making it a performance block."),
        ],
        [
            entry("Monday", "Upper body strength-hypertrophy", "Repeat Week 1 and add a set to the first press or row if recovery is good.", 78, "RPE 7 to 8.", "Slightly progresses muscle-maintenance volume."),
            entry("Tuesday", "Lower body strength-hypertrophy", "Same exercise family as Week 1; add reps before load on split squat and leg curl.", 80, "RPE 7.", "Progresses the lower body carefully while respecting the calf."),
            entry("Wednesday", "Low-impact conditioning", "30 minutes incline walk, bike, or elliptical plus mobility.", 45, "Easy to moderate.", "Builds conditioning support without extra impact."),
            entry("Thursday", "Upper hypertrophy", "Same template as Week 1 with small rep progression.", 72, "RPE 7 to 8.", "Maintains upper-body stimulus during the deficit-focused phase."),
            entry("Friday", "Rest", "Full rest.", 0, "Rest.", "Helps control cumulative fatigue."),
            entry("Saturday", "Lower hypertrophy and conditioning finisher", "Repeat Saturday template with small rep progressions and optional short bike finisher.", 80, "RPE 7.", "Balances fat-loss support with muscle retention."),
            entry("Sunday", "Easy run or run-walk", "22 to 28 minutes easy run-walk if the calf remains calm; otherwise incline walk.", 30, "Easy only.", "Keeps running secondary and fully flexible."),
        ],
        [
            entry("Monday", "Upper body strength-hypertrophy", "Maintain Week 2 volume and push load slightly on one press and one row.", 78, "RPE 8 on top sets.", "Week 3 is the most demanding week for resistance work."),
            entry("Tuesday", "Lower body strength-hypertrophy", "Keep the same movement menu but do not add calf-specific work beyond the planned dose.", 80, "RPE 7 to 8.", "Maintains lower-body muscle without unnecessary lower-leg irritation."),
            entry("Wednesday", "Low-impact conditioning", "30 to 35 minutes incline walk, bike, or elliptical plus mobility.", 50, "Easy to moderate.", "Increases conditioning slightly while staying impact-aware."),
            entry("Thursday", "Upper hypertrophy", "Same template with modest load or rep progression.", 72, "RPE 7 to 8.", "Supports muscle retention as the primary training target."),
            entry("Friday", "Rest", "Full rest or easy walk.", 20, "Very easy.", "Creates recovery before the weekend sessions."),
            entry("Saturday", "Lower hypertrophy and conditioning finisher", "Repeat Saturday structure without extra load jumps; stay technically crisp.", 78, "RPE 7.", "Controls fatigue so the weekly structure stays sustainable."),
            entry("Sunday", "Easy run or run-walk", "20 to 25 minutes easy run-walk only if the calf feels normal; otherwise use incline walk or bike.", 30, "Easy only.", "Prevents the secondary tool from becoming the recovery bottleneck."),
        ],
        [
            entry("Monday", "Upper body strength-hypertrophy", "Reduce total sets by roughly 25 percent while keeping the same exercises.", 65, "RPE 6 to 7.", "Deloads fatigue while retaining muscle-focused work."),
            entry("Tuesday", "Lower body strength-hypertrophy", "Keep the same structure but reduce lower-body volume and skip any optional finisher.", 68, "RPE 6 to 7.", "Lets the legs and calf recover while maintaining the routine."),
            entry("Wednesday", "Low-impact conditioning", "20 to 25 minutes easy bike or incline walk plus mobility.", 35, "Easy.", "Keeps conditioning stress low in the deload week."),
            entry("Thursday", "Upper hypertrophy", "Shortened upper-body pump-style session with moderate loads.", 60, "RPE 6 to 7.", "Maintains frequency without chasing overload."),
            entry("Friday", "Rest", "Full rest.", 0, "Rest.", "Maintains recovery."),
            entry("Saturday", "Lower hypertrophy", "Shortened lower session with reduced sets and no optional conditioning finisher.", 65, "RPE 6 to 7.", "Finishes the block without excessive impact or fatigue."),
            entry("Sunday", "Easy walk or bike", "20 minutes easy incline walk or bike instead of running if any calf tightness is present.", 20, "Easy.", "Makes recovery the priority while preserving routine continuity."),
        ],
    ]
    return {
        "summary": summary,
        "weeks": weeks,
        "tradeoff": "Because the primary goal is fat loss with muscle maintenance, lifting volume stays high enough to preserve muscle while conditioning stays supportive rather than competitive. Running appears only in conservative, flexible doses, and low-impact conditioning carries more of the aerobic workload so the calf and recovery budget are protected.",
        "safety": [
            "Keep running easy and replace it with incline walking, bike, or elliptical if calf discomfort rises.",
            "Do not stack extra intervals or long runs on top of the plan because that would push conditioning beyond its intended role.",
            "Maintain resistance training quality and avoid turning lower-body days into exhaustion sessions.",
            "If recovery drops, reduce conditioning first rather than cutting the muscle-preserving lifting work.",
        ],
        "progression": "Week 1 establishes the split and conservative conditioning volume. Week 2 adds a small amount of training work. Week 3 is the highest resistance-training week, but running still stays modest. Week 4 reduces both lifting and conditioning volume so the user can recover without losing rhythm.",
        "tradeoff_extract": "The main conflict is that too much running would both challenge the calf and steal recovery from the muscle-maintenance lifting work.",
        "strategy": [
            "Prioritize lifting to keep muscle while using conditioning as a secondary fat-loss tool.",
            "Favor low-impact aerobic work over running progression because the user does not need performance-oriented running.",
            "Keep calf stress flexible by allowing run-walk or non-impact substitutions.",
            "Use a small deload in Week 4 so the plan stays realistic and repeatable.",
        ],
        "self_check": [
            "Does the plan respect the primary goal? Yes, lifting remains the anchor and conditioning stays supportive.",
            "Does the plan stay within schedule constraints? Yes, it uses five or fewer days with 70 to 80 minute sessions.",
            "Does the plan address physical limitations? Yes, calf risk is directly handled through impact control and substitutions.",
            "Does the plan avoid obvious running-lifting conflicts? Yes, there is no aggressive running build that would interfere with lower-body recovery.",
        ],
    }


def p4_plan():
    summary = [
        "Primary goal is building a sustainable gym habit and basic fitness, so simplicity is more important than variety.",
        "The plan stays gym-centered with only light optional running because the user is a beginner and mainly interested in the gym.",
        "Training frequency is capped at three days per week to match the schedule and reduce dropout risk.",
        "Each session repeats familiar patterns so the user can improve confidence and technique.",
        "Progression is modest and clear across four weeks rather than complex or aggressive.",
    ]
    weeks = [
        [
            entry("Monday", "Full-body gym A", "Goblet squat, dumbbell bench press, seated row, Romanian deadlift with dumbbells, cable pulldown, and plank variations.", 60, "RPE 6 to 7.", "A simple full-body session builds the core habit without excessive complexity."),
            entry("Tuesday", "Rest", "Full rest or easy walk.", 15, "Very easy.", "Keeps the weekly structure manageable."),
            entry("Wednesday", "Full-body gym B", "Leg press, incline dumbbell press, chest-supported row, split squat with support, hamstring curl, and side plank.", 60, "RPE 6 to 7.", "Adds a second simple full-body day with slightly different patterns."),
            entry("Thursday", "Rest", "Rest or light mobility.", 15, "Very easy.", "Protects recovery for a beginner."),
            entry("Friday", "Full-body gym A", "Repeat Monday with the same exercises and controlled effort.", 60, "RPE 6 to 7.", "Repetition improves consistency and confidence."),
            entry("Saturday", "Rest or optional light jog", "Rest by default; optional 15 to 20 minutes easy jog or brisk walk only if energy is good.", 20, "Easy.", "Keeps running truly optional and secondary."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Maintains a low-complexity weekly rhythm."),
        ],
        [
            entry("Monday", "Full-body gym A", "Same movements as Week 1; add one set to the first lower-body and upper-body exercise if technique is good.", 60, "RPE 6 to 7.", "A small volume increase drives adaptation without changing the structure."),
            entry("Tuesday", "Rest", "Full rest.", 0, "Rest.", "Supports consistency."),
            entry("Wednesday", "Full-body gym B", "Repeat Week 1 and aim for a few extra reps before increasing load.", 60, "RPE 6 to 7.", "Keeps progression simple and beginner-friendly."),
            entry("Thursday", "Rest", "Light mobility.", 15, "Very easy.", "Helps recovery without adding complexity."),
            entry("Friday", "Full-body gym A", "Same session structure with modest rep progressions.", 60, "RPE 6 to 7.", "Reinforces habit formation through familiarity."),
            entry("Saturday", "Rest or optional light jog", "Rest by default; optional 15 to 20 minutes easy jog or brisk walk.", 20, "Easy.", "Maintains the gym-first emphasis."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Keeps total training stress appropriate."),
        ],
        [
            entry("Monday", "Full-body gym A", "Maintain the same exercise menu and use slightly more load on the first two lifts if form stays stable.", 60, "RPE 7.", "Week 3 is the modest high point for training quality."),
            entry("Tuesday", "Rest", "Full rest.", 0, "Rest.", "Allows recovery."),
            entry("Wednesday", "Full-body gym B", "Repeat the same structure and keep technique smooth rather than pushing complexity.", 60, "RPE 7.", "Builds confidence and a sustainable base."),
            entry("Thursday", "Rest", "Light mobility or easy walk.", 15, "Very easy.", "Supports adherence."),
            entry("Friday", "Full-body gym A", "Repeat Monday and stop every set with a rep or two in reserve.", 60, "RPE 7.", "The plan stays simple even in the hardest week."),
            entry("Saturday", "Rest or optional light jog", "Optional 15 to 20 minutes easy jog or walk only if legs feel fresh.", 20, "Easy.", "Prevents the optional running from competing with the gym routine."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Completes the week with a clear reset."),
        ],
        [
            entry("Monday", "Full-body gym A", "Use the same movements but cut one set from most exercises.", 50, "RPE 6.", "Deloads fatigue while preserving the pattern."),
            entry("Tuesday", "Rest", "Full rest.", 0, "Rest.", "Keeps recovery high."),
            entry("Wednesday", "Full-body gym B", "Shortened full-body session with controlled effort and no new exercises.", 50, "RPE 6.", "Makes the final week easy to complete."),
            entry("Thursday", "Rest", "Light mobility if desired.", 10, "Very easy.", "Encourages sustainability."),
            entry("Friday", "Full-body gym A", "Repeat the shortened Monday structure.", 50, "RPE 6.", "Ends the block with success rather than exhaustion."),
            entry("Saturday", "Rest or easy walk", "Optional easy walk only.", 20, "Very easy.", "Keeps the week uncomplicated."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Provides a full reset before the next block."),
        ],
    ]
    return {
        "summary": summary,
        "weeks": weeks,
        "tradeoff": "The plan favors a simple gym habit over trying to improve everything at once. Running appears only as an optional easy add-on because the user mainly wants a sustainable gym routine, and any extra complexity would work against the primary goal of consistency.",
        "safety": [
            "Keep every session simple and stop well before failure because the user is new to structured training.",
            "Do not add extra workout variety just for novelty, since complexity is a risk factor for dropout here.",
            "Optional jogging should stay light and should be skipped if it makes the week feel harder to sustain.",
            "If soreness builds, keep the same schedule but reduce sets rather than adding catch-up sessions.",
        ],
        "progression": "Week 1 establishes a repeatable three-day routine. Week 2 adds a small amount of volume. Week 3 uses slightly stronger loading while keeping the same simple structure. Week 4 reduces volume so the user ends the month feeling capable of continuing.",
        "tradeoff_extract": "The main conflict is between wanting a little body-composition progress and needing a plan that stays very simple and sustainable.",
        "strategy": [
            "Prioritize repeatability and confidence over exercise variety or advanced splits.",
            "Keep the plan gym-centered and use running only as an optional low-stakes add-on.",
            "Use the same movement patterns across weeks so progression is easy to understand.",
            "Finish with a deload-style week to reinforce sustainability.",
        ],
        "self_check": [
            "Does the plan respect the primary goal? Yes, it focuses on building a repeatable gym habit first.",
            "Does the plan stay within schedule constraints? Yes, it uses three main days of about 60 minutes.",
            "Does the plan address physical limitations? Yes, there are no reported injuries, but beginner recovery is still respected.",
            "Does the plan avoid obvious running-lifting conflicts? Yes, running is optional and very light.",
        ],
    }


def p5_plan():
    summary = [
        "Primary goal is to improve or maintain running performance and enjoyment, so running gets the best weekly slots.",
        "Lifting is kept efficient and supportive rather than turning into a bodybuilding split.",
        "The plan uses three run days and two short full-body lifting days inside the five-day limit.",
        "Lower-body lifting is present but controlled so it does not ruin key running sessions.",
        "Progression favors run quality and consistency while using lifting to support aesthetics and durability.",
    ]
    weeks = [
        [
            entry("Monday", "Quality run", "10-minute warm-up, 4 x 4 minutes at comfortably hard 10 km effort with 2-minute easy jog recoveries, then cool-down.", 60, "Quality session around RPE 7 to 8.", "Gives the primary goal the freshest slot of the week."),
            entry("Tuesday", "Efficient full-body lifting", "Leg press, Romanian deadlift, dumbbell bench press, seated row, split squat, and core; 2 to 3 working sets each.", 65, "RPE 6 to 7.", "Supports aesthetics and general strength without exhausting the legs."),
            entry("Wednesday", "Easy run", "35 to 40 minutes easy conversational running.", 40, "Zone 2.", "Adds aerobic support and recovery-friendly mileage."),
            entry("Thursday", "Rest", "Full rest or easy walk.", 20, "Very easy.", "Creates space before the next quality run."),
            entry("Friday", "Steady or threshold run", "10-minute warm-up, 20 minutes steady to threshold-adjacent running, then cool-down.", 55, "RPE 7, controlled.", "Builds running performance without requiring race-level effort."),
            entry("Saturday", "Efficient full-body lifting", "Machine press, chest-supported row, leg press, hamstring curl, lateral raise, and arms; moderate volume.", 60, "RPE 6 to 7.", "Keeps lifting supportive and time-efficient."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Protects running recovery and enjoyment."),
        ],
        [
            entry("Monday", "Quality run", "Warm-up, 5 x 4 minutes at controlled 10 km effort with easy recoveries, then cool-down.", 62, "RPE 7 to 8.", "Progresses the main performance session slightly."),
            entry("Tuesday", "Efficient full-body lifting", "Same template as Week 1 with small rep or load increases on the first two lifts.", 65, "RPE 6 to 7.", "Maintains supportive strength work without overshadowing running."),
            entry("Wednesday", "Easy run", "40 minutes easy conversational running.", 40, "Zone 2.", "Expands easy mileage without adding intensity."),
            entry("Thursday", "Rest", "Full rest.", 0, "Rest.", "Preserves recovery."),
            entry("Friday", "Steady or threshold run", "Warm-up, 22 to 24 minutes steady to threshold-adjacent running, cool-down.", 58, "RPE 7.", "Builds the primary goal through specific but sustainable work."),
            entry("Saturday", "Efficient full-body lifting", "Same lifting pattern; keep lower-body work smooth and submaximal.", 60, "RPE 6 to 7.", "Supports physique goals while protecting the run focus."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Maintains freshness."),
        ],
        [
            entry("Monday", "Quality run", "Warm-up, 6 x 3 minutes at around 5 km to 10 km effort with easy recoveries, then cool-down.", 60, "RPE 8 but controlled.", "Provides the sharpest run stimulus of the block."),
            entry("Tuesday", "Efficient full-body lifting", "Repeat the same lifting menu with no major volume increase.", 62, "RPE 6 to 7.", "Prevents lower-body fatigue from spilling into Friday."),
            entry("Wednesday", "Easy run", "40 to 45 minutes easy running.", 45, "Zone 2.", "Maintains aerobic support and enjoyment."),
            entry("Thursday", "Rest", "Full rest or easy walk.", 20, "Very easy.", "Keeps fatigue in check before the second key run."),
            entry("Friday", "Steady or threshold run", "Warm-up, 25 minutes steady to threshold-adjacent running, cool-down.", 60, "RPE 7.", "Supports the primary goal with another meaningful run session."),
            entry("Saturday", "Efficient full-body lifting", "Short, supportive lifting session with moderate loads and no grinding lower-body sets.", 58, "RPE 6 to 7.", "Keeps lifting helpful rather than disruptive."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Allows recovery before the final week."),
        ],
        [
            entry("Monday", "Quality run", "Warm-up, 4 x 3 minutes at controlled quality effort, then cool-down.", 50, "RPE 7.", "Deloads running volume while retaining sharpness."),
            entry("Tuesday", "Efficient full-body lifting", "Shortened full-body session with fewer sets.", 55, "RPE 6.", "Maintains strength with less fatigue."),
            entry("Wednesday", "Easy run", "30 to 35 minutes easy running.", 35, "Zone 2.", "Keeps the routine and recovery aligned."),
            entry("Thursday", "Rest", "Full rest.", 0, "Rest.", "Supports freshness."),
            entry("Friday", "Steady run", "Warm-up, 15 to 18 minutes steady running, cool-down.", 45, "RPE 6 to 7.", "Retains the running feel without carrying fatigue forward."),
            entry("Saturday", "Efficient full-body lifting", "Shortened supportive lifting session with no extra volume.", 50, "RPE 6.", "Lets the secondary goal stay present without dominating the week."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Ends the block fresh."),
        ],
    ]
    return {
        "summary": summary,
        "weeks": weeks,
        "tradeoff": "Running is clearly the main objective, so the week is organized around two quality run slots and one easy run. Lifting appears twice as efficient full-body support, with controlled lower-body volume so it improves aesthetics and durability without blunting running performance or enjoyment.",
        "safety": [
            "Keep lower-body lifting submaximal and avoid turning support sessions into heavy leg-destruction days.",
            "If the legs feel unusually flat before a key run, reduce Tuesday or Saturday lower-body volume first.",
            "Do not expand lifting into a high-volume bodybuilding split because it would conflict with the stated priority.",
            "Running quality should feel controlled, not like repeated race efforts every week.",
        ],
        "progression": "Week 1 sets the run-lift rhythm. Week 2 modestly increases run quality and easy mileage. Week 3 reaches the highest run-specific demand while keeping lifting stable. Week 4 trims volume across both modalities so recovery and enjoyment remain high.",
        "tradeoff_extract": "The main conflict is that too much lifting, especially for the legs, would compromise running quality and enjoyment.",
        "strategy": [
            "Prioritize run quality and consistency with the freshest weekly slots.",
            "Keep lifting brief, full-body, and supportive instead of physique-dominant.",
            "Limit lower-body lifting fatigue so it does not collide with key run sessions.",
            "Use Week 4 to unload both run and lifting fatigue before the next block.",
        ],
        "self_check": [
            "Does the plan respect the primary goal? Yes, running gets the best sessions and the clearest progression.",
            "Does the plan stay within schedule constraints? Yes, it uses five days with 60 to 75 minute sessions.",
            "Does the plan address physical limitations? Yes, there is no reported injury, but lower-body fatigue is still managed carefully.",
            "Does the plan avoid obvious running-lifting conflicts? Yes, lower-body lifting is supportive and controlled rather than dominant.",
        ],
    }


def p6_plan():
    summary = [
        "Primary goal is sustainable long-term health through balanced hybrid training rather than a peak in one modality.",
        "The user's left upper-limb limitation is a central design constraint, so upper-body exercise selection must be modified.",
        "The plan balances three gym sessions and two runs across a 4 to 5 day week.",
        "Running can remain normal, but upper-body training favors machines, dumbbells, unilateral work, and modified ranges of motion.",
        "Progression stays moderate because the aim is long-term sustainability rather than short-term overload.",
    ]
    weeks = [
        [
            entry("Monday", "Lower body and core", "Leg press or squat pattern, Romanian deadlift, split squat, leg curl, calf raise, and anti-rotation core work.", 75, "RPE 6 to 7.", "Starts the week with a lower-body dominant day that is not limited by the left upper limb."),
            entry("Tuesday", "Easy run", "35 to 40 minutes easy running plus light mobility.", 45, "Zone 2.", "Maintains aerobic ability with low complexity."),
            entry("Wednesday", "Upper body modified strength-hypertrophy", "Single-arm cable press, chest-supported row, neutral-grip pulldown, machine chest press with adjusted range, landmine press if comfortable, and grip-assisted accessory work.", 70, "RPE 6 to 7, prioritize control.", "Uses safer upper-body options that do not demand symmetrical barbell stability."),
            entry("Thursday", "Rest", "Full rest or easy walk.", 20, "Very easy.", "Creates recovery between hybrid sessions."),
            entry("Friday", "Full-body hybrid gym session", "Leg press, dumbbell or machine press, chest-supported row, hip hinge, unilateral accessory work, and trunk training.", 75, "RPE 6 to 7.", "Maintains balanced strength while keeping exercise choices adaptable."),
            entry("Saturday", "Steady run", "40 to 45 minutes steady easy running.", 45, "Zone 2 to low Zone 3.", "Keeps running ability present without turning it into a race-focused block."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Supports recovery and long-term adherence."),
        ],
        [
            entry("Monday", "Lower body and core", "Repeat Week 1 and add one set to the first lower-body lift if recovery is good.", 78, "RPE 6 to 7.", "Progresses lower-body work modestly."),
            entry("Tuesday", "Easy run", "40 minutes easy running plus mobility.", 45, "Zone 2.", "Slightly expands aerobic work without changing the balance."),
            entry("Wednesday", "Upper body modified strength-hypertrophy", "Same pattern as Week 1, using load increases only where the left side remains controlled and pain-free.", 72, "RPE 6 to 7.", "Progresses safely through quality rather than forced symmetry."),
            entry("Thursday", "Rest", "Full rest.", 0, "Rest.", "Maintains recovery."),
            entry("Friday", "Full-body hybrid gym session", "Same structure as Week 1 with a small rep increase on leg and row patterns.", 78, "RPE 6 to 7.", "Builds balanced general strength without ignoring the limb limitation."),
            entry("Saturday", "Steady run", "45 minutes steady easy running.", 45, "Zone 2 to low Zone 3.", "Keeps the secondary running goal consistent."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Allows recovery."),
        ],
        [
            entry("Monday", "Lower body and core", "Keep the same pattern and use slightly more load on the first lift if technique remains solid.", 78, "RPE 7.", "Week 3 is the modest peak for lower-body and general strength work."),
            entry("Tuesday", "Easy run", "40 to 45 minutes easy running.", 45, "Zone 2.", "Maintains aerobic capacity without excessive stress."),
            entry("Wednesday", "Upper body modified strength-hypertrophy", "Repeat the same safe exercise menu; use straps or assisted grips where helpful and avoid forcing overhead range.", 72, "RPE 6 to 7.", "Prioritizes safe, individualized upper-body work."),
            entry("Thursday", "Rest", "Full rest or light mobility.", 15, "Very easy.", "Prevents cumulative fatigue."),
            entry("Friday", "Full-body hybrid gym session", "Maintain the same exercises and keep total volume moderate, especially on movements that challenge grip symmetry.", 78, "RPE 6 to 7.", "Sustains balanced training without chasing unstable bilateral loading."),
            entry("Saturday", "Steady run", "45 minutes steady easy running.", 45, "Zone 2 to low Zone 3.", "Preserves running ability and enjoyment."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Sets up the deload week."),
        ],
        [
            entry("Monday", "Lower body and core", "Reduce lower-body volume by roughly 25 percent while keeping the same movement patterns.", 65, "RPE 6.", "Deloads fatigue while maintaining structure."),
            entry("Tuesday", "Easy run", "30 to 35 minutes easy running.", 35, "Zone 2.", "Keeps the routine intact with less stress."),
            entry("Wednesday", "Upper body modified strength-hypertrophy", "Shorter upper-body session using the same safe machine, cable, and unilateral movements.", 60, "RPE 6.", "Maintains safe upper-body practice while unloading fatigue."),
            entry("Thursday", "Rest", "Full rest.", 0, "Rest.", "Protects recovery."),
            entry("Friday", "Full-body hybrid gym session", "Shortened full-body session with reduced sets and no forced heavy bilateral pressing.", 65, "RPE 6.", "Ends the block in a sustainable place."),
            entry("Saturday", "Steady run", "35 minutes easy steady running.", 35, "Zone 2.", "Keeps running present without adding wear."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Closes the block with recovery."),
        ],
    ]
    return {
        "summary": summary,
        "weeks": weeks,
        "tradeoff": "The plan balances running and lifting evenly because the main goal is sustainable hybrid training, but upper-body exercise safety outranks generic performance programming. Running can stay fairly normal, while gym work is individualized around machines, unilateral patterns, modified ranges, and grip-friendly options so the program remains realistic and safe.",
        "safety": [
            "Avoid fixed bilateral barbell presses or any overhead position that feels unstable with the left upper limb.",
            "Use machine, cable, dumbbell, unilateral, or grip-assisted variations when they improve control and comfort.",
            "Do not force symmetrical loading or identical range of motion side to side if the limitation makes that unrealistic.",
            "Running is fine to maintain, but upper-body exercise selection should always stay subordinate to safe execution.",
        ],
        "progression": "Week 1 establishes safe movement choices. Week 2 adds a small amount of volume or duration. Week 3 is the modest high point, but upper-body choices remain conservative and individualized. Week 4 reduces volume so the plan feels sustainable enough to continue long term.",
        "tradeoff_extract": "The main conflict is balancing hybrid training while avoiding upper-body exercises that demand symmetrical barbell control or overhead stability the user may not have.",
        "strategy": [
            "Prioritize long-term sustainability and balanced training rather than aggressive loading in one modality.",
            "Keep running normal but make upper-body gym choices highly individualized.",
            "Use machines, dumbbells, unilateral work, modified ROM, and grip assistance where helpful.",
            "Progress conservatively so safety is not sacrificed for performance.",
        ],
        "self_check": [
            "Does the plan respect the primary goal? Yes, it supports balanced, long-term hybrid training instead of over-specializing.",
            "Does the plan stay within schedule constraints? Yes, it uses five or fewer days and 60 to 80 minute sessions.",
            "Does the plan address physical limitations? Yes, the left upper-limb limitation is explicitly built into exercise selection.",
            "Does the plan avoid obvious running-lifting conflicts? Yes, running is manageable and upper-body work is modified for safety first.",
        ],
    }


def p7_plan():
    summary = [
        "Primary goal is to build basic strength and muscle mass safely in a complete beginner.",
        "Lower-back discomfort and very low bodyweight both argue for conservative loading and a reassuring structure.",
        "The plan uses only three gym days per week with 45 to 60 minute sessions.",
        "Running is not emphasized because it would add fatigue without helping the main goal of strength and muscle gain.",
        "Exercise selection favors supported, stable patterns and core work that does not heavily load the spine.",
    ]
    weeks = [
        [
            entry("Monday", "Beginner full-body A", "Leg press, dumbbell bench press, chest-supported row, glute bridge, cable pulldown, and dead-bug core work after a gentle warm-up.", 50, "RPE 5 to 6.", "Starts safely with stable movements that are less intimidating and less demanding on the back."),
            entry("Tuesday", "Rest", "Full rest or easy walk.", 15, "Very easy.", "Allows recovery and adaptation."),
            entry("Wednesday", "Beginner full-body B", "Box squat or sit-to-stand, machine chest press, seated row, hamstring curl, step-up to low box, and side plank.", 50, "RPE 5 to 6.", "Builds general strength while keeping spinal loading modest."),
            entry("Thursday", "Rest", "Rest and light mobility.", 15, "Very easy.", "Maintains recovery."),
            entry("Friday", "Beginner full-body A", "Repeat Monday and focus on better control and confidence rather than load.", 50, "RPE 5 to 6.", "Repetition helps habit formation and technical comfort."),
            entry("Saturday", "Rest", "Full rest.", 0, "Rest.", "Keeps total fatigue low."),
            entry("Sunday", "Rest", "Full rest or easy walk.", 15, "Very easy.", "Maintains a beginner-friendly weekly demand."),
        ],
        [
            entry("Monday", "Beginner full-body A", "Repeat Week 1 and add a small amount of weight or one set on leg press and row if the back felt fine.", 55, "RPE 5 to 6.", "Gradual progress supports strength and muscle gain safely."),
            entry("Tuesday", "Rest", "Full rest.", 0, "Rest.", "Supports recovery."),
            entry("Wednesday", "Beginner full-body B", "Same pattern as Week 1 with slightly smoother range of motion and one small progression.", 55, "RPE 5 to 6.", "Builds comfort and consistency."),
            entry("Thursday", "Rest", "Light mobility only.", 10, "Very easy.", "Keeps the plan non-intimidating."),
            entry("Friday", "Beginner full-body A", "Repeat Monday with controlled reps and no pushing through back discomfort.", 55, "RPE 5 to 6.", "Maintains a safe training habit."),
            entry("Saturday", "Rest", "Full rest.", 0, "Rest.", "Prevents fatigue creep."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Protects recovery."),
        ],
        [
            entry("Monday", "Beginner full-body A", "Keep the same exercise list and progress one or two lifts slightly if form remains comfortable.", 55, "RPE 6.", "Week 3 is the modest high point, still far from maximal effort."),
            entry("Tuesday", "Rest", "Full rest or easy walk.", 15, "Very easy.", "Keeps recovery high."),
            entry("Wednesday", "Beginner full-body B", "Repeat Week 2 with stable technique and no rushed loading.", 55, "RPE 6.", "Supports continued adaptation without aggravating the back."),
            entry("Thursday", "Rest", "Light mobility.", 10, "Very easy.", "Maintains comfort."),
            entry("Friday", "Beginner full-body A", "Same structure with careful rep control and one to two reps in reserve at all times.", 55, "RPE 6.", "Builds confidence and basic muscle stimulus."),
            entry("Saturday", "Rest", "Full rest.", 0, "Rest.", "Avoids unnecessary fatigue."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Keeps the block sustainable."),
        ],
        [
            entry("Monday", "Beginner full-body A", "Reduce total sets and keep the same comfortable movement choices.", 45, "RPE 5.", "Deloads fatigue while preserving routine and confidence."),
            entry("Tuesday", "Rest", "Full rest.", 0, "Rest.", "Maintains recovery."),
            entry("Wednesday", "Beginner full-body B", "Shortened session with the same supported exercise patterns.", 45, "RPE 5.", "Keeps the habit going without extra strain."),
            entry("Thursday", "Rest", "Light mobility only.", 10, "Very easy.", "Supports comfort."),
            entry("Friday", "Beginner full-body A", "Repeat the shortened pattern from Monday.", 45, "RPE 5.", "Ends the block with success rather than overwhelm."),
            entry("Saturday", "Rest", "Full rest.", 0, "Rest.", "Preserves energy."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Closes the block recovered."),
        ],
    ]
    return {
        "summary": summary,
        "weeks": weeks,
        "tradeoff": "The plan intentionally minimizes conditioning and focuses on supported strength work because the user's primary need is basic muscle and strength gain, not calorie burn or running fitness. That trade-off keeps the program less intimidating and better aligned with frequent lower-back discomfort and beginner recovery capacity.",
        "safety": [
            "Avoid heavy axial loading or aggressive barbell work early in the process.",
            "Use supported machines, bodyweight boxes, and dumbbells to reduce lower-back stress.",
            "Do not add running sessions just to increase activity, because that would raise fatigue without serving the primary goal.",
            "If any movement clearly increases back discomfort, shorten the range or substitute a more supported pattern.",
        ],
        "progression": "Week 1 introduces safe patterns. Week 2 adds a very small amount of work if tolerated. Week 3 is the highest week but still conservative. Week 4 lowers volume so the user finishes feeling capable of continuing the habit.",
        "tradeoff_extract": "The main conflict is between wanting faster progress and needing a gentle beginner structure that does not aggravate lower-back discomfort.",
        "strategy": [
            "Prioritize supported strength training and muscle-building basics over extra cardio.",
            "Keep exercise choices simple, non-intimidating, and relatively back-friendly.",
            "Use low effort ranges and modest progression rather than aggressive loading.",
            "Protect the habit by making all three weekly sessions feel achievable.",
        ],
        "self_check": [
            "Does the plan respect the primary goal? Yes, it focuses on basic strength and muscle-building work.",
            "Does the plan stay within schedule constraints? Yes, it uses three days of 45 to 60 minutes.",
            "Does the plan address physical limitations? Yes, lower-back discomfort drives exercise selection and intensity control.",
            "Does the plan avoid obvious running-lifting conflicts? Yes, the plan does not add unnecessary running stress.",
        ],
    }


def p8_plan():
    summary = [
        "Primary goal is safe, consistent exercise without worsening knee pain.",
        "Lower-body work stays in the plan, but exercise choices and cardio modes are knee-friendly.",
        "The schedule uses three main training days plus one optional low-impact conditioning day inside the 3 to 4 day limit.",
        "The plan avoids impact-heavy running, jumping, and deep repetitive knee flexion.",
        "Progression is cautious and focuses on consistency, strength support, and symptom-aware exercise selection.",
    ]
    weeks = [
        [
            entry("Monday", "Upper body and glute support", "Machine chest press, seated row, dumbbell incline press, cable pulldown, glute bridge, and core work.", 60, "RPE 6 to 7.", "Builds overall fitness while keeping knee stress low."),
            entry("Tuesday", "Rest", "Full rest or easy walk on a flat surface if comfortable.", 15, "Very easy.", "Keeps recovery intact."),
            entry("Wednesday", "Modified lower body", "Box squat to a pain-tolerable depth, Romanian deadlift, glute bridge, hamstring curl, short-range split squat or step-up if comfortable, and calf work.", 60, "RPE 6, controlled range.", "Keeps lower-body training in place without ignoring the knee."),
            entry("Thursday", "Rest", "Light mobility and recovery.", 15, "Very easy.", "Supports tissue tolerance without extra stress."),
            entry("Friday", "Upper body and posterior-chain support", "Machine press, chest-supported row, hip hinge pattern, cable work, and trunk stability training.", 60, "RPE 6 to 7.", "Builds total-body fitness while keeping impact low."),
            entry("Saturday", "Optional low-impact conditioning", "20 to 25 minutes easy bike or elliptical plus light mobility.", 30, "Easy.", "Improves fitness in a knee-friendlier way than impact running."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Maintains recovery and consistency."),
        ],
        [
            entry("Monday", "Upper body and glute support", "Repeat Week 1 and add a small progression on upper-body lifts.", 60, "RPE 6 to 7.", "Allows progress without stressing the knee."),
            entry("Tuesday", "Rest", "Full rest.", 0, "Rest.", "Protects recovery."),
            entry("Wednesday", "Modified lower body", "Repeat Week 1 and only increase depth or load if the knee tolerated the prior week well.", 60, "RPE 6.", "Respects the pain-limited nature of lower-body work."),
            entry("Thursday", "Rest", "Light mobility only.", 10, "Very easy.", "Helps maintain movement quality."),
            entry("Friday", "Upper body and posterior-chain support", "Same pattern as Week 1 with small rep progressions.", 60, "RPE 6 to 7.", "Improves fitness while staying knee-aware."),
            entry("Saturday", "Optional low-impact conditioning", "25 minutes easy bike or elliptical.", 25, "Easy.", "Keeps conditioning conservative."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Prevents overload."),
        ],
        [
            entry("Monday", "Upper body and glute support", "Maintain the same structure with a modest load progression on selected upper-body lifts.", 60, "RPE 7.", "Week 3 is the strongest week for upper-body progress."),
            entry("Tuesday", "Rest", "Full rest or easy walk if comfortable.", 15, "Very easy.", "Keeps fatigue low."),
            entry("Wednesday", "Modified lower body", "Same lower-body menu; keep range of motion pain-tolerable and prioritize glute and hamstring work.", 60, "RPE 6 to 7.", "Retains lower-body stimulus without forcing knee-aggravating positions."),
            entry("Thursday", "Rest", "Light mobility.", 10, "Very easy.", "Supports recovery."),
            entry("Friday", "Upper body and posterior-chain support", "Repeat Friday with slightly more reps or load where comfortable.", 60, "RPE 7.", "Maintains total-body progress without extra knee load."),
            entry("Saturday", "Optional low-impact conditioning", "25 to 30 minutes easy bike or elliptical.", 30, "Easy.", "Allows a small conditioning progression without impact."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Sets up the final week."),
        ],
        [
            entry("Monday", "Upper body and glute support", "Reduce sets slightly and keep the same stable movement pattern.", 50, "RPE 6.", "Deloads fatigue while preserving consistency."),
            entry("Tuesday", "Rest", "Full rest.", 0, "Rest.", "Maintains recovery."),
            entry("Wednesday", "Modified lower body", "Shorter lower session with conservative range of motion and no extra volume.", 50, "RPE 6.", "Lets the knee recover while keeping the habit."),
            entry("Thursday", "Rest", "Light mobility only.", 10, "Very easy.", "Supports comfort."),
            entry("Friday", "Upper body and posterior-chain support", "Shortened supportive session.", 50, "RPE 6.", "Ends the block without excessive fatigue."),
            entry("Saturday", "Optional low-impact conditioning", "20 minutes easy bike or elliptical.", 20, "Easy.", "Keeps conditioning easy and joint-friendly."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Closes the block recovered."),
        ],
    ]
    return {
        "summary": summary,
        "weeks": weeks,
        "tradeoff": "The plan keeps lower-body training in place because removing it entirely would limit fitness and body-composition progress, but it shifts exercise choice toward posterior-chain work, controlled depth, and low-impact conditioning. That trade-off protects the knee while still allowing steady training progress.",
        "safety": [
            "Avoid jumping, impact-heavy running, or deep repetitive knee flexion if those patterns aggravate symptoms.",
            "Use pain-tolerable ranges of motion and adjust depth before adding load.",
            "Low-impact cardio such as cycling or elliptical work is preferred over aggressive running.",
            "If the knee is more irritated after lower-body day, reduce lower-body range or volume before removing training altogether.",
        ],
        "progression": "Week 1 establishes safe movement choices. Week 2 adds only small progressions if the knee tolerated Week 1. Week 3 is the modest high point, mostly through upper-body and posterior-chain progress. Week 4 reduces volume so consistency remains high and symptoms are less likely to build.",
        "tradeoff_extract": "The main conflict is keeping lower-body work and fitness progress in the plan while not worsening knee pain through impact or deep knee-dominant volume.",
        "strategy": [
            "Prioritize consistency and symptom-aware exercise selection over aggressive lower-body loading.",
            "Keep lower-body training but bias it toward knee-friendly ranges and posterior-chain work.",
            "Use low-impact conditioning instead of impact-heavy running.",
            "Progress cautiously and deload in Week 4 to protect sustainability.",
        ],
        "self_check": [
            "Does the plan respect the primary goal? Yes, safety and consistency are the main organizing principles.",
            "Does the plan stay within schedule constraints? Yes, it uses three main days plus one optional short conditioning day.",
            "Does the plan address physical limitations? Yes, knee pain directly shapes lower-body and cardio choices.",
            "Does the plan avoid obvious running-lifting conflicts? Yes, impact-heavy running is avoided and lower-body loading is moderated.",
        ],
    }


def p9_plan():
    summary = [
        "Primary goal is to rebuild a sustainable routine, so adherence matters more than ambitious volume.",
        "The plan uses four manageable days rather than trying to match past training levels.",
        "Both lifting and running stay in the program because the user likes both, but each is kept realistic.",
        "The structure uses two full-body gym days and two easy cardio or hybrid days to make restarting easier.",
        "Progression is conservative and includes a built-in easier week so the routine can stick.",
    ]
    weeks = [
        [
            entry("Monday", "Full-body gym A", "Leg press or squat pattern, dumbbell bench press, seated row, Romanian deadlift, pulldown, and core work.", 60, "RPE 6 to 7.", "Starts the week with a manageable full-body session."),
            entry("Tuesday", "Rest", "Full rest or easy walk.", 15, "Very easy.", "Leaves room for recovery and schedule variability."),
            entry("Wednesday", "Easy run or run-walk", "25 to 30 minutes easy running or run-walk plus 5 to 10 minutes mobility.", 35, "Easy conversational effort.", "Reintroduces running without assuming previous fitness is still present."),
            entry("Thursday", "Rest", "Full rest.", 0, "Rest.", "Prevents the week from feeling packed."),
            entry("Friday", "Full-body gym B", "Goblet squat or leg press, incline dumbbell press, chest-supported row, hip hinge, hamstring curl, and side plank.", 60, "RPE 6 to 7.", "Provides a second strength stimulus without excessive complexity."),
            entry("Saturday", "Easy cardio and accessories", "20 to 25 minutes easy run, incline walk, or bike plus 10 to 15 minutes light accessory work.", 40, "Easy.", "Keeps the week active without pushing all-or-nothing intensity."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Gives a full reset before the next week."),
        ],
        [
            entry("Monday", "Full-body gym A", "Repeat Week 1 and add a small rep or load increase on the first two lifts.", 60, "RPE 6 to 7.", "Progresses carefully while protecting adherence."),
            entry("Tuesday", "Rest", "Full rest.", 0, "Rest.", "Keeps the schedule realistic."),
            entry("Wednesday", "Easy run or run-walk", "30 minutes easy running or run-walk.", 30, "Easy conversational effort.", "Builds routine without requiring old performance levels."),
            entry("Thursday", "Rest", "Full rest or easy walk.", 15, "Very easy.", "Leaves buffer room."),
            entry("Friday", "Full-body gym B", "Same template as Week 1 with modest progression.", 60, "RPE 6 to 7.", "Strength work stays practical and repeatable."),
            entry("Saturday", "Easy cardio and accessories", "25 minutes easy run, incline walk, or bike plus short accessory work.", 40, "Easy.", "Adds a small amount of training volume without risking dropout."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Supports recovery."),
        ],
        [
            entry("Monday", "Full-body gym A", "Keep the same pattern and use slightly heavier loads only where technique remains smooth.", 60, "RPE 7.", "Week 3 is the modest high point of the restart block."),
            entry("Tuesday", "Rest", "Full rest.", 0, "Rest.", "Keeps the plan manageable."),
            entry("Wednesday", "Easy run or run-walk", "30 to 35 minutes easy running or run-walk.", 35, "Easy.", "Builds confidence and consistency, not performance pressure."),
            entry("Thursday", "Rest", "Full rest.", 0, "Rest.", "Prevents schedule overload."),
            entry("Friday", "Full-body gym B", "Repeat the same movements and keep one to two reps in reserve on all sets.", 60, "RPE 7.", "Encourages progress without overreaching."),
            entry("Saturday", "Easy cardio and accessories", "25 to 30 minutes easy cardio plus optional 10 minutes accessory work.", 40, "Easy.", "Keeps the plan adherence-friendly even in the highest week."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Sets up the deload week."),
        ],
        [
            entry("Monday", "Full-body gym A", "Reduce sets slightly and keep the same exercises.", 50, "RPE 6.", "Deloads fatigue and reinforces success."),
            entry("Tuesday", "Rest", "Full rest.", 0, "Rest.", "Maintains recovery."),
            entry("Wednesday", "Easy run or walk-jog", "20 to 25 minutes easy running or walk-jog.", 25, "Easy.", "Preserves the routine without creating pressure."),
            entry("Thursday", "Rest", "Full rest.", 0, "Rest.", "Keeps the schedule easy to follow."),
            entry("Friday", "Full-body gym B", "Shortened full-body session with controlled effort.", 50, "RPE 6.", "Ends the block with a repeatable template."),
            entry("Saturday", "Easy cardio and accessories", "20 minutes easy cardio plus short mobility if desired.", 25, "Easy.", "Makes the easiest week feel highly achievable."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Closes the block with good recovery."),
        ],
    ]
    return {
        "summary": summary,
        "weeks": weeks,
        "tradeoff": "The plan intentionally sacrifices aggressive progression in favor of repeatability because the user is currently inconsistent. Both lifting and running remain present, but neither is pushed hard enough to create an all-or-nothing cycle that would undermine adherence.",
        "safety": [
            "Do not try to train at past fitness levels just because the user used to handle more volume.",
            "If a session is missed, resume the next planned day rather than doubling up later in the week.",
            "Keep running easy for this block so it supports habit rebuilding instead of becoming a recovery problem.",
            "Avoid chasing failure in the gym because that raises soreness and threatens consistency.",
        ],
        "progression": "Week 1 re-establishes rhythm. Week 2 adds a small amount of work. Week 3 is the highest but still moderate. Week 4 deliberately becomes easier so the user ends the month ready to continue instead of falling off again.",
        "tradeoff_extract": "The main conflict is between liking both lifting and running and the reality that adherence is unstable right now, so volume must stay realistic.",
        "strategy": [
            "Prioritize adherence and realistic weekly rhythm over ambitious training stress.",
            "Keep both lifting and running in the plan because that supports motivation, but make both manageable.",
            "Build in rest days and an easier final week so the restart is sustainable.",
            "Use repeatable full-body training rather than complex splits or performance blocks.",
        ],
        "self_check": [
            "Does the plan respect the primary goal? Yes, it is built around sustainability and adherence.",
            "Does the plan stay within schedule constraints? Yes, it uses four days of about 60 minutes.",
            "Does the plan address physical limitations? Yes, there is no injury, but the restart phase is treated conservatively.",
            "Does the plan avoid obvious running-lifting conflicts? Yes, both modalities stay easy enough to coexist during the rebuild.",
        ],
    }


def p10_plan():
    summary = [
        "Primary goal is general fitness and a healthy habit, so the plan stays simple, indoor-friendly, and beginner-appropriate.",
        "Lower-back discomfort means exercise choice should limit heavy spinal loading and high-skill barbell work.",
        "The user prefers treadmill running, so cardio stays indoors and low-complexity.",
        "The schedule uses three core days and one optional lighter day inside the 3 to 4 day limit.",
        "Progression is gentle so the habit can grow without back flare-ups or intimidation.",
    ]
    weeks = [
        [
            entry("Monday", "Indoor full-body gym A", "Leg press, machine chest press, seated row, glute bridge, pulldown, and dead-bug core work.", 55, "RPE 6.", "Builds a beginner-friendly gym base with lower back-aware exercise choices."),
            entry("Tuesday", "Rest", "Full rest.", 0, "Rest.", "Maintains recovery."),
            entry("Wednesday", "Treadmill cardio and core", "20 to 25 minutes treadmill walk or easy jog, then 15 minutes of simple core and mobility work.", 45, "Easy conversational effort.", "Matches the indoor preference while keeping cardio supportive."),
            entry("Thursday", "Rest", "Light mobility or rest.", 10, "Very easy.", "Helps the back recover."),
            entry("Friday", "Indoor full-body gym B", "Goblet squat to a comfortable depth or leg press, incline dumbbell press, chest-supported row, hamstring curl, cable work, and side plank.", 55, "RPE 6.", "Adds a second gym day without requiring complex barbell skills."),
            entry("Saturday", "Optional indoor fitness day", "15 to 20 minutes treadmill walk plus a short machine circuit if energy is good.", 30, "Easy.", "Provides optional extra activity without forcing frequency."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Keeps the plan sustainable."),
        ],
        [
            entry("Monday", "Indoor full-body gym A", "Repeat Week 1 and add a small rep or load progression to one lower-body and one upper-body lift.", 55, "RPE 6 to 7.", "Supports steady beginner progress."),
            entry("Tuesday", "Rest", "Full rest.", 0, "Rest.", "Maintains recovery."),
            entry("Wednesday", "Treadmill cardio and core", "25 minutes treadmill walk or easy jog plus simple core work.", 45, "Easy.", "Gently progresses indoor cardio."),
            entry("Thursday", "Rest", "Light mobility.", 10, "Very easy.", "Supports consistency."),
            entry("Friday", "Indoor full-body gym B", "Same structure as Week 1 with modest rep progression.", 55, "RPE 6 to 7.", "Keeps the gym routine familiar and manageable."),
            entry("Saturday", "Optional indoor fitness day", "20 minutes treadmill walk plus a short machine circuit if recovery is good.", 30, "Easy.", "Keeps the extra day light and optional."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Prevents overload."),
        ],
        [
            entry("Monday", "Indoor full-body gym A", "Keep the same exercise list and progress selected lifts slightly if the back feels stable.", 55, "RPE 7.", "Week 3 is the modest high point of the block."),
            entry("Tuesday", "Rest", "Full rest.", 0, "Rest.", "Maintains recovery."),
            entry("Wednesday", "Treadmill cardio and core", "25 to 30 minutes treadmill walk or easy jog, then brief core work.", 45, "Easy to moderate, still comfortable.", "Builds fitness while staying indoors and controlled."),
            entry("Thursday", "Rest", "Light mobility.", 10, "Very easy.", "Helps keep the back settled."),
            entry("Friday", "Indoor full-body gym B", "Repeat Friday's pattern with modest progression and no heavy spinal loading.", 55, "RPE 7.", "Maintains gym progress safely."),
            entry("Saturday", "Optional indoor fitness day", "20 to 25 minutes treadmill walking plus easy machine accessories if desired.", 30, "Easy.", "Keeps the optional day safe and simple."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Sets up the easier final week."),
        ],
        [
            entry("Monday", "Indoor full-body gym A", "Reduce total sets and keep the same easy-to-learn exercise pattern.", 50, "RPE 6.", "Deloads fatigue and reinforces consistency."),
            entry("Tuesday", "Rest", "Full rest.", 0, "Rest.", "Maintains recovery."),
            entry("Wednesday", "Treadmill cardio and core", "20 minutes treadmill walking or easy jog plus short core work.", 35, "Easy.", "Keeps the cardio habit without extra strain."),
            entry("Thursday", "Rest", "Light mobility only.", 10, "Very easy.", "Supports comfort."),
            entry("Friday", "Indoor full-body gym B", "Shortened full-body gym session with the same supported movements.", 50, "RPE 6.", "Ends the block in a repeatable state."),
            entry("Saturday", "Optional indoor fitness day", "15 to 20 minutes treadmill walking only if desired.", 20, "Easy.", "Leaves room for recovery and choice."),
            entry("Sunday", "Rest", "Full rest.", 0, "Rest.", "Closes the block recovered."),
        ],
    ]
    return {
        "summary": summary,
        "weeks": weeks,
        "tradeoff": "The plan keeps both gym work and treadmill cardio in the week, but the gym sessions stay simple and back-aware while cardio stays easy and indoor-based. That trade-off supports the primary habit goal better than a more intense or outdoor-focused program would.",
        "safety": [
            "Avoid heavy free-weight spinal loading and high-skill barbell movements while the lower back is a recurring issue.",
            "Use indoor treadmill work at easy effort rather than building an outdoor running program.",
            "Keep core work simple and supportive instead of aggressive fatigue-based circuits.",
            "If the back feels more irritated after gym day, reduce lower-body load or switch to more supported machine work.",
        ],
        "progression": "Week 1 establishes an indoor-friendly routine. Week 2 adds a small amount of work. Week 3 is the strongest week, still within beginner limits. Week 4 reduces volume so the user can continue the habit comfortably.",
        "tradeoff_extract": "The main conflict is combining a beginner fitness plan with treadmill cardio while avoiding lower-back aggravation and overcomplicated gym work.",
        "strategy": [
            "Prioritize a simple indoor habit over ambitious strength or running progress.",
            "Keep cardio treadmill-based and easy because that matches preference and safety needs.",
            "Use supported gym exercises that limit lower-back stress.",
            "Progress gradually and finish with a lighter week to improve sustainability.",
        ],
        "self_check": [
            "Does the plan respect the primary goal? Yes, it centers on safe consistency and general fitness.",
            "Does the plan stay within schedule constraints? Yes, it uses three main days plus one optional lighter day.",
            "Does the plan address physical limitations? Yes, lower-back discomfort shapes both gym and cardio choices.",
            "Does the plan avoid obvious running-lifting conflicts? Yes, treadmill cardio stays easy and gym work stays back-aware.",
        ],
    }


PLAN_BUILDERS = {
    "P1": p1_plan,
    "P2": p2_plan,
    "P3": p3_plan,
    "P4": p4_plan,
    "P5": p5_plan,
    "P6": p6_plan,
    "P7": p7_plan,
    "P8": p8_plan,
    "P9": p9_plan,
    "P10": p10_plan,
}


PERSONAS = [
    {
        "id": "P1",
        "age": "25",
        "training_background": "Experienced in both weight training and running; regularly runs 10 km and half marathon distances.",
        "primary_goal": "Hypertrophy",
        "secondary_goal": "Maintain running performance",
        "schedule_constraint": "Can train up to 6 days per week, up to 90 minutes per session.",
        "injury_or_limitation": "No major injury reported.",
        "preferences": "Wants to keep both lifting and running, enjoys structured training, and does not want to give up lower-body training.",
        "dislikes": "Does not want a plan that sacrifices either lifting or running completely.",
    },
    {
        "id": "P2",
        "age": "29",
        "training_background": "Recently started weight training; beginner level with low flexibility.",
        "primary_goal": "Build strength and muscle",
        "secondary_goal": "Improve general fitness",
        "schedule_constraint": "3 to 4 days per week, around 60 minutes per session.",
        "injury_or_limitation": "No injury reported, but flexibility is limited.",
        "preferences": "Prefers gym training over running.",
        "dislikes": "Does not enjoy running-focused plans.",
    },
    {
        "id": "P3",
        "age": "25",
        "training_background": "Enjoys both weight training and running; running is mainly used for fat loss.",
        "primary_goal": "Fat loss while maintaining muscle",
        "secondary_goal": "Maintain exercise routine",
        "schedule_constraint": "Around 5 days per week, 70 to 80 minutes per session.",
        "injury_or_limitation": "Occasional calf injury issues.",
        "preferences": "Likes both lifting and running, but sees running mainly as a conditioning and fat-loss tool.",
        "dislikes": "Does not need performance-oriented running plans.",
    },
    {
        "id": "P4",
        "age": "27",
        "training_background": "Beginner in weight training; running only occasionally as a hobby.",
        "primary_goal": "Build a sustainable gym habit and basic fitness",
        "secondary_goal": "Mild body composition improvement",
        "schedule_constraint": "3 days per week, around 60 minutes per session.",
        "injury_or_limitation": "No major injury reported.",
        "preferences": "Mainly interested in gym training and is okay with light occasional running.",
        "dislikes": "Does not want an overly complicated plan.",
    },
    {
        "id": "P5",
        "age": "27",
        "training_background": "More interested in running than weight training; does lifting mainly for aesthetics.",
        "primary_goal": "Improve or maintain running performance and enjoyment",
        "secondary_goal": "Build a lean, aesthetic physique",
        "schedule_constraint": "About 5 days per week, 60 to 75 minutes per session.",
        "injury_or_limitation": "No major injury reported.",
        "preferences": "Enjoys running more and wants lifting to be efficient and supportive.",
        "dislikes": "Does not want a bodybuilding-style plan to dominate the schedule.",
    },
    {
        "id": "P6",
        "age": "24",
        "training_background": "Consistently active; has completed a half marathon and also does regular weight training.",
        "primary_goal": "Sustainable long-term health and balanced hybrid training",
        "secondary_goal": "Maintain both running ability and general strength",
        "schedule_constraint": "4 to 5 days per week, 60 to 80 minutes per session.",
        "injury_or_limitation": "Has a congenital limitation in the left upper limb, with reduced shoulder range of motion and weaker grip strength on that side.",
        "preferences": "Wants a balanced and realistic plan and wants to keep both running and gym training.",
        "dislikes": "Does not want a generic one-size-fits-all plan that ignores his physical limitation.",
    },
    {
        "id": "P7",
        "age": "23",
        "training_background": "Almost no exercise experience; very underweight and regularly carries a heavy bag.",
        "primary_goal": "Build basic strength and muscle mass",
        "secondary_goal": "Establish a stable exercise habit",
        "schedule_constraint": "3 days per week, 45 to 60 minutes per session.",
        "injury_or_limitation": "Frequent lower-back discomfort.",
        "preferences": "Wants to start gym training safely.",
        "dislikes": "Should avoid overly intense or intimidating programs.",
    },
    {
        "id": "P8",
        "age": "24",
        "training_background": "Occasionally does gym workouts.",
        "primary_goal": "Exercise safely and consistently",
        "secondary_goal": "Improve lower-body and general fitness without worsening pain",
        "schedule_constraint": "3 to 4 days per week, around 60 minutes per session.",
        "injury_or_limitation": "Knee pain.",
        "preferences": "Wants to keep exercising but cautiously.",
        "dislikes": "Should avoid knee-aggravating activities.",
    },
    {
        "id": "P9",
        "age": "22",
        "training_background": "Likes both weight training and running; previously trained a lot, but is currently inconsistent.",
        "primary_goal": "Rebuild a sustainable exercise routine",
        "secondary_goal": "Recover fitness and physique",
        "schedule_constraint": "Wants to train 4 days per week, around 60 minutes per session, but adherence may be unstable.",
        "injury_or_limitation": "No major injury; physically healthy.",
        "preferences": "Likes both running and lifting.",
        "dislikes": "Does not benefit from unrealistic all-or-nothing plans.",
    },
    {
        "id": "P10",
        "age": "23",
        "training_background": "Beginner; likes gym workouts and treadmill running.",
        "primary_goal": "Improve general fitness and build a healthy exercise habit",
        "secondary_goal": "Basic body composition improvement",
        "schedule_constraint": "3 to 4 days per week, 50 to 60 minutes per session.",
        "injury_or_limitation": "Frequent lower-back pain due to carrying a heavy bag.",
        "preferences": "Prefers indoor exercise and treadmill running.",
        "dislikes": "Likely to dislike plans centered on outdoor running or high-skill barbell movements.",
    },
]


def revise_weeks(persona_id, original_weeks):
    revised = copy.deepcopy(original_weeks)
    problems = []
    changes = []

    if persona_id == "P1":
        problems = [
            "The original plan was broadly aligned, but the Friday run in the highest-fatigue week could be a little too steady before Saturday lower-body hypertrophy.",
            "Week 4 deload was good, but the rationale for keeping running clearly secondary could be stated more explicitly.",
        ]
        revised[2][4]["details"] = "35 minutes easy steady running, fully conversational, followed by 8 minutes light mobility."
        revised[2][4]["intensity"] = "Mid Zone 2 only."
        revised[2][4]["reason"] = "Keeps running maintenance in place while protecting Saturday lower-body recovery more clearly."
        changes = [
            "Reduced the Week 3 Friday run from a higher steady effort to a clearly easy maintenance effort.",
            "Preserved all lifting structure because it already matched the hypertrophy-first goal well.",
        ]
    elif persona_id == "P2":
        problems = [
            "The original plan fit a beginner well, but mobility emphasis could be more explicit on every lifting day given the user's low flexibility.",
        ]
        for week in revised:
            for idx in [0, 2, 4]:
                week[idx]["details"] = "Begin with 8 to 10 minutes of hip, ankle, and thoracic mobility, then perform the planned lifting session with stable machine and dumbbell patterns."
        changes = [
            "Made the flexibility-focused warm-up explicit on every main gym day.",
            "Left the rest of the structure unchanged because the beginner-friendly split was already sound.",
        ]
    elif persona_id == "P3":
        problems = [
            "The original plan already treated running as secondary, but Week 3 still left room for calf irritation because a run was retained at the end of the heaviest week.",
        ]
        revised[2][6]["focus"] = "Low-impact conditioning"
        revised[2][6]["details"] = "20 to 25 minutes easy incline walk, bike, or elliptical instead of running for this week."
        revised[2][6]["reason"] = "Removes unnecessary calf risk during the heaviest lifting week while keeping conditioning in place."
        changes = [
            "Replaced the Week 3 Sunday run-walk with low-impact conditioning.",
            "Kept the lifting structure unchanged because muscle retention remained the correct priority.",
        ]
    elif persona_id == "P4":
        problems = [
            "The original plan was appropriately simple, but the optional jog wording could still encourage unnecessary add-ons in a beginner trying to build consistency.",
        ]
        for week in revised:
            week[5]["focus"] = "Rest or easy walk"
            week[5]["details"] = "Rest by default; optional easy walk only."
            week[5]["reason"] = "Keeps the plan even simpler and more sustainable for a beginner habit phase."
        changes = [
            "Removed the optional jog and kept only optional walking.",
            "Preserved the three-day gym structure because it already matched the main goal well.",
        ]
    elif persona_id == "P5":
        problems = [
            "The original plan already prioritized running, but Tuesday lower-body work could still slightly dampen Friday run quality if volume drifts upward.",
        ]
        revised[2][1]["details"] = "Repeat the same lifting menu, but keep lower-body work to 2 controlled sets on leg press and split squat while maintaining upper-body volume."
        revised[2][1]["reason"] = "Keeps lifting supportive while protecting the running-focused week."
        changes = [
            "Capped lower-body volume more clearly in the hardest running week.",
            "Left the overall run-first schedule unchanged.",
        ]
    elif persona_id == "P6":
        problems = [
            "The original plan accounted for the left upper-limb limitation, but the need for grip assistance and ROM modification could be stated more explicitly on upper-body days.",
        ]
        revised[0][2]["details"] = "Single-arm cable press, chest-supported row, neutral-grip pulldown, machine chest press with adjusted range, landmine press only if stable, and straps or assisted grip work where useful."
        revised[2][2]["details"] = "Repeat the same safe exercise menu, explicitly using straps, cuff attachments, or assisted grips where helpful and avoiding forced overhead range."
        changes = [
            "Made grip-assisted and ROM-modified options more explicit on upper-body training days.",
            "Kept the balanced hybrid structure unchanged because it already fit the goal and schedule.",
        ]
    elif persona_id == "P7":
        problems = [
            "The original plan was safe overall, but one squat pattern could still be interpreted too aggressively for a very underweight beginner with recurring lower-back discomfort.",
        ]
        revised[0][2]["details"] = "Supported sit-to-stand or leg press, machine chest press, seated row, hamstring curl, low step-up if comfortable, and side plank."
        revised[0][2]["reason"] = "Uses an even more supported lower-body pattern for an especially cautious start."
        changes = [
            "Replaced the more demanding squat pattern in the first week with a more supported option.",
            "Preserved the three-day beginner structure and low intensity.",
        ]
    elif persona_id == "P8":
        problems = [
            "The original plan was knee-aware, but the optional flat walking suggestion on a rest day was unnecessary because conditioning already appears elsewhere.",
        ]
        revised[0][1]["details"] = "Full rest."
        revised[0][1]["duration"] = 0
        revised[0][1]["reason"] = "Keeps recovery cleaner between sessions when knee symptoms are the main constraint."
        changes = [
            "Made the first rest day a true rest day instead of suggesting optional walking.",
            "Kept the low-impact cardio and modified lower-body structure unchanged.",
        ]
    elif persona_id == "P9":
        problems = [
            "The original plan was adherence-friendly, but it could support inconsistent weeks even better by defining a minimum viable session option.",
        ]
        revised[1][5]["details"] = "15 to 20 minutes easy cardio plus 1 to 2 accessory movements only if time and energy are good; otherwise stop after the easy cardio."
        revised[1][5]["reason"] = "Adds an explicit fallback option that supports adherence during unstable weeks."
        changes = [
            "Added a minimum viable session option to the lighter Saturday day.",
            "Left the overall four-day rebuild structure unchanged.",
        ]
    elif persona_id == "P10":
        problems = [
            "The original plan matched the indoor preference well, but the easy jog wording could still be a little too casual for someone with recurring lower-back pain.",
        ]
        for week in revised:
            week[2]["details"] = week[2]["details"].replace("walk or easy jog", "walk or brisk walk")
            week[2]["reason"] = "Keeps indoor cardio beginner-friendly while reducing unnecessary back irritation risk."
        changes = [
            "Shifted treadmill guidance toward walking or brisk walking instead of jogging.",
            "Preserved the simple indoor gym structure because it already fit the user well.",
        ]
    else:
        problems = ["No major problems were found; the original plan was already well aligned and safe."]
        changes = ["No structural changes were required."]

    why_better = (
        "The revised version improves the plan by clarifying the main priority, tightening fatigue or irritation control, "
        "and preserving the original structure everywhere that already worked. That keeps primary-goal alignment, safety, "
        "trade-off handling, and four-week coherence intact without rewriting a plan that was already mostly sound."
    )
    return {
        "problems": problems,
        "weeks": annotate_revision_status(original_weeks, revised),
        "changes": changes,
        "why_better": why_better,
    }


def build_samples():
    samples = []
    for persona in PERSONAS:
        plan_data = PLAN_BUILDERS[persona["id"]]()
        a_text = render_condition_a(persona, plan_data)
        b_text = render_condition_b(persona, plan_data)
        c_review = revise_weeks(persona["id"], plan_data["weeks"])
        c_text = render_condition_c(c_review)
        d_text = a_text

        base = {
            "user": {
                "age": persona["age"],
                "training_background": persona["training_background"],
                "primary_goal": persona["primary_goal"],
                "secondary_goal": persona["secondary_goal"],
                "schedule_constraint": persona["schedule_constraint"],
                "injury_or_limitation": persona["injury_or_limitation"],
                "preferences": persona["preferences"],
                "dislikes": persona["dislikes"],
            },
            "metadata": {
                "prompt_version": "v1",
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2048,
                "seed": 42,
            },
        }

        samples.append(
            {
                **base,
                "condition": "A",
                "model_name": "Qwen 3 8B",
                "solution_raw_text": a_text,
            }
        )
        samples.append(
            {
                **base,
                "condition": "B",
                "model_name": "Qwen 3 8B",
                "solution_raw_text": b_text,
            }
        )
        samples.append(
            {
                **base,
                "condition": "C",
                "model_name": "Qwen 3 32B",
                "solution_raw_text": c_text,
                "original_plan": a_text,
                "revised_plan": c_text,
            }
        )
        samples.append(
            {
                **base,
                "condition": "D",
                "model_name": "Qwen 3 32B",
                "solution_raw_text": d_text,
            }
        )
    return samples


def main():
    samples = build_samples()
    OUTPUT_PATH.write_text(json.dumps(samples, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(samples)} samples to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
