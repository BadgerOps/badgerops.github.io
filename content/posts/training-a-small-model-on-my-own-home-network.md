---
title: "Training a Small Model on My Own Home Network"
slug: "training-a-small-model-on-my-own-home-network"
date: 2026-10-04T16:31:01Z
lastmod: 2026-10-04T16:31:01Z
draft: false
description: "I have been using LLMs for years without ever training one. So I spent a few weeks teaching a 0.6B model to answer questions about my own UniFi network, and learned that my measuring stick was broken, my control group was a lucky pair,…"
topics: ["AI", "Homelab", "Machine Learning", "networking", "UniFi"]
aliases: ["/2026/10/04/training-a-small-model-on-my-own-home-network/"]
migration_source: ghost
---
<p><em>(Or, me fighting a 0.6B model and my own measurement errors, in that order)</em></p>
<p>I have been using LLMs for a couple of years now - well, since ChatGPT was announced. I have not, until this summer, actually <em>trained</em> one.</p>
<p>Knowing fine-tuning exists and having done it are different things. So I went and did it, end to end: data curation, SFT, LoRA, preference tuning, RL, quantization. The whole ladder.</p>
<p>The immediate problem was picking something to train it <em>on</em>.</p>
<p>Most fine-tuning tutorials train on text. Summarize this, rewrite that, answer in the voice of a pirate. Which is fine, except that when you are done you have no idea if it worked. LLMs spit out text for a living - I wanted something gradeable.</p>
<p>So I trained mine on my own home network instead.</p>
<h2 id="why-the-network">Why the network</h2>
<p>I have a UDM Pro, a handful of APs and switches, a Prometheus stack on <code>guiltyspark</code>, and a NixOS fleet with Halo-themed hostnames because I am who I am. That is a pile of real, queryable data.</p>
<p>If I teach a small model to turn "what's on the guest wifi?" into a tool call, the grader can't* make stuff up. It has to return real data.</p>
<p>*yes, of course it <em>could</em>. The point is making it not.</p>
<p>Either the model named a real tool with valid arguments, or it did not. Either the call returned data from the live controller, or it threw an error. Ideally.</p>
<p>To be clear: the model is <em>not</em> the detector. Prometheus rules and unpoller already do detection, deterministically and testably. The model is just the language surface on top.</p>
<pre><code>detection    Prometheus rules, Loki, unpoller, blackbox   (already built)
   |
   v
tools        16 typed verbs. Parameterized query catalog, NOT free PromQL.
   |
   v
SLM          llama.cpp + GBNF grammar -&gt; output is always a valid call
   |
   v
