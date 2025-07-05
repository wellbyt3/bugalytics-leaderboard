# A Possible Solution For Broken Incentives in Audit Contest

**TLDR**
- Audit contests have contributed immensely to blockchain security, but a recent misalignment of incentives threaten their effectiveness and ultimately weakens security for protocols.
- One potential solution for realigning incentives is to better educate protocols, security researchers, and contest platforms utilizing real contest data.
- The critical missing piece is a reliable method for quantifying the skill level of security researchers, which would reveal the talent each contest attracts. Comparing the talent attracted by different contests can help us better understand how to structure contests effectively.
- I propose using **TrueSkill**, a Microsoft algorithm originally created for ranking gamers (e.g., Call of Duty), adapted specifically for security contests. This repo contains a beta implementation of TrueSkill tuned for this purpose.
- If you’d rather skip the Python and just view the rankings and scores directly, visit the leaderboard at [bugalytics.xyz/leaderboard](https://bugalytics.xyz/leaderboard).
- For a lot more context, keep reading...

## Background
Code4rena’s popularization of security contests marked a pivotal moment in blockchain security. It’s not machines keeping the ecosystem safe (yet), it’s people. Individual security researchers. And audit contests have played a critical role in attracting and onboarding this talent into the space. Many of today's top security researchers got their start on Code4rena or Sherlock.

When incentives align properly, audit contests consistently deliver the highest quality security due to the sheer number of sharp minds reviewing the code. [One analysis](https://diligence.consensys.io/blog/2024/04/diving-deep-into-audit-contests-analytics-and-economics/) demonstrated it takes an average of 13 people to find all bugs in a codebase — far more than the typical audit firm team of ~4. But today, security contests are struggling to get these incentives right. Conditional pots that guarantee only a fraction of the advertised prize, shrinking rewards relative to the amount of code reviewed, ever-growing and more complex codebases, and "time-boxed bug bounties" disguised as contests have become commonplace. 

Anyone working in security can see the problem — **when contests fail to attract top talent, protocols get weaker security — and that hurts everyone.**

Yet most protocols can't see this clearly. They’re focused on building their product and rely on security providers for guidance on how to approach security. While many firms and platforms operate with high integrity, others do not. Regardless, all are influenced by incentives, which can be at odds with protocols receiving the highest quality and most efficient security outcomes.

One potential solution is to better educate the customer (i.e. protocol) so they understand what they're buying and why. Currently, most of the information they're receiving comes in the form of opinions from security providers. Sometimes these opinions are credible and accurate, others frankly sucks. But we need more than just opinions. We need data.

Fortunately, this data already exists. It just hasn't yet been presented in a clear, actionable format that provides meaningful insights we as an industry can use. Over the last few weeks, I've been setting up data pipelines, cleaning contest data, and have begun publishing analyses using this data on my Twitter and now bugalytics(dot)xyz. 

While analyzing this data, I realized something crucial is missing:
**A reliable way to quantify the skill of a security researcher.**

Having this data point unlocks answers to some of our most pressing questions about audit contests:
- What is the optimal $ per nSLOC to attract a certain skill level of competitor?
- Which platforms attract the highest skilled security researchers?
- Do conditional pots attract a lower total skill?
- Does the model of the specific platforms matter?
- And much, much more.

To fill this gap, I've developed an approach to quantitfying the skill of a security researcher — and the beta version is ready.

Enter TrueSkill.

## TrueSkill: Quantifying the Skill of Security Researchers

TrueSkill, developed by Microsoft Research, is an algorithm originally used to rank gamers (e.g., Call of Duty) based on match outcomes.

Security contests have many similarities to free-for-all Call of Duty matches, so the Trueskill algorithm (with some tweaks to the input parameters) works great for measuring security researcher's skill.

### How TrueSkill Works

TrueSkill assigns each researcher a skill level represented as a normal distribution (bell curve). This distribution is represented by:

- μ (mu): the researcher’s estimated skill (mean skill level).
- σ (sigma): the uncertainty around the researcher’s skill. A larger σ indicates greater uncertainty, whereas a smaller σ means greater certainty.

When a researcher participates in a contest, TrueSkill updates their μ and σ based on their performance relative to other participants. Winning increases μ, and consistently strong performances reduce σ.

### Why TrueSkill Outperforms Leaderboards at Measuring Skill

Contest platform leaderboards rank security researchers roughly by the amount they've earned. Amount earned correlates to skill, but there are some problems measuring skill this way:
1. Ignores strength of competition. Earning $20k by beating low-skill opponents is treated the same as earning $20k by outperforming top-tier researchers — even though the latter is a much stronger signal of skill.
2. Ignores talent dilution from overlapping contests. Winning means less when top researchers are busy elsewhere.
3. Not all leaderboards are equally competitive. It’s hard to compare the top researcher on one platform to the top of another.
4. Most researchers compete on all the platforms, but leaderboards only take into account performance on their platform.

Merging data from all platforms and applying TrueSkill solves these problems, producing a single, consistent skill score and leaderboard for researchers across the entire contest ecosystem.

**The main key takeaway: TrueSkill doesn’t just reward wins, it rewards beating strong opponents.**

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

## The bugalytics.xyz Leaderboard

The V1 implementation of TrueSkill is live on bugalytics(dot)xyz as a public leaderboard.

I chose to publish it as a leaderboard for a simple reason: it’s the easiest format for the security researcher community to view, interpret, and give feedback on.

So go check it out — and DM me on Twitter or message me on Telegram with your thoughts.

I’m especially looking for examples where you think the rankings could be improved. If you believe a certain researcher is ranked too high or too low, tell me why — what signals or context might TrueSkill be missing?

While I think this leaderboard is already a better signal of real skill than any contest platform-specific ranking, the leaderboard itself isn’t the point.

The real value comes only if the security researcher community agrees that this is the most credible, directionally accurate representation of skill we have.

If we reach that shared belief, then the underlying scores can be used to analyze contest dynamics, measure platform quality, understand what drives researcher participation and performance — and ultimately, figure out how to deliver the highest level of security to the protocols that rely on us.

I can’t produce meaningful answers unless the community believes in the data. So please: **review the leaderboard, challenge it, help improve it — and let’s make something we all trust.**

## Contributions
If you're interested in helping me refine this system, contributions are welcome and appreciated.

Here's how to get started:

1. Clone the repo
2. Install dependencies listed in requirements.txt: `pip install -r requirements.txt`
3. Run the script:  `python main.py`

The script injests `input-trueskill.csv`, runs the Trueskill algorithm, and then outputs:
- `output-trueskill.csv`: the current scores up to the most recent contest in the dataset
- `output-trueskill-history.csv`: the histroical scores after each contest. This gives us a snapshot of skill at a specific point in time, which is important for tracking how skill changes over time and for future analysis.

Here are some TrueSkill resources I found useful when building this:
- https://www.moserware.com/assets/computing-your-skill/The%20Math%20Behind%20TrueSkill.pdf
- https://trueskill.org/
- https://en.wikipedia.org/wiki/TrueSkill

DM me on Telegram if you want to collaborate, @wellbyt3.

## Special Thanks
Highly recommend reading the following:
- [@joranhonig](https://x.com/joranhonig) for writing ["Diving deep into Audit Contests Analytics and Economics,"](https://diligence.consensys.io/blog/2024/04/diving-deep-into-audit-contests-analytics-and-economics/) which introduced me to TrueSkill.
- [@0xEV_om](https://x.com/0xEV_om) for writing ["Meritocracy or Mirage? Fixing the Contest Crisis,"](https://x.com/0xEV_om/status/1937537990860927102) which helped a lot in clarifying the problems audit contests currently face.
- [@jack__sanford](https://x.com/jack__sanford) for writing ["Audit Contests Are Dead, Long Live Audit Contests,"](https://x.com/jack__sanford/status/1920453729603514555) another piece that shines light on the problems contests currently face.

