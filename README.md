# Quantifying Security Researcher Skill Using TrueSkill and Contest Performance

**TLDR**
I used the TrueSkill algorithm to rank security researchers based on their historical contest performance. See the results at [bugalytics.xyz/leaderboard](https://bugalytics.xyz/leaderboard).

## Background
Code4rena’s popularization of security contests marked a turning point in blockchain security. It’s not machines keeping the ecosystem safe (yet), it’s people. And audit contests have played a crucial role in attracting and onboarding this talent into the space. Many of today's top security researchers got their start on Code4rena or Sherlock.

When incentives align properly, audit contests deliver superior security because there are more eyes on the code. [One analysis](https://diligence.consensys.io/blog/2024/04/diving-deep-into-audit-contests-analytics-and-economics/) demonstrated it takes an average of 13 people to find all bugs in a codebase — far more than the typical audit firm team of ~4. But today, security contests are struggling to get these incentives right. Conditional pots that guarantee only a fraction of the advertised prize, shrinking rewards relative to the amount of code reviewed, ever-growing and more complex codebases, and "time-boxed bug bounties" disguised as contests have become commonplace. 

The issue is clear — **when contests fail to incentivize top talent, protocols receive weaker security.**

One solution is leveraging historical contest data to measure contest effectiveness. Protocols and contest platforms can use this data to optimize rules, prize amounts, and structures for future contests.

I'm currently working on this solution at [bugalytics.xyz](bugalytics.xyz).

## Quantifying Skill

Skill is an interesting dimension to look at contest effectiveness through.

By measuring the skill level of participants, we can better evaluate a contest's overall efficacy.

Enter TrueSkill.

## TrueSkill: Quantifying the Skill of Security Researchers

TrueSkill, developed by Microsoft Research, is an algorithm originally used to rank gamers (e.g., Call of Duty) based on match outcomes.

Security contests have many similarities to free-for-all Call of Duty matches, so the Trueskill algorithm (with some tweaks) works well for quantifying skill.

### How TrueSkill Works

TrueSkill assigns each researcher a skill level represented as a normal distribution. This distribution is represented by:

- μ (mu): the researcher’s estimated skill (mean skill level).
- σ (sigma): the uncertainty around the researcher’s skill. A larger σ indicates greater uncertainty, whereas a smaller σ means greater certainty.

When a researcher participates in a contest, TrueSkill updates their μ and σ based on their performance relative to other participants. Winning increases μ, and consistently strong performances reduce σ.

**The main key takeaway: TrueSkill doesn’t just reward wins, it rewards beating strong opponents.**

### Why TrueSkill Outperforms Leaderboards at Measuring Skill

Contest platform leaderboards rank security researchers roughly by the amount they've earned. Amount earned correlates to skill, but there are some problems measuring skill this way:
1. Ignores strength of competition. Earning $20k by beating low-skill opponents is treated the same as earning $20k by outperforming top-tier researchers — even though the latter is a much stronger signal of skill.
2. Ignores talent dilution from overlapping contests. Winning means less when top researchers are busy elsewhere.
3. Certain contests have much less comeptition due to their niche. For example, non-Solidity contests.
4. Not all leaderboards are equally competitive. It’s hard to compare the top researcher on one platform to the top of another.
5. Leaderboards only take into account performance on their platform, but many researchers have competed on multiple platforms.

Merging data from all platforms and applying TrueSkill solves a lot of these problems.

### Tuning TrueSkill For Security Contests
While security contests have many similarities to games like Call of Duty, there are also some significant differences. Thus, the default TrueSkill parameters require adjustment to account for the unique nuances of security contests.

Below is a quick overview of each parameter and how its been adjusted to better fit audit contest dynamics.

#### μ (mu), σ (sigma), and C (certainty-multiplier)
Remember, mu represents the researcher’s estimated (mean) skill, sigma is the uncertainty around the researcher’s skill, and that everyone begins with the same mu and sigma. 

Mu is only an anchor point for our skill scale, so it doesn't matter what we set it to initially.

The default TrueSkill sigma is ~8.33, but in this implementation, it's increased to 12 to better reflect the uncertainty in security contests. A higher sigma prevents newcomers from ranking too high after a single strong showing and ensures researchers must prove themselves across multiple contests.

To calculate a researcher’s skill score, we use TrueSkill to generate their updated μ (mu) and σ (sigma), then apply:

`Skill Score = μ – C × σ`

C is the “certainty multiplier.” It controls how much we penalize uncertainty. A higher C makes individual contest results count less, placing more weight on consistent performance over time. Researchers with lower sigma are less affected, rewarding proven track records. The default C is 3, whereas in this TrueSkill implementation, it's set to 4.5.

#### β (beta)

β (beta) controls performance noise, or how much a contest result can deviate from actual skill. A high β means each result is treated as noisy, so ratings (μ) update slowly and uncertainty (σ) shrinks gradually. In this implementation, β = 12 to reflect the reality that researcher effort varies per contest. A top skilled researcher might do poorly on a one off contest, but only because they spent 2 hours on it. A high β prevents one-off results from overly impacting their rating.

#### τ (tau)

τ (tau) is TrueSkill’s “drift” or “rust” factor. Before each rating update, it slightly increases a researcher’s uncertainty by adding `τ²` to `σ²` and then taking the square root, modeling the idea that skill can change or become harder to assess over time.

In security, many top researchers transition to private audits after proving themselves in contests. Their skill may keep growing, but public evidence fades. Conversely, someone who excelled in 2022 but has since focused on development or running a company may be out of practice.

Tau applies a slow, steady penalty for inactivity. 

This implementation takes the following stance: If you claim to be one of the best, you should prove it a couple times a year in the contest scene. Blockchain security is unique in that it provides this opportunity to literally everyone. If you don’t, contest results (or the lack of them) speak louder than your sales and marketing ever could.

### Effort

One significant difference between a security contest and a game like Call of Duty is participant effort. In gaming, player effort remains relatively consistent, while in security contests it varies widely. Even elite researchers can perform poorly simply due to low effort.

To account for this, the algorithm excludes each researcher's worst contest performances when calculating TrueSkill scores. The more contests a researcher participates in, the higher the exclusion percentage. (See contest-exclusion-percentage.csv for exact details.)

### Solo Leaderboards
Occasionally, a researcher might be the only participant listed on a contest leaderboard. In these cases, the algorithm generates simulated participants whose skills match average researcher levels from similar prize pools. This ensures the solo researcher still receives an appropriate TrueSkill adjustment for their performance.

### Total Earnings

Currently, the leaderboard at [bugalytics.xyz](bugalytics.xyz/leaderboard) combines TrueSkill scores (weighted 75%) with total contest earnings (weighted 25%). Incorporating earnings smooths out minor discrepancies that arise from directly adapting TrueSkill, originally designed for gaming, to security contests.

## Feedback and Contributions

I chose to publish this as a leaderboard because it's an easy format to view, interpret, and give feedback on.

So go check it out — and DM me on Twitter or message me on Telegram (@wellbyt3) with your thoughts.

I’m especially looking for examples where you think the rankings could be improved. If you believe a certain researcher is ranked too high or too low, tell me why — what signals or context might TrueSkill be missing?

If you're interested in helping me refine this system, contributions are welcome and appreciated.

Here's how to get started:

1. Clone the repo
2. Install dependencies listed in requirements.txt: `pip install -r requirements.txt`
3. Run the script:  `python main.py`

The script injests `input-trueskill.csv`, runs the Trueskill algorithm, and then outputs:
- `output-trueskill.csv`: the current scores up to the most recent contest in the dataset
- `output-trueskill-history.csv`: the histroical scores after each contest. This gives us a snapshot of skill at a specific point in time, which is important for tracking how skill changes over time and for future analysis.

Here are some TrueSkill resources I found useful when building this:
- [The Math Behind TrueSkill](https://www.moserware.com/assets/computing-your-skill/The%20Math%20Behind%20TrueSkill.pdf)
- [TrueSkill.org](https://trueskill.org/)
- [TrueSkill on Wikipedia](https://en.wikipedia.org/wiki/TrueSkill)

## Credit
- [@joranhonig](https://x.com/joranhonig) wrote ["Diving deep into Audit Contests Analytics and Economics,"](https://diligence.consensys.io/blog/2024/04/diving-deep-into-audit-contests-analytics-and-economics/) which introduced me to TrueSkill.
- [@Guhu95](https://x.com/Guhu95) wrote a piece on [measuring how vulnerable code is after a contest](https://x.com/Guhu95/status/1938224258515448042) and provided a ton of helpful feedback and clarifying thoughts on the nuances of measuring contest efficacy.
- [@0xEV_om](https://x.com/0xEV_om) wrote ["Meritocracy or Mirage? Fixing the Contest Crisis,"](https://x.com/0xEV_om/status/1937537990860927102) which helped a lot in clarifying the problems audit contests currently face.
- [@jack__sanford](https://x.com/jack__sanford) wrote ["Audit Contests Are Dead, Long Live Audit Contests,"](https://x.com/jack__sanford/status/1920453729603514555) which is another article that shines light on the problems contests currently face.