policy       reads auto-run, writes only ever *proposed*, human confirms
</code></pre>
<p>The deliverable was never "a useful tool." My 27B already answers these questions better than anything I was going to train. The deliverable was the training.</p>
<h2 id="the-box">The box</h2>
<p>All of this runs on my old Gaming PC <code>optimus</code> - a Legion T7 with a 12700K and the RTX 3090 I moved over in August. (Yes, Optimus. Transformers are just as cool as Halo, right?)</p>
<blockquote>
<p>Incidentally, I'm running <a href="https://bazzite.gg/">Bazzite</a> on this host, I've used quote a few immutable distros over the  years, starting with CoreOS (Shoutout to Brian 'Redbeard').</p>
</blockquote>
<p>The 3090 was already busy serving a 27B at Q4, which eats 17.9 of the 23.6 GB available. So before writing a line of training code I measured what would actually fit next to it:</p>
<table>
<thead>
<tr>
<th>Qwen3-0.6B bf16</th>
<th>peak VRAM</th>
<th>with the 27B up</th>
</tr>
</thead>
<tbody>
<tr>
<td>load + generate</td>
<td>1.19 GB</td>
<td>fine</td>
</tr>
<tr>
<td>LoRA r=16, grad checkpointing</td>
<td>1.66 GB</td>
<td>fits</td>
</tr>
<tr>
<td>full fine-tune backward</td>
<td>&gt;3 GB</td>
<td>OOM</td>
</tr>
</tbody>
</table>
<p>That table decided a lot. LoRA coexists with inference. A full fine-tune means stopping the 27B first. Desktop apps hold about 900 MB, so budget that too.</p>
<p>The training environment lives in its own Distrobox called <code>netmon-train</code>, deliberately separate from the <code>llamacpp</code> box. A torch upgrade should never be able to take the 27B down as collateral damage. I have been burned by shared Python environments enough times to stop pretending it is fine.</p>
<h2 id="rule-zero-build-the-referee-before-the-player">Rule zero: build the referee before the player</h2>
<p>This is the part worth stealing.</p>
<p>Before any training, I built a second repo, <code>netmon_evals</code>, that exists only to grade. 208 questions, each with the tool call that correctly answers it. A tool contract. A scorer. A sha256 manifest so <code>validate.py</code> fails loudly if anyone edits the question set. (Anyone = future me.)</p>
<blockquote>
<p>This, of course, is a  recommended path - I didn't figure it out on my own. Learning from others is important!</p>
</blockquote>
<p>Two rules, both written down early because I knew I would want to break them later:</p>
<ol>
<li>Never train on <code>eval/</code>. Check overlap before every single run.</li>
<li>Never edit <code>questions.jsonl</code> in place. A changed set silently invalidates every score you have already recorded.</li>
</ol>
<p>19 of the 208 are unanswerable or ambiguous on purpose. The scorer reports refusal recall <em>and</em> over-refusal separately, because a model that answers "which device did you mean?" to everything scores beautifully on the first one and is completely useless.</p>
<p>Scoring is on tool-call correctness, never answer text. Client counts around here change hourly. An answer-text eval would rot in a day.</p>
<p>Then I ran the floor and the ceiling:</p>
<table>
<thead>
<tr>
<th></th>
<th>Qwen3-0.6B (floor)</th>
<th>Qwen3.8-27B (ceiling)</th>
</tr>
</thead>
<tbody>
<tr>
<td>call accuracy</td>
<td>26.4%</td>
<td>81.7%</td>
</tr>
<tr>
<td>tool accuracy</td>
<td>34.1%</td>
<td>88.0%</td>
</tr>
<tr>
<td>refusal recall</td>
<td>36.8%</td>
<td>84.2%</td>
</tr>
<tr>
<td>over-refusals</td>
<td>21</td>
<td>6</td>
</tr>
<tr>
<td>208 questions in</td>
<td>47s</td>
<td>152s</td>
</tr>
</tbody>
</table>
<p>About 55 points of headroom. That is the whole exercise: a number to move.</p>
<p>Worth noting, <code>verify_gold.py</code> executes all 208 gold calls against the live network, and all 208 pass. So a miss belongs to the model, not to my plumbing. That acceptance test took an afternoon and saved me from at least three wild-goose chases later.</p>
<h2 id="two-things-that-make-a-tiny-model-viable">Two things that make a tiny model viable</h2>
<p><strong>Constrained decoding, not prompting.</strong> GBNF grammar makes malformed output structurally impossible. You are not hoping for valid JSON; the sampler literally cannot emit anything else. Unconstrained, the 27B answers "is my internet up?" with four paragraphs about ping. Grammar on: <code>{"tool":"get_health","args":{}}</code> in 1.1 seconds. Zero unparseable outputs across 416 generations.</p>
<p><strong>Tools return conclusions, not raw numbers.</strong> Never hand a model <code>[143, 211, 98]</code> and ask if that is unusual. Return this instead:</p>
<pre><code class="language-json">{"current": 211, "baseline_7d": 98, "delta_pct": 115, "verdict": "elevated"}
</code></pre>
<p>Every numeric comparison you move out of the weights is a hallucination you have deleted.</p>
<p>Small gotcha banked along the way: reasoning models and grammars do not mix. With thinking enabled, the grammar constrains the reasoning channel and <code>content</code> comes back empty. Set <code>chat_template_kwargs: {"enable_thinking": false}</code> and move on.</p>
<h2 id="first-training-run">First training run</h2>
<p>Hand-rolled SFT loop, no TRL - I wanted to see the masking logic with my own eyes. Qwen3-0.6B, full fine-tune, 688 examples, 3 epochs.</p>
<p>169 seconds. Val loss 1.5923 to 0.0524.</p>
<table>
<thead>
<tr>
<th>run</th>
<th>call acc</th>
<th>tool acc</th>
<th>refusal recall</th>
</tr>
</thead>
<tbody>
<tr>
<td>base 0.6B</td>
<td>22.6%</td>
<td>33.2%</td>
<td>31.6%</td>
</tr>
<tr>
<td>sft1</td>
<td>64.4%</td>
<td>74.0%</td>
<td>68.4%</td>
</tr>
<tr>
<td>27B ceiling</td>
<td>81.7%</td>
<td>88.0%</td>
<td>84.2%</td>
</tr>
</tbody>
</table>
<p>Three quarters of the distance to a model 45 times its size, from 688 examples and under three minutes of compute. <code>clarify</code> went from 0.0% to 75.0%. Not bad for a 0.6B, imho.</p>
<p>One caveat, though. The base row there is re-scored through the <em>same</em> greedy decode path as the trained model, no grammar on either. The Phase 0 numbers used GBNF. Comparing across that line would have measured the grammar, not the training, and would have handed me a much nicer number than I earned.</p>
<h2 id="the-loss-curve-lies">The loss curve lies</h2>
<p>Same data, same hyperparameters, one flag. <code>--no-mask</code> puts loss on the prompt tokens as well as the answer tokens.</p>
<table>
<thead>
<tr>
<th></th>
<th>masked</th>
<th>unmasked</th>
</tr>
</thead>
<tbody>
<tr>
<td>final val loss</td>
<td>0.0524</td>
<td>0.0561</td>
</tr>
<tr>
<td>call accuracy</td>
<td>64.4%</td>
<td>51.4%</td>
</tr>
<tr>
<td>refusal recall</td>
<td>68.4%</td>
<td>42.1%</td>
</tr>
</tbody>
</table>
<p>A 7% difference in validation loss - the kind you would shrug at or never even see on a chart - is thirteen points of task accuracy. A quarter of the model's usefulness.</p>
<p>If I had been watching the loss curve I would have concluded both runs were fine. That is the entire argument for building the frozen eval before you write any training code. I got to learn it on run two instead of run forty, so I count that.</p>
<h2 id="composition-beats-volume">Composition beats volume</h2>
<p>Two categories got <em>worse</em> after training. The data told me exactly why:</p>
<table>
<thead>
<tr>
<th>tool</th>
<th>training examples</th>
<th>what happened</th>
</tr>
</thead>
<tbody>
<tr>
<td><code>list_wlans</code></td>
<td>5</td>
<td>7 misses, every one routed to <code>get_network</code> (100 examples)</td>
</tr>
<tr>
<td><code>list_port_forwards</code></td>
<td>4</td>
<td>misrouted to <code>clarify</code> and <code>list_clients</code></td>
</tr>
<tr>
<td><code>get_sysinfo</code></td>
<td>4</td>
<td>routed to <code>unsupported</code></td>
</tr>
</tbody>
</table>
<p>My generator capped the dominant tools at 110 so <code>propose_action</code> and <code>get_client</code> would not swamp the set. Capping the head does nothing for the tail. <code>list_wlans</code> kept its five examples, and the model learned the higher-prior rule "named network thing goes to <code>get_network</code>" and cheerfully applied it to SSIDs.</p>
<p>688 examples bought 42 points. Nine missing examples cost two categories outright.</p>
<h2 id="the-ruler-was-broken">The ruler was broken</h2>
<p>I eventually moved to Qwen3-4B with a merged LoRA at r32, which got to 86.5% on the frozen eval. That matches my 27B teacher at 6.75x fewer parameters, which felt great for about a day.</p>
<p>Then I went looking at the two categories still dragging, <code>metrics</code> at 53.8% and <code>actions</code> at 58.3%.</p>
<p>Here is what the shipped model produced for three action questions, and what the tool layer did with each:</p>
<pre><code>"cut off the printer's internet"
  -&gt; propose_action{verb: "block", target: "printer"}
  -&gt; resolved: null, no error, status: ok

"unblock the kids iPad"
  -&gt; propose_action{verb: "unblock", target: "kids iPad"}
  -&gt; resolved: null, no error, status: ok

"bounce the switch that truenas is plugged into"
  -&gt; propose_action{verb: "reconnect", target: "truenas"}
  -&gt; resolved: truenas, no error, status: ok
</code></pre>
<p>The first two name nothing at all. The real printer is <code>prusa-mk3-5</code>, and my resolvers match by substring, so "printer" matches nothing. But <code>propose_action</code> attached <code>resolved: null</code> and returned <em>normally</em>. My dispatcher treats "no error key" as success. So the harness recorded a confident, well-formed, cleanly-executed instruction to act on a device that does not exist, and counted it toward a 98.1% execution rate. (Lovely.)</p>
<p>The third one is the cleanest example of this. <code>truenas</code> resolves. It is a real client. The call is well-formed and executes cleanly. It is also completely wrong, because the user asked about the <em>switch</em> the NAS is plugged into, and this proposal would kick the NAS off the wifi. Nothing anywhere in my stack could tell the difference.</p>
<p>Both paths return errors now. The check that made it safe to tighten them: all 189 executable gold calls still pass. So what the stricter layer rejects was genuinely broken, not merely unusual.</p>
<p>Re-measuring the same weights with the fixed denominator moved execution from 98.1% to 97.1%. Every previously published number for this project was flattering by exactly two phantom calls.</p>
<p>When a metric and a tool disagree about what "worked" means, fix the definition before you touch the model.</p>
<h2 id="confabulation">Confabulation</h2>
<p>With that fixed, I built a second evaluation that needs no answer key at all. 74 questions the frozen eval does not contain, built from live inventory, scored only on things that are objectively checkable. Does a <code>propose_action</code> target resolve to a real device? Is a <code>metric_query</code> id in the catalog? Does a <code>clarify</code> assert something about the inventory that is false?</p>
<p>None of that can be improved by fitting the referee, which was the point. I had read those 208 eval questions far too many times.</p>
<p>Then I ran it across the whole family.</p>
<table>
<thead>
<tr>
<th>model</th>
<th>confabulation</th>
<th>unparseable</th>
<th>invented a metric id</th>
</tr>
</thead>
<tbody>
<tr>
<td>Qwen3-0.6B, untuned</td>
<td>9.5%</td>
<td>11 / 74</td>
<td>-</td>
</tr>
<tr>
<td>Qwen3-1.7B, untuned</td>
<td>5.4%</td>
<td>7 / 74</td>
<td>-</td>
</tr>
<tr>
<td>Qwen3-4B, untuned</td>
<td>5.4%</td>
<td>7 / 74</td>
<td>0</td>
</tr>
<tr>
<td>Qwen3-4B, fine-tuned</td>
<td>9.7%</td>
<td>0</td>
<td>5</td>
</tr>
<tr>
<td>Qwen3.8-27B teacher</td>
<td>0.0%</td>
<td>0</td>
<td>0</td>
</tr>
</tbody>
</table>
<p>Read rows three and four together.</p>
<p>The untuned base <em>never once</em> invented a catalog id. Asked whether the radio link to the kitchen AP had been deteriorating, it produced no parseable call at all for seven of 74 questions, and otherwise stayed inside the catalog. My fine-tune removed every single parse failure, and produced five confident references to <code>wlan_signal</code> and <code>wlan_link_quality</code>, neither of which exists anywhere except in the model's own output. Both names are extremely plausible. Neither is in the catalog printed in its own prompt.</p>
<p>Fine-tuning did not reduce hallucination. It made hallucination well-formed.</p>
<p>And it is the same fact. My training set taught fluency in the output format and never once penalized invention, because no example in it ever needed to. So the model learned that a syntactically valid call is always available - true - and that its contents are always allowed. Which is not.</p>
<p>That inverts the intuition that the less-trained model is the riskier one. The base model's failures are <em>visible</em>: malformed output, an obvious error, a thing you notice. The fine-tune's failures are <em>invisible</em>: well-formed, executable, and wrong.</p>
<p>The 27B row matters too. It scores 0.0%, so this is not "every model does this." A big model handles it fine. The claim is narrower and more useful: fine-tuning a small model on data that never punished invention created a failure mode the base model did not have.</p>
<p>Fixing it was mostly a data problem, and it worked. A later revision matched the 27B's 0.0% while routing action-shaped questions <em>better</em> than the teacher does - 27 of 27 against 20 of 27. Which also rules out the boring "it just got timid" explanation.</p>
<h2 id="two-seeds-is-not-a-control">Two seeds is not a control</h2>
<p>I need to include this one, because the rest of the post reads too clean without it.</p>
<p>Every claim I made over those two days was measured against a control group of two seeds with a 0.5-point spread. I said out loud, more than once, that a spread that tight looked wrong. And then I kept iterating anyway.</p>
<p>Eventually I ran a third control seed. It moved the control from 86.3% to 87.0% and widened the spread from 0.5 to 2.4 points.</p>
<table>
<thead>
<tr>
<th>group</th>
<th>seeds</th>
<th>call accuracy</th>
<th>range</th>
</tr>
</thead>
<tbody>
<tr>
<td>control</td>
<td>3</td>
<td>87.0 +/- 1.2</td>
<td>86.1 - 88.5</td>
</tr>
<tr>
<td>v12</td>
<td>3</td>
<td>87.7 +/- 1.7</td>
<td>85.6 - 88.9</td>
</tr>
<tr>
<td>v13</td>
<td>5</td>
<td>87.9 +/- 2.2</td>
<td>85.6 - 89.9</td>
</tr>
</tbody>
</table>
<p>My own run picker started returning the <em>control</em> as the winner and printing "tied within noise" for all three. On the headline number, five dataset revisions bought nothing measurable. The two-seed control was not a control, it was a lucky pair, and everything measured against its spread was measured against noise.</p>
<p>That third seed cost 45 minutes. It should have been the first thing I did.</p>
<p>What survives, with ranges still disjoint from the control's:</p>
<table>
<thead>
<tr>
<th></th>
<th>control</th>
<th>v13</th>
</tr>
</thead>
<tbody>
<tr>
<td>args given tool</td>
<td>92.8 +/- 0.6</td>
<td>94.5 +/- 0.8</td>
</tr>
<tr>
<td><code>metric_query</code></td>
<td>51.3 +/- 3.8</td>
<td>87.7 +/- 7.7</td>
</tr>
<tr>
<td><code>propose_action</code></td>
<td>54.5 +/- 9.1</td>
<td>76.4 +/- 4.5</td>
</tr>
<tr>
<td><code>get_health</code></td>
<td>57.1 +/- 0.0</td>
<td>77.1 +/- 14.3</td>
</tr>
<tr>
<td>probe confabulation</td>
<td>9.7%</td>
<td>0.0%</td>
</tr>
</tbody>
</table>
<p>So. Net result: the work did not improve aggregate accuracy. It changed the failure mode. The model gets about the same proportion of questions right, and is far less likely to be confidently wrong in a way that reaches real hardware. Those are different properties, and I managed to conflate them for two solid days.</p>
<h2 id="one-more-negative-result">One more negative result</h2>
<p>The plan for RL was to retry GRPO now that the model gets enough right for a k-sample filter to find prompts in the 20-80% success band, where group-relative advantage is actually non-zero. Two previous attempts had died on a saturated reward.</p>
<p>Before spending an hour on rollouts, I spent twenty minutes sampling k=8 at temperature 1.0 and printing a histogram:</p>
<table>
<thead>
<tr>
<th>success rate</th>
<th>training set (240)</th>
<th>hard set (90)</th>
</tr>
</thead>
<tbody>
<tr>
<td>always right</td>
<td>220 (91.7%)</td>
<td>71 (78.9%)</td>
</tr>
<tr>
<td>in band 0.2 - 0.8</td>
<td>8 (3.3%)</td>
<td>5 (5.6%)</td>
</tr>
<tr>
<td>always wrong</td>
<td>1</td>
<td>8 (8.9%)</td>
</tr>
</tbody>
</table>
<p>Thirteen usable prompts. GRPO is not blocked by my optimizer or my reward function, it is blocked by a policy too confident to disagree with itself. Eight prompts that are wrong all eight times have exactly as little gradient as eight that are right all eight times.</p>
<p>Run the cheap diagnostic before the expensive optimizer. That histogram would have killed both previous attempts for twenty minutes each.</p>
<h2 id="what-i-learned">What I learned</h2>
<p><strong>Build the referee before the player.</strong> A frozen eval, a hash to stop you editing it, and an acceptance test proving every question is answerable by your plumbing. Do the question set <em>before</em> you look at the training data - if you can't write two hundred questions about the thing, you don't know what the thing is. And run the gold answers through the live system once, so that when the model misses, the miss is the model's and not your wiring. That acceptance test took an afternoon. It was the cheapest insurance in the whole project.</p>
<p><strong>Check what your data generator silently guarantees.</strong> One line of template code meant the correct answer was always a literal substring of the question, so a whole capability was never trained and no per-tool metric could possibly show it. The fix is a grep: generate the set once, and look for answers sitting inside the questions. Any silent guarantee in the generator shows up in the data before it ever shows up in a chart.</p>
<p><strong>The loss curve lies.</strong> A difference you would not notice was a quarter of the model's task accuracy. So don't make decisions off it. Keep an eval that finishes in a couple of minutes, run it after every single change, and treat val loss as a sanity check for "is it learning something" - not as a score.</p>
<p><strong>Fine-tuning for structured output can manufacture confident nonsense.</strong> It removes the visible failure and can add an invisible one. Accuracy cannot see it, so score for it directly: does the named target exist? Is the ID in the catalog? Does a refusal claim something false about the system? Build that check once, keep it, and run it against the untuned base too - the base's failures are ugly and obvious, and that contrast is most of the lesson.</p>
<p><strong>Your control group needs as many seeds as your challenger.</strong> A two-seed control with a suspiciously tight spread is not a yardstick. I let one underwrite two days of conclusions. If a spread looks too small to be real, it is - run the extra seed. It costs less than one rollout hour, and it tells you whether your "win" is a pair of dice.</p>
<p>That is the list. No magic hyperparameters, no trick I can paste into a tweet. The model ended up matching the 27B on confabulation (0.0%), routing action-shaped questions slightly better, and landing right on top of the control on aggregate accuracy. Same number of correct answers, different kind of wrong - that is the takeaway. And the biggest wins were not in the model at all. They were in the plumbing around it.</p>
<p>Next, the obvious bit: find the ~13 prompts that actually leave GRPO something to optimize against, and see if preference tuning does anything the data revisions did not. If it does not, I will keep the 4B as-is. It already answers "what's on the guest wifi?" well enough, and that is a question I actually ask, from the couch, more than you would think.</p>
<p>The whole thing runs on one 3090 sharing a desktop. The lab notebook, the per-run analyses, and every wrong turn are in the repo - because the wrong turns were most of the value. If the eval harness or the grammar setup is useful to you (or it breaks in an interesting way), tell me.</p>
<p>All for now...</p>
<p>-BadgerOps</p>
